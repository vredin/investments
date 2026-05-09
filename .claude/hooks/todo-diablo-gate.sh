#!/bin/bash
# todo-diablo-gate.sh — PreToolUse hook
#
# Blocks Edit/Write of docs/TASK.md when adding a NEW T-NNN row whose spec
# does NOT have a valid step_5_diablo frontmatter verdict.
#
# Triggers: PreToolUse where matcher targets Edit | Write.
# Behavior:
#   - exit 0 → allow tool call
#   - exit 2 → block tool call, print reason to stderr (Claude reads it)
#
# Activation: register in .claude/settings.json hooks.PreToolUse:
#   {
#     "hooks": [{"type": "command", "command": "bash .claude/hooks/todo-diablo-gate.sh"}]
#   }
#
# Defensive: if any check is unclear, allow (exit 0). Hook errs on permissive.

set -uo pipefail

# Tool input from Claude Code — Edit uses NEW_STRING, Write uses CONTENT.
f="${CLAUDE_TOOL_INPUT_FILE_PATH:-}"

# Only fire on docs/TASK.md
[[ -z "$f" ]] && exit 0
case "$f" in
  *docs/TASK.md|docs/TASK.md) : ;;
  *) exit 0 ;;
esac

GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$GIT_ROOT" || exit 0

# Extract proposed new content (Edit's new_string OR Write's content)
new="${CLAUDE_TOOL_INPUT_NEW_STRING:-${CLAUDE_TOOL_INPUT_CONTENT:-}}"
[[ -z "$new" ]] && exit 0

# Find T-NNN ids in NEW content
new_ids=$(printf '%s\n' "$new" | grep -oE 'T-[0-9]{3,4}' | sort -u)
[[ -z "$new_ids" ]] && exit 0

# Find T-NNN ids ALREADY in current TASK.md (so we only check newly-added)
current_ids=""
[[ -f docs/TASK.md ]] && current_ids=$(grep -oE 'T-[0-9]{3,4}' docs/TASK.md 2>/dev/null | sort -u)

violations=()

while IFS= read -r tid; do
  [[ -z "$tid" ]] && continue
  # Skip if already in TASK.md (status change, not new add)
  if [[ -n "$current_ids" ]] && printf '%s\n' "$current_ids" | grep -qx "$tid"; then
    continue
  fi

  # New T-NNN — check spec frontmatter
  spec=$(ls docs/specs/${tid}-*.md 2>/dev/null | head -1)
  if [[ -z "$spec" ]]; then
    violations+=("$tid: spec file missing in docs/specs/. Run /todo or /quick-plan first.")
    continue
  fi

  # Extract step_5_diablo value from spec YAML frontmatter
  verdict=$(awk '
    /^---[[:space:]]*$/ { fm = !fm; next }
    fm && /^[[:space:]]*step_5_diablo:/ {
      sub(/^[^:]*:[[:space:]]*/, "")
      sub(/[[:space:]]*$/, "")
      gsub(/"/, "")
      print
      exit
    }
  ' "$spec")

  case "$verdict" in
    ACCEPTABLE|PROCEED_CAUTION|"PROCEED CAUTION")
      ;;
    BLOCKED|FIX_FIRST|"FIX FIRST")
      violations+=("$tid: Diablo verdict '$verdict' — fix spec before adding to backlog.")
      ;;
    "")
      violations+=("$tid: spec missing 'step_5_diablo' frontmatter. Run: /da spec $tid first.")
      ;;
    *)
      violations+=("$tid: unknown step_5_diablo value '$verdict'. Expected: ACCEPTABLE|PROCEED_CAUTION|FIX_FIRST|BLOCKED.")
      ;;
  esac
done <<< "$new_ids"

if [[ ${#violations[@]} -gt 0 ]]; then
  {
    echo "[BLOCKED by todo-diablo-gate.sh]"
    echo "Cannot add T-NNN to docs/TASK.md without a valid Diablo verdict in spec frontmatter."
    echo
    for v in "${violations[@]}"; do
      echo "  - $v"
    done
    echo
    echo "Fix: complete /todo workflow STEP 5 (run /da spec T-NNN), update spec frontmatter step_5_diablo, then retry."
    echo "Reference: workflow.md § Process Step Discipline + .claude/commands/todo.md STEP 5."
  } >&2
  exit 2
fi

exit 0
