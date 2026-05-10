"""Add watchlist_items table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10

"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(200)),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("added_at", sa.DateTime),
        sa.Column("last_synced_at", sa.DateTime),
        sa.Column("sync_status", sa.String(10), default="new"),
        sa.Column("current_price", sa.Float),
        sa.Column("ytd_return_pct", sa.Float),
        sa.Column("drawdown_from_peak", sa.Float),
        sa.Column("volatility_pct", sa.Float),
        sa.Column("llm_analysis", sa.Text),
        sa.Column("llm_analyzed_at", sa.DateTime),
        sa.Column("chart_data_json", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
