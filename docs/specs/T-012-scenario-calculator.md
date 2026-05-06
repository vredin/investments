# T-012: Сценарный калькулятор — "что если"

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Пользователь хочет понять: "Что если откладывать €300 вместо €200?",
"Что если рынок вырастет только на 5%?", "На сколько лет раньше достигну цели?".
Добавить на дашборд интерактивный калькулятор FV с мгновенным пересчётом.

## 2. Objectives
- [ ] Три слайдера/инпута: бюджет, доходность %, горизонт (лет)
- [ ] Мгновенный пересчёт без перезагрузки страницы (JS или HTMX)
- [ ] Показывает: итоговую сумму, разницу с текущим планом, дату достижения цели
- [ ] Не меняет реальные настройки (только симуляция)

## 3. Scope
**In scope**:
- Новая секция на dashboard.html "Сценарный калькулятор"
- GET /api/scenario?budget=300&return_pct=8&years=20 → JSON {fv, months_to_goal, delta}
- JS для мгновенного обновления без reload

**Out of scope**: сохранение сценариев, сравнение нескольких сценариев одновременно

## 5. Technical Approach

**Backend**: новый endpoint в `app/routers/dashboard.py` или отдельный `api.py`:
```python
@router.get("/api/scenario")
async def scenario(budget: float, return_pct: float, years: int, db: Session = Depends(get_db)):
    data = compute_dashboard_data(db)
    pv = data["total_capital"]
    goal = data["goal_usd"]
    fv = fv_projection(pv, budget, return_pct, years * 12)
    current_fv = fv_projection(pv, data["budget_usd"], data["assumed_return"], years * 12)
    return {"fv": round(fv), "delta": round(fv - current_fv), "goal_pct": min(100, fv / goal * 100)}
```

**Frontend**: форма с range + number inputs, fetch() при `input` event, обновление span с результатом.
Никаких библиотек — чистый fetch API.

Input defaults = текущие значения из настроек.
Дополнительно: показать "достигнете цели через X лет" через бинарный поиск по FV.

## 6. Deliverables
| File | Changes |
|------|---------|
| `app/routers/dashboard.py` | GET /api/scenario endpoint |
| `app/templates/dashboard.html` | Секция калькулятора с JS |
| `tests/test_dashboard.py` | Unit тест /api/scenario |

## 7. Success Criteria
- Изменение слайдера мгновенно обновляет результат (< 200ms)
- При budget=0 не выдаёт ошибку
- При return_pct=0 использует линейный рост
- Результат не влияет на настройки

## 8. BQC Risks
| Risk | Mitigation |
|------|------------|
| Division by zero (goal=0) | Guard в endpoint |
| Очень большие числа | Ограничить: budget≤100000, years≤50 |
| XSS через URL params | FastAPI автовалидация типов float/int |

Security-reviewed: no auth threats (read-only calculation, no persistence).

## 9. Testing Strategy
- Unit: /api/scenario с разными параметрами, edge cases (budget=0, return=0)
- E2E: проверить наличие секции калькулятора на дашборде

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| API | low | dashboard.py |
| Templates + JS | medium | dashboard.html |
| Tests | low | test_dashboard.py |
