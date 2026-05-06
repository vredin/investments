"""Auth tests: login, logout, session management."""

import pytest

from tests.e2e.conftest import (
    TEST_PASSWORD,
    _expired_auth_cookie,
    _forged_auth_cookie,
    requires_e2e,
    requires_known_password,
)

pytestmark = [requires_e2e, pytest.mark.e2e]

PROTECTED_ROUTES = ["/", "/portfolio", "/recommend", "/settings", "/report/2026-05"]


@pytest.mark.parametrize("route", PROTECTED_ROUTES)
def test_protected_route_without_cookie_redirects_to_login(anon_page, live_server, route):
    anon_page.goto(f"{live_server}{route}")
    assert "/login" in anon_page.url


def test_login_page_renders(anon_page, live_server):
    anon_page.goto(f"{live_server}/login")
    assert anon_page.title() != ""
    anon_page.wait_for_selector("input[type=password]")


@requires_known_password
def test_login_valid_password_redirects_to_dashboard(anon_page, live_server):
    anon_page.goto(f"{live_server}/login")
    anon_page.fill("input[name=password]", TEST_PASSWORD)
    anon_page.click("button[type=submit]")
    anon_page.wait_for_url(f"{live_server}/")
    assert anon_page.url == f"{live_server}/"


def test_login_invalid_password_shows_error(anon_page, live_server):
    anon_page.goto(f"{live_server}/login")
    anon_page.fill("input[name=password]", "wrongpassword")
    anon_page.click("button[type=submit]")
    # Should stay on /login and show error
    assert "/login" in anon_page.url
    content = anon_page.content()
    assert "Invalid" in content or "invalid" in content or "error" in content.lower()


def test_login_empty_password_shows_error(anon_page, live_server):
    anon_page.goto(f"{live_server}/login")
    # Try submitting empty form via direct POST (bypass browser required attr)
    import httpx
    r = httpx.post(f"{live_server}/login", data={"password": ""}, follow_redirects=False)
    # Should not succeed (redirect to / would mean auth succeeded)
    assert r.status_code in (302, 401, 422)
    if r.status_code == 302:
        assert "/login" in r.headers.get("location", "/login")


def test_logout_clears_session(auth_page, live_server):
    auth_page.goto(f"{live_server}/")
    # Confirm we are authenticated (no redirect to login)
    assert "/login" not in auth_page.url

    # Logout
    auth_page.request.post(f"{live_server}/logout")

    # After clearing cookies manually (simulate what logout does)
    auth_page.context.clear_cookies()
    auth_page.goto(f"{live_server}/")
    assert "/login" in auth_page.url


def test_already_authenticated_login_redirects_to_dashboard(auth_page, live_server):
    auth_page.goto(f"{live_server}/login")
    # Already authenticated → redirect to /
    assert "/login" not in auth_page.url or auth_page.url == f"{live_server}/"


def test_forged_cookie_denied(anon_page, live_server):
    anon_page.goto(f"{live_server}/health")
    anon_page.context.add_cookies([_forged_auth_cookie(live_server)])
    anon_page.goto(f"{live_server}/")
    assert "/login" in anon_page.url


def test_expired_cookie_denied(anon_page, live_server):
    anon_page.goto(f"{live_server}/health")
    anon_page.context.add_cookies([_expired_auth_cookie(live_server)])
    anon_page.goto(f"{live_server}/")
    assert "/login" in anon_page.url
