---
name: migrate-to-vault
description: 'One-time migration: move legacy docs/FAILS.md and docs/PATTERNS.md from this project into the shared vault at {{VAULT_PATH}}/. Classifies each entry (fail/pattern/gotcha), writes via vault-write skill with source-project set to current project, then deletes the local files.'
argument-hint: (no args — reads local docs/FAILS.md and docs/PATTERNS.md)
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

> **Style:** Load `caveman-distillate` skill — terse, no filler, fragments OK.

# Migrate Legacy FAILS/PATTERNS to Shared Vault

Move this project's cross-project knowledge from deprecated local files into `{{VAULT_PATH}}/`. Run ONCE per project.

## Pre-flight

### STEP 0 — Sanity checks

```bash
# Confirm vault exists
test -d {{VAULT_PATH}}/fails || { echo "❌ Vault not scaffolded. Run the bootstrap first."; exit 1; }

# Confirm this project has legacy files
test -f docs/FAILS.md || test -f docs/PATTERNS.md || { echo "✅ No legacy files — nothing to migrate."; exit 0; }

# Confirm vault-write skill exists in this project
test -f .claude/skills/vault-write/SKILL.md || { echo "❌ vault-write skill missing — update project from template first."; exit 1; }

# Determine source-project name
SRC=$(basename "$(pwd)")
echo "Source project: $SRC"
```

If any check fails — stop and report to user.

### STEP 0.5 — Template freshness gate (MANDATORY precondition)

Migration only patches data (`docs/FAILS.md` → vault). It does NOT refresh the project's `.claude/` template files. If the project is running a pre-vault template snapshot, `.claude/rules/workflow.md`, `.claude/skills/anti-best-practice/SKILL.md`, `.claude/commands/fix.md`, and `.claude/commands/review.md` still reference the deleted `docs/FAILS.md` / `docs/PATTERNS.md` — and your next `/fix` or `/review` will break.

**Run this check before touching any data:**

```bash
# Any template file that still mentions deprecated legacy paths?
STALE=$(grep -rln "docs/FAILS\.md\|docs/PATTERNS\.md" \
  .claude/rules/ \
  .claude/skills/anti-best-practice/ \
  .claude/commands/fix.md \
  .claude/commands/review.md \
  2>/dev/null)

if [ -n "$STALE" ]; then
  echo "❌ BLOCKED — project template is stale. These files still reference deprecated docs/FAILS.md / docs/PATTERNS.md:"
  echo "$STALE"
  echo ""
  echo "Refresh the template FIRST, then re-run /migrate-to-vault:"
  echo "  1. cd ~/PycharmProjects/!claude-project-template && git pull"
  echo "  2. Copy these files from template to project (preserve project-specific .claude/rules/project.md and .claude/settings.json):"
  echo "       .claude/rules/workflow.md"
  echo "       .claude/rules/skill-routing.md"
  echo "       .claude/skills/anti-best-practice/SKILL.md"
  echo "       .claude/commands/fix.md"
  echo "       .claude/commands/review.md"
  echo "       .claude/commands/init-project.md"
  echo "       .claude/commands/migrate-to-vault.md   (new)"
  echo "       .claude/skills/vault-write/             (new)"
  echo "       .claude/agents/code-reviewer.md"
  echo "  3. [BACKUP] commit, overwrite, [CHANGE] commit."
  echo "  4. Then re-run /migrate-to-vault."
  exit 1
fi

echo "✅ Template freshness OK — safe to migrate data."
```

**Why this gate exists:** `/migrate-to-vault` deletes `docs/FAILS.md` and `docs/PATTERNS.md`. Every `.claude/` file that still points to those paths becomes a broken reference. The template refresh fixes those references; without it, the project is half-migrated and the next `/fix` or `/review` will fail hunting a file that no longer exists.

**Note:** `.claude/rules/project.md` and `.claude/settings.json` are project-specific — do NOT overwrite them during refresh.

If this gate blocks you — STOP, instruct the user to refresh the template first, do NOT continue with data migration.

### STEP 1 — Read vault contract

```
Read: {{VAULT_PATH}}/CLAUDE.md
Read: {{VAULT_PATH}}/meta/taxonomy.md
```

This sets the rules for classification and allowed stack/domain/project-context values. Do not skip.

### STEP 2 — Read local legacy files

```
Read: docs/FAILS.md   (if exists)
Read: docs/PATTERNS.md (if exists)
```

Parse entries. Each one will likely look like:
- In FAILS.md — a section with symptom / root cause / fix
- In PATTERNS.md — a section with problem / pattern / when to use

### STEP 3 — Classify each entry

For every entry, decide which vault bucket it belongs to:

| If the entry is… | → type | folder | ID prefix |
|--|--|--|--|
| reproducible bug + root cause + fix | `fail` | `fails/` | `F-NNN` |
| reusable solution worth naming, applies across projects | `pattern` | `patterns/` | `P-NNN` |
| wrong-assumption about API / service / config (no code to "fix", just avoid) | `gotcha` | `gotchas/` | `G-NNN` |
| only useful to THIS project (specific schema, specific service name) | → SKIP | — | — |
| typo / lint / trivial | → SKIP | — | — |

When in doubt between `fail` and `gotcha`: if the symptom was a runtime error that needed a code fix → `fail`. If the symptom was "I thought X worked, it didn't, I just avoid it now" → `gotcha`.

Build a migration plan as a table and show it to the user via `AskUserQuestion` BEFORE writing anything:

```
Plan for migrating <N> entries from $SRC:

| # | source       | title                              | → type   | notes |
|---|--------------|------------------------------------|----------|-------|
| 1 | FAILS.md     | Playwright hangs on iOS simulator  | fail     |       |
| 2 | FAILS.md     | Local env var in my machine        | SKIP     | not reusable |
| 3 | PATTERNS.md  | SQLAlchemy async sessionmaker      | pattern  |       |
| 4 | PATTERNS.md  | Meta test numbers drop real sends  | gotcha   | wrong-assumption |
...

Options:
(a) Proceed as shown
(b) Let me adjust classifications first
```

Wait for user confirmation before STEP 4.

### STEP 4 — Write each entry to vault via vault-write skill

For every non-SKIP entry in the approved plan:

1. **Invoke the `vault-write` skill** (`.claude/skills/vault-write/SKILL.md`) — do the full 8-step protocol for this one entry:
   - Dedup check (`grep -rli "<keywords>" {{VAULT_PATH}}/<folder>/`)
   - If a dedup hit appears → use `AskUserQuestion`:
     > "Found existing `<ID>` — `<title>` (source: `<other-project>`). Options:
     > (a) skip migrating this entry — already in vault
     > (b) create new with `related: [[<ID>]]` — this project's angle is different
     > (c) abort migration and let me decide"
   - Determine new ID by scanning folder
   - Create file from template at `{{VAULT_PATH}}/<folder>/<ID>-<slug>.md`
   - Frontmatter: `source-project: <current project folder name>`, `created: <today ISO>`, `status: active`, taxonomy values from `meta/taxonomy.md`
   - Body: translate the legacy content into the template structure (symptom/root cause/fix for fail; problem/pattern/when/when-not for pattern; assumption/reality/how-it-burned for gotcha)
   - Append one line to `log.md`: `YYYY-MM-DD HH:MM  CREATE  <ID>  "<title>"  source=<project>  [migrated]`
   - Update `hot.md` — push entry to top, pop bottom if >20
   - Commit: `git -C {{VAULT_PATH}} add <file> log.md hot.md && git commit -m "[vault] CREATE <ID> from <project> (migration)"`

2. **One commit per entry.** Do not batch.

3. **Preserve provenance** — in the body, add a line at the bottom:
   ```
   > Migrated from <project>/docs/FAILS.md on YYYY-MM-DD.
   ```

### STEP 5 — Verify writes landed

```bash
# Count migrated entries
SRC=$(basename "$(pwd)")
echo "Entries with source-project: $SRC"
grep -rl "source-project: $SRC" {{VAULT_PATH}}/fails/ {{VAULT_PATH}}/patterns/ {{VAULT_PATH}}/gotchas/ 2>/dev/null | wc -l

# Check log
grep "$SRC" {{VAULT_PATH}}/log.md | tail -20
```

The count should match the number of non-SKIP entries in your approved plan. If not — stop and investigate.

### STEP 6 — Delete local legacy files

Only after STEP 5 passes:

```bash
# BACKUP commit in the project repo before deletion
git add docs/FAILS.md docs/PATTERNS.md 2>/dev/null
git commit -m "[BACKUP] Pre-migration snapshot of legacy FAILS/PATTERNS before vault migration"

# Delete
rm -f docs/FAILS.md docs/PATTERNS.md

# CHANGE commit
git add -u docs/
git commit -m "[CHANGE] Remove deprecated docs/FAILS.md and docs/PATTERNS.md — migrated to shared vault

Content is now at {{VAULT_PATH}}/ (fails/, patterns/, gotchas/).
Access via vault-write skill for writes and hot.md/grep for reads.
Source-project field = $(basename $(pwd))."
```

### STEP 7 — Remove stale references in project files

Some project-level docs may still mention the old files. Grep and fix:

```bash
grep -rln "docs/FAILS\.md\|docs/PATTERNS\.md\|FAILS\.md\|PATTERNS\.md" \
  CLAUDE.md .claude/ docs/ 2>/dev/null
```

For each hit, edit the file to point to the vault instead. Typical replacements:
- "check docs/FAILS.md" → "grep {{VAULT_PATH}}/fails/"
- "add to docs/PATTERNS.md" → "invoke vault-write skill"
- "see FAILS.md for known issues" → "see hot.md in shared vault"

Commit: `[CHANGE] Update references from local FAILS/PATTERNS to shared vault`.

### STEP 8 — Report

```
✅ Migration complete for <project>

Entries migrated:
- Fails:    <N>  → fails/F-NNN..F-MMM
- Patterns: <N>  → patterns/P-NNN..P-MMM
- Gotchas:  <N>  → gotchas/G-NNN..G-MMM
- Skipped:  <N>  (not reusable / trivial)

Local files:
- docs/FAILS.md — DELETED
- docs/PATTERNS.md — DELETED
- References in CLAUDE.md / .claude/ — updated to point at vault

Vault commits: <N> new CREATE commits in {{VAULT_PATH}}/

Next time you fumble something worth sharing — vault-write skill handles the rest.
```

## Rules

- **Never batch** vault writes into one commit — one entry = one commit.
- **Never** create a vault entry without running the vault-write dedup check first.
- **Always** set `source-project` to the CURRENT project's folder name (not the vault, not the template).
- **Always** escalate to `AskUserQuestion` on dedup/contradiction hits — never resolve silently.
- **Do not migrate project-specific content** (schema names, local service URLs, "this project's" decisions) — those stay in git history.
- **Run once per project.** After deletion of legacy files, running again is a no-op (STEP 0 exits early).
