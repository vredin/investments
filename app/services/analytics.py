"""Analytics service — allocation snapshot, goal projection, rebalancing signals."""

import logging
from datetime import date

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import ExternalBalance, Position, Price, ProgressSnapshot
from app.services import settings_service

logger = logging.getLogger(__name__)

GOAL_USD = 1_300_000.0
GOAL_YEAR = 2046


def fv_projection(pv: float, pmt: float, r_annual: float, n_months: int) -> float:
    """Future value: FV = PV*(1+r)^n + PMT*(((1+r)^n - 1)/r)."""
    if r_annual <= 0 or n_months <= 0:
        return pv + pmt * n_months
    r = r_annual / 100 / 12
    growth = (1 + r) ** n_months
    return pv * growth + pmt * ((growth - 1) / r)


def _months_to_goal() -> int:
    today = date.today()
    target = date(GOAL_YEAR, 1, 1)
    return max(1, (target.year - today.year) * 12 + (target.month - today.month))


def rebalancing_signals(
    current_pct: dict[str, float],
    target_pct: dict[str, float],
    threshold: float = 5.0,
) -> list[str]:
    """Return tickers where abs(target - current) > threshold pp."""
    return [
        t
        for t in target_pct
        if abs(target_pct[t] - current_pct.get(t, 0.0)) > threshold
    ]


def _latest_price(db: Session, ticker: str) -> float | None:
    row = (
        db.query(Price.close)
        .filter(Price.ticker == ticker, Price.close.isnot(None))
        .order_by(Price.date.desc())
        .limit(1)
        .scalar()
    )
    return float(row) if row is not None else None


def compute_dashboard_data(db: Session) -> dict:
    """Return all data needed by dashboard template."""
    target_pct = settings_service.get_target_allocations(db)
    budget_usd = settings_service.get_float(db, "budget_usd")
    assumed_return = settings_service.get_float(db, "assumed_return_pct")
    goal_usd = settings_service.get_float(db, "goal_usd") or GOAL_USD

    last_sync = db.query(func.max(Position.snapshot_date)).scalar()
    positions: list[Position] = []
    if last_sync:
        positions = db.query(Position).filter(Position.snapshot_date == last_sync).all()

    # Use market_value_usd from positions as fallback; try quantity*price if available
    current_values: dict[str, float] = {}
    for p in positions:
        price = _latest_price(db, p.ticker)
        if price is not None and p.quantity:
            current_values[p.ticker] = p.quantity * price
        else:
            current_values[p.ticker] = p.market_value_usd or 0.0

    broker_capital = sum(current_values.values())

    # External balances (staking etc.)
    last_ext_date = db.query(func.max(ExternalBalance.date)).scalar()
    ext_balances: list[ExternalBalance] = []
    if last_ext_date:
        ext_balances = (
            db.query(ExternalBalance)
            .filter(ExternalBalance.date == last_ext_date)
            .all()
        )
    staking_capital = sum(b.amount_usd or 0.0 for b in ext_balances)
    total_capital = broker_capital + staking_capital

    # Allocation percentages
    total_for_pct = broker_capital if broker_capital > 0 else 1.0
    target_tickers = set(target_pct.keys())
    current_pct: dict[str, float] = {}
    unmanaged = 0.0
    for ticker, val in current_values.items():
        if ticker in target_tickers:
            current_pct[ticker] = val / total_for_pct * 100
        else:
            unmanaged += val / total_for_pct * 100
    for t in target_tickers:
        if t not in current_pct:
            current_pct[t] = 0.0

    # Donut chart: labels/data for current allocation (target tickers + Unmanaged)
    donut_labels = list(target_tickers) + (["Unmanaged"] if unmanaged > 0.01 else [])
    donut_current = [current_pct.get(t, 0.0) for t in target_tickers] + (
        [unmanaged] if unmanaged > 0.01 else []
    )
    donut_target = [target_pct.get(t, 0.0) for t in target_tickers] + (
        [0.0] if unmanaged > 0.01 else []
    )

    signals = rebalancing_signals(current_pct, target_pct) if broker_capital > 0 else []

    n_months = _months_to_goal()
    projection = fv_projection(total_capital, budget_usd, assumed_return, n_months)
    progress_pct = min(100.0, total_capital / goal_usd * 100) if goal_usd > 0 else 0.0

    return {
        "total_capital": total_capital,
        "broker_capital": broker_capital,
        "staking_capital": staking_capital,
        "current_pct": current_pct,
        "target_pct": target_pct,
        "rebalance_signals": signals,
        "projection_2046_usd": projection,
        "progress_pct": progress_pct,
        "goal_usd": goal_usd,
        "donut_labels": donut_labels,
        "donut_current": donut_current,
        "donut_target": donut_target,
        "ext_balances": ext_balances,
        "last_sync": last_sync,
    }


def upsert_snapshot(db: Session, month: str, data: dict) -> ProgressSnapshot:
    """Upsert ProgressSnapshot for the given month."""
    total = data["total_capital"]
    goal = data["goal_usd"]
    stmt = pg_insert(ProgressSnapshot).values(
        month=month,
        total_capital_usd=total,
        broker_capital_usd=data["broker_capital"],
        staking_capital_usd=data["staking_capital"],
        ttm_return_pct=None,
        projected_capital_2046_usd=data["projection_2046_usd"],
        delta_to_goal_usd=goal - total,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["month"],
        set_={
            "total_capital_usd": stmt.excluded.total_capital_usd,
            "broker_capital_usd": stmt.excluded.broker_capital_usd,
            "staking_capital_usd": stmt.excluded.staking_capital_usd,
            "projected_capital_2046_usd": stmt.excluded.projected_capital_2046_usd,
            "delta_to_goal_usd": stmt.excluded.delta_to_goal_usd,
        },
    )
    db.execute(stmt)
    db.commit()
    return db.query(ProgressSnapshot).filter(ProgressSnapshot.month == month).first()


def llm_report_narrative(month: str, data: dict) -> str:
    """Generate LLM monthly narrative via OpenRouter. Falls back to empty string on error."""
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
        signals_str = ", ".join(data["rebalance_signals"]) or "none"
        prompt = (
            f"You are a personal finance advisor. Write a concise 3-sentence portfolio "
            f"summary for {month}. "
            f"Total capital: ${data['total_capital']:,.0f}. "
            f"Broker: ${data['broker_capital']:,.0f}, Staking: ${data['staking_capital']:,.0f}. "
            f"Goal $1.3M projected: ${data['projection_2046_usd']:,.0f}. "
            f"Rebalancing needed: {signals_str}. "
            f"Be encouraging but realistic. Max 60 words."
        )
        resp = client.chat.completions.create(
            model="anthropic/claude-sonnet-4-5",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("LLM report narrative failed for %s: %s", month, exc)
        return ""
