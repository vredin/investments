---
name: vault-bootstrap
description: 'One-time setup of the shared cross-project knowledge vault. Prompts for target path (or accepts it as argument), copies vault-skeleton/ from the template, substitutes the {{VAULT_PATH}} placeholder with the resolved absolute path, initializes a git repo, writes the resolved path to ~/.claude-template-vault-path for /init-project to read, and verifies the structure. Run ONCE per machine, before running /init-project on any project.'
argument-hint: '[target path] (optional — if omitted, prompts interactively via AskUserQuestion)'
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

> **Style:** Load `caveman-distillate` skill — terse responses, no filler, fragments OK.

# Bootstrap the Shared Knowledge Vault

Initialize the cross-project vault that `vault-write`, `migrate-to-vault`, and every `/fix`/`/review` hook depends on. Run once per machine.

## Variables

- `VAULT_PATH`: absolute path to the target vault directory (resolved in STEP 0)
- `TEMPLATE_PATH`: directory containing `vault-skeleton/` (the template repo root)
- `CONFIG_FILE`: `~/.claude-template-vault-path` — single-line config written after successful bootstrap

## STEP 0 — Resolve target path

### If `$ARGUMENTS` provided

```bash
VAULT_PATH="${1}"
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"
# Resolve to absolute path
VAULT_PATH="$(cd "$(dirname "$VAULT_PATH")" 2>/dev/null && pwd)/$(basename "$VAULT_PATH")" || VAULT_PATH="$1"
```

### If `$ARGUMENTS` empty — ask interactively

Use `AskUserQuestion` with TWO questions in one call:

1. **Question**: "Where should the shared knowledge vault live? (parent directory)"
   **Header**: "Parent dir"
   **Options**:
   - `~/PycharmProjects` (Recommended) — default location alongside your project repos
   - `~/Documents` — if you keep notes under Documents
   - `~/vaults` — dedicated vault folder
   (User can pick "Other" to type a custom absolute path.)

2. **Question**: "What folder name should the vault use?"
   **Header**: "Vault name"
   **Options**:
   - `Obsidian` (Recommended) — works with Obsidian 1.8+ dashboards out of the box
   - `knowledge-vault` — more generic name if you don't use Obsidian
   - `claude-vault` — makes the connection to Claude Code explicit

After the user answers, compose:
```bash
VAULT_PATH="$PARENT_DIR/$VAULT_NAME"
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"
```

### Locate template root

```bash
# The template is this repo — find it by walking up from any file in .claude/commands/
TEMPLATE_PATH="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
test -d "$TEMPLATE_PATH/vault-skeleton" || {
  echo "❌ vault-skeleton/ not found at $TEMPLATE_PATH."
  echo "   Run this command from inside the claude-project-template repo."
  exit 1
}
```

### Refuse to clobber existing vault

```bash
if [ -e "$VAULT_PATH/CLAUDE.md" ]; then
  echo "⚠ Vault already exists at $VAULT_PATH (CLAUDE.md present)."
  echo "  Aborting to avoid overwriting your notes."
  echo "  If you want to re-bootstrap: move the old vault aside first."
  exit 1
fi

echo "Target: $VAULT_PATH"
echo "Source: $TEMPLATE_PATH/vault-skeleton"
```

If `VAULT_PATH` exists but has no `CLAUDE.md` → use `AskUserQuestion` to ask whether to proceed into the existing directory or pick another path.

## STEP 1 — Copy the skeleton

```bash
mkdir -p "$VAULT_PATH"
cp -R "$TEMPLATE_PATH/vault-skeleton/." "$VAULT_PATH/"
```

Verify structure:

```bash
test -f "$VAULT_PATH/CLAUDE.md"              || { echo "❌ CLAUDE.md missing"; exit 1; }
test -f "$VAULT_PATH/README.md"              || { echo "❌ README.md missing"; exit 1; }
test -f "$VAULT_PATH/index.md"               || { echo "❌ index.md missing"; exit 1; }
test -f "$VAULT_PATH/hot.md"                 || { echo "❌ hot.md missing"; exit 1; }
test -f "$VAULT_PATH/log.md"                 || { echo "❌ log.md missing"; exit 1; }
test -f "$VAULT_PATH/meta/taxonomy.md"       || { echo "❌ meta/taxonomy.md missing"; exit 1; }
test -f "$VAULT_PATH/meta/templates/fail.md" || { echo "❌ meta/templates/fail.md missing"; exit 1; }
test -d "$VAULT_PATH/fails"                  || { echo "❌ fails/ missing"; exit 1; }
test -d "$VAULT_PATH/patterns"               || { echo "❌ patterns/ missing"; exit 1; }
test -d "$VAULT_PATH/gotchas"                || { echo "❌ gotchas/ missing"; exit 1; }
test -f "$VAULT_PATH/dashboards/all-active-fails.base" || { echo "❌ dashboards missing"; exit 1; }
echo "✅ Skeleton structure verified."
```

## STEP 2 — Substitute `{{VAULT_PATH}}` placeholder

The skeleton files reference themselves via the placeholder so the template stays portable. Replace it with the resolved absolute path across every `.md` and `.base` file in the copied vault:

```bash
# macOS sed needs the empty '' after -i
find "$VAULT_PATH" -type f \( -name "*.md" -o -name "*.base" \) \
  -exec sed -i '' "s|{{VAULT_PATH}}|$VAULT_PATH|g" {} \;

# Sanity check — no placeholder should remain
REMAINING=$(grep -rln "{{VAULT_PATH}}" "$VAULT_PATH" 2>/dev/null || true)
if [ -n "$REMAINING" ]; then
  echo "❌ Placeholder still present in:"
  echo "$REMAINING"
  exit 1
fi
echo "✅ {{VAULT_PATH}} → $VAULT_PATH substituted."
```

> **Why:** the skeleton in `template/vault-skeleton/` uses `{{VAULT_PATH}}` so the template can be committed once and work for any user. At bootstrap time we materialize the user's actual path.

## STEP 3 — Initialize git

```bash
cd "$VAULT_PATH"
if [ ! -d .git ]; then
  git init -b main
  # Explicit file list — never use `git add .` or `git add -A` per workflow.md SSOT rule.
  git add CLAUDE.md README.md index.md hot.md log.md \
          meta/taxonomy.md meta/templates/fail.md meta/templates/pattern.md meta/templates/gotcha.md \
          dashboards/all-active-fails.base dashboards/critical-gotchas.base dashboards/patterns-by-stack.base \
          fails/.gitkeep patterns/.gitkeep gotchas/.gitkeep
  git commit -m "[vault] initial scaffold from claude-project-template/vault-skeleton"
  echo "✅ Git repo initialized."
else
  echo "ℹ Git repo already exists — skipping git init."
fi
```

## STEP 4 — Write config file for /init-project to read

```bash
echo "$VAULT_PATH" > "$HOME/.claude-template-vault-path"
echo "✅ Wrote $HOME/.claude-template-vault-path (used by /init-project)"
```

> **Why this config file exists:** `/init-project` copies template files into a new project and needs to materialize `{{VAULT_PATH}}` in them. It reads this file to learn where the vault lives without asking the user again.

## STEP 5 — Verify Obsidian dashboards

```bash
BASE_COUNT=$(find "$VAULT_PATH/dashboards" -maxdepth 1 -name "*.base" | wc -l | tr -d ' ')
[ "$BASE_COUNT" -eq 3 ] || echo "⚠ Expected 3 .base dashboards, found $BASE_COUNT"
```

Dashboards require Obsidian 1.8+ (Bases feature). If the user isn't using Obsidian, the `.base` files are harmless YAML.

## STEP 6 — Report

```
✅ Vault bootstrapped: $VAULT_PATH

Structure:
- CLAUDE.md           — vault CRUD policy (Claude reads this automatically)
- README.md           — overview
- index.md            — entry point with grep recipes
- hot.md              — last 20 entries (always cheap)
- log.md              — append-only activity log
- meta/taxonomy.md    — controlled vocabulary (stack/domain/project-context)
- meta/templates/     — frontmatter skeletons for fails/patterns/gotchas
- fails/, patterns/, gotchas/  — empty, ready for first entry
- dashboards/         — 3 Obsidian Bases (.base) files

Config:
- ~/.claude-template-vault-path   — resolved path, read by /init-project

Next steps:
1. cd $VAULT_PATH && ls -la      # inspect what was created
2. Open in Obsidian 1.8+ if you use it (dashboards become live)
3. Return to your projects — /init-project and /fix will now find the vault
4. First fail/pattern/gotcha will auto-write here via the vault-write skill
```

## Troubleshooting

- **`vault-skeleton/` not found**: you're running from outside the template repo. `cd` into the cloned template first, then re-run.
- **Vault exists but has no CLAUDE.md**: user had a stub dir. Ask whether to proceed (content preserved, skeleton files added alongside) or abort.
- **Placeholder still present after STEP 2**: sed failed — check file permissions and re-run. The sanity check in STEP 2 will catch this before git commit.
- **Config file not written**: `/init-project` will fall back to asking for the path, but rerun this command to write the file correctly.

## Rules

- Run ONCE per machine. Subsequent projects share the same vault.
- NEVER re-run on a populated vault — it will refuse via STEP 0 guard.
- The vault is its own git repo, separate from any project.
- Do NOT push the vault to a public remote without reviewing content first — it may contain cross-project business context.
- The config file at `~/.claude-template-vault-path` is the SSOT for the vault location — `/init-project` reads it, never hardcodes a path.
