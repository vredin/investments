# Implementation Notes

**Session ID**: `phase01-session01-broker-sync`
**Started**: 2026-05-04 00:00
**Last Updated**: 2026-05-04 00:00

---

## Session Progress

| Metric | Value |
|--------|-------|
| Tasks Completed | 0 / 21 |
| Estimated Remaining | 3-4 hours |
| Blockers | 0 |

---

## Design Decisions

### Decision 1: tradernet SDK has no importable source

**Context**: `import tradernet` raises `ModuleNotFoundError` despite being listed in pip. The
installed package (0.1.3) contains only dist-info metadata — no Python source files in RECORD.

**Options Considered**:
1. Block on SDK — not feasible, SDK is broken
2. Implement using `requests` directly with HMAC signing — portable, matches API docs

**Chosen**: Option 2 — direct `requests` HTTP calls with HMAC-SHA256 signing.
**Rationale**: The TraderNet REST API is documented. Signing pattern (HMAC + body JSON) is known
from the kazanzhy/tradernet repo research. Tests mock `requests.post`, not the tradernet module.

### Decision 2: Position model has no instrument_id FK

**Context**: The spec mentions `upsert on (instrument_id, broker)` but `Position` model uses
`(snapshot_date, ticker)` as composite PK, with `ticker` directly (no FK to instruments).

**Chosen**: Upsert positions on `(snapshot_date, ticker)` PK. `upsert_instrument` called first
per row to ensure ticker stub exists in instruments. snapshot_date = today.

### Decision 3: Instrument model has `category`, not `asset_class`

**Context**: Spec says `asset_class="unknown"` for stubs, but actual model column is `category`.

**Chosen**: Use `category=None` for stub instruments (column is nullable).

### Decision 4: Freedom transactions get synthetic ibkr_txn_id

**Context**: No stable Freedom transaction ID from API. Using `freedom_{order_id}` when order ID
is present; `freedom_{date}_{ticker}_{qty}` as fallback.

---

## Task Log

### T001-T003 - Setup & Discovery

**Completed**: 2026-05-04
**Notes**:
- tradernet 0.1.3 PyPI package has no Python source files (only dist-info). `import tradernet` raises ModuleNotFoundError.
- Decided to implement Freedom adapter using `requests` directly with HMAC-SHA256 signing.
- Migration 0001 exists locally. VPS check deferred to deploy step.

### T004-T008 - broker.py Foundation

**Completed**: 2026-05-04
**Files Changed**: `app/services/ingestion/broker.py` — full rewrite

**BQC Fixes**:
- Idempotency: `on_conflict_do_nothing` for instruments, `on_conflict_do_update` for positions/transactions
- Failure path: `sync_all_brokers` catches BrokerSyncError per broker, continues to next
- Empty rows: early return for empty lists (no empty INSERT)

### T009-T011 - ibkr.py

**Completed**: 2026-05-04
**Files Changed**: `app/services/ingestion/ibkr.py` — full rewrite

**BQC Fixes**:
- Schema validation: ET.ParseError → BrokerSyncError (no 500 on bad XML)
- Safe defaults: `element.get("attr") or 0` instead of assuming attribute presence
- Logging: warnings for skipped rows but no crash

### T012-T013 - freedom.py

**Completed**: 2026-05-04
**Files Changed**: `app/services/ingestion/freedom.py` — full rewrite

**BQC Fixes**:
- Timeout: 30s per request
- Retry: 2 retries with exponential backoff (1s, 2s)
- PII: never logs API response payload, only "synced N positions" counts
- Auth failure → BrokerSyncError with clear message (not 500)

### T014-T018 - Routes & Templates

**Completed**: 2026-05-04
**Files Changed**: `app/routers/sync.py`, `app/templates/sync_ibkr.html`, `app/templates/base.html`

**BQC Fixes**:
- File type validation before reading content
- Empty file check before passing to parser
- `db.rollback()` on all error paths before redirect
- Generic error message to user (no stack trace exposure)
- Auth enforced at router level (`dependencies=[Depends(login_required)]`)

### T019-T022 - Tests & Quality Gates

**Completed**: 2026-05-04
**Files Created**: `tests/test_ibkr_parser.py` (19 tests), `tests/test_freedom_adapter.py` (19 tests), `tests/test_sync_routes.py` (12 tests)
**Files Modified**: `tests/conftest.py` (added dotenv load + requires_db marker), `tests/test_models.py` (added requires_db)

**Results**:
- `ruff check app/ tests/`: 0 errors
- `pytest tests/ -v`: 38 passed, 17 skipped (DB tests skip when no local PostgreSQL)
- Integration tests marked `@requires_db` — auto-skip when DB not available

**Additional fix**: tradernet SDK empty → implemented direct HTTP client in freedom.py
**Additional fix**: conftest.py used os.environ.get(DATABASE_URL) without loading dotenv — added load_dotenv()

---

## Session Complete: 2026-05-04
All 21 tasks done. Ruff 0 errors. 38 unit/adapter tests pass. Ready for /validate.
