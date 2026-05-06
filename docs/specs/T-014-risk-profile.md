# T-014: Риск-профиль — 3 вопроса → рекомендованная аллокация

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Новичок не знает зачем 65% в VWCE и 15% в облигациях.
Добавить простой опросник (3 вопроса) который объясняет текущую аллокацию и при необходимости
предлагает скорректировать её под горизонт и терпимость к риску.

## 2. Objectives
- [ ] 3 вопроса: горизонт инвестирования, реакция на просадку -30%, наличие других источников дохода
- [ ] На основе ответов — рекомендованный профиль (Conservative/Balanced/Growth) с аллокацией
- [ ] Сравнение текущей аллокации с рекомендованной
- [ ] Кнопка "Применить рекомендованную аллокацию" (записывает в настройки)

## 3. Scope
**In scope**:
- `app/templates/settings.html`: секция "Риск-профиль" с формой из 3 select/radio
- `app/services/settings_service.py` или inline в роутере: функция `recommend_allocation(answers) -> dict`
- Три профиля:
  - **Conservative** (горизонт < 10 лет или "продам при -20%"): VWCE 40%, VEUR 10%, AGGH 40%, XEON 10%
  - **Balanced** (10-15 лет, "подожду восстановления"): VWCE 55%, VEUR 15%, AGGH 25%, XEON 5%
  - **Growth** (> 15 лет, "куплю ещё на просадке"): VWCE 65%, VEUR 20%, AGGH 10%, XEON 5%

**Out of scope**: сохранение истории профилей, персонализация за пределами 4 ETF

## 5. Technical Approach

Форма в settings.html, POST к новому эндпоинту `/settings/risk-profile`:
```python
@router.post("/settings/risk-profile")
async def risk_profile(horizon: int = Form(...), panic_sell: str = Form(...), ...):
    profile = _recommend_profile(horizon, panic_sell, other_income)
    # Вернуть рекомендации как JSON или редиректить на /settings с flash
```

Либо проще: JS-only, без бэкенда. Три select → JS вычисляет профиль → показывает рекомендацию + кнопку "Применить" (POST /settings с нужными значениями).

Предпочтительно: JS-only для мгновенного результата, POST /settings для применения.

## 6. Deliverables
| File | Changes |
|------|---------|
| `app/templates/settings.html` | Секция риск-профиль + JS логика |

## 7. Success Criteria
- Выбор ответов мгновенно показывает профиль и рекомендованную аллокацию
- "Применить" записывает значения в поля формы настроек (не сразу сохраняет — пользователь видит и нажимает Save)
- Три профиля покрывают все комбинации ответов

## 8. BQC Risks
Security-reviewed: no threats (JS-only logic, save goes through existing /settings validation).

## 9. Testing Strategy
- Manual: проверить все 3 профиля через UI

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Templates + JS | low | settings.html |
