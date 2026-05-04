"""Unit tests for IBKR Flex XML parser."""

import pytest

from app.services.ingestion.broker import BrokerSyncError, PositionRow, TransactionRow
from app.services.ingestion.ibkr import parse_flex_xml

_FIXTURE_PATH = "tests/fixtures/ibkr_flex_sample.xml"


@pytest.fixture(scope="module")
def fixture_xml() -> bytes:
    with open(_FIXTURE_PATH, "rb") as f:
        return f.read()


def test_parse_returns_correct_position_count(fixture_xml):
    positions, _ = parse_flex_xml(fixture_xml)
    assert len(positions) == 2


def test_parse_returns_correct_transaction_count(fixture_xml):
    _, transactions = parse_flex_xml(fixture_xml)
    assert len(transactions) == 3


def test_position_types_are_position_rows(fixture_xml):
    positions, _ = parse_flex_xml(fixture_xml)
    for pos in positions:
        assert isinstance(pos, PositionRow)


def test_transaction_types_are_transaction_rows(fixture_xml):
    _, txns = parse_flex_xml(fixture_xml)
    for txn in txns:
        assert isinstance(txn, TransactionRow)


def test_position_tickers_not_empty(fixture_xml):
    positions, _ = parse_flex_xml(fixture_xml)
    for pos in positions:
        assert pos.ticker, "ticker must not be empty"


def test_position_qty_is_numeric(fixture_xml):
    positions, _ = parse_flex_xml(fixture_xml)
    for pos in positions:
        assert isinstance(pos.qty, float)
        assert pos.qty > 0


def test_position_market_value_is_numeric(fixture_xml):
    positions, _ = parse_flex_xml(fixture_xml)
    for pos in positions:
        assert isinstance(pos.market_value, float)


def test_position_broker_is_ibkr(fixture_xml):
    positions, _ = parse_flex_xml(fixture_xml)
    for pos in positions:
        assert pos.broker == "ibkr"


def test_aapl_position_values(fixture_xml):
    positions, _ = parse_flex_xml(fixture_xml)
    aapl = next((p for p in positions if p.ticker == "AAPL"), None)
    assert aapl is not None
    assert aapl.qty == 10.0
    assert aapl.cost_basis == 1500.0
    assert aapl.market_value == 1839.20


def test_transaction_tickers_not_empty(fixture_xml):
    _, txns = parse_flex_xml(fixture_xml)
    for txn in txns:
        assert txn.ticker, "ticker must not be empty"


def test_transaction_dates_are_date_objects(fixture_xml):
    from datetime import date

    _, txns = parse_flex_xml(fixture_xml)
    for txn in txns:
        assert isinstance(txn.trade_date, date)


def test_transaction_ibkr_txn_id_not_empty(fixture_xml):
    _, txns = parse_flex_xml(fixture_xml)
    for txn in txns:
        assert txn.ibkr_txn_id, "ibkr_txn_id must not be empty"


def test_transaction_txn_ids_unique(fixture_xml):
    _, txns = parse_flex_xml(fixture_xml)
    ids = [t.ibkr_txn_id for t in txns]
    assert len(ids) == len(set(ids)), "ibkr_txn_id values must be unique"


def test_transaction_qty_positive(fixture_xml):
    _, txns = parse_flex_xml(fixture_xml)
    for txn in txns:
        assert txn.qty > 0


def test_transaction_type_valid(fixture_xml):
    _, txns = parse_flex_xml(fixture_xml)
    for txn in txns:
        assert txn.txn_type in ("BUY", "SELL", "DIV")


def test_transaction_broker_is_ibkr(fixture_xml):
    _, txns = parse_flex_xml(fixture_xml)
    for txn in txns:
        assert txn.broker == "ibkr"


def test_parse_invalid_xml_raises_broker_sync_error():
    with pytest.raises(BrokerSyncError, match="Invalid XML"):
        parse_flex_xml(b"this is not xml <unclosed")


def test_parse_empty_xml_returns_empty_lists():
    xml = b'<?xml version="1.0"?><FlexQueryResponse><FlexStatements /></FlexQueryResponse>'
    positions, transactions = parse_flex_xml(xml)
    assert positions == []
    assert transactions == []


def test_parse_trade_without_trade_id_is_skipped():
    xml = (
        b'<?xml version="1.0"?>'
        b"<FlexQueryResponse><FlexStatements>"
        b'<FlexStatement><Trades>'
        b'<Trade symbol="AAPL" quantity="10" tradePrice="150" tradeMoney="1500" ibCommission="-1" buySell="BUY" tradeDate="2024-01-01" currency="USD"/>'
        b"</Trades></FlexStatement></FlexStatements></FlexQueryResponse>"
    )
    _, txns = parse_flex_xml(xml)
    assert txns == []
