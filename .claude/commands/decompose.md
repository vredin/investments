---
name: decompose
description: 'Decompose a PRD or external requirements doc into Architecture (ADRs) → Epics → Tasks via 4 Diablo gates. Output: docs/adr/, docs/epics/, docs/specs/T-NNN-*. Use AFTER /intent or with external requirements doc.'
argument-hint: <PRD-NNN | path-to-requirements-doc>
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion, Glob, Grep
model: opus
---

> **Style:** Load `caveman-distillate` skill — terse, evidence-first.

# /decompose — PRD → Architecture → Epics → Tasks

Input: **$ARGUMENTS** (one of):
- `PRD-NNN` reference (must exist in `docs/prd/`)
- Path to external requirements doc (`.md` / `.pdf` / `.docx`)
- `inline:<paste>` for quick input

**Insight from BMAD v6**: «Epics created AFTER architecture, not before.» Tech choices affect work breakdown. So the order is: PRD → ADRs → Epics → Tasks. Skipping the architecture step produces epics that don't align with chosen tech.

This command runs **4 Diablo gates**: PRD review (skip if from /intent — already gated) → Architecture → Epics → Tasks. Each gate must pass before next phase.

---

## STEP 0 — Resolve input

```bash
ARG="$ARGUMENTS"
case "$ARG" in
  PRD-*)            INPUT="docs/prd/${ARG}-*.md" ;;
  inline:*)         echo "${ARG#inline:}" > "/tmp/decompose-input-$$.md"; INPUT="/tmp/decompose-input-$$.md" ;;
  *.md|*.pdf|*.docx) INPUT="$ARG" ;;
  *)                echo "FAIL: unrecognized input — expected PRD-NNN, file path, or inline:..."; exit 1 ;;
esac
```

If PDF or DOCX: convert to markdown via existing tooling or ask user to provide markdown version.

## STEP 1 — Read input + load skills

1. Read `$INPUT` fully — never excerpt
2. Load skills: `spec-normalizer`, `decision-matrix`, `verification-pass`, `humanizer`, `improve-codebase-architecture`, `planning`
3. Load agent: Diablo

If input is external (not PRD-NNN), normalize it via `spec-normalizer` into PRD format first → save as `docs/prd/PRD-NNN-<slug>.md` → run Diablo gate ZERO on it before proceeding. Skip if input was already a PRD-NNN.

## STEP 2 — Outline read-before-start

```
mcp__outline__search_documents
  query: "<keywords from PRD>"
  collectionId: <project_collection_id>
  limit: 10
```

Look for:
- Existing ADRs (Decisions sub-page) — what tech was already chosen?
- Existing Epics — overlap with this PRD?
- Existing Tasks (T-NNN) — already addressed parts?

If overlap found → ask user: «PRD overlaps with existing X. Decompose only delta, or replace?»

## STEP 3 — Architecture (ADR generation) ← Diablo gate 1

Goal: identify 3-7 architectural decisions this PRD requires.

For each major design choice (DB, framework, auth, deploy, integrations, observability):

1. Check `docs/adr/` for existing decision — if exists and applicable → reuse, link from new ADRs
2. If no existing decision → propose 2-3 options via `decision-matrix` skill format
3. User picks one (AskUserQuestion)
4. Render `docs/adr/<NNNN>-<slug>.md` per existing template

**Diablo gate 1**:
Invoke `/da plan` against the full set of new ADRs.
Diablo attacks:
- Hidden decision NOT made — what didn't you choose because you didn't notice?
- Decisions that conflict with existing ADRs?
- Decisions made without alternatives considered?
- Decisions implying tooling/infra not in `docs/STACK.md`?

`BLOCKED` → user resolves, re-run gate. Loop until `ACCEPTABLE` / `PROCEED CAUTION`.

After gate: commit each ADR + auto-publish to Outline `Project: <name> / Decisions`.

## STEP 4 — Epic decomposition ← Diablo gate 2

Goal: split PRD work into 3-7 logical epic groups.

Heuristic for splitting (BMAD-inspired):
- One epic per major architectural slice (e.g. «Auth», «Data ingestion», «Reporting»)
- Each epic should deliverable ≥1 user story end-to-end
- Epics MUST be orderable — there should exist a dependency DAG between them

For each epic, propose:
- Title (1 line)
- Goal (1-2 sentences)
- User stories included (refs to PRD §5)
- Acceptance criteria (refs to PRD §6)
- Architectural ADRs constraining it (refs to STEP 3)
- Estimated tasks count (broad: 2-3 / 4-7 / 8+)
- Prerequisites: which other epics must complete first

Show user the proposed split with a dependency diagram (text):
```
EPIC-001: Auth foundation
EPIC-002: Data ingestion          (deps: 001)
EPIC-003: Dashboard               (deps: 001, 002)
EPIC-004: LLM-powered analysis    (deps: 002)
```

User confirms / refines.

**Diablo gate 2**:
Invoke `/da plan` against the epic split.
Diablo attacks:
- Epic missing — what work isn't covered by any epic?
- Epic overlap — two epics doing same thing?
- Wrong sequencing — does dep order respect technical reality (DB before API before UI)?
- Epic too big (≥10 tasks predicted) — should be split further?
- Epic too small (1 task) — should be inlined into adjacent epic?

`BLOCKED` → user resolves, re-run gate.

After gate: render `docs/epics/EPIC-NNN-<slug>.md` per epic, commit, auto-publish.

## STEP 5 — Task decomposition (per epic) ← Diablo gate 3

For each epic, generate ordered task list with deps.

For each task:
- Title + slug
- Parent epic (`parent_epic: EPIC-NNN`)
- Acceptance criteria (subset of epic's AC)
- Dependencies (`depends_on: [T-NNN, T-NNN]`)
- Estimated effort (S/M/L/XL — tshirt sizes; not hours)
- Risk level (Low/Med/High → routes to `/todo add` BQC matrix)

Spec format: same as `/todo add` produces, with extra `parent_epic` field.

Show user task list per epic. User confirms / refines.

**Diablo gate 3**:
Invoke `/da spec` against the FULL task set (cross-epic).
Diablo attacks:
- Missing prerequisite tasks (DB schema before queries; auth before protected routes)
- Hidden cross-epic deps (task in epic B implicitly needs task in epic A)
- Tasks that are actually multiple tasks
- Tasks with vague AC («works correctly» banned)
- Tasks duplicating prior closed T-NNN — not new work

`BLOCKED` → user resolves, re-run gate.

After gate: render `docs/specs/T-NNN-<slug>.md` per task with `parent_epic` field, append to TASK.md backlog in dependency order, optionally `gh issue create` per task.

## STEP 6 — verification-pass + humanizer

Load `verification-pass`. Re-verify all claims in:
- Each new ADR
- Each new EPIC
- Each new T-NNN spec

Catch any product/number claims that snuck through Diablo. Tag `[verified]` / `[unverified]` / `[contradicted]`. If contradicted → STOP, fix.

Load `humanizer`. Apply to all generated docs (ADRs, EPICs, T-NNN specs). Removes AI-text patterns. Once.

## STEP 7 — Commit batch

Single batch commit:
```bash
git add docs/prd/PRD-NNN-*.md \
        docs/adr/<new-ADRs>.md \
        docs/epics/EPIC-*.md \
        docs/specs/T-*.md \
        docs/TASK.md

git commit -m "[CHANGE] PRD-NNN decomposed: <N> ADRs, <M> epics, <K> tasks

PRD: <PRD-NNN>
Architecture: <list of new ADR-NNN>
Epics: <list of EPIC-NNN>
Tasks: <K total, breakdown per epic>

Diablo gates passed: 4 (PRD/ADR/Epic/Task)
Verification: <N verified, M unverified flagged>
Sources: <K external>"
```

## STEP 8 — Auto-publish to Outline

Per `.claude/.setup.json` flags:
- PRD updated → Outline `Project: <name> / PRDs / PRD-NNN`
- Each new ADR → `Project: <name> / Decisions`
- Each new EPIC → `Project: <name> / Epics`
- Tasks remain LOCAL (T-NNN specs in repo only — not noisy in Outline)

## STEP 9 — Confirm

```
✓ PRD-NNN decomposed
ADRs: <list> (Outline: Project / Decisions)
Epics: <list> (Outline: Project / Epics)
Tasks: <count> (TASK.md backlog, local only)

Next:
  /orchestrate           ← starts executing tasks in dependency order
```

---

## Hard rules

- 4 Diablo gates are MANDATORY. Skipping = decomposition that surprises during implementation.
- NEVER create epics without ADRs (BMAD v6 ordering)
- NEVER create tasks without parent_epic
- NEVER skip the dependency DAG check — orchestrator relies on it
- Tasks remain LOCAL by design — they churn too fast to mirror in Outline; ADRs and Epics are stable enough
- `verification-pass` is mandatory — catches what Diablo missed (different angle)
- If user can't answer architectural question → STOP, don't pick at random; ADR with «TBD» blocks downstream
