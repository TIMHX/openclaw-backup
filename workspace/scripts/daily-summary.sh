#!/bin/bash
# Daily Summary Script
# Simple daily summary - just key events and knowledge to record

TODAY=$(date +%Y-%m-%d)
MEMORY_DIR="$HOME/.openclaw/workspace-routine-runner/memory"
DAILY_NOTE="$MEMORY_DIR/${TODAY}.md"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

mkdir -p "$MEMORY_DIR"

echo "# Daily Summary - $TODAY" > "$DAILY_NOTE"
echo "" >> "$DAILY_NOTE"
echo "Generated: $TIMESTAMP" >> "$DAILY_NOTE"
echo "" >> "$DAILY_NOTE"

echo "## Key Events" >> "$DAILY_NOTE"
echo "- Summary of today's main interactions" >> "$DAILY_NOTE"
echo "- " >> "$DAILY_NOTE"
echo "" >> "$DAILY_NOTE"

echo "## Knowledge to Record" >> "$DAILY_NOTE"
echo "- [ ] Check if any topics need updating based on today's work" >> "$DAILY_NOTE"
echo "" >> "$DAILY_NOTE"

echo "Daily summary created: $DAILY_NOTE"
