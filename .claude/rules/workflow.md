# Development Workflow Rules

> HARD RULES on Persistence / Business Logic / E2E Test Discipline live in `CLAUDE.md` (primary attention slot). This file owns process protocols.

---

## Project file overwrite discipline (HARD RULE)

> Bug 2026-05-08: blanket `cp -f $TPL/CLAUDE.md $PROJ/CLAUDE.md` overwrote project values (`Investment Assistant` / `Russian` reverted to `[PROJECT_NAME]` / placeholder).

**`cp -f` is BANNED on these files** (project-customized after `/init-project`):

| File | Project-specific content |
|---|---|
| `CLAUDE.md` | Project name, language, stack customizations |
| `.claude/rules/project.md` | Stack, deploy, secrets per project |
| `.claude/settings.json` | User permissions, hooks customizations |
| `.claude/.setup.json` | Outline collection IDs, loops, language |
| `docs/STACK.md` | Real lint/test/db/ssh values |
| `docs/CONTEXT.md` | Filled domain glossary |
| `docs/RUNBOOK.md` | Filled SSH alias / container names |
| `docs/RULES.md` | Real R-NNN business rules |
| `docs/KNOWLEDGE.md` | Project-specific architectural decisions |
| `docs/FAILS.md` | Project-specific F-NNN entries |
| `docs/PATTERNS.md` | Project-specific patterns |
| `docs/TASK.md` | Active backlog |
| `docs/DEPLOY.md` | Real server config |

**Allowed approaches** (preferred order):

1. **`Edit` tool surgical** — only changes what needs changing
2. **`cp -n`** (no-clobber) — safe for new projects, no-op for existing
3. **Conditional `cp` with grep** — `grep -q '\[PROJECT_NAME\]' file && cp -f tpl file`
4. **`cp -f`** — ONLY for template-defined files (commands, agents, skills, hooks, references)

When in doubt — assume project-customized, use Edit.

---

## TDD Discipline (HARD RULE — applies to ALL code-touching work)

> Test before code. Period. Commands `/fix`, `/orchestrate`, `/improve-arch` enforce. Direct edits without these commands violate.

**Cycle (5 steps):**
1. Write failing test FIRST — captures expected behavior
2. Run test → MUST FAIL (red) — proof test is real
3. Implement / fix — minimum code to pass
4. Run test → MUST PASS (green)
5. Static analysis from `docs/STACK.md` (`lint_cmd`, `typecheck_cmd`) — zero tolerance

**Anti-regression check** (separates real tests from theatre):
After step 4, mentally `git revert` impl. Test must FAIL again. If not — test targets implementation, not behavior. Rewrite assertions.

**Where enforced:**
| Command | TDD step location |
|---|---|
| `/fix` | STEP 2/3 (test+red), STEP 5/6 (fix+green) |
| `/orchestrate` | STEP 4 (test-writer agent), STEP 7 (green) |
| `/improve-arch` | refactor spec → /todo → /orchestrate |
| `/review` | quality gates verify tests for changes |

Direct edits without these commands: not enforced. PreToolUse hook still requires `[BACKUP]`, but TDD = self-discipline.

---

## Output style routing

> Full details: `.claude/rules/references/output-styles.md`

- **caveman-distillate** = always active (token economy, applied to everything)
- **humanizer** = final pass on human-facing reports (`/report`, `/docs sync`, `/self-audit`, `/gaps`, `/intent`, `/decompose`)
- They compose: caveman at generation, humanizer at finalization

---

## No Deferral Policy

If you CAN solve a problem — solve it. Do not defer.

**Resolve yourself:** missing dep → install. missing config → create. failing test → fix. needed env var → add to `.env.example`. file needed on server → `ssh`/`scp`. migration needed → generate+run. lint/type errors → fix.

**Ask user ONLY if:** missing creds (not in `.env.production`); business decision (scope/priority/UX); destructive action on shared resources (drop DB, force push, delete prod data).

**Banned:** "you can configure later" / "you may want to add" / "consider adding tests" / "don't forget to". Do it now.

---

## Session Scoping (context window discipline)

### Context Budget

Track via `/context`:
- **~60%**: write `docs/handoff.md`, run `/compact`
- **~80%**: finish current task only, then `/clear`
- **Never** wait for auto-compact at 95% (quality already degraded)

**Activity counters** (secondary):
| Metric | Warning | Hard limit |
|---|---|---|
| Tasks completed | 3-4 | 5 |
| File reads | 10 | 12 |
| Tool calls | 25 | 30 |

At warning: do NOT start new task. Finish, commit, handoff.
At hard limit: save state, compact.
Mid-task: `[WIP]` commit, handoff, compact, continue.

### Surviving compaction
1. Write `docs/handoff.md` BEFORE context critical
2. `/compact`
3. Next turn reads handoff (it's in Session Start), resumes
4. Delete `handoff.md` after pickup

`.claude/hooks/pre-compact-snapshot.sh` dumps transcript to `.claude/session-log/compact-*.jsonl` as fallback. Async — not a substitute for writing handoff yourself.

### Session Start (and after compaction)
1. If `docs/handoff.md` exists — read FIRST, resume, delete
2. **Post-compaction sanity check**: verify summary captured user's last message. If question NOT answered in summary — STOP, tell user "Твоє останнє запитання не потрапило в summary. Повтори, будь ласка." Don't proceed until answered.
3. Read `docs/TASK.md`, identify scope
4. Announce: "Session scope: T-NNN, T-NNN, T-NNN (X tasks)"
5. Review `/mcp`, disconnect unused
6. Load on demand: `CONVENTIONS.md` (before code), `KNOWLEDGE.md` (before arch), `FAILS.md` (before debug), `PATTERNS.md` (before recurring), `DEPLOY.md` (before deploy)

### Exit Signals (trigger Handoff)
"на сьогодні все" / "на сегодня все" / "done for today" / "закриваю" / "стоп" / "stop" / "хватит"

### Session-End Learning Review (before handoff)
Non-obvious fix → `docs/FAILS.md`. Reusable pattern → `docs/PATTERNS.md`. Architecture decision → `docs/KNOWLEDGE.md`.

### Handoff template
Write to `docs/handoff.md`:
- Completed: `- T-NNN: <title> — done, committed`
- In Progress: `- T-NNN: <title> — <state>` + uncommitted files list
- Next Session Should: 3 numbered items
- Context That Would Be Lost: non-obvious decisions, gotchas, blockers
- User's Last Unanswered Question: exact quote (CRITICAL for post-compact resume)
- Open Questions for User

Commit: `git commit -m "[HANDOFF] Session end: <summary>"`. Report: "Session done. X tasks. Handoff in `docs/handoff.md`."

---

## Research Protocol

When unsure about implementation/API/library/best-practice:
1. Check `docs/KNOWLEDGE.md`, `docs/PATTERNS.md`, `docs/FAILS.md`
2. Context7 MCP (`mcp__context7__*`) for lib/framework docs
3. Tavily / WebSearch for broader (API changes, known issues)

Never guess when official docs exist.

---

## Stuck Protocol (2+ failed attempts)

After 2 fails on same problem — STOP brute-forcing.

1. Stop and analyze: write what you tried + why it failed
2. Check `docs/FAILS.md` for similar pattern
3. Research via Context7 / WebSearch
4. Try fundamentally different strategy, not variation
5. Still stuck after 3rd attempt: tell user honestly — what you tried (3 approaches), root cause hypothesis, suggested next step (manual debug, dep upgrade, different lib). Ask guidance.

**NEVER:** retry same approach hoping different result; silently modify unrelated code; "it should work now" without verifying.

---

## Pre-Change Protocol (mandatory before editing ANY file)

### Step 1 — BACKUP Commit
```bash
git add <specific files> && git commit -m "[BACKUP] Pre-change: <description> | Risks: <list> | Scope: <files>"
```
**Never `git add -A`** — can stage `.env.production` or unrelated. List specific files.

Required: `[BACKUP]` prefix + what's changing + key risks + affected scope.

### Step 2 — Implement
Make changes per rules.

### Step 3 — Quality Gate (every commit)
Adapt to stack:
- Python: `uv run ruff check . && mypy src/ --ignore-missing-imports`
- TS: `npx tsc --noEmit && npx eslint src/`
- Tests: `pytest tests/ -q` or `npm test`
- Debug artifacts: `grep -rn "console\.log\|debugger\|TODO\|FIXME\|print(" src/`

### Step 4 — DA Review
Invoke `Diablo` agent. Verdict goes in CHANGE commit message.

### Step 5 — CHANGE Commit
```
[CHANGE] T-NNN: <imperative description>

What changed: <bullets>
Why: <requirement from spec AC>
Risk mitigation: <how risk addressed>
DA verdict: <ACCEPTABLE | PROCEED CAUTION — note | FIX FIRST — fixed: what>
Tested by: <command>
```

BACKUP commit stays in history. Do NOT use `--amend` (Claude Code prohibits).

---

## Commit message taxonomy (HARD RULE)

Every commit MUST start with one of:

| Prefix | When | Example |
|---|---|---|
| `[BACKUP]` | Pre-change checkpoint | `[BACKUP] Pre-change: T-005 \| Risks: ... \| Scope: app/bot/` |
| `[CHANGE]` | Implementation paired with prior `[BACKUP]` | `[CHANGE] T-005: Telegram bot bridge` |
| `[FIX]` | Bug fix via `/fix` (failing-test-first) | `[FIX] F-007: bcrypt corruption from env_file mount` |
| `[SEC]` | Security fix verified by Rex | `[SEC] xlsx zip-bomb size cap + magic bytes` |
| `[META]` | TASK.md, archive, planning (no code) | `[META] T-018 archived` |
| `[PROCESS]` | Workflow/hooks/settings/template | `[PROCESS] Add commit-msg validation hook` |
| `[HANDOFF]` | Session-end handoff doc | `[HANDOFF] Session end — 3 tasks done` |
| `[RULES]` | Business rule via `/rule` | `[RULES] Add R-014: senior coach 1500 UAH/training` |

PreToolUse hook on `Bash` matcher blocks `git commit -m` when message lacks valid prefix.

---

## Bug fix triggers (HARD RULE — Claude must invoke `/fix`, not edit directly)

> Bypassing `/fix` causes: no failing test, no FAILS.md entry, no anti-regression, no Diablo on diagnosis.

User message contains (case-insensitive): "fix" / "bug" / "broken" / "doesn't work" / "сломано" / "не работает" / "падает" / "ошибка" / "regression" / "broke after" / "почему X не Y" / direct error reports (traceback, stack trace, exception class).

Claude MUST:
1. STOP. No code edits.
2. Reply: "This looks like a bug fix. Use `/fix` for failing-test-first + Diablo + FAILS.md. Run `/fix <bug>` to start. Skip protocol only for trivial typo if you say so explicitly."
3. Wait for direction.

Override (rare): "skip /fix, just fix typo on line N" → proceed inline.

---

## Bug Fix Protocol (mandatory)

1. Check `docs/FAILS.md` for similar past failures FIRST
2. `[BACKUP]` commit
3. Write failing test FIRST — don't touch impl until test exists
4. Run test → red phase
5. Root cause analysis — exact cause, list 2-3 options
6. Fix + quality gate
7. Run test → green phase
8. **Same bug elsewhere?** — search codebase for same pattern. Fix ALL occurrences now.
9. DA review
10. `[CHANGE]` commit
11. If non-obvious fix → add `docs/FAILS.md` entry
12. If deploying — follow `docs/DEPLOY.md`, verify services after

---

## Deploy Protocol

Before deploy — read `docs/DEPLOY.md`. All server config there.

**Rules:**
1. SSH: use ALIAS from `docs/DEPLOY.md` (e.g. `ssh vps3`). Never raw IP.
2. Secrets: `scp .env.production <alias>:<path>/.env`. Never ask user to manually edit on server.
3. API keys: provided once → in `.env.production`. Never ask again. Missing → tell user which key, ask to add to local `.env.production`.
4. Flow: follow exact steps in `docs/DEPLOY.md`. Don't improvise.
5. Verify: check services running after deploy.
6. Never edit code on server. Local edit → commit → push → server pull. Runtime config (`.env`) excepted.

**Secrets:** live in local `.env.production` (gitignored). Never commit. Never print/log values. Never store in `docs/` or memory files. Missing `.env.production` → create from `.env.example`, ask user to fill values ONCE.

---

## Memory System

- Architecture decisions: `docs/KNOWLEDGE.md`
- Active tasks: `docs/TASK.md`
- Failure patterns: `docs/FAILS.md` (append after non-obvious fix)
- Established solutions: `docs/PATTERNS.md` (append on recurring solved)
- Deploy config: `docs/DEPLOY.md`
- Never duplicate info already in git history or code comments
- **Pruning**: when FAILS.md/PATTERNS.md exceeds 30 entries, archive older to `docs/archive/FAILS_ARCHIVE.md` / `PATTERNS_ARCHIVE.md`. Keep 20 most recent in active.

---

## Task Completion (mandatory)

When marking task done:
1. Remove from TASK.md Backlog/In Progress
2. Append to `docs/archive/TASK_ARCHIVE.md` with commit hash
3. Close GitHub issue: `gh issue close <number> --comment "Done in <commit>"` (find via `gh issue list --search "T-NNN" --state open`)

---

## Confidence Check

Before finishing non-trivial implementation: code compiles/type-checks? test passes? edge cases considered? debug code left? If any NO — fix before presenting.

---

## Token Economy Rules

> Full details: `.claude/rules/references/token-economy.md`. Persistence/BusinessLogic/E2E rules: `CLAUDE.md`.

**Core (always active):**
- No code until 95% confident. <70% = Plan Mode + ask first.
- `/compact` at ~60% context. After 3-4 compactions → `/clear`.
- `/clear` on unrelated task switch.
- Terminal output: `--oneline -20`, `-q`, `| tail -n 50`. Never unbounded.
- Read with `limit` + `offset`. One precise read > three exploratory.
- Disconnect unused MCP at session start. Each adds ~17K tokens/message.
- Sonnet default. Opus = deep planning only, <20%. Subagents 7-10×.
- Prompt cache 5 min idle. `/compact` before stepping away.
