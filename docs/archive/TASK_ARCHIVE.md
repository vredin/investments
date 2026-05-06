# Task Archive

| ID | Task | Completed | Commit |
|----|------|-----------|--------|
| T-001 | Fix handoff/compact state transfer — PreCompact hook (audit snapshot + hint file) + hard counter-based Context Budget rules in workflow.md. Hook cannot block compaction (async), so design is defensive: durable transcript snapshot + marker hint file read post-compact. Diablo DA pass: 2 fatal fixes (python fallback + path sanitization), 4 serious fixes (rotation, gitignore, tests, diagnostic-on-failure). 21/21 tests pass. | 2026-04-11 | 87f9514 |
| T-002 | Blocking Stop-hook context enforcement (DA-009 follow-up). Stop hook exits 2 when commits since last [HANDOFF] > 6 OR lines changed > 500 AND docs/handoff.md is stale/missing — forces Claude to continue with instruction to write handoff. Portable stat (BSD+GNU), works without [HANDOFF] anchor via 4h window fallback, immune to initial-commit parent lookup via per-commit log aggregation. Tunable via CTX_BUDGET_MAX_COMMITS / CTX_BUDGET_MAX_LINES env. 17/17 tests pass. | 2026-04-11 | TBD |
| T-001 | Freedom Finance Excel import (portfolio + trades) | 2026-05-05 | 8eac09a |
| T-002 | Dashboard summary cards (total value, by broker, last sync) | 2026-05-05 | b123a28 |
| T-003 | Portfolio page /portfolio (positions + transactions tables) | 2026-05-05 | a1bd936 |
| T-004 | Price sync via yfinance (/sync/prices, 250d history, 4 target ETFs) | 2026-05-05 | 570ad2a |
| T-005 | Monthly buy recommender — underweight-first allocation + oversold scoring + LLM rationale + web UI | 2026-05-05 | 89e93f5 |
| T-006 | Analytics dashboard — allocation donut, goal projection (FV), rebalancing signal, monthly report with LLM | 2026-05-05 | 47c1a66 |
| T-007 | Playwright E2E тесты — 41 tests (auth/pages/hacker), dual-mode server (subprocess or E2E_BASE_URL), QA hacker: XSS, SQLi, path traversal, IDOR, boundary values | 2026-05-06 | 8652260 |
