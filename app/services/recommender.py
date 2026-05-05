"""Subsystem A: monthly buy plan algorithm.
Underweight-first allocation + oversold scoring (SMA200 / RSI / 52w drawdown).
"""

import logging
from dataclasses import dataclass
from statistics import mean

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Position, Price, Recommendation
from app.services import settings_service

logger = logging.getLogger(__name__)


@dataclass
class BuyRow:
    ticker: str
    amount_usd: float
    week_of_month: int
    target_pct: float
    current_pct: float
    deviation_pct: float
    rationale: str


def _calc_rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = mean(gains[-period:])
    avg_loss = mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _oversold_score(db: Session, ticker: str) -> float:
    """0.0–1.0, higher = more oversold. Returns 0.0 if insufficient price data."""
    prices = (
        db.query(Price)
        .filter(Price.ticker == ticker)
        .order_by(Price.date.asc())
        .all()
    )
    closes = [p.close for p in prices if p.close is not None]
    if len(closes) < 20:
        return 0.0

    current = closes[-1]
    sma200 = mean(closes[-200:]) if len(closes) >= 200 else mean(closes)
    sma_score = max(0.0, (sma200 - current) / sma200)

    high_52w = max(closes[-252:] if len(closes) >= 252 else closes)
    drawdown_score = max(0.0, (high_52w - current) / high_52w) if high_52w > 0 else 0.0

    rsi = _calc_rsi(closes[-15:])
    rsi_score = max(0.0, (30 - rsi) / 30) if rsi < 30 else 0.0

    return (sma_score + drawdown_score + rsi_score) / 3


def _llm_rationale(ticker: str, target_pct: float, current_pct: float) -> str:
    """One-sentence rationale via OpenRouter. Falls back to static string on any error."""
    try:
        from openai import OpenAI

        from app.config import get_settings

        settings = get_settings()
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")
        client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=30,
        )
        prompt = (
            f"You are a portfolio advisor. Write ONE concise sentence (max 25 words) "
            f"explaining why buying {ticker} makes sense this month. "
            f"Current weight: {current_pct:.1f}%, target: {target_pct:.1f}%."
        )
        resp = client.chat.completions.create(
            model="anthropic/claude-sonnet-4-5",
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("LLM rationale failed for %s: %s", ticker, exc)
        return f"Allocation-driven purchase — target {target_pct:.0f}%, current {current_pct:.1f}%."


def generate_buy_plan(budget_usd: float, db: Session) -> list[BuyRow]:
    """Compute this month's buy plan. Returns list of BuyRow sorted by amount DESC."""
    target = settings_service.get_target_allocations(db)

    last_sync = db.query(func.max(Position.snapshot_date)).scalar()
    positions: list[Position] = []
    if last_sync:
        positions = db.query(Position).filter(Position.snapshot_date == last_sync).all()

    total_value = sum(p.market_value_usd or 0.0 for p in positions)
    current_values: dict[str, float] = {p.ticker: (p.market_value_usd or 0.0) for p in positions}

    current_pct: dict[str, float] = {
        t: (current_values.get(t, 0.0) / total_value * 100) if total_value > 0 else 0.0
        for t in target
    }

    deviations = {t: target[t] - current_pct[t] for t in target}
    underweight = {t: d for t, d in deviations.items() if d > 0}
    if not underweight:
        return []

    scores = {t: d * (1 + _oversold_score(db, t)) for t, d in underweight.items()}
    total_score = sum(scores.values())

    rows: list[BuyRow] = []
    for i, (ticker, score) in enumerate(sorted(scores.items(), key=lambda x: -x[1])):
        amount = round(budget_usd * score / total_score, 2)
        if amount < 1.0:
            continue
        week = 1 if i % 2 == 0 else 3
        rationale = _llm_rationale(ticker, target[ticker], current_pct[ticker])
        rows.append(BuyRow(
            ticker=ticker,
            amount_usd=amount,
            week_of_month=week,
            target_pct=target[ticker],
            current_pct=current_pct[ticker],
            deviation_pct=deviations[ticker],
            rationale=rationale,
        ))

    return rows


def upsert_recommendations(db: Session, month: str, rows: list[BuyRow]) -> None:
    if not rows:
        return
    values = [
        {
            "month": month,
            "ticker": r.ticker,
            "amount_usd": r.amount_usd,
            "week_of_month": r.week_of_month,
            "rationale": r.rationale,
            "executed": False,
        }
        for r in rows
    ]
    stmt = pg_insert(Recommendation).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["month", "ticker"],
        set_={
            "amount_usd": stmt.excluded.amount_usd,
            "week_of_month": stmt.excluded.week_of_month,
            "rationale": stmt.excluded.rationale,
        },
    )
    db.execute(stmt)


def get_month_recommendations(db: Session, month: str) -> list[Recommendation]:
    return (
        db.query(Recommendation)
        .filter(Recommendation.month == month)
        .order_by(Recommendation.amount_usd.desc())
        .all()
    )
