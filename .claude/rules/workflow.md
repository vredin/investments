# Development Workflow Rules

## Persistence Discipline (HARD RULE)

> Conversation memory is not persistence. /compact and /clear erase it. Files survive.

Phrases like "записал", "added to TODO", "noted", "I'll remember", "зафиксирую" are BANNED unless the same turn includes a tool call that writes to disk.

**Map: claim → required tool call**

| Claim | Required action |
|---|---|
| "added to TODO" / "записал в задачи" | `/todo add <description>` (creates docs/specs/T-NNN-*.md) |
| "noted this decision" / "запомнил" | Edit `docs/KNOWLEDGE.md` or create `docs/adr/<NNNN>-*.md` |
| "captured the rule" / "запомнил ставку" | `/rule <statement>` (creates row in docs/RULES.md) |
| "I'll remember this failure" / "зафиксирую этот баг-паттерн" | Edit `docs/FAILS.md` |
| "this is captured for next time" | At minimum: append to `docs/handoff.md` or `docs/PATTERNS.md` |

If user is brainstorming (not yet ready to commit info to disk) — say so explicitly:
> "This is NOT persisted yet. To save: run /todo / /rule / Edit docs/KNOWLEDGE.md."

**Never let the user believe something is recorded when it isn't.**

---

## Business Logic Discipline (HARD RULE)

Before answering any numerical or policy question:
1. Read `docs/RULES.md`
2. grep for the subject
3. If found → cite the `R-NNN` row
4. If NOT found → STOP. Refuse to invent. Output the "RULE NOT IN docs/RULES.md" message from CLAUDE.md.

This rule applies even when:
- User seems to expect a number ("какая ставка у тренера?")
- The number was discussed earlier in this conversation (conversation memory ≠ source)
- A "similar" rule exists for a different subject (do not infer by analogy)

Refusing to invent is the correct answer. The cost of "I don't know, show me where this is defined" is much lower than the cost of inventing the wrong number.

---

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

### Context Budget

You work best at the top of your context window. Track TWO things:

**Context window %** (primary — check with `/context`):
- **~60%**: write handoff.md, run `/compact` proactively
- **~80%**: finish current task ONLY, then `/clear` + new session
- **Never** wait for auto-compact at 95% — quality is already degraded

**Activity counters** (secondary safety net):

| Metric | Warning | Hard limit |
|--------|---------|------------|
| Tasks completed | 3-4 | 5 |
| File reads | 10 | 12 |
| Total tool calls | 25 | 30 |

**At warning** (any metric): do NOT start a new task. Finish current, commit, handoff.
**At hard limit**: save state and compact (see below).
**Mid-task at limit**: commit `[WIP]`, write handoff, compact, continue.

### Surviving Compaction (auto-recovery)

Context compaction WILL happen. Prepare for it so nothing is lost:

1. **Before compaction** — write `docs/handoff.md` with current state (what's done, what remains, decisions made)
2. **Compact** — run `/compact` or let auto-compaction happen
3. **After compaction** — Claude reads `docs/handoff.md` (it's in Session Start rules), picks up context, continues work
4. **Delete handoff.md** after picking up context

> handoff.md is external memory that survives compaction. The user does NOT need to start a new session.
> Write it BEFORE context gets critical — not after. If compaction happens before you write it, the context is lost.

### Limits
- **Max tasks per session**: 3-5 (not 15-25 — quality over quantity).
- **Hard stop trigger**: 12 file reads OR 30 tool calls OR 5 completed tasks — whichever comes first.

### Session Start (also applies after compaction)
1. If `docs/handoff.md` exists — read it FIRST, resume from there, then delete it
2. **After compaction only — check for lost user question**: if resuming from auto-compaction summary, verify the summary captures the user's last message. If the last user message was a question or request that is NOT answered in the summary — stop, tell the user: "Твоє останнє запитання не потрапило в summary. Повтори, будь ласка." Do NOT proceed with pending tasks until the user's question is answered.
3. Read `docs/TASK.md` — identify scope for this session
4. Announce: "Session scope: T-NNN, T-NNN, T-NNN (X tasks)"
5. Review MCP servers (`/mcp`) — disconnect any not needed for current tasks
6. Load other docs **on demand** (not all at once — saves ~500+ tokens per turn):
   - `docs/CONVENTIONS.md` — before writing/reviewing code
   - `docs/KNOWLEDGE.md` — before architecture decisions
   - `docs/FAILS.md` — before debugging or fixing bugs
   - `docs/PATTERNS.md` — before solving recurring problems
   - `docs/DEPLOY.md` — before any deploy action

### Exit Signals (trigger Session End immediately)
If the user says any of these — start Handoff Protocol NOW:
- "на сьогодні все" / "на сегодня все" / "done for today" / "that's all"
- "закриваю" / "heading out" / "talk later" / "closing"
- "стоп" / "stop" / "enough" / "хватит"

### Session-End Learning Review (before writing handoff)
Before writing handoff.md, review the session for learnings:
- Any non-obvious fix? → Add to `docs/FAILS.md`
- Any reusable pattern discovered? → Add to `docs/PATTERNS.md`
- Any architecture decision made? → Add to `docs/KNOWLEDGE.md`

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
- <gotcha discovered but not yet in FAILS.md>
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

1. **First**: check `docs/KNOWLEDGE.md`, `docs/PATTERNS.md`, `docs/FAILS.md`
2. **Second**: use Context7 MCP (`mcp__context7__*`) for technical documentation of libraries and frameworks
3. **Third**: use Tavily / WebSearch for broader internet search (API changes, known issues, community solutions)

**Never guess** when official documentation is available. Look it up.

---

## Stuck Protocol (2+ failed attempts)

If you've tried to fix something **twice and it still fails** — STOP brute-forcing.

### After 2 failed attempts:
1. **Stop and analyze**: write down what you tried and why it failed
2. **Check FAILS.md**: has this pattern been seen before?
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
uv run ruff check . && mypy src/ --ignore-missing-imports

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
1. Check `docs/FAILS.md` for similar past failures FIRST
2. `[BACKUP]` commit (Step 1 above)
3. Write failing test FIRST — do not touch implementation until test exists
4. Run test to confirm failure (`red` phase)
5. Root cause analysis — identify exact cause, list 2–3 options
6. Fix + quality gate (Step 3 above)
7. Run test again — must pass (`green` phase)
8. **Same bug elsewhere?** — search codebase for the same pattern that caused this bug. If found in other files — fix ALL occurrences now, not just the one reported
9. DA review (Step 4 above)
10. `[CHANGE]` commit (Step 5 above)
11. If fix pattern was non-obvious: add entry to `docs/FAILS.md`
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

---

## Memory System
- Architecture decisions: `docs/KNOWLEDGE.md`
- Active tasks: `docs/TASK.md`
- Failure patterns: `docs/FAILS.md` — append after every non-obvious fix
- Established solutions: `docs/PATTERNS.md` — append when a recurring pattern is solved
- Deploy config: `docs/DEPLOY.md` — server access, paths, deploy flow
- Never duplicate info already in git history or code comments
- **Pruning**: when FAILS.md or PATTERNS.md exceeds 30 entries, archive older entries to `docs/archive/FAILS_ARCHIVE.md` or `docs/archive/PATTERNS_ARCHIVE.md` — keep only the 20 most recent/relevant in the active file

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
- `/compact` at **~60%** context. After 3-4 compactions — `/clear` + fresh session.
- `/clear` when switching to unrelated task.
- Limit terminal output: `--oneline -20`, `-q`, `| tail -n 50`. Never unbounded.
- Read files with `limit` + `offset`. One precise read > three exploratory reads.
- Disconnect unused MCP servers at session start (`/mcp`). Each adds ~17K tokens/message.
- Sonnet = default. Opus = deep planning only, <20% usage. Subagents cost 7-10x.
- Prompt cache expires after 5 min idle. `/compact` before stepping away.
