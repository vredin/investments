# [PROJECT_NAME] — Project Rules

## Stack
- **Backend**: [e.g. FastAPI + SQLAlchemy async + PostgreSQL + Redis]
- **Frontend**: [e.g. React 18 + TypeScript + TanStack Query v5 + Vite]
- **Deploy**: [e.g. Docker Compose on VPS via Traefik]

## Code Standards

> Full conventions: `docs/CONVENTIONS.md` — read at every session start.

Project-specific overrides (add as needed):
<!-- Example:
- TanStack Query: always set `staleTime` and `refetchOnMount` explicitly
- EventSource SSE must be set up at the page level, not inside child components
- Never create asyncio tasks inside a `while True` loop wrapping a generator
-->

## Deploy
- **Read `docs/DEPLOY.md` before any deploy action** — all config is there
- SSH to server: use ONLY the alias from DEPLOY.md
- Secrets delivery: `scp .env.production` to server — never ask user to edit `.env` on server manually
- After deploy: verify services are running

## Secrets
- All production secrets live in local `.env.production` (in `.gitignore`)
- **NEVER** ask the user to re-enter API keys — if provided once, they're in `.env.production`
- **NEVER** commit `.env`, `.env.production`, or any file with secrets
- **NEVER** print/log secret values in terminal output
- If a key is missing — name the exact key and ask user to add it to `.env.production` locally

## Known Gotchas
<!-- Add project-specific gotchas here as you discover them -->
