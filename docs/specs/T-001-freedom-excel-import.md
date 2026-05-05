# T-001: Freedom Finance Excel Import

**Created**: 2026-05-05
**Risk**: Medium
**Status**: Done

## 1. Overview
Freedom Finance (freedom24.com) uses the TraderNet platform, whose REST API exposes
portfolio data only via WebSocket (notifyPortfolio) — not HTTP. Import is implemented
via Excel exports from the Freedom24 web UI, parsed server-side and upserted into DB.

## 2. Objectives
- [x] Upload "Відкриті позиції" Excel → positions table
- [x] Upload "Угоди" Excel → transactions table
- [x] Idempotent: re-uploading same file produces no duplicate rows
- [x] Invalid file type rejected with clear user message
- [x] No 500 / stack trace exposed to user

## 3. Prerequisites
- openpyxl in project dependencies (for pandas xlsx backend)
- DB running and migrations applied
- User authenticated (login_required dependency)

## 4. Scope
**In scope**: parse Freedom24 portfolio.xlsx and Trades.xlsx, upsert via existing
`upsert_positions` / `upsert_transactions`, upload UI at `/sync/freedom`.

**Out of scope**: TraderNet WebSocket real-time sync, Freedom24 API key auth,
cash rows (USD/EUR FX conversions), multi-account portfolios.

## 5. Technical Approach
- `freedom.py`: `parse_freedom_portfolio_xlsx(bytes)`, `parse_freedom_trades_xlsx(bytes)`,
  `import_freedom_portfolio_xlsx(bytes, db)`, `import_freedom_trades_xlsx(bytes, db)`
- `sync.py`: `GET /sync/freedom` (form), `POST /sync/freedom/portfolio`,
  `POST /sync/freedom/trades`
- `sync_freedom.html`: two-panel upload form
- Column mapping portfolio: Тікер→ticker, К-ть→qty, Ціна входу×К-ть→cost_basis, Вартість→market_value_usd
- Column mapping trades: Номер→ibkr_txn_id (`freedom_{id}`), Дата→trade_date,
  Купівля/Продаж→BUY/SELL, Quantity→qty, Ціна→price_usd, Плата→commission
- Cash rows (ticker contains "/") skipped silently

## 6. Deliverables
| File | Purpose |
|------|---------|
| `app/services/ingestion/freedom.py` | Added 4 xlsx functions |
| `app/routers/sync.py` | GET + 2×POST routes |
| `app/templates/sync_freedom.html` | Upload UI |
| `pyproject.toml` | Added openpyxl>=3.1 |

## 7. Success Criteria
- Functional: portfolio.xlsx → 1 position in DB (ZIM.US, qty=7, market_value=182.35)
- Functional: Trades.xlsx → 1 transaction in DB (ZIM.US BUY, id=freedom_527716496)
- Idempotency: re-upload → counts unchanged (1, 1)
- Invalid file → error flash, no 500
- Tests: manual verified; unit tests — deferred (see Red Flags)

## 8. Implementation Notes & BQC Risks
| If task involves... | Risk | Mitigation |
|---------------------|------|------------|
| File upload | Malicious xlsx (zip bomb, XXE) | openpyxl reads data_only=True; no macro exec; file size limit via reverse proxy |
| Write path | Duplicate rows | ON CONFLICT DO UPDATE (upsert) — verified idempotent |
| External file format | Column name change in Freedom24 export | BrokerSyncError with list of missing columns |
| Auth resource | Unauth upload | login_required dependency on entire /sync prefix |
| Error information | Stack trace leak | Generic message to user; full exception logged server-side only |

Security-reviewed: file upload path. No macro execution (data_only=True). Auth enforced.
No CRITICAL risks identified.

## 9. Testing Strategy
- Unit: `parse_freedom_portfolio_xlsx` / `parse_freedom_trades_xlsx` with fixture bytes — **deferred**
- Integration: manual upload via curl ✅
- Idempotency: second upload → row count unchanged ✅
- Edge cases: non-xlsx → error flash ✅
- QA Hacker: empty file, file with only header row, cash-only file (all "/" tickers)

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| Ingestion service | high | `app/services/ingestion/freedom.py` |
| API routes | medium | `app/routers/sync.py` |
| Templates | low | `app/templates/sync_freedom.html` |
| Dependencies | low | `pyproject.toml` |
| Tests | low | deferred |

## 11. Red Flags
- Unit tests for parsers not written — if Freedom24 changes column names, parser breaks silently until user uploads and sees BrokerSyncError
- `ibkr_txn_id` for trades is derived from "Номер" column — if Freedom24 changes order number format, old rows won't deduplicate correctly
- Cash FX rows (USD/EUR) silently skipped — user has no visibility that some rows were dropped

## 12. Dependencies
- openpyxl>=3.1 (xlsx reading)
- Existing `upsert_positions`, `upsert_transactions` from `broker.py`
- Migrations: positions + transactions tables must exist (migration 0001)
