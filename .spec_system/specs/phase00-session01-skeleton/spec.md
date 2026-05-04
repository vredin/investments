# Session Specification

**Session ID**: `phase00-session01-skeleton`
**Phase**: 00 - Foundation
**Status**: Not Started
**Created**: 2026-05-04

---

## 1. Session Overview

This session bootstraps the entire project: Docker Compose environment, FastAPI app skeleton, PostgreSQL + pgvector schema via SQLAlchemy + Alembic, single-user auth, and APScheduler wiring. After this session the app must start, serve a login page, accept credentials, and show a blank dashboard — with all future routes registered as stubs.

The session deliberately avoids implementing real data logic. Every service file created here is a stub that future sessions fill in. The goal is a running container with correct structure, working auth, and a verified DB schema.

Platform shift from the original design: VPS + Docker (not macOS local), PostgreSQL + pgvector (not SQLite + LanceDB), python-dotenv (not macOS Keychain), APScheduler (not launchd). The stack matches the user's existing proven setup on another project.

---

## 2. Objectives

1. `docker compose up` starts PostgreSQL (with pgvector) + app; app is reachable at configured subdomain
2. Login page with bcrypt password check and itsdangerous signed session cookie
3. All 10 SQLAlchemy models defined + Alembic initial migration applied (including pgvector extension)
4. APScheduler wired into FastAPI lifespan with 3 stub jobs (prices, channels, backup)
5. All 6 route files registered (dashboard, sync, recommend, report, settings, admin) — stubs only
6. Base Jinja2 template with Chart.js 4.4 + Flatpickr CDN links

---

## 3. Prerequisites

### Required Sessions
- None (first session)

### Required Tools/Knowledge
- Docker + Docker Compose installed on VPS
- Traefik running on VPS with configured subdomain
- Python 3.12 + uv installed locally for development
- PostgreSQL 16 with pgvector 0.7+ available via Docker image `pgvector/pgvector:pg16`

### Environment Requirements
- VPS with Docker + Traefik already configured
- `.env` file created from `.env.example` before `docker compose up`
- `ADMIN_PASSWORD_HASH` generated via `python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"`

---

## 4. Scope

### In Scope (MVP)
- `docker-compose.yml` with `db` (pgvector/pgvector:pg16) + `app` services + Traefik labels
- `Dockerfile` for app: Python 3.12 slim, uv install, uvicorn entrypoint
- `.env.example` with all required variables (no real values)
- `pyproject.toml` with all deps declared (full stack from PRD)
- `app/config.py` — pydantic-settings `Settings` class reading from .env
- `app/db.py` — SQLAlchemy engine + `SessionLocal` + `get_db()` dependency
- `app/models.py` — all 10 SQLAlchemy models with pgvector `Vector(1024)` columns
- `migrations/` — Alembic setup + `0001_initial.py` migration (CREATE EXTENSION vector + all tables)
- `app/auth.py` — `verify_password()`, `login_required()` dependency, `create_session()`, `clear_session()`
- `app/main.py` — FastAPI app, all routers registered, lifespan with APScheduler start/stop
- `app/scheduler.py` — APScheduler instance + 3 stub jobs registered
- `app/routers/dashboard.py` — `GET /` returns `dashboard.html` (login required)
- `app/routers/auth_router.py` — `GET /login`, `POST /login`, `POST /logout`
- `app/routers/sync.py`, `recommend.py`, `report.py`, `settings.py`, `admin.py` — stub routes
- `app/templates/base.html` — layout with nav, Chart.js 4.4 CDN, Flatpickr CDN, flash messages
- `app/templates/login.html` — login form
- `app/templates/dashboard.html` — blank dashboard with placeholder sections
- All `app/services/` files as stubs with docstrings

### Out of Scope (Deferred)
- Any real broker API calls — *Phase 01*
- Real dashboard data (charts, portfolio values) — *Phase 02-03*
- Telegram bot sending messages — *Phase 02*
- APScheduler jobs doing real work — *Phase 04*

---

## 5. Technical Approach

### Architecture

Single Docker Compose stack: `db` container runs PostgreSQL 16 with pgvector extension; `app` container runs FastAPI + Uvicorn. Traefik handles TLS termination and subdomain routing via container labels.

FastAPI lifespan manages APScheduler lifecycle. All routes are protected by `login_required` dependency except `/login`. Session is an itsdangerous `TimestampSigner` cookie — single-user, no DB sessions table needed.

### Design Patterns
- **Dependency injection**: `get_db()` yields SQLAlchemy session; `login_required` checks session cookie
- **Stub pattern**: all service functions raise `NotImplementedError` with phase reference
- **Settings singleton**: `get_settings()` is `lru_cache`-decorated, reads `.env` once at startup
- **Upsert-ready**: all models designed for `INSERT ... ON CONFLICT DO UPDATE` from day one

### Technology Stack (versions from PRD)
- FastAPI >=0.115, Uvicorn >=0.30
- SQLAlchemy >=2.0 (sync), psycopg2-binary >=2.9
- Alembic >=1.13
- Jinja2 >=3.1, python-multipart >=0.0.9
- APScheduler >=3.10
- itsdangerous >=2.1, bcrypt >=4.0
- python-dotenv >=1.0
- pgvector Python package (for `Vector` column type in SQLAlchemy)

---

## 6. Deliverables

### Files to Create

| File | Purpose | Est. Lines |
|------|---------|------------|
| `docker-compose.yml` | PostgreSQL + app services + Traefik labels | ~55 |
| `Dockerfile` | Python 3.12 slim app image | ~25 |
| `.env.example` | All required env vars, no real values | ~30 |
| `pyproject.toml` | All deps + entry point | ~65 |
| `alembic.ini` | Alembic config pointing to migrations/ | ~15 |
| `app/__init__.py` | Package marker | ~1 |
| `app/config.py` | pydantic-settings Settings class | ~45 |
| `app/db.py` | Engine + SessionLocal + get_db() | ~30 |
| `app/models.py` | All 10 SQLAlchemy models | ~180 |
| `app/auth.py` | bcrypt verify + session helpers + dependency | ~60 |
| `app/main.py` | FastAPI app + routers + lifespan | ~55 |
| `app/scheduler.py` | APScheduler + 3 stub jobs | ~40 |
| `app/routers/auth_router.py` | GET/POST /login, POST /logout | ~50 |
| `app/routers/dashboard.py` | GET / -> dashboard.html | ~20 |
| `app/routers/sync.py` | POST /sync/* stubs | ~30 |
| `app/routers/recommend.py` | GET/POST /recommend stub | ~20 |
| `app/routers/report.py` | GET /report/{month} stub | ~20 |
| `app/routers/settings.py` | GET/POST /settings stub | ~20 |
| `app/routers/admin.py` | POST /admin/* stubs | ~20 |
| `app/templates/base.html` | Layout + CDN links + nav + flash | ~60 |
| `app/templates/login.html` | Login form | ~35 |
| `app/templates/dashboard.html` | Blank dashboard with sections | ~40 |
| `migrations/env.py` | Alembic env with SQLAlchemy models | ~50 |
| `migrations/versions/0001_initial.py` | CREATE EXTENSION vector + all tables | ~120 |
| `app/services/llm.py` stub | Claude adapter stub | ~20 |
| `app/services/portfolio.py` stub | Portfolio analytics stub | ~10 |
| `app/services/recommender.py` stub | Recommender stub | ~10 |
| `app/services/monitor.py` stub | Monitor stub | ~10 |
| `app/services/backup.py` stub | Backup stub | ~10 |
| `app/services/prices.py` stub | Prices stub | ~10 |
| `app/services/telegram.py` stub | Telegram stub | ~10 |
| `app/services/ingestion/__init__.py` | Package marker | ~1 |
| `app/services/ingestion/ibkr.py` stub | IBKR adapter stub | ~10 |
| `app/services/ingestion/freedom.py` stub | Freedom adapter stub | ~10 |
| `app/services/ingestion/broker.py` stub | Unified broker stub | ~10 |
| `app/services/ingestion/course.py` stub | PDF ingestion stub | ~10 |
| `app/services/ingestion/channels.py` stub | Telegram ingest stub | ~10 |
| `tests/__init__.py` | Test package | ~1 |
| `tests/conftest.py` | Test DB session + TestClient fixture | ~40 |
| `tests/test_models.py` | Schema verification tests | ~50 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] `docker compose up` starts without errors; PostgreSQL healthcheck passes
- [ ] `GET /login` returns 200 with login form
- [ ] `POST /login` with correct password sets session cookie and redirects to `/`
- [ ] `POST /login` with wrong password returns login page with error message
- [ ] `GET /` without session redirects to `/login`
- [ ] `GET /` with valid session returns 200 dashboard page
- [ ] `POST /logout` clears session and redirects to `/login`
- [ ] `alembic upgrade head` applies migration without errors on fresh DB
- [ ] All 10 tables exist in PostgreSQL after migration
- [ ] pgvector extension enabled; `Vector(1024)` columns exist on `course_chunks` and `channel_signals`

### Testing Requirements
- [ ] `pytest tests/ -v` passes with 0 failures
- [ ] All 10 tables verified in `test_models.py`
- [ ] Login flow tested (correct + wrong password)

### Non-Functional Requirements
- [ ] App container starts in < 30 seconds
- [ ] No secrets in any committed file

### Quality Gates
- [ ] `.env` not in git; `.env.example` is committed
- [ ] `ruff check app/ tests/` passes with 0 errors
- [ ] All files ASCII-encoded, Unix LF line endings

---

## 8. Implementation Notes

### Passwords — user action required
The `ADMIN_PASSWORD_HASH` in `.env` is generated by the user before first run:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```
This hash goes into `.env`. Never send passwords through chat or commit them.

### pgvector setup
First Alembic migration must run `CREATE EXTENSION IF NOT EXISTS vector` before any table DDL. The `pgvector/pgvector:pg16` Docker image has the extension available but it must be activated per-database.

### itsdangerous session
Single-user: no DB sessions table. Session = signed cookie containing `{"authenticated": true}`. `TimestampSigner` with `SECRET_KEY` from `.env`. Max age: 12 hours (configurable).

### APScheduler in FastAPI lifespan
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()
```

### Potential Challenges
- **pgvector on first migration**: if `CREATE EXTENSION` fails, user needs `superuser` PostgreSQL role — the `pgvector/pgvector:pg16` image default user `postgres` has this, but custom users may not
- **Alembic autogenerate with Vector columns**: pgvector's `Vector` type may not autogenerate cleanly — write migration DDL manually for vector columns

### Relevant Considerations
- **No Streamlit, no Django**: user has explicit bad experience with both — do not suggest them as alternatives for any UI work
- **Single user, simple auth**: no user table, no registration, no password reset — bcrypt hash in .env is sufficient and maintainable for 20 years
- **VPS + Docker**: all paths, file mounts, and cron schedules assume Linux container environment, not macOS

---

## 9. Testing Strategy

### Unit Tests
- `test_models.py`: apply migration to test DB, verify all 10 table names, verify `ibkr_txn_id` UNIQUE, verify `Vector(1024)` column exists on `course_chunks`
- `test_auth.py`: verify `verify_password()` returns True/False correctly; verify session cookie created/cleared

### Integration Tests
- `TestClient` from fastapi.testclient: GET /login returns 200; POST /login with correct hash redirects to /; GET / without session returns 302 to /login

### Manual Testing
- `docker compose up` on VPS, navigate to subdomain, log in, verify dashboard loads

---

## 10. Dependencies

### External Libraries
See pyproject.toml — full stack declared upfront

### Other Sessions
- **Depends on**: none
- **Depended by**: all subsequent sessions

---

## Next Steps

Run `/implement` to begin AI-led implementation.
