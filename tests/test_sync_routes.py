"""Integration tests for /sync/ibkr and /sync/freedom routes.

Tests that require a live PostgreSQL database are marked with @requires_db and
are automatically skipped when the test database is not reachable.
"""

import pytest
from itsdangerous import TimestampSigner

from app.config import get_settings
from app.models import Instrument, Position, Transaction
from tests.conftest import requires_db

pytestmark = requires_db

_FIXTURE_XML = "tests/fixtures/ibkr_flex_sample.xml"


@pytest.fixture
def authed_client(client):
    """TestClient with a valid auth cookie."""
    signer = TimestampSigner(get_settings().SECRET_KEY)
    token = signer.sign("authenticated").decode()
    client.cookies.set("auth_token", token)
    return client


# --- GET /sync/ibkr ---


def test_get_sync_ibkr_form_returns_200(authed_client):
    resp = authed_client.get("/sync/ibkr")
    assert resp.status_code == 200
    assert b"Upload" in resp.content or b"upload" in resp.content


def test_get_sync_ibkr_requires_auth(client):
    resp = client.get("/sync/ibkr", allow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("location", "")


# --- POST /sync/ibkr ---


def test_ibkr_upload_fixture_creates_positions(authed_client, db_session):
    with open(_FIXTURE_XML, "rb") as f:
        resp = authed_client.post(
            "/sync/ibkr",
            files={"file": ("test.xml", f, "application/xml")},
            allow_redirects=False,
        )
    assert resp.status_code == 302

    db_session.expire_all()
    positions = db_session.query(Position).all()
    assert len(positions) >= 2


def test_ibkr_upload_fixture_creates_transactions(authed_client, db_session):
    with open(_FIXTURE_XML, "rb") as f:
        authed_client.post(
            "/sync/ibkr",
            files={"file": ("test.xml", f, "application/xml")},
            allow_redirects=False,
        )

    db_session.expire_all()
    transactions = db_session.query(Transaction).all()
    assert len(transactions) >= 3


def test_ibkr_upload_creates_instrument_stubs(authed_client, db_session):
    with open(_FIXTURE_XML, "rb") as f:
        authed_client.post(
            "/sync/ibkr",
            files={"file": ("test.xml", f, "application/xml")},
            allow_redirects=False,
        )

    db_session.expire_all()
    tickers = {i.ticker for i in db_session.query(Instrument).all()}
    # Fixture has AAPL, MSFT in positions and TSLA, AAPL, MSFT in trades
    assert {"AAPL", "MSFT", "TSLA"}.issubset(tickers)


def test_ibkr_upload_idempotent(authed_client, db_session):
    """Uploading the same file twice must not create duplicate rows."""
    for _ in range(2):
        with open(_FIXTURE_XML, "rb") as f:
            authed_client.post(
                "/sync/ibkr",
                files={"file": ("test.xml", f, "application/xml")},
                allow_redirects=False,
            )

    db_session.expire_all()
    positions = db_session.query(Position).all()
    transactions = db_session.query(Transaction).all()
    # Counts must not double
    assert len(positions) == 2
    assert len(transactions) == 3


def test_ibkr_upload_wrong_type_redirects_with_error(authed_client):
    resp = authed_client.post(
        "/sync/ibkr",
        files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")},
        allow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/sync/ibkr" in resp.headers.get("location", "")


def test_ibkr_upload_invalid_xml_redirects_to_root(authed_client):
    bad_xml = b"<this is not valid xml <<<<"
    resp = authed_client.post(
        "/sync/ibkr",
        files={"file": ("bad.xml", bad_xml, "application/xml")},
        allow_redirects=False,
    )
    assert resp.status_code == 302


def test_ibkr_upload_empty_file_redirects_with_error(authed_client):
    resp = authed_client.post(
        "/sync/ibkr",
        files={"file": ("empty.xml", b"", "application/xml")},
        allow_redirects=False,
    )
    assert resp.status_code == 302


def test_ibkr_upload_requires_auth(client):
    with open(_FIXTURE_XML, "rb") as f:
        resp = client.post(
            "/sync/ibkr",
            files={"file": ("test.xml", f, "application/xml")},
            allow_redirects=False,
        )
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("location", "")


# --- POST /sync/freedom ---


def test_freedom_sync_with_no_keys_returns_error_flash(authed_client):
    """Freedom sync with missing API keys must redirect with error flash, not 500."""
    from unittest.mock import patch

    with patch("app.services.ingestion.freedom.get_settings") as mock_settings:
        mock_settings.return_value.FREEDOM_PUBLIC_KEY = ""
        mock_settings.return_value.FREEDOM_PRIVATE_KEY = ""
        resp = authed_client.post("/sync/freedom", allow_redirects=False)

    assert resp.status_code == 302
    # Must redirect to dashboard, not crash
    assert resp.headers.get("location") == "/"


def test_freedom_sync_requires_auth(client):
    resp = client.post("/sync/freedom", allow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("location", "")
