"""Unified broker interface: DTOs, upsert functions, sync orchestration."""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Instrument, Position, Transaction

logger = logging.getLogger(__name__)


class BrokerSyncError(Exception):
    """Raised when a broker adapter fails to sync data."""


@dataclass
class PositionRow:
    ticker: str
    qty: float
    market_value: float
    cost_basis: float
    currency: str
    broker: str


@dataclass
class TransactionRow:
    ibkr_txn_id: str
    ticker: str
    trade_date: date
    txn_type: str  # BUY / SELL / DIV
    qty: float
    price: float
    amount: float
    commission: float
    currency: str
    broker: str


def upsert_instrument(db: Session, ticker: str) -> None:
    """Insert stub instrument row if ticker is not already in instruments table."""
    stmt = pg_insert(Instrument).values(
        ticker=ticker,
        name=ticker,
        active=True,
    ).on_conflict_do_nothing(index_elements=["ticker"])
    db.execute(stmt)


def upsert_positions(db: Session, rows: list[PositionRow]) -> int:
    """Upsert positions for today's snapshot date. Returns count of rows processed."""
    if not rows:
        return 0

    today = date.today()

    for row in rows:
        upsert_instrument(db, row.ticker)

    values = [
        {
            "snapshot_date": today,
            "ticker": row.ticker,
            "quantity": row.qty,
            "avg_cost_usd": row.cost_basis,
            "market_value_usd": row.market_value,
            "broker": row.broker,
        }
        for row in rows
    ]

    insert_stmt = pg_insert(Position).values(values)
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["snapshot_date", "ticker"],
        set_={
            "quantity": insert_stmt.excluded.quantity,
            "avg_cost_usd": insert_stmt.excluded.avg_cost_usd,
            "market_value_usd": insert_stmt.excluded.market_value_usd,
            "broker": insert_stmt.excluded.broker,
        },
    )
    db.execute(upsert_stmt)
    return len(rows)


def upsert_transactions(db: Session, rows: list[TransactionRow]) -> int:
    """Upsert transactions keyed on ibkr_txn_id UNIQUE constraint. Returns count processed."""
    if not rows:
        return 0

    for row in rows:
        upsert_instrument(db, row.ticker)

    values = [
        {
            "trade_date": row.trade_date,
            "ticker": row.ticker,
            "type": row.txn_type,
            "quantity": row.qty,
            "price_usd": row.price,
            "amount_usd": row.amount,
            "fee_usd": row.commission,
            "broker": row.broker,
            "ibkr_txn_id": row.ibkr_txn_id,
        }
        for row in rows
    ]

    insert_stmt = pg_insert(Transaction).values(values)
    upsert_stmt = insert_stmt.on_conflict_do_update(
        constraint="uq_transactions_ibkr_txn_id",
        set_={
            "quantity": insert_stmt.excluded.quantity,
            "price_usd": insert_stmt.excluded.price_usd,
            "amount_usd": insert_stmt.excluded.amount_usd,
            "fee_usd": insert_stmt.excluded.fee_usd,
        },
    )
    db.execute(upsert_stmt)
    return len(rows)


def sync_all_brokers(db: Session) -> dict:
    """Orchestrate sync across all brokers. One broker failure does not abort others."""
    from app.services.ingestion import freedom, ibkr  # local import to avoid circular refs

    results: dict = {
        "ibkr_positions": 0,
        "freedom_positions": 0,
        "freedom_transactions": 0,
        "errors": [],
    }

    try:
        results["ibkr_positions"] = ibkr.sync_ibkr_positions(db)
    except BrokerSyncError as exc:
        logger.warning("IBKR sync skipped: %s", exc)
        results["errors"].append(f"IBKR: {exc}")

    try:
        results["freedom_positions"] = freedom.sync_freedom_positions(db)
    except BrokerSyncError as exc:
        logger.warning("Freedom positions sync failed: %s", exc)
        results["errors"].append(f"Freedom positions: {exc}")

    try:
        results["freedom_transactions"] = freedom.sync_freedom_transactions(db)
    except BrokerSyncError as exc:
        logger.warning("Freedom transactions sync failed: %s", exc)
        results["errors"].append(f"Freedom transactions: {exc}")

    return results
