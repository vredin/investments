# Task Archive

| ID | Task | Completed | Commit |
|----|------|-----------|--------|
| T-001 | Fix handoff/compact state transfer — PreCompact hook (audit snapshot + hint file) + hard counter-based Context Budget rules in workflow.md. Hook cannot block compaction (async), so design is defensive: durable transcript snapshot + marker hint file read post-compact. Diablo DA pass: 2 fatal fixes (python fallback + path sanitization), 4 serious fixes (rotation, gitignore, tests, diagnostic-on-failure). 21/21 tests pass. | 2026-04-11 | 87f9514 |
| T-002 | Blocking Stop-hook context enforcement (DA-009 follow-up). Stop hook exits 2 when commits since last [HANDOFF] > 6 OR lines changed > 500 AND docs/handoff.md is stale/missing — forces Claude to continue with instruction to write handoff. Portable stat (BSD+GNU), works without [HANDOFF] anchor via 4h window fallback, immune to initial-commit parent lookup via per-commit log aggregation. Tunable via CTX_BUDGET_MAX_COMMITS / CTX_BUDGET_MAX_LINES env. 17/17 tests pass. | 2026-04-11 | TBD |
| T-001 | Freedom Finance Excel import (portfolio + trades) | 2026-05-05 | 8eac09a |
