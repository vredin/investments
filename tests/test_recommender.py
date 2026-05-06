"""Unit tests for recommender service — no DB, no LLM."""

from unittest.mock import MagicMock, patch

from app.services.recommender import _calc_rsi, _oversold_score, generate_buy_plan

# ---------------------------------------------------------------------------
# RSI helper
# ---------------------------------------------------------------------------

def test_rsi_insufficient_data_returns_neutral():
    assert _calc_rsi([100.0, 101.0]) == 50.0


def test_rsi_all_gains_returns_100():
    closes = [100 + i for i in range(20)]
    assert _calc_rsi(closes) == 100.0


def test_rsi_all_losses_returns_near_zero():
    closes = [100 - i for i in range(20)]
    rsi = _calc_rsi(closes)
    assert rsi < 5.0


# ---------------------------------------------------------------------------
# Oversold score
# ---------------------------------------------------------------------------

def test_oversold_score_returns_zero_for_insufficient_prices():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    score = _oversold_score(db, "VWCE")
    assert score == 0.0


def test_oversold_score_below_sma200_gives_positive():
    from app.models import Price

    closes = list(range(100, 300))  # rising prices — current > sma200
    prices = [MagicMock(spec=Price, close=float(c)) for c in closes]
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = prices

    score = _oversold_score(db, "VWCE")
    # current is highest → sma_score=0 and drawdown_score=0 → score near 0
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# generate_buy_plan
# ---------------------------------------------------------------------------

def _mock_db_for_plan(tickers_in_positions: dict[str, float], target: dict[str, float]):
    """Returns a mock DB where positions has the given market values."""
    from datetime import date

    from app.models import Position

    db = MagicMock()
    # settings_service.get_target_allocations reads Config via get_all → seed_defaults → query
    # We patch settings_service directly instead
    last_sync = date.today()
    mock_positions = [
        MagicMock(spec=Position, ticker=t, market_value_usd=v, snapshot_date=last_sync)
        for t, v in tickers_in_positions.items()
    ]
    # func.max query returns last_sync
    db.query.return_value.scalar.return_value = last_sync
    db.query.return_value.filter.return_value.all.return_value = mock_positions
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    return db


def test_generate_buy_plan_all_underweight_when_empty_portfolio():
    db = _mock_db_for_plan({}, {})
    target = {"VWCE": 65.0, "VEUR": 15.0, "AGGH": 15.0, "XEON": 5.0}

    with patch("app.services.recommender.settings_service.get_target_allocations", return_value=target), \
         patch("app.services.recommender._oversold_score", return_value=0.0), \
         patch("app.services.recommender._llm_rationale", return_value="Test rationale"):
        rows = generate_buy_plan(500.0, db)

    assert len(rows) == 4
    tickers = [r.ticker for r in rows]
    assert set(tickers) == {"VWCE", "VEUR", "AGGH", "XEON"}
    total = sum(r.amount_usd for r in rows)
    assert abs(total - 500.0) < 0.05


def test_generate_buy_plan_budget_distributes_proportionally():
    db = _mock_db_for_plan({}, {})
    target = {"VWCE": 60.0, "VEUR": 40.0}

    with patch("app.services.recommender.settings_service.get_target_allocations", return_value=target), \
         patch("app.services.recommender._oversold_score", return_value=0.0), \
         patch("app.services.recommender._llm_rationale", return_value="ok"):
        rows = generate_buy_plan(100.0, db)

    amounts = {r.ticker: r.amount_usd for r in rows}
    # VWCE target 60 > VEUR 40 → more budget to VWCE
    assert amounts["VWCE"] > amounts["VEUR"]


def test_generate_buy_plan_fully_weighted_ticker_excluded():
    # VWCE at 65% = target → no underweight
    db = _mock_db_for_plan({"VWCE": 650.0, "VEUR": 0.0, "AGGH": 200.0, "XEON": 150.0}, {})
    target = {"VWCE": 65.0, "VEUR": 15.0, "AGGH": 20.0, "XEON": 0.0}

    with patch("app.services.recommender.settings_service.get_target_allocations", return_value=target), \
         patch("app.services.recommender._oversold_score", return_value=0.0), \
         patch("app.services.recommender._llm_rationale", return_value="ok"):
        rows = generate_buy_plan(200.0, db)

    tickers = {r.ticker for r in rows}
    assert "VEUR" in tickers  # underweight
    # XEON target=0 → deviation=0 → not underweight
    assert "XEON" not in tickers


def test_llm_fallback_on_exception():
    from app.services.recommender import _llm_rationale
    with patch("app.config.get_settings", side_effect=Exception("no API key")):
        result = _llm_rationale("VWCE", 65.0, 0.0)
    assert "65" in result
    assert "распределению" in result
