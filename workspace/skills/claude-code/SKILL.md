---
name: claude-code
description: "Use Claude Code (Anthropic) for coding tasks, image analysis, and general tasks. Triggers on: '用claude', 'claude code', 'run claude', 'let claude', 'claude帮我', 'claude.build', '看看这张图', '分析图片', 'describe image', 'claude看', etc."
metadata:
  {
    "openclaw": { "emoji": "🧠", "requires": { "anyBins": ["claude", "python3"] } },
  }
---

# Claude Code

使用 Claude Code (Anthropic) 执行开发任务、图片分析和一般任务。支持 Discord 通知回调。

## 快速调用

### 方式一: 直接调用 (无通知)
```bash
cd ~/.openclaw/workspace-routine-runner/skills/claude-code-dispatch
mkdir -p /tmp/myproject

CLAUDE_CODE_BIN=/home/xing/.local/bin/claude python3 scripts/claude_code_run.py \
  -p "任务描述" \
  --cwd /tmp/myproject \
  --permission-mode bypassPermissions
```

### 方式二: dispatch.sh (带 Discord 通知) ⭐推荐
```bash
cd ~/.openclaw/workspace-routine-runner/skills/claude-code-dispatch
mkdir -p /tmp/myproject

CLAUDE_CODE_BIN=/home/xing/.local/bin/claude bash scripts/dispatch.sh \
  -p "任务描述" \
  -n "任务名称" \
  -w /tmp/myproject \
  --permission-mode bypassPermissions \
  --group 1469849142556627059
```

## 参数说明

### claude_code_run.py
| 参数 | 说明 |
|------|------|
| `-p` | 任务描述 (必填) |
| `--cwd` | 工作目录 (必须已存在) |
| `--permission-mode` | 权限模式: `bypassPermissions` / `plan` / `acceptEdits` |
| `--allowedTools` | 工具白名单 (如 `"Bash,Read,Edit,Write"`) |
| `--output-format` | 输出格式: `text` / `json` / `stream-json` |
| `--agent-teams` | 启用 Agent Teams 模式 |
| `--teammate-mode` | Agent Teams 显示模式: `auto` / `in-process` / `tmux` |
| `--append-system-prompt` | 追加系统提示 |
| `--system-prompt` | 替换系统提示 |

### dispatch.sh
| 参数 | 简写 | 说明 |
|------|------|------|
| `--prompt` | `-p` | 任务描述 (必填) |
| `--name` | `-n` | 任务名称 |
| `--workdir` | `-w` | 工作目录 (必须已存在) |
| `--permission-mode` | | 权限模式 |
| `--group` | `-g` | Discord Channel ID (通知目标) |

## 使用场景

### 1. 代码开发 (带 Discord 通知)
```bash
cd ~/.openclaw/workspace-routine-runner/skills/claude-code-dispatch
mkdir -p ~/Projects/myproject

CLAUDE_CODE_BIN=/home/xing/.local/bin/claude bash scripts/dispatch.sh \
  -p "Build a Python CLI tool for managing TODO items with SQLite storage" \
  -n "todo-cli" \
  -w ~/Projects/myproject \
  --permission-mode bypassPermissions \
  --group 1469849142556627059
```

### 2. 图片/文件分析
```bash
# 直接使用 OpenClaw 工作目录中的文件，无需复制
# 文件位于 ~/.openclaw/workspace-routine-runner/

CLAUDE_CODE_BIN=/home/xing/.local/bin/claude python3 scripts/claude_code_run.py \
  -p "Describe the image ~/.openclaw/workspace-routine-runner/path/to/image.jpg in detail. What's happening?" \
  --cwd ~/.openclaw \
  --permission-mode bypassPermissions
```

### 3. Agent Teams (并行开发 + 测试)
```bash
CLAUDE_CODE_BIN=/home/xing/.local/bin/claude bash scripts/dispatch.sh \
  -p "Build a weather CLI with API integration, caching, and colored output" \
  -n "weather-cli" \
  --agent-teams \
  --teammate-mode auto \
  -w ~/Projects \
  --permission-mode bypassPermissions \
  --group 1469849142556627059
```

### 4. 只读分析 (Plan Mode)
```bash
CLAUDE_CODE_BIN=/home/xing/.local/bin/claude python3 scripts/claude_code_run.py \
  -p "Analyze this codebase and propose a refactoring plan" \
  --cwd ~/Projects/myproject \
  --permission-mode plan
```

### 5. 限制工具权限
```bash
CLAUDE_CODE_BIN=/home/xing/.local/bin/claude python3 scripts/claude_code_run.py \
  -p "Run tests and fix failures" \
  --cwd ~/Projects/myproject \
  --allowedTools "Bash,Read" \
  --permission-mode acceptEdits
```

## Discord 通知

当使用 `--group` 参数时，任务完成后会自动发送 Discord 消息，包含:
- 任务状态 (✅/❌)
- 任务名称
- 工作目录
- 执行时长
- 创建的文件列表

**前提条件**:
1. `~/.claude/settings.json` 配置了 hook 路径
2. OpenClaw Gateway 正在运行

### Hook 配置
```bash
# 检查是否已配置
cat ~/.claude/settings.json

# 如果未配置，创建:
cat > ~/.claude/settings.json << 'EOF'
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/home/xing/.openclaw/workspace-routine-runner/skills/claude-code-dispatch/scripts/notify-hook.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/home/xing/.openclaw/workspace-routine-runner/skills/claude-code-dispatch/scripts/notify-hook.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
EOF
```

### Gateway 状态检查
```bash
openclaw gateway status
# 确保 Runtime: running
# 如未运行: openclaw gateway start
```

## 交互模式 (tmux)

如果提示包含斜杠命令 (如 `/speckit.*`)，需要使用交互模式:

```bash
CLAUDE_CODE_BIN=/home/xing/.local/bin/claude python3 scripts/claude_code_run.py \
  --mode interactive \
  --permission-mode acceptEdits \
  --allowedTools "Bash,Read,Edit,Write" \
  -p "/speckit.constitution\n/speckit.specify\n/speckit.plan"
```

## 高效使用技巧

1. **给出验证方式**: 让 Claude 可以验证结果
   - "修复 bug **并运行测试**，当 `npm test` 通过时完成"
   - "实现 UI 改动，**截图**对比参考图"

2. **使用 Plan Mode**: 先只读分析，再执行
   ```bash
   --permission-mode plan  # 只读分析
   --permission-mode acceptEdits  # 确认后执行
   ```

3. **CLAUDE.md**: 为项目设置持久规则
   - 构建/测试命令
   - 代码风格规范
   - 环境注意事项

4. **权限原则**: deny > ask > allow
   - 在 settings.json 中用 deny 规则阻止访问敏感文件

5. **使用子代理**: 大范围代码研究时使用子代理，避免污染主上下文

## 结果文件

位于 `skills/claude-code-dispatch/data/claude-code-results/`:
- `task-meta.json` - 任务元数据
- `task-output.txt` - Claude Code 原始输出
- `latest.json` - 完整结果
- `hook.log` - Hook 执行日志

## 注意事项

- `--cwd` 目录必须**预先创建**
- 设置 `CLAUDE_CODE_BIN=/home/xing/.local/bin/claude`
- **文件路径**: prompt 中使用 **完整绝对路径** 或 `~/.openclaw/workspace-routine-runner/` 开头的路径
- 图片/文件分析时，直接使用工作目录中的文件，无需复制
- Gateway 需保持运行才能发送 Discord 通知
- 交互模式 (tmux) 用于斜杠命令场景

## 自动触发关键词

当用户提及以下内容时自动调用此 skill：

- "用claude" / "claude code" / "run claude" / "let claude"
- "claude帮我" / "claude.build" / "让claude" / "叫claude"
- "claude写" / "claude创建"