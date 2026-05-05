# Session Handoff — 2026-05-05

## Completed This Session

- T-002: Dashboard summary cards — `app/routers/dashboard.py` reads DB, shows total value, by-broker breakdown, last sync date. Empty-state when no positions. Commit `b123a28`. Deployed.
- T-003: Portfolio page `/portfolio` — new route + template with positions table (latest snapshot, sorted by market_value DESC) + transactions table (last 50). Broker badges, BUY/SELL/DIV color coding. Nav link added. Commit `a1bd936`. Deployed.

## In Progress (not finished)

Nothing.

## Next Session Should

1. **Verify live data on VPS** — open https://money.semishan.pro/portfolio and https://money.semishan.pro and confirm positions/transactions from Freedom sync are visible
2. **Run e2e tests on VPS** — `ssh vps3 "cd /opt/Investments && uv run pytest tests/test_dashboard.py tests/test_portfolio.py tests/test_sync_routes.py -v"` against live PostgreSQL
3. **Plan next Phase 01 task** — backlog is empty; Phase 01 remaining: price sync (`/sync/prices` via yfinance), PDF ingestion, LLM rule extraction, Telegram parser (see PRD Phase 01 objectives 5-8)

## Context That Would Be Lost

- Dashboard shows only the single latest `snapshot_date` across ALL brokers — if ibkr and freedom sync on different days, only the later date's positions appear. Accepted tradeoff for now, will need per-broker latest snapshot in Phase 03.
- `/portfolio` positions table uses `nullslast()` for market_value_usd ordering — positions with NULL market value appear at the bottom.
- Transaction type stored as `t.type` in DB model (not `t.txn_type`) — template uses `t.type | lower` for CSS class.
- T-002 and T-003 specs created in `docs/specs/`, GitHub issues #2 and #3 closed.

## User's Last Unanswered Question

None — user said "да, T-003" and T-003 is complete and deployed.

## Open Questions for User

- Phase 01 has 5 more objectives (price sync, PDF ingestion, LLM rules, Telegram parser) — which to tackle next?
