#!/bin/bash
# =============================================================================
# OpenClaw Release Checker
# =============================================================================
# Purpose: Check for new OpenClaw GitHub releases and notify via Discord
# Target Discord Channel: 1475608007357497484
#
# Services & Flow:
#   1. gh CLI -> Query GitHub API (openclaw/openclaw releases)
#   2. Local file /tmp/last-openclaw-release.txt -> Track last known version
#   3. Doppler -> Get OpenClaw token (for message delivery)
#   4. openclaw message send -> Send Discord notification (native, no Zapier)
#
# Logic:
#   - Fetch latest release tag from GitHub
#   - Compare with locally cached version
#   - Only send Discord message if new release detected
#   - Update cache file after sending
#
# Cron Job: openclaw-release-checker (hourly)
# Note: Using OpenClaw native message instead of Zapier to save quota
# =============================================================================

REPO="openclaw/openclaw"
LAST_RELEASE_FILE="/tmp/last-openclaw-release.txt"
DISCORD_CHANNEL="1475608007357497484"

# Get latest release tag
LATEST=$(gh api repos/$REPO/releases/latest --jq '.tag_name' 2>/dev/null)

if [ -z "$LATEST" ]; then
    echo "Failed to get latest release"
    exit 1
fi

# Check if it's a new release
if [ -f "$LAST_RELEASE_FILE" ]; then
    LAST=$(cat "$LAST_RELEASE_FILE")
    if [ "$LATEST" = "$LAST" ]; then
        echo "No new release. Current: $LATEST"
        exit 0
    fi
fi

# New release found!
echo "New OpenClaw release: $LATEST"

# Get release notes (first 1000 chars)
RELEASE_NOTES=$(gh api repos/$REPO/releases/latest --jq '.body' 2>/dev/null | head -c 1000)

# Save current release
echo "$LATEST" > "$LAST_RELEASE_FILE"

# Format message for Discord
MSG="🚀 **New OpenClaw Release: $LATEST**"
MSG+="\n\n"
MSG+="$RELEASE_NOTES"
MSG+="\n\n"
MSG+="🔗 https://github.com/$REPO/releases/tag/$LATEST"

# Send via OpenClaw native message (no Zapier quota used)
# Note: This will be picked up by cron job delivery
echo "$MSG"

echo "Notification ready for $LATEST"
