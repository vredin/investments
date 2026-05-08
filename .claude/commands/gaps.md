---
name: gaps
description: 'Service-level audit — finds (a) what is MISSING in the service vs production-grade SaaS checklist, (b) what is OUTDATED vs modern 2025-26 best practices for the stack. Read-only analysis, never modifies code.'
argument-hint: [missing | modern | both | <subsystem path>]
allowed-tools: Read, Grep, Glob, Bash
model: opus
---

> **Style:** Load `caveman-distillate` skill — terse, structured output.

# /gaps — Service maturity audit

Mode: `${1:-both}` (one of: `missing`, `modern`, `both`, or a subsystem path like `app/auth/`)

This is **NOT** a code review of recent changes (use `/review` for that).
This is **NOT** an architecture refactor proposal (use `/improve-arch` for that).
This is a **whole-service audit** against a maturity checklist.

---

## STEP 1 — Load context

Read in order:
1. `docs/STACK.md` — to know what stack we're auditing (FastAPI? React? GraphQL? Celery?)
2. `docs/CONTEXT.md` — to know domain (payments? auth? data processing?)
3. `docs/CONVENTIONS.md` — to know what user already considers required
4. `docs/adr/` — decisions that the audit should NOT challenge
5. Outline `Knowledge Base / Best Practices` — search for `<stack>` patterns

If any of these are missing — proceed but flag in output.

---

## STEP 2 — Mode `missing` (gap analysis)

Audit the codebase against this checklist. For each item: **PRESENT / PARTIAL / MISSING / N/A**.

### Authentication & sessions
- [ ] Login + register endpoints with rate limiting
- [ ] Password hashing with bcrypt/argon2/scrypt (NOT md5/sha1/sha256)
- [ ] Session management: secure cookies (HttpOnly, Secure, SameSite)
- [ ] Logout invalidates session server-side
- [ ] Password reset with single-use, expiring tokens
- [ ] 2FA / MFA support (or explicit decision against)
- [ ] Account lockout / progressive delays after failed attempts

### API design
- [ ] Versioning strategy (URL or header, picked one and documented)
- [ ] Pagination on every list endpoint (cursor or offset)
- [ ] Rate limiting on every endpoint (or explicit per-endpoint exception)
- [ ] Request validation at boundary (Pydantic / Zod / similar)
- [ ] Response shapes documented (OpenAPI / GraphQL schema)
- [ ] Idempotency keys on POST/PUT for unsafe operations
- [ ] Correlation IDs across services
- [ ] CORS locked to specific origins (NOT `*` in prod)

### Data layer
- [ ] All schema changes via migrations (no manual `ALTER TABLE` in prod)
- [ ] Migration tool present and used (alembic / drizzle / etc)
- [ ] Backup strategy documented + last backup verified within 7 days
- [ ] Retention policy for PII (GDPR/CCPA awareness)
- [ ] Indexes on frequently-queried columns (verify with `EXPLAIN`)
- [ ] N+1 query guards (eager loading where appropriate)
- [ ] Connection pooling configured

### Observability
- [ ] Structured logging (JSON, not plain text)
- [ ] Log levels enforced (no `print()` in prod paths)
- [ ] Errors include request context (user_id, request_id, endpoint)
- [ ] Metrics exposed (Prometheus, StatsD, or vendor)
- [ ] Tracing for cross-service requests (OpenTelemetry)
- [ ] Health endpoint distinguishes `/livez` (process up) vs `/readyz` (deps ok)
- [ ] Critical alerts configured (5xx rate, latency p99, queue depth)
- [ ] PII NOT in logs (emails, phones, tokens)

### Security
- [ ] Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- [ ] CSRF tokens on state-changing operations (or stateless JWT)
- [ ] Input sanitization before rendering (XSS guard)
- [ ] Secrets in env, not committed (`gitleaks` clean)
- [ ] Dependencies scanned (`npm audit` / `pip-audit`) clean of CRITICAL CVEs
- [ ] GitHub Actions pinned to `@<sha>` not `@main`/`@v1`
- [ ] Docker: non-root user, read-only filesystem where possible
- [ ] TLS 1.2+ enforced (Traefik/nginx config)

### Resilience
- [ ] Timeout on every external call (no infinite hangs)
- [ ] Retry logic bounded (max attempts, exponential backoff)
- [ ] Circuit breaker for unstable upstreams
- [ ] Graceful shutdown (SIGTERM handling, drain in-flight)
- [ ] Idempotent retry support (no double-charge / double-send)

### Testing
- [ ] Unit tests cover happy path + error paths (≥70% on critical modules)
- [ ] Integration tests against real DB (not just mocks)
- [ ] E2E test for primary user flow
- [ ] Test data realistic (Unicode, edge lengths, nulls)
- [ ] Anti-regression: tests fail when feature is reverted

### Operations
- [ ] CI runs on every push (lint + typecheck + tests)
- [ ] Deploy is reversible (rollback documented in RUNBOOK.md)
- [ ] DB migrations are reversible OR the up-only approach is documented
- [ ] Zero-downtime deploy strategy chosen (rolling / blue-green / canary)
- [ ] Disaster recovery: RPO + RTO targets stated
- [ ] On-call: someone responds to alerts within X minutes

### User experience
- [ ] Loading states on every async UI operation
- [ ] Empty states (no data) handled visually, not "0 results"
- [ ] Error states show actionable messages (not stacktrace)
- [ ] Form validation at boundary AND on field blur
- [ ] Optimistic updates with rollback on failure
- [ ] Accessibility: WCAG 2.2 AA on critical flows

### Documentation
- [ ] README has 5-line "what is this + how to run locally"
- [ ] STACK.md fills in real values (no `[PROJECT_NAME]` placeholders)
- [ ] RUNBOOK.md has at least 3 known failure scenarios
- [ ] ADR for every non-obvious architecture decision
- [ ] API documented (OpenAPI / GraphQL introspection / handwritten)

---

## STEP 3 — Mode `modern` (modernization audit)

For each technology in `docs/STACK.md`, audit code against modern (2025-26) idioms.

### Python (if FastAPI / SQLAlchemy / pytest)
- [ ] `from __future__ import annotations` at top of every module
- [ ] Modern type syntax: `list[str]`, `dict[str, int]`, `X | None` (NOT `List`, `Dict`, `Optional`)
- [ ] `match` statement used where it fits (not always cascading `if/elif`)
- [ ] `async def` only when actual I/O present (not just for fashion)
- [ ] `httpx.AsyncClient` (not `requests` in async context)
- [ ] Pydantic v2 (not v1 — `model_validate` not `parse_obj`)
- [ ] SQLAlchemy 2.0 style (`session.execute(select(...))`, not `query()`)
- [ ] `pathlib.Path` (not `os.path.join`)
- [ ] Walrus operator (`:=`) where it actually helps readability
- [ ] No `pkg_resources` (use `importlib.metadata`)
- [ ] uv for deps (NOT pip directly), uv lock committed
- [ ] ruff for lint+format (NOT black + flake8 + isort separately)

### TypeScript / React (if applicable)
- [ ] React Server Components used where they fit (Next.js / Remix apps)
- [ ] Suspense for async boundaries
- [ ] `use(promise)` pattern (React 19+) where appropriate
- [ ] No class components in new code (functional only)
- [ ] No `useEffect` for derived state — use `useMemo` or `useSyncExternalStore`
- [ ] No `any` — use `unknown` with narrowing
- [ ] TanStack Query (or SWR) for server state, not raw fetch + useState
- [ ] Zod or Valibot for runtime validation (not type assertions alone)
- [ ] Vitest (not Jest) for new projects on Vite
- [ ] CSS-in-JS dying — Tailwind, vanilla-extract, or plain CSS modules preferred

### Docker / Infra
- [ ] Multi-stage builds (build stage + runtime stage)
- [ ] Distroless or alpine for runtime
- [ ] Health checks in Dockerfile / compose
- [ ] BuildKit features (`--mount=cache`) for fast rebuilds
- [ ] No `latest` tags — pinned to digest where possible
- [ ] Compose v2 syntax (`services:` not `version: '3'`)

### Database
- [ ] Connection pool sizing matches concurrency (not default)
- [ ] Indexes use `CONCURRENTLY` for prod migrations (Postgres)
- [ ] JSONB used over JSON in Postgres for queryable data
- [ ] Logical replication / CDC for read replicas (where applicable)

### General
- [ ] No CHANGELOG manual maintenance — release-please / conventional commits
- [ ] Dependabot / Renovate for dep updates
- [ ] OpenTelemetry for observability (not vendor-specific by default)

---

## STEP 4 — Output format

```
# /gaps audit — <service> — <DATE>
Mode: <missing | modern | both>
Stack: <from STACK.md>

## Summary
- Missing: <count> items (PRESENT/PARTIAL/MISSING)
- Outdated: <count> items
- N/A (not applicable to this service): <count>

## Critical gaps (block production-readiness)
| Item | Status | Why critical | Suggested action |
|------|--------|--------------|------------------|
| Rate limiting on /auth/login | MISSING | Brute force unmitigated | Add `slowapi` rate limiter, 5/min per IP |
| Bcrypt for passwords | PARTIAL | Found sha256 in legacy/auth.py:42 | Migrate to bcrypt with rehash-on-login |
| ... |

## Significant gaps (address within 1 sprint)
<table>

## Modernization opportunities (low risk)
<table>

## N/A (deliberately skipped per docs/adr/)
- <item> — see ADR-NNN

## Coverage notes
- <what I couldn't audit and why>
```

---

## STEP 5 — Optional: persist findings

After audit completes, ask:
```
Save audit findings to docs/audits/<DATE>.md? [y/n]
Save key gaps to Outline `Knowledge Base / Best Practices` for cross-project reuse? [y/n]
```

If yes:
- Write `docs/audits/<DATE>.md` with full output
- For each gap that's a generalizable pattern (e.g. "always rate-limit auth endpoints"), publish to Outline `Best Practices` if not already there

---

## Hard rules

- READ-ONLY. NEVER modifies source files. NEVER suggests fixes inline — fixes go in audit doc only.
- Items marked `N/A` MUST cite an ADR or `docs/CONVENTIONS.md` clause that explicitly excludes them.
- "Best practice" claims (mode `modern`) MUST cite a real source where possible: PEP, Anthropic guidance, framework docs, OWASP, NIST.
- "Suggested action" is one line. NOT a refactor plan. Refactor plans = `/improve-arch`.
- If user disagrees with a gap classification — they can mark it `IGNORED: <reason>` in the audit doc; future runs respect that file.
- Scope-aware: if user passes a path argument (`/gaps app/auth/`), audit only that subsystem; don't run whole-service checklist.

---

## Designed for /loop

Periodic service-level audits — but NOT too frequent (gaps don't appear daily):

```bash
# Monthly: full audit
/loop "0 8 1 * *" /gaps both

# Every 2 weeks: just modernization sweep (faster, less noise)
/loop "0 8 1,15 * *" /gaps modern
```

Use `/gaps missing` ad-hoc when you suspect something's missing.
Use `/gaps modern` when you're considering a refactor and want to know what's outdated first.
Use `/gaps both` for new project onboarding or pre-launch readiness.
