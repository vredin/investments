# Considerations

> Institutional memory for AI assistants. Updated between phases via /carryforward.
> **Line budget**: 600 max | **Last updated**: Phase 01 Session 01 planning (2026-05-04)

---

## Active Concerns

### Technical Debt
<!-- Max 5 items -->

*None yet.*

### External Dependencies
<!-- Max 5 items -->

- **Freedom Finance TraderNet API**: perpetual API key pair generated 2026-05-04. Stored in `.env` as `FREEDOM_PUBLIC_KEY` + `FREEDOM_PRIVATE_KEY` + `FREEDOM_LOGIN` + `FREEDOM_PASSWORD`. Auth: `TraderNetAPI(public_key, private_key, login, passwd)`. Official Python SDK: `tradernet`.
- **IBKR**: CP Gateway not feasible headless on VPS. Decision made: use Flex Query XML file upload only. `/sync/ibkr` = multipart upload form, not live API.
- **yfinance ToS risk**: scrapes Yahoo Finance; use for dev/backtest only. Production price data comes from broker APIs.
- **LLM via OpenRouter**: use `openai` SDK with `base_url="https://openrouter.ai/api/v1"` and `OPENROUTER_API_KEY`. Never call `anthropic.Anthropic()` directly. Models: `google/gemini-flash-1.5` (fast), `anthropic/claude-sonnet-4-5` (reports).
- **pgvector first migration**: `CREATE EXTENSION IF NOT EXISTS vector` must run before any table DDL. Requires PostgreSQL superuser role — the `pgvector/pgvector:pg16` default `postgres` user has this.

### Performance / Security
<!-- Max 5 items -->

- **Secrets in .env only**: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD_HASH`, all API keys. Never in `docker-compose.yml`, `config.py` defaults, or any committed file.
- **Single-user auth**: bcrypt hash of admin password in `.env` as `ADMIN_PASSWORD_HASH`. Session = itsdangerous signed cookie, 12h max age. No user table, no registration.
- **Broker API responses**: never log raw payloads — log only summaries ("synced 12 positions from IBKR"). Responses contain PII + financial data.
- **Every LLM output shown to user**: must include "Not investment advice. For informational purposes only."

### Architecture
<!-- Max 5 items -->

- **Corpus toxicity (DA-S01)**: Telegram channel exports may contain pump-and-dump signals. The RAG layer must NOT use `channel_signals` as investment truth — only retrospective educational data. Course PDFs are the authoritative knowledge source.
- **20-year horizon**: PostgreSQL schema + Alembic migrations are more durable than SQLite for VPS deployment. Each migration must have a working `downgrade()`. Never modify an applied migration.
- **Pause-mode**: system must work correctly when contributions are paused 1-6 months. No service logic should assume monthly contribution is always present.
- **Regulatory boundary**: personal use only. Do not add sharing, public reports, or multi-user features without legal review of MiFID II / Ukrainian capital markets law implications.

---

## Lessons Learned

### What Worked
<!-- Max 15 items -->

- **git-based deploy over rsync**: `git push origin main` + `ssh vps3 "git pull + docker compose up --build"`. `.env` preserved because it is gitignored. No scp needed.
- **Separate cookie names**: auth cookie `auth_token` (itsdangerous) + session cookie `session` (SessionMiddleware). Same name = `binascii.Error: Invalid base64` on every request.
- **CPU-only torch in Dockerfile**: `RUN uv pip install torch --index-url https://download.pytorch.org/whl/cpu` BEFORE main install. Otherwise sentence-transformers pulls 2GB CUDA.

### What to Avoid
<!-- Max 10 items -->

- **Streamlit**: user has explicit bad experience — do not suggest under any circumstances.
- **Django**: user has explicit bad experience — do not suggest under any circumstances.
- **Chrome extension for broker data scraping**: session cookies expire in 15-30 min, requires credential storage, fragile on UI changes. TraderNet API is the correct solution.
- **Automated broker API trading**: read-only access only. Any write/order endpoint creates MiFID II exposure.
- **Mocking the database in tests**: use a real test PostgreSQL DB. Mock/prod divergence can mask broken migrations.
- **Env-var-conditional Alembic data migrations** (vault F-048): if startup script auto-runs `alembic upgrade head`, env vars passed via `docker compose exec` are NOT available. Use schema-only migrations; run data updates via psql directly after deploy.
- **Alembic revision ID > 32 chars** (vault F-038): `alembic_version.version_num` is VARCHAR(32). Revision IDs longer than 32 chars break deploy with `value too long`. Keep IDs short: `0001_initial` = OK, `0002_add_embedding_index` = OK (24 chars).
- **Starlette 1.0 TemplateResponse API**: signature is `TemplateResponse(request, "name.html", context_dict)` — no keyword arg `name=`. Starlette 0.x `TemplateResponse("name.html", {"request": req})` raises `TypeError: unhashable type: 'dict'`.

### Tool/Library Notes
<!-- Max 5 items -->

- **hatchling + non-standard package name**: if project name in `pyproject.toml` differs from the `app/` directory, add `[tool.hatch.build.targets.wheel] packages = ["app"]` — otherwise `ValueError: Unable to determine which files to ship`.
- **tradernet SDK**: discover actual method names before implementing (`python -c "import tradernet; help(tradernet.TraderNetAPI)"`) — do not assume `get_portfolio()` exists.

---

## Resolved

| Phase | Item | Resolution |
|-------|------|------------|
| 00 | Freedom Finance API path | Confirmed: freedom24.com = tradernet.com, same account. Official Python SDK (`tradernet`), perpetual API key generated 2026-05-04. |
| 00 | SQLite vs PostgreSQL | Decided: PostgreSQL + pgvector on VPS. Replaces both SQLite and LanceDB. |
| 00 | Platform | Decided: VPS + Docker + Traefik (not macOS local). APScheduler replaces launchd. |
| 00 | Web UI framework | Decided: FastAPI + Jinja2 + Chart.js 4.4 + Flatpickr + vanilla JS + inline CSS. Matches user's proven stack on another project. |
| 00 | IBKR integration | Decided: Flex Query XML file upload only. CP Gateway not feasible headless on VPS. |
| 00 | Deploy method | Decided: git-based (git push + server git pull + docker rebuild). Replaced rsync. |
| 00 | GitHub repo | git@github.com:vredin/investments.git. Deploy key on server: ed25519 key added 2026-05-04. |

---

*Auto-generated by /initspec. Updated by /carryforward between phases.*
