---
name: init-project
description: 'Initialize a new project from the claude-project-template. Interactive setup: collects project info, copies template, replaces placeholders, configures deploy.'
argument-hint: [/path/to/new-project]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

> **Style:** Load `caveman-distillate` skill — terse responses, no filler, fragments OK.

# Init Project from Template

Set up a new project using the claude-project-template. Collect all info interactively, then configure everything in one pass.

## Variables

TARGET_PATH: $ARGUMENTS
TEMPLATE_PATH: The directory where THIS command is running from (the template repo root).

## Workflow

### STEP 1 — Collect project info

Use `AskUserQuestion` to gather the following. Ask in ONE message, not one-by-one:

```
Setting up a new project. Please provide:

1. **Project name** (e.g. "Slugger", "MyApp")
2. **Response language** (e.g. Ukrainian, English, Russian)
3. **Stack**:
   - Backend: (e.g. FastAPI + SQLAlchemy + PostgreSQL + Redis)
   - Frontend: (e.g. React 18 + TypeScript + Vite)
   - Deploy: (e.g. Docker Compose on VPS)
4. **Server access**:
   - SSH alias: (e.g. `ssh vps3`)
   - Project path on server: (e.g. `/opt/slugger`)
   - Domain(s): (e.g. `slugger.example.com`, `metabase.example.com`)
   - Reverse proxy: (e.g. Traefik / Nginx / Caddy)
5. **Deploy flow** — how code gets to production:
   - (e.g. "git push → ssh → git pull → docker compose up -d")
   - (e.g. "git push origin main → GitHub Actions deploys automatically")
```

If TARGET_PATH was not provided as argument, also ask:
```
6. **Target directory**: full path where the project should be created
```

### STEP 2 — Copy template structure

```bash
# Create target directory if needed
mkdir -p <TARGET_PATH>

# Copy .claude/ directory (agents, commands, rules, skills, settings)
cp -r <TEMPLATE_PATH>/.claude <TARGET_PATH>/

# Copy docs/ directory (local docs only: CONVENTIONS, KNOWLEDGE, DEPLOY, TASK, specs, archive)
cp -r <TEMPLATE_PATH>/docs <TARGET_PATH>/

# Copy CLAUDE.md
cp <TEMPLATE_PATH>/CLAUDE.md <TARGET_PATH>/

# Copy .gitignore template
cp <TEMPLATE_PATH>/.gitignore.template <TARGET_PATH>/.gitignore
```

Do NOT copy: `CLAUDE_SETUP.md`, `README.md`, `memory/`, `.git/`.

**Note**: The template no longer contains `docs/FAILS.md` or `docs/PATTERNS.md` — those are now stored in the shared vault at `~/PycharmProjects/Obsidian/`. All projects read/write fails, patterns, and gotchas from there via the `vault-write` skill. If a copy of an older template still has these files, delete them from the target project after copying — they are deprecated.

### STEP 2.5 — Resolve vault path (read config, bootstrap if missing)

The template files you just copied reference the shared vault via the `{{VAULT_PATH}}` placeholder. Before continuing, resolve that placeholder to the user's actual vault path.

```bash
CONFIG_FILE="$HOME/.claude-template-vault-path"

if [ -f "$CONFIG_FILE" ]; then
  VAULT_PATH="$(cat "$CONFIG_FILE" | tr -d '\n' | tr -d ' ')"
  if [ -f "$VAULT_PATH/CLAUDE.md" ]; then
    echo "✅ Vault found at $VAULT_PATH (from $CONFIG_FILE)"
  else
    echo "⚠ Config points at $VAULT_PATH but CLAUDE.md is missing there."
    VAULT_PATH=""
  fi
fi

if [ -z "$VAULT_PATH" ]; then
  echo "⚠ Shared knowledge vault not bootstrapped yet."
  echo "Bootstrapping it now from vault-skeleton/..."
fi
```

**If `$VAULT_PATH` is empty** (no config file, or config points at a broken vault):

1. **Read `.claude/commands/vault-bootstrap.md` and execute its steps inline.** Slash commands cannot programmatically invoke other slash commands — you read the file, then run its bash blocks yourself. That command will prompt the user for the vault location via `AskUserQuestion`, copy `vault-skeleton/` there, substitute `{{VAULT_PATH}}`, initialize git, and write the resolved path to `~/.claude-template-vault-path`.
2. **After bootstrap completes**, re-read the config file: `VAULT_PATH="$(cat "$CONFIG_FILE")"`.

Without the vault, `vault-write`, `migrate-to-vault`, and every "check the vault first" step in `/fix` and `/review` will fail. Bootstrap is mandatory — do not skip.

If the user refuses the bootstrap: set `VAULT_PATH=""`, fall back to local-only memory (KNOWLEDGE.md, CONVENTIONS.md, TASK.md, DEPLOY.md), tell them they can bootstrap later with `/vault-bootstrap`, and **skip the placeholder substitution in STEP 3.5** (the `{{VAULT_PATH}}` references will remain as literal strings — the user can run `/vault-bootstrap` later and then re-run a sed-replace manually).

### STEP 3 — Replace placeholders

Using the info from STEP 1, edit these files:

**`CLAUDE.md`**:
- Replace `[PROJECT_NAME]` with actual project name
- Replace `[Ukrainian / English / ...]` with chosen language

**`.claude/rules/project.md`**:
- Replace `[PROJECT_NAME]` in title
- Replace stack placeholders with actual stack
- Update Deploy section with actual deploy flow

**`docs/DEPLOY.md`**:
- Fill in SSH command, project path, domain(s), reverse proxy
- Fill in deploy flow steps with actual commands
- Fill in Services table with actual services and URLs
- Remove placeholder brackets — everything should be concrete values

### STEP 3.5 — Substitute `{{VAULT_PATH}}` in copied template files

The template files reference the shared vault via a `{{VAULT_PATH}}` placeholder so the template stays portable across machines. Materialize it to the actual path you resolved in STEP 2.5:

```bash
# Re-read config file here — bash variables don't persist between slash-command steps.
VAULT_PATH="$(cat "$HOME/.claude-template-vault-path" 2>/dev/null | tr -d '\n' | tr -d ' ')"

if [ -n "$VAULT_PATH" ] && [ -f "$VAULT_PATH/CLAUDE.md" ]; then
  find "<TARGET_PATH>/.claude" "<TARGET_PATH>/docs" -type f \( -name "*.md" -o -name "*.json" \) \
    -exec sed -i '' "s|{{VAULT_PATH}}|$VAULT_PATH|g" {} \;
  sed -i '' "s|{{VAULT_PATH}}|$VAULT_PATH|g" "<TARGET_PATH>/CLAUDE.md"

  # Sanity check — no placeholder should remain in the new project
  REMAINING=$(grep -rln "{{VAULT_PATH}}" "<TARGET_PATH>/.claude" "<TARGET_PATH>/docs" "<TARGET_PATH>/CLAUDE.md" 2>/dev/null || true)
  if [ -n "$REMAINING" ]; then
    echo "❌ {{VAULT_PATH}} still present in:"
    echo "$REMAINING"
    exit 1
  fi
  echo "✅ {{VAULT_PATH}} → $VAULT_PATH substituted in new project."
else
  echo "⚠ Skipping placeholder substitution — vault not bootstrapped."
  echo "  {{VAULT_PATH}} references remain as literal strings in:"
  echo "  $TARGET_PATH/.claude/ , $TARGET_PATH/docs/ , $TARGET_PATH/CLAUDE.md"
  echo "  Run /vault-bootstrap later, then re-run this sed block manually."
fi
```

> **Why STEP 3.5 exists:** the template stores `{{VAULT_PATH}}` instead of a hardcoded `~/PycharmProjects/Obsidian` so it works for any user regardless of their preferred projects directory. STEP 2.5 resolved the actual path via the config file (or bootstrap); this step writes it into the new project's copy of the template files.

### STEP 4 — Create .env.example

Create `<TARGET_PATH>/.env.example` with common variables for the chosen stack:

```bash
# [PROJECT_NAME] Environment Variables
# Copy to .env for local dev, .env.production for production secrets

# App
APP_NAME=[project_name]
APP_ENV=development
APP_PORT=8000

# Database (adapt to stack)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Add stack-specific variables below
```

### STEP 5 — Initialize git

```bash
cd <TARGET_PATH>
git init -b main
# Add only the files this command explicitly created — never use `git add -A`
# (per workflow.md: `-A` can stage secrets or unrelated files).
git add .claude/ docs/ CLAUDE.md .env.example .gitignore
git commit -m "[BACKUP] Initial project setup from claude-project-template"
```

> **Note**: `git init` is allowed — it creates a fresh repository and is not destructive.
> The destructive-command hook in `.claude/settings.json` does NOT block `git init`.

### STEP 6 — Verify and report

Check that all placeholder strings are gone:
```bash
grep -rn "\[PROJECT_NAME\]\|\[e\.g\.\|/PATH/TO/\|{{VAULT_PATH}}" <TARGET_PATH>/.claude/ <TARGET_PATH>/docs/ <TARGET_PATH>/CLAUDE.md 2>/dev/null
```

If any remain — fix them. `{{VAULT_PATH}}` residue specifically means STEP 3.5 didn't run (user refused bootstrap) — re-run `/vault-bootstrap` and the sed block in STEP 3.5, or fix manually.

Then report:

```
✅ Project initialized: <name>

Directory: <TARGET_PATH>
Stack: <backend> + <frontend>
Deploy: <ssh alias> → <server path>

Files created (local):
- .claude/ (agents, commands, rules, skills, settings)
- docs/ (KNOWLEDGE — project ADRs; CONVENTIONS; TASK; DEPLOY)
- CLAUDE.md
- .env.example
- .gitignore

Shared knowledge (read/write via vault-write skill):
- $VAULT_PATH — fails, patterns, gotchas across all projects
  (deprecated local docs/FAILS.md and docs/PATTERNS.md are NOT created)

Next steps:
1. Open the project: cd <TARGET_PATH>
2. Fill in API keys: cp .env.example .env.production
3. Start working: claude
```

## Rules

- Ask ALL questions in ONE message — don't drip-feed questions one by one
- Never leave placeholder brackets in output files — every `[...]` must be replaced
- If user skips a field (e.g. no frontend) — remove that section entirely, don't leave empty placeholders
- The init-project command is PLANNING ONLY — never write application code
- If target directory already has `.claude/` — warn and ask before overwriting
