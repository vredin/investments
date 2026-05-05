"""Tests for GET /portfolio."""

import datetime

import pytest
from itsdangerous import TimestampSigner

from app.config import get_settings
from app.models import Position, Transaction
from tests.conftest import requires_db

pytestmark = requires_db


@pytest.fixture
def authed_client(client):
    signer = TimestampSigner(get_settings().SECRET_KEY)
    token = signer.sign("authenticated").decode()
    client.cookies.set("auth_token", token)
    return client


def test_portfolio_requires_auth(client):
    resp = client.get("/portfolio", allow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("location", "")


def test_portfolio_empty_state(authed_client, db_session):
    db_session.query(Position).delete()
    db_session.query(Transaction).delete()
    db_session.flush()
    resp = authed_client.get("/portfolio")
    assert resp.status_code == 200
    assert "No positions" in resp.text
    assert "No transactions" in resp.text


def test_portfolio_shows_positions(authed_client, db_session):
    db_session.query(Position).delete()
    db_session.flush()
    today = datetime.date.today()
    db_session.add(Position(
        snapshot_date=today, ticker="VWCE", quantity=12.5,
        avg_cost_usd=95.0, market_value_usd=1250.0, broker="ibkr",
    ))
    db_session.flush()

    resp = authed_client.get("/portfolio")
    assert resp.status_code == 200
    assert "VWCE" in resp.text
    assert "1250.00" in resp.text
    assert "ibkr" in resp.text.lower()


def test_portfolio_shows_transactions(authed_client, db_session):
    db_session.query(Transaction).delete()
    db_session.flush()
    db_session.add(Transaction(
        trade_date=datetime.date(2025, 4, 23),
        ticker="AAPL",
        type="BUY",
        quantity=7.0,
        price_usd=13.84,
        amount_usd=96.88,
        fee_usd=1.85,
        broker="freedom",
        ibkr_txn_id="freedom_test_001",
    ))
    db_session.flush()

    resp = authed_client.get("/portfolio")
    assert resp.status_code == 200
    assert "AAPL" in resp.text
    assert "BUY" in resp.text
    assert "freedom" in resp.text.lower()


def test_portfolio_only_latest_snapshot(authed_client, db_session):
    db_session.query(Position).delete()
    db_session.flush()
    old_date = datetime.date(2024, 1, 1)
    today = datetime.date.today()
    db_session.add(Position(
        snapshot_date=old_date, ticker="OLD", quantity=1.0,
        avg_cost_usd=1.0, market_value_usd=99999.0, broker="ibkr",
    ))
    db_session.add(Position(
        snapshot_date=today, ticker="NEW", quantity=1.0,
        avg_cost_usd=1.0, market_value_usd=100.0, broker="ibkr",
    ))
    db_session.flush()

    resp = authed_client.get("/portfolio")
    assert "NEW" in resp.text
    assert "OLD" not in resp.text
