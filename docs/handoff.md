# Session Handoff — 2026-05-06

## Completed This Session
- T-016: E2E тести для T-010..T-015 — 19 page + 30 hacker тестів, 61/61 pass — commit 5495c0d
- Бонусний фікс: report.py — redirect при недійсному форматі місяця замість 500 — commit 5495c0d
- T-017: спек + GitHub issue #17 — калькулятор сложных процентов + фінансової незалежності — commit 9c31ea4

## In Progress (not finished)
T-017 — лише спек, реалізація не розпочата.

## Next Session Should
1. `/implement` — реалізувати T-017: new `app/routers/calculators.py`, `app/templates/calculators.html`, підключити в `main.py`, ссилка в `base.html`
2. Перевірити success criteria: PV=100, N=10, r=10% → $259.37; monthly=$2000, years=20, inflation=3%, withdrawal=4% → capital≈$1,083,600
3. Запустити E2E тести проти VPS: `E2E_BASE_URL=https://money.semishan.pro E2E_SECRET_KEY="<key>" uv run pytest tests/e2e/ -v`

## Context That Would Be Lost
- E2E тести потребують `E2E_SECRET_KEY` = SECRET_KEY з VPS (`ssh vps3 "grep '^SECRET_KEY=' /opt/Investments/.env | cut -d= -f2-"`)
- T-017 spec: калькулятор сложных процентов використовує модель "довкладення в кінці періоду" (end-of-period)
- T-017 spec: при N > 60 — показувати кожен `ceil(N/60)` рядок; cap 600 для обчислення
- PMT формула при r=0: `capital / n` (лінійний випадок, без ділення на нуль)
- Після deploy потрібно переінсталювати Playwright deps: `docker compose exec app python3 -m playwright install-deps chromium`

## User's Last Unanswered Question
Немає. Остання дія — `/todo add` для T-017, задача додана в бекелог.

## Open Questions for User
- Немає відкритих питань.
