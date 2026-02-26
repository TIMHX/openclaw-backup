# YouTube Tech Trend Scouter

从 YouTube 抓取技术视频并推送到 Notion 的自动化工具。

## 项目结构

```
youtube_scouter/
├── youtube_scouter.py          # 主程序 (每日运行)
├── update_channel_ids.py       # Channel ID 更新脚本 (每周运行)
├── youtube-scouter-config.yaml # 配置文件
├── .env                       # 环境变量 (API keys)
├── channel-updater.log        # Channel 更新日志
├── youtube-scouter.log        # 主程序日志
├── youtube-scouter-videos.json # 视频历史记录
└── .venv/                     # Python 虚拟环境
```

## Notion 数据库

| Database ID | 用途 |
|-------------|------|
| `channel_db_id` (2ff55a34-9949-8001-9654-e5e4461ee6a7) | 频道列表 - 存储要监控的 YouTube 频道 |
| `results_db_id` (2f855a34-9949-8020-83b5-cc37c2f54df5) | 视频推荐 - 输出视频推荐结果 |
| `log_db_id` (2ff55a34994980e0a7f1000c4196bff0) | 运行日志 - 存储每次运行的日志 |

### Channel 数据库字段

- **Name** (title): 频道名称
- **Channel ID** (rich_text): YouTube Channel ID
- **Homepage** (url): 频道首页 URL
- **Status** (select): 状态 (active/done 等)

## 功能逻辑

### 1. 数据源 (sources)

#### RSS 抓取
- 从 Notion Channel 数据库读取频道列表
- 通过 YouTube RSS feed (`https://www.youtube.com/feeds/videos.xml?channel_id=XXX`) 获取最新视频

#### YouTube API 搜索
- 根据配置的 topics 列表搜索技术视频
- 支持 fallback 到网页抓取 (当 API quota 不足时)

### 2. 视频筛选 (filtering)

- **max_age_days**: 只抓取 120 天内的视频
- **skip_patterns**: 过滤包含 "shorts", "#shorts" 等关键词的视频

### 3. 质量评分 (scoring)

| 评分项 | 加分/扣分 |
|--------|-----------|
| 高价值词 (tutorial, deep dive, course 等) | +2.0 |
| 中等价值词 (guide, tips, tricks 等) | +0.5 |
| 低价值词 (subscribe, vlog, news 等) | -5.0 |
| 长描述 (>300 字符) | +1.0 |
| RSS 来源 | +0.5 |
| 爬虫 fallback | -0.5 |

### 4. 自动更新 Channel ID

当频道缺少 Channel ID 时，系统会尝试：

1. **有 Homepage**: 使用 TranscriptAPI 解析 Channel ID
2. **无 Homepage**: 使用 YouTube 搜索/API 查找频道
3. 成功后自动更新 Notion 数据库

## 调度配置

| Job | 频率 | 命令 |
|-----|------|------|
| youtube-scouter-daily | 每天 9:00 AM (ET) | `python youtube_scouter.py` |
| youtube-scouter-channel-updater | 每周日 3:00 AM (ET) | `python update_channel_ids.py` |

**注意**: v2.0+ 版本的 `youtube_scouter.py` 已内置 Channel ID 自动更新逻辑，可禁用单独的 channel-updater job。

## 环境变量 (.env)

```bash
NOTION_API_KEY=ntn_xxx        # Notion API Token
YOUTUBE_API_KEY=AIzaSyxxx     # YouTube Data API Key
TRANSCRIPT_API_KEY=sk_xxx    # TranscriptAPI Key (用于解析 Channel ID)
GEMINI_API_KEY=AIzaSyxxx     # Gemini API (可选)
```

## 使用方法

### 测试模式
```bash
cd /home/xing/.openclaw/workspace/youtube_scouter
./.venv/bin/python3 youtube_scouter.py --test
```

### 完整运行
```bash
./.venv/bin/python3 youtube_scouter.py
```

### 手动更新 Channel ID
```bash
./.venv/bin/python3 update_channel_ids.py
```

## 依赖

- python-dotenv
- pyyaml
- notion-client (可选，用于 MCP)
- requests (通过 curl 调用 Notion API)

## 故障排除

### list index out of range

**原因**: Notion 数据库返回空数据或结构异常

**解决**: 代码已内置空数据检查和自动修复逻辑

### RSS 获取失败

- 检查频道的 Channel ID 是否有效
- 确认 YouTube RSS feed 可访问

### API Quota 不足

- 系统会自动 fallback 到网页抓取模式
- 降低 `search.max_results_per_topic` 配置值
