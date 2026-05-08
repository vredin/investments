# Investment Assistant — Claude Instructions

## Language
Respond in: **Russian** (user writes in Russian/Ukrainian)

## Session Memory (LAZY LOAD — don't read everything at once)

> **At session start** — read ONLY what's needed now (saves tokens every turn):
> 1. `docs/handoff.md` — if exists, read FIRST, resume from there, then delete it
> 2. `docs/TASK.md` — identify scope for this session
> 3. `{{VAULT_PATH}}/hot.md` — last 20 cross-project fails/patterns/gotchas (~2K tokens, always cheap)
> 4. Review MCP servers (`/mcp`) — disconnect any not needed for current tasks
>
> **Load on demand** (when relevant to current task):
> - `docs/CONVENTIONS.md` — before writing or reviewing code
> - `docs/KNOWLEDGE.md` — before architecture decisions (project-specific ADRs only)
> - `docs/DEPLOY.md` — before any deploy action
> - **Shared vault** (`{{VAULT_PATH}}/`) — grep-filter on demand:
>   - Before debugging: `grep -rl "<stack/domain>" {{VAULT_PATH}}/fails/`
>   - Before 3rd-party API integration: `grep -rl "<service>" {{VAULT_PATH}}/gotchas/`
>   - Before designing a solution: `grep -rl "<pattern keyword>" {{VAULT_PATH}}/patterns/`
>   - Never read the entire vault. Drill into specific `F-NNN`/`P-NNN`/`G-NNN` files only after filtering.

## Response Style

> Always load `caveman-distillate` skill for all dev tasks — fragments OK, drop filler,
> answer first. Deactivate only when user asks for verbose/detailed explanation.

## Token Economy

> - Do NOT write code until **95% confident** in what to build. Ask questions first.
> - **Context hard rule**: check `/context` every 20 tool calls. At **>50%** — STOP, write `docs/handoff.md`, `/compact`. Never wait for auto-compact at 95%. PreCompact hook snapshots transcript as fallback only (see `.claude/rules/workflow.md` § Context Budget).
> - `/clear` when switching to an unrelated task.
> - Limit terminal output: `--oneline -20`, `-q`, `| tail -n 50`.
> - Read files with `limit` + `offset` — never read 2000 lines for a 20-line function.
> - Subagents cost 7-10x — scale review depth to change size (see `skill-routing.md`).

## SSOT — Single Source of Truth (each fact lives in ONE place)

| Info Type | SSOT Location | Do NOT write to |
|-----------|---------------|-----------------|
| Code standards | `docs/CONVENTIONS.md` (local) | Code comments, KNOWLEDGE.md |
| Architecture decisions (this project) | `docs/KNOWLEDGE.md` (local) | Code comments, TASK.md |
| **Cross-project fails** | `{{VAULT_PATH}}/fails/` (shared vault) | Local files, KNOWLEDGE.md |
| **Cross-project patterns** | `{{VAULT_PATH}}/patterns/` (shared vault) | Local files, KNOWLEDGE.md |
| **Cross-project gotchas** (API/service surprises) | `{{VAULT_PATH}}/gotchas/` (shared vault) | Local files, code comments |
| Active tasks | `docs/TASK.md` (local) | handoff.md (handoff is one-time) |
| Deploy config | `docs/DEPLOY.md` (local) | KNOWLEDGE.md, .env files |
| Server/infra secrets | `.env.production` (local, gitignored) | docs/, code, logs |

> If you're about to write info that belongs in another file — stop and write it there instead.
> If the info is **reusable across projects**, it belongs in the shared vault (see Shared Knowledge Vault section below), NOT in any local file.

## Shared Knowledge Vault (cross-project KB)

**Location**: `{{VAULT_PATH}}/`
**What lives there**: fails (reproducible bugs + fix), patterns (reusable working solutions), gotchas (non-obvious API/service truths — e.g. "Meta test phone numbers silently drop real broadcasts").
**What stays local**: `docs/KNOWLEDGE.md` (this project's architectural decisions), `docs/TASK.md`, `docs/DEPLOY.md`, `docs/CONVENTIONS.md`.

### Reading from vault (lazy 3-tier)
1. **Always**: `{{VAULT_PATH}}/hot.md` — last 20 entries, ~2K tokens
2. **On demand**: grep-filter by stack/domain into `fails/`, `patterns/`, `gotchas/`
3. **Drill**: read a specific `F-NNN` / `P-NNN` / `G-NNN` file only after narrowing via 1-2

### Writing to vault
Use the **`vault-write`** skill. Full protocol lives in `.claude/skills/vault-write/SKILL.md`. Key rules:
- Dedup check before CREATE (grep the relevant folder first)
- `source-project` frontmatter field is mandatory — this is the authorship wall
- **Never** edit the body of another project's note — only append `## Contradictions` / `## Related` sections
- **Never** delete vault files — use `status: obsolete` / `superseded` flags
- One CRUD op = one git commit in the vault repo
- Contradictions always escalate to user via `AskUserQuestion` — never silently resolve

Vault has its own `CLAUDE.md` at the vault root — Claude reads it automatically when working with files there.

## Rules
See `.claude/rules/` — auto-loaded by Claude Code:
- `project.md` — stack, code standards, deploy
- `workflow.md` — pre-change protocol, bug fix protocol, deploy protocol
- `skill-routing.md` — which skill/agent to load per task type

## Key Commands
- `/init-project [path]` — initialize new project from this template (interactive)
- `/fix <bug>` — disciplined bug fix with failing test first
- `/test [backend|frontend|e2e|all]` — run test suites
- `/todo add <description>` — spec-first task planning with mandatory DA review
- `/todo done <id>` — archive completed task
- `/review [scope]` — full review pipeline: code quality + security audit + QA hacker scan
- `/orchestrate` — autonomous backlog execution with DA at every stage
- `/quick-plan <description>` — create implementation plan and save to specs/
- `/plansession` — plan next implementation session (spec system)
- `/implement` — execute current session plan (spec system)

## Agents
- `Diablo` — **mandatory critic**. Runs at: (1) spec planning before backlog, (2) implementation before commit. Verdicts: BLOCKED (stop), FIX FIRST (fix before commit), PROCEED WITH CAUTION, ACCEPTABLE. If BLOCKED — work stops until fixed.
- `Rex` — **dual Red/Blue team security agent**. RED mode: taint analysis, OWASP Top 10, PoC generation. BLUE mode: mitigation verification. Runs: before every deploy, on auth/payment/upload changes, on-demand audit. CRITICAL finding = deploy blocked. Skill: `.claude/skills/security-scan/`.

## Persistence Discipline (HARD RULE — applies to every response)

> Conversation memory is NOT persistence. /compact and /clear erase it. Only the file system survives.

**Banned phrases without an immediate tool call:**
- "записал" / "noted" / "I'll remember" / "I have it"
- "добавил в TODO" / "added to TODO"
- "зафиксирую" / "I'll record this"
- "это учтено" / "this is captured"

**Each such claim MUST be paired in the same turn with a tool call that writes to disk:**
- Task → `/todo add` → produces `docs/specs/T-NNN-*.md`
- Architectural decision → Edit `docs/KNOWLEDGE.md` or `docs/adr/<NNNN>-*.md`
- Business rule → `/rule` → produces row in `docs/RULES.md`
- Failure pattern → Edit `docs/FAILS.md` + (optional) Outline `Knowledge Base / Fails`
- Reusable solution → Edit `docs/PATTERNS.md` + (optional) Outline `Knowledge Base / Best Practices`

**If you can't pair the claim with a tool call** (e.g. user is brainstorming, not yet ready to commit) — say:
> "This is NOT persisted. To save: run /todo add for tasks, /rule for business rules, or ask me to Edit docs/KNOWLEDGE.md."

Never let the user believe something is recorded when it isn't.

## Business Logic Discipline (HARD RULE — applies to numerical/policy answers)

> The worst failure mode of LLMs: confidently inventing numbers that look correct.

**Before answering ANY question that involves:**
- Numerical values: rates, prices, fees, commissions, limits, quotas, percentages, deadlines, durations
- Calculation formulas
- Policy decisions: who can do X, when Y is allowed, what happens if Z

**You MUST:**
1. Read `docs/RULES.md` (auto-loaded at session start, but re-read if uncertain)
2. grep for the relevant subject
3. If found → cite the exact `R-NNN` row in your answer (e.g. "Per R-014: senior coach rate is 1500 UAH")
4. If NOT found → STOP. Output:
   > **RULE NOT IN docs/RULES.md.**  
   > I will not invent a value. Please:
   > - Confirm the rule + source, then I'll add via `/rule`
   > - OR point me to the document/contract where it's defined

**Banned phrases:**
- "I think the rate is..."
- "Based on similar features, it would be..."
- "Approximately..."
- "From our earlier conversation..." (conversation = not a source)

This rule applies even when the user seems to expect a number — refusing to invent is the correct answer.

