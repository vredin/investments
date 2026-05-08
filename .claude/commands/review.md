---
name: review
description: 'Full code review: code quality + security audit + QA hacker scan. Use before merging, before deploy, or on demand.'
argument-hint: [file or commit range, e.g. "HEAD~3..HEAD" or "src/api/"]
---

> **Style:** Load `caveman-distillate` skill — terse responses, no filler, fragments OK.

# Full Review Pipeline

Run a comprehensive review combining code quality, security, and adversarial QA.

## Arguments

TARGET: $ARGUMENTS

If TARGET is empty — review all changes since last `[CHANGE]` commit.

---

## STEP 1 — Determine scope

```bash
# If no target specified, find changes since last [CHANGE] or [BACKUP] commit
git log --oneline -20
git diff --name-only HEAD~1
```

Identify files to review. Read each file before reviewing.

---

## STEP 2 — Code Review

Invoke the `code-reviewer` agent on the identified files.
Focus: correctness, performance, maintainability.

---

## STEP 3 — Security Audit

Invoke the `Rex` agent (RED mode, CRITICAL+HIGH depth) on the same scope.
Focus: OWASP Top 10, secrets, auth bypass, injection, taint analysis.

---

## STEP 4 — QA Hacker Scan

Invoke the `qa-expert` agent on the same scope.
Focus: business logic abuse, input fuzzing, race conditions, IDOR.

---

## STEP 4.5 — Design Review (if frontend changes)

Check if scope includes `.tsx`, `.css`, `.scss`, `.html`, or `.vue` files.
If YES — invoke the `design-reviewer` agent.
Focus: responsiveness (mobile/tablet/desktop), accessibility WCAG 2.1 AA, interaction robustness.
If NO frontend files — skip this step.

---

## STEP 4.7 — Performance Analysis (if significant logic changes)

Check if scope includes business logic, DB queries, API routes, or React components.
If YES — invoke the `performance-analyzer` agent.
Focus: N+1 queries, missing indexes, bundle size, unnecessary re-renders, memory leaks.
If scope is only config/docs/styles — skip this step.

---

## STEP 4.9 — Diablo (mandatory)

Invoke `/da impl <scope>` (Diablo agent). Adversarial check across all the above findings.
Focus: hidden assumptions, edge cases the other agents missed, scope creep, test quality.

Diablo verdict goes into the consolidated report:
- BLOCKED → final verdict in STEP 5 must be REQUEST CHANGES regardless of other agents
- FIX FIRST → list FATAL items must be addressed before merge
- PROCEED WITH CAUTION → SUSPICIOUS items documented in PR description

---

## STEP 5 — Consolidated Report

Merge findings from all three agents into one report:

```
## Review Report — <date>

### Scope
- Files: <list>
- Commits: <range>

### Code Quality
<code-reviewer findings — MUST FIX / SHOULD FIX / CONSIDER>

### Security
<Rex findings — CRITICAL / HIGH / MEDIUM / INFO>

### QA Hacker
<qa-expert findings — CRITICAL / HIGH / MEDIUM / LOW>

### Design (if applicable)
<design-reviewer findings — BLOCKER / HIGH / MEDIUM / NITPICK>

### Performance (if applicable)
<performance-analyzer findings — CRITICAL / HIGH / MEDIUM / OK>

### Devil's Advocate
<Diablo findings — FATAL / SERIOUS / SUSPICIOUS, with VERDICT and Next step>

### Summary
- Total findings: <count by severity>
- Blocks merge: YES / NO
- Blocks deploy: YES / NO

### Verdict
APPROVED / REQUEST CHANGES / NEEDS DISCUSSION
```

---

## Rules
- All three agents must run — never skip security or QA
- If any CRITICAL finding exists — verdict is REQUEST CHANGES
- Cross-reference findings with `docs/FAILS.md` — flag recurrences
- If a new failure pattern is discovered, add to `docs/FAILS.md`
