---
name: self-audit
description: 'Analyze recent sessions for recurring failure patterns and propose diff-ready improvements to template rules/commands. Run weekly via /loop.'
argument-hint: [--global | --since YYYY-MM-DD]
allowed-tools: Read, Write, Bash, Grep, Glob
model: opus
---

> **Style:** Load `caveman-distillate` skill.

# /self-audit — Process improvement loop

Mode:
- (no args) — local: analyze this project's sessions only
- `--global` — aggregate across all projects via Outline
- `--since YYYY-MM-DD` — explicit period

---

## Why this command exists

`docs/FAILS.md` and Outline `Knowledge Base / Fails` log WHAT broke. They don't change WHY it kept breaking.

Self-audit reads the failure log, finds patterns, and proposes **diff-ready** changes to:
- `.claude/rules/workflow.md`
- `.claude/rules/skill-routing.md`
- `.claude/commands/*.md`
- agents

Output is a remediation file the user can apply or reject. Each suggestion has exact file path, exact old text, exact new text.

---

## STEP 1 — Gather data

### Local mode (default)
```bash
# Sessions covered
SINCE="${SINCE:-$(date -v-7d +%Y-%m-%d)}"

# 1. Recent fails: grep FAILS.md and search Outline
grep -A 5 "## F-" docs/FAILS.md | grep -B 1 "$SINCE" || true
mcp__outline__search_documents query="<project_name>" collectionId=<fails_subpage>

# 2. Stuck Protocol triggers (from handoffs)
grep -r "Stuck Protocol\|3rd attempt" docs/reports/ docs/handoff.md 2>/dev/null

# 3. Workflow rules ignored (transcript heuristic)
# - BACKUP commits skipped before edits → check git log for [BACKUP] before [CHANGE]
git log --pretty="%H %s" --since="$SINCE" | \
  awk '/\[CHANGE\]/{change=$0; getline prev; if (prev !~ /\[BACKUP\]/) print "MISSING_BACKUP:", change}'

# 4. /todo skipped (changes without spec)
git log --pretty="%s" --since="$SINCE" | grep -E "T-[0-9]+" | sort -u > /tmp/changes_with_T
ls docs/specs/T-*.md 2>/dev/null | sed 's|.*T-||;s|-.*||' > /tmp/specs
comm -23 <(sort /tmp/changes_with_T) <(sort /tmp/specs) || true
```

### Global mode (`--global`)
1. `mcp__outline__search_documents` query=`F-` collectionId=`<shared_kb_fails>` limit=200
2. Group by tag/title prefix (project name).
3. Identify failures appearing in ≥3 projects → template-level issue.

---

## STEP 2 — Pattern detection

Cluster gathered evidence by category:

| Category | Signal | Threshold |
|---|---|---|
| Recurring fail class | Same root cause appears in N fails | N ≥ 3 (local), ≥ 3 projects (global) |
| Workflow violations | Step skipped repeatedly | ≥ 5 occurrences in period |
| Skill not loaded when needed | task type matches skill, but not loaded | ≥ 3 occurrences |
| Command missing | shell commands run that should be a slash command | same shell pattern ≥ 5 times |
| Time wasted in rabbit holes | Stuck Protocol triggered | every occurrence is a finding |

For each category, generate finding:
```
PATTERN [<category>] (×<count>): <one-line description>

Evidence:
  - <fail/event 1, with link>
  - <fail/event 2>
  - ...

Root cause: <what process gap allows this>

Suggested fix:
  File: <exact path>
  Old text: <quote, ≤3 lines>
  New text: <proposed replacement, ≤5 lines>
  Rationale: <why this fix prevents future occurrences>
```

---

## STEP 3 — Output remediation file

Write to `docs/SELF-AUDIT-<DATE>.md`:

```markdown
# Self-Audit — <PROJECT or GLOBAL> — <DATE>
Period: <SINCE> to <today>

## Summary
- Patterns found: N
- Suggested file changes: M
- Severity: <high if any pattern with ≥5 occurrences, medium if ≥3, low otherwise>

## Findings
<one block per pattern, format from STEP 2>

## Apply
For each finding, user reviews and either:
- Accepts → user runs the suggested edit (manually or via "apply finding K")
- Rejects → mark `REJECTED: <reason>` in this file (audit memory for next run)
- Defers → mark `DEFERRED: <until>`

## Audit memory
Previous audits and their outcomes:
- <DATE>: N findings, K accepted, M rejected, J deferred
```

---

## STEP 3.5 — humanizer pass on remediation file (mandatory)

The remediation file (`docs/SELF-AUDIT-<DATE>.md`) is **read by humans** — you decide which findings to apply. Apply `humanizer` skill to:
- Pattern descriptions
- Root cause prose
- Rationale lines

Diff blocks (file path, old text, new text) pass through unchanged — those are exact citations.

---

## STEP 4 — Apply (optional)

If user says `apply finding K` after reading the audit:
1. Read finding K from `docs/SELF-AUDIT-<DATE>.md`.
2. Verify the `Old text:` exists at the named file path.
3. Use Edit tool to replace.
4. Mark finding as `APPLIED: <commit_sha>` in audit file.
5. Commit with message: `[PROCESS] Apply self-audit finding: <one-line>`.

---

## STEP 5 — Global aggregation (only `--global`)

After local report:
1. Post the audit summary as Outline doc: `Knowledge Base / Best Practices / process-audit-<DATE>`.
2. If a pattern affects ≥3 projects → propose a **template-level** change (path = `~/PycharmProjects/1claude-project-template-*/.claude/...`), not a per-project change.

---

## Hard rules

- Output format MUST include exact file path + exact old text + exact new text. No "consider adding...", "you might want to...".
- "Be more careful" / "pay attention to X" — banned outputs. Auto-rejected.
- Findings without ≥3 supporting evidence items are filtered out (signal vs noise).
- Audit memory: if a finding is REJECTED, do not propose the same fix in subsequent audits unless new evidence emerges.

---

## Designed for /loop

```bash
# Local weekly Friday 10:00
/loop "0 10 * * 5" /self-audit

# Global bi-weekly 1st and 15th 11:00
/loop "0 11 1,15 * *" /self-audit --global
```
