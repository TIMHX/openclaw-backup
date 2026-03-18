#!/bin/bash
# cleanup-sessions.sh — Destroy tmux sessions older than 1 day

set -euo pipefail

SOCKET_DIR="${CLAWDBOT_TMUX_SOCKET_DIR:-/tmp/claude-code-sessions}"
SOCKET_PATH="${SOCKET_DIR}/claude-code.sock"
MAX_AGE_SECONDS=$((24 * 60 * 60))  # 1 day

mkdir -p "$SOCKET_DIR"

echo "=== Claude Code Session Cleanup ==="
echo "Max age: 1 day"
echo ""

if ! tmux -S "$SOCKET_PATH" ls >/dev/null 2>&1; then
    echo "No sessions to clean up"
    exit 0
fi

# Get current time
NOW=$(date +%s)
CLEANED=0

# List all sessions and check age
for session in $(tmux -S "$SOCKET_PATH" ls -F '#{session_name}' 2>/dev/null); do
    # Skip non-cc sessions
    [[ "$session" != cc-* ]] && continue
    
    CREATED=$(tmux -S "$SOCKET_PATH" list-sessions -F '#{session_created}' -t "$session" 2>/dev/null || continue)
    AGE=$((NOW - CREATED))
    
    if [ "$AGE" -gt "$MAX_AGE_SECONDS" ]; then
        echo "Destroying old session: $session (age: $((AGE / 3600))h)"
        tmux -S "$SOCKET_PATH" kill-session -t "$session" 2>/dev/null || true
        CLEANED=$((CLEANED + 1))
    else
        echo "Keeping: $session (age: $((AGE / 3600))h)"
    fi
done

echo ""
echo "Cleaned up: $CLEANED session(s)"
