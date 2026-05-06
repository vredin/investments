"""Happy path E2E tests for all pages."""

import pytest

from tests.e2e.conftest import requires_e2e

pytestmark = [requires_e2e, pytest.mark.e2e]


def test_dashboard_renders(auth_page, live_server):
    resp = auth_page.goto(f"{live_server}/")
    assert resp.status == 200
    content = auth_page.content()
    assert "500" not in auth_page.title()
    assert any(kw in content for kw in ["Портфель", "Позиций не найдено", "Главная"])


def test_dashboard_no_500_on_empty_db(auth_page, live_server):
    auth_page.goto(f"{live_server}/")
    assert "Internal Server Error" not in auth_page.content()


def test_portfolio_renders(auth_page, live_server):
    resp = auth_page.goto(f"{live_server}/portfolio")
    assert resp.status == 200
    content = auth_page.content()
    assert "Позиции" in content
    assert "Internal Server Error" not in content


def test_recommend_page_renders(auth_page, live_server):
    resp = auth_page.goto(f"{live_server}/recommend")
    assert resp.status == 200
    content = auth_page.content()
    assert "Бюджет" in content or "budget" in content.lower()
    assert "Internal Server Error" not in content


def test_recommend_form_visible(auth_page, live_server):
    auth_page.goto(f"{live_server}/recommend")
    auth_page.wait_for_selector("input[name=budget]")
    budget_input = auth_page.locator("input[name=budget]")
    assert budget_input.is_visible()


def test_recommend_generate_empty_portfolio(auth_page, live_server):
    """With empty portfolio, plan should generate or return flash — no 500."""
    auth_page.goto(f"{live_server}/recommend")
    auth_page.fill("input[name=budget]", "200")
    auth_page.click("button[type=submit]")
    auth_page.wait_for_load_state("networkidle")
    assert "Internal Server Error" not in auth_page.content()


def test_settings_page_renders(auth_page, live_server):
    resp = auth_page.goto(f"{live_server}/settings")
    assert resp.status == 200
    content = auth_page.content()
    assert "VWCE" in content
    assert "VEUR" in content
    assert "Internal Server Error" not in content


def test_settings_shows_goal_field(auth_page, live_server):
    auth_page.goto(f"{live_server}/settings")
    assert auth_page.locator("input[name=goal_usd]").is_visible()
    assert auth_page.locator("input[name=budget_usd]").is_visible()
    assert auth_page.locator("input[name=assumed_return_pct]").is_visible()


def test_settings_save_valid(auth_page, live_server):
    auth_page.goto(f"{live_server}/settings")
    auth_page.fill("input[name='allocation.VWCE']", "65")
    auth_page.fill("input[name='allocation.VEUR']", "15")
    auth_page.fill("input[name='allocation.AGGH']", "15")
    auth_page.fill("input[name='allocation.XEON']", "5")
    auth_page.fill("input[name=goal_usd]", "1300000")
    auth_page.fill("input[name=budget_usd]", "200")
    auth_page.fill("input[name=assumed_return_pct]", "8")
    auth_page.click("button[type=submit]")
    auth_page.wait_for_load_state("networkidle")
    assert "Internal Server Error" not in auth_page.content()
    content = auth_page.content()
    assert "Сохранено" in content or "save" in content.lower() or "success" in content.lower()


def test_report_current_month_renders(auth_page, live_server):
    from datetime import date
    month = date.today().strftime("%Y-%m")
    resp = auth_page.goto(f"{live_server}/report/{month}")
    assert resp.status == 200
    content = auth_page.content()
    assert month in content
    assert "Internal Server Error" not in content


def test_health_endpoint_public(anon_page, live_server):
    """Health endpoint must be accessible without auth."""
    anon_page.goto(f"{live_server}/health")
    assert "ok" in anon_page.content()


def test_nav_links_visible(auth_page, live_server):
    auth_page.goto(f"{live_server}/")
    content = auth_page.content()
    assert "Главная" in content
    assert "Портфель" in content
    assert "Рекомендации" in content
    assert "Настройки" in content
