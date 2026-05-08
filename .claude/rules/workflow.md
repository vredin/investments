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

## Project file overwrite discipline (HARD RULE)

> Bug discovered 2026-05-08: blanket `cp -f $TPL/CLAUDE.md $PROJ/CLAUDE.md` during template propagation overwrote project-customized values (`Investment Assistant` / `Russian` reverted to `[PROJECT_NAME]` / `[Ukrainian / English / ...]`). Same risk for any per-project file.

**`cp -f` is BANNED on these files** (always project-customized after `/init-project`):

| File | Project-specific content |
|---|---|
| `CLAUDE.md` | Project name, language, project-specific stack, command list customizations |
| `.claude/rules/project.md` | Stack details, deploy info, secrets handling per project |
| `.claude/settings.json` | User permissions block, hooks customizations |
| `.claude/.setup.json` | Outline collection IDs, registered loops, language preference |
| `docs/STACK.md` | Real lint/test/db/ssh values |
| `docs/CONTEXT.md` | Filled domain glossary |
| `docs/RUNBOOK.md` | Filled SSH alias / container names / failure scenarios |
| `docs/RULES.md` | Real R-NNN business rules |
| `docs/KNOWLEDGE.md` | Architectural decisions specific to project |
| `docs/FAILS.md` | Project-specific F-NNN entries |
| `docs/PATTERNS.md` | Project-specific patterns |
| `docs/TASK.md` | Active backlog |
| `docs/DEPLOY.md` | Real server config |

**Allowed approaches** (in order of preference):

1. **Edit tool with surgical `old_string`/`new_string`** — only changes what needs changing, preserves rest
2. **`cp -n` (no-clobber)** — only copies if file doesn't exist; safe for new projects, no-op for existing
3. **Conditional copy with grep** — `grep -q '\[PROJECT_NAME\]' file && cp -f tpl file` — only overwrite if still placeholder
4. **`cp -f`** — ONLY for files NOT in the table above (template-defined files like commands, agents, skills, hooks)

**Specific rule for propagation scripts (running cp from template to projects)**:
- For each file in the table above: use `cp -n`, NOT `cp -f`
- If you intentionally want to update one of these — use `Edit` to merge changes, never `cp -f`
- Exception: when you've just verified via grep that the file STILL has placeholders (means it was never customized) — then `cp -f` is OK

**The mental model**: template files are categorized as either:
- **Template-defined** (cp -f safe): commands, agents, skills, hooks, scripts in `bin/`, examples
- **Project-customized** (cp -f BANNED): everything in the table above

When in doubt — assume project-customized and use Edit.

---

## TDD Discipline (HARD RULE — applies to ALL code-touching work)

> Test before code. Period. Commands /fix, /orchestrate, /todo→/orchestrate, /improve-arch→/orchestrate enforce this. Direct edits without going through these commands violate the rule.

**The TDD cycle (5 steps, every time)**:

1. **Write failing test FIRST** — captures the expected behavior. Test references current code state where applicable.
2. **Run test → MUST FAIL (red)** — proof that the test reproduces the absence/break of the feature. If test passes here, it's testing the wrong thing.
3. **Implement / fix** — minimum code to make test pass.
4. **Run test → MUST PASS (green)** — feature is implemented.
5. **Static analysis** — read commands from `docs/STACK.md`:
   - `lint_cmd` (ruff / eslint)
   - `typecheck_cmd` (mypy / tsc)
   - All errors fixed before commit. Zero tolerance.

**Anti-regression check** (the rule that distinguishes real tests from theatre):
After step 4, mentally `git revert` the implementation. Would the test FAIL again? If yes — test is real. If no — test is testing implementation details, not behavior. Rewrite assertions to target observable user-facing outcomes.

**Where this is enforced**:

| Command | TDD step location |
|---|---|
| `/fix` | STEP 2 (write test), STEP 3 (red), STEP 5 (fix + static), STEP 6 (green) |
| `/orchestrate` | STEP 4 (test-writer agent, gate=fail), STEP 5 (impl), STEP 6 (static), STEP 7 (green), STEP 7.3 (code-reviewer quality gate) |
| `/improve-arch` | Produces refactor spec → goes through /todo → /orchestrate which enforces TDD |
| `/review` | Quality gates including verifying tests exist for changes |

**Direct edits without /fix or /orchestrate**: not enforced. Discouraged for non-trivial changes. PreToolUse hook still requires `[BACKUP]` commit, but TDD must be self-discipline.

---

## Output style routing — token economy + human readability

> Different consumers, different style. Internal output → terse. Human-facing reports → natural.

**caveman-distillate** (token economy — ALWAYS active):
- All commands load it as default
- Strips filler words, articles, hedging
- Fragments OK
- Output ~65-85% shorter than naive AI prose
- Applied to: tool calls, status updates, internal artifacts, code review findings

**humanizer** (anti-AI-prose — applied to FINAL human-facing output):
- Strips «delve», «tapestry», «pivotal», em-dash overuse
- Removes sycophantic openers («Great question…»)
- Removes promotional language («seamlessly», «cutting-edge»)
- Keeps facts/numbers/code intact, only prose changes
- Applied to:
  - `/report` daily status (humans read in morning)
  - `/docs sync` auto-generated content (devs read for onboarding)
  - `/self-audit` remediation file (you decide which to apply)
  - `/gaps` audit report (prioritization basis)
  - `/intent` PRD (contract for team)
  - `/decompose` ADRs/Epics (architecture review)

**caveman + humanizer together**:
- caveman fights LLM verbosity at generation time
- humanizer fights LLM prose-mannerisms at finalization time
- They compose: terse + natural

**NOT applied with humanizer**:
- Tables (already structured)
- Code blocks (semantic, can't paraphrase)
- Diff blocks in self-audit (exact citations)
- Direct quotes from source files (in /general VERIFIED claims)

---

## E2E Test Discipline (HARD RULE)

> Frontend changes without a Playwright e2e test are NOT done. Browser-tool clicking is NOT a test.

**Frontend change** = any modification touching:
- `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.html`, `*.css`, `*.scss`
- Route handlers / API endpoints called from the frontend (auth, data, payment, upload)
- User-facing flows in any form

**Required**: a Playwright `.spec.ts` file in `tests/e2e/` (or whatever path `docs/STACK.md` declares) that:
- Reproduces the user-facing flow end-to-end against the real running app
- FAILS before the change (red)
- PASSES after the change (green)
- FAILS again after `git revert` of the implementation (anti-regression)

The test goes in the **same commit** as the implementation. A frontend `[CHANGE]` commit with no `tests/e2e/*.spec.ts` in the diff is not done.

**Banned phrases as substitutes for an e2e test**:
- "Я проверил в браузере, работает"
- "Кликнул, всё ok"
- "Запросил через chrome MCP, выглядит правильно"
- "Скриншот в браузере подтверждает"
- "Это маленькая правка, тест не нужен"
- "Это тривиальное изменение"
- "В UI визуально работает"

**Browser-MCP tools (`mcp__claude-in-chrome__*` and similar) are for DEBUGGING, never as a test substitute.** See `.claude/skills/webapp-testing/SKILL.md` for the explicit allowed/forbidden boundary.

**If the project doesn't have Playwright set up yet** — set it up as part of the first frontend task that needs e2e coverage. Don't defer. The setup overhead amortizes after the second test.

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

## Commit message taxonomy (HARD RULE)

Every commit MUST start with one of:

| Prefix | When | Example |
|---|---|---|
| `[BACKUP]` | Pre-change checkpoint, before editing files | `[BACKUP] Pre-change: T-005 Telegram bot \| Risks: ... \| Scope: app/bot/` |
| `[CHANGE]` | Implementation completed, paired with prior `[BACKUP]` | `[CHANGE] T-005: Telegram bot bridge` |
| `[FIX]` | Bug fix completed via `/fix` protocol (failing-test-first) | `[FIX] F-007: bcrypt corruption from env_file mount` |
| `[SEC]` | Security fix verified by Rex | `[SEC] xlsx zip-bomb size cap + magic bytes` |
| `[META]` | TASK.md, archive, planning artifacts (no code change) | `[META] T-018 archived` |
| `[PROCESS]` | Workflow rules, hooks, settings, template updates | `[PROCESS] Add commit-msg validation hook` |
| `[HANDOFF]` | Session-end handoff doc | `[HANDOFF] Session end — 3 tasks done` |
| `[RULES]` | Business rule via `/rule` command (auto-generated) | `[RULES] Add R-014: senior coach 1500 UAH/training` |

The PreToolUse hook on `Bash` matcher blocks `git commit -m` when message lacks valid prefix.

## Bug fix triggers (HARD RULE — Claude must invoke `/fix`, not edit directly)

> Bypassing `/fix` causes: no failing test, no FAILS.md entry, no anti-regression
> guarantee, no Diablo attack on the diagnosis. The `/fix` protocol exists to
> prevent the same bug from recurring silently.

When the user message contains any of these phrases (case-insensitive):

- "fix", "bug", "broken", "doesn't work", "not working"
- "сломано", "не работает", "падает", "ошибка"
- "regression", "broke after", "stopped working"
- "почему X не Y", "should be Z but isn't"
- direct error reports: traceback, stack trace, error code, exception class

Claude MUST:
1. **Stop**. Do not jump into code edits.
2. Reply: "This looks like a bug fix. Use `/fix` to ensure failing-test-first + Diablo + FAILS.md entry. Run `/fix <bug description>` to start. If you want to skip the protocol for a trivial typo, say so explicitly."
3. Wait for user direction.

The user can override (rarely): "skip /fix, just fix the typo on line N" → then proceed inline. But default behavior is route to `/fix`.

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
