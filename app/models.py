from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Config(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Instrument(Base):
    __tablename__ = "instruments"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    isin: Mapped[str | None] = mapped_column(String(12))
    name: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str | None] = mapped_column(String(10))
    exchange: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Price(Base):
    __tablename__ = "prices"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(BigInteger)


class Position(Base):
    __tablename__ = "positions"

    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    quantity: Mapped[float | None] = mapped_column(Float)
    avg_cost_usd: Mapped[float | None] = mapped_column(Float)
    market_value_usd: Mapped[float | None] = mapped_column(Float)
    broker: Mapped[str | None] = mapped_column(String(20))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("ibkr_txn_id", name="uq_transactions_ibkr_txn_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL / DIV
    quantity: Mapped[float | None] = mapped_column(Float)
    price_usd: Mapped[float | None] = mapped_column(Float)
    amount_usd: Mapped[float | None] = mapped_column(Float)
    fee_usd: Mapped[float | None] = mapped_column(Float)
    broker: Mapped[str | None] = mapped_column(String(20))
    ibkr_txn_id: Mapped[str | None] = mapped_column(String(50))


class ExternalBalance(Base):
    __tablename__ = "external_balances"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset: Mapped[str] = mapped_column(String(50), primary_key=True)
    amount_usd: Mapped[float | None] = mapped_column(Float)
    apy_pct: Mapped[float | None] = mapped_column(Float)


class ChannelSignal(Base):
    __tablename__ = "channel_signals"

    channel: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_msg_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    message_date: Mapped[datetime | None] = mapped_column(DateTime)
    ticker: Mapped[str | None] = mapped_column(String(20))
    sentiment: Mapped[str | None] = mapped_column(String(10))  # positive / negative / neutral
    excerpt: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(Vector(1024))


class Recommendation(Base):
    __tablename__ = "recommendations"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)  # YYYY-MM
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    amount_usd: Mapped[float | None] = mapped_column(Float)
    week_of_month: Mapped[int | None] = mapped_column(Integer)
    rationale: Mapped[str | None] = mapped_column(Text)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProgressSnapshot(Base):
    __tablename__ = "progress_snapshots"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)  # YYYY-MM
    total_capital_usd: Mapped[float | None] = mapped_column(Float)
    broker_capital_usd: Mapped[float | None] = mapped_column(Float)
    staking_capital_usd: Mapped[float | None] = mapped_column(Float)
    ttm_return_pct: Mapped[float | None] = mapped_column(Float)
    projected_capital_2046_usd: Mapped[float | None] = mapped_column(Float)
    delta_to_goal_usd: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CourseChunk(Base):
    __tablename__ = "course_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    page_num: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(1024))
