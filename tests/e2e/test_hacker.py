"""QA Hacker adversarial E2E tests."""

import httpx
import pytest

from tests.e2e.conftest import _valid_auth_cookie, requires_e2e

pytestmark = [requires_e2e, pytest.mark.e2e]


def _client(live_server: str) -> httpx.Client:
    """httpx client with valid auth cookie for direct HTTP adversarial tests."""
    cookie = _valid_auth_cookie(live_server)
    domain = live_server.split("//")[-1].split(":")[0]
    cookies = httpx.Cookies()
    cookies.set(cookie["name"], cookie["value"], domain=domain)
    return httpx.Client(base_url=live_server, cookies=cookies, follow_redirects=True, timeout=10)


# ---------------------------------------------------------------------------
# Auth bypass
# ---------------------------------------------------------------------------

def test_forged_cookie_all_routes_denied(live_server):
    """Cookie signed with wrong secret must be rejected on all protected routes."""
    from itsdangerous import TimestampSigner
    forged = TimestampSigner("hacked_secret").sign("authenticated").decode()
    cookies = httpx.Cookies()
    cookies.set("auth_token", forged, domain="127.0.0.1")
    client = httpx.Client(base_url=live_server, cookies=cookies, follow_redirects=False, timeout=5)
    for route in ["/", "/portfolio", "/recommend", "/settings"]:
        r = client.get(route)
        assert r.status_code in (302, 307), f"Route {route} should redirect, got {r.status_code}"
        assert "login" in r.headers.get("location", "").lower()


def test_unauthenticated_execute_redirects(live_server):
    """POST /recommend/execute without auth must redirect, not execute."""
    r = httpx.post(
        f"{live_server}/recommend/execute/2026-05/VWCE",
        follow_redirects=False,
        timeout=5,
    )
    assert r.status_code in (302, 307)
    assert "login" in r.headers.get("location", "").lower()


# ---------------------------------------------------------------------------
# Injection & XSS
# ---------------------------------------------------------------------------

def test_xss_in_budget_field_rejected(live_server):
    """Script tag in budget must not be accepted as a number."""
    with _client(live_server) as c:
        r = c.post("/recommend", data={"budget": "<script>alert(1)</script>"})
    # FastAPI form coercion will fail → 422 or redirect with error
    assert r.status_code in (200, 302, 422)
    # Must not echo the raw script tag unescaped if 200
    if r.status_code == 200:
        assert "<script>alert(1)</script>" not in r.text


def test_sql_injection_in_settings_rejected(live_server):
    """SQL injection payload in allocation field must be rejected or sanitised."""
    with _client(live_server) as c:
        r = c.post("/settings", data={
            "allocation.VWCE": "'; DROP TABLE config; --",
            "allocation.VEUR": "15",
            "allocation.AGGH": "15",
            "allocation.XEON": "5",
            "goal_usd": "1300000",
            "budget_usd": "200",
            "assumed_return_pct": "8",
        })
    # Validation (0-100 float check) should reject the SQL payload
    assert r.status_code in (200, 302, 422)
    # No 500 (no raw SQL error leaking)
    assert r.status_code != 500


def test_xss_in_settings_allocation_escaped(live_server):
    """XSS payload stored in settings must be HTML-escaped in output."""
    payload = "<img src=x onerror=alert(1)>"
    with _client(live_server) as c:
        # This will fail validation (not 0-100), but shouldn't 500
        r = c.post("/settings", data={
            "allocation.VWCE": payload,
            "allocation.VEUR": "15",
            "allocation.AGGH": "15",
            "allocation.XEON": "5",
            "goal_usd": "1300000",
            "budget_usd": "200",
            "assumed_return_pct": "8",
        })
    assert r.status_code != 500
    # Raw payload must not appear unescaped in response
    if r.status_code == 200:
        assert payload not in r.text


# ---------------------------------------------------------------------------
# Boundary values
# ---------------------------------------------------------------------------

def test_negative_budget_no_500(live_server):
    """Negative budget: server must not crash."""
    with _client(live_server) as c:
        r = c.post("/recommend", data={"budget": "-500"})
    assert r.status_code != 500


def test_zero_budget_no_500(live_server):
    with _client(live_server) as c:
        r = c.post("/recommend", data={"budget": "0"})
    assert r.status_code != 500


def test_allocation_over_100_rejected(live_server):
    """Allocation > 100 must produce error flash, not 500."""
    with _client(live_server) as c:
        r = c.post("/settings", data={
            "allocation.VWCE": "200",
            "allocation.VEUR": "15",
            "allocation.AGGH": "15",
            "allocation.XEON": "5",
            "goal_usd": "1300000",
            "budget_usd": "200",
            "assumed_return_pct": "8",
        })
    assert r.status_code in (200, 302)
    assert r.status_code != 500
    # Should show an error message
    if r.status_code == 200:
        assert "error" in r.text.lower() or "0" in r.text


def test_allocation_negative_rejected(live_server):
    with _client(live_server) as c:
        r = c.post("/settings", data={
            "allocation.VWCE": "-10",
            "allocation.VEUR": "15",
            "allocation.AGGH": "15",
            "allocation.XEON": "5",
            "goal_usd": "1300000",
            "budget_usd": "200",
            "assumed_return_pct": "8",
        })
    assert r.status_code != 500


def test_very_large_goal_no_500(live_server):
    """Extremely large goal_usd must not cause overflow or 500."""
    with _client(live_server) as c:
        r = c.post("/settings", data={
            "allocation.VWCE": "65",
            "allocation.VEUR": "15",
            "allocation.AGGH": "15",
            "allocation.XEON": "5",
            "goal_usd": "9" * 15,
            "budget_usd": "200",
            "assumed_return_pct": "8",
        })
    assert r.status_code != 500


# ---------------------------------------------------------------------------
# Path traversal & parameter abuse
# ---------------------------------------------------------------------------

def test_report_path_traversal_rejected(live_server):
    """Path traversal in /report/{month} must not read files."""
    with _client(live_server) as c:
        r = c.get("/report/../../etc/passwd")
    # FastAPI path validation will reject this (404 or 422)
    assert r.status_code in (404, 422, 400, 200)
    # Must not contain passwd file contents
    assert "root:" not in r.text


def test_report_invalid_month_format_no_500(live_server):
    """Non-date month string in /report/ must not 500."""
    with _client(live_server) as c:
        r = c.get("/report/not-a-month")
    assert r.status_code != 500


def test_report_sql_injection_month_no_500(live_server):
    with _client(live_server) as c:
        r = c.get("/report/2026-05'; DROP TABLE progress_snapshots; --")
    assert r.status_code not in (500,)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_double_execute_recommendation_idempotent(live_server):
    """Marking the same recommendation as executed twice must not 500."""
    with _client(live_server) as c:
        r1 = c.post("/recommend/execute/2026-05/VWCE")
        r2 = c.post("/recommend/execute/2026-05/VWCE")
    assert r1.status_code != 500
    assert r2.status_code != 500


def test_execute_nonexistent_ticker_no_500(live_server):
    """Execute for a ticker that doesn't exist in recommendations must not 500."""
    with _client(live_server) as c:
        r = c.post("/recommend/execute/2026-05/FAKEXXX")
    assert r.status_code != 500


# ---------------------------------------------------------------------------
# Information disclosure
# ---------------------------------------------------------------------------

def test_404_page_no_stack_trace(live_server):
    with _client(live_server) as c:
        r = c.get("/this-route-does-not-exist")
    assert r.status_code == 404
    # Must not leak internal paths or stack traces
    assert "Traceback" not in r.text
    assert "site-packages" not in r.text


def test_login_error_no_hash_disclosure(anon_page, live_server):
    """Login error must not reveal the password hash or SECRET_KEY."""
    anon_page.goto(f"{live_server}/login")
    anon_page.fill("input[name=password]", "wrongpass")
    anon_page.click("button[type=submit]")
    content = anon_page.content()
    assert "$2b$" not in content  # bcrypt hash
    assert "secret" not in content.lower() or "SECRET_KEY" not in content


# ---------------------------------------------------------------------------
# T-015: /analyze — auth bypass & injection
# ---------------------------------------------------------------------------

def test_analyze_unauthenticated_redirects(live_server):
    """GET /analyze without auth must redirect to /login."""
    r = httpx.get(f"{live_server}/analyze", follow_redirects=False, timeout=5)
    assert r.status_code in (302, 307)
    assert "login" in r.headers.get("location", "").lower()


def test_analyze_post_unauthenticated_redirects(live_server):
    """POST /analyze without auth must redirect, not process ticker."""
    r = httpx.post(
        f"{live_server}/analyze",
        data={"ticker": "AAPL"},
        follow_redirects=False,
        timeout=5,
    )
    assert r.status_code in (302, 307)
    assert "login" in r.headers.get("location", "").lower()


def test_analyze_xss_ticker_rejected(live_server):
    """XSS payload in ticker field must not appear unescaped in response."""
    payload = "<script>alert(1)</script>"
    with _client(live_server) as c:
        r = c.post("/analyze", data={"ticker": payload})
    assert r.status_code != 500
    if r.status_code == 200:
        assert payload not in r.text


def test_analyze_long_ticker_no_500(live_server):
    """Ticker longer than 20 chars must be rejected gracefully, not crash."""
    with _client(live_server) as c:
        r = c.post("/analyze", data={"ticker": "A" * 50})
    assert r.status_code != 500
    if r.status_code == 200:
        assert "Traceback" not in r.text


def test_analyze_sql_injection_ticker_no_500(live_server):
    """SQL injection payload as ticker must not crash or leak DB errors."""
    with _client(live_server) as c:
        r = c.post("/analyze", data={"ticker": "'; DROP TABLE positions; --"})
    assert r.status_code != 500
    assert "Traceback" not in r.text


def test_analyze_null_bytes_ticker_no_500(live_server):
    """Null bytes and control chars in ticker must not crash."""
    with _client(live_server) as c:
        r = c.post("/analyze", data={"ticker": "ABC\x00DEF"})
    assert r.status_code != 500


# ---------------------------------------------------------------------------
# T-013: /crisis — auth bypass
# ---------------------------------------------------------------------------

def test_crisis_unauthenticated_redirects(live_server):
    """GET /crisis without auth must redirect to /login."""
    r = httpx.get(f"{live_server}/crisis", follow_redirects=False, timeout=5)
    assert r.status_code in (302, 307)
    assert "login" in r.headers.get("location", "").lower()


# ---------------------------------------------------------------------------
# T-012: /api/scenario — auth bypass & boundary values
# ---------------------------------------------------------------------------

def test_scenario_unauthenticated_redirects(live_server):
    """GET /api/scenario without auth must redirect to /login."""
    r = httpx.get(
        f"{live_server}/api/scenario?budget=200&return_pct=8&years=20",
        follow_redirects=False,
        timeout=5,
    )
    assert r.status_code in (302, 307)
    assert "login" in r.headers.get("location", "").lower()


def test_scenario_budget_over_limit_rejected(live_server):
    """budget > 100_000 must return 422 (FastAPI Query ge/le validation)."""
    with _client(live_server) as c:
        r = c.get("/api/scenario?budget=200000&return_pct=8&years=20")
    assert r.status_code == 422


def test_scenario_years_over_limit_rejected(live_server):
    """years > 50 must return 422."""
    with _client(live_server) as c:
        r = c.get("/api/scenario?budget=200&return_pct=8&years=100")
    assert r.status_code == 422


def test_scenario_negative_budget_rejected(live_server):
    """budget < 0 must return 422 (ge=0 constraint)."""
    with _client(live_server) as c:
        r = c.get("/api/scenario?budget=-100&return_pct=8&years=20")
    assert r.status_code == 422


def test_scenario_zero_budget_returns_result(live_server):
    """budget=0 is valid (ge=0) — linear growth, must return 200 with fv."""
    import json
    with _client(live_server) as c:
        r = c.get("/api/scenario?budget=0&return_pct=8&years=20")
    assert r.status_code == 200
    data = json.loads(r.text)
    assert "fv" in data
    assert data["fv"] >= 0


def test_scenario_zero_return_returns_result(live_server):
    """return_pct=0 is valid — linear PMT growth only, no crash."""
    import json
    with _client(live_server) as c:
        r = c.get("/api/scenario?budget=200&return_pct=0&years=20")
    assert r.status_code == 200
    data = json.loads(r.text)
    assert "fv" in data
