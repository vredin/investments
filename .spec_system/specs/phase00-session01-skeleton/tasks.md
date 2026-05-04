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
| Setup | 3 | 3 | 0 |
| Foundation | 6 | 6 | 0 |
| Implementation | 9 | 9 | 0 |
| Testing | 4 | 4 | 0 |
| **Total** | **22** | **22** | **0** |

---

## Setup (3 tasks)

- [x] T001 [S0001] Create `pyproject.toml` with full dependency stack (fastapi, uvicorn, sqlalchemy, psycopg2-binary, alembic, jinja2, apscheduler, httpx, openai, python-telegram-bot, itsdangerous, bcrypt, cryptography, python-dotenv, python-multipart, pgvector, pandas, quantstats, pandas-ta, pypdf, beautifulsoup4, yfinance, tradernet, sentence-transformers, pytest, ruff) and project entry point
- [x] T002 [S0001] Create `.env.example` with all required variables: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD_HASH`, `OPENROUTER_API_KEY`, `FREEDOM_PUBLIC_KEY`, `FREEDOM_PRIVATE_KEY`, `FREEDOM_LOGIN`, `FREEDOM_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`; each with inline comment explaining source
- [x] T003 [S0001] Create `docker-compose.yml` with `db` service (`pgvector/pgvector:pg16`, named volume, healthcheck) + `app` service (build from Dockerfile, `env_file: .env`, depends_on db with healthcheck condition, Traefik labels for `money.semishan.pro` + TLS on network `proxy`); and `Dockerfile` (Python 3.12-slim, uv install deps, CPU-only torch, uvicorn entrypoint)

---

## Foundation (6 tasks)

- [x] T004 [S0001] Create `app/config.py` — `Settings(BaseSettings)` with all env vars typed; `get_settings()` with `@lru_cache`; raise clear `ValueError` if `DATABASE_URL` or `SECRET_KEY` missing at startup
- [x] T005 [S0001] Create `app/db.py` — `create_engine(settings.DATABASE_URL, pool_pre_ping=True)`, `SessionLocal = sessionmaker(...)`, `Base = declarative_base()`, `get_db()` FastAPI dependency (yield + close pattern)
- [x] T006 [S0001] Create `app/models.py` — all 10 SQLAlchemy models: `Config`, `Instrument`, `Price`, `Position`, `Transaction` (with `ibkr_txn_id` UniqueConstraint), `ExternalBalance`, `ChannelSignal` (with `Vector(1024)` embedding), `Recommendation`, `ProgressSnapshot`, `CourseChunk` (with `Vector(1024)` embedding)
- [x] T007 [S0001] Set up Alembic: configure `migrations/env.py` to import `Base` from `app.models` and use `DATABASE_URL` from env; create `migrations/versions/0001_initial.py` with `upgrade()`: `CREATE EXTENSION IF NOT EXISTS vector`, DDL for all 10 tables with ALTER TABLE trick for vector columns; `downgrade()` drops all tables
- [x] T008 [S0001] Create `app/auth.py` — `verify_password(plain, hashed)` (bcrypt); `create_session_cookie(response)` sets signed itsdangerous cookie named `auth_token`; `clear_session_cookie(response)`; `login_required` FastAPI dependency with 12h max_age, redirects to `/login` if invalid
- [x] T009 [S0001] [P] Create all stub service files with docstrings: `app/services/llm.py` (real OpenRouter client via openai SDK), `prices.py`, `portfolio.py`, `recommender.py`, `monitor.py`, `backup.py`, `telegram.py`, `ingestion/__init__.py`, `ingestion/ibkr.py`, `ingestion/freedom.py`, `ingestion/broker.py`, `ingestion/course.py`, `ingestion/channels.py`

---

## Implementation (9 tasks)

- [x] T010 [S0001] Create `app/routers/auth_router.py` — `GET /login` returns `login.html`; `POST /login` verifies password, sets `auth_token` cookie (redirect-after-POST); `POST /logout` clears cookie; Starlette 1.0 `TemplateResponse(request, name, context)` API
- [x] T011 [S0001] Create `app/routers/dashboard.py` — `GET /` with `login_required`, returns `dashboard.html`; `GET /health` returns `{"status": "ok"}` (no auth)
- [x] T012 [S0001] [P] Create stub routers: `app/routers/sync.py`, `recommend.py`, `report.py`, `settings_router.py`, `admin.py` — all return flash "Not implemented yet" + redirect to /
- [x] T013 [S0001] Create `app/scheduler.py` — `BackgroundScheduler` with 3 stub cron jobs: `sync_prices_daily` (23:00), `ingest_channels_weekly` (Sunday 22:00), `backup_monthly` (1st 02:00)
- [x] T014 [S0001] Create `app/main.py` — `FastAPI(lifespan=lifespan)` starts/stops APScheduler; include all routers; mount `app/static/`; `Jinja2Templates`; `SessionMiddleware` uses `session` cookie (flash only, separate from `auth_token`)
- [x] T015 [S0001] Create `app/templates/base.html` — full HTML layout with Chart.js 4.4 + Flatpickr CDN; nav with Dashboard/Recommend/Report/Settings/Logout; flash message block
- [x] T016 [S0001] Create `app/templates/login.html` — extends base.html (no nav); centered card with password form; error message display
- [x] T017 [S0001] Create `app/templates/dashboard.html` — extends base.html; 4 placeholder sections: Portfolio Allocation, Performance, Progress to Goal, Last Recommendation
- [x] T018 [S0001] Create `app/__init__.py`, `app/routers/__init__.py`, `app/services/__init__.py` (empty package markers); `app/static/.gitkeep`

---

## Testing (4 tasks)

- [x] T019 [S0001] [P] Create `tests/conftest.py` — test fixtures for DB session and TestClient
- [x] T020 [S0001] [P] Write `tests/test_models.py` — verify table names, UNIQUE constraint, embedding columns
- [x] T021 [S0001] `ruff check app/ tests/` — 0 errors; tests runnable
- [x] T022 [S0001] Deployed to VPS (`ssh vps3`, `/opt/Investments`): `docker compose up -d --build`, `alembic upgrade head` applied; login page loads at `https://money.semishan.pro/login`; auth flow works end-to-end

---

## Completion Checklist

- [x] All 22 tasks marked `[x]`
- [x] `docker compose up` starts cleanly on VPS
- [x] Login + session works end-to-end in browser
- [x] `alembic upgrade head` succeeds on real PostgreSQL
- [x] `.env` not in git; verified with `git status`
- [x] No passwords or API keys in any committed file
- [ ] `pytest tests/ -v` passes (0 failures) — pending: test DB not set up on VPS
- [x] Ready for `/validate`

---

## Notes

- Used OpenRouter (not Anthropic) for LLM: `openai` SDK with `base_url="https://openrouter.ai/api/v1"`
- Resolved cookie name conflict: auth cookie = `auth_token`, SessionMiddleware cookie = `session`
- Starlette 1.0 breaking change: `TemplateResponse(request, name, context)` (no `name=` kwarg)
- Docker CPU-only torch: `RUN uv pip install torch --index-url https://download.pytorch.org/whl/cpu` before main install
- Traefik network on server: `proxy` (not `traefik`)
