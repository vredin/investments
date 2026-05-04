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

Apply the fix. Then run appropriate static checks:
```bash
# TypeScript/React:
npx tsc --noEmit

# Python:
uv run ruff check <changed_files>

# Node.js:
npm run lint
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
- **Root cause is a security pattern with broader impact** → after STEP 7, use the `vault-write` skill to create a `fail` entry in the shared vault (severity: critical, domain: auth/csrf/injection/etc.) documenting the vulnerability class, root cause, fix pattern, and detection method. Reusable across projects.
- **Fix is incomplete** (same vulnerability reachable via different path) → fix all paths before proceeding

If no security-sensitive files changed AND bug is not security-related → skip this step.

---

## STEP 7 — Update documentation

If applicable:
- Update README or inline comments if the fix changes expected behavior
- Note the root cause pattern for future reference

---

## STEP 8 — Notify user

Present a concise summary:
```
✅ Fixed: <one line description>
Root cause: <one line>
Test: <test file and test name>
Files changed: <list>
```
