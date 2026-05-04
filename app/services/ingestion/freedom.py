"""Freedom Finance TraderNet adapter using direct HTTP calls.

The `tradernet` PyPI package (0.1.3) has no importable source; this module
implements HMAC-SHA256 signing and REST calls directly using `requests`.
API base: https://tradernet.com/api
Auth: public_key + HMAC-SHA256(private_key, JSON_body).
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import date, timedelta

import requests

from app.config import get_settings
from app.services.ingestion.broker import (
    BrokerSyncError,
    PositionRow,
    TransactionRow,
    upsert_positions,
    upsert_transactions,
)

logger = logging.getLogger(__name__)

_API_URL = "https://tradernet.com/api"
_TIMEOUT = 30
_MAX_RETRIES = 2
_BROKER = "freedom"

# TraderNet portfolio API method name (REST endpoint)
_METHOD_PORTFOLIO = "getPortfolio"
# TraderNet trade history API method name
_METHOD_TRANSACTIONS = "getTransactionHistory"


def _send_request(method: str, params: dict | None = None) -> dict:
    """Send HMAC-signed request to TraderNet REST API.

    Raises BrokerSyncError on auth failure, timeout, or unexpected HTTP response.
    Never logs the response payload (PII/financial data rule).
    """
    settings = get_settings()
    if not settings.FREEDOM_PUBLIC_KEY or not settings.FREEDOM_PRIVATE_KEY:
        raise BrokerSyncError("Freedom Finance API keys not configured in environment")

    payload = json.dumps(
        {"method": method, "apiKey": settings.FREEDOM_PUBLIC_KEY, **(params or {})},
        separators=(",", ":"),
        sort_keys=True,
    )
    sig = hmac.new(
        settings.FREEDOM_PRIVATE_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                _API_URL,
                data={"data": payload, "sig": sig},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout as exc:
            last_exc = exc
            logger.warning("Freedom API timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES + 1)
        except requests.HTTPError as exc:
            raise BrokerSyncError(
                f"Freedom API HTTP {exc.response.status_code}: {exc.response.reason}"
            ) from exc
        except requests.RequestException as exc:
            raise BrokerSyncError(f"Freedom API request failed: {exc}") from exc

        if attempt < _MAX_RETRIES:
            time.sleep(2**attempt)  # 1s, 2s

    raise BrokerSyncError(
        f"Freedom API timed out after {_MAX_RETRIES + 1} attempts ({_TIMEOUT}s each)"
    ) from last_exc


def _normalize_freedom_position(item: dict) -> PositionRow | None:
    """Normalize a TraderNet portfolio position dict to PositionRow. Returns None on bad data."""
    ticker = item.get("i", "")
    if not ticker:
        logger.warning("Freedom position item missing ticker field, skipping")
        return None
    try:
        return PositionRow(
            ticker=str(ticker),
            qty=float(item.get("q") or 0),
            market_value=float(item.get("s") or 0),
            cost_basis=float(item.get("open_bal") or 0),
            currency=str(item.get("curr") or "USD"),
            broker=_BROKER,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("Skipping Freedom position %s: %s", ticker, exc)
        return None


def _normalize_freedom_transaction(item: dict) -> TransactionRow | None:
    """Normalize a TraderNet order dict to TransactionRow. Returns None on bad data."""
    order_id = str(item.get("id") or "")
    ticker = str(item.get("instr") or "")
    if not ticker:
        logger.warning("Freedom transaction missing ticker, skipping")
        return None

    try:
        ts = item.get("date") or 0
        trade_date = date.fromtimestamp(float(ts)) if ts else date.today()

        oper = int(item.get("oper") or 1)
        txn_type = "BUY" if oper in (1, 2) else "SELL"

        qty = abs(float(item.get("q") or 0))
        price = float(item.get("p") or 0)

        ibkr_txn_id = (
            f"freedom_{order_id}"
            if order_id
            else f"freedom_{trade_date.isoformat()}_{ticker}_{qty}"
        )

        return TransactionRow(
            ibkr_txn_id=ibkr_txn_id,
            ticker=ticker,
            trade_date=trade_date,
            txn_type=txn_type,
            qty=qty,
            price=price,
            amount=abs(qty * price),
            commission=float(item.get("commission") or 0),
            currency=str(item.get("curr") or "USD"),
            broker=_BROKER,
        )
    except (ValueError, TypeError, OSError) as exc:
        logger.warning("Skipping Freedom transaction %s: %s", order_id, exc)
        return None


def sync_freedom_positions(db) -> int:
    """Fetch Freedom Finance portfolio and upsert positions. Returns count of rows upserted.

    Raises BrokerSyncError on API failure. Never calls db.commit() — caller owns transaction.
    """
    data = _send_request(_METHOD_PORTFOLIO)

    # Expected response shape: {"result": {"pos": [...]}} or {"pos": [...]}
    positions_raw = (
        data.get("result", {}).get("pos")
        or data.get("pos")
        or []
    )

    rows = [r for item in positions_raw if (r := _normalize_freedom_position(item)) is not None]
    count = upsert_positions(db, rows)
    logger.info("Synced %d positions from Freedom Finance", count)
    return count


def sync_freedom_transactions(db) -> int:
    """Fetch Freedom Finance trade history (last 365 days) and upsert. Returns count upserted.

    Raises BrokerSyncError on API failure. Never calls db.commit() — caller owns transaction.
    """
    today = date.today()
    from_date = (today - timedelta(days=365)).isoformat()
    to_date = today.isoformat()

    data = _send_request(_METHOD_TRANSACTIONS, {"from": from_date, "to": to_date})

    transactions_raw = (
        data.get("result", {}).get("orders")
        or data.get("orders")
        or data.get("result", {}).get("transactions")
        or data.get("transactions")
        or []
    )

    rows = [
        r
        for item in transactions_raw
        if (r := _normalize_freedom_transaction(item)) is not None
    ]
    count = upsert_transactions(db, rows)
    logger.info("Synced %d transactions from Freedom Finance", count)
    return count
