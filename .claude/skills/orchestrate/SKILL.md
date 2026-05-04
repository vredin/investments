---
name: orchestrate
description: "Conductor: autonomous multi-agent pipeline. Picks tasks from backlog, implements, verifies, loops until done or blocked."
argument-hint: "next-task | stabilize | write-tests"
---

# Orchestrate — Conductor Skill

You are the **conductor**. You orchestrate agents and skills as an autonomous pipeline.
The user gives a high-level goal; you break it into steps, delegate, collect results,
decide next action, and loop until done or blocked.

## Core Principles

1. **File-based state** — each step writes output to `artifacts/conductor/`. Next step reads files, not context.
2. **Keep/Discard git loop** — code change + quality gate pass = `[CHANGE]` commit (keep). Gate fail after 3 retries = `git checkout -- .` (discard).
3. **Append-only log** — every action logged to `artifacts/conductor/session.jsonl`.
4. **Don't stop** — loop until all work is done or you hit a true blocker.
5. **NEVER ask permission** — create todos, run agents, commit autonomously. Only stop if truly blocked (external service down, destructive git op requested, cost confirmation needed).
6. **UNSTOPPABLE BACKLOG RULE** — NEVER stop mid-execution while PLANNED items exist in the backlog. "Seems complex", "needs more info", "might break something" are NOT valid blockers — investigate and solve autonomously. Only stop if the task literally cannot proceed without a human action (missing credentials, physical device offline, money cost).
7. **SUBAGENT COMPLETION ≠ PIPELINE COMPLETION** — when any sub-step (analysis, fix, audit) returns a result, that is a STEP completion, not the pipeline end. Always check: are there PLANNED tasks? If yes → continue. Only stop when backlog is empty AND re-audit finds 0 new gaps.
8. **DA at every implementation** — run Devil's Advocate attack before every `[CHANGE]` commit. BLOCKED verdict = fix before committing.

---

## Sub-commands

Parse `$ARGUMENTS` to determine pipeline:

### `/orchestrate next-task`

Pick the highest-priority PLANNED task and execute it end-to-end.

```
Step 1: READ BACKLOG
  Read: docs/TASK.md
  Find: first PLANNED/Backlog task by priority
  If none → run audit (see below) OR report "backlog empty"

Step 2: SPEC CHECK
  Read: docs/specs/T-NNN-slug.md
  Verify AC is clear enough to implement
  If spec unclear: write missing AC, re-check

Step 3: IMPLEMENT
  [BACKUP] commit
  Implement all AC
  Run quality gate (lint + types + tests)
  DA implementation attack
  [CHANGE] commit with DA verdict

Step 4: UPDATE BACKLOG
  Mark task DONE in docs/TASK.md
  Append to docs/archive/TASK_ARCHIVE.md with commit hash
  Append to docs/timeline.md

Step 5: VAULT LEARNING REVIEW (mandatory — do not skip)
  Threshold (prevents junk entries): only write a vault entry if BOTH hold —
    (a) the fix/solution is non-obvious (would not be found by reading docs or grepping stdlib), AND
    (b) a second project on a different stack could plausibly hit the same issue.
  If either fails → log "no vault entry: <reason>" and move on. Per-session cap: max 3 vault writes.

  Ask: did this task surface a reusable cross-project lesson that meets the threshold?
    - Non-obvious fix reusable across projects → vault-write skill, type=fail
    - Reusable working solution / architecture pattern → vault-write skill, type=pattern
    - Wrong assumption about 3rd-party API / service / config → vault-write skill, type=gotcha

  If yes: invoke vault-write skill (`.claude/skills/vault-write/SKILL.md`)
    - Full 8-step protocol: dedup check → ID → create → log → hot.md → commit → report
    - One CRUD op = one commit in the vault repo

  INTERACTIVE GATE HANDLING (critical — orchestrate is autonomous, vault-write is not):
    vault-write blocks on AskUserQuestion for two conditions —
      (1) dedup grep hit with >70% topical overlap
      (2) contradiction with an existing entry from another project
    The orchestrator MUST NOT block on these. On either gate:
      - Abort the vault-write for this cycle (do not commit a half-written entry)
      - Append one line to `artifacts/conductor/session.jsonl`:
        `{"ts":"…","task":"T-NNN","vault-escalation-needed":"dedup|contradiction","candidate-title":"…","existing-id":"F-NNN"}`
      - Continue with Step 6 (NEXT) — user reviews escalation queue later
    Never silently pick branch (a) / (b) / (c) on contradictions — that corrupts the vault's authorship wall.

  If the lesson is project-specific only (schema names, local services): append to docs/KNOWLEDGE.md instead
  If nothing reusable: log "no vault entry" in artifacts/conductor/session.jsonl and continue

Step 6: NEXT
  Check docs/TASK.md for more PLANNED items
  If exist → back to Step 1
  If empty → run /audit → continue from new tasks
```

### `/orchestrate stabilize`

Run tests, fix failures, loop until green.

```
Step 1: RUN TESTS
  [adapt command to project stack]
  Output: test results

Step 2: ANALYZE
  Classify failures: logic error / locator drift / state race / infra
  If 0 failures → report green, STOP

Step 3: FIX (per failure, max 3 retries each)
  [BACKUP] commit
  Apply fix
  Re-run failing test only
  Pass → [CHANGE] commit
  3x fail → git checkout -- . → mark BLOCKED → continue with next failure

Step 4: RE-RUN ALL → back to Step 1
  Max 5 total loops
```

---

## State Management

### Session log: `artifacts/conductor/session.jsonl`

Append one JSON line per action:
```json
{"ts": "2026-01-01T09:00:00Z", "cmd": "next-task", "step": "implement", "task": "T-042", "result": "done", "commit": "abc123"}
{"ts": "2026-01-01T09:05:00Z", "cmd": "next-task", "step": "implement", "task": "T-043", "result": "blocked", "reason": "missing API key"}
```

### Resume protocol

On start, check `artifacts/conductor/session.jsonl`:
- If exists: read last entry → "Resuming from step {step}" → continue
- If not: fresh start

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Quality gate fails | Log, retry fix (max 3), then discard + mark BLOCKED |
| DA returns BLOCKED | Fix the issue, re-run DA, do not commit |
| Spec missing or unclear | Write missing spec sections, then continue |
| Backlog empty | Run project audit → generate new tasks → continue |
| Context > 70% full | Write `artifacts/conductor/handoff.md`, tell user to restart |
| External service unavailable | Log as infrastructure blocker, move to next task |

---

## What This Skill Does NOT Do

- Does NOT push to remote or create PRs without explicit user confirmation
- Does NOT run operations with significant cost (cloud, paid APIs) without confirmation
- Does NOT modify `CLAUDE.md`, rules, or agent definitions
- Does NOT skip DA review before `[CHANGE]` commits
