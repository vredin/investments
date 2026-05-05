# Session Handoff — 2026-05-05

## Completed This Session

- T-002: Dashboard summary cards — DB-backed, total value + by-broker + last sync. Commit `b123a28`. Deployed.
- T-003: Portfolio page `/portfolio` — positions + transactions tables, nav link. Commit `a1bd936`. Deployed.
- T-004: Price sync via yfinance — `app/services/prices.py`, POST `/sync/prices`, "Sync Prices" nav button. Ticker mapping: AAPL.US→AAPL, VWCE→VWCE.AS, VEUR→VEUR.AS, AGGH→AGGH.L, XEON→XEON.DE. 7 unit tests pass. Commit `570ad2a`. Deployed.
- T-004/T-005/T-006 specs created and GitHub issues #4/#5/#6 opened.

## In Progress (not finished)

Nothing.

## Next Session Should

1. **`/todo start T-005`** then implement buy recommender — `app/services/recommender.py`, settings page (Config table: target allocations + budget), `/recommend` route, LLM rationale with Claude Sonnet fallback
2. **Before T-005**: run "Sync Prices" on live site to populate `prices` table — needed for oversold scoring in recommender
3. **After T-005**: `T-006` — analytics dashboard (allocation donut, goal projection to $1.3M, rebalancing signal)

## Context That Would Be Lost

- Target ETF yfinance symbols are hardcoded in `app/services/prices.py:_TARGET_ETF_MAP`: VWCE.AS, VEUR.AS, AGGH.L, XEON.DE. If user ever buys these on a different exchange (e.g. Xetra for VWCE.DE), the mapping must be updated manually.
- T-005 recommender spec: AAPL.US is NOT in target allocation (VWCE/VEUR/AGGH/XEON) — must be shown as "unmanaged position", not recommended for purchase.
- T-005 LLM fallback: if Anthropic API fails, use "Allocation-driven purchase (target: X%)" string — no 500 error.
- Config table seeds: first run needs default target allocations (VWCE=65, VEUR=15, AGGH=15, XEON=5) and budget_usd=200 seeded on first access — missing seed = division by zero in allocation calc.
- User is just starting portfolio (AAPL.US test position only). Real portfolio being built around VWCE/VEUR/AGGH/XEON.
- PRD goal: $1.3M by 2046, monthly contributions $200-1000, target allocation 65/15/15/5.

## User's Last Unanswered Question

None — last message was "запусти T-004 по процессу" and T-004 is complete and deployed.

## Open Questions for User

- Ready to implement T-005 (recommender)? It's the most complex task (High risk, LLM integration).
- Should we verify "Sync Prices" worked on live site before starting T-005?
