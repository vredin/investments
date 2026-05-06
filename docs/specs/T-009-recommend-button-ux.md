# T-009: Recommend — UX кнопки "Купить" vs статус "Куплено"

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Кнопка "✓ Куплено" на странице рекомендаций выглядит как статус-индикатор, хотя является
кнопкой-действием (POST /recommend/execute). Пользователь видит "✓ Куплено" для всех позиций
и думает, что они уже помечены как купленные.

## 2. Objectives
- [ ] Кнопка-действие визуально отличается от статуса "уже куплено"
- [ ] Текст кнопки однозначно читается как действие, не как состояние

## 3. Scope
**In scope**:
- `app/templates/recommend.html`: изменить label кнопки и/или стиль
- Кнопка (not r.executed): "Купить ✓" или "Отметить купленным"
- Статус (r.executed): "✓ Куплено" (зелёный текст, не кнопка)

**Out of scope**: логика executed, маршруты, БД

## 5. Technical Approach

Изменение только в шаблоне:
```html
<!-- Было: -->
<button class="execute-btn">✓ Куплено</button>

<!-- Станет: -->
<button class="execute-btn">Купить</button>
```

Статус при `r.executed = True` — оставить "✓ Куплено" (зелёный текст без кнопки). Так
разница очевидна: кнопка = действие, текст без кнопки = факт.

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/templates/recommend.html` | Изменить label execute-btn |

## 7. Success Criteria
- Кнопка показывает "Купить" (императив)
- После клика — исчезает кнопка, появляется "✓ Куплено" зелёным

## 8. Implementation Notes & BQC Risks
Security-reviewed: no threats identified.

## 9. Testing Strategy
- E2E: test_pages.py — кнопка с текстом "Купить" присутствует на странице /recommend

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Templates | low | `app/templates/recommend.html` |

## 11. Red Flags
- E2E тест test_hacker.py кликает кнопку execute через httpx (не браузер) — не затронут
