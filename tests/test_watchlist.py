"""Unit tests for watchlist service — no DB, no LLM, no yfinance."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# _compute_chart_data
# ---------------------------------------------------------------------------

def _make_hist(n: int) -> pd.DataFrame:
    """Return a minimal yfinance-like history DataFrame with n rows."""
    closes = [100.0 + i * 0.5 for i in range(n)]
    return pd.DataFrame({"Close": closes})


def test_compute_chart_data_full_year():
    from app.services.watchlist_service import _compute_chart_data

    hist = _make_hist(252)
    data = _compute_chart_data(hist)

    assert len(data["dates"]) == 252
    assert len(data["closes"]) == 252
    assert len(data["sma200"]) == 252
    assert len(data["rsi"]) == 252
    # RSI first 13 entries must be None (NaN→null conversion)
    assert data["rsi"][0] is None
    assert data["rsi"][12] is None
    # RSI after period must be non-None
    assert data["rsi"][14] is not None


def test_compute_chart_data_short_history():
    from app.services.watchlist_service import _compute_chart_data

    hist = _make_hist(10)
    data = _compute_chart_data(hist)

    assert len(data["dates"]) == 10
    assert len(data["rsi"]) == 10
    # All RSI values are None when history < 14 days
    assert all(v is None for v in data["rsi"])
    # SMA200 all None when < 200 bars
    assert all(v is None for v in data["sma200"])


def test_compute_chart_data_nan_to_null():
    """NaN values in SMA/RSI must be serialized as Python None (→ JSON null), not float('nan')."""
    from app.services.watchlist_service import _compute_chart_data

    hist = _make_hist(50)
    data = _compute_chart_data(hist)

    import math
    for val in data["rsi"] + data["sma200"]:
        if val is not None:
            assert not math.isnan(val), "NaN leaked — must be converted to None"


# ---------------------------------------------------------------------------
# add_ticker
# ---------------------------------------------------------------------------

def test_add_ticker_not_found():
    """get_ticker_data returns None → add_ticker returns None, no DB write."""
    from app.services.watchlist_service import add_ticker

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None  # not in watchlist
    db.query.return_value.count.return_value = 0

    with patch("app.services.watchlist_service.get_ticker_data", return_value=None):
        result = add_ticker("FAKE", db)

    assert result is None
    db.add.assert_not_called()


def test_add_ticker_duplicate_returns_existing():
    """Adding same ticker twice → returns existing WatchlistItem, no duplicate insert."""
    from app.models import WatchlistItem
    from app.services.watchlist_service import add_ticker

    existing = WatchlistItem(ticker="AAPL", added_at=datetime.utcnow())
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing

    result = add_ticker("AAPL", db)

    assert result is existing
    db.add.assert_not_called()


def test_add_ticker_normalizes_to_uppercase():
    """Lowercase input is normalized to uppercase before DB insert."""
    from app.services.watchlist_service import add_ticker

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.count.return_value = 0

    fake_data = {
        "ticker": "AAPL", "name": "Apple Inc.", "current_price": 180.0,
        "currency": "USD", "ytd_return_pct": 5.0,
        "drawdown_from_peak": -3.0, "volatility_pct": 20.0,
    }
    with patch("app.services.watchlist_service.get_ticker_data", return_value=fake_data), \
         patch("app.services.watchlist_service._compute_chart_data", return_value={"dates": [], "closes": [], "sma200": [], "rsi": []}), \
         patch("app.services.watchlist_service.yf.Ticker"):
        result = add_ticker("aapl", db)

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.ticker == "AAPL"


def test_add_ticker_limit_exceeded():
    """50+ tickers in watchlist → HTTPException 400."""
    from fastapi import HTTPException
    from app.services.watchlist_service import add_ticker

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.count.return_value = 50  # at limit

    with pytest.raises(HTTPException) as exc_info:
        add_ticker("MSFT", db)

    assert exc_info.value.status_code == 400
    assert "50" in str(exc_info.value.detail)


# ---------------------------------------------------------------------------
# remove_ticker
# ---------------------------------------------------------------------------

def test_remove_nonexistent_ticker_is_idempotent():
    """Removing a ticker not in watchlist → returns False, no error."""
    from app.services.watchlist_service import remove_ticker

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = remove_ticker("NONEXISTENT", db)

    assert result is False
    db.delete.assert_not_called()


# ---------------------------------------------------------------------------
# refresh_prices — error paths
# ---------------------------------------------------------------------------

def test_refresh_prices_partial_failure():
    """One ticker yfinance fails → sync_status='failed', price not wiped, others updated."""
    from app.models import WatchlistItem
    from app.services.watchlist_service import refresh_prices

    ticker_ok = WatchlistItem(ticker="VWCE", current_price=100.0)
    ticker_fail = WatchlistItem(ticker="FAKE", current_price=50.0)

    db = MagicMock()
    db.query.return_value.all.return_value = [ticker_ok, ticker_fail]

    good_data = {
        "ticker": "VWCE", "name": "VWCE ETF", "current_price": 105.0,
        "currency": "EUR", "ytd_return_pct": 5.0,
        "drawdown_from_peak": -2.0, "volatility_pct": 12.0,
    }

    def mock_get_data(ticker):
        if ticker == "VWCE":
            return good_data
        return None  # FAKE fails

    with patch("app.services.watchlist_service.get_ticker_data", side_effect=mock_get_data), \
         patch("app.services.watchlist_service._compute_chart_data", return_value={"dates": [], "closes": [], "sma200": [], "rsi": []}), \
         patch("app.services.watchlist_service.yf.Ticker"), \
         patch("app.services.watchlist_service.time.sleep"):
        count = refresh_prices(db)

    assert count == 1  # only VWCE succeeded
    assert ticker_ok.current_price == 105.0
    assert ticker_ok.sync_status == "ok"
    assert ticker_fail.current_price == 50.0  # unchanged
    assert ticker_fail.sync_status == "failed"


def test_refresh_prices_all_fail():
    """All tickers fail → count=0, all sync_status='failed'."""
    from app.models import WatchlistItem
    from app.services.watchlist_service import refresh_prices

    tickers = [WatchlistItem(ticker="FAKE1", current_price=10.0),
               WatchlistItem(ticker="FAKE2", current_price=20.0)]

    db = MagicMock()
    db.query.return_value.all.return_value = tickers

    with patch("app.services.watchlist_service.get_ticker_data", return_value=None), \
         patch("app.services.watchlist_service.time.sleep"):
        count = refresh_prices(db)

    assert count == 0
    assert all(t.sync_status == "failed" for t in tickers)


# ---------------------------------------------------------------------------
# refresh_llm — error path
# ---------------------------------------------------------------------------

def test_refresh_llm_openrouter_error_does_not_overwrite():
    """LLM call throws → refresh_llm returns '', existing analysis preserved."""
    from app.models import WatchlistItem
    from app.services.watchlist_service import refresh_llm

    item = WatchlistItem(ticker="VWCE", llm_analysis="старый анализ")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = item

    with patch("app.services.watchlist_service._client", side_effect=Exception("OpenRouter down")):
        result = refresh_llm("VWCE", db)

    assert result == ""
    assert item.llm_analysis == "старый анализ"  # not overwritten
    db.commit.assert_not_called()
