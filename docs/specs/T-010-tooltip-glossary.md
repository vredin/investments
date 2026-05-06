# T-010: Глоссарий терминов через ⓘ-tooltip

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Пользователь видит DCA, ребалансировка, РАЗРЫВ, underweight — и не понимает что это.
Добавить ⓘ после каждого термина с hover/click tooltip на русском.
Реализация CSS-only через `title` атрибут или кастомный CSS tooltip без JS-зависимостей.

## 2. Objectives
- [ ] ⓘ-символ после терминов: DCA, Ребалансировка, РАЗРЫВ, ETF, TER (если упоминается), Факт %, Цель %
- [ ] Tooltip открывается по hover (desktop) и tap (mobile)
- [ ] Единый стиль через базовый CSS в base.html

## 3. Scope
**In scope**:
- `base.html`: CSS класс `.term` + `.term::after` tooltip
- `recommend.html`: ⓘ после "DCA", "РАЗРЫВ", "ФАКТ %", "ЦЕЛЬ %", "Ребалансировка"
- `dashboard.html`: ⓘ после "Ребалансировка", "ФАКТ %"
- `settings.html`: ⓘ после "Предполагаемая доходность", "Аллокация"

**Out of scope**: отдельная страница глоссария, JS-библиотеки

## 5. Technical Approach
```css
/* base.html */
.term { cursor: help; border-bottom: 1px dotted #888; position: relative; }
.term::after {
  content: attr(data-tip);
  position: absolute; bottom: 100%; left: 0;
  background: #1e293b; color: #fff; padding: .4rem .6rem;
  border-radius: 4px; font-size: .75rem; white-space: nowrap;
  display: none; z-index: 100;
}
.term:hover::after, .term:focus::after { display: block; }
```

```html
<!-- Пример использования -->
<span class="term" data-tip="Dollar Cost Averaging — регулярные покупки фиксированной суммой">DCA ⓘ</span>
```

Словарь (статичные строки, хардкод в шаблонах):
- **DCA** — Dollar Cost Averaging: покупаете фиксированную сумму каждый месяц независимо от цены. Усредняет цену покупки.
- **РАЗРЫВ** — отклонение текущей доли от целевой. +15% = вы на 15 пп ниже цели по этому активу.
- **ФАКТ %** — текущая доля актива в вашем портфеле по рыночной стоимости.
- **ЦЕЛЬ %** — желаемая доля, которую вы задали в Настройках.
- **Ребалансировка** — приведение долей к целевым значениям. Не продажа, а перераспределение новых взносов.
- **ETF** — биржевой фонд. Покупая одну акцию ETF, вы инвестируете в сотни компаний сразу.
- **Предполагаемая доходность** — среднегодовой рост портфеля, который вы ожидаете. Исторически мировой рынок: 7-10% в USD.

## 6. Deliverables
| File | Changes |
|------|---------|
| `app/templates/base.html` | CSS класс `.term` |
| `app/templates/recommend.html` | ⓘ на терминах в заголовках таблицы и тексте |
| `app/templates/dashboard.html` | ⓘ на ребалансировке и доходности |
| `app/templates/settings.html` | ⓘ на полях настроек |

## 7. Success Criteria
- Hover на "DCA ⓘ" показывает tooltip с объяснением
- Работает без JS
- Mobile: tap показывает tooltip

## 8. BQC Risks
Security-reviewed: no threats (static content, no user input).

## 9. Testing Strategy
- E2E: test_pages.py — проверить наличие `.term` элементов на /recommend

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Templates | low | 4 шаблона |
| CSS | low | base.html |
