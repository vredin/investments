# Investments — Stack & Commands

> All commands resolved from here, no hardcoded `npx`/`uv` in agents.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12 / FastAPI / SQLAlchemy 2.0 / Alembic / APScheduler |
| Data | PostgreSQL 16 + pgvector / pandas / yfinance / quantstats |
| LLM | OpenRouter (openai-compatible) / sentence-transformers |
| Infra | Docker Compose / Traefik v2.11 / VPS (vps3) |

## Commands (used by agents)

```yaml
lint_cmd:        "uv run ruff check ."
typecheck_cmd:   "uv run mypy app/ --ignore-missing-imports"
format_cmd:      "uv run ruff format ."
test_backend:    "uv run pytest tests/ -q --tb=short"
test_frontend:   ""
test_e2e:        ""
test_all:        "uv run pytest tests/ -q --tb=short"
```

## Production access (used by /general, /report)

```yaml
ssh_alias:       "vps3"
db_container:    "investments-db-1"
db_user:         "investments_user"
db_name:         "investments"
app_service:     "app"
logs_default:    "ssh vps3 'cd /opt/Investments && docker compose logs app --tail=50'"
```

Set in `~/.zshrc` for `bin/psql_ro.sh`:
```bash
export PROD_SSH_ALIAS=vps3
export PROD_DB_CONTAINER=investments-db-1
export PROD_DB_USER=investments_user
export PROD_DB_NAME=investments
```

## Outline knowledge base

```yaml
outline_url:           "https://outline.semishan.pro"
shared_collection:     "Knowledge Base"        # Fails / Best Practices / Daily Status / Tricks
project_collection:    "Project: Investments"
```

## Source layout

```
Investments/
├── app/              # FastAPI backend source
├── migrations/       # Alembic migrations
├── tests/            # pytest tests
├── docs/             # project docs
├── specs/            # task specs (T-NNN-*.md)
└── bin/              # outline.sh, psql_ro.sh, project scripts
```
