"""IBKR Flex Query XML parser. Live CP Gateway not feasible headless on VPS.
Use Flex XML upload (Activity Statement, XML format) for full sync."""

import logging
import xml.etree.ElementTree as ET
from datetime import date

from sqlalchemy.orm import Session

from app.services.ingestion.broker import (
    BrokerSyncError,
    PositionRow,
    TransactionRow,
    upsert_positions,
    upsert_transactions,
)

logger = logging.getLogger(__name__)

_BROKER = "ibkr"


def parse_flex_xml(file_content: bytes) -> tuple[list[PositionRow], list[TransactionRow]]:
    """Parse IBKR Flex Activity Statement XML. Returns (positions, transactions).

    Raises BrokerSyncError on unparseable XML or missing required fields.
    Uses element.get() with safe defaults; logs warnings for unexpected data.
    """
    try:
        root = ET.fromstring(file_content)
    except ET.ParseError as exc:
        raise BrokerSyncError(f"Invalid XML: {exc}") from exc

    positions: list[PositionRow] = []
    for elem in root.iter("OpenPosition"):
        ticker = elem.get("symbol")
        if not ticker:
            logger.warning("OpenPosition missing 'symbol' attribute, skipping")
            continue
        try:
            positions.append(
                PositionRow(
                    ticker=ticker,
                    qty=float(elem.get("position") or 0),
                    market_value=float(elem.get("positionValue") or 0),
                    cost_basis=float(elem.get("costBasisMoney") or 0),
                    currency=elem.get("currency") or "USD",
                    broker=_BROKER,
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("Skipping OpenPosition %s: %s", ticker, exc)

    transactions: list[TransactionRow] = []
    for elem in root.iter("Trade"):
        txn_id = elem.get("tradeID")
        if not txn_id:
            # Row without tradeID is a summary/lot entry — skip
            continue

        ticker = elem.get("symbol")
        if not ticker:
            logger.warning("Trade %s missing 'symbol', skipping", txn_id)
            continue

        try:
            trade_date_str = elem.get("tradeDate") or ""
            trade_date = (
                date.fromisoformat(trade_date_str) if trade_date_str else date.today()
            )

            qty_raw = float(elem.get("quantity") or 0)
            buy_sell = (elem.get("buySell") or "BUY").upper()
            txn_type = "BUY" if buy_sell == "BUY" or qty_raw > 0 else "SELL"

            transactions.append(
                TransactionRow(
                    ibkr_txn_id=txn_id,
                    ticker=ticker,
                    trade_date=trade_date,
                    txn_type=txn_type,
                    qty=abs(qty_raw),
                    price=float(elem.get("tradePrice") or 0),
                    amount=abs(float(elem.get("tradeMoney") or 0)),
                    commission=abs(float(elem.get("ibCommission") or 0)),
                    currency=elem.get("currency") or "USD",
                    broker=_BROKER,
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("Skipping Trade %s: %s", txn_id, exc)

    return positions, transactions


def import_flex_xml(file_content: bytes, db: Session) -> dict:
    """Parse XML and upsert positions + transactions. Returns row counts.

    Raises BrokerSyncError on parse failure. Never calls db.commit() — caller owns transaction.
    """
    positions, transactions = parse_flex_xml(file_content)
    pos_count = upsert_positions(db, positions)
    txn_count = upsert_transactions(db, transactions)
    logger.info("IBKR Flex import: %d positions, %d transactions", pos_count, txn_count)
    return {"positions": pos_count, "transactions": txn_count}


def sync_ibkr_positions(db: Session) -> int:
    """Live IBKR CP Gateway not feasible headless on VPS. Direct to upload form."""
    raise BrokerSyncError(
        "IBKR live API requires CP Gateway (not available headless). "
        "Use Flex XML upload at /sync/ibkr instead."
    )
