#!/usr/bin/env bash
# Stop hook — BLOCKING context budget enforcement.
#
# Fires at every Claude stop attempt. When heuristic indicators (commits + lines
# changed since last [HANDOFF] commit) exceed thresholds AND docs/handoff.md is
# stale, exits 2 to force Claude to continue — with an instruction to write the
# handoff before actually stopping.
#
# This is the BLOCKING counterpart to the advisory context-budget warning in
# settings.json (the advisory one nudges at 2-4 commits; this one blocks at >6
# commits OR >500 lines changed without a fresh handoff).
#
# Exit 0 = allow stop (under threshold OR fresh handoff exists).
# Exit 2 = force continue with stderr message as instruction to Claude.
# Any error inside the hook → exit 0 (never block Claude due to hook bugs).

set -uo pipefail

# Never block on missing git — templates can be non-repo.
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -d "$GIT_ROOT/.git" ] || exit 0

HANDOFF_FILE="$GIT_ROOT/docs/handoff.md"

# Thresholds (tuned for ~50% context budget — adjust as the model's window evolves)
MAX_COMMITS=${CTX_BUDGET_MAX_COMMITS:-6}
MAX_LINES=${CTX_BUDGET_MAX_LINES:-500}

# --- Find the comparison base: last [HANDOFF] commit, else 4h window fallback ---
LAST_HANDOFF_HASH=$(git -C "$GIT_ROOT" log --grep='^\[HANDOFF\]' -1 --format='%H' 2>/dev/null || true)

COMMITS=0
LINES=0

# Sum insertions+deletions across a set of commits given by `git log` format filter.
# Per-commit --shortstat aggregation avoids the initial-commit parent lookup bug.
# LC_ALL=C forces C locale so "insertion"/"deletion" words match across systems
# (DA-002: Ukrainian/other locales emit translated strings that would silently
# zero out line counts).
_sum_lines_from_log() {
  LC_ALL=C git -C "$GIT_ROOT" log --shortstat --format='' "$@" 2>/dev/null \
    | awk '/insertion|deletion/ {
        for (i=1;i<=NF;i++) {
          if ($i ~ /^[0-9]+$/ && ($(i+1) ~ /insertion/ || $(i+1) ~ /deletion/)) s+=$i
        }
      } END { print s+0 }'
}

if [ -n "${LAST_HANDOFF_HASH:-}" ]; then
  COMMITS=$(git -C "$GIT_ROOT" log --oneline "${LAST_HANDOFF_HASH}..HEAD" 2>/dev/null | wc -l | tr -d ' ')
  LINES=$(_sum_lines_from_log "${LAST_HANDOFF_HASH}..HEAD")
  BASE_LABEL="last [HANDOFF] commit ${LAST_HANDOFF_HASH:0:7}"
else
  COMMITS=$(git -C "$GIT_ROOT" log --since='4 hours ago' --oneline 2>/dev/null | wc -l | tr -d ' ')
  LINES=$(_sum_lines_from_log --since='4 hours ago')
  BASE_LABEL='4h window (no [HANDOFF] commit found)'
fi

LINES=${LINES:-0}

# --- Handoff freshness check ---
# Fresh if ANY of:
#   (1) last commit subject starts with [HANDOFF] (user just committed handoff;
#       self-staleness race from committing handoff immunises here — DA-003)
#   (2) handoff.md exists AND contains the required section headers AND
#       mtime >= last non-HANDOFF work commit time (DA-005 content-check
#       closes the "touch empty file" escape hatch)
# On any parse error → unknown → default to NO (block-biased for known file
# presence, allow-biased for unknown-mtime — see DA-007 below).
HANDOFF_FRESH='no'

LAST_SUBJECT=$(git -C "$GIT_ROOT" log -1 --format='%s' 2>/dev/null || echo '')
if printf '%s' "$LAST_SUBJECT" | grep -q '^\[HANDOFF\]'; then
  HANDOFF_FRESH='yes'
elif [ -f "$HANDOFF_FILE" ]; then
  # Content check: handoff.md must mention at least 3 of the 5 required sections
  REQUIRED_HEADERS=(
    'Completed This Session'
    'In Progress'
    'Next Session Should'
    'Context That Would Be Lost'
    'Unanswered Question'
  )
  HEADER_HITS=0
  for h in "${REQUIRED_HEADERS[@]}"; do
    if grep -q -- "$h" "$HANDOFF_FILE" 2>/dev/null; then
      HEADER_HITS=$((HEADER_HITS + 1))
    fi
  done

  if [ "$HEADER_HITS" -ge 3 ]; then
    # Compare handoff mtime to last non-[HANDOFF] work commit time. If no
    # such commit exists (only [HANDOFF] commits in history), fresh by default.
    # DA-009: avoid `--invert-grep` (git >= 2.4) so hook degrades gracefully on
    # older git installs. Portable approach: list hash + subject, filter out
    # [HANDOFF] with plain grep, take first. LC_ALL=C protects the filter from
    # any locale-specific git log reformatting.
    LAST_WORK_HASH=$(LC_ALL=C git -C "$GIT_ROOT" log --format='%H %s' -n 100 2>/dev/null \
      | grep -v ' \[HANDOFF\]' \
      | head -1 \
      | awk '{print $1}' \
      || echo '')
    if [ -z "${LAST_WORK_HASH:-}" ]; then
      HANDOFF_FRESH='yes'
    else
      # Portable stat: BSD (-f %m) first, GNU (-c %Y) fallback.
      # DA-007: on exotic platforms where neither works, leave HANDOFF_MTIME
      # empty and bias toward allow-stop (set fresh=yes). Hook bugs must never
      # block — per the "never block Claude due to hook bugs" principle.
      HANDOFF_MTIME=$(stat -f %m "$HANDOFF_FILE" 2>/dev/null || stat -c %Y "$HANDOFF_FILE" 2>/dev/null || echo '')
      LAST_WORK_TIME=$(git -C "$GIT_ROOT" log -1 --format='%ct' "$LAST_WORK_HASH" 2>/dev/null || echo '')
      if [ -z "${HANDOFF_MTIME:-}" ] || [ -z "${LAST_WORK_TIME:-}" ]; then
        HANDOFF_FRESH='yes'   # unknown → allow (hook-bug safety)
      elif [ "$HANDOFF_MTIME" -ge "$LAST_WORK_TIME" ]; then
        HANDOFF_FRESH='yes'
      fi
    fi
  fi
fi

# --- Decision ---
OVER_COMMITS='no'
OVER_LINES='no'
[ "${COMMITS:-0}" -gt "$MAX_COMMITS" ] && OVER_COMMITS='yes'
[ "${LINES:-0}"   -gt "$MAX_LINES"   ] && OVER_LINES='yes'

# --- Circuit breaker (DA-004) ---
# If this hook has already blocked N times in the last WINDOW seconds, give up
# and allow stop — prevents infinite stop-continue loops if Claude's reaction
# doesn't satisfy the freshness check (e.g. reads files first, never writes
# handoff). State lives in a single tmp file with monotonic append of timestamps.
TRIP_FILE="${GIT_ROOT}/.claude/session-log/context-budget-trips.log"
TRIP_WINDOW=${CTX_BUDGET_TRIP_WINDOW:-300}   # 5 minutes
TRIP_MAX=${CTX_BUDGET_TRIP_MAX:-3}
mkdir -p "$(dirname "$TRIP_FILE")" 2>/dev/null || true
NOW=$(date +%s 2>/dev/null || echo 0)

# Count existing trip timestamps within window and prune stale ones.
RECENT_TRIPS=0
if [ -f "$TRIP_FILE" ] && [ "${NOW:-0}" -gt 0 ]; then
  PRUNED=$(awk -v cutoff=$((NOW - TRIP_WINDOW)) '$1 >= cutoff { print $1 }' "$TRIP_FILE" 2>/dev/null || echo '')
  printf '%s\n' "$PRUNED" | grep -v '^$' > "$TRIP_FILE.tmp" 2>/dev/null && mv "$TRIP_FILE.tmp" "$TRIP_FILE" 2>/dev/null || true
  RECENT_TRIPS=$(wc -l < "$TRIP_FILE" 2>/dev/null | tr -d ' ' || echo 0)
fi

if { [ "$OVER_COMMITS" = 'yes' ] || [ "$OVER_LINES" = 'yes' ]; } && [ "$HANDOFF_FRESH" = 'no' ] && [ "${RECENT_TRIPS:-0}" -ge "$TRIP_MAX" ]; then
  cat >&2 <<EOF
[CONTEXT BUDGET — CIRCUIT BREAKER TRIPPED] Hook would block for the $((RECENT_TRIPS + 1))th time in ${TRIP_WINDOW}s, giving up to avoid infinite loop.

Metrics: commits=$COMMITS lines=$LINES handoff_fresh=$HANDOFF_FRESH

You are allowed to stop, BUT the context budget is still over threshold. Before the next message please:
1. Write docs/handoff.md properly
2. Commit as [HANDOFF]
3. /compact

Reset circuit breaker: rm $TRIP_FILE
EOF
  exit 0
fi

if { [ "$OVER_COMMITS" = 'yes' ] || [ "$OVER_LINES" = 'yes' ]; } && [ "$HANDOFF_FRESH" = 'no' ]; then
  # Record this block attempt for circuit breaker
  [ "${NOW:-0}" -gt 0 ] && printf '%s\n' "$NOW" >> "$TRIP_FILE" 2>/dev/null || true
  # BLOCK — emit instruction and force Claude to continue with handoff-writing task
  cat >&2 <<EOF
[CONTEXT BUDGET — HARD BLOCK] Over threshold AND docs/handoff.md is stale/missing.

Metrics since $BASE_LABEL:
  Commits:       $COMMITS (limit $MAX_COMMITS, over=$OVER_COMMITS)
  Lines changed: $LINES (limit $MAX_LINES, over=$OVER_LINES)
  handoff fresh: $HANDOFF_FRESH

Do this NOW before you can stop:
1. Write docs/handoff.md — follow template in .claude/rules/workflow.md § Session End — Handoff Protocol. Required sections:
   - Completed This Session
   - In Progress (not finished)
   - Next Session Should (concrete first 3 actions)
   - Context That Would Be Lost
   - User's Last Unanswered Question (CRITICAL)
2. git add docs/handoff.md
3. git commit -m "[HANDOFF] <one-line summary>"
4. Run /compact
5. Only then is it safe to stop

Override for genuine false positives: set CTX_BUDGET_MAX_COMMITS or CTX_BUDGET_MAX_LINES env var higher, or temporarily disable this hook in .claude/settings.json.
EOF
  exit 2
fi

exit 0
