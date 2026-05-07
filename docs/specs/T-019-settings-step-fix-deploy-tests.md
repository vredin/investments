# T-019: Деплой step-фикса + Playwright-тесты HTML5 валидации settings

**Created**: 2026-05-07
**Risk**: Low
**Status**: Backlog

## 1. Overview

Баг: `<input name="goal_usd" step="10000">` блокировал сохранение любого значения, не кратного 10000
(например 1000000, 1300000). Фикс (`step="1"`) закоммичен локально (коммит 31445d0), но НЕ задеплоен
на VPS — сервер работает со старым шаблоном. Дополнительно: существующий тест `test_settings_save_valid`
использует Playwright `fill()` + `click()`, что обходит browser HTML5 validation и не ловит такие баги.
Задача — задеплоить фикс и написать тест, который явно проверяет атрибут `step` и `checkValidity()`.

## 2. Objectives

- [ ] Задеплоить коммит 31445d0 на VPS (push + pull + restart)
- [ ] Написать Playwright-тест `test_settings_goal_usd_step_attribute`: проверяет что `step="1"` на `goal_usd`
- [ ] Написать Playwright-тест `test_settings_goal_usd_accepts_arbitrary_values`: 1000000, 850000, 1300000 — все `checkValidity() == True`
- [ ] Написать тест-регрессию `test_settings_form_submit_non_round_goal`: отправить 1000000, убедиться что ответ 200 и нет ошибки

## 3. Prerequisites

- Коммит 31445d0 — уже в локальном git ✅
- `tests/e2e/test_pages.py` — существующий E2E файл ✅
- VPS доступен по SSH alias из `docs/DEPLOY.md`

## 4. Scope

**In scope:**
- Push локальных коммитов на remote
- Деплой на VPS (git pull + restart)
- 3 новых Playwright-теста в `tests/e2e/test_pages.py`

**Out of scope:**
- Изменения в settings.html (уже исправлено)
- Тесты других страниц
- Тестирование `step` атрибутов на других формах (allocation, budget — у них step=1 и step=0.5, проблемы нет)

## 5. Technical Approach

### Деплой
```bash
git push origin main
ssh vps "cd /opt/Investments && git pull && docker compose restart app"
```

### Правильный способ тестировать HTML5 step-валидацию в Playwright

Playwright `fill()` + `click("button[type=submit]")` обходит browser validation.
Нужно использовать `element.checkValidity()` через `evaluate`:

```python
def test_settings_goal_usd_step_attribute(auth_page, live_server):
    auth_page.goto(f"{live_server}/settings")
    step = auth_page.locator("input[name='goal_usd']").get_attribute("step")
    assert step == "1", f"goal_usd step must be 1, got {step!r}"

def test_settings_goal_usd_accepts_arbitrary_values(auth_page, live_server):
    auth_page.goto(f"{live_server}/settings")
    inp = auth_page.locator("input[name='goal_usd']")
    for value in ["1000000", "850000", "1300000", "1"]:
        inp.fill(value)
        is_valid = inp.evaluate("el => el.checkValidity()")
        assert is_valid, f"goal_usd={value} should pass HTML5 validation"

def test_settings_form_submit_non_round_goal(auth_page, live_server):
    auth_page.goto(f"{live_server}/settings")
    auth_page.fill("input[name='goal_usd']", "1000000")
    auth_page.fill("input[name='budget_usd']", "200")
    auth_page.fill("input[name='assumed_return_pct']", "8")
    auth_page.click("button[type=submit]")
    auth_page.wait_for_load_state("networkidle")
    assert auth_page.locator("input[name='goal_usd']").get_attribute("value") == "1000000" \
        or "Сохранено" in auth_page.content() \
        or "success" in auth_page.content().lower()
```

## 6. Deliverables

| File | Purpose |
|------|---------|
| `tests/e2e/test_pages.py` | 3 новых теста для step-валидации |
| VPS: `/opt/Investments` | Обновлённый код после `git pull` |

## 7. Success Criteria

- **Functional:** На VPS /settings принимает 1000000 без ошибки браузера
- **Tests:**
  - `test_settings_goal_usd_step_attribute` — PASS (step=="1")
  - `test_settings_goal_usd_accepts_arbitrary_values` — PASS для 1000000, 850000, 1300000
  - `test_settings_form_submit_non_round_goal` — PASS (нет ошибки при submit)
  - Все существующие тесты по-прежнему зелёные

## 8. Implementation Notes & BQC Risks

| If task involves... | Risk | Mitigation |
|---------------------|------|------------|
| git push | Не заходит на remote | Проверить ssh-agent, remote URL |
| docker restart на VPS | Кратковременный downtime | Restart за <3s — приемлемо |
| `checkValidity()` | Разные браузеры — разное поведение | Playwright использует Chromium, этого достаточно |
| Playwright `evaluate` | Timeout если JS не выполнится | Добавить `timeout=5000` |

Security-reviewed: no threats identified. Только публичные атрибуты DOM и деплой собственного кода.

## 9. Testing Strategy

- **E2E:** 3 теста выше — полное покрытие step-валидации
- **Regression:** Запустить весь suite `pytest tests/e2e/ -q` после деплоя

## 10. Layer Impact Map

| Layer | Impact | Files |
|-------|--------|-------|
| Frontend | fixed (уже) | `app/templates/settings.html` |
| Tests | high | `tests/e2e/test_pages.py` |
| Deploy | medium | VPS `/opt/Investments` |

## 11. Red Flags

- `test_settings_form_submit_non_round_goal` проверяет ответ через content, а не через HTTP status — менее надёжно. Лучше использовать `response.status` или flash-message.
- Если VPS не обновлён, тест против live_server (localhost) пройдёт, но продакшн всё равно сломан.

## 12. Dependencies

- `docs/DEPLOY.md` — SSH alias и команды деплоя
- Playwright уже настроен (T-007)
