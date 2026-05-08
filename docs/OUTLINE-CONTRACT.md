# Outline Contract — what writes where, when, and in what mode

> Single source of truth for Outline integration. When in doubt about whether something
> auto-publishes or not, this file is authoritative.

## Layout

```
Knowledge Base                              ← shared, cross-project
├── Fails              F-NNN entries from any project
├── Best Practices     Reusable patterns (proven >1× across projects)
├── Tricks             One-liners, heuristics
└── Daily Status       Daily reports — title format: "<project> — YYYY-MM-DD"

Project: <name>                             ← per-project, not reusable
├── Architecture       Mirror of docs/ARCHITECTURE.md
├── API Reference      Mirror of docs/API.md
├── Runbook            Mirror of docs/RUNBOOK.md
├── Knowledge          Mirror of docs/KNOWLEDGE.md (this project's decisions)
├── Decisions          ADR-NNN — one page per ADR (mirror of docs/adr/)
└── Rules              R-NNN business rules (mirror of docs/RULES.md)
```

## Triggers — what publishes, where, in what mode

| Source | Outline destination | Mode |
|---|---|---|
| `/fix` STEP 7 — F-NNN with non-obvious root cause | Knowledge Base / Fails | **AUTO** (no prompt) |
| `/rule` STEP 9 — R-NNN created | Project: <name> / Rules | **AUTO** |
| `/improve-arch` — ADR created | Project: <name> / Decisions | **AUTO** |
| `/improve-arch` — pattern flagged `reusable: true` | Knowledge Base / Best Practices | **AUTO** |
| `/improve-arch` — pattern not flagged reusable | local docs/PATTERNS.md only | not published |
| `/council` — verdict accepted by user | Knowledge Base / Best Practices | **ASK** (judgment) |
| `/general` — verified fact, useful for later | Knowledge Base / Fails or Tricks | **ASK** (subjective) |
| `/report` (daily, via /loop) | Knowledge Base / Daily Status | **AUTO** if has activity |
| `/docs sync --publish` (weekly, via /loop) | Project: <name> / Architecture, API, Runbook, Knowledge | **AUTO** gated by drift-check |
| `/self-audit --global` (bi-weekly, via /loop) | Knowledge Base / Best Practices (process audit) | **AUTO** |
| `/self-audit` (weekly, via /loop) | local docs/SELF-AUDIT-<date>.md | not published |

## Control flags — `.claude/.setup.json`

```json
{
  "version": 3,
  "outline": {
    "shared_kb_id": "<UUID of Knowledge Base collection>",
    "project_collection_id": "<UUID of Project: <name> collection>",
    "auto_publish": {
      "fails_to_shared": true,
      "rules_to_project": true,
      "adrs_to_project": true,
      "reusable_patterns_to_shared": true,
      "daily_status_to_shared": true,
      "docs_sync_to_project": true
    }
  }
}
```

Flip a flag to `false` to disable that auto-publish. Defaults are all `true`.

## Read flow — commands check Outline BEFORE work

Auto-publish is one direction. The other direction (read prior knowledge before starting) is equally important — without it, every new task risks duplicating or contradicting prior work.

| Command | Reads from | When |
|---|---|---|
| `/fix` STEP 0.5 | `Knowledge Base / Fails` (matching F-NNN), `Knowledge Base / Best Practices` (defensive patterns) | Before diagnosing — recurring bugs surfaced |
| `/todo add` STEP 2.5 | `Knowledge Base / Best Practices`, `Knowledge Base / Fails`, `Project: <name> / Decisions` (ADRs), `Project: <name> / Rules` | Before researching — task constraints surfaced |
| `orchestrator` STEP 2.5 | `Knowledge Base / Fails` (newer than spec), `Project: <name> / Decisions`, `Knowledge Base / Daily Status` (recent adjacent work) | After reading spec, before writing tests — refresh context |
| `/general` (per bucket) | `Knowledge Base / Fails`, `Knowledge Base / Best Practices`, `Project: <name> / *` | Always when relevant to the question type |

**Decision shape** (same for all read points):
- Match found, applicable → reuse the prior pattern, link from new artifact
- Match found, contradicts → flag, ask user to reconcile (often means ADR override)
- Nothing relevant → proceed, document the search in artifact

This is the feedback loop: writes from one task become reads for the next.

## Why this design

- **Objective → AUTO**. Failures, rules, ADRs are facts; asking permission per-publish is friction without value.
- **Subjective → ASK**. Patterns/Best Practices are judgment calls — a one-off solution shouldn't claim "best practice" status.
- **Cross-project knowledge → Shared**. Failure patterns from Project A often save time in Project B.
- **Project-specific → Project collection**. Business rules / architecture / runbook are not transferable.
- **Daily status → Shared**, not Project. Single timeline of "what got done today across everything" is more useful than 5 separate timelines.

## What is NOT published

These stay local only:
- `docs/TASK.md` — transient backlog
- `docs/specs/T-NNN-*.md` — transient spec files
- `docs/handoff/*.md` — checkpoint artifacts
- `docs/reports/<date>.md` — local mirror of Daily Status (for offline access)
- `docs/archive/*` — completed task history
- `docs/SELF-AUDIT-<date>.md` — process improvement findings

If you want any of these published, do it manually via `mcp__outline__create_document`.

## Manual publish — when needed

For one-off shares (e.g. wanting to publish PATTERNS.md content to KB):

```
mcp__outline__create_document
  collectionId: <shared_kb_id>
  title: "<descriptive title>"
  text: "<markdown content>"
  publish: true
```

Or via `bin/outline.sh create <collection_id> "<title>" < content.md`.

## Rate limits & failure handling

- Outline API doesn't enforce strict rate limits, but commands batch publishes when possible
- If MCP outline is disconnected — auto-publish silently fails locally (logged, but doesn't block command)
- Local files (FAILS.md, RULES.md, etc.) ALWAYS get written first; Outline is a mirror, not the primary
- This means: if Outline is down, you don't lose work — local is source of truth, Outline is replication

## Migration / replay

If a project missed publishes (Outline was down, MCP not connected, etc.):

```
/docs publish --since <date>
```

(NOT IMPLEMENTED YET — placeholder for future. For now use manual `bin/outline.sh create` per missed entry.)
