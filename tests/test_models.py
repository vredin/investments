from datetime import date

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    Transaction,
)
from tests.conftest import requires_db

pytestmark = requires_db

EXPECTED_TABLES = {
    "config",
    "instruments",
    "prices",
    "positions",
    "transactions",
    "external_balances",
    "channel_signals",
    "recommendations",
    "progress_snapshots",
    "course_chunks",
}


def test_all_tables_exist(engine):
    inspector = inspect(engine)
    actual = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(actual), f"Missing tables: {EXPECTED_TABLES - actual}"


def test_ibkr_txn_id_unique_constraint(db_session):
    txn_a = Transaction(trade_date=date(2026, 1, 1), ticker="VWCE", type="BUY", ibkr_txn_id="TXN001")
    txn_b = Transaction(trade_date=date(2026, 1, 2), ticker="VWCE", type="BUY", ibkr_txn_id="TXN001")
    db_session.add(txn_a)
    db_session.commit()
    db_session.add(txn_b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_course_chunks_has_embedding_column(engine):
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("course_chunks")}
    assert "embedding" in columns


def test_channel_signals_has_embedding_column(engine):
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("channel_signals")}
    assert "embedding" in columns


def test_embedding_column_is_vector_type(engine):
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name='course_chunks' AND column_name='embedding'"
            )
        ).fetchone()
    assert result is not None
    # pgvector registers as 'USER-DEFINED' in information_schema
    assert result[0] in ("USER-DEFINED", "vector")
