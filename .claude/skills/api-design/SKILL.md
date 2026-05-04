# API Design Skill

> Sources: "Software Engineering at Google", "Python Patterns: TDD, DDD, Event-Driven", "Modern Software Architecture"

## When to Load

- Designing new API endpoints (REST, GraphQL, WebSocket)
- Integrating services (backend-to-backend, frontend-to-backend)
- Reviewing API contracts or schemas
- Planning database schema and data access layer

## Core Principles

| Principle | Application |
|-----------|-------------|
| **Contract-first** | Define API schema before implementation. OpenAPI/JSON Schema as SSOT |
| **Backwards compatibility** | Never break existing clients. Additive changes only. Deprecate gradually |
| **Explicit over implicit** | Every endpoint documents input, output, errors, auth requirements |
| **Fail fast, fail clearly** | Validate at boundaries. Return structured errors with codes |
| **Idempotency** | PUT/DELETE must be idempotent. POST with idempotency keys for payments |

## API Design Checklist

### Endpoint Design
- [ ] RESTful resource naming (`/users/{id}/orders`, not `/getUserOrders`)
- [ ] Consistent HTTP methods (GET=read, POST=create, PUT=replace, PATCH=update, DELETE=remove)
- [ ] Pagination for list endpoints (`?page=1&per_page=20` or cursor-based)
- [ ] Filtering and sorting via query params, not body
- [ ] Versioning strategy chosen (URL prefix `/v1/` or header `Accept-Version`)

### Request/Response
- [ ] Request validation at the boundary (Pydantic, Zod, JSON Schema)
- [ ] Consistent error format: `{"error": {"code": "...", "message": "...", "details": [...]}}`
- [ ] HTTP status codes used correctly (400 vs 422, 401 vs 403, 404 vs 410)
- [ ] No sensitive data in URLs (tokens, passwords) — use headers or body
- [ ] Content-Type negotiation (JSON default, support others if needed)

### Integration Patterns
- [ ] Circuit breaker for external service calls (timeout + fallback)
- [ ] Retry with exponential backoff for transient failures
- [ ] Request/response logging (structured, no secrets)
- [ ] Correlation IDs across service boundaries (`X-Request-ID`)
- [ ] Graceful degradation when downstream is unavailable

## Backend Architecture Patterns

### Repository Pattern
Isolate data access from business logic:
```
Domain Model ← Repository Interface ← Repository Implementation → Database
```
- Domain models are plain objects (dataclasses/Pydantic) — no ORM coupling
- Repository interface defines CRUD operations
- Implementation handles SQL/ORM details
- Unit tests mock the repository, not the database

### Unit of Work (UoW)
Manage transaction boundaries atomically:
```
async with uow:
    user = await uow.users.get(user_id)
    order = Order(user=user, items=items)
    await uow.orders.add(order)
    await uow.commit()
```
- One UoW per business operation
- Rollback on any exception
- Never commit in the repository — only in UoW

### Command/Query Separation
- **Commands** (write) return nothing or ID — go through domain model + UoW
- **Queries** (read) return DTOs — can bypass domain model, use optimized queries
- Separate read models from write models when scale demands it (CQRS)

### Event-Driven Patterns
For decoupling services:
- **Domain Events**: raised inside aggregates, handled by event bus
- **Message Queue**: Redis/RabbitMQ for async processing
- **Idempotent handlers**: every handler must handle duplicate events safely
- **Event schema versioning**: never break consumers — add fields, don't remove

## API Versioning Strategy

| Strategy | When to Use |
|----------|-------------|
| URL prefix (`/v1/`) | Simple, visible, good for breaking changes |
| Header (`Accept-Version: 2`) | Cleaner URLs, harder to test in browser |
| Query param (`?version=2`) | Easy migration, slightly messy |

**Rule**: Support N and N-1 simultaneously. Deprecate N-1 after 3 months with `Sunset` header.

## Anti-Patterns

- Chatty APIs: client needs 5 requests for one screen → create aggregated endpoint
- God endpoints: one endpoint does everything via query params → split by resource
- Leaking internals: DB column names in response → use DTOs/serializers
- Ignoring pagination: returning 10K records → always paginate lists
- Stringly-typed: using strings for enums/dates/IDs → use proper types with validation
