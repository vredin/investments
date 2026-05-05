"""Price cache service — fetches OHLCV history via yfinance and upserts into prices table."""

import logging
from datetime import date

import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Position, Price

logger = logging.getLogger(__name__)

# Target ETFs: DB ticker → yfinance symbol
_TARGET_ETF_MAP: dict[str, str] = {
    "VWCE": "VWCE.AS",
    "VEUR": "VEUR.AS",
    "AGGH": "AGGH.L",
    "XEON": "XEON.DE",
}

_FREEDOM_SUFFIX = ".US"
_HISTORY_PERIOD = "1y"  # ~250 trading days — covers SMA200 + 52w drawdown


def _to_yf_symbol(db_ticker: str) -> str:
    """Map internal DB ticker to yfinance symbol."""
    if db_ticker in _TARGET_ETF_MAP:
        return _TARGET_ETF_MAP[db_ticker]
    if db_ticker.endswith(_FREEDOM_SUFFIX):
        return db_ticker[: -len(_FREEDOM_SUFFIX)]
    return db_ticker


def _fetch_ticker_prices(db_ticker: str) -> list[dict]:
    """Fetch price history for one ticker. Returns list of row dicts or empty on failure."""
    yf_symbol = _to_yf_symbol(db_ticker)
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=_HISTORY_PERIOD, interval="1d", auto_adjust=True, timeout=30)
        if hist.empty:
            logger.warning("No price data returned for %s (yf: %s)", db_ticker, yf_symbol)
            return []
        rows = []
        for idx, row in hist.iterrows():
            trade_date: date = idx.date() if hasattr(idx, "date") else idx
            rows.append({
                "ticker": db_ticker,
                "date": trade_date,
                "open": float(row["Open"]) if row["Open"] == row["Open"] else None,
                "high": float(row["High"]) if row["High"] == row["High"] else None,
                "low": float(row["Low"]) if row["Low"] == row["Low"] else None,
                "close": float(row["Close"]) if row["Close"] == row["Close"] else None,
                "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else None,
            })
        return rows
    except Exception as exc:
        logger.warning("Price fetch failed for %s (yf: %s): %s", db_ticker, yf_symbol, exc)
        return []


def sync_prices(db: Session) -> dict:
    """Fetch 1y of daily OHLCV for all position tickers + target ETFs. Returns summary dict."""
    position_tickers: set[str] = {
        row[0] for row in db.query(Position.ticker).distinct().all()
    }
    all_tickers = position_tickers | set(_TARGET_ETF_MAP.keys())

    total_rows = 0
    failed: list[str] = []

    for db_ticker in sorted(all_tickers):
        rows = _fetch_ticker_prices(db_ticker)
        if not rows:
            failed.append(db_ticker)
            continue

        stmt = pg_insert(Price).values(rows)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "date"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        db.execute(upsert_stmt)
        total_rows += len(rows)
        logger.info("Synced %d price rows for %s", len(rows), db_ticker)

    return {"rows": total_rows, "tickers": len(all_tickers), "failed": failed}
