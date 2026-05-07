"""Config table read/write. Key-value store for target allocations, budget, etc."""

import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Config

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, str] = {
    "allocation.VWCE": "65",
    "allocation.VEUR": "15",
    "allocation.AGGH": "15",
    "allocation.XEON": "5",
    "budget_usd": "200",
    "assumed_return_pct": "8",
    "goal_usd": "1300000",
    "btd_threshold_pct": "-10",
    "btd_extra_budget_usd": "200",
}

TARGET_TICKERS = ["VWCE", "VEUR", "AGGH", "XEON"]


def seed_defaults(db: Session) -> None:
    """Insert default config rows if they don't exist."""
    for key, value in _DEFAULTS.items():
        stmt = pg_insert(Config).values(key=key, value=value)
        stmt = stmt.on_conflict_do_nothing(index_elements=["key"])
        db.execute(stmt)


def get_all(db: Session) -> dict[str, str]:
    seed_defaults(db)
    rows = db.query(Config).all()
    return {r.key: r.value for r in rows}


def get_float(db: Session, key: str) -> float:
    cfg = get_all(db)
    return float(cfg.get(key, _DEFAULTS.get(key, "0")))


def get_target_allocations(db: Session) -> dict[str, float]:
    cfg = get_all(db)
    return {
        ticker: float(cfg.get(f"allocation.{ticker}", _DEFAULTS.get(f"allocation.{ticker}", "0")))
        for ticker in TARGET_TICKERS
    }


def save(db: Session, updates: dict[str, str]) -> None:
    """Upsert config keys. Values validated as non-empty strings."""
    for key, value in updates.items():
        stmt = pg_insert(Config).values(key=key, value=str(value))
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={"value": stmt.excluded.value},
        )
        db.execute(stmt)
