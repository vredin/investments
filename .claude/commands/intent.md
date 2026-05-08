---
name: intent
description: 'Greenfield entry — convert vague intent ("хочу систему X") into a structured PRD via research + Diablo + verification. Outputs docs/prd/PRD-NNN.md, ready for /decompose. Use when no requirements exist yet.'
argument-hint: <vague intent or path to brief>
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion, WebSearch, WebFetch, Glob, Grep
model: opus
---

> **Style:** Load `caveman-distillate` skill — terse, evidence-first.

# /intent — Vague idea → PRD

Input: **$ARGUMENTS** (one-line intent OR path to brief document)

If `$ARGUMENTS` is a file path that exists → read it. Otherwise treat as intent text.

This command produces a PRD. **Does not** create epics or tasks. After PRD is finalized,
run `/decompose PRD-NNN` to split into epics → tasks.

For full multi-stage analysis (decision matrix on solution variants, deep research):
this command runs a compact version of that. For full requirements analysis, use the
external `requirements-analyzer` framework first, then run `/decompose` on its output.

---

## STEP 1 — Pre-flight

1. Check that `docs/prd/` exists; create if not (`mkdir -p docs/prd`)
2. Find next free PRD-NNN number: `ls docs/prd/PRD-*.md 2>/dev/null | grep -oE 'PRD-[0-9]+' | sort -r | head -1`
3. Load skills: `spec-normalizer`, `verification-pass`, `humanizer`, `decision-matrix`, `planning`

## STEP 2 — Outline read-before-start (mandatory)

Search Outline before starting — may already be a similar product / pattern documented.
```
mcp__outline__search_documents
  query: "<keywords from intent>"
  collectionId: <shared_kb_id>      # Best Practices + Tricks
  limit: 5

mcp__outline__search_documents
  query: "<keywords>"
  collectionId: <project_collection_id>   # existing PRDs in this project
  limit: 5
```

If similar PRD found in same project → ask user: «Existing PRD-XX covers this. Extend it, or create new?» Don't silently create duplicates.

## STEP 3 — Research (compact, NOT 8-stage requirements-analyzer)

Three parallel research questions:
1. **What exists** — search GitHub / awesome-lists / docs for existing solutions in this domain. WebSearch + WebFetch on top 3 hits. Aim: 5-min recon, not 50-min deep dive.
2. **What's the simplest possible MVP** — single sentence definition.
3. **Build vs buy** — is there an off-the-shelf option that solves 80%?

Output (mental, not yet written): brief notes for STEP 4.

## STEP 4 — Propose 2-3 solution variants

Use `decision-matrix` skill format. Axes (auto-pick from `decision-matrix/axes-library.md`):
- Implementation effort (weeks)
- Maintenance burden (ongoing)
- User-facing fit (features delivered)
- Reversibility (lock-in)
- Cost ($)

Each cell = `{score, confidence, source_id}` per skill rules — NEVER bare numbers.

Variants to consider:
- A: Minimal MVP from scratch (lowest scope)
- B: Build on existing OSS (e.g. fork + customize)
- C: Buy / SaaS adapter (lowest effort)

Show matrix to user. Ask: «Which variant for the PRD? [A/B/C/refine matrix/skip — describe own]»

## STEP 5 — Compose PRD via spec-normalizer

Load `spec-normalizer` skill. Apply its YAML structure to the chosen variant.

Render to `docs/prd/PRD-NNN-<slug>.md` with these sections:

```markdown
# PRD-NNN: <Title>

**Created**: YYYY-MM-DD
**Status**: Draft → Review → Accepted → Implemented
**Source**: <intent / brief / contract>

## 1. Problem
What user pain does this solve? One paragraph.

## 2. Users
Primary user persona + their context. Who is NOT a user (out of scope)?

## 3. Goals (measurable)
- [ ] Functional: <observable outcome>
- [ ] Non-functional: <perf/security/uptime target>

## 4. Non-goals
What we explicitly do NOT solve.

## 5. User stories
- As a <role>, I want to <action>, so that <outcome>.
(3-7 stories; if more, this should be split into multiple PRDs)

## 6. Acceptance criteria (measurable)
For each goal in §3, what is the testable assertion?

## 7. Solution variant chosen
Reference to decision matrix from /intent STEP 4.
**Trade-offs accepted**:
- Gave up: <X>
- In favour of: <Y>

## 8. Risks (top 5)
| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|

## 9. Phasing (optional — if PRD spans >1 sprint)
- Phase 1 (MVP): <minimum to deliver §3.functional[0]>
- Phase 2 (v1): ...
- Phase 3 (later): ...

## 10. Open questions
Unanswered things to be resolved during /decompose.

## Sources
[1] URL — what was confirmed via WebFetch on YYYY-MM-DD
[2] ...
```

## STEP 6 — Diablo gate on PRD (mandatory)

Invoke `/da spec docs/prd/PRD-NNN-<slug>.md`.

Diablo MUST attack:
- §1 Problem too vague?
- §3 Goals not measurable? («хорошо работает» is banned)
- §4 Non-goals missing — what will scope-creep into?
- §6 Acceptance criteria reflective of goals?
- §8 Risks: are top 5 real or strawmen?
- §9 Phasing realistic per Phase 1?
- §10 Open questions are real (not «we'll figure out later» = blocker)

If verdict is `BLOCKED` or `FIX FIRST`:
1. Report Diablo findings to user
2. User addresses (ask via `AskUserQuestion` if scope decisions needed)
3. Update PRD-NNN
4. Re-run Diablo
5. Loop until `ACCEPTABLE` or `PROCEED CAUTION`

## STEP 7 — verification-pass

Load `verification-pass` skill. For every claim in the PRD that contains:
- Numerical metrics (percentages, $, time)
- Product / library names
- Third-party feature claims
- External standards (ISO, OWASP, etc.)

→ verify via WebFetch / WebSearch. Tag each as `[verified]` / `[unverified]` / `[contradicted]`.

If ≥1 contradicted → STOP, fix the PRD, re-verify.

## STEP 8 — humanizer pass

Load `humanizer` skill. Apply anti-AI-text patterns to the PRD draft. Removes "delve", "tapestry", em-dash overuse, sycophantic openers. PRD reads natural.

## STEP 9 — Commit

```bash
git add docs/prd/PRD-NNN-<slug>.md
git commit -m "[CHANGE] PRD-NNN: <title>

Variant chosen: <A/B/C from STEP 4>
Diablo verdict: ACCEPTABLE
Verified claims: N
Sources: K external"
```

## STEP 10 — Auto-publish to Outline

Read `.claude/.setup.json` → `outline.auto_publish.adrs_to_project` (PRDs use same flag).

If `true` (default):
```
mcp__outline__create_document
  title: "PRD-NNN: <title>"
  collectionId: <project_collection_id>
  parentDocumentId: <PRDs sub-page id>
  text: <full PRD markdown>
  publish: true
```

## STEP 11 — Confirm + suggest next

```
✓ PRD-NNN: <title> created
File: docs/prd/PRD-NNN-<slug>.md
Outline: <url or "skipped — MCP unavailable">
Diablo: ACCEPTABLE (or PROCEED CAUTION + N items)
Status: Draft

Next:
  /decompose PRD-NNN     ← split into architecture decisions, epics, tasks
```

---

## Hard rules

- NEVER skip Diablo gate (STEP 6) — that's the whole point of this command
- NEVER skip verification-pass (STEP 7) — galmlucinations get caught here
- If user can't answer key questions in PRD →  STEP 10's "Open questions" section gets entries; do NOT silently invent
- PRD is a contract for the team. If acceptance criteria aren't measurable, the PRD is wrong; don't ship.
- /decompose is a separate command — this command does NOT auto-trigger it. PRD must be reviewed before decomposition.
