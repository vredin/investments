---
name: setup
description: 'Template setup wizard — fresh install, MCP reconfigure, health check, or v2→v3 migration. Idempotent. Run from template root or initialized project.'
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

> **Style:** Load `caveman-distillate` skill — terse responses.

# Setup Wizard

Single entry point for template configuration. Detects state and routes.

---

## STEP 1 — Detect current state

```bash
# Marker file written on first successful setup
test -f .claude/.setup.json && SETUP_DONE=1 || SETUP_DONE=0

# Check MCP
claude mcp list 2>/dev/null | grep -q outline && MCP_OK=1 || MCP_OK=0

# Check stack docs
test -f docs/STACK.md && grep -q '\[PROJECT_NAME\]' docs/STACK.md && STACK_FILLED=0 || STACK_FILLED=1

# Detect if running in template repo or in a derived project
test -f README.md && grep -q "claude-project-template" README.md 2>/dev/null && IS_TEMPLATE=1 || IS_TEMPLATE=0
```

Report state to user:
```
Template setup state:
- Setup marker: [yes/no]
- MCP outline: [connected/not connected]
- STACK.md: [filled/placeholder]
- Running in: [template repo/project copy]
```

---

## STEP 2 — Pick mode (interactive)

Use `AskUserQuestion`:

| Mode | When |
|------|------|
| **Fresh install** | First time on this machine; SETUP_DONE=0 |
| **Reconfigure MCP** | After token rotation; MCP_OK=0 or user says so |
| **Verify health** | Periodic check; everything should be 1 |
| **Migrate v2→v3** | Existing project with old template version |

---

## STEP 3 — Execute

### Fresh install

1. **Outline MCP setup** — display this exactly to the user, then wait:
   ```
   Open your terminal and run (DO NOT paste your token here in chat):
   
   claude mcp add outline --transport http https://outline.semishan.pro/mcp \
     --header "Authorization: Bearer <YOUR_OUTLINE_TOKEN>"
   
   Get/rotate the token at:
   https://outline.semishan.pro/settings/api-keys
   
   Reply 'done' when complete.
   ```

2. After user says done — verify:
   ```bash
   claude mcp list | grep -q outline || echo "FAIL: outline not in mcp list"
   ```
   If failed → ask user to check the command output, retry.

3. **Verify Outline reachability** by attempting a tool call:
   - Try `mcp__outline__list_collections` (if available) or `mcp__outline__search_documents` with an empty query.
   - If returns data → `MCP_OUTLINE: ok`
   - If error → instruct user to check token validity and Outline URL; do not proceed.

4. **Confirm shared collection structure** in Outline:
   - Tell user to ensure these collections exist in `outline.semishan.pro`:
     - `Knowledge Base` (shared, with sub-pages: Fails, Best Practices, Daily Status, Tricks)
     - `Project: <name>` (one per project; `/init-project` creates one for each new project)
   - Capture the collection IDs (user will run a one-liner via MCP and paste IDs)
   - Save IDs to `.claude/.setup.json`

5. **Register /loop schedules** (optional but recommended):
   - Read `.claude/loop-schedules.md` for the four default routines.
   - Tell user: "To register the four default routines (daily report, weekly docs audit, weekly self-audit, bi-weekly global audit), run these in your terminal:"
     ```
     /loop "0 18 * * *" /report
     /loop "0 9 * * 1" /docs audit
     /loop "0 10 * * 5" /self-audit
     /loop "0 11 1,15 * *" /self-audit --global
     ```
   - This is optional — commands work manually too. Skip if `/loop` skill unavailable.

6. **Write .setup.json**:
   ```json
   {
     "version": 3,
     "ts": "<ISO timestamp>",
     "mcp_outline": "ok",
     "outline_url": "https://outline.semishan.pro",
     "shared_collection_id": "<id>",
     "next_steps": [
       "Run /init-project to create a project from this template, OR",
       "Configure docs/STACK.md if working in this repo directly"
     ]
   }
   ```

6. **Report**:
   ```
   ✅ Setup complete (v3)
   Outline MCP: connected
   Next: /init-project <path>  to scaffold a new project
   ```

### Reconfigure MCP

1. Tell user to run in their terminal:
   ```
   claude mcp remove outline
   claude mcp add outline --transport http <OUTLINE_URL>/mcp \
     --header "Authorization: Bearer <NEW_TOKEN>"
   ```
2. Wait for "done", then verify with `claude mcp list | grep outline`.
3. Update `.claude/.setup.json` timestamp.

### Verify health

Run all checks, report status table:

```
Component               Status
──────────────────────────────────────
.claude/.setup.json     [ok/missing]
MCP outline             [connected/not]
docs/STACK.md           [filled/placeholder]
docs/CONTEXT.md         [present/missing]
docs/adr/               [present/missing]
bin/outline.sh          [executable/missing]
bin/psql_ro.sh          [executable/missing]
.claude/agents/         [N agents]
.claude/commands/       [N commands]
.claude/skills/         [N skills]
.claude/hooks/          [N hooks]
```

For each missing/broken: print fix command (`chmod +x`, `claude mcp add ...`, etc).

### Migrate v2→v3

1. Read `.claude/migrations/v2-to-v3.md` (full changeset).
2. Confirm with user: "Apply v2→v3 migration? This deletes some skills, renames others, adds new commands. [y/N]"
3. If yes — execute the steps in the migration doc, report each.
4. After: write/update `.setup.json` with `"version": 3, "migrated_from": 2`.

---

## Rules

- NEVER ask the user to paste their Outline token in chat. Always direct them to their terminal.
- NEVER write the token to any file in the repo. MCP config is stored by Claude Code internally.
- `.claude/.setup.json` is gitignored — local marker only.
- Idempotent: running `/setup` twice in same state should be a no-op except for "Verify health".
- If MCP verification fails, do NOT mark setup as complete.
