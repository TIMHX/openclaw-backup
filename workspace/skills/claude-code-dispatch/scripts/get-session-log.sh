#!/bin/bash
# get-session-log.sh — Retrieve Claude Code session log from tmux

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOCKET_DIR="${CLAWDBOT_TMUX_SOCKET_DIR:-/tmp/claude-code-sessions}"
SESSION="${1:-}"
SOCKET_PATH="${SOCKET_DIR}/claude-code.sock"

mkdir -p "$SOCKET_DIR"

# List sessions if no argument
if [ -z "$SESSION" ]; then
    echo "Usage: $0 <session-name>"
    echo ""
    echo "Available sessions:"
    tmux -S "$SOCKET_PATH" ls 2>/dev/null || echo "  (no sessions found)"
    echo ""
    echo "Session names: cc-{task-name} or cc-adhoc-{timestamp}"
    exit 1
fi

TARGET="${SESSION}:0.0"

echo "=== Capturing session: $SESSION ==="
echo ""

# Capture full history
if tmux -S "$SOCKET_PATH" has-session -t "$SESSION" 2>/dev/null; then
    # Get session creation time
    CREATED=$(tmux -S "$SOCKET_PATH" list-sessions -F "#{session_created}" -t "$SESSION" 2>/dev/null || echo "unknown")
    echo "Session created: $(date -d "@$CREATED" 2>/dev/null || echo "$CREATED")"
    echo ""
    
    # Capture all panes
    tmux -S "$SOCKET_PATH" capture-pane -p -J -t "$TARGET" -S -10000 2>/dev/null || \
    tmux -S "$SOCKET_PATH" capture-pane -p -t "$TARGET" 2>/dev/null || \
    echo "(no output captured)"
else
    echo "Session '$SESSION' not found"
    exit 1
fi
