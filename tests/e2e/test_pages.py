"""Happy path E2E tests for all pages."""

import pytest

from tests.e2e.conftest import requires_e2e

pytestmark = [requires_e2e, pytest.mark.e2e]


def test_dashboard_renders(auth_page, live_server):
    resp = auth_page.goto(f"{live_server}/")
    assert resp.status == 200
    content = auth_page.content()
    assert "500" not in auth_page.title()
    # Empty DB shows onboarding (T-011); populated DB shows portfolio panels
    assert any(kw in content for kw in ["Портфель", "Добро пожаловать", "Шаг 1", "Главная"])


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


# T-019: Regression tests for HTML5 step validation on settings form
def test_settings_goal_usd_step_attribute(auth_page, live_server):
    """step must be '1' so any integer is valid, not just multiples of 10000."""
    auth_page.goto(f"{live_server}/settings")
    step = auth_page.locator("input[name='goal_usd']").get_attribute("step")
    assert step == "1", f"goal_usd step must be '1', got {step!r}"


def test_settings_goal_usd_accepts_arbitrary_values(auth_page, live_server):
    """Arbitrary non-round values must pass HTML5 checkValidity (not blocked by browser)."""
    auth_page.goto(f"{live_server}/settings")
    inp = auth_page.locator("input[name='goal_usd']")
    for value in ["1000000", "850000", "1300000", "999999", "1"]:
        inp.fill(value)
        is_valid = inp.evaluate("el => el.checkValidity()")
        assert is_valid, f"goal_usd={value} should pass HTML5 validation but checkValidity() returned False"


def test_settings_form_submit_non_round_goal(auth_page, live_server):
    """Submitting goal_usd=1000000 must reach server and return success, not be blocked by browser."""
    auth_page.goto(f"{live_server}/settings")
    auth_page.fill("input[name='goal_usd']", "1000000")
    auth_page.fill("input[name='budget_usd']", "200")
    auth_page.fill("input[name='assumed_return_pct']", "8")
    auth_page.click("button[type=submit]")
    auth_page.wait_for_load_state("networkidle")
    content = auth_page.content()
    assert "Internal Server Error" not in content
    assert any(kw in content for kw in ["Сохранено", "success", "saved"]), \
        "Form did not return success confirmation after submit with goal_usd=1000000"


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
    assert "Анализ тикера" in content  # added in T-015


# ---------------------------------------------------------------------------
# T-013: /crisis page
# ---------------------------------------------------------------------------

def test_crisis_page_renders(auth_page, live_server):
    resp = auth_page.goto(f"{live_server}/crisis")
    assert resp.status == 200
    content = auth_page.content()
    assert "Internal Server Error" not in content
    assert any(kw in content.lower() for kw in ["рынок", "просадк", "кризис"])


# ---------------------------------------------------------------------------
# T-015: /analyze page
# ---------------------------------------------------------------------------

def test_analyze_page_renders(auth_page, live_server):
    resp = auth_page.goto(f"{live_server}/analyze")
    assert resp.status == 200
    assert "Internal Server Error" not in auth_page.content()
    assert auth_page.locator("input[name=ticker]").is_visible()


def test_analyze_invalid_ticker_shows_error(auth_page, live_server):
    """Non-existent ticker must show user-friendly error, not 500."""
    auth_page.goto(f"{live_server}/analyze")
    auth_page.fill("input[name=ticker]", "XYZXYZ123FAKE")
    auth_page.click("button[type=submit]")
    auth_page.wait_for_load_state("networkidle")
    content = auth_page.content()
    assert "Internal Server Error" not in content
    assert "500" not in auth_page.title()
    assert any(kw in content for kw in ["не найден", "Тикер", "не найдено"])


# ---------------------------------------------------------------------------
# T-012: /api/scenario endpoint
# ---------------------------------------------------------------------------

def test_scenario_api_returns_json(auth_page, live_server):
    """GET /api/scenario must return JSON with fv/delta/goal_pct fields."""
    auth_page.goto(f"{live_server}/")  # establish auth context
    result = auth_page.evaluate("""async () => {
        const r = await fetch('/api/scenario?budget=200&return_pct=8&years=20');
        return await r.json();
    }""")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "fv" in result
    assert "delta" in result
    assert "goal_pct" in result
    assert result["fv"] > 0


# ---------------------------------------------------------------------------
# T-014: Risk profile section in settings
# ---------------------------------------------------------------------------

def test_settings_has_risk_profile_section(auth_page, live_server):
    """Settings page must contain the 3 risk-profile select elements."""
    auth_page.goto(f"{live_server}/settings")
    assert auth_page.locator("select#rp-horizon").count() == 1
    assert auth_page.locator("select#rp-panic").count() == 1
    assert auth_page.locator("select#rp-income").count() == 1


# ---------------------------------------------------------------------------
# T-010: Tooltip CSS system
# ---------------------------------------------------------------------------

def test_tooltip_css_loaded_on_pages(auth_page, live_server):
    """CSS .term tooltip class must be present in base.html on all pages."""
    for path in ["/", "/recommend", "/settings", "/analyze"]:
        auth_page.goto(f"{live_server}{path}")
        content = auth_page.content()
        assert "cursor: help" in content, f"Tooltip CSS missing on {path}"


def test_tooltips_visible_on_settings(auth_page, live_server):
    """/settings always renders .term elements (alloc header, DCA, return rate)."""
    auth_page.goto(f"{live_server}/settings")
    assert auth_page.locator(".term").count() > 0


# ---------------------------------------------------------------------------
# T-017: /calculators
# ---------------------------------------------------------------------------

def test_calculators_unauthenticated_redirects(live_server):
    """GET /calculators without auth must redirect to /login."""
    import httpx
    r = httpx.get(f"{live_server}/calculators", follow_redirects=False, timeout=5)
    assert r.status_code in (302, 307)
    assert "login" in r.headers.get("location", "").lower()


def test_calculators_renders(auth_page, live_server):
    """GET /calculators must return 200 and render both calculators."""
    resp = auth_page.goto(f"{live_server}/calculators")
    assert resp.status == 200
    content = auth_page.content()
    assert "Калькулятор сложных процентов" in content
    assert "Калькулятор финансовой независимости" in content
    assert "Internal Server Error" not in content


def test_calculators_compound_fields_present(auth_page, live_server):
    """Compound interest form inputs must be present."""
    auth_page.goto(f"{live_server}/calculators")
    assert auth_page.locator("#ci-pv").count() == 1
    assert auth_page.locator("#ci-n").count() == 1
    assert auth_page.locator("#ci-r").count() == 1
    assert auth_page.locator("#ci-pmt").count() == 1


def test_calculators_fi_fields_present(auth_page, live_server):
    """Financial independence form inputs must be present."""
    auth_page.goto(f"{live_server}/calculators")
    assert auth_page.locator("#fi-monthly").count() == 1
    assert auth_page.locator("#fi-years").count() == 1
    assert auth_page.locator("#fi-withdrawal").count() == 1
    assert auth_page.locator("#fi-return").count() == 1


def test_calculators_nav_link_present(auth_page, live_server):
    """Nav must contain 'Калькуляторы' link pointing to /calculators."""
    auth_page.goto(f"{live_server}/")
    assert auth_page.locator("nav a[href='/calculators']").count() == 1
