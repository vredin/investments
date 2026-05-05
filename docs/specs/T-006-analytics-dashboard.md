# T-006: Portfolio analytics dashboard (Phase 03)

**Created**: 2026-05-05
**Risk**: Medium
**Status**: Backlog

## 1. Overview
Phase 03 monitoring UI: replaces "Available in Phase 03" placeholders on the dashboard
with real charts and metrics. Covers: allocation donut vs target, goal projection to $1.3M,
rebalancing signal, and a monthly progress snapshot. TWRR is deferred until sufficient
snapshot history (≥ 3 months) accumulates.

## 2. Objectives
- [ ] Allocation donut chart (Chart.js): current allocation % per ticker vs target slices
- [ ] "Unmanaged" slice for tickers outside target allocation (e.g. AAPL.US during transition)
- [ ] Goal projection panel: FV formula, configurable assumed annual return (default 8%)
- [ ] Rebalancing signal: highlight tickers where deviation > 5 percentage points
- [ ] Monthly `ProgressSnapshot` upsert: total capital, ttm_return_pct, projection stored in DB
- [ ] Progress bar: current total / $1,300,000 × 100%
- [ ] External balances panel: shows staking balances from `external_balances` table
- [ ] Monthly report page (`/report/YYYY-MM`): renders ProgressSnapshot + LLM narrative

## 3. Prerequisites
- T-004 (prices — needed for current values per ticker)
- T-005 (settings — target allocations stored in Config)

## 4. Scope
**In scope**:
- Dashboard `/` — replace Phase 03 placeholder panels with charts + goal
- `app/services/analytics.py` — compute_snapshot(db): returns ProgressSnapshot data
- `app/routers/dashboard.py` — pass analytics context to template
- `app/templates/dashboard.html` — allocation donut + goal panel + rebalancing alert
- `app/routers/report.py` — implement `/report/{month}` with LLM narrative
- `app/templates/report.html` — monthly report view
- `app/routers/settings.py` — add `assumed_return_pct` and `goal_usd` config fields (default 8%, $1.3M)

**Out of scope**:
- TWRR/IRR calculation (needs ≥3 months history — deferred)
- V80A LifeStrategy comparison (deferred)
- Telegram delivery (Phase 04)
- APScheduler automatic monthly snapshot (Phase 04)

## 5. Technical Approach

### Allocation donut data
```python
# From positions (latest snapshot) + prices (latest close)
# current_value[ticker] = position.quantity × price.close
# total = sum(current_value.values())
# current_pct[ticker] = current_value[ticker] / total × 100
# target_pct from Config keys "allocation.VWCE" etc.
# Chart data: two datasets — current vs target — as doughnut chart
```

### Goal projection (FV formula)
```python
# FV = PV*(1+r)^n + PMT*(((1+r)^n - 1) / r)
# PV = current total capital
# PMT = monthly contribution (from Config "budget_usd")
# r = Config "assumed_return_pct" / 100 / 12
# n = months to 2046-01 (approx 237 months from 2026-05)
# Target: 1_300_000 USD
```

### Rebalancing signal
```python
# For each target ticker: if abs(target_pct - current_pct) > 5 → REBALANCE signal
# Show as warning badge on dashboard
```

### Monthly ProgressSnapshot
```python
# On report page load: upsert ProgressSnapshot for current month
# total_capital_usd = sum market_value_usd from positions (latest) + external_balances
# projected_capital_2046_usd = FV formula result
# ttm_return_pct = NULL until 12 months of snapshots available
```

### Report LLM narrative
```python
# /report/YYYY-MM: Claude Sonnet call with snapshot data
# Prompt: portfolio summary, allocation deviation, goal progress, notable changes
# Fallback: plain table view without LLM text
# Cache: store generated narrative in ProgressSnapshot.report_text (new column) 
#   OR generate on-demand (simpler — generate on each load if not stored)
```

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/services/analytics.py` | Snapshot computation, FV projection, rebalancing signal |
| `app/routers/dashboard.py` | Pass analytics context |
| `app/templates/dashboard.html` | Allocation donut + goal progress + rebalancing alert |
| `app/routers/report.py` | Implement monthly report route with LLM narrative |
| `app/templates/report.html` | Monthly report template |
| `app/routers/settings.py` | Add assumed_return_pct + goal_usd config fields |

## 7. Success Criteria
- Dashboard: allocation donut shows current vs target (both AAPL and ETFs)
- Dashboard: goal progress bar shows current total / $1.3M
- Dashboard: rebalancing warning appears when deviation > 5pp
- `/report/2026-05`: shows ProgressSnapshot for current month + LLM paragraph
- LLM timeout/error: report renders without narrative (no 500)
- Settings: changing assumed_return_pct updates projection on next dashboard load

## 8. Implementation Notes & BQC Risks
| Risk | Notes | Mitigation |
|------|-------|------------|
| No prices in DB | Can't compute current_value from quantity×price | Show market_value_usd from last sync as fallback |
| No positions | All-zero chart | Empty-state message, no chart render |
| LLM report timeout | Report page hangs | 30s timeout, show fallback "Report pending" |
| ProgressSnapshot column missing | report_text not in model | Add migration or store in existing columns |
| FV negative PMT | If budget_usd not in Config | Default to $200/month if Config missing |

Security-reviewed: read-only analytics, LLM prompt with local DB data only, no user PII in prompts, login_required. No threats identified.

## 9. Testing Strategy
- Unit: FV formula — known inputs → expected output
- Unit: rebalancing signal — deviation=6 → signal triggered, deviation=4 → no signal
- Unit: allocation computation — mock positions + prices → correct percentages
- E2e: GET / with seeded positions → 200, "allocation" in content
- E2e: GET /report/2026-05 → 200 (LLM mocked)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Service | high | `app/services/analytics.py` (new) |
| Routes | medium | `app/routers/dashboard.py`, `app/routers/report.py` |
| Templates | high | `app/templates/dashboard.html`, `app/templates/report.html` |
| DB | low | `progress_snapshots` table (read/write), `external_balances` (read) |
| Tests | medium | `tests/test_analytics.py` |

## 11. Red Flags
- `ProgressSnapshot` model has no `report_text` column — either add migration or generate narrative without storing it (stateless, simpler).
- TWRR placeholder: if positions table has only 1 date, return N/A — don't show "0%" which is misleading.
- Chart.js CDN already in base.html — no new dependency. But donut chart data must be passed as JSON in template context, not rendered inline (XSS risk if tickers have special chars).
- Month navigation on report page: need list of months that have snapshots.

## 12. Dependencies
- `anthropic>=0.30` (already installed)
- T-004 (prices for real current values)
- T-005 (Config table with target allocation + budget)
