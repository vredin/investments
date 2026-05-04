# Development Workflow Rules

## No Deferral Policy (applies to ALL work)

If you CAN solve a problem — solve it. Do not defer to the user.

**You MUST resolve it yourself if**:
- A dependency is missing → install it
- A config file is missing → create it
- A test is failing → fix it
- An env variable is needed → add it to `.env.example` and tell user to fill the value
- A file needs to exist on server → create and deliver it via `ssh`/`scp`
- A migration is needed → generate and run it
- Linter/type errors after your changes → fix them before moving on

**You MAY ask the user ONLY if**:
- You need credentials/API keys that you don't have (and they're not in `.env.production`)
- A business decision is required (scope, priority, UX choice)
- Destructive action on shared resources (drop DB, force push, delete production data)

**NEVER say**:
- "You can configure this later" → configure it now
- "You may want to add..." → add it now if it's needed
- "Consider adding tests" → write the tests
- "Don't forget to..." → do it yourself

---

## Session Scoping (context window discipline)

A session = one focused work block within a safe context window.

### Context Budget (HARD RULES — enforced, not suggested)

You work best at the top of your context window. The old rule "write handoff at ~60%" was soft — routinely ignored until auto-compact fired silently at 95% and state was lost. Replaced with counter-based hard rules below.

**Rule 1 — Periodic context check**
Every **20 tool calls** run `/context` (or recall the last report). No skipping. If you forget, the PreCompact hook will snapshot your transcript to `.claude/session-log/` — that's the audit trail, not a free pass.

**Rule 2 — Context thresholds (hard, not advisory)**
| Context % | Action | Allowed to start new task? |
|-----------|--------|----------------------------|
| **<40%**   | Normal work | ✅ yes |
| **40–50%** | Finish current step, then write `docs/handoff.md` before next tool call that starts new work | ⚠ only trivial |
| **>50%**   | **STOP**. Write/update handoff.md NOW. `/compact` after handoff is written. | ❌ no |
| **>70%**   | Emergency: commit `[WIP]` if mid-task, write skeleton handoff, `/compact` immediately | ❌ no |
| **>90%**   | You failed to follow the rule above. Write whatever state you can, then `/clear`. Expect loss. | ❌ no |

**Rule 3 — Handoff write order (never skip a step)**
When threshold is crossed, handoff protocol is NOT optional:
1. Finish the current tool call (don't abort mid-edit)
2. Commit anything dirty as `[WIP]` or `[CHANGE]`
3. Write `docs/handoff.md` using the template in § Session End
4. **Only then** run `/compact`

**Rule 4 — Never start a new task above 50%**
No "I'll just quickly check X". That's how 50% becomes 75% becomes 95%-silent-compact. Finish current, handoff, compact. Then take the new task in fresh context.

**Rule 5 — PreCompact hook is a safety net, not a substitute**
`.claude/hooks/pre-compact-snapshot.sh` fires on every compact (manual and auto) and dumps the transcript to `.claude/session-log/compact-*.jsonl`. That means nothing is _permanently_ lost — but grepping a raw transcript is 10x slower and uglier than reading a properly-written handoff.md. Write the handoff.

**Activity counters (secondary backup — use when `/context` isn't available):**

| Metric | Warning | Hard limit |
|--------|---------|------------|
| Tasks completed | 3-4 | 5 |
| File reads | 10 | 12 |
| Total tool calls | 25 | 30 |

**At warning** (any metric): do NOT start a new task. Finish current, commit, handoff.
**At hard limit**: save state and compact (see below).
**Mid-task at limit**: commit `[WIP]`, write handoff, compact, continue.

### Surviving Compaction (auto-recovery)

Context compaction WILL happen. Two layers of defense:

**Layer 1 — handoff.md (the primary, Claude-written)**
1. **Before compaction** — write `docs/handoff.md` with current state per the hard rules above
2. **Compact** — run `/compact` (manual is always preferred over auto)
3. **After compaction** — Claude reads `docs/handoff.md` (see Session Start), resumes, then deletes it
4. handoff.md is external memory that survives compaction. The user should NOT need to start a new session.

**Layer 2 — PreCompact hook (the automatic, hook-written)**
`.claude/hooks/pre-compact-snapshot.sh` fires on **every** compact event (both manual and auto). It:
- Copies the raw transcript to `.claude/session-log/compact-<trigger>-<ts>-<session>.jsonl`
- Appends one line to `.claude/session-log/compact-audit.log`
- Prints a POST-COMPACT CHECKLIST to stdout (visible in the next turn after compaction)

This is purely defensive. The hook **cannot block compaction** (Claude Code runs PreCompact async and ignores exit codes), so it's not a substitute for writing handoff.md yourself. But if you fail to write one, the transcript snapshot ensures the user's last question and recent decisions are still recoverable via grep.

**Post-compaction recovery order:**
1. Does `docs/handoff.md` exist? → read it, resume, delete it. Done.
2. Does the auto-compaction summary contain the user's last message / question? → proceed normally.
3. Neither? → grep the most recent `.claude/session-log/compact-*.jsonl` for `"role":"user"` and read the last few entries. Report what you find to the user and ask for confirmation before acting on it.
4. Nothing recoverable? → tell the user: "Контекст загублено при компакції. Що було останнє — повтори, будь ласка." Do not guess.

### Limits
- **Max tasks per session**: 3-5 (not 15-25 — quality over quantity).
- **Hard stop trigger**: 12 file reads OR 30 tool calls OR 5 completed tasks — whichever comes first.

### Session Start (also applies after compaction)
1. If `docs/handoff.md` exists — read it FIRST, resume from there, then delete it
2. **After compaction only — check for lost user question**: if resuming from auto-compaction summary, verify the summary captures the user's last message. If the last user message was a question or request that is NOT answered in the summary — stop, tell the user: "Твоє останнє запитання не потрапило в summary. Повтори, будь ласка." Do NOT proceed with pending tasks until the user's question is answered.
3. Read `docs/TASK.md` — identify scope for this session
4. Read `{{VAULT_PATH}}/hot.md` — recent cross-project fails/patterns/gotchas (~2K tokens, always cheap)
5. Announce: "Session scope: T-NNN, T-NNN, T-NNN (X tasks)"
6. Review MCP servers (`/mcp`) — disconnect any not needed for current tasks
7. Load other docs **on demand** (not all at once — saves ~500+ tokens per turn):
   - `docs/CONVENTIONS.md` — before writing/reviewing code
   - `docs/KNOWLEDGE.md` — before project-specific architecture decisions (ADRs)
   - `docs/DEPLOY.md` — before any deploy action
   - **Shared vault grep** (`{{VAULT_PATH}}/`):
     - Before debugging → `grep -rl "<stack/domain>" {{VAULT_PATH}}/fails/`
     - Before 3p-API integration → `grep -rl "<service>" {{VAULT_PATH}}/gotchas/`
     - Before solution design → `grep -rl "<keyword>" {{VAULT_PATH}}/patterns/`
   - See CLAUDE.md § Shared Knowledge Vault for full protocol.

### Exit Signals (trigger Session End immediately)
If the user says any of these — start Handoff Protocol NOW:
- "на сьогодні все" / "на сегодня все" / "done for today" / "that's all"
- "закриваю" / "heading out" / "talk later" / "closing"
- "стоп" / "stop" / "enough" / "хватит"

### Session-End Learning Review (before writing handoff)
Before writing handoff.md, review the session for learnings:
- Any non-obvious fix (reusable across projects)? → Write to vault via `vault-write` skill (`fails/`)
- Any reusable pattern discovered? → Write to vault via `vault-write` skill (`patterns/`)
- Any API/service gotcha (wrong assumption about external system)? → Write to vault via `vault-write` skill (`gotchas/`)
- Any architecture decision tied to **this** project's codebase? → Add to `docs/KNOWLEDGE.md` (local)
- If a local fix also reveals a cross-project lesson — write both: local KNOWLEDGE.md entry AND a vault entry that references it.

### Session End — Handoff Protocol
When session is ending (tasks done, context heavy, exit signal, or user says "stop"):

1. Write `docs/handoff.md`:
```markdown
# Session Handoff — YYYY-MM-DD

## Completed This Session
- T-NNN: <title> — done, committed
- T-NNN: <title> — done, committed

## In Progress (not finished)
- T-NNN: <title> — <exact state: what's done, what remains>
- Files modified but not committed: <list>

## Next Session Should
1. <first thing to do>
2. <second thing to do>
3. <third thing to do>

## Context That Would Be Lost
- <non-obvious decision made during session>
- <gotcha discovered but not yet written to the shared vault>
- <dependency or blocker discovered>

## User's Last Unanswered Question
- <exact quote of the user's last question/request if it hasn't been answered yet — CRITICAL for post-compaction resume>

## Open Questions for User
- <anything that needs user input before next session>
```

2. Commit handoff: `git add docs/handoff.md && git commit -m "[HANDOFF] Session end: <summary>"`
3. Report to user: "Session done. X tasks completed. Handoff written to `docs/handoff.md`."

### Next Session Pickup
When starting a new session and `docs/handoff.md` exists:
1. Read it FIRST (before TASK.md)
2. Resume from "Next Session Should"
3. Delete `docs/handoff.md` after picking up context (it's a one-time transfer, not permanent docs)

---

## Research Protocol

When unsure about implementation, API, library usage, or best practice:

1. **First**: check local `docs/KNOWLEDGE.md` (this project's ADRs) AND the shared vault:
   - `{{VAULT_PATH}}/hot.md` (recent 20)
   - grep `{{VAULT_PATH}}/fails/`, `/patterns/`, `/gotchas/` by stack/domain/service
2. **Second**: use Context7 MCP (`mcp__context7__*`) for technical documentation of libraries and frameworks
3. **Third**: use Tavily / WebSearch for broader internet search (API changes, known issues, community solutions)

**Never guess** when official documentation is available. Look it up.

---

## Stuck Protocol (2+ failed attempts)

If you've tried to fix something **twice and it still fails** — STOP brute-forcing.

### After 2 failed attempts:
1. **Stop and analyze**: write down what you tried and why it failed
2. **Check the shared vault**: `grep -rli "<keyword>" {{VAULT_PATH}}/fails/ {{VAULT_PATH}}/gotchas/` — has this pattern been seen in another project?
3. **Research**: use Context7 / WebSearch to find the actual cause
4. **Change approach**: try a fundamentally different strategy, not a variation of the same one
5. **If still stuck after 3rd attempt**: tell the user honestly:
   - What you tried (3 approaches)
   - What you think the root cause is
   - What you'd suggest as next step (manual debug, dependency upgrade, different library)
   - Ask for guidance

**NEVER**:
- Retry the same approach hoping for a different result
- Silently modify unrelated code hoping it "fixes" things
- Say "it should work now" without verifying

---

## Pre-Change Protocol (mandatory before editing ANY file)

### Step 1 — BACKUP Commit
Before touching any source file, create a safety checkpoint:

```bash
git add <specific files> && git commit -m "[BACKUP] Pre-change: <description> | Risks: <list> | Scope: <files>"
```

> **Never use `git add -A`** — it can stage secrets (`.env.production`) or unrelated files.
> Always list specific files or use `git add src/` with a known-safe directory.

Commit message rules:
- MUST start with `[BACKUP]`
- MUST name what is about to change
- MUST list key risks (what could break)
- MUST name affected files/scope

### Step 2 — Implement

Make changes. Follow all quality rules.

### Step 3 — Quality Gate (run before EVERY commit)
```bash
# Adapt to your stack:

# Python
uv run ruff check . && mypy src/ --ignore-missing-imports && uv run bandit -r src/ -q

# TypeScript
npx tsc --noEmit && npx eslint src/

# Tests
pytest tests/ -q   OR   npm test

# Debug artifacts
grep -rn "console\.log\|debugger\|TODO\|FIXME\|print(" src/
```

### Step 4 — DA Review

Invoke the `Diablo` agent (`.claude/agents/diablo.md`).
Verdict must appear in the CHANGE commit message.

### Step 5 — CHANGE Commit

Create a new commit with the completed change:

```bash
git add <changed files> && git commit -m "[CHANGE] T-NNN: <brief imperative description>

What changed:
- <specific change 1>
- <specific change 2>

Why:
<requirement from spec AC>

Risk mitigation:
- <how risk 1 was addressed>

DA verdict: <ACCEPTABLE | PROCEED WITH CAUTION — <note> | FIX FIRST — fixed: <what>>
Tested by: <command>"
```

> **Note:** BACKUP commit stays in history as a safety checkpoint.
> Do NOT use `--amend` — Claude Code prohibits amending commits.

---

## Bug Fix Protocol (mandatory)
1. Check the shared vault FIRST: grep `{{VAULT_PATH}}/fails/` and `{{VAULT_PATH}}/gotchas/` for similar past failures across all projects
2. `[BACKUP]` commit (Step 1 above)
3. Write failing test FIRST — do not touch implementation until test exists
4. Run test to confirm failure (`red` phase)
5. Root cause analysis — identify exact cause, list 2–3 options
6. Fix + quality gate (Step 3 above)
7. Run test again — must pass (`green` phase)
8. **Same bug elsewhere?** — search codebase for the same pattern that caused this bug. If found in other files — fix ALL occurrences now, not just the one reported
9. DA review (Step 4 above)
10. `[CHANGE]` commit (Step 5 above)
11. If fix pattern is **reusable across projects** (non-obvious, not stack-trivial): write to vault using the `vault-write` skill — choose type `fail` for bugs, `gotcha` for wrong-assumption/API-quirk discoveries
12. If deploying — follow `docs/DEPLOY.md` and verify services after deploy

---

## Deploy Protocol (mandatory)

Before any deploy action — **read `docs/DEPLOY.md` first**. All server config is there.

### Rules
1. **SSH**: use ONLY the alias from `docs/DEPLOY.md` (e.g. `ssh vps3`). Never use raw IP.
2. **Secrets**: deliver via `scp .env.production <alias>:<project_path>/.env`. Never ask user to manually edit `.env` on the server.
3. **API keys**: if the user provided a key once, it's in `.env.production`. Never ask for it again. If a key is missing — tell user which key and ask to add it to local `.env.production`.
4. **Deploy flow**: follow the exact steps in `docs/DEPLOY.md`. Do not improvise.
5. **Verify**: always check services are running after deploy.
6. **Never edit code on server**: only flow is local edit → commit → push → server pull. Runtime config (`.env`) excepted.

### Secrets Handling
- Production secrets live in local `.env.production` (in `.gitignore`)
- Never commit secrets to git
- Never print/log secret values
- Never store secrets in `docs/` or memory files
- If `.env.production` doesn't exist — create it from `.env.example` and ask user to fill in values ONCE

### CRITICAL: .env Delivery Rules (learned the hard way — 2026-05-04)

**Rule 1 — NEVER `scp` the whole local `.env` to the server.**
The local `.env` is for local dev and may have test/dummy values (e.g. `ADMIN_PASSWORD_HASH=$2b$12$dummyhash...`). `scp .env vps3:/opt/.../.env` silently overwrites real production values with local test data.

To update a specific key on the server, use a Python heredoc over SSH — never shell echo/sed:
```bash
ssh vps3 python3 << 'PYEOF'
import re
path = '/opt/Investments/.env'
new_val = 'THE_ACTUAL_VALUE_WITH_$_SIGNS'
with open(path, 'r') as f:
    content = f.read()
content = re.sub(r'^KEY_NAME=.*$', 'KEY_NAME=' + new_val, content, flags=re.MULTILINE)
with open(path, 'w') as f:
    f.write(content)
PYEOF
```

**Rule 2 — Secrets containing `$` MUST be written via Python, never via shell.**
`echo`, `sed`, and docker-compose `env_file:` ALL expand `$VAR` patterns. Bcrypt hashes (`$2b$12$...`), some API keys, and any value with `$` will be silently corrupted.

- `echo 'KEY=$2b$12$...' >> .env` — safe locally (single quotes), but shell injection risk in other contexts
- `docker-compose env_file: .env` — **ALWAYS corrupts bcrypt hashes** (expands `$2b`, `$XXXX` as variables)
- **Safe method**: volume-mount `.env` into container (`- ./.env:/app/.env:ro`) so pydantic-settings reads the raw file directly without docker-compose interpolation

**Rule 3 — docker-compose `env_file:` is banned for apps that use bcrypt or any secret with `$`.**
Use volume mount instead:
```yaml
# WRONG — corrupts $2b$12$... hashes:
app:
  env_file: .env

# CORRECT — pydantic-settings reads raw file, no interpolation:
app:
  volumes:
    - ./.env:/app/.env:ro
```

---

## Memory System

### Local (this project)
- **Architecture decisions (ADRs)**: `docs/KNOWLEDGE.md` — project-specific only. What you chose, why, what you rejected, impact. Read before architecture work.
- **Active tasks**: `docs/TASK.md`
- **Deploy config**: `docs/DEPLOY.md` — server access, paths, deploy flow
- **Code standards**: `docs/CONVENTIONS.md`

### Shared (cross-project, `{{VAULT_PATH}}/`)
- **Fails**: `fails/` — reproducible bugs + root cause + fix
- **Patterns**: `patterns/` — reusable working solutions
- **Gotchas**: `gotchas/` — non-obvious API/service/config truths
- Write via the `vault-write` skill. Read via lazy 3-tier (hot.md → grep folder → drill into specific file).
- Vault is its own git repo with its own CRUD policy (see vault CLAUDE.md).

### Rules
- Never duplicate info already in git history or code comments.
- Never write to both local and vault the same content — each fact has exactly one SSOT.
- If you find yourself wanting to write the same fail/pattern/gotcha to a second project's local file — STOP, write it to the vault instead.

## Task Completion (mandatory)
When marking any task done:
1. Remove from TASK.md Backlog/In Progress
2. Append to `docs/archive/TASK_ARCHIVE.md` with commit hash
3. Close GitHub issue: `gh issue close <number> --comment "Done in <commit>"`
   - Find issue: `gh issue list --search "T-NNN" --state open`

## Confidence Check
Before finishing any non-trivial implementation:
- Does the code compile/type-check? (tsc / ruff)
- Does the test pass?
- Did I consider edge cases?
- Is there debug code left?
If any answer is NO — fix before presenting to user.

---

## Token Economy Rules

> Full details: `.claude/rules/references/token-economy.md`

**Core rules (always active):**
- Do NOT write code until **95% confident** in what to build. <70% = Plan Mode + questions first.
- Write handoff + `/compact` at **>50% context** (hard rule — see § Context Budget). After 3-4 compactions — `/clear` + fresh session.
- `/clear` when switching to unrelated task.
- Limit terminal output: `--oneline -20`, `-q`, `| tail -n 50`. Never unbounded.
- Read files with `limit` + `offset`. One precise read > three exploratory reads.
- Disconnect unused MCP servers at session start (`/mcp`). Each adds ~17K tokens/message.
- Sonnet = default. Opus = deep planning only, <20% usage. Subagents cost 7-10x.
- Prompt cache expires after 5 min idle. `/compact` before stepping away.
