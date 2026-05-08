# [PROJECT_NAME] — Claude Instructions

## Language
Respond in: **[Ukrainian / English / ...]**

## Session Memory (LAZY LOAD — don't read everything at once)

> **At session start — ALWAYS read these (mandatory):**
> 1. `docs/handoff.md` — if exists, read FIRST, resume from there, then delete it
> 2. `docs/TASK.md` — identify scope for this session
> 3. **`docs/RULES.md`** — business rules. ALWAYS auto-loaded. Required to refuse hallucination on rate/policy questions. Keep it small (<200 lines); archive old rows as needed.
> 4. Review MCP servers (`/mcp`) — disconnect any not needed for current tasks
>
> **Load on demand** (when relevant to current task):
> - `docs/CONVENTIONS.md` — before writing or reviewing code
> - `docs/KNOWLEDGE.md` — before architecture decisions
> - `docs/CONTEXT.md` — before refactoring or design discussions (domain glossary)
> - `docs/FAILS.md` — before debugging or fixing bugs
> - `docs/PATTERNS.md` — before solving recurring problems
> - `docs/DEPLOY.md` — before any deploy action
> - `docs/RUNBOOK.md` — when prod misbehaves

## Response Style

> Always load `caveman-distillate` skill for all dev tasks — fragments OK, drop filler,
> answer first. Deactivate only when user asks for verbose/detailed explanation.

## Token Economy

> - Do NOT write code until **95% confident** in what to build. Ask questions first.
> - `/compact` at **~60%** context — don't wait for auto-compact at 95%.
> - `/clear` when switching to an unrelated task.
> - Limit terminal output: `--oneline -20`, `-q`, `| tail -n 50`.
> - Read files with `limit` + `offset` — never read 2000 lines for a 20-line function.
> - Subagents cost 7-10x — scale review depth to change size (see `skill-routing.md`).

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

## E2E Test Discipline (HARD RULE — applies to frontend changes)

Frontend changes without a Playwright `.spec.ts` are NOT done. Period.

Browser-MCP tools (`mcp__claude-in-chrome__*` and similar) are for **debugging** only — never as a substitute for writing a test.

**Forbidden mental patterns:**
- "Проверю в браузере" → write `tests/e2e/<feature>.spec.ts`
- "Кликну через chrome-MCP" → write the spec
- "Это маленькое изменение, тест избыточен" → small changes hide regressions; write the spec

The Playwright spec goes in the SAME commit as the implementation. The PreToolUse hook + `/review` STEP 4.6 + `/fix` STEP 6.5 enforce this — a frontend `[CHANGE]` without `tests/e2e/*.spec.ts` in the diff is BLOCKED.

See `.claude/rules/workflow.md` and `.claude/skills/webapp-testing/SKILL.md` for full rule and the narrow chrome-MCP allowed list.

---

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

## SSOT — Single Source of Truth (each fact lives in ONE file)

| Info Type | SSOT File | Do NOT write to |
|-----------|-----------|-----------------|
| Code standards | `docs/CONVENTIONS.md` | Code comments, KNOWLEDGE.md |
| Architecture decisions | `docs/KNOWLEDGE.md` | Code comments, TASK.md |
| Failure patterns | `docs/FAILS.md` | KNOWLEDGE.md, code comments |
| Reusable solutions | `docs/PATTERNS.md` | FAILS.md, KNOWLEDGE.md |
| Active tasks | `docs/TASK.md` | handoff.md (handoff is one-time) |
| **Business rules / rates / formulas** | **`docs/RULES.md`** | **conversation memory, KNOWLEDGE.md** |
| Deploy config | `docs/DEPLOY.md` | KNOWLEDGE.md, .env files |
| Server/infra secrets | `.env.production` (local, gitignored) | docs/, code, logs |

> If you're about to write info that belongs in another file — stop and write it there instead.

## Rules
See `.claude/rules/` — auto-loaded by Claude Code:
- `project.md` — stack, code standards, deploy
- `workflow.md` — pre-change protocol, bug fix protocol, deploy protocol
- `skill-routing.md` — which skill/agent to load per task type

## Key Commands

**Daily (memorize these 4):**
- `/todo` — spec-first task planning (uses grill-me skill, then Diablo via /da)
- `/orchestrate` — autonomous backlog execution (calls test-writer, code-reviewer, perf-analyzer, Rex, Diablo)
- `/general <question>` — verified answer with mandatory evidence-first, no speculation
- `/rule <statement>` — capture business rule into docs/RULES.md (rates, fees, formulas, policies). Use INSTEAD of conversation memory.

**Setup & init:**
- `/setup` — wizard: fresh install (asks language), MCP reconfigure, verify health, v2→v3 migrate, Bootstrap project collection, Register loops, Setup launchd schedules
- `/init-project [path]` — scaffold a new project from this template (interactive)
- `/911` — cheatsheet of all template commands grouped by use case (when you forget what's available)

**On-demand (rare):**
- `/intent <vague-idea>` — greenfield: idea → PRD via research + Diablo + verification. Output: docs/prd/PRD-NNN.md
- `/decompose <PRD-NNN | requirements-doc>` — PRD → Architecture (ADRs) → Epics → Tasks. 4 Diablo gates. Output: docs/adr/, docs/epics/, docs/specs/T-NNN.
- `/council <question>` — Opus + Sonnet parallel deliberation (no external API)
- `/fix <bug>` — disciplined bug fix with failing test first + Diablo
- `/review [scope]` — full review pipeline: code-reviewer + Rex + qa-expert + perf + Diablo
- `/gaps [missing|modern|both|<path>]` — service-level audit: what's missing in the service vs production-grade SaaS, what's outdated vs 2025-26 modern practices
- `/da [spec|plan|impl|review] [target]` — explicit Diablo invocation
- `/improve-arch [path]` — refactor for depth (Ousterhout-style, with ADR generation)

**Auto via /loop (you don't invoke manually):**
- `/report` — daily progress to Outline `Knowledge Base / Daily Status` (set `/loop "0 18 * * *" /report`)
- `/docs sync` / `/docs audit` — weekly drift detection (`/loop "0 9 * * 1" /docs audit`)
- `/self-audit` — weekly process improvement (`/loop "0 10 * * 5" /self-audit`)
- `/self-audit --global` — bi-weekly cross-project pattern detection

**Inside-other-commands (don't invoke directly):**
- `/test`, `/quick-plan`

## Knowledge Base (Outline)

External KB at `https://outline.semishan.pro` via MCP (configure once via `/setup`).

**Two collections:**
- `Knowledge Base` (shared, cross-project): Fails, Best Practices, Tricks, Daily Status
- `Project: <name>` (per-project): Architecture, API Reference, Runbook, Knowledge, Decisions, Rules

**Auto-publish (no prompt):**
- `/fix` → F-NNN to Shared/Fails
- `/rule` → R-NNN to Project/Rules
- `/improve-arch` → ADR to Project/Decisions; reusable patterns to Shared/Best Practices (after explicit flag)
- `/report` (via /loop daily) → Shared/Daily Status
- `/docs sync --publish` (via /loop weekly) → Project/{Architecture, API, Runbook, Knowledge, Rules}

**Ask first:**
- `/general` final save (subjective whether to publish)
- `/council` verdict to Best Practices

**Control flags** in `.claude/.setup.json` → `outline.auto_publish.*` — flip to `false` per category to disable.

**Full contract**: `docs/OUTLINE-CONTRACT.md` — single source of truth on what publishes where, when.

Search via `mcp__outline__search_documents` (preferred) or `bin/outline.sh search` (fallback).

## Agents

- `Diablo` — **mandatory critic**. Runs from `/da`, auto-invoked in `/todo`, `/fix`, `/review`, `/orchestrate`. Verdicts: BLOCKED / FIX FIRST / PROCEED CAUTION / ACCEPTABLE; each carries a Next step.
- `Rex` — **dual Red/Blue team security agent**. RED: taint analysis, OWASP Top 10, supply-chain checks, PoC generation. BLUE: crypto + auth + secrets verification. Runs: before deploy, on auth/payment/upload changes, on-demand audit.
- `code-reviewer`, `qa-expert`, `design-reviewer`, `performance-analyzer` — invoked from `/review` and `/orchestrate` STEPs 7.3/7.4.
- `test-writer`, `orchestrator` — internal pipeline agents.
