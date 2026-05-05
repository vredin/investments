"""Unit tests for app/services/prices.py — ticker mapping and upsert logic.

Network calls are mocked. DB tests use @requires_db.
"""

from unittest.mock import MagicMock, patch

import pandas as pd

from app.services.prices import _TARGET_ETF_MAP, _to_yf_symbol, sync_prices

# ---------------------------------------------------------------------------
# Ticker mapping
# ---------------------------------------------------------------------------

def test_target_etf_mapped_to_yf_symbol():
    assert _to_yf_symbol("VWCE") == "VWCE.AS"
    assert _to_yf_symbol("VEUR") == "VEUR.AS"
    assert _to_yf_symbol("AGGH") == "AGGH.L"
    assert _to_yf_symbol("XEON") == "XEON.DE"


def test_freedom_us_suffix_stripped():
    assert _to_yf_symbol("AAPL.US") == "AAPL"
    assert _to_yf_symbol("TSLA.US") == "TSLA"


def test_plain_ticker_unchanged():
    assert _to_yf_symbol("AAPL") == "AAPL"
    assert _to_yf_symbol("MSFT") == "MSFT"


# ---------------------------------------------------------------------------
# sync_prices — mocked yfinance + DB
# ---------------------------------------------------------------------------

def _make_fake_hist(ticker: str, n: int = 5) -> pd.DataFrame:
    import datetime
    dates = pd.date_range(end=datetime.date.today(), periods=n, freq="B")
    return pd.DataFrame(
        {"Open": [100.0] * n, "High": [105.0] * n, "Low": [98.0] * n,
         "Close": [102.0] * n, "Volume": [1_000_000] * n},
        index=dates,
    )


def _make_mock_db(tickers: list[str]):
    db = MagicMock()
    db.query.return_value.distinct.return_value.all.return_value = [
        (t,) for t in tickers
    ]
    db.execute.return_value = None
    return db


def test_sync_prices_calls_all_tickers():
    db = _make_mock_db(["AAPL.US"])
    expected_db_tickers = {"AAPL.US"} | set(_TARGET_ETF_MAP.keys())

    with patch("app.services.prices.yf.Ticker") as mock_ticker_cls:
        mock_ticker_cls.return_value.history.return_value = _make_fake_hist("AAPL")
        result = sync_prices(db)

    assert result["tickers"] == len(expected_db_tickers)
    assert result["rows"] > 0
    assert result["failed"] == []


def test_sync_prices_failed_ticker_does_not_abort():
    db = _make_mock_db(["AAPL.US"])

    def side_effect(yf_sym):
        mock = MagicMock()
        # Fail AAPL, succeed all others
        if yf_sym == "AAPL":
            mock.history.side_effect = Exception("network error")
        else:
            mock.history.return_value = _make_fake_hist(yf_sym)
        return mock

    with patch("app.services.prices.yf.Ticker", side_effect=side_effect):
        result = sync_prices(db)

    assert "AAPL.US" in result["failed"]
    assert result["rows"] > 0  # other tickers succeeded


def test_sync_prices_empty_hist_counted_as_failed():
    db = _make_mock_db([])  # no positions

    with patch("app.services.prices.yf.Ticker") as mock_ticker_cls:
        mock_ticker_cls.return_value.history.return_value = pd.DataFrame()
        result = sync_prices(db)

    # All target ETFs fail with empty hist
    assert len(result["failed"]) == len(_TARGET_ETF_MAP)
    assert result["rows"] == 0


def test_sync_prices_idempotent_no_error():
    db = _make_mock_db(["AAPL.US"])

    with patch("app.services.prices.yf.Ticker") as mock_ticker_cls:
        mock_ticker_cls.return_value.history.return_value = _make_fake_hist("AAPL")
        result1 = sync_prices(db)
        result2 = sync_prices(db)

    # Both calls succeed — idempotency is guaranteed by ON CONFLICT in the SQL
    assert result1["rows"] == result2["rows"]
