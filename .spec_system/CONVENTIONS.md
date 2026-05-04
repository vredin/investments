# CONVENTIONS.md

## Guiding Principles

- Optimize for readability over cleverness
- Code is written once, read many times (by future self, possibly years later)
- Consistency beats personal preference
- When writing code: Make NO assumptions. Do not be lazy. Pattern match precisely. Validate systematically.
- This tool must survive 3-5 years without modification; design accordingly

## Naming

- Be descriptive: `calculate_allocation_deviation` > `calc_dev` > `compute`
- Booleans read as questions: `is_rebalance_needed`, `has_positions`, `should_split_dca`
- Functions describe actions: `sync_ibkr_positions`, `generate_recommendation`, `compute_twrr`
- Match domain language: `ticker`, `position`, `contribution`, `drawdown`, `rebalance`
- URL routes: kebab-case (`/sync-ibkr`, `/ingest-course`)
- SQLAlchemy models: PascalCase (`Instrument`, `Transaction`, `Recommendation`)
- DB tables: snake_case plural (`instruments`, `transactions`, `recommendations`)

## Project Structure

```
investments-assistant/
  app/
    main.py               # FastAPI app, router registration, lifespan (APScheduler)
    auth.py               # login/logout, itsdangerous session, bcrypt
    db.py                 # SQLAlchemy engine + get_db() session dependency
    models.py             # All SQLAlchemy ORM models (single file, all tables)
    config.py             # pydantic-settings: reads .env, exposes Settings singleton
    scheduler.py          # APScheduler instance + job registration stubs
    routers/
      dashboard.py        # GET / -> dashboard.html
      sync.py             # POST /sync/ibkr, /sync/freedom, /sync/prices
      recommend.py        # GET/POST /recommend
      report.py           # GET /report/{month}
      settings.py         # GET/POST /settings
      admin.py            # POST /admin/ingest-course, /admin/ingest-channels
    services/
      ingestion/
        ibkr.py           # IBKR adapter (httpx)
        freedom.py        # Freedom TraderNet SDK adapter
        broker.py         # Unified broker interface (normalize to common schema)
        course.py         # PDF -> chunks -> pgvector
        channels.py       # Telegram HTML -> channel_signals
      llm.py              # Claude adapter (model selection, prompt caching, disclaimer)
      prices.py           # yfinance price cache
      portfolio.py        # allocation, TWRR, IRR, drawdown
      recommender.py      # Subsystem A: buy plan algorithm
      monitor.py          # Subsystem B: report, rebalancing
      backup.py           # pg_dump + tar
      telegram.py         # Telegram bot: send message, send report
    templates/
      base.html           # Base layout: nav, Chart.js CDN, Flatpickr CDN, session flash
      login.html
      dashboard.html
      recommend.html
      report.html
      settings.html
    static/               # Empty - all assets via CDN
  migrations/
    env.py
    versions/
  tests/
    conftest.py           # pytest fixtures: test DB session, test client
    test_models.py
    test_portfolio.py
    test_recommender.py
  docker-compose.yml
  Dockerfile
  .env.example            # Committed template; .env on server NOT committed
  alembic.ini
  pyproject.toml
```

## FastAPI Conventions

- Routers use `APIRouter` with `prefix` and `tags`
- All template routes: `response_class=HTMLResponse`, inject `request: Request`
- Session auth: check `request.session.get("authenticated")` in every protected route
- Never return raw DB objects to templates — convert to dicts or Pydantic response models
- Action routes (sync, ingest) return redirect to referrer with flash message on success/error

## SQLAlchemy Conventions

- Single `models.py` for all models (project is small, keep it navigable)
- All models inherit from `Base = declarative_base()`
- Use `get_db()` FastAPI dependency for session injection — never create sessions inside service functions
- Service functions signature: `def sync_ibkr_positions(db: Session) -> int` (return count of synced rows)
- Upsert pattern: `INSERT ... ON CONFLICT DO UPDATE` via `insert().on_conflict_do_update()`
- Never use `db.commit()` inside service functions — commit in the router after service call

## Alembic Conventions

- Each migration: one logical change (e.g., "add embedding column to channel_signals")
- Never modify a migration already applied to the server
- Migration file naming: auto-generated hash prefix is fine
- Always test `alembic downgrade -1` works before deploying

## Templates Conventions

- All pages extend `base.html` via `{% extends "base.html" %}`
- `base.html` loads Chart.js 4.4 and Flatpickr via CDN `<script>` tags
- Flash messages: stored in session as `{"flash": {"type": "success|error", "msg": "..."}}`
- Forms: `method="POST"`, include CSRF token via itsdangerous if needed
- Charts: initialized in `<script>` block at bottom of each template, data passed via `data-*` attributes or inline JSON

## Security Conventions

- `.env` file: never committed; `.env.example` always committed
- `ADMIN_PASSWORD_HASH`: bcrypt hash stored in `.env`, never plaintext
- Session secret: `SECRET_KEY` in `.env`, minimum 32 random bytes
- All broker API keys in `.env`: `FREEDOM_PUBLIC_KEY`, `FREEDOM_PRIVATE_KEY`, `FREEDOM_LOGIN`, `FREEDOM_PASSWORD`, `ANTHROPIC_API_KEY`
- Every LLM output shown to user includes disclaimer: "Not investment advice. For informational purposes only."
- Never log API keys, passwords, or broker response payloads — log only summaries

## Database Layer

### Connection
- Engine: `create_engine(settings.DATABASE_URL, pool_pre_ping=True)`
- Session: `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- Dependency: `def get_db(): db = SessionLocal(); try: yield db; finally: db.close()`

### Migrations
- Tool: Alembic
- Location: `migrations/versions/`
- CRITICAL: Never modify a migration already applied to production
- Every migration must have a `downgrade()` function

### pgvector
- Extension: `CREATE EXTENSION IF NOT EXISTS vector` in first migration
- Column type: `Vector(1024)` for BGE-M3 embeddings (1024 dimensions)
- Index: `CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops)` after bulk insert
- Tables with embeddings: `course_chunks`, `channel_signals`

### Upsert pattern (idempotent sync)
```python
from sqlalchemy.dialects.postgresql import insert
stmt = insert(Price).values(rows).on_conflict_do_update(
    index_elements=["ticker", "date"],
    set_={"close": insert_stmt.excluded.close}
)
db.execute(stmt)
```

## Testing

- Test DB: separate PostgreSQL DB named `investments_test` or use pytest-postgresql
- `conftest.py`: fixture creates all tables, yields session, drops all tables on teardown
- Test behavior, not implementation details
- Critical path tests: allocation deviation, TWRR formula, DCA split, upsert idempotency
- Never mock the database — use a real test DB (lesson from CONSIDERATIONS.md)

## Docker Conventions

- `docker-compose.yml`: services `db` (postgres:16) + `app`
- `app` depends_on `db` with healthcheck
- Volumes: `postgres_data` for DB persistence
- `.env` file mounted via `env_file: .env` — never hardcoded in compose file
- Traefik labels on `app` service for subdomain routing + TLS

## APScheduler Conventions

- Scheduler started in FastAPI `lifespan` context manager
- Jobs defined in `scheduler.py`, imported in `main.py`
- All jobs call service functions, never contain business logic themselves
- Job IDs: `"sync_prices_daily"`, `"ingest_channels_weekly"`, `"backup_monthly"`

## When In Doubt

- Ask future self: "Will I understand this in 3 years without the commit history?"
- Ship the MVP (5 phases), then extend only if actively used for 3+ months
- Every dollar spent on infrastructure is a dollar not invested
