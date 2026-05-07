# T-018: BTD-сигнал на странице рекомендаций

**Created**: 2026-05-07
**Risk**: Low
**Status**: Backlog

## 1. Overview

Курс (часть 16) рекомендует комбинировать DCA с BTD (Buy the Dip): держать базовый DCA-взнос каждый месяц
плюс дополнительно покупать при значимых просадках рынка. Система уже генерирует DCA-план и имеет
`get_market_drawdown()`, но не использует этот сигнал для рекомендаций. Задача — добавить
BTD-баннер на страницу /recommend, который показывает просадку и рассчитывает
дополнительное распределение при срабатывании порога.

## 2. Objectives

- [ ] Добавить настройки `btd_threshold_pct` (дефолт: -10) и `btd_extra_budget_usd` (дефолт: 200) в settings_service
- [ ] Добавить BTD-баннер на /recommend: показывается только когда просадка VWCE ≤ threshold
- [ ] Баннер содержит: текущую просадку %, рекомендацию по допбюджету с разбивкой по тикерам (underweight-first)
- [ ] Настройки BTD редактируются на странице /settings
- [ ] Если просадки нет — баннер скрыт, страница работает как прежде

## 3. Prerequisites

- T-005 (buy recommender) — уже выполнен ✅
- T-013 (crisis guide с `get_market_drawdown()`) — уже выполнен ✅
- `app/services/recommender.py::generate_buy_plan()` — уже работает ✅

## 4. Scope

**In scope:**
- Новые ключи конфига: `btd_threshold_pct`, `btd_extra_budget_usd`
- Функция `get_btd_signal(db)` в `recommender.py` — возвращает данные для баннера или None
- BTD-баннер в `recommend.html` (показывается только при активном сигнале)
- Два новых поля в `settings.html` (threshold и extra budget)

**Out of scope:**
- Сохранение BTD-рекомендаций в БД отдельно от обычных
- История BTD-событий
- Push/email уведомления при просадке
- Отдельная кнопка "Сгенерировать BTD-план"

## 5. Technical Approach

### Новые настройки (settings_service.py)
```python
_DEFAULTS = {
    ...
    "btd_threshold_pct": "-10",   # срабатывает при просадке ≤ -10%
    "btd_extra_budget_usd": "200", # доп. бюджет при BTD
}
```

### Новая функция (recommender.py)
```python
def get_btd_signal(db: Session) -> dict | None:
    """
    Returns BTD signal dict if drawdown <= threshold, else None.
    Dict: {drawdown_pct, threshold_pct, extra_budget, allocation: list[BuyRow]}
    """
    threshold = settings_service.get_float(db, "btd_threshold_pct")  # e.g. -10.0
    extra_budget = settings_service.get_float(db, "btd_extra_budget_usd")
    drawdown = get_market_drawdown()  # from analytics import
    if drawdown > threshold / 100:
        return None
    rows = generate_buy_plan(extra_budget, db)
    return {
        "drawdown_pct": round(drawdown * 100, 1),
        "threshold_pct": threshold,
        "extra_budget": extra_budget,
        "rows": rows,
    }
```

### Роутер (recommend.py)
- GET /recommend: вызвать `get_btd_signal(db)`, передать в шаблон как `btd`
- Шаблон рендерит баннер если `btd is not None`

### UI (recommend.html)
```html
{% if btd %}
<div class="btd-banner">
  ⚠️ VWCE просел на {{ btd.drawdown_pct }}% от годового максимума.
  По стратегии BTD рекомендуем дополнительно ${{ btd.extra_budget }}:
  [таблица разбивки по тикерам]
</div>
{% endif %}
```

### Настройки (settings.html)
Новая секция "BTD — Докупка на просадке" с двумя полями.

## 6. Deliverables

| File | Purpose |
|------|---------|
| `app/services/settings_service.py` | Добавить 2 ключа в `_DEFAULTS` |
| `app/services/recommender.py` | Добавить `get_btd_signal()` |
| `app/routers/recommend.py` | Вызвать `get_btd_signal`, передать в шаблон |
| `app/templates/recommend.html` | BTD-баннер (условный рендер) |
| `app/templates/settings.html` | Два новых поля для BTD настроек |

## 7. Success Criteria

- **Functional:**
  - При просадке VWCE ≤ -10% на /recommend появляется баннер с просадкой и допбюджетом
  - При просадке > -10% баннер отсутствует (без ошибок)
  - Настройки threshold и extra_budget сохраняются через /settings и влияют на логику
  - Если yfinance недоступен — баннер не показывается (graceful degradation)
- **Tests:**
  - Unit: `get_btd_signal()` возвращает None при drawdown > threshold, dict при ≤ threshold
  - E2E: Playwright проверяет наличие/отсутствие баннера (mock drawdown)

## 8. Implementation Notes & BQC Risks

| If task involves... | Risk | Mitigation |
|---------------------|------|------------|
| yfinance call в GET-запросе | Таймаут → медленная страница | Таймаут 5s в `get_market_drawdown()`, graceful except |
| Отрицательный threshold | Неверное сравнение знаков | threshold хранится как отрицательное число (-10), сравниваем drawdown > threshold/100 |
| Нет позиций в БД | `generate_buy_plan` вернёт [] | Баннер показывается с пустой таблицей или скрывается (проверить) |
| UI fetch | Missing states | Показывать "данные недоступны" при ошибке drawdown |

Security-reviewed: no threats identified. Читает только публичные рыночные данные через yfinance. Настройки читаются из Config (auth-protected). Нет пользовательского ввода в GET-запросе.

## 9. Testing Strategy

- **Unit**: `tests/unit/test_btd_signal.py` — mock `get_market_drawdown`, проверить граничные случаи (-9.9%, -10%, -10.1%)
- **Integration**: вызов `get_btd_signal(db)` с реальной test БД
- **E2E (Playwright)**: mock yfinance через monkeypatch или ENV-флаг; проверить что баннер рендерится / не рендерится
- **QA Hacker**: передать threshold=0 (всегда активен), negative extra_budget, отсутствие позиций

## 10. Layer Impact Map

| Layer | Impact | Files |
|-------|--------|-------|
| Config / settings | low | `app/services/settings_service.py` |
| Service layer | medium | `app/services/recommender.py` |
| API routes | low | `app/routers/recommend.py` |
| Frontend | medium | `app/templates/recommend.html`, `app/templates/settings.html` |
| Tests | medium | `tests/unit/test_btd_signal.py`, Playwright spec |

## 11. Red Flags

- `get_market_drawdown()` делает live HTTP-запрос к yfinance при каждом GET /recommend — нет кеширования. При медленном соединении страница зависнет. Нужен timeout и fallback None.
- Знак threshold: если пользователь вводит "+10" вместо "-10" в настройках — логика инвертируется. Нужна валидация или автоматическое приведение к отрицательному значению.
- Если `generate_buy_plan()` возвращает [] (нет позиций, нет underweight) — BTD-сигнал активен, но таблица пустая. UX неочевидный.

## 12. Dependencies

- `yfinance` — уже установлен (T-004)
- `openai` (OpenRouter) — только для rationale в `generate_buy_plan`, опционально
- Без новых миграций БД (только новые Config-ключи через `seed_defaults`)
