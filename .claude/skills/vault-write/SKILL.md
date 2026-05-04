---
name: vault-write
description: "Write a fail / pattern / gotcha to the shared cross-project knowledge vault at {{VAULT_PATH}}/. Use when a non-obvious fix, reusable pattern, or surprising API/service truth is encountered during work in any project. Replaces deprecated local docs/FAILS.md and docs/PATTERNS.md."
---

# vault-write — Write to shared knowledge vault

## When to use

Invoke this skill when, during work in any project, you need to record:

- **A fail** — reproducible bug with root cause and fix (e.g., "Playwright hangs on iOS Simulator when using `waitUntil: 'load'`")
- **A pattern** — reusable solution that works well and could apply to other projects (e.g., "SQLAlchemy async: engine per-process, sessionmaker per-request")
- **A gotcha** — non-obvious truth about an API / service / config that burned you (e.g., "Meta test phone numbers silently drop real broadcasts")

Do NOT use for:
- Project-specific architecture decisions → `docs/KNOWLEDGE.md` (stays local)
- Active tasks → `docs/TASK.md` (stays local)
- Code itself → the project repo (stays local)

## Vault location

```
{{VAULT_PATH}}/
```

All paths below are relative to this root.

## Full protocol (MANDATORY — do all steps, in order)

### STEP 1 — Read the vault contract

Read these two files **every time** before writing (they define rules that may have been updated):

1. `{{VAULT_PATH}}/CLAUDE.md` — CRUD policy, contradiction protocol, status lifecycle
2. `{{VAULT_PATH}}/meta/taxonomy.md` — allowed values for `stack` / `domain` / `project-context`

If you need a taxonomy value that does not exist:
1. Edit `meta/taxonomy.md` to add it in the right section (alphabetical within group).
2. Commit separately: `[vault] TAXONOMY add <field>:<value>`.
3. Then proceed to STEP 2.

### STEP 2 — Dedup check

Before creating a new note, search the vault for existing notes on the same topic:

```bash
cd {{VAULT_PATH}}

# Folder depends on type
FOLDER=fails   # or patterns / gotchas

# Grep titles and body keywords
grep -rli "keyword1\|keyword2\|keyword3" "$FOLDER/" | head -10
```

For each candidate result, read the file and compare:
- If topical overlap is **>70%** → STOP. Use `AskUserQuestion` to ask the user:
  > "Знайдено існуючий запис `F-NNN` — `<title>` (source: `<project>`). Варіанти:
  > (a) доповнити існуючий (тільки якщо source-project збігається з поточним)
  > (b) створити новий із `related: [[F-NNN]]`
  > (c) скасувати"
- If overlap is **<70%** → proceed to STEP 3.

### STEP 3 — Determine the new ID

Scan the folder for the highest existing ID:

```bash
ls {{VAULT_PATH}}/fails/ | grep -oE '^F-[0-9]+' | sort -V | tail -1
```

Increment by 1. Zero-pad to 3 digits (`F-001`, `F-042`, `F-123`). Same scheme for `P-NNN` (patterns) and `G-NNN` (gotchas).

### STEP 4 — Create the note

Copy the appropriate template:

```bash
cp {{VAULT_PATH}}/meta/templates/fail.md \
   {{VAULT_PATH}}/fails/F-042-short-slug.md
```

Slug rules: 4-6 meaningful words, lowercase, dashes, no stop-words.

Fill the frontmatter **completely**:

```yaml
---
id: F-042
type: fail
title: Short descriptive title
stack: [<values from taxonomy>]
domain: [<values from taxonomy>]
project-context: [<values from taxonomy>]
severity: warning
status: active
created: <today's ISO date>
source-project: <current project folder name under ~/PycharmProjects/>
related: []
contradicts: []
superseded-by: null
---
```

`source-project` is mandatory and must match the project you are currently working in — this is the authorship wall (see vault CLAUDE.md § CRUD Policy § UPDATE).

Fill the body following the template structure (symptom / root cause / fix / detection / source).

### STEP 5 — Append to log.md

Add one line to `{{VAULT_PATH}}/log.md`:

```
YYYY-MM-DD HH:MM  CREATE  F-042  "Short title"  source=<project>
```

Never edit past entries. Never sort. Append only.

### STEP 6 — Update hot.md

Edit `{{VAULT_PATH}}/hot.md`:

1. Push a new entry to the top (under the header), following the format in the HTML comment at the bottom of that file.
2. If total entry count exceeds 20, remove the oldest (bottom) entry.

### STEP 7 — Git commit (one commit per operation)

```bash
cd {{VAULT_PATH}}
git add fails/F-042-short-slug.md log.md hot.md
git commit -m "[vault] CREATE F-042 from <source-project>"
```

Commit message format (see vault CLAUDE.md § Git safety net):
- `[vault] CREATE F-NNN from <project>`
- `[vault] UPDATE F-NNN from <project> (own-entry edit)`
- `[vault] CONTRADICT F-NNN by <project> via F-MMM`
- `[vault] SUPERSEDE F-NNN → F-MMM (user approved)`
- `[vault] OBSOLETE F-NNN (reason)`
- `[vault] TAXONOMY add <field>:<value>`

Forbidden: `git reset --hard`, `git push --force`, `git clean -fd`, `--amend`.

### STEP 8 — Report to user

Short report:
```
✅ Vault write: F-042 "Short title" → fails/F-042-short-slug.md
Committed: [vault] CREATE F-042 from <project>
```

## Contradiction handling

If during STEP 2 (dedup) you discover existing info that **contradicts** what you are about to write (not duplicates — contradicts):

1. **Do not edit the existing note body.**
2. Create your new note normally (STEPS 3-4) with `contradicts: ["[[F-042]]"]` in frontmatter.
3. In the existing note, **append only** a `## Contradictions` section at the end:
   ```markdown
   ## Contradictions
   - YYYY-MM-DD (from `<your-project>` via [[F-089]]) — <one-line explanation>
   ```
4. Commit your new note: `[vault] CREATE F-089 from <project>`
5. Commit the contradiction append separately: `[vault] CONTRADICT F-042 by <project> via F-089`
6. **Escalate to user** via `AskUserQuestion`:
   > "⚠ Contradiction detected between existing [[F-042]] (source: `<other-project>`) and new [[F-089]] (this project).
   > Options:
   > (a) context-dependent — both stay `active`, tighten `project-context` on each
   > (b) F-042 is now wrong — mark as `superseded`, `superseded-by: [[F-089]]`
   > (c) both obsolete — API changed, mark both `obsolete`
   > Which?"

Never resolve contradictions silently. Always escalate.

## Reading from vault (complement — not this skill's job, but related)

To **read** from the vault during project work (not write), use the lazy 3-tier pattern:

1. Always start: `{{VAULT_PATH}}/hot.md` — ~2K tokens, last 20 entries
2. On demand: grep-filter a specific folder (e.g., `grep -rl "stack:.*playwright" {{VAULT_PATH}}/fails/`)
3. Drill: read a specific `F-NNN` file only after finding it via 1-2

Never read the entire vault. Never read all of `fails/` or `patterns/` at once.

## Anti-patterns (never do)

- ❌ Write to `docs/FAILS.md` / `docs/PATTERNS.md` in the project — deprecated, those files no longer exist in the template.
- ❌ Delete a file in the vault — use `status: obsolete` or `status: superseded` instead.
- ❌ Edit the body of a note where `source-project` is a different project.
- ❌ Use a taxonomy value that is not in `meta/taxonomy.md` — add it there first.
- ❌ Skip the dedup check — creates duplicates that rot the vault.
- ❌ Batch multiple CRUD ops into one commit — one op = one commit (required for audit trail and rollback).
- ❌ Use `git add -A` in the vault — only add files you intentionally changed.
