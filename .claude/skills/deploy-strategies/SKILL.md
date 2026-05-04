# Deploy Strategies Skill

> Sources: "The DevOps Handbook", "Distributed Systems Design Patterns", "Software Engineering at Google"

## When to Load

- Setting up CI/CD pipeline
- Planning deployment strategy (blue-green, canary, rolling)
- Configuring observability (logging, metrics, tracing)
- Writing Dockerfiles and docker-compose for production
- Troubleshooting production issues

## Core Principles (Three Ways of DevOps)

| Way | Principle | Application |
|-----|-----------|-------------|
| **Flow** | Reduce work-in-progress | Small, frequent deploys. No big-bang releases |
| **Feedback** | Shorten feedback loops | Automated tests, monitoring, alerting |
| **Learning** | Continual experimentation | Post-mortems, chaos engineering, A/B testing |

## Deployment Pipeline

### Stages
```
Code → Lint/Type-check → Unit Tests → Build → Integration Tests → Deploy Staging → E2E Tests → Deploy Production → Smoke Tests
```

### Rules
- Every stage must be automated — no manual steps
- Pipeline fails fast: lint before tests, unit before integration
- Artifacts are built ONCE, promoted through stages (not rebuilt)
- Rollback must be one command or one click

## Deployment Strategies

### Blue-Green
Two identical environments. Switch traffic atomically.
```
[Load Balancer] → [Blue (current)] 
                → [Green (new)] ← deploy here, test, then switch
```
- **Pro**: instant rollback (switch back to Blue)
- **Con**: 2x infrastructure cost
- **When**: zero-downtime requirement, stateless services

### Canary
Gradually shift traffic to new version.
```
[Load Balancer] → [v1: 95%] → [v2: 5%] → monitor → [v2: 25%] → ... → [v2: 100%]
```
- **Pro**: detect issues with minimal blast radius
- **Con**: complex routing, need good metrics
- **When**: large user base, risk-averse

### Rolling Update
Replace instances one at a time.
```
[v1, v1, v1] → [v2, v1, v1] → [v2, v2, v1] → [v2, v2, v2]
```
- **Pro**: no extra infrastructure
- **Con**: mixed versions during rollout
- **When**: Docker Compose / Kubernetes default, stateless services

## Observability Stack

### Structured Logging
```json
{"ts": "2025-01-15T10:30:00Z", "level": "error", "service": "api", "request_id": "abc-123", "user_id": 42, "msg": "payment failed", "error": "timeout"}
```
- JSON format — machine-parseable
- Always include: timestamp, level, service, request_id
- Never log: passwords, tokens, PII, full credit card numbers
- Log levels: ERROR (needs action), WARN (degraded), INFO (business events), DEBUG (dev only)

### Metrics (what to track)
| Category | Metrics |
|----------|---------|
| **RED** (request) | Rate, Errors, Duration per endpoint |
| **USE** (resource) | Utilization, Saturation, Errors per resource |
| **Business** | Signups, orders, payments per minute |

### Health Checks
Every service must expose:
- `/health` — is the process alive? (liveness)
- `/ready` — can it serve traffic? (readiness — DB connected, cache warm)

## Docker Production Checklist

- [ ] Multi-stage build (build stage → slim runtime stage)
- [ ] Non-root user in container (`USER app`)
- [ ] `.dockerignore` excludes: `.git`, `node_modules`, `.env*`, `__pycache__`
- [ ] Pinned base image versions (not `latest`)
- [ ] Health check in Dockerfile or compose
- [ ] Resource limits set (memory, CPU)
- [ ] Secrets via env vars or mounted files — never baked into image
- [ ] Logs to stdout/stderr (not files inside container)

## Zero-Downtime Migration Checklist

For database schema changes:
1. **Expand**: add new column/table (nullable or with default)
2. **Migrate**: backfill data, update code to write to both old and new
3. **Contract**: remove old column/table after all code uses new schema

Never: rename columns, change types, or drop columns in one deploy.

## Rollback Protocol

| Signal | Action |
|--------|--------|
| Error rate > 5% | Auto-rollback or alert |
| P99 latency > 2x baseline | Investigate, prepare rollback |
| Health check failing | Immediate rollback |
| Business metrics drop > 10% | Manual investigation + rollback if needed |

## Anti-Patterns

- **Manual deploy**: "SSH in and pull" → automate with pipeline
- **Deploy on Friday**: high-risk changes before weekend → deploy early in the week
- **No rollback plan**: "we'll fix forward" → always have one-click rollback
- **Monitoring after**: "we'll add metrics later" → observability from day one
- **Big-bang releases**: 3 months of changes in one deploy → small, frequent deploys
