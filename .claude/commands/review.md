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

## STEP 4.6 — E2E Test Gate (if frontend changes)

Detect frontend changes in the scope:
```bash
FRONT_CHANGED=$(git diff --name-only $TARGET 2>/dev/null | \
  grep -E '\.(tsx|jsx|vue|svelte|html|css|scss)$|^app/routes/|^src/routes/|^app/api/|^src/api/' | head)
```

If frontend changes detected → check Playwright spec is in same diff:
```bash
SPEC_ADDED=$(git diff --name-only $TARGET 2>/dev/null | \
  grep -E 'tests?/e2e/.*\.spec\.(ts|js)$|tests?/e2e/.*\.test\.(ts|js)$')
```

**Decision:**
- `FRONT_CHANGED` is non-empty AND `SPEC_ADDED` is empty → **BLOCKED**:
  ```
  E2E TEST GATE: BLOCKED
  
  Frontend files changed:
  <list>
  
  No Playwright .spec.ts found in same diff.
  
  Action:
    1. Invoke test-writer agent for the changed feature
    2. Test-writer outputs tests/e2e/<slug>.spec.ts
    3. Confirm test FAILS without the implementation (red)
    4. Confirm test PASSES with the implementation (green)
    5. Add test to commit
    6. Re-run /review
  
  See: .claude/skills/webapp-testing/SKILL.md
  See: .claude/rules/workflow.md → E2E Test Discipline
  ```
- `FRONT_CHANGED` non-empty AND `SPEC_ADDED` non-empty → verify quality:
  - Read the spec file(s) added
  - Confirm at least one `expect(...)` assertion exists
  - Confirm assertions target observable behavior (visible text / URL / element state), NOT trivially-true (`expect(true).toBe(true)`)
  - Confirm test goes against real app URL, not mocked
  - Diablo will deeper-attack test quality in STEP 4.9
- No frontend changes → skip this step

**Edge case — frontend change with explicit "no behavior change":**
If user states the change is CSS-only with no visual diff (e.g. variable rename, dead code removal), exemption is allowed ONLY IF:
1. User explicitly states this in the PR description
2. There's a corresponding `toHaveScreenshot()` test that confirms no visual diff
3. Diablo agrees the change is genuinely behaviorless (not a hidden behavior change)

Otherwise: BLOCKED.

---

## STEP 4.7 — Performance Analysis (if significant logic changes)

Check if scope includes business logic, DB queries, API routes, or React components.
If YES — invoke the `performance-analyzer` agent.
Focus: N+1 queries, missing indexes, bundle size, unnecessary re-renders, memory leaks.
If scope is only config/docs/styles — skip this step.

---

## STEP 4.8 — Static Analysis Tier 2 (Python projects only)

Tier 1 (ruff + mypy) runs every commit. Tier 2 catches what ruff doesn't: cross-file dead code + duplicate code blocks.

**This step is self-bootstrapping. User does NOT manually install anything.**

### Detect Python project
```bash
([ -f pyproject.toml ] && grep -q "requires-python\|\[tool\.ruff" pyproject.toml) || [ -f setup.py ] || [ -f requirements.txt ]
```
If not Python → skip this step.

### Auto-install on first run
```bash
# Check if vulture is in dev deps
if ! uv run vulture --version >/dev/null 2>&1; then
  echo "Tier 2 first-run: installing vulture + pylint"
  uv add --dev vulture pylint
fi
```

### Auto-create whitelist on first run
```bash
if [ ! -f .vulture_whitelist.py ] && ! grep -q '\[tool\.vulture\]' pyproject.toml 2>/dev/null; then
  echo "Tier 2 first-run: creating .vulture_whitelist.py from template"
  cp templates/.vulture_whitelist.py.template .vulture_whitelist.py
  echo ""
  echo "Created .vulture_whitelist.py with FastAPI/SQLAlchemy/Pydantic/pytest defaults."
  echo "It silences known-good patterns. You can customize later if needed."
  echo ""
fi
```

### Run Tier 2
```bash
# Dead code (cross-file unused functions/classes/imports)
uv run vulture src/ .vulture_whitelist.py --min-confidence 80 --exclude tests/,migrations/,alembic/

# Duplicate code blocks (only this checker, not full pylint)
uv run pylint --disable=all --enable=duplicate-code src/
```

### Findings interpretation
- vulture confidence=100 → almost always real dead code → MUST FIX
- vulture confidence 80-99 → triage manually → SHOULD FIX (could be framework-implicit usage)
- pylint duplicate-code → always real (token-based) → SHOULD FIX (extract function/class) or document why intentional

### What Claude reports back to user

After running:
- Findings sorted by confidence/severity
- For each high-confidence vulture finding: file:line + suggestion to delete
- For pylint duplicate findings: pair of file:line ranges + suggestion to extract
- If many false positives detected → suggest specific entries to add to `.vulture_whitelist.py`

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

### Static Analysis Tier 2 (Python only, if applicable)
<vulture findings — confidence 100 / 80-99>
<pylint duplicate-code findings — file:line pairs with similarity score>

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
