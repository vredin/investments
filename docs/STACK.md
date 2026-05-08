# [PROJECT_NAME] — Stack & Commands

> Filled by `/init-project`. All commands resolved from here, no hardcoded `npx`/`uv` in agents.

## Stack

| Layer | Tech |
|-------|------|
| Backend | [e.g. Python 3.11 / FastAPI / SQLAlchemy / PostgreSQL] |
| Frontend | [e.g. React 18 / TypeScript / Vite] |
| Infra | [e.g. Docker Compose / Traefik / VPS] |

## Commands (used by agents)

```yaml
# Read by orchestrator, /fix, /test, /general
lint_cmd:        "uv run ruff check ."
typecheck_cmd:   "uv run mypy app/ --ignore-missing-imports"
format_cmd:      "uv run ruff format ."
test_backend:    "uv run pytest tests/ -q --tb=short"
test_frontend:   "npx tsc --noEmit && npx vitest run"
test_e2e:        "npx playwright test --reporter=list"
test_all:        "<test_backend> && <test_frontend> && <test_e2e>"
```

## Production access (used by /general, /report)

```yaml
ssh_alias:       "[e.g. slugger]"
db_container:    "[e.g. slugger-db-1]"
db_user:         "[e.g. slugger]"
db_name:         "[e.g. slugger_crm]"
app_service:     "[e.g. app]"             # docker compose service name
logs_default:    "ssh <alias> 'sudo docker compose logs <app_service> --tail=50'"
```

Set in `~/.zshrc` for `bin/psql_ro.sh`:
```bash
export PROD_SSH_ALIAS=slugger
export PROD_DB_CONTAINER=slugger-db-1
export PROD_DB_USER=slugger
export PROD_DB_NAME=slugger_crm
```

## Outline knowledge base

```yaml
outline_url:           "https://outline.semishan.pro"
shared_collection:     "Knowledge Base"        # Fails / Best Practices / Daily Status / Tricks
project_collection:    "Project: [PROJECT_NAME]"
```

## Source layout

```
[PROJECT_NAME]/
├── app/              # backend source
├── frontend/         # frontend source (if any)
├── tests/            # tests
├── docs/             # this directory
└── bin/              # outline.sh, psql_ro.sh, project scripts
```
