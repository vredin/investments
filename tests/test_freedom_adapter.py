"""Unit tests for Freedom Finance adapter normalization and sync functions."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.ingestion.broker import BrokerSyncError, PositionRow, TransactionRow
from app.services.ingestion.freedom import (
    _normalize_freedom_position,
    _normalize_freedom_transaction,
    sync_freedom_positions,
    sync_freedom_transactions,
)

# --- _normalize_freedom_position ---


def test_normalize_position_returns_position_row():
    item = {"i": "AAPL", "q": 10, "s": 1839.2, "open_bal": 1500.0, "curr": "USD"}
    result = _normalize_freedom_position(item)
    assert isinstance(result, PositionRow)


def test_normalize_position_ticker():
    item = {"i": "TSLA", "q": 5, "s": 1000.0, "open_bal": 900.0, "curr": "USD"}
    result = _normalize_freedom_position(item)
    assert result.ticker == "TSLA"


def test_normalize_position_qty():
    item = {"i": "MSFT", "q": 7, "s": 2625.0, "open_bal": 2240.0, "curr": "USD"}
    result = _normalize_freedom_position(item)
    assert result.qty == 7.0


def test_normalize_position_market_value():
    item = {"i": "AAPL", "q": 10, "s": 1839.2, "open_bal": 1500.0, "curr": "USD"}
    result = _normalize_freedom_position(item)
    assert result.market_value == 1839.2


def test_normalize_position_cost_basis():
    item = {"i": "AAPL", "q": 10, "s": 1839.2, "open_bal": 1500.0, "curr": "USD"}
    result = _normalize_freedom_position(item)
    assert result.cost_basis == 1500.0


def test_normalize_position_broker_is_freedom():
    item = {"i": "AAPL", "q": 10, "s": 1000.0, "open_bal": 900.0, "curr": "USD"}
    result = _normalize_freedom_position(item)
    assert result.broker == "freedom"


def test_normalize_position_missing_ticker_returns_none():
    item = {"q": 10, "s": 1000.0}
    result = _normalize_freedom_position(item)
    assert result is None


def test_normalize_position_defaults_currency_to_usd():
    item = {"i": "AAPL", "q": 5, "s": 900.0, "open_bal": 800.0}
    result = _normalize_freedom_position(item)
    assert result.currency == "USD"


# --- _normalize_freedom_transaction ---


def test_normalize_transaction_returns_transaction_row():
    item = {"id": 12345, "instr": "AAPL", "date": 1704844800, "oper": 1, "q": 10, "p": 183.92, "curr": "USD"}
    result = _normalize_freedom_transaction(item)
    assert isinstance(result, TransactionRow)


def test_normalize_transaction_ticker():
    item = {"id": 1, "instr": "TSLA", "date": 1704844800, "oper": 1, "q": 5, "p": 230.5, "curr": "USD"}
    result = _normalize_freedom_transaction(item)
    assert result.ticker == "TSLA"


def test_normalize_transaction_buy_type():
    item = {"id": 1, "instr": "AAPL", "date": 1704844800, "oper": 1, "q": 10, "p": 150.0, "curr": "USD"}
    result = _normalize_freedom_transaction(item)
    assert result.txn_type == "BUY"


def test_normalize_transaction_sell_type():
    item = {"id": 2, "instr": "AAPL", "date": 1704844800, "oper": 3, "q": 5, "p": 183.0, "curr": "USD"}
    result = _normalize_freedom_transaction(item)
    assert result.txn_type == "SELL"


def test_normalize_transaction_ibkr_txn_id_uses_order_id():
    item = {"id": 99999, "instr": "AAPL", "date": 1704844800, "oper": 1, "q": 10, "p": 150.0, "curr": "USD"}
    result = _normalize_freedom_transaction(item)
    assert result.ibkr_txn_id == "freedom_99999"


def test_normalize_transaction_missing_ticker_returns_none():
    item = {"id": 1, "date": 1704844800, "oper": 1, "q": 10, "p": 150.0}
    result = _normalize_freedom_transaction(item)
    assert result is None


def test_normalize_transaction_qty_is_positive():
    item = {"id": 1, "instr": "AAPL", "date": 1704844800, "oper": 3, "q": 5, "p": 183.0, "curr": "USD"}
    result = _normalize_freedom_transaction(item)
    assert result.qty > 0


def test_normalize_transaction_broker_is_freedom():
    item = {"id": 1, "instr": "AAPL", "date": 1704844800, "oper": 1, "q": 10, "p": 150.0, "curr": "USD"}
    result = _normalize_freedom_transaction(item)
    assert result.broker == "freedom"


# --- sync_freedom_positions (integration-style with mocked HTTP) ---


@patch("app.services.ingestion.freedom.requests.post")
@patch("app.services.ingestion.freedom.upsert_positions", return_value=2)
def test_sync_freedom_positions_calls_upsert(mock_upsert, mock_post, tmp_path):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "pos": [
            {"i": "AAPL", "q": 10, "s": 1839.2, "open_bal": 1500.0, "curr": "USD"},
            {"i": "MSFT", "q": 5, "s": 1875.0, "open_bal": 1600.0, "curr": "USD"},
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    with patch("app.services.ingestion.freedom.get_settings") as mock_settings:
        mock_settings.return_value.FREEDOM_PUBLIC_KEY = "pub"
        mock_settings.return_value.FREEDOM_PRIVATE_KEY = "priv"
        db = MagicMock()
        count = sync_freedom_positions(db)

    assert count == 2
    mock_upsert.assert_called_once()
    rows = mock_upsert.call_args[0][1]
    assert len(rows) == 2
    assert all(isinstance(r, PositionRow) for r in rows)


@patch("app.services.ingestion.freedom.requests.post")
@patch("app.services.ingestion.freedom.upsert_transactions", return_value=1)
def test_sync_freedom_transactions_calls_upsert(mock_upsert, mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "orders": [
            {"id": 1, "instr": "AAPL", "date": 1704844800, "oper": 1, "q": 10, "p": 150.0, "curr": "USD"},
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    with patch("app.services.ingestion.freedom.get_settings") as mock_settings:
        mock_settings.return_value.FREEDOM_PUBLIC_KEY = "pub"
        mock_settings.return_value.FREEDOM_PRIVATE_KEY = "priv"
        db = MagicMock()
        count = sync_freedom_transactions(db)

    assert count == 1
    mock_upsert.assert_called_once()
    rows = mock_upsert.call_args[0][1]
    assert len(rows) == 1
    assert all(isinstance(r, TransactionRow) for r in rows)


@patch("app.services.ingestion.freedom.requests.post")
def test_sync_freedom_positions_raises_on_missing_keys(mock_post):
    with patch("app.services.ingestion.freedom.get_settings") as mock_settings:
        mock_settings.return_value.FREEDOM_PUBLIC_KEY = ""
        mock_settings.return_value.FREEDOM_PRIVATE_KEY = ""
        db = MagicMock()
        with pytest.raises(BrokerSyncError, match="keys not configured"):
            sync_freedom_positions(db)
