"""E2E test fixtures: live server subprocess OR remote server via E2E_BASE_URL."""

import os
import subprocess
import sys
import time
from pathlib import Path

import bcrypt
import httpx
import pytest
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine, text

_PORT = 18765
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# If E2E_BASE_URL is set — use that server directly (no subprocess).
# Example: E2E_BASE_URL=http://localhost:8000 pytest tests/e2e/ -m e2e
_REMOTE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")

# Secret key — must match the server's SECRET_KEY env var.
# When using E2E_BASE_URL, set E2E_SECRET_KEY to match the running server.
_TEST_SECRET = os.environ.get(
    "E2E_SECRET_KEY",
    os.environ.get("SECRET_KEY", "test_secret_key_32_bytes_minimum_padding_here_"),
)

# Password used for UI login tests (subprocess mode only).
TEST_PASSWORD = "testpass123"
_TEST_HASH = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()

_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "").replace("/investments", "/investments_test"),
)


def _server_available(url: str) -> bool:
    try:
        r = httpx.get(f"{url}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _db_available() -> bool:
    if not _TEST_DB_URL:
        return False
    try:
        eng = create_engine(_TEST_DB_URL, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _e2e_available() -> bool:
    """E2E tests available if: remote URL set and reachable, OR local DB available."""
    if _REMOTE_URL:
        return _server_available(_REMOTE_URL)
    return _db_available()


requires_e2e = pytest.mark.skipif(
    not _e2e_available(),
    reason=(
        "E2E tests require either E2E_BASE_URL (remote server) "
        "or local PostgreSQL test DB. "
        "Set E2E_BASE_URL=http://localhost:8000 to run against live server."
    ),
)


def _ensure_db_schema():
    from app.db import Base  # noqa: PLC0415
    eng = create_engine(_TEST_DB_URL, pool_pre_ping=True)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(eng)
    eng.dispose()


@pytest.fixture(scope="session")
def live_server():
    """Start local test server OR return remote URL if E2E_BASE_URL is set."""
    if _REMOTE_URL:
        if not _server_available(_REMOTE_URL):
            pytest.skip(f"Remote server {_REMOTE_URL} not reachable")
        yield _REMOTE_URL
        return

    if not _db_available():
        pytest.skip("PostgreSQL test DB not available")

    _ensure_db_schema()

    base = f"http://127.0.0.1:{_PORT}"
    env = {
        **os.environ,
        "DATABASE_URL": _TEST_DB_URL,
        "SECRET_KEY": _TEST_SECRET,
        "ADMIN_PASSWORD_HASH": _TEST_HASH,
        "OPENROUTER_API_KEY": "",
        "SESSION_MAX_AGE": "3600",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(_PORT)],
        env=env,
        cwd=str(_PROJECT_ROOT),
    )
    for _ in range(30):
        try:
            r = httpx.get(f"{base}/health", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("Test server did not start in 15s")

    yield base

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def base_url(live_server):
    return live_server


def _valid_auth_cookie(server_url: str) -> dict:
    domain = server_url.split("//")[-1].split(":")[0]
    token = TimestampSigner(_TEST_SECRET).sign("authenticated").decode()
    return {"name": "auth_token", "value": token, "domain": domain, "path": "/"}


def _forged_auth_cookie(server_url: str) -> dict:
    domain = server_url.split("//")[-1].split(":")[0]
    token = TimestampSigner("totally_wrong_secret_key_here_!!!").sign("authenticated").decode()
    return {"name": "auth_token", "value": token, "domain": domain, "path": "/"}


def _expired_auth_cookie(server_url: str) -> dict:
    import time as _time
    domain = server_url.split("//")[-1].split(":")[0]
    signer = TimestampSigner(_TEST_SECRET)
    real = _time.time
    _time.time = lambda: real() - 90000
    try:
        token = signer.sign("authenticated").decode()
    finally:
        _time.time = real
    return {"name": "auth_token", "value": token, "domain": domain, "path": "/"}


@pytest.fixture
def auth_page(page, live_server):
    """Playwright page with valid auth cookie pre-set."""
    page.goto(f"{live_server}/health")
    page.context.add_cookies([_valid_auth_cookie(live_server)])
    return page


@pytest.fixture
def anon_page(page):
    return page
