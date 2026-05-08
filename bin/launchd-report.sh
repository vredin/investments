#!/usr/bin/env bash
# launchd-report.sh — wrapper invoked by launchd for daily /report
#
# Loaded via: ~/Library/LaunchAgents/com.semishan.investments-report.plist
# Daily at 23:00 local time.
#
# What it does:
# 1. Sources user shell profile (PATH, env vars including OUTLINE_TOKEN if set)
# 2. cd into project directory
# 3. Invokes `claude -p "/report"` — single-turn non-interactive mode
# 4. /report reads project files, builds report, publishes to Outline
#    (needs MCP outline configured globally via `claude mcp add`)
# 5. stdout/stderr go to ~/Library/Logs/investments-report.log per plist

set -euo pipefail

# Source shell profile to get PATH, env vars
# launchd doesn't load these by default
if [ -f "$HOME/.zshrc" ]; then
  # Tolerate failures inside zshrc (e.g. nvm initialization in a non-tty)
  source "$HOME/.zshrc" 2>/dev/null || true
fi

# Resolve claude binary path explicitly (PATH from launchd is minimal)
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
echo "[$(date)] Running daily /report for $(basename "$PROJECT_DIR")"
echo "===================================="

# -p flag: print mode — runs single prompt, prints response, exits.
# /report command is project-defined in .claude/commands/report.md
exec "$CLAUDE_BIN" -p "/report"
