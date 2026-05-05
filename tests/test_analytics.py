"""Unit tests for analytics service."""

from unittest.mock import MagicMock, patch

from app.services.analytics import fv_projection, rebalancing_signals


def test_fv_projection_known_values():
    # PV=0, PMT=200/mo, r=8%/yr, n=240mo → ~$117k (FV annuity formula)
    result = fv_projection(0.0, 200.0, 8.0, 240)
    assert 100_000 < result < 135_000


def test_fv_projection_zero_rate():
    result = fv_projection(1000.0, 100.0, 0.0, 12)
    assert abs(result - 2200.0) < 0.01


def test_fv_projection_zero_months():
    result = fv_projection(5000.0, 100.0, 8.0, 0)
    assert result == 5000.0


def test_rebalancing_signals_triggered():
    current = {"VWCE": 50.0, "VEUR": 30.0}
    target = {"VWCE": 65.0, "VEUR": 15.0}
    signals = rebalancing_signals(current, target)
    assert "VWCE" in signals
    assert "VEUR" in signals


def test_rebalancing_signals_not_triggered():
    current = {"VWCE": 62.0, "VEUR": 13.0}
    target = {"VWCE": 65.0, "VEUR": 15.0}
    signals = rebalancing_signals(current, target)
    assert signals == []


def test_rebalancing_signals_threshold():
    current = {"VWCE": 60.0}
    target = {"VWCE": 65.0}
    # gap=5, not > 5 → no signal
    assert rebalancing_signals(current, target) == []
    # gap=5.1 → signal
    assert rebalancing_signals({"VWCE": 59.9}, target) == ["VWCE"]


def test_compute_dashboard_data_empty_db():
    from app.services.analytics import compute_dashboard_data

    db = MagicMock()
    db.query.return_value.scalar.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.scalar.return_value = None
    db.query.return_value.all.return_value = []

    with patch("app.services.analytics.settings_service.get_target_allocations",
               return_value={"VWCE": 65.0, "VEUR": 15.0, "AGGH": 15.0, "XEON": 5.0}), \
         patch("app.services.analytics.settings_service.get_float", return_value=200.0):
        data = compute_dashboard_data(db)

    assert data["total_capital"] == 0.0
    assert data["progress_pct"] == 0.0
    assert data["rebalance_signals"] == []
