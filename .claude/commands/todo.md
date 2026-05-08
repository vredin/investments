---
name: todo
description: 'Manage active task list in docs/TASK.md. Usage: /todo [add <text>] [done <id>] [start <id>] [list]'
---

> **Style:** Load `caveman-distillate` skill — terse responses, no filler, fragments OK.

Manage the active task list in `docs/TASK.md`.

Arguments: $ARGUMENTS

---

## Actions

### `/todo` or `/todo list`
Read `docs/TASK.md` and show a formatted table of In Progress + Backlog tasks.

---

### `/todo add <description>`

This is NOT a simple append. Follow ALL steps:

**STEP 1 — Grill the user (replaces ConfidenceChecker)**

Load skill: `.claude/skills/grill-me/SKILL.md`.

Walk the decision tree for the new task. **One question at a time.** Provide a recommended answer with each question. Resolve each branch's dependencies before moving to the next.

If a question can be answered by exploring the codebase — explore first, ask only if the codebase doesn't answer.

Stop conditions (any one):
- Shared understanding is reached (no remaining unknowns)
- User says "enough" or "skip the rest"
- 5 questions asked without new information surfacing → escalate: "Specs may be premature; consider /general first to investigate."

What to grill:
- Which files/components/screens are affected?
- Current vs expected behavior — quote actual current behavior, not assumed
- Acceptance criteria — measurable, not "works correctly"
- Edge cases not mentioned (empty / null / Unicode / huge / concurrent)
- Failure modes the user hasn't considered
- Dependencies on other tasks, external systems, or in-flight work
- Scope: one task vs split? too narrow? too broad?

**STEP 3 — Research the problem**

Read the relevant code. Understand what exists, what's broken, what constraints apply.
Use Context7 / WebSearch if the task involves external libraries or APIs you're unsure about.

**STEP 4 — Write a Structured Spec**

Create `docs/specs/T-NNN-slug.md`:

```markdown
# T-NNN: <title>

**Created**: YYYY-MM-DD
**Risk**: Low | Medium | High
**Status**: Backlog

## 1. Overview
2-3 sentences: what, why, how it fits the product.

## 2. Objectives
- [ ] Specific measurable objective 1
- [ ] Specific measurable objective 2

## 3. Prerequisites
- Required tasks / tools / env

## 4. Scope
**In scope**: what will be built
**Out of scope**: what is explicitly deferred

## 5. Technical Approach
Architecture, design patterns, affected files.

## 6. Deliverables
| File | Purpose |
|------|---------|
| path/to/file | description |

## 7. Success Criteria
- Functional: what must work
- Tests: what tests must pass

## 8. Implementation Notes & BQC Risks
| If task involves... | Risk | Mitigation |
|---------------------|------|------------|
| State mutation | Duplicate-trigger | Optimistic lock / disabled state |
| External API | Timeout / failure | Timeout + backoff + error boundary |
| Auth resource | Auth bypass | Enforce auth at resource boundary |
| Write path | Data loss | Transaction + compensation |
| UI fetch | Missing states | Loading / empty / error states |

## 9. Testing Strategy
- Unit: ...
- Integration: ...
- E2E: ...
- QA Hacker: adversarial cases

## 10. Layer Impact Map
| Layer | Impact | Files |
|-------|--------|-------|
| [e.g. API routes] | high | [e.g. src/routes/cameras.py] |
| [e.g. DB models] | low | — |
| [e.g. Frontend] | medium | [e.g. src/components/List.tsx] |
| [e.g. Tests] | high | [e.g. tests/test_feature.py] |

## 11. Red Flags
- <hidden dependency that could break unexpectedly>
- <assumption that might be wrong>
- <part of the spec that is vague or contradictory>

## 12. Dependencies
- External libraries
- Cross-task dependencies
```

**STEP 4.5 — Security Threat Assessment**

Determine if the task touches any security-sensitive area:
- Authentication, authorization, session management
- Payments, financial transactions, balances, credits
- File uploads, downloads, storage
- User data, PII, sensitive information
- External API integrations, webhooks, OAuth
- Permissions, roles, access control, admin functions
- Cryptography, tokens, secrets, password handling

If YES → **Invoke `Rex` agent** in RED mode:
> "Review spec T-NNN for security risks. Identify attack vectors this feature introduces, missing security controls in the technical approach, and adversarial test scenarios."

Map Rex output into the spec:
- **Section 8 (BQC Risks)** — add each security risk as a row with mitigation
- **Section 9 (QA Hacker)** — add adversarial test cases (auth bypass, IDOR, injection, race conditions)
- **Section 11 (Red Flags)** — add security red flags from the analysis

Verdicts:
- **CRITICAL risk in spec** → revise Section 5 (Technical Approach) before proceeding. Do NOT add to backlog with an unmitigated CRITICAL.
- **HIGH risk** → mitigation must be explicit in Section 8 before proceeding.
- **CLEAN** → add note to Section 8: "Security-reviewed: no threats identified."

If task does NOT touch security-sensitive areas → skip this step.

---

**STEP 5 — Add to TASK.md**

1. Read `docs/TASK.md`
2. Assign next available T-NNN id
3. Add row to Backlog with link to spec

**STEP 6 — Create GitHub Issue**

```bash
gh issue create \
  --title "T-NNN: <title>" \
  --body "$(cat docs/specs/T-NNN-slug.md)" \
  --label "backlog"
```

**STEP 7 — Confirm**
```
✓ T-NNN added: <title>
Risk: <level>
Spec: docs/specs/T-NNN-slug.md
GitHub: <issue URL or "skipped">
```

---

### `/todo done <id>`
1. Read `docs/TASK.md`
2. Get latest commit: `git log -1 --format="%h %s"`
3. Remove row from In Progress / Backlog
4. Append to `docs/archive/TASK_ARCHIVE.md`: `| T-NNN | Task | YYYY-MM-DD | <commit> |`
5. Close GitHub issue: `gh issue close <number> --comment "Done in <commit>"`
6. Confirm: "✓ Task <id> archived with commit <hash>"

---

### `/todo start <id>`
1. Read `docs/TASK.md`
2. Move row Backlog → In Progress
3. Confirm: "✓ Task <id> moved to In Progress"

---

## Notes
- `/todo` is STRICTLY planning only — never write implementation code
- Completed tasks go to `docs/archive/TASK_ARCHIVE.md` — NEVER stay in TASK.md
- Archive entries MUST include git commit hash
- grill-me is mandatory for `/todo add` — never skip it (replaces v2 ConfidenceChecker)
- After spec is written and grill-me yields shared understanding, Diablo (`/da spec T-NNN`) is invoked automatically before backlog add
