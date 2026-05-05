"""Tests for the dashboard route (/)."""

import datetime

import pytest
from itsdangerous import TimestampSigner

from app.config import get_settings
from app.models import Position
from tests.conftest import requires_db

pytestmark = requires_db


@pytest.fixture
def authed_client(client):
    signer = TimestampSigner(get_settings().SECRET_KEY)
    token = signer.sign("authenticated").decode()
    client.cookies.set("auth_token", token)
    return client


def test_dashboard_requires_auth(client):
    resp = client.get("/", allow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("location", "")


def test_dashboard_empty_state(authed_client, db_session):
    db_session.query(Position).delete()
    db_session.flush()
    resp = authed_client.get("/")
    assert resp.status_code == 200
    assert "No positions found" in resp.text


def test_dashboard_shows_positions(authed_client, db_session):
    db_session.query(Position).delete()
    db_session.flush()
    today = datetime.date.today()
    db_session.add(Position(
        snapshot_date=today,
        ticker="AAPL",
        quantity=10.0,
        avg_cost_usd=150.0,
        market_value_usd=1800.0,
        broker="ibkr",
    ))
    db_session.add(Position(
        snapshot_date=today,
        ticker="VWCE",
        quantity=5.0,
        avg_cost_usd=90.0,
        market_value_usd=500.0,
        broker="freedom",
    ))
    db_session.flush()

    resp = authed_client.get("/")
    assert resp.status_code == 200
    assert "2300.00" in resp.text
    assert "IBKR" in resp.text
    assert "FREEDOM" in resp.text


def test_dashboard_only_latest_snapshot(authed_client, db_session):
    db_session.query(Position).delete()
    db_session.flush()
    old_date = datetime.date(2025, 1, 1)
    today = datetime.date.today()
    db_session.add(Position(
        snapshot_date=old_date, ticker="AAPL", quantity=1.0,
        avg_cost_usd=100.0, market_value_usd=99999.0, broker="ibkr",
    ))
    db_session.add(Position(
        snapshot_date=today, ticker="AAPL", quantity=1.0,
        avg_cost_usd=100.0, market_value_usd=200.0, broker="ibkr",
    ))
    db_session.flush()

    resp = authed_client.get("/")
    assert "99999" not in resp.text
    assert "200.00" in resp.text
