#!/usr/bin/env bash
# launchd-runner.sh — generic wrapper invoked by launchd for any scheduled Claude prompt.
#
# Usage (from launchd plist):
#   launchd-runner.sh "/report"
#   launchd-runner.sh "/docs sync --publish"
#   launchd-runner.sh "/self-audit"
#   launchd-runner.sh "/self-audit --global"

set -euo pipefail

PROMPT="${1:?prompt required as first argument}"

if [ -f "$HOME/.zshrc" ]; then
  source "$HOME/.zshrc" 2>/dev/null || true
fi

CLAUDE_BIN="${CLAUDE_BIN:-/Users/semishan/.local/bin/claude}"
if [ ! -x "$CLAUDE_BIN" ]; then
  echo "[$(date)] FAIL: claude binary not found at $CLAUDE_BIN" >&2
  exit 1
fi

PROJECT_DIR="/Users/semishan/PycharmProjects/Investments"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "[$(date)] FAIL: project dir not found: $PROJECT_DIR" >&2
  exit 1
fi

cd "$PROJECT_DIR"

echo "===================================="
echo "[$(date)] Running '$PROMPT' for $(basename "$PROJECT_DIR")"
echo "===================================="

exec "$CLAUDE_BIN" -p "$PROMPT"
