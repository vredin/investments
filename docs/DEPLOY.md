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
| GitHub repo | `git@github.com:vredin/investments.git` |

> **IMPORTANT**: Always use `ssh vps3`. Never use raw IP or alternative SSH commands.

---

## Environment Files

| File | Location | Purpose |
|------|----------|---------|
| `.env.example` | project root | Template (committed) |
| `.env` on server | `/opt/Investments/.env` | Active production env — never committed |

### Secrets on server
- Edit via: `ssh vps3 "nano /opt/Investments/.env"`
- Current state: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD_HASH` set. `OPENROUTER_API_KEY`, `FREEDOM_*`, `TELEGRAM_*` — pending.

---

## Deploy Flow (git-based)

```bash
# 1. Push from local (always push to main first)
git push origin main

# 2. Pull on server + rebuild
ssh vps3 "cd /opt/Investments && git pull origin main && docker compose up -d --build --no-deps app"

# 3. Run migrations (only after schema changes)
ssh vps3 "cd /opt/Investments && docker compose exec app alembic upgrade head"

# 4. Verify
curl -s https://money.semishan.pro/health
```

### One-liner for code-only deploys (no migration):
```bash
git push origin main && ssh vps3 "cd /opt/Investments && git pull origin main && docker compose up -d --build --no-deps app"
```

---

## Server GitHub Setup (one-time, already done)

```bash
# Server SSH key (deploy key added to github.com/vredin/investments -> Settings -> Deploy keys):
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILXHy4/36PsZGchANQRWvWG+Ud9HrI34eI6P7tq5saXH

# Verify access:
ssh vps3 "ssh -T git@github.com"

# First-time server git setup (already done):
# ssh vps3 "cd /opt/Investments && git init && git remote add origin git@github.com:vredin/investments.git"

# First pull (after adding deploy key):
# ssh vps3 "cd /opt/Investments && git fetch origin && git checkout -b main origin/main"
```

---

## Services

| Service | URL | Health check |
|---------|-----|-------------|
| Investment Assistant | `https://money.semishan.pro` | `curl -s https://money.semishan.pro/health` -> `{"status":"ok"}` |
| PostgreSQL + pgvector | internal (db container) | `docker compose ps` -> `healthy` |

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
- `.env` is gitignored — never overwritten by `git pull`
- `postgres_data/` volume is gitignored — DB data persists across deploys
