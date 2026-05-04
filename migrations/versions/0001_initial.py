"""Initial schema: all 10 tables + pgvector extension

Revision ID: 0001
Revises:
Create Date: 2026-05-04

"""

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension must exist before any vector column DDL
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "config",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "instruments",
        sa.Column("ticker", sa.String(20), primary_key=True),
        sa.Column("isin", sa.String(12)),
        sa.Column("name", sa.String(255)),
        sa.Column("category", sa.String(50)),
        sa.Column("currency", sa.String(10)),
        sa.Column("exchange", sa.String(50)),
        sa.Column("active", sa.Boolean, default=True),
    )

    op.create_table(
        "prices",
        sa.Column("ticker", sa.String(20), primary_key=True),
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("open", sa.Float),
        sa.Column("high", sa.Float),
        sa.Column("low", sa.Float),
        sa.Column("close", sa.Float),
        sa.Column("volume", sa.BigInteger),
    )

    op.create_table(
        "positions",
        sa.Column("snapshot_date", sa.Date, primary_key=True),
        sa.Column("ticker", sa.String(20), primary_key=True),
        sa.Column("quantity", sa.Float),
        sa.Column("avg_cost_usd", sa.Float),
        sa.Column("market_value_usd", sa.Float),
        sa.Column("broker", sa.String(20)),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Float),
        sa.Column("price_usd", sa.Float),
        sa.Column("amount_usd", sa.Float),
        sa.Column("fee_usd", sa.Float),
        sa.Column("broker", sa.String(20)),
        sa.Column("ibkr_txn_id", sa.String(50)),
        sa.UniqueConstraint("ibkr_txn_id", name="uq_transactions_ibkr_txn_id"),
    )

    op.create_table(
        "external_balances",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("source", sa.String(50), primary_key=True),
        sa.Column("asset", sa.String(50), primary_key=True),
        sa.Column("amount_usd", sa.Float),
        sa.Column("apy_pct", sa.Float),
    )

    op.create_table(
        "channel_signals",
        sa.Column("channel", sa.String(100), primary_key=True),
        sa.Column("source_msg_id", sa.String(50), primary_key=True),
        sa.Column("message_date", sa.DateTime),
        sa.Column("ticker", sa.String(20)),
        sa.Column("sentiment", sa.String(10)),
        sa.Column("excerpt", sa.Text),
        sa.Column("embedding", sa.Text),  # vector type applied via raw SQL below
    )
    # Replace the Text placeholder with the actual vector type
    op.execute("ALTER TABLE channel_signals ALTER COLUMN embedding TYPE vector(1024) USING NULL")

    op.create_table(
        "recommendations",
        sa.Column("month", sa.String(7), primary_key=True),
        sa.Column("ticker", sa.String(20), primary_key=True),
        sa.Column("amount_usd", sa.Float),
        sa.Column("week_of_month", sa.Integer),
        sa.Column("rationale", sa.Text),
        sa.Column("executed", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "progress_snapshots",
        sa.Column("month", sa.String(7), primary_key=True),
        sa.Column("total_capital_usd", sa.Float),
        sa.Column("broker_capital_usd", sa.Float),
        sa.Column("staking_capital_usd", sa.Float),
        sa.Column("ttm_return_pct", sa.Float),
        sa.Column("projected_capital_2046_usd", sa.Float),
        sa.Column("delta_to_goal_usd", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "course_chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column("page_num", sa.Integer),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text),  # vector type applied via raw SQL below
    )
    op.execute("ALTER TABLE course_chunks ALTER COLUMN embedding TYPE vector(1024) USING NULL")


def downgrade() -> None:
    op.drop_table("course_chunks")
    op.drop_table("progress_snapshots")
    op.drop_table("recommendations")
    op.drop_table("channel_signals")
    op.drop_table("external_balances")
    op.drop_table("transactions")
    op.drop_table("positions")
    op.drop_table("prices")
    op.drop_table("instruments")
    op.drop_table("config")
    op.execute("DROP EXTENSION IF EXISTS vector")
