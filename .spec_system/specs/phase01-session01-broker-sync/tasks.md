# Task Checklist

**Session ID**: `phase01-session01-broker-sync`
**Total Tasks**: 21
**Estimated Duration**: 3-4 hours
**Created**: 2026-05-04

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0101]` = Session reference (phase 01, session 01)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 3 | 0 | 3 |
| Foundation | 5 | 0 | 5 |
| Implementation | 9 | 0 | 9 |
| Testing | 4 | 0 | 4 |
| **Total** | **21** | **0** | **21** |

---

## Setup (3 tasks)

Initial verification before writing any code.

- [ ] T001 [S0101] Discover real `tradernet` SDK API surface: run `docker compose exec app python -c "import tradernet; help(tradernet.TraderNetAPI)"` on VPS (or locally with uv), document actual method names for positions and transactions
- [ ] T002 [S0101] Create `tests/fixtures/` directory and write `tests/fixtures/ibkr_flex_sample.xml` -- minimal valid IBKR Flex Activity Statement XML with 2 open positions and 3 trades (use real IBKR element/attribute names from IBKR Flex documentation)
- [ ] T003 [S0101] Verify migration 0001 is applied on VPS: `docker compose exec app alembic current` -- confirms `instruments`, `positions`, `transactions` tables exist with correct schema

---

## Foundation (5 tasks)

Core DTOs and upsert layer before adapter implementations.

- [ ] T004 [S0101] Rewrite `app/services/ingestion/broker.py` -- define `@dataclass PositionRow(ticker, qty, market_value, cost_basis, currency, broker)` and `@dataclass TransactionRow(ibkr_txn_id, ticker, trade_date, settle_date, qty, price, commission, currency, broker)` as typed contracts; add `class BrokerSyncError(Exception)` for adapter errors
- [ ] T005 [S0101] Add `upsert_instrument(db, ticker) -> int` to `broker.py` -- checks `instruments` table for ticker; if missing inserts stub row (`ticker`, `name=ticker`, `asset_class="unknown"`); returns instrument_id; with idempotency protection
- [ ] T006 [S0101] Add `upsert_positions(db, rows: list[PositionRow]) -> int` to `broker.py` -- uses `sqlalchemy.dialects.postgresql.insert().on_conflict_do_update()` on `(instrument_id, broker)` unique pair; calls `upsert_instrument()` per row; returns count of upserted rows; with idempotency protection, transaction boundaries, and compensation on failure
- [ ] T007 [S0101] Add `upsert_transactions(db, rows: list[TransactionRow]) -> int` to `broker.py` -- upsert on `ibkr_txn_id` UNIQUE column; for Freedom transactions (no stable ID) generate synthetic key as `f"{broker}_{settle_date}_{ticker}_{qty}"`; returns count; with idempotency protection and transaction boundaries
- [ ] T008 [S0101] Add `sync_all_brokers(db) -> dict` to `broker.py` -- orchestrates `ibkr.sync_ibkr_positions(db)` + `freedom.sync_freedom_positions(db)` + `freedom.sync_freedom_transactions(db)`; returns `{"ibkr_positions": N, "freedom_positions": N, "freedom_transactions": N}`; with failure-path handling (one broker failure does not abort the other)

---

## Implementation (9 tasks)

Replace NotImplementedError stubs with real logic.

- [ ] T009 [S0101] Implement `parse_flex_xml(file_content: bytes) -> tuple[list[PositionRow], list[TransactionRow]]` in `app/services/ingestion/ibkr.py` -- parse with `xml.etree.ElementTree`, iterate `OpenPositions` elements for positions and `Trades` elements for transactions; use `element.get("attr", None)` safe defaults; raise `BrokerSyncError` on missing required fields; with schema-validated input and explicit error mapping
- [ ] T010 [S0101] Implement `import_flex_xml(file_content: bytes, db) -> dict` in `ibkr.py` -- calls `parse_flex_xml()`, then `broker.upsert_positions()` + `broker.upsert_transactions()`; returns `{"positions": N, "transactions": N}`; with idempotency protection and transaction boundaries
- [ ] T011 [S0101] Implement `sync_ibkr_positions(db) -> int` in `ibkr.py` -- note: live IBKR API not feasible headless (CP Gateway); this function raises `BrokerSyncError("Use Flex XML upload for IBKR sync")` with clear message directing user to upload form
- [ ] T012 [S0101] Implement `sync_freedom_positions(db) -> int` in `app/services/ingestion/freedom.py` -- instantiate `TraderNetAPI` from settings; call correct SDK method (discovered in T001); normalize response to `list[PositionRow]`; call `broker.upsert_positions()`; with timeout (30s), retry/backoff (2 retries), and failure-path handling; log only "synced N positions from Freedom" (no payload logging)
- [ ] T013 [S0101] Implement `sync_freedom_transactions(db) -> int` in `freedom.py` -- call SDK transactions method for last 365 days; normalize to `list[TransactionRow]` with synthetic key; call `broker.upsert_transactions()`; with timeout, retry/backoff, and failure-path handling
- [ ] T014 [S0101] Add `GET /sync/ibkr` to `app/routers/sync.py` -- returns `sync_ibkr.html` upload form (HTML response); with authorization enforced at boundary (login_required dependency)
- [ ] T015 [S0101] Rewrite `POST /sync/ibkr` in `sync.py` -- accept `file: UploadFile`; validate content_type is XML or filename ends `.xml`; call `ibkr.import_flex_xml(await file.read(), db)`; commit; flash `"Synced {N} positions, {M} transactions from IBKR"`; on error flash `"IBKR import failed: {error}"`; redirect to `/`; with authorization enforced, schema-validated input, and duplicate-trigger prevention
- [ ] T016 [S0101] Rewrite `POST /sync/freedom` in `sync.py` -- call `freedom.sync_freedom_positions(db)` + `freedom.sync_freedom_transactions(db)`; commit; flash success with counts; on `BrokerSyncError` flash error message; redirect to `/`; with authorization enforced and failure-path handling
- [ ] T017 [S0101] Create `app/templates/sync_ibkr.html` -- extends `base.html`; `<form method="POST" enctype="multipart/form-data" action="/sync/ibkr">`; file input for `.xml`; submit button; note "Download Activity Statement from IBKR Portal (XML format, include Open Positions and Trades)"
- [ ] T018 [S0101] [P] Add nav link "Sync IBKR" to `app/templates/base.html` nav bar pointing to `GET /sync/ibkr`; add "Sync Freedom" button/form in dashboard or base nav pointing to `POST /sync/freedom` with confirmation to avoid accidental API calls

---

## Testing (4 tasks)

- [ ] T019 [S0101] [P] Write `tests/test_ibkr_parser.py` -- call `parse_flex_xml()` with `tests/fixtures/ibkr_flex_sample.xml`; assert correct count of `PositionRow` (2) and `TransactionRow` (3); assert key fields: ticker not empty, qty is numeric, trade_date is date
- [ ] T020 [S0101] [P] Write `tests/test_freedom_adapter.py` -- mock `tradernet.TraderNetAPI` with `unittest.mock.patch`; call `sync_freedom_positions(db)` and `sync_freedom_transactions(db)`; assert `PositionRow` / `TransactionRow` fields are correctly mapped from mock payload
- [ ] T021 [S0101] Write `tests/test_sync_routes.py` -- use `TestClient`; POST `/sync/ibkr` with `files={"file": ("test.xml", open("tests/fixtures/ibkr_flex_sample.xml", "rb"), "application/xml")}`; assert redirect + flash set; query test DB, assert `positions` and `transactions` rows exist; POST again, assert row counts unchanged (idempotency verified)
- [ ] T022 [S0101] Run `uv run ruff check app/ tests/` (0 errors) + `uv run pytest tests/ -v -q`; deploy updated image to VPS: `docker compose up -d --build --no-deps app`; verify `/sync/ibkr` GET returns form (200); verify `/sync/freedom` POST with empty .env keys returns error flash (not 500)

---

## Completion Checklist

Before marking session complete:

- [ ] All 21 tasks marked `[x]`
- [ ] Broker response payloads NOT appearing in logs
- [ ] IBKR upload form renders at `GET /sync/ibkr`
- [ ] Upload fixture XML → rows in DB, flash shows count
- [ ] Upload same file again → identical row count (no dupes)
- [ ] Freedom sync with invalid keys → error flash, not 500
- [ ] `ruff check` passes (0 errors)
- [ ] `pytest tests/ -v` passes (skipping Freedom integration if no live keys)
- [ ] Ready for `/validate`

---

## Next Steps

Run `/implement` to begin AI-led implementation.
