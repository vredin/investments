# Deploy Configuration

> **Claude reads this file before every deploy action.**
> Never ask the user for this info — it's here.

---

## Server Access

| Parameter | Value |
|-----------|-------|
| SSH command | `ssh vps3` |
| Project path on server | `/opt/Investments` |
| Reverse proxy | Traefik v2.11 (running, network: `proxy`) |
| Web URL | `https://money.semishan.pro` |

> **IMPORTANT**: Always use `ssh vps3`. Never use raw IP or alternative SSH commands.

---

## Environment Files

| File | Location | Purpose |
|------|----------|---------|
| `.env.example` | project root | Template (committed) |
| `.env` on server | `/opt/Investments/.env` | Active production env — edit directly on server |

### Secrets on server
- Edit via: `ssh vps3 "nano /opt/Investments/.env"`
- Current state: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD_HASH` set. `OPENROUTER_API_KEY`, `FREEDOM_*`, `TELEGRAM_*` — pending.

---

## Deploy Flow

```bash
# Sync code (never syncs .env)
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.ruff_cache' --exclude='.DS_Store' --exclude='.spec_system' \
  --exclude='ChatExport*' --exclude='specs' --exclude='.env' \
  /Users/semishan/PycharmProjects/Investments/ vps3:/opt/Investments/

# Rebuild and restart app (db stays running)
ssh vps3 "cd /opt/Investments && docker compose up -d --build --no-deps app"

# Run migrations (only after schema changes)
ssh vps3 "cd /opt/Investments && docker compose exec app alembic upgrade head"

# Verify
curl -s https://money.semishan.pro/health
```

---

## Services

| Service | URL | Health check |
|---------|-----|-------------|
| Investment Assistant | `https://money.semishan.pro` | `curl -s https://money.semishan.pro/health` → `{"status":"ok"}` |
| PostgreSQL + pgvector | internal (db container) | `docker compose ps` → `healthy` |

---

## Rollback

```bash
ssh vps3 "cd /opt/Investments && git log --oneline -5"
ssh vps3 "cd /opt/Investments && git checkout <hash> && docker compose up -d --build --no-deps app"
```

---

## Notes

- Traefik handles SSL (Let's Encrypt) and routing — no nginx/certbot
- `pgvector/pgvector:pg16` image — pgvector extension pre-installed, activated via first Alembic migration
- App container name: `investments-app-1` / DB: `investments-db-1`
- DB password: stored in `/opt/Investments/.env` as `DB_PASSWORD` and embedded in `DATABASE_URL`
