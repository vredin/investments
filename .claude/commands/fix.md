---
name: fix
description: 'Fix a bug using the full disciplined process: git backup → write failing test → confirm failure → root cause analysis → fix → confirm passing → update docs → notify.'
---

> **Style:** Load `caveman-distillate` skill — terse responses, no filler, fragments OK.

You are fixing a bug. Follow ALL steps in order. Do NOT skip any step. Do NOT fix anything before step 5.

Arguments: $ARGUMENTS

---

## STEP 0 — Fetch context (if GitHub issue)

If arguments contain a GitHub issue number (e.g. `#123` or just `123`):
```bash
gh issue view $ISSUE_NUMBER
```
Read the issue title, body, labels, and comments. Use this as the bug description for all subsequent steps.

If arguments are plain text — use them directly as the bug description.

---

## STEP 1 — Git backup

Run `git add <tracked changed files> && git commit -m "[BACKUP] Pre-fix: $ARGUMENTS | Risks: unknown until root cause | Scope: TBD"`. Never use `git add -A` — it can stage secrets.
If nothing to commit, note it and continue.

---

## STEP 2 — Write a failing test

Before touching any implementation code:
- Identify the correct test file (Playwright e2e, pytest, vitest, etc.) based on the nature of the bug
- Write a minimal test that reproduces the exact problem described
- The test MUST fail before the fix is applied
- Save the test to the appropriate file

Ask the user: "Test written. Shall I run it to confirm it fails? [y/n]"

---

## STEP 3 — Run the test, confirm failure

Run the test. Show the output.
- If the test **PASSES** unexpectedly: stop, explain the test does not reproduce the problem, ask for more details
- If the test **FAILS** as expected: confirm "✓ Test fails — problem reproduced" and continue

---

## STEP 4 — Root cause analysis

Investigate the code:
- Read all relevant files
- Identify the exact root cause (not just symptoms)
- List 2–3 fix options with trade-offs and risks

Present the analysis to the user and ask: "Shall I proceed with fix option [recommended]? [y/n]"

---

## STEP 5 — Fix the problem + static checks

Apply the fix. Then run static checks per `docs/STACK.md`:
```bash
# Resolve commands from docs/STACK.md (lint_cmd, typecheck_cmd) — do NOT hardcode npx/uv.
$(grep '^lint_cmd:' docs/STACK.md | awk '{$1=""; print substr($0,2)}' | tr -d '"')
$(grep '^typecheck_cmd:' docs/STACK.md | awk '{$1=""; print substr($0,2)}' | tr -d '"')
```
Fix any static errors before proceeding.

---

## STEP 6 — Run the test again, confirm it passes

Run the same test from Step 2.
- If it **FAILS**: go back to Step 5
- If it **PASSES**: confirm "✓ Test passes — bug is fixed"

---

## STEP 6.5 — Same bug elsewhere?

Search the codebase for the same pattern that caused this bug:
```bash
grep -rn "<pattern that caused the bug>" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" | grep -v node_modules | grep -v __pycache__
```
If found in other files — fix ALL occurrences now. Do not leave known broken code for later.

---

## STEP 6.7 — Security Impact Check

Check if the fix touches security-sensitive files:
```bash
git diff HEAD --name-only | grep -iE "auth|session|payment|permission|upload|middleware|user|password|token|secret|crypto|hash|jwt|oauth"
```

If matches found **OR** if the bug itself is security-related (auth bypass, data leak, injection, IDOR, etc.) →
**Invoke `Rex` agent** in BLUE mode, passing:
- List of changed files
- Bug description: `$ARGUMENTS`

> "Verify that the fix for '$ARGUMENTS' in [changed files] is complete and does not introduce new vulnerabilities. Check: was the root cause a security pattern that requires broader remediation?"

Verdicts:
- **CLEAN** → proceed to STEP 7
- **New vulnerability introduced** → return to STEP 5, fix the new issue, loop back from STEP 6
- **Root cause is a security pattern with broader impact** → after STEP 7, add `[SEC-NNN]` entry to `docs/FAILS.md` documenting the vulnerability class, root cause, fix pattern, and detection method
- **Fix is incomplete** (same vulnerability reachable via different path) → fix all paths before proceeding

If no security-sensitive files changed AND bug is not security-related → skip this step.

---

## STEP 6.5 — E2E Test Gate (if fix touches frontend)

Detect if the fix touched frontend:
```bash
FRONT_CHANGED=$(git diff HEAD --name-only | \
  grep -E '\.(tsx|jsx|vue|svelte|html|css|scss)$|^app/routes/|^src/routes/' | head)
```

If non-empty:
- The failing test from STEP 2 should ALREADY be a Playwright `.spec.ts` (per E2E Test Discipline)
- If STEP 2 wrote a unit test instead — STOP. Return to STEP 2 and rewrite as Playwright e2e:
  ```
  E2E TEST GATE: REWRITE STEP 2
  
  Fix touches frontend (see files below) but the failing test is a unit test.
  Per E2E Test Discipline (.claude/rules/workflow.md), frontend bugs require
  Playwright e2e reproduction.
  
  Files: <FRONT_CHANGED>
  Existing test: <test from STEP 2>
  
  Action: rewrite as tests/e2e/<bug-slug>.spec.ts that reproduces the bug
  via real user interaction. Then continue from STEP 3.
  ```
- If STEP 2 already produced a Playwright `.spec.ts` — confirm it asserts observable behavior, then proceed.

If no frontend changes → skip.

---

## STEP 6.9 — Diablo (mandatory)

Invoke `/da impl <fix_scope>`. Diablo attacks the fix:
- Is this really the root cause, or just a symptom?
- Could the fix introduce a new bug?
- Is the test catching the right thing? (anti-regression check)
- Are there other call paths that hit the same bug?

Verdicts:
- BLOCKED → return to STEP 4 (root cause analysis)
- FIX FIRST → address FATAL findings, loop back from STEP 5
- PROCEED CAUTION / ACCEPTABLE → continue

---

## STEP 7 — Update documentation + auto-publish to Outline

### 7.1 — Local docs
- Update README or inline comments if the fix changes expected behavior
- Append entry to `docs/FAILS.md` if root cause is non-obvious. Format:
  ```
  ## F-NNN: <slug>
  
  **Symptom**: <one-line user-visible behavior>
  **Root cause**: <technical cause>
  **Fix pattern**: <what to apply when this recurs>
  **Detection**: <how to spot in other code: grep pattern, file pattern>
  ```

### 7.2 — Auto-publish to Outline (no prompt)

Read `.claude/.setup.json` → `outline.auto_publish.fails_to_shared`. If `true` (default):

```
mcp__outline__create_document
  title: "F-NNN: <slug>"
  collectionId: <outline.shared_kb_id>
  parentDocumentId: <Fails sub-page ID, if known>
  text: |
    ## Project
    <project name> (from CLAUDE.md or directory)
    
    ## Symptom
    <copy from FAILS.md>
    
    ## Root cause
    <copy>
    
    ## Fix pattern
    <copy>
    
    ## Detection
    <copy>
    
    ## Commit
    <SHA of the [CHANGE] commit fixing this>
  publish: true
```

If MCP outline disconnected or `auto_publish.fails_to_shared = false`:
- Skip silently — local FAILS.md is source of truth, Outline is replication
- Log: `[OUTLINE] auto-publish skipped (MCP unavailable or disabled)`

If user wants to suppress for this specific F-NNN — add `[NOPUB]` tag in FAILS.md
entry; auto-publish detects and skips.

---

## STEP 8 — Notify user

Present a concise summary:
```
✅ Fixed: <one line description>
Root cause: <one line>
Test: <test file and test name>
Files changed: <list>
```
