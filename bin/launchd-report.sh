#!/usr/bin/env bash
# launchd-report.sh — legacy wrapper for /report (kept for existing plist compatibility).
# New schedules use bin/launchd-runner.sh which is generic + multi-task.
#
# Loaded via: ~/Library/LaunchAgents/com.semishan.investments-report.plist
# Daily at 23:00 local time.
#
# Invokes Claude via ccs (Claude profile switcher) — same as launchd-runner.sh —
# so auth/profile match interactive sessions.

set -euo pipefail

if [ -f "$HOME/.zshrc" ]; then
  source "$HOME/.zshrc" 2>/dev/null || true
fi

CCS_PROFILE="${CCS_PROFILE:-personal}"

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
echo "[$(date)] Running daily /report for $(basename "$PROJECT_DIR")"
echo "[$(date)] Runner: ${RUNNER[*]}"
echo "===================================="

exec "${RUNNER[@]}" -p "/report"
