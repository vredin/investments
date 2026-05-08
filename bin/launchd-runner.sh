#!/usr/bin/env bash
# launchd-runner.sh — generic wrapper invoked by launchd for any scheduled Claude prompt.
#
# Usage (from launchd plist):
#   launchd-runner.sh "/report"
#   launchd-runner.sh "/docs sync --publish"
#   launchd-runner.sh "/self-audit"
#   launchd-runner.sh "/self-audit --global"
#
# Invokes Claude via ccs (Claude profile switcher) so that the same auth/profile
# the user uses interactively is reused. CCS_PROFILE env var overrides which
# profile to use (default: personal).

set -euo pipefail

PROMPT="${1:?prompt required as first argument}"

# Source shell profile to get PATH (nvm/ccs binary live there) + any env vars
if [ -f "$HOME/.zshrc" ]; then
  source "$HOME/.zshrc" 2>/dev/null || true
fi

CCS_PROFILE="${CCS_PROFILE:-personal}"

# Prefer ccs (matches interactive workflow with account isolation).
# Fall back to direct claude if ccs not on PATH.
if command -v ccs >/dev/null 2>&1; then
  CCS_BIN="$(command -v ccs)"
  RUNNER=("$CCS_BIN" "$CCS_PROFILE")
else
  CLAUDE_BIN="${CLAUDE_BIN:-/Users/semishan/.local/bin/claude}"
  if [ ! -x "$CLAUDE_BIN" ]; then
    echo "[$(date)] FAIL: neither ccs nor claude binary found" >&2
    echo "[$(date)] PATH was: $PATH" >&2
    exit 1
  fi
  RUNNER=("$CLAUDE_BIN")
fi

PROJECT_DIR="/Users/semishan/PycharmProjects/Investments"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "[$(date)] FAIL: project dir not found: $PROJECT_DIR" >&2
  exit 1
fi

cd "$PROJECT_DIR"

echo "===================================="
echo "[$(date)] Running '$PROMPT' for $(basename "$PROJECT_DIR")"
echo "[$(date)] Runner: ${RUNNER[*]}"
echo "===================================="

# --dangerously-skip-permissions: required for headless scheduled runs.
# Safe here because prompt is fixed (controlled by plist), not external input.
# Without it: tools (Edit/Write/Bash/MCP) get blocked → /report can't write
# docs/reports/, /self-audit can't save audit file, /docs sync can't publish.
exec "${RUNNER[@]}" -p "$PROMPT" --dangerously-skip-permissions
