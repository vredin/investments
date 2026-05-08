---
name: docs
description: 'Documentation lifecycle — init missing docs, sync from code, create ADR, publish to Outline, audit drift.'
argument-hint: [init | sync | adr <title> | publish | audit]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

> **Style:** Load `caveman-distillate` skill.

# /docs — Documentation lifecycle

Mode: `$ARGUMENTS` (one of: `init`, `sync`, `adr <title>`, `publish`, `audit`)

---

## Mode: `init`

Create missing documentation stubs. Idempotent (skip files that exist).

| File | Created if missing | Source |
|---|---|---|
| `docs/STACK.md` | yes | Template stub, fill from `/init-project` answers |
| `docs/CONTEXT.md` | yes | Template stub (domain glossary) |
| `docs/RUNBOOK.md` | yes | Template stub (incident response) |
| `docs/RULES.md` | yes | Business rules template — NEVER answer rate/policy questions without it |
| `docs/CONVENTIONS.md` | yes | Template stub + Python section if Python in stack |
| `docs/KNOWLEDGE.md` | yes | Empty stub for ADR-summary |
| `docs/FAILS.md` | yes | Header only — entries grow over time |
| `docs/PATTERNS.md` | yes | Header only |
| `docs/TASK.md` | yes | Backlog/In Progress headers |
| `docs/adr/0001-template.md` | yes | ADR template |
| `docs/reports/` | yes | Directory only |
| `docs/specs/` | yes | Directory only |
| `docs/archive/TASK_ARCHIVE.md` | yes | Header only |

After init: report which files were created vs already existed.

---

## Mode: `sync`

Audit + update documentation from real code. Read-mostly with surgical edits.

### STEP 1 — ARCHITECTURE.md
1. Glob the source root (`app/`, `src/`, etc — read from `docs/STACK.md`).
2. Identify entry points (FastAPI routers, React app root, CLI handlers).
3. Build module map: top-level packages → public interfaces.
4. Compare with existing `docs/ARCHITECTURE.md`. If sections drifted (module deleted/renamed/moved) → mark with `[DRIFT]` comment, propose update diff.
5. Use `improve-codebase-architecture/LANGUAGE.md` glossary. NEVER write "service", "boundary", "API alone".

### STEP 2 — API.md
1. Find all FastAPI/Express/etc route definitions.
2. Generate flat table: method | path | handler | auth required | response type.
3. Compare with existing `docs/API.md`. Mark routes that vanished or changed signature.

### STEP 3 — CONVENTIONS.md
1. Detect added/removed dependencies in `pyproject.toml` / `package.json`.
2. Flag tool changes ("ruff added → update format command in CONVENTIONS").

### STEP 4 — Report
```
DOCS SYNC — <DATE>

ARCHITECTURE.md: <N drift items, see diff below>
API.md:          <M new endpoints, K changed, J removed>
CONVENTIONS.md:  <updates needed>

Apply changes? [y/n/per-file]
```

Apply mode = surgical edits (Edit tool), no rewrites of user-authored sections (those marked `<!-- USER -->`).

---

## Mode: `adr <title>`

Create new ADR.

1. Find next free number: `ls docs/adr/ | grep -E '^[0-9]{4}-' | sort -r | head -1`.
2. New file: `docs/adr/<NNNN>-<slug>.md` from `docs/adr/0001-template.md`.
3. Pre-fill: title, today's date, deciders=`<git config user.name>`.
4. Open for user input (return path, instruct user to fill).
5. After save: link from `docs/KNOWLEDGE.md` summary table.

Trigger: usually after `improve-codebase-architecture` skill grilling produces a rejection worth recording.

---

## Mode: `publish`

Mirror local `docs/` to Outline `Project: <name>` collection.

1. Read project Outline collection ID from `.claude/.setup.json`.
2. For each top-level `docs/*.md` (excluding reports/, archive/, specs/):
   - Search Outline for existing doc with same title.
   - If exists → `mcp__outline__update_document` with new body.
   - If not → `mcp__outline__create_document`.
3. Report mapping local → Outline URL for each.

`reports/`, `archive/`, `specs/` are NOT mirrored (too noisy, project-internal).

---

## Mode: `audit`

Find docs/code drift without applying changes. Read-only.

Output:
```
DOCS AUDIT — <DATE>

ARCHITECTURE.md
  ❌ References module `app/legacy/` (deleted in commit abc1234)
  ⚠️  Section "Caching" outdated — Redis no longer in pyproject.toml

API.md
  ❌ Lists endpoint POST /v1/old-thing (removed)
  ⚠️  POST /api/cameras has different request shape since commit def5678

CONVENTIONS.md
  ⚠️  References "black" — replaced by "ruff format" 3 weeks ago

STACK.md
  ✓ in sync

Run /docs sync to apply fixes.
```

---

## Designed for /loop

```bash
# Weekly Monday 9:00 — audit + alert if drift found
/loop "0 9 * * 1" /docs audit
```

If audit finds drift, you decide whether to run sync. Auto-sync without review can stomp manual edits — explicit gate required.

---

## Rules

- NEVER overwrite sections marked `<!-- USER -->` — those are user-authored.
- Sync is surgical (Edit tool), never wholesale rewrite.
- ADR files are immutable once written — supersede with new ADR.
- Publish to Outline only after successful sync — stale local = stale Outline = worse than missing.
