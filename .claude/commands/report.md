---
name: report
description: 'Daily progress report — what was done, what is in progress, what is blocked. Posts to Outline + saves locally. Designed for /loop daily.'
argument-hint: [today | yesterday | YYYY-MM-DD]
allowed-tools: Read, Write, Bash
model: sonnet
---

> **Style:** Load `caveman-distillate` skill — terse responses.

# /report — Daily Status

Period: `${ARGUMENTS:-today}` (default: today)

---

## STEP 1 — Determine period and resolve project

```bash
case "${ARGUMENTS:-today}" in
  today)     SINCE=$(date -v0H -v0M -v0S +%Y-%m-%d) ;;
  yesterday) SINCE=$(date -v-1d -v0H +%Y-%m-%d); UNTIL=$(date -v0H +%Y-%m-%d) ;;
  *)         SINCE="$ARGUMENTS" ;;
esac
PROJECT=$(basename "$(pwd)")
```

---

## STEP 2 — Gather data

| Source | Command | Purpose |
|---|---|---|
| Git activity | `git log --since=$SINCE --pretty='%h %s' --no-merges` | Commits this period |
| Files changed | `git log --since=$SINCE --name-only --pretty='' \| sort -u` | Touched files |
| Closed tasks | `grep '$SINCE' docs/archive/TASK_ARCHIVE.md` | T-NNN done |
| In progress | `awk '/## In Progress/,/##/' docs/TASK.md` | Active tasks |
| New fails | search Outline `Knowledge Base / Fails` for docs created since $SINCE with project tag | What broke |
| Last report | search Outline `Knowledge Base / Daily Status` for `<project>` last entry | Delta basis |

If git log is empty AND no TASK movements AND no new fails → output `No activity for $PROJECT on $SINCE` and STOP. Do not publish empty reports.

---

## STEP 3 — Compose report

Template:
```markdown
# Daily Report — <PROJECT> — <DATE>

## Done (<N> commits)
- T-NNN: <title> — <one-line outcome> [<commit_sha>]
- T-NNN: <title> — <one-line outcome> [<commit_sha>]

## In Progress
- T-NNN: <title> — <state in one sentence>

## Blocked / Needs decision
- <blocker> — needs <user input | external | architectural call>

## Learned this session
- F-NNN: <fail title> (link to Outline)
- <new pattern observed, if non-trivial>

## Tomorrow / Next session
- T-NNN, T-NNN  
- <or: "no specific plan, /todo list to choose">

## Metrics
- Files touched: <N>
- Tests added: <N>
- LOC delta: +<N> -<N>
```

**Rules for composition:**
- One bullet per task. No prose paragraphs.
- "Done" = commit landed AND tests pass. If commit landed but tests broken → put it in "Blocked".
- "Tomorrow" must reference task IDs or say "no plan". Vague aspirations are banned.
- If an entry has no useful content, omit the section entirely (no "—" placeholders).

---

## STEP 4 — Persist

### Local
Write to `docs/reports/<DATE>.md` (append `-2`, `-3` if multiple reports per day).

### Outline
1. Search `Knowledge Base / Daily Status` collection for existing doc with title `<PROJECT> — <DATE>`.
2. If exists → `mcp__outline__update_document` with full new body.
3. If not → `mcp__outline__create_document` in Daily Status sub-page, title = `<PROJECT> — <DATE>`.
4. Capture returned doc URL.

---

## STEP 5 — Confirm

```
✅ Daily report — <PROJECT> — <DATE>
Local:   docs/reports/<DATE>.md
Outline: <url>
N commits, M tasks done, K blocked
```

---

## Designed for /loop

```bash
# Set up via /loop skill (one-time per machine):
/loop "0 18 * * *" /report

# This fires at 18:00 daily and runs /report autonomously.
# Empty days produce no output (STEP 2 short-circuit).
```

## Rules

- NEVER fabricate task titles or outcomes — read from TASK.md / TASK_ARCHIVE.md / commit messages
- If git history is too noisy (>50 commits in period) — refuse and ask user to narrow period
- PII in commit messages → DO NOT publish to Outline; ask user to redact first
- Daily Status entries are ephemeral — pruning policy in /docs sync (older than 90 days → archive)
