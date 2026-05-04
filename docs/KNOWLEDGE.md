# KNOWLEDGE — Architecture Decisions & Tech Context (THIS project only)

> Record **project-specific** architecture decisions, tech choices, and non-obvious context tied to THIS codebase.
> Read before architecture work.
> This file is **local** — it holds ADRs that only make sense in the context of this project's code.
>
> **Not for**:
> - Cross-project fails / patterns / gotchas → write to the shared vault at `{{VAULT_PATH}}/` via the `vault-write` skill
> - Code standards → `docs/CONVENTIONS.md`
> - Active tasks → `docs/TASK.md`
> - Deploy config → `docs/DEPLOY.md`
>
> **Rule of thumb**: if the decision would be meaningless in another project (because it references THIS project's schema, THIS project's service names, THIS project's data model) — it goes here. If it would be valuable to a completely different project — write it to the shared vault as a `pattern`.

---

## How to Read This File

Each entry follows the format:
- **Decision** — what was decided
- **Why** — the reasoning (constraints, trade-offs)
- **Alternatives Considered** — what was rejected and why
- **Impact** — what this affects going forward

---

## Template Entry (replace with real decisions)

### K-001 — [DECISION TITLE]

**Date**: YYYY-MM-DD
**Decision**: [What was decided]
**Why**: [Constraints, trade-offs, context]
**Alternatives Considered**: [What else was considered and why it was rejected]
**Impact**: [What this means for future work]

---
