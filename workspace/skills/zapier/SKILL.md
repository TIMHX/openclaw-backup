---
name: zapier
description: Interact with Zapier MCP to create and manage automation workflows. Use when user wants to set up automated tasks between apps (e.g., send Discord messages, trigger Gmail actions, etc.)
metadata:
  {
    "openclaw": { "emoji": "⚡", "requires": { "anyBins": ["node"] } },
  }
---

# Zapier MCP Skill

Use Zapier MCP to create and manage automation workflows.

## Default Configuration

- **Default Discord Channel**: `1475592534720774296`
- **Zapier MCP Token**: Stored in Doppler as `ZAPIER_MCP_TOKEN`

## Setup

The Zapier MCP token is stored in Doppler. To get the connection URL:

```bash
# Get the token from Doppler
export ZAPIER_MCP_TOKEN=$(doppler secrets get ZAPIER_MCP_TOKEN --plain)

# Connection URL
https://mcp.zapier.com/api/v1/connect?token=${ZAPIER_MCP_TOKEN}
```

## Usage

### Via mcporter CLI (Recommended)

```bash
# Get token
export ZAPIER_MCP_TOKEN=$(doppler secrets get ZAPIER_MCP_TOKEN --plain)

# Send Discord message (use default channel)
mcporter call zapier discord_send_channel_message \
    instructions:"Send message to Discord" \
    channel_id:"1475592534720774296" \
    content:"Your message here" \
    output_hint:"confirm message was sent"

# Find Discord channel
mcporter call zapier discord_find_channel \
    instructions:"Find channel by name" \
    name:"general" \
    output_hint:"show channel id"
```

### Available Functions

**Discord:**
- `discord_send_channel_message` - Send message to channel (default: 1475592534720774296)
- `discord_send_direct_message` - Send DM to user
- `discord_find_channel` - Find channel by name
- `discord_find_user` - Find user by name

**GitHub:**
- `github_find_repository` - Find repo by owner/name
- `github_find_issue` - Search issues
- `github_create_issue` - Create new issue
- `github_create_pull_request` - Create PR

**Notion:**
- `notion_create_page` - Create new page
- `notion_find_page_by_title` - Find page
- `notion_add_block_to_page` - Add content

## Examples

### Send Discord Notification
```bash
export ZAPIER_MCP_TOKEN=$(doppler secrets get ZAPIER_MCP_TOKEN --plain)
mcporter call zapier discord_send_channel_message \
    instructions:"Send release notification" \
    channel_id:"1475592534720774296" \
    content:"🚀 New release available!" \
    output_hint:"confirm sent"
```

### Create GitHub Issue
```bash
mcporter call zapier github_create_issue \
    instructions:"Create a bug report issue" \
    repo:"openclaw/openclaw" \
    title:"Bug: Something is broken" \
    body:"Description of the bug" \
    output_hint:"show created issue number"
```

## Important Notes

- **Free Plan Limit**: ~100 tasks/month - use sparingly, prioritize critical notifications
- Default Discord channel is `1475592534720774296` - use this unless specified otherwise
- Zapier MCP requires authentication via the token from Doppler
- Some actions require premium Zapier plans
- Use natural language in `instructions` parameter for best results
