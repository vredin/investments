# T-002: Dashboard summary cards

**Created**: 2026-05-05
**Risk**: Low
**Status**: Backlog

## 1. Overview
Dashboard (/) currently renders a static placeholder. After broker sync, the DB has positions
and transactions but nothing is displayed. This task wires the dashboard route to the DB and
renders summary cards: total portfolio value, number of positions, breakdown by broker.
Charts and goal-tracking are Phase 03 and remain out of scope here.

## 2. Objectives
- [ ] Dashboard route reads latest positions from DB (most recent snapshot_date per ticker)
- [ ] Renders total market value (USD), positions count, and per-broker breakdown
- [ ] Shows last sync date (max snapshot_date in positions table)
- [ ] Empty-state message when no positions synced yet

## 3. Prerequisites
- T-001 complete (positions/transactions in DB) ✓
- DB running with Position model populated

## 4. Scope
**In scope**:
- Update `app/routers/dashboard.py` to query DB
- Update `app/templates/dashboard.html` with summary cards
- Empty state: "No positions found — sync from IBKR or Freedom"

**Out of scope**:
- Charts (Phase 03)
- Progress to goal $1.3M (Phase 03)
- Performance metrics TWRR/IRR (Phase 03)
- Recommendations panel (Phase 02)

## 5. Technical Approach
`dashboard.py` route:
```python
@router.get("/", response_class=HTMLResponse, dependencies=[Depends(login_required)])
async def dashboard(request: Request, db: Session = Depends(get_db)):
    # Latest snapshot_date per ticker (subquery)
    subq = db.query(func.max(Position.snapshot_date)).scalar_subquery()
    positions = db.query(Position).filter(Position.snapshot_date == subq).all()

    total_value = sum(p.market_value_usd or 0 for p in positions)
    by_broker = {}
    for p in positions:
        by_broker.setdefault(p.broker, 0.0)
        by_broker[p.broker] += p.market_value_usd or 0

    last_sync = db.query(func.max(Position.snapshot_date)).scalar()
    return templates.TemplateResponse(request, "dashboard.html", {
        "positions": positions,
        "total_value": total_value,
        "by_broker": by_broker,
        "last_sync": last_sync,
    })
```

Template: replace placeholder panels with real summary cards.
Style: keep existing CSS grid + .panel — just replace `<p class="placeholder">` with data.

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/routers/dashboard.py` | Add DB dependency, query, template context |
| `app/templates/dashboard.html` | Summary cards: total value, # positions, by broker, last sync |

## 7. Success Criteria
- After sync: dashboard shows correct total market_value_usd from DB
- Per-broker breakdown shows ibkr / freedom split
- No DB = empty-state message (no crash)
- Auth redirect works (no regression)

## 8. Implementation Notes & BQC Risks
| Risk | Notes | Mitigation |
|------|-------|------------|
| Empty positions table | Page must not crash | empty-state branch in template |
| Multiple snapshot dates | Only latest snapshot | subquery `max(snapshot_date)` |
| NULL market_value_usd | Some rows may be NULL | `or 0` default in sum |

Security-reviewed: read-only query, login_required already enforced at router level. No threats identified.

## 9. Testing Strategy
- Unit: mock DB session, assert template context has correct totals
- E2e: authed_client GET /, assert 200 + "USD" in content after fixture positions inserted
- Edge: GET / with empty DB → 200 + empty-state text

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| API routes | medium | `app/routers/dashboard.py` |
| Templates | medium | `app/templates/dashboard.html` |
| DB models | none (read-only) | — |
| Tests | medium | `tests/test_dashboard.py` |

## 11. Red Flags
- `max(snapshot_date)` returns ONE date — if ibkr and freedom sync on different days, only the later date's positions show. For now acceptable.
- If positions table has no rows: `scalar()` returns None → handle None last_sync in template.

## 12. Dependencies
- SQLAlchemy `func.max`, `scalar_subquery` — already in use
- No new external libraries
