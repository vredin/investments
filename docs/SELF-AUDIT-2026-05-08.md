# Self-Audit — Investments — 2026-05-08
Period: 2026-05-01 to 2026-05-08 (extended to 2026-04-01 for stronger evidence)

## Summary
- Patterns found: 4
- Suggested file changes: 4
- Severity: **HIGH** (3 findings ≥5 occurrences)

## Findings

---

### PATTERN [workflow violation] (×23 in 5 weeks, ×9 in 7 days): [CHANGE] commits without preceding [BACKUP]

Evidence (last 7 days only — full list in audit data):
- `1ad404f [CHANGE] T-010: tooltip glossary` — preceded by `[BACKUP] T-010..015: спеки` (BACKUP was for specs, NOT for source edits)
- `c522fb4 [CHANGE] T-011: онбординг` — preceded by `[META] T-011 added` ✗
- `9771710 [CHANGE] T-012: scenario calc` — preceded by `[META] T-012` ✗
- `6694c6b [CHANGE] T-013: crisis guide` — preceded by `[META] T-013` ✗
- `1d4469b [CHANGE] T-014: risk profile` — preceded by `[META] T-014` ✗
- `81d88f1 [CHANGE] T-015: ticker analysis` — preceded by `[META] T-015 archived` ✗
- `5495c0d [CHANGE] T-016: E2E tests` — preceded by `[META] T-016 added` ✗
- `31445d0 [CHANGE] fix: step=1 goal_usd` — preceded by `[META] todo.md` ✗
- `4de5b40 [CHANGE] Fill docs/STACK.md` — preceded by `715925e Remove custom hook scripts` (no prefix) ✗

Root cause: PreToolUse hook in `.claude/settings.json` accepts last commit being `[BACKUP]` **OR** `[CHANGE]`. Once a `[CHANGE]` lands, the next edit session passes the gate without a fresh `[BACKUP]`. Pattern: do `[BACKUP] → edit → [CHANGE] → edit → [CHANGE] → edit → [CHANGE]…` — only the first BACKUP is real.

Suggested fix:
  File: `/Users/semishan/PycharmProjects/Investments/.claude/settings.json`
  Old text:
  ```
  "command": "bash -c 'GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0; LAST=$(git -C \"$GIT_ROOT\" log -1 --pretty=%s 2>/dev/null); [ -z \"$LAST\" ] && exit 0; echo \"$LAST\" | grep -qE \"^\\[(BACKUP|CHANGE)\\]\" && exit 0; echo \"=== PRE-CHANGE PROTOCOL REQUIRED ===\" >&2;
  ```
  New text:
  ```
  "command": "bash -c 'GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0; LAST=$(git -C \"$GIT_ROOT\" log -1 --pretty=%s 2>/dev/null); [ -z \"$LAST\" ] && exit 0; echo \"$LAST\" | grep -qE \"^\\[BACKUP\\]\" && exit 0; echo \"=== PRE-CHANGE PROTOCOL REQUIRED ===\" >&2;
  ```
  Rationale: Drop `CHANGE` from the accept regex. Force a fresh `[BACKUP]` before every edit session. After `[CHANGE]`, the next file edit blocks until user creates a new BACKUP commit.

---

### PATTERN [convention violation] (×20 in 14 days): commits without standard prefix

Evidence (sample):
- `b084bee Update launchd to multi-task wizard pattern from template` (today)
- `9c99040 Add generic launchd-runner for multi-task scheduling` (today)
- `5a2cd75 Add launchd /report scheduling pattern from template v3` (today)
- `c315216 Add launchd wrapper for daily /report` (today)
- `cf69c72 Update commands for Outline auto-publish architecture`
- `715925e Remove custom hook scripts that pre-dated v3`
- `94370d7 chore: archive T-004 price sync`
- `570ad2a feat: T-004 price sync via yfinance`
- `8eac09a fix(security): T-001 xlsx zip-bomb`
- ...11 more with `feat:`/`fix:`/`docs:`/`chore:` Conventional Commits style

Root cause: Pre-Change Protocol documents the prefix convention `[BACKUP]/[CHANGE]/[META]/[HANDOFF]/[FIX]/[PROCESS]` in `workflow.md` Step 5, but no commit-msg hook validates it. Today's 4 launchd commits prove the gap is still active.

Suggested fix:
  File: `/Users/semishan/PycharmProjects/Investments/.claude/hooks/commit-msg-prefix.sh` (NEW)
  Old text: (file does not exist)
  New text:
  ```bash
  #!/usr/bin/env bash
  # Reject commits without one of the approved prefixes.
  MSG_FILE="$1"
  FIRST_LINE=$(head -1 "$MSG_FILE")
  if echo "$FIRST_LINE" | grep -qE '^\[(BACKUP|CHANGE|META|HANDOFF|FIX|PROCESS)\]'; then
    exit 0
  fi
  echo "=== COMMIT MSG PREFIX REQUIRED ===" >&2
  echo "First line must start with one of:" >&2
  echo "  [BACKUP] [CHANGE] [META] [HANDOFF] [FIX] [PROCESS]" >&2
  echo "Got: $FIRST_LINE" >&2
  exit 1
  ```
  Plus install via `git config core.hooksPath .githooks` (or symlink to `.git/hooks/commit-msg`). Add note in `.claude/rules/workflow.md` Step 5.
  Rationale: Hook layer, not documentation. Prevents the pattern at write time, not at audit time.

---

### PATTERN [bug-fix protocol bypass] (×4 in 5 weeks): bug fixes skip /fix protocol

Evidence:
- `31445d0 [CHANGE] fix: step=1 goal_usd` — no preceding [BACKUP], no failing test mentioned in commit body, no FAILS.md entry
- `ead49d0 [CHANGE] Fix step=50 browser validation` — no [BACKUP], no FAILS.md
- `3e2349f [CHANGE] Fix recommend page crash` — no [BACKUP], no FAILS.md
- `e756b1a fix: mount .env as volume instead of env_file` — no [BACKUP] (no prefix at all), no FAILS.md

Root cause: `/fix` skill exists and enforces failing-test-first + FAILS.md update, but ad-hoc fixes are committed as plain `[CHANGE]` without invoking it. No friction — user notices bug, edits file directly.

Suggested fix:
  File: `/Users/semishan/PycharmProjects/Investments/.claude/rules/workflow.md`
  Old text:
  ```
  ## Bug Fix Protocol (mandatory)
  1. Check `docs/FAILS.md` for similar past failures FIRST
  2. `[BACKUP]` commit (Step 1 above)
  3. Write failing test FIRST — do not touch implementation until test exists
  ```
  New text:
  ```
  ## Bug Fix Protocol (mandatory)

  > **Trigger detection**: if user message contains `fix`, `сломалось`, `не работает`, `crash`, `error`, `bug`, `падает`, `500`, or commit subject begins with `fix:` — Claude MUST invoke `/fix` skill BEFORE editing any source file. Plain `[CHANGE]` commits for bug fixes are violations of this protocol (see SELF-AUDIT-2026-05-08 PATTERN [bug-fix protocol bypass]).

  1. Check `docs/FAILS.md` for similar past failures FIRST
  2. `[BACKUP]` commit (Step 1 above)
  3. Write failing test FIRST — do not touch implementation until test exists
  ```
  Rationale: Make trigger explicit. The skill exists; the gap is when to fire it. Adding the trigger phrase list makes it actionable.

---

### PATTERN [missing artifact] (×1, but blocks 4+ FAILS.md updates): docs/FAILS.md does not exist

Evidence:
- `docs/FAILS.md` referenced in `CLAUDE.md`, `workflow.md` (×4), `skill-routing.md` (×3)
- File missing on disk
- Bug fixes documented only in commit messages, not in queryable FAILS.md
- Outline KB / Fails created today (2026-05-08) but local file absent

Root cause: Template documentation references `docs/FAILS.md` but bootstrapping never creates the stub. Each bug fix that "should have updated FAILS.md" finds no file → silently skipped.

Suggested fix:
  File: `/Users/semishan/PycharmProjects/Investments/docs/FAILS.md` (NEW)
  Old text: (file does not exist)
  New text:
  ```markdown
  # FAILS — Reproducible bug patterns + fixes

  Local index. Outline mirror: Knowledge Base / Fails.

  Format per entry:

  ```
  ## F-NNN: <one-line symptom>
  - Date: YYYY-MM-DD
  - Stack: <python|js|infra|...>
  - Symptom: <what user/system observed>
  - Root cause: <actual cause, not workaround>
  - Fix: <commit hash + what changed>
  - Test: <test that prevents regression>
  ```

  ---
  ```
  Plus retroactive backfill: add F-001 (bcrypt env_file corruption — `e756b1a`), F-002 (step=50 browser validation — `ead49d0`), F-003 (recommend crash on missing pct fields — `3e2349f`), F-004 (step=1 goal_usd — `31445d0`).
  Rationale: Stub + 4 backfilled entries unblocks the workflow. Future fixes append.

---

## Apply
For each finding, you can:
- Accept → reply `apply finding K` (I run Edit + commit `[PROCESS] Apply self-audit finding: <one-line>`)
- Reject → I add `REJECTED: <reason>` here, won't suggest again
- Defer → I add `DEFERRED: <until>`

## Audit memory
- 2026-05-08: 4 findings (severity HIGH), pending review
