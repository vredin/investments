# Session Specification

**Session ID**: `phase01-session01-broker-sync`
**Phase**: 01 - Data Ingestion
**Status**: Not Started
**Created**: 2026-05-04

---

## 1. Session Overview

This session implements real broker data synchronization — replacing all `NotImplementedError` stubs
in `app/services/ingestion/` with working adapters. Two brokers are connected: IBKR (via Flex Query
XML file upload, since CP Gateway requires a browser session and cannot run headless on VPS) and
Freedom Finance (via the official `tradernet` Python SDK with API keys already in `.env`).

Both adapters normalize their broker-specific payloads to common `PositionRow` and `TransactionRow`
dataclasses defined in `broker.py`. Upsert semantics (idempotent on primary keys) ensure running
sync twice does not create duplicates. The router layer commits the transaction and flashes the
result count to the user.

After this session, the user can upload an IBKR Flex XML report to see positions and transactions
appear in the database, and trigger a Freedom Finance sync from the web UI that pulls live data.

---

## 2. Objectives

1. IBKR Flex XML parser: read Activity Statement, extract `OpenPositions` + `Trades` sections,
   normalize to `PositionRow` / `TransactionRow` with schema validation and explicit error mapping.
2. Freedom Finance adapter: call `tradernet` SDK, normalize portfolio and trade history to the
   same `PositionRow` / `TransactionRow` schema, with timeout and failure-path handling.
3. Unified upsert layer: `broker.py` orchestrates both adapters and writes to `instruments`,
   `positions`, `transactions` tables using idempotent `INSERT ... ON CONFLICT DO UPDATE`.
4. Live routes: `/sync/ibkr` (multipart file upload form) and `/sync/freedom` (API pull) both
   return flash success with row count or flash error with message.

---

## 3. Prerequisites

### Required Sessions
- [x] `phase00-session01-skeleton` - DB schema, models, router stubs, auth, APScheduler

### Required Tools/Knowledge
- `tradernet` Python package (already in pyproject.toml) — Freedom Finance SDK
- IBKR Flex Query: user downloads XML from IBKR portal (Activity Statement, XML format)
- SQLAlchemy `insert().on_conflict_do_update()` from `sqlalchemy.dialects.postgresql`
- `httpx` for any direct IBKR API calls (not used this session — Flex upload only)

### Environment Requirements
- `FREEDOM_PUBLIC_KEY`, `FREEDOM_PRIVATE_KEY`, `FREEDOM_LOGIN`, `FREEDOM_PASSWORD` in `.env`
- PostgreSQL running with all tables from migration 0001

---

## 4. Scope

### In Scope (MVP)
- User (owner) can upload IBKR Flex XML file to sync positions + transactions — multipart POST
- User can trigger Freedom Finance sync from dashboard — API pull via `tradernet` SDK
- Both syncs are idempotent: re-running does not create duplicates (`ibkr_txn_id` UNIQUE)
- Sync result shown as flash message: "Synced 12 positions, 34 transactions from IBKR"
- `broker.py` `sync_all_brokers(db)` orchestrates both and returns combined counts
- Instruments table auto-populated from ticker symbols seen in positions/transactions

### Out of Scope (Deferred)
- IBKR Client Portal REST API (live positions) — *Reason: requires CP Gateway process, not feasible headless on VPS this phase*
- Price sync via yfinance — *Reason: Phase 01 Session 02*
- Displaying synced data in dashboard charts — *Reason: Phase 03 (Monitoring)*
- Freedom Finance real-time websocket feed — *Reason: out of scope for personal use*

---

## 5. Technical Approach

### Architecture

IBKR path: user uploads XML file → `/sync/ibkr` POST (UploadFile) → `ibkr.import_flex_xml()`
parses XML with `xml.etree.ElementTree` → yields `PositionRow` / `TransactionRow` →
`broker.upsert_positions()` + `broker.upsert_transactions()` → router commits + flash.

Freedom path: `/sync/freedom` POST → `freedom.sync_freedom_positions(db)` +
`freedom.sync_freedom_transactions(db)` → internally calls `tradernet` SDK → normalizes →
`broker.upsert_*()` → router commits + flash.

Instrument auto-population: before upserting positions, check `instruments` table for ticker;
if missing, insert minimal row (`ticker`, `name=ticker`, `asset_class="unknown"`).

### Design Patterns
- **Dataclass schema**: `PositionRow` / `TransactionRow` are `@dataclass` with typed fields —
  acts as contract between adapter and upsert layer, caught at parse time not DB time
- **Upsert idempotency**: `insert().on_conflict_do_update()` on `ibkr_txn_id` for transactions,
  `(instrument_id, broker)` for positions
- **Commit in router**: service functions never call `db.commit()` — router owns the transaction
- **Timeout wrapper**: Freedom API calls wrapped in `httpx`-style timeout via SDK's own timeout;
  if SDK raises, catch and re-raise as `BrokerSyncError`

### Technology Stack
- `xml.etree.ElementTree` (stdlib) — IBKR Flex XML parsing
- `tradernet` — Freedom Finance SDK
- `sqlalchemy.dialects.postgresql.insert` — upsert
- `fastapi.UploadFile` — multipart file upload
- Python `@dataclass` — broker-neutral data transfer objects

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `app/services/ingestion/broker.py` | PositionRow, TransactionRow DTOs + upsert functions | ~120 |
| `app/templates/sync_ibkr.html` | File upload form for IBKR Flex XML | ~40 |
| `tests/fixtures/ibkr_flex_sample.xml` | Minimal IBKR Flex Activity Statement for tests | ~80 |
| `tests/test_ibkr_parser.py` | Unit tests: parse_flex_xml fixture, field mapping | ~80 |
| `tests/test_freedom_adapter.py` | Unit tests: normalize_freedom_position with mock SDK | ~60 |
| `tests/test_sync_routes.py` | Integration tests: upload CSV, verify DB rows, idempotency | ~80 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `app/services/ingestion/ibkr.py` | Replace NotImplementedError stubs with real parser | ~100 |
| `app/services/ingestion/freedom.py` | Replace NotImplementedError stubs with SDK calls | ~90 |
| `app/routers/sync.py` | Add GET /sync/ibkr form route; rewrite POST /sync/ibkr + /sync/freedom | ~60 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Upload a real IBKR Flex XML → positions + transactions appear in `instruments`, `positions`, `transactions` tables
- [ ] Upload same file twice → row counts unchanged (idempotency)
- [ ] POST /sync/freedom (with valid .env keys) → Freedom positions appear in DB
- [ ] Failed upload (wrong file format) → error flash, no DB change, no 500

### Testing Requirements
- [ ] `test_ibkr_parser.py` passes: correct field mapping from fixture XML
- [ ] `test_sync_routes.py` passes: upload fixture → rows in DB; upload again → no duplicates
- [ ] `ruff check app/ tests/` → 0 errors

### Non-Functional Requirements
- [ ] Freedom API call has explicit timeout (30s) — no hung requests
- [ ] Broker response payload not logged (financial data / PII — CONSIDERATIONS.md rule)
- [ ] Sync flash message includes row count (user feedback)

### Quality Gates
- [ ] All files ASCII-encoded
- [ ] Unix LF line endings
- [ ] Code follows CONVENTIONS.md (upsert pattern, no commit in service functions)

---

## 8. Implementation Notes

### Key Considerations
- IBKR Flex XML format: root `<FlexQueryResponse>`, child `<FlexStatements>`, then
  `<FlexStatement>` with `<OpenPositions>` and `<Trades>` sections. Each row is an XML element
  with attributes (not child elements). Parse with `ElementTree.iter()`.
- Freedom `tradernet` SDK: exact method names need verification against package source.
  Common pattern: `api.get_portfolio()` for positions, `api.get_trade_history(from, to)` for
  transactions. If SDK methods differ, adapt accordingly — do not guess.
- `ibkr_txn_id` UNIQUE: IBKR Flex `tradeID` attribute maps to this column. Used as conflict key
  for upsert. Freedom transactions: use `<broker>_<settlement_date>_<ticker>_<qty>` as synthetic
  key until a stable Freedom transaction ID is confirmed from SDK.
- Instrument auto-populate: check `SELECT id FROM instruments WHERE ticker = ?` before insert.
  If missing, create stub row. Do not call yfinance here (Phase 02 fills in metadata).

### Potential Challenges
- **tradernet SDK API discovery**: SDK may not have the expected method names. Mitigation: run
  `python -c "import tradernet; help(tradernet)"` in Docker to discover real API surface before
  implementing.
- **IBKR Flex XML schema variations**: different account types may have slightly different
  element names. Mitigation: use `element.get("attr", None)` with safe defaults, log warnings
  for missing fields rather than raising.
- **Freedom API rate limits / auth errors**: if `.env` keys are missing or wrong, catch exception
  and flash clear error. Do not let auth errors become 500s.

### Relevant Considerations
- **[External Dependencies]** Freedom Finance TraderNet API: perpetual key pair in `.env`.
  Auth: `TraderNetAPI(public_key, private_key, login, passwd)`. Discover real method names
  before implementing.
- **[External Dependencies]** IBKR CP Gateway not feasible headless on VPS. Flex Query XML
  upload is the correct approach for this phase.
- **[Security]** Broker API responses must not be logged. Log only summaries
  ("synced 12 positions from Freedom").
- **[Architecture]** Never call `db.commit()` inside service functions — commit in router only.

### Behavioral Quality Focus
Checklist active: Yes
Top behavioral risks for this session:
- File upload handler: must validate MIME type + XML structure before processing — invalid file
  must return 422 flash, not 500
- Upsert write path: must be atomic (all-or-none) — partial insert on crash must not corrupt DB
- Freedom API call: must timeout after 30s — never block indefinitely on external service

---

## 9. Testing Strategy

### Unit Tests
- `test_ibkr_parser.py`: parse `tests/fixtures/ibkr_flex_sample.xml`, assert correct number of
  `PositionRow` and `TransactionRow` objects, check key field values (ticker, qty, cost_basis)
- `test_freedom_adapter.py`: mock `tradernet.TraderNetAPI`, assert `normalize_freedom_position()`
  returns correctly typed `PositionRow` from a known mock payload

### Integration Tests
- `test_sync_routes.py`: use `TestClient`, POST to `/sync/ibkr` with fixture XML file, query
  test DB, assert rows exist; POST again, assert row counts unchanged (idempotency)

### Manual Testing
- Upload a real IBKR Flex XML (user obtains from IBKR portal) → verify positions table
- Check flash message shows correct counts
- Test with corrupted XML → verify error flash, no traceback exposed to user

### Edge Cases
- Empty XML file (0 positions, 0 transactions) → flash "Synced 0 positions, 0 transactions"
- XML with unknown element structure → warning log, best-effort parse, no crash
- Freedom API auth failure → flash error "Freedom Finance auth failed: <reason>" (no traceback)
- Duplicate transaction ID in same upload → upsert handles silently, no IntegrityError

---

## 10. Dependencies

### External Libraries
- `tradernet`: Freedom Finance SDK (already in pyproject.toml)
- `sqlalchemy.dialects.postgresql`: `insert` for upsert (already in pyproject.toml)
- `xml.etree.ElementTree`: stdlib, no install needed

### Other Sessions
- **Depends on**: `phase00-session01-skeleton` (models, DB, auth, router stubs)
- **Depended by**: `phase01-session02-prices` (needs `instruments` table populated with tickers)

---

## Next Steps

Run `/implement` to begin AI-led implementation.
