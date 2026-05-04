# Investment Assistant - Product Requirements Document

## Overview

Personal investment assistant for retirement savings accumulation over a 20-year horizon (age 45 to 65). Monthly contributions $200-1000 via Interactive Brokers Europe and Freedom Finance (freedom24.com). Target: ~$1.3M nominal capital by 2046 to sustain $2000/month real pension (4% safe withdrawal rule).

The system is a web application running on a personal VPS (Docker + Traefik), accessible via a private subdomain. Single user (owner only).

Two core subsystems:
- **Subsystem A** - Monthly buy recommender: given a monthly budget, outputs a purchase plan (ticker, amount, week, rationale)
- **Subsystem B** - Portfolio monitoring & rebalancing: syncs broker data, computes returns, tracks allocation vs. target, generates monthly progress report

All trading is done **manually** by the user in their broker's interface. The assistant only reads data and provides recommendations.

---

## Goals

1. Accumulate retirement capital of ~$1.3M nominal by 2046
2. Web dashboard: view portfolio allocation, performance charts, progress to goal
3. Algorithmic monthly buy recommendations aligned with target allocation (65/15/15/5)
4. Monitor portfolio performance (TWRR, IRR, drawdown) and signal rebalancing needs
5. Systematize knowledge from course PDFs and Telegram channels via RAG Q&A (pgvector)
6. Telegram notifications: monthly recommendations and reports delivered to personal chat
7. Keep total operational cost below $15/month (LLM tokens + VPS)

---

## Platform

- **Runtime**: VPS with Docker + Traefik + configured subdomain
- **Interface**: Web application (FastAPI + Jinja2 + Chart.js + Flatpickr + vanilla JS)
- **Auth**: Single-user login (itsdangerous session + bcrypt password)
- **Database**: PostgreSQL + pgvector extension (replaces SQLite + LanceDB)
- **Scheduler**: APScheduler (replaces launchd) — runs inside the app container
- **Secrets**: python-dotenv (.env file on VPS, not in git)

---

## Constraints

- **Brokers**: Interactive Brokers Europe + Freedom Finance (freedom24.com) — read-only API, no automated trading
- **Monthly contributions**: $200-1000, schedule: first business day of month
- **Target allocation**: VWCE 65% / VEUR 15% / AGGH 15% / XEON 5%
- **Rebalancing threshold**: 5 percentage points from target
- **LLM**: Claude Haiku 4.5 (fast tasks) + Claude Sonnet 4.6 (monthly reports)
- **Language of corpus**: Russian + Ukrainian (BGE-M3 multilingual embeddings via pgvector)
- **Single user**: no multi-tenancy, no user management

---

## Out of Scope

- Automated trade execution (all trades done manually by user in broker UI)
- Market prediction or price forecasting
- Crypto trading (staking tracked as external balance only)
- Options, futures, leverage
- Tax declaration (only FIFO export for self-filing)
- Multi-user access

---

## Phases

| Phase | Name | Sessions | Status |
|-------|------|----------|--------|
| 00 | Foundation | 1 | Not Started |
| 01 | Data Ingestion | 3 | Not Started |
| 02 | Recommender (Subsystem A) | 2 | Not Started |
| 03 | Monitoring (Subsystem B) | 2 | Not Started |
| 04 | Automation & Hardening | 1 | Not Started |

---

## Phase 00: Foundation

### Objectives

1. Docker Compose: PostgreSQL (with pgvector) + app container + Traefik labels
2. FastAPI app skeleton with Uvicorn, Jinja2 templates
3. SQLAlchemy models (all 9 tables + pgvector columns) + Alembic initial migration
4. .env template + pydantic-settings config
5. Single-user auth: login page, itsdangerous signed session cookie, bcrypt password
6. APScheduler wired into FastAPI lifespan with stub jobs
7. Base HTML template + login page + dashboard stub

---

## Phase 01: Data Ingestion

### Objectives

1. IBKR Client Portal REST API adapter via httpx (`/sync/ibkr` route)
2. IBKR Flex Query adapter for full transaction history
3. Freedom Finance TraderNet SDK adapter (`/sync/freedom` route)
4. Unified broker service: both normalize to same `positions` + `transactions` schema
5. Price cache update via yfinance (`/sync/prices` route)
6. PDF ingestion: pypdf + BGE-M3 + pgvector store (`/admin/ingest-course`)
7. LLM rule extraction from course chunks -> `methodology_rules` table
8. Telegram HTML parser + LLM sentiment -> `channel_signals` table

### Broker API Details

**IBKR Client Portal REST API**
- Auth: OAuth via CP Gateway
- Positions: `GET /v1/api/portfolio/{accountId}/positions`
- HTTP client: httpx
- Flex Query: token-based CSV delivery

**Freedom Finance TraderNet API (freedom24.com = tradernet.com)**
- SDK: official `tradernet` Python package
- Auth: `TraderNetAPI(public_key, private_key, login, passwd)` from .env
- API key generated: 2026-05-04, perpetual

---

## Phase 02: Recommender (Subsystem A)

### Objectives

1. Allocation deviation calculator (current vs. target)
2. Algorithmic buy plan: underweight-first + oversold scoring (SMA200/RSI/52w-drawdown)
3. DCA split into week 1 and week 3 of month
4. LLM rationale generation (Claude Sonnet) with course rules + channel signals context
5. Web UI: budget input form -> recommendation table with rationale
6. Mark recommendation as executed (checkbox per line)
7. Output: stored in `recommendations` table + Telegram notification

---

## Phase 03: Monitoring (Subsystem B)

### Objectives

1. TWRR, IRR, drawdown calculation via quantstats
2. Category-level and position-level attribution
3. Rebalancing signal (threshold check + minimum-trade plan)
4. Goal projection: FV formula with trailing 12m return
5. V80A LifeStrategy baseline comparison
6. Web UI: performance charts (Chart.js), allocation donut, progress to goal
7. Monthly report generation with LLM narrative (Claude Sonnet)
8. External balances (staking) manual entry form
9. Telegram delivery of monthly report

---

## Phase 04: Automation & Hardening

### Objectives

1. APScheduler jobs: price sync (daily), channel ingest (weekly), backup (monthly)
2. Backup command: pg_dump + vector store tar to backup destination
3. Integration test: full cycle sync -> recommend -> report
4. Error handling: httpx retry/backoff, LLM timeout fallback
5. README for future self

---

## Technical Stack

| Layer | Choice | Version |
|-------|--------|---------|
| Language | Python | 3.12 |
| Package manager | uv | latest |
| Web framework | FastAPI | >=0.115 |
| ASGI server | Uvicorn | >=0.30 |
| ORM | SQLAlchemy (sync) | >=2.0 |
| DB | PostgreSQL + pgvector | 16 + 0.7 |
| DB driver | psycopg2-binary | >=2.9 |
| Migrations | Alembic | >=1.13 |
| Templates | Jinja2 | >=3.1 |
| Scheduler | APScheduler | >=3.10 |
| HTTP client | httpx | >=0.27 |
| AI / LLM | anthropic | >=0.30 |
| Telegram | python-telegram-bot | >=20.0 |
| Sessions | itsdangerous | >=2.1 |
| Forms | python-multipart | >=0.0.9 |
| Crypto / passwords | cryptography + bcrypt | >=42 / >=4.0 |
| Config | python-dotenv | >=1.0 |
| Charts (frontend) | Chart.js 4.4 | CDN |
| Datepicker (frontend) | Flatpickr | CDN |
| CSS | Custom inline styles | - |
| JS | Vanilla JS | - |
| Portfolio analytics | pandas + quantstats | >=2.2 / >=0.0.62 |
| Technical indicators | pandas-ta | >=0.3 |
| PDF parsing | pypdf | >=4.0 |
| HTML parsing | BeautifulSoup4 | >=4.12 |
| Market data | yfinance | >=0.2 |
| Broker SDK | tradernet (Freedom) | latest |
| Embeddings | sentence-transformers (BGE-M3) | >=3.0 |
| Testing | pytest | >=8.0 |
| Linting | ruff | >=0.4 |
| Containerization | Docker + Docker Compose | latest |

---

## Project Structure

```
investments-assistant/
  app/
    main.py               # FastAPI app, router registration, lifespan (APScheduler)
    auth.py               # login/logout, itsdangerous session, bcrypt
    db.py                 # SQLAlchemy engine + session factory
    models.py             # All SQLAlchemy ORM models
    config.py             # pydantic-settings from .env
    scheduler.py          # APScheduler instance + job registration
    routers/
      dashboard.py        # GET / -> dashboard.html
      sync.py             # POST /sync/ibkr, /sync/freedom, /sync/prices
      recommend.py        # GET/POST /recommend
      report.py           # GET /report/{month}
      settings.py         # GET/POST /settings
      admin.py            # POST /admin/ingest-course, /admin/ingest-channels
    services/
      ingestion/
        ibkr.py           # IBKR Client Portal REST API adapter (httpx)
        freedom.py        # Freedom TraderNet SDK adapter
        broker.py         # Unified broker interface
        course.py         # PDF -> chunks -> pgvector
        channels.py       # Telegram HTML -> channel_signals
      llm.py              # Claude adapter (model selection, caching, disclaimer)
      prices.py           # yfinance price cache
      portfolio.py        # allocation, TWRR, IRR, drawdown
      recommender.py      # Subsystem A: buy plan algorithm
      monitor.py          # Subsystem B: report, rebalancing
      backup.py           # pg_dump + tar
      telegram.py         # Telegram bot notifications
    templates/
      base.html           # Base layout (nav, Chart.js CDN, Flatpickr CDN)
      login.html
      dashboard.html      # Allocation donut + performance chart + progress
      recommend.html      # Budget form + recommendation table
      report.html         # Monthly report view
      settings.html       # Config + staking entry
    static/               # Empty (all assets via CDN)
  migrations/
    env.py
    versions/
      0001_initial.py
  tests/
  docker-compose.yml
  Dockerfile
  .env.example            # Template (committed); .env (NOT committed)
  alembic.ini
  pyproject.toml
```

---

## Target Instruments

| Category | Ticker | ISIN | Target % |
|----------|--------|------|----------|
| Global stocks (FTSE All-World) | VWCE | IE00BK5BQT80 | 65% |
| Europe stocks (FTSE Dev Europe) | VEUR | IE00B945VV12 | 15% |
| Global bonds (EUR-hedged) | AGGH | IE00BDBRDM35 | 15% |
| Cash/overnight EUR | XEON | LU0290358497 | 5% |

Baseline comparison: Vanguard LifeStrategy 80% Equity (V80A, IE00BMVB5R75)

---

## Database Schema (SQLAlchemy models in models.py)

| Table | Key columns |
|-------|-------------|
| config | key PK, value |
| instruments | ticker PK, isin, name, category, currency, exchange, active |
| prices | ticker + date PK, open, high, low, close, volume |
| positions | snapshot_date + ticker PK, quantity, avg_cost_usd, market_value_usd |
| transactions | id PK, trade_date, ticker, type, quantity, price_usd, amount_usd, fee_usd, ibkr_txn_id UNIQUE |
| external_balances | date + source + asset PK, amount_usd, apy_pct |
| channel_signals | channel + source_msg_id PK, message_date, ticker, sentiment, excerpt, embedding vector(1024) |
| recommendations | month + ticker PK, amount_usd, week_of_month, rationale, executed |
| progress_snapshots | month PK, total_capital_usd, broker_capital_usd, staking_capital_usd, ttm_return_pct, projected_capital_2046_usd, delta_to_goal_usd |
| course_chunks | id PK, source_file, page_num, content, embedding vector(1024) |

pgvector enables semantic search on `channel_signals.embedding` and `course_chunks.embedding` — replaces LanceDB.

---

## Financial Model

| Monthly contribution | 7% annual | 8% | 9% | 10% |
|---------------------|-----------|----|----|-----|
| $200 | $104K | $118K | $134K | $152K |
| $500 | $260K | $294K | $334K | $379K |
| $700 | $364K | $412K | $467K | $530K |
| $1000 | $521K | $589K | $668K | $759K |

Target: $1,314,000 nominal. Goal achievable only at $1000+/month with 9-10% returns. Dashboard shows monthly gap and required contribution to meet goal.

---

## Success Criteria

- [ ] `docker compose up` starts PostgreSQL + app without errors
- [ ] Login page accessible at configured subdomain; session persists across requests
- [ ] `sync-freedom` fetches live positions from freedom24.com TraderNet API
- [ ] `sync-ibkr` fetches positions via IBKR Client Portal API or Flex CSV upload
- [ ] `ingest-course` indexes all 16 PDFs into pgvector; semantic search returns relevant chunks
- [ ] `recommend --budget 700` produces recommendation page in <60s
- [ ] `report` page shows correct TWRR, IRR, allocation chart, goal projection
- [ ] Monthly report and recommendations delivered to Telegram
- [ ] Backup produces restorable pg_dump
- [ ] System handles missing contribution months without errors
- [ ] Total LLM cost per month <= $10 at $700 average contribution
