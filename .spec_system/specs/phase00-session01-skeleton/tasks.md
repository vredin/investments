# Task Checklist

**Session ID**: `phase00-session01-skeleton`
**Total Tasks**: 22
**Estimated Duration**: 3-4 hours
**Created**: 2026-05-04

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0001]` = Session reference (phase 00, session 01)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 3 | 0 | 3 |
| Foundation | 6 | 0 | 6 |
| Implementation | 9 | 0 | 9 |
| Testing | 4 | 0 | 4 |
| **Total** | **22** | **0** | **22** |

---

## Setup (3 tasks)

- [ ] T001 [S0001] Create `pyproject.toml` with full dependency stack (fastapi, uvicorn, sqlalchemy, psycopg2-binary, alembic, jinja2, apscheduler, httpx, anthropic, python-telegram-bot, itsdangerous, bcrypt, cryptography, python-dotenv, python-multipart, pgvector, pandas, quantstats, pandas-ta, pypdf, beautifulsoup4, yfinance, tradernet, sentence-transformers, pytest, ruff) and project entry point
- [ ] T002 [S0001] Create `.env.example` with all required variables: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD_HASH`, `ANTHROPIC_API_KEY`, `FREEDOM_PUBLIC_KEY`, `FREEDOM_PRIVATE_KEY`, `FREEDOM_LOGIN`, `FREEDOM_PASSWORD`; each with inline comment explaining source
- [ ] T003 [S0001] Create `docker-compose.yml` with `db` service (`pgvector/pgvector:pg16`, named volume, healthcheck) + `app` service (build from Dockerfile, `env_file: .env`, depends_on db with healthcheck condition, Traefik labels for subdomain + TLS); and `Dockerfile` (Python 3.12-slim, uv install deps, `uvicorn app.main:app --host 0.0.0.0 --port 8000` entrypoint)

---

## Foundation (6 tasks)

- [ ] T004 [S0001] Create `app/config.py` — `Settings(BaseSettings)` with all env vars typed; `get_settings()` with `@lru_cache`; raise clear `ValueError` if `DATABASE_URL` or `SECRET_KEY` missing at startup
- [ ] T005 [S0001] Create `app/db.py` — `create_engine(settings.DATABASE_URL, pool_pre_ping=True)`, `SessionLocal = sessionmaker(...)`, `Base = declarative_base()`, `get_db()` FastAPI dependency (yield + close pattern)
- [ ] T006 [S0001] Create `app/models.py` — all 10 SQLAlchemy models: `Config`, `Instrument`, `Price`, `Position`, `Transaction` (with `ibkr_txn_id` UniqueConstraint), `ExternalBalance`, `ChannelSignal` (with `Vector(1024)` embedding), `Recommendation`, `ProgressSnapshot`, `CourseChunk` (with `Vector(1024)` embedding); import `Vector` from `pgvector.sqlalchemy`
- [ ] T007 [S0001] Set up Alembic: `alembic init migrations`, configure `migrations/env.py` to import `Base` from `app.models` and use `DATABASE_URL` from settings; create `migrations/versions/0001_initial.py` with `upgrade()`: `CREATE EXTENSION IF NOT EXISTS vector`, then `Base.metadata.create_all` equivalent DDL for all 10 tables; `downgrade()` drops all tables + extension
- [ ] T008 [S0001] Create `app/auth.py` — `verify_password(plain: str, hashed: str) -> bool` (bcrypt); `create_session_cookie(response)` sets signed itsdangerous cookie; `clear_session_cookie(response)`; `login_required` FastAPI dependency: reads cookie, verifies signature + max_age (12h), redirects to `/login` if invalid
- [ ] T009 [S0001] [P] Create all stub service files with docstrings only: `app/services/llm.py`, `prices.py`, `portfolio.py`, `recommender.py`, `monitor.py`, `backup.py`, `telegram.py`, `ingestion/__init__.py`, `ingestion/ibkr.py`, `ingestion/freedom.py`, `ingestion/broker.py`, `ingestion/course.py`, `ingestion/channels.py`

---

## Implementation (9 tasks)

- [ ] T010 [S0001] Create `app/routers/auth_router.py` — `GET /login` returns `login.html` (redirect to `/` if already authenticated); `POST /login` reads `password` from form, calls `verify_password()` against `settings.ADMIN_PASSWORD_HASH`, sets session cookie and redirects to `/` on success, returns login page with error on failure (with duplicate-submit prevention via redirect-after-POST pattern); `POST /logout` clears cookie + redirects to `/login`
- [ ] T011 [S0001] Create `app/routers/dashboard.py` — `GET /` with `login_required` dependency, returns `dashboard.html` with empty context `{}`; `GET /health` returns `{"status": "ok"}` (no auth, for Docker healthcheck)
- [ ] T012 [S0001] [P] Create stub routers: `app/routers/sync.py` (POST /sync/ibkr, /sync/freedom, /sync/prices — each returns flash "Not implemented yet" + redirect to /); `app/routers/recommend.py` (GET/POST /recommend); `app/routers/report.py` (GET /report/{month}); `app/routers/settings.py` (GET/POST /settings); `app/routers/admin.py` (POST /admin/ingest-course, /admin/ingest-channels)
- [ ] T013 [S0001] Create `app/scheduler.py` — `BackgroundScheduler` instance; register 3 stub jobs: `sync_prices_daily` (cron: daily 23:00), `ingest_channels_weekly` (cron: Sunday 22:00), `backup_monthly` (cron: 1st of month 02:00); each job logs "Job X triggered, not yet implemented"
- [ ] T014 [S0001] Create `app/main.py` — `FastAPI(lifespan=lifespan)` app; `lifespan` async context manager starts/stops APScheduler; include all routers with prefixes; mount `app/static/` as StaticFiles; `Jinja2Templates(directory="app/templates")`; add flash message middleware helper
- [ ] T015 [S0001] Create `app/templates/base.html` — full HTML layout: `<head>` with Chart.js 4.4 CDN + Flatpickr CDN; `<nav>` with links to Dashboard, Recommend, Report, Settings + Logout button; flash message block (success/error styling via inline CSS); `{% block content %}{% endblock %}`
- [ ] T016 [S0001] Create `app/templates/login.html` — extends base.html (no nav); centered card with username/password form fields (POST /login); error message display; inline CSS for card layout
- [ ] T017 [S0001] Create `app/templates/dashboard.html` — extends base.html; 4 placeholder sections with inline CSS grid: "Portfolio Allocation" (Chart.js canvas placeholder), "Performance", "Progress to Goal", "Last Recommendation"; each shows "Data will appear after first sync"
- [ ] T018 [S0001] Create `app/__init__.py` and `app/routers/__init__.py` and `app/services/__init__.py` (empty package markers); create `app/static/` directory with `.gitkeep`

---

## Testing (4 tasks)

- [ ] T019 [S0001] [P] Create `tests/conftest.py` — `engine` fixture creates test DB (separate `investments_test` DB or `DATABASE_URL` with `_test` suffix from env); `db_session` fixture runs `Base.metadata.create_all`, yields session, runs `Base.metadata.drop_all`; `client` fixture returns `TestClient(app)` with overridden `get_db` dependency
- [ ] T020 [S0001] [P] Write `tests/test_models.py` — verify all 10 table names exist after `create_all`; verify `ibkr_txn_id` UNIQUE constraint raises `IntegrityError` on duplicate; verify `course_chunks` has `embedding` column; verify `alembic upgrade head` applies cleanly on fresh DB
- [ ] T021 [S0001] Run `uv run pytest tests/ -v` — all tests pass; run `ruff check app/ tests/` — 0 errors
- [ ] T022 [S0001] Deploy to VPS: `git push`, `docker compose pull && docker compose up -d`; run `docker compose exec app alembic upgrade head`; navigate to subdomain, verify login page loads, log in, verify dashboard renders without errors

---

## Completion Checklist

Before marking session complete:

- [ ] All 22 tasks marked `[x]`
- [ ] `docker compose up` starts cleanly on VPS
- [ ] Login + session works end-to-end in browser
- [ ] `alembic upgrade head` succeeds on real PostgreSQL
- [ ] `pytest tests/ -v` passes (0 failures)
- [ ] `ruff check app/ tests/` passes (0 errors)
- [ ] `.env` not in git; verified with `git status`
- [ ] No passwords or API keys in any committed file
- [ ] Ready for `/validate`

---

## Next Steps

Run `/implement` to begin AI-led implementation.
