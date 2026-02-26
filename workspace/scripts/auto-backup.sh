#!/bin/bash
# Auto-commit and push OpenClaw config changes

cd ~/.openclaw || exit 1

# Check for changes
if git diff --quiet && git diff --staged --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Get current timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

# Stage all changes
git add -A

# Create commit message with changed files
CHANGED=$(git status --short | grep -E '^\s*M' | awk '{print $2}' | head -5 | tr '\n' ', ')
if [ -z "$CHANGED" ]; then
    CHANGED="configuration"
fi

# Commit and push
git commit -m "Auto-backup: $CHANGED - $TIMESTAMP"
git push origin master

echo "Backup complete: $TIMESTAMP"
