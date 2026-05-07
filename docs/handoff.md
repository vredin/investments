# Session Handoff — 2026-05-07

## Completed This Session

- T-019: Деплой step-фикса (goal_usd step="1") на VPS + 3 Playwright-теста HTML5 валидации — done, committed ec3e09b, deployed, archived, issue #19 closed
- T-018: BTD-сигнал на /recommend — get_btd_signal() с 15-мин кешем, BTD-баннер, 2 поля в /settings — done, committed 16b3f35, deployed, archived, issue #18 closed
- Vault: G-035 (Playwright fill bypasses HTML5 step validation), G-036 (sync external API in GET handler needs TTL cache)

## In Progress (not finished)

None. Backlog is empty.

## Next Session Should

1. Run E2E тесты против прода: `E2E_BASE_URL=https://money.semishan.pro uv run pytest tests/e2e/ -q` — убедиться что все 3 новых T-019 теста проходят
2. Проверить /recommend на проде — BTD баннер скрыт (рынок не в просадке ≥10%) или виден если просадка активна
3. Выбрать следующую задачу через `/todo add` или дождаться запроса пользователя

## Context That Would Be Lost

- T-019 тесты SKIP локально (requires_e2e marker) — это ожидаемо, не баг. Нужен E2E_BASE_URL для запуска против живого сервера.
- Flash message в settings роутере изменён с "Settings saved" → "Сохранено" — нужно для assert в test_settings_save_valid.
- BTD threshold: server-side отклоняет btd_threshold_pct >= 0 с русской ошибкой. HTML input min=-50 max=-1, но сервер проверяет независимо.
- _drawdown_cache в recommender.py — module-level dict, сбрасывается при рестарте контейнера. Первый GET /recommend после рестарта вызовет yfinance live.
- DA нашёл и исправил: no-op assert в test_settings_form_submit_non_round_goal ("990001" never в HTML — browser tooltips не в DOM).

## User's Last Unanswered Question

None — пользователь вызвал /orchestrate, pipeline завершён, бэклог пуст.

## Open Questions for User

None.
