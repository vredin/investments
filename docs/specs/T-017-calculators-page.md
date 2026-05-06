# T-017: Страница /calculators — калькулятор сложных процентов + калькулятор финансовой независимости

**Created**: 2026-05-06
**Risk**: Low
**Status**: Backlog

## 1. Overview
Новая страница /calculators с двумя standalone-калькуляторами:
1. **Калькулятор сложных процентов** — начальный депозит, периоды, ставка за период, довложения → таблица роста по периодам.
2. **Калькулятор финансовой независимости** — желаемый ежемесячный доход в сегодняшних деньгах, горизонт, инфляция, ставка изъятия → необходимый капитал, инфляция-скорректированный доход, требуемые ежемесячные взносы.
Оба калькулятора работают на чистом JS (нет API, нет DB). Мгновенный пересчёт при вводе.

## 2. Objectives
### Калькулятор сложных процентов
- [ ] Поля ввода: Начальный депозит ($), Количество периодов (N), Доходность за 1 период (%), Довложения каждый период ($)
- [ ] Таблица: Период | Начало | Начислено % | Довложено | Конец периода
- [ ] Итоги: Итого начислено процентов, Итого довложений, Финальная сумма
- [ ] При N > 60: показывать каждый 5-й период + последний (cap отображения)
- [ ] Предупреждение при N > 600 (не вычислять)

### Калькулятор финансовой независимости
- [ ] Поля ввода: Желаемый доход ($/мес, сегодняшние $, default 2000), Горизонт (лет, default 20), Инфляция (%/год, default 3), Ставка изъятия (%/год, default 4), Ожидаемая доходность портфеля (%/год, default 8)
- [ ] Вывод 1: Доход через N лет = monthly * (1+inflation/100)^years $/мес
- [ ] Вывод 2: Необходимый капитал = annual_income_future / (withdrawal_rate/100)
- [ ] Вывод 3: Требуемые ежемесячные взносы (с $0) = PMT формула от нужного капитала
- [ ] Вывод 4: Процент прогресса если есть портфель (ссылка на дашборд, не API)

## 3. Prerequisites
- Базовая верстка (`base.html`, стиль проекта)

## 4. Scope
**In scope**:
- `app/routers/calculators.py` — GET /calculators (static page, login_required)
- `app/templates/calculators.html` — два калькулятора, чистый JS
- `app/main.py` — подключить router
- `app/templates/base.html` — ссылка "Калькуляторы" в nav

**Out of scope**: сохранение результатов, интеграция с реальными данными портфеля через API, графики (chart.js), мобильное приложение

## 5. Technical Approach

### Формулы JS

**Сложные проценты (per period):**
```js
// FV_n = (FV_{n-1} + PMT) * (1 + r/100)
function compoundTable(pv, n, r, pmt) {
  const rows = [];
  let balance = pv;
  for (let i = 1; i <= n; i++) {
    const interest = balance * r / 100;
    const end = balance + interest + pmt;
    rows.push({ period: i, start: balance, interest, pmt, end });
    balance = end;
  }
  return rows;
}
```

**Финансовая независимость:**
```js
// future monthly income
const futureMonthly = monthly * Math.pow(1 + inflation/100, years);
// required capital (4% rule)
const capital = futureMonthly * 12 / (withdrawal/100);
// monthly PMT to reach capital in N years at expected_return
const r = expected/100/12;
const n = years * 12;
const pmt = r > 0
  ? capital * r / (Math.pow(1+r, n) - 1)
  : capital / n;
```

### Структура страницы
- H1 "Финансовые калькуляторы"
- Section 1: "Калькулятор сложных процентов" — форма + таблица результатов
- Section 2: "Калькулятор финансовой независимости" — форма + карточки результатов
- JS: event listeners на input, пересчёт <50ms, без библиотек

### Отображение таблицы (>60 периодов)
```js
// Показывать каждые Math.ceil(n/60) период
const step = n <= 60 ? 1 : Math.ceil(n / 60);
// Всегда показывать последний период
```

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/routers/calculators.py` | GET /calculators |
| `app/templates/calculators.html` | Два калькулятора + JS логика |
| `app/main.py` | include router calculators |
| `app/templates/base.html` | ссылка в nav |

## 7. Success Criteria
- При вводе PV=100, N=10, r=10%, PMT=0 → финальная сумма $259.37 (точность ≤ $0.01)
- При вводе monthly=$2000, years=20, inflation=3%, withdrawal=4%, return=8%:
  - Доход через 20 лет ≈ $3612/мес
  - Необходимый капитал ≈ $1,083,600
  - Ежемесячные взносы ≈ $1,821/мес
- N=0 или r=0 не вызывают ошибки JS
- N>600 показывает предупреждение "Слишком много периодов"
- Оба калькулятора работают без перезагрузки страницы

## 8. BQC Risks
Security-reviewed: no threats — read-only page, all math in client-side JS, no user input reaches server/DB.

| Risk | Mitigation |
|------|------------|
| N=0 division by zero | Guard: if n <= 0 return |
| r=0 PMT formula: division by zero | Guard: linear calc when r=0 |
| Очень большие числа (N=600, PV=1e9) | toLocaleString() обрабатывает корректно, нет overflow в JS float |
| XSS через input (не актуально) | input type=number, все вывод через textContent |

## 9. Testing Strategy
- Manual: проверить все success criteria выше
- E2E (опционально): GET /calculators → 200, поля присутствуют
- Unit (JS): нет (логика простая, покрывается manual тестом)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Router | low | calculators.py |
| Templates + JS | medium | calculators.html |
| Nav | low | base.html |
| App wiring | low | main.py |

## 11. Red Flags
- PMT формула при r=0: `capital / n` — корректно для линейного случая
- Довложения в конце vs начале периода: выбрана модель "в конце" (end-of-period) как стандарт
- N > 600 не вычисляется (JS может зависнуть на O(600) итерациях в tight loop — нет, 600 итераций мгновенно, но 600 строк в DOM медленно). Cap строк = 120 строк в таблице (отображение), вычисление до 600.

## 12. Dependencies
- Нет внешних зависимостей
