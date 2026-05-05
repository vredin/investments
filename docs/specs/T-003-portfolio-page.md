# T-003: Portfolio page /portfolio

**Created**: 2026-05-05
**Risk**: Low
**Status**: Backlog

## 1. Overview
No page currently shows the full list of positions and transaction history. `/portfolio`
gives the user a complete view of what was synced: all current positions sorted by value,
and the last 50 transactions sorted by date descending. This is the primary "did the sync
work?" verification page, and a pre-requisite for Phase 02 allocation deviation calculator.

## 2. Objectives
- [ ] New GET `/portfolio` route with login_required
- [ ] Positions table: latest snapshot per ticker, sorted by market_value_usd DESC
- [ ] Columns: Ticker | Broker | Qty | Avg Cost (USD) | Market Value (USD)
- [ ] Transactions table: last 50 rows sorted by trade_date DESC
- [ ] Columns: Date | Ticker | Type | Qty | Price | Amount | Fee | Broker
- [ ] Navigation link to /portfolio in base.html nav
- [ ] Empty-state messages if tables are empty

## 3. Prerequisites
- T-001 complete ✓
- T-002 (dashboard) is independent — can be built in any order

## 4. Scope
**In scope**:
- `app/routers/portfolio.py` — new router
- `app/templates/portfolio.html` — new template
- Register router in `app/main.py`
- Add nav link in `app/templates/base.html`

**Out of scope**:
- Filtering/search UI
- Pagination (50 tx limit is sufficient for now)
- Charts or P&L calculation (Phase 03)
- Edit/delete positions

## 5. Technical Approach
```python
# app/routers/portfolio.py
router = APIRouter(prefix="/portfolio", tags=["portfolio"], dependencies=[Depends(login_required)])

@router.get("", response_class=HTMLResponse)
async def portfolio_page(request: Request, db: Session = Depends(get_db)):
    subq = db.query(func.max(Position.snapshot_date)).scalar_subquery()
    positions = (
        db.query(Position)
        .filter(Position.snapshot_date == subq)
        .order_by(Position.market_value_usd.desc().nullslast())
        .all()
    )
    transactions = (
        db.query(Transaction)
        .order_by(Transaction.trade_date.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(request, "portfolio.html", {
        "positions": positions,
        "transactions": transactions,
    })
```

Template: two `<table>` sections with Tailwind-style (or existing CSS) formatting.
Use `|floatformat:2` Jinja2 filter for numbers.

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/routers/portfolio.py` | New router with single GET /portfolio route |
| `app/templates/portfolio.html` | Two tables: positions + transactions |
| `app/main.py` | Register portfolio router |
| `app/templates/base.html` | Add "Portfolio" nav link |

## 7. Success Criteria
- GET /portfolio with auth → 200, positions table visible, transactions table visible
- Data matches what was uploaded via /sync/freedom and /sync/ibkr
- Empty tables → empty-state row "No data" (not crash)
- Unauthenticated GET /portfolio → 302 to /login

## 8. Implementation Notes & BQC Risks
| Risk | Notes | Mitigation |
|------|-------|------------|
| NULL values in display | qty/price/amount may be NULL | `or 0` / `"-"` in template |
| Large tx count | No pagination yet | limit(50) |
| Multiple snapshot dates | subquery for latest only | same as T-002 |

Security-reviewed: read-only route, login_required at router level. No user input. No threats identified.

## 9. Testing Strategy
- E2e: GET /portfolio requires auth (302 → /login)
- E2e: GET /portfolio after fixture insert → 200, ticker in content
- Unit: not needed (pure DB read + template render)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| API routes | high | `app/routers/portfolio.py` (new) |
| Templates | high | `app/templates/portfolio.html` (new) |
| App wiring | low | `app/main.py` |
| Navigation | low | `app/templates/base.html` |
| Tests | medium | `tests/test_portfolio.py` |

## 11. Red Flags
- `nullslast()` requires SQLAlchemy 2.0+ — already in use ✓
- If main.py router registration order matters for prefix conflicts — check existing order

## 12. Dependencies
- No new libraries
- T-001 for data to display (independent of T-002)
