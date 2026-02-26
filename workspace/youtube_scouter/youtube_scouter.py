#!/usr/bin/env python3
"""
YouTube Tech Trend Scouter - Hybrid Version with Fallbacks + Logging

Features:
- RSS fetching from Notion channel database
- YouTube API search with fallback to scraping
- Auto-update missing Channel IDs from Notion
"""

import os, sys, json, traceback, subprocess, time, re
from datetime import datetime, timedelta
from typing import Dict, List

# ====== CONFIG ======
CONFIG_PATH = "youtube-scouter-config.yaml"
LOG_FILE = "youtube-scouter.log"

def load_config():
    import yaml
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

config = load_config()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY")
TRANSCRIPT_API_KEY = os.getenv("TRANSCRIPT_API_KEY")

# Database IDs
CHANNEL_DB_ID = config['notion']['channel_db_id']
RESULTS_DB_ID = config['notion']['results_db_id']
LOG_DB_ID = config['notion']['log_db_id']

SOURCES = config['sources']
RSS_CONFIG = SOURCES['rss']
SEARCH_CONFIG = SOURCES['search']
FALLBACK_CONFIG = config.get('fallback', {})
FILTERING = config['filtering']
QUALITY_TERMS = config['quality_terms']
SCORING = config['scoring']
NOTION_CONFIG = config['notion']
OUTPUT_CONFIG = config['output']
VIDEOS_PATH = OUTPUT_CONFIG['videos_path']

# ====== LOGGING (simple, no recursion) ======
log_lines = []

def log(msg: str, level: str = "INFO"):
    """Add log line - stores in memory and prints"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    log_lines.append(line)
    print(line)  # Direct print, no override

def save_log_to_file():
    """Save logs to file"""
    try:
        with open(LOG_FILE, 'a') as f:
            f.write('\n'.join(log_lines) + '\n')
    except Exception as e:
        print(f"[ERROR] Failed to save log file: {e}")

def push_log_to_notion(success: bool, error_msg: str = None):
    """Push complete log to Notion
    
    Notion database schema:
    - Run Date: title (required for new pages)
    - Run Result: status (Success/Failed)
    """
    if not NOTION_API_KEY:
        print("[WARNING] No NOTION_API_KEY - skipping Notion log push")
        return False
        
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    run_result = "Success" if success else "Failed"
    status_emoji = "✅" if success else "❌"
    
    log_content = '\n'.join(log_lines)
    if len(log_content) > 18000:
        log_content = log_content[:18000] + "\n\n... [LOG TRUNCATED] ..."
    
    payload = {
        "parent": {"database_id": LOG_DB_ID},
        "properties": {
            "Run Date": {"title": [{"text": {"content": run_date}}]},
            "Run Result": {"status": {"name": run_result}}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"{status_emoji} YouTube Scouter Run - {run_result}\n\n{log_content}"}
                    }]
                }
            }
        ]
    }
    
    if error_msg:
        payload["children"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"\n❌ ERROR DETAILS:\n{error_msg}"}
                }]
            }
        })
    
    cmd = [
        "curl", "-s", "-X", "POST", "https://api.notion.com/v1/pages",
        "-H", f"Authorization: Bearer {NOTION_API_KEY}",
        "-H", "Notion-Version: 2022-06-28",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        response = json.loads(result.stdout) if result.stdout else {}
        if result.returncode == 0:
            log(f"Log pushed to Notion: {run_result}", "SUCCESS")
            return True
        else:
            error_detail = response.get('message', result.stderr[:200])
            log(f"Failed to push log to Notion: {error_detail}", "ERROR")
            return False
    except Exception as e:
        log(f"Exception pushing log to Notion: {e}", "ERROR")
        return False

# ====== FAILURE TRACKER ======
class FailureTracker:
    def __init__(self):
        self.rss_failures = self.search_failures = self.scrape_fallbacks = 0
    def record_rss_failure(self): self.rss_failures += 1
    def record_search_failure(self): self.search_failures += 1
    def record_scrape_fallback(self): self.scrape_fallbacks += 1
    def get_rss_penalty(self): return min(self.rss_failures * 0.1, 1.0)
    def get_search_penalty(self): return min(self.search_failures * 0.1, 1.0)
    def get_scrape_penalty(self): return SCORING.get('scrape_penalty', -0.5) + min(self.scrape_fallbacks * 0.1, 0.5)

failure_tracker = FailureTracker()

# ====== HELPER FUNCTIONS ======
def load_video_history():
    if os.path.exists(VIDEOS_PATH):
        try:
            with open(VIDEOS_PATH, 'r') as f:
                return json.load(f)
        except: pass
    return {"recommended_videos": []}

def save_video_history(history):
    with open(VIDEOS_PATH, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def curl_notion(url: str, data: dict = None):
    cmd = ["curl", "-s", "-X", "POST", url,
           "-H", f"Authorization: Bearer {NOTION_API_KEY}",
           "-H", "Notion-Version: 2022-06-28", "-H", "Content-Type: application/json"]
    if data: cmd.extend(["-d", json.dumps(data)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0: return {"error": f"curl failed: {result.stderr}"}
    try: return json.loads(result.stdout)
    except: return {"error": "Failed to parse JSON"}

def fetch_channels_from_notion():
    """Fetch channels from Tech Youtuber database - with auto-update for missing Channel IDs"""
    if not NOTION_API_KEY:
        log("No NOTION_API_KEY configured", "WARNING")
        return {}
    log(f"Fetching channels from Notion database...")
    data = curl_notion(f"https://api.notion.com/v1/databases/{CHANNEL_DB_ID}/query", {})

    # Handle empty or error responses
    if data.get("object") == "error":
        log(f"Notion API error: {data.get('code', 'unknown')}", "ERROR")
        return {}
    if not data.get("results"):
        log(f"Notion returned empty results - database may be empty or query failed", "WARNING")
        return {}

    channels = {}
    channels_needing_update = []  # Track channels missing Channel ID

    for page in data.get("results", []):
        props = page.get("properties", {})
        page_id = page.get("id")

        # Get Channel ID (required)
        channel_id = ""
        id_list = props.get("Channel ID", {}).get("rich_text", [])
        if id_list:
            channel_id = id_list[0].get("text", {}).get("content", "")

        # Get Name
        name_data = props.get("Name", {})
        channel_name = ""
        if name_data and name_data.get("title"):
            channel_name = name_data["title"][0].get("text", {}).get("content", "")

        # Get Homepage for fallback resolution
        homepage = props.get("Homepage", {}).get("url", "") or ""

        # Get Status
        status = props.get("Status", {}).get("select", {}).get("name", "")
        if status and status.lower() not in ["active", "done", ""]:
            log(f"  ⏭️ {channel_name or page_id[:8]}: skipped (status: {status})")
            continue

        # If Channel ID is missing but we have name/homepage, track for update
        if not channel_id:
            if homepage or channel_name:
                channels_needing_update.append({
                    "page_id": page_id,
                    "name": channel_name,
                    "homepage": homepage
                })
            else:
                log(f"  ⚠️ Skipping page {page_id[:8]} - no name, homepage, or channel_id", "WARNING")
            continue

        channels[channel_name or f"Unknown-{channel_id[:8]}"] = channel_id

    log(f"Found {len(channels)} active channels", "SUCCESS")

    # Auto-update missing Channel IDs if TRANSCRIPT_API_KEY is available
    if channels_needing_update:
        log(f"Found {len(channels_needing_update)} channels needing Channel ID update")
        update_missing_channel_ids(channels_needing_update, channels)

    return channels


def resolve_channel_id_via_transcriptapi(homepage: str) -> str:
    """Resolve YouTube channel ID using TranscriptAPI"""
    if not TRANSCRIPT_API_KEY:
        return ""

    import urllib.parse
    encoded = urllib.parse.quote(homepage)
    url = f"https://transcriptapi.com/api/v2/youtube/channel/resolve?input={encoded}"

    cmd = ["curl", "-s", "-X", "GET", url, "-H", f"Authorization: Bearer {TRANSCRIPT_API_KEY}"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return data.get("channel_id", "") if "channel_id" in data else ""
    except:
        return ""


def scrape_youtube_search(channel_name: str) -> str:
    """Search YouTube and find channel URL"""
    import urllib.parse
    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(channel_name)}"

    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", "Mozilla/5.0", "-m", "15", search_url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return ""

        content = result.stdout

        # Method 1: Find channel IDs in JSON data
        channel_data = re.findall(r'"channelId":"(UC[^"]+)","[^"]+":"([^"]+)"', content)

        # Try to match by channel name
        for cid, cname in channel_data[:15]:
            if channel_name.lower() in cname.lower():
                log(f"    → Matched: {cname}", "SUCCESS")
                return f"https://www.youtube.com/channel/{cid}"

        # Method 2: If no exact match, use first channel
        channel_ids = re.findall(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', content)
        if channel_ids:
            log(f"    → Using first channel result", "INFO")
            return f"https://www.youtube.com/channel/{channel_ids[0]}"

        # Method 3: Look for /@handle URLs
        handles = re.findall(r'youtube\.com/@([a-zA-Z0-9_.-]+)', content)
        if handles:
            log(f"    → Found @handle: {handles[0]}", "INFO")
            return f"https://www.youtube.com/@{handles[0]}"

    except Exception as e:
        log(f"    ⚠️ Scrape error: {e}", "WARNING")

    return ""


def search_youtube_api_for_channel(channel_name: str) -> str:
    """Search YouTube API for channel (fallback)"""
    if not YOUTUBE_API_KEY:
        return ""

    import urllib.parse
    query = urllib.parse.quote(f"{channel_name} channel")
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=channel&maxResults=3&key={YOUTUBE_API_KEY}"

    try:
        result = subprocess.run(["curl", "-s", "-m", "10", url], capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)

        if "error" in data:
            log(f"    ⚠️ YouTube API quota exceeded", "WARNING")
            return ""

        for item in data.get("items", []):
            title = item.get("snippet", {}).get("title", "")
            if channel_name.lower() in title.lower():
                cid = item.get("id", {}).get("channelId", "")
                log(f"    → Found via API: {title}", "SUCCESS")
                return f"https://www.youtube.com/channel/{cid}"
    except:
        pass
    return ""


def update_notion_page(page_id: str, updates: dict) -> bool:
    """Update Notion page with Homepage and/or Channel ID"""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": {}}

    if "homepage" in updates:
        payload["properties"]["Homepage"] = {"url": updates["homepage"]}
    if "channel_id" in updates:
        payload["properties"]["Channel ID"] = {"rich_text": [{"text": {"content": updates["channel_id"]}}]}

    cmd = ["curl", "-s", "-X", "PATCH", url,
           "-H", f"Authorization: Bearer {NOTION_API_KEY}",
           "-H", "Notion-Version: 2022-06-28",
           "-H", "Content-Type: application/json",
           "-d", json.dumps(payload)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def update_missing_channel_ids(channels_needing_update: List[Dict], existing_channels: Dict):
    """Update missing Channel IDs in Notion - called before fetching RSS"""
    if not TRANSCRIPT_API_KEY:
        log("⚠️ TRANSCRIPT_API_KEY not set - cannot auto-update Channel IDs", "WARNING")
        return

    updated_count = 0
    failed_count = 0

    for item in channels_needing_update:
        name = item["name"] or "Unnamed"
        homepage = item["homepage"]
        page_id = item["page_id"]

        log(f"  🔍 Resolving Channel ID for: {name}")

        channel_id = ""

        # Strategy 1: Use TranscriptAPI with Homepage
        if homepage:
            log(f"    → Using Homepage: {homepage}")
            channel_id = resolve_channel_id_via_transcriptapi(homepage)

        # Strategy 2: Search YouTube if no Homepage or resolution failed
        if not channel_id and name:
            log(f"    → Searching YouTube for: {name}")
            channel_url = search_youtube_api_for_channel(name)
            if not channel_url:
                channel_url = scrape_youtube_search(name)

            if channel_url:
                channel_id = resolve_channel_id_via_transcriptapi(channel_url)
                if channel_id:
                    # Also update Homepage if we found one
                    if update_notion_page(page_id, {"homepage": channel_url, "channel_id": channel_id}):
                        log(f"    ✅ Updated Homepage AND Channel ID: {channel_id}", "SUCCESS")
                        updated_count += 1
                        # Add to existing channels for this run
                        existing_channels[name] = channel_id
                        continue
                    else:
                        failed_count += 1
                else:
                    # Update Homepage at least
                    if update_notion_page(page_id, {"homepage": channel_url}):
                        log(f"    ⚠️ Updated Homepage only (Channel ID resolution failed)", "WARNING")
                    else:
                        failed_count += 1
            else:
                failed_count += 1
                log(f"    ❌ Could not find channel on YouTube", "ERROR")
                continue

        # Strategy 3: Direct resolution if we have homepage but no channel_id yet
        if not channel_id and homepage:
            # Already tried above, mark as failed
            failed_count += 1
            continue

        if channel_id:
            if update_notion_page(page_id, {"channel_id": channel_id}):
                log(f"    ✅ Updated Channel ID: {channel_id}", "SUCCESS")
                updated_count += 1
                # Add to existing channels for this run
                existing_channels[name] = channel_id
            else:
                log(f"    ❌ Failed to update Notion", "ERROR")
                failed_count += 1
        else:
            failed_count += 1

        time.sleep(0.5)  # Rate limiting

    log(f"  📊 Channel ID Update: {updated_count} updated, {failed_count} failed")

def fetch_channel_rss_with_retry(channel_id: str, channel_name: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            videos = fetch_channel_rss(channel_id, channel_name)
            if videos or attempt == max_retries - 1:
                return videos
            time.sleep(1 * (attempt + 1))
        except Exception as e:
            if attempt == max_retries - 1:
                log(f"RSS {channel_name}: {e}", "ERROR")
                failure_tracker.record_rss_failure()
                return []
            time.sleep(1 * (attempt + 1))
    return []

def fetch_channel_rss(channel_id: str, channel_name: str):
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        result = subprocess.run(["curl", "-s", "-L", "-m", "10", rss_url], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            failure_tracker.record_rss_failure()
            return []
        content = result.stdout
        if "Channel not found" in content or "No longer available" in content:
            failure_tracker.record_rss_failure()
            return []
        videos = []
        entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
        if not entries:
            video_ids = re.findall(r'<yt:videoId>([^<]+)</yt:videoId>', content)
            for vid in video_ids[:OUTPUT_CONFIG['max_videos_per_channel']]:
                videos.append({"video_id": vid, "title": "RSS Video", "url": f"https://www.youtube.com/watch?v={vid}",
                    "description": "", "published_at": "", "channel": channel_name, "source": "rss", "quality_score": 0.0})
            return videos
        for entry in entries[:OUTPUT_CONFIG['max_videos_per_channel']]:
            video_id_match = re.search(r'<yt:videoId>([^<]+)</yt:videoId>', entry)
            if not video_id_match: continue
            video_id = video_id_match.group(1)
            title = re.search(r'<title>([^<]+)</title>', entry).group(1) if re.search(r'<title>([^<]+)</title>', entry) else "No title"
            desc_match = re.search(r'<media:description>([^<]+)</media:description>', entry, re.DOTALL)
            description = desc_match.group(1)[:500] if desc_match else ""
            pub_match = re.search(r'<published>([^<]+)</published>', entry)
            published_at = pub_match.group(1) if pub_match else ""
            if published_at:
                try:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    if (datetime.now(pub_date.tzinfo) - pub_date).days > FILTERING['max_age_days']:
                        continue
                except: pass
            skip = any(pattern.lower() in title.lower() for pattern in FILTERING['skip_patterns'])
            if skip: continue
            videos.append({"video_id": video_id, "title": title[:200], "url": f"https://www.youtube.com/watch?v={video_id}",
                "description": description, "published_at": published_at, "channel": channel_name, "source": "rss",
                "quality_score": calculate_quality_score(title, description, channel_name)})
        return videos
    except Exception as e:
        failure_tracker.record_rss_failure()
        return []

def search_youtube_api(query: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            videos = _do_api_search(query)
            if videos or attempt == max_retries - 1:
                return videos, False
            time.sleep(1 * (attempt + 1))
        except Exception as e:
            if attempt == max_retries - 1:
                log(f"API Search {query[:30]}: {e}", "ERROR")
                if FALLBACK_CONFIG.get('scrape_fallback', True):
                    videos = search_youtube_scrape(query)
                    return videos, True
                failure_tracker.record_search_failure()
                return [], False
            time.sleep(1 * (attempt + 1))
    return [], False

def _do_api_search(query: str):
    import urllib.parse
    days_back = SEARCH_CONFIG['published_after_days']
    published_after = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    max_results = min(SEARCH_CONFIG['max_results_per_topic'], 50)
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&order=relevance&publishedAfter={published_after}&maxResults={max_results}&key={YOUTUBE_API_KEY}"
    result = subprocess.run(["curl", "-s", "-m", "10", url], capture_output=True, text=True, timeout=15)
    if result.returncode != 0: raise Exception("curl failed")
    data = json.loads(result.stdout)
    if 'error' in data:
        error_msg = data['error'].get('message', 'Unknown error')
        if 'quota' in error_msg.lower():
            failure_tracker.record_search_failure()
            raise Exception(f"Quota exceeded: {error_msg}")
        raise Exception(error_msg)
    videos = []
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        video_id = item.get('id', {}).get('videoId', '')
        if not video_id: continue
        title = snippet.get('title', 'No title')
        description = snippet.get('description', '')[:500]
        channel = snippet.get('channelTitle', 'Unknown')
        skip = any(pattern.lower() in title.lower() for pattern in FILTERING['skip_patterns'])
        if skip: continue
        videos.append({"video_id": video_id, "title": title[:200], "url": f"https://www.youtube.com/watch?v={video_id}",
            "description": description, "published_at": snippet.get('publishedAt', ''), "channel": channel, "source": "search", "query": query,
            "quality_score": calculate_quality_score(title, description, channel)})
    return videos

def search_youtube_scrape(query: str):
    failure_tracker.record_scrape_fallback()
    import urllib.parse
    videos = []
    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}&sp=CAI%253D"
    try:
        result = subprocess.run(["curl", "-s", "-L", "-A", "Mozilla/5.0", "-m", "10", search_url], capture_output=True, text=True, timeout=15)
        if result.returncode != 0: return []
        content = result.stdout
        video_ids = re.findall(r'"videoId":"([^"]+)"', content)[:20]
        titles = re.findall(r'"title":{"runs":\[{"text":"([^"]+)"', content)
        channel_names = re.findall(r'"longBylineText":{"runs":\[{"text":"([^"]+)"', content)
        seen = set()
        for i, video_id in enumerate(video_ids):
            if video_id in seen: continue
            seen.add(video_id)
            title = titles[i] if i < len(titles) else "No title"
            skip = any(pattern.lower() in title.lower() for pattern in FILTERING['skip_patterns'])
            if skip: continue
            channel = channel_names[i] if i < len(channel_names) else "Unknown"
            videos.append({"video_id": video_id, "title": title[:200], "url": f"https://www.youtube.com/watch?v={video_id}",
                "description": "", "published_at": "", "channel": channel, "source": "scrape", "query": query,
                "quality_score": calculate_quality_score(title, "", channel)})
    except Exception as e:
        log(f"Scrape {query[:30]}: {e}", "ERROR")
    return videos

def search_youtube(query: str):
    videos, _ = search_youtube_api(query)
    return videos

def calculate_quality_score(title: str, description: str, channel: str):
    score = 0.0
    title_lower = title.lower()
    for term in QUALITY_TERMS['high_value_terms']:
        if term in title_lower: score += SCORING['high_value_bonus']
    for term in QUALITY_TERMS['medium_terms']:
        if term in title_lower: score += SCORING['medium_bonus']
    if len(description) > SCORING['long_description_threshold']:
        score += SCORING['long_description_bonus']
    elif len(description) > SCORING['medium_description_threshold']:
        score += SCORING['medium_description_bonus']
    for term in QUALITY_TERMS['low_effort_terms']:
        if term in title_lower: score -= SCORING['low_effort_penalty']
    for term in QUALITY_TERMS['duration_terms']:
        if term in title_lower: score += SCORING['duration_bonus']
    score += SCORING.get('rss_bonus', 0.0) + SCORING.get('search_penalty', 0.0) + SCORING.get('scrape_penalty', -0.5)
    score += failure_tracker.get_rss_penalty() + failure_tracker.get_search_penalty() + failure_tracker.get_scrape_penalty()
    if FALLBACK_CONFIG.get('global_fallback', True):
        score += SCORING.get('fallback_penalty', -0.2)
    return score

def deduplicate_videos(videos: List[Dict], history: dict):
    existing_ids = {v.get("video_id") for v in history.get("recommended_videos", [])}
    unique = []
    for video in videos:
        if video["video_id"] not in existing_ids and video["video_id"] not in [v["video_id"] for v in unique]:
            unique.append(video)
    return unique

def rank_videos(videos: List[Dict]):
    return sorted(videos, key=lambda x: x.get("quality_score", 0), reverse=True)

def create_notion_page(video: Dict):
    """Create page in 知识中心 database"""
    properties = {
        "Goal name": {"title": [{"text": {"content": video["title"][:190]}}]},
        "Category": {"select": {"name": NOTION_CONFIG['category']}}
    }
    description = video.get("description", "").strip()
    channel = video.get("channel", "")
    query = video.get("query", "")
    source = video.get("source", "")
    if description:
        sentences = re.split(r'[.!?]', description)
        summary = ""
        for i, s in enumerate(sentences[:2]):
            s = s.strip()
            if len(s) > 20:
                summary += s + ". "
                if i == 0 and len(sentences) > 1: break
        if not summary.endswith("."): summary = summary.strip() + "."
    else:
        summary = f"This video covers {channel}'s technical content."
    source_info = f" [Query: {query}]" if query else f" [{source}]"
    content_blocks = [
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"text": {"content": f"📝 {summary} (Source: {channel}){source_info}"}}]
        }},
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "🔗 Watch Video", "link": {"url": video["url"]}}}]
        }}
    ]
    payload = {"parent": {"database_id": RESULTS_DB_ID}, "properties": properties, "children": content_blocks}
    cmd = ["curl", "-s", "-X", "POST", "https://api.notion.com/v1/pages",
           "-H", f"Authorization: Bearer {NOTION_API_KEY}",
           "-H", "Notion-Version: 2025-09-03",
           "-H", "Content-Type: application/json", "-d", json.dumps(payload)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"    ✓ {video['title'][:50]}... (score: {video.get('quality_score', 0):.1f})")
            return True
        log(f"    ✗ Failed to create Notion page", "ERROR")
        return False
    except Exception as e:
        log(f"    ✗ Error: {e}", "ERROR")
        return False

# ====== MAIN FUNCTION ======
def main(test_mode: bool = False):
    global failure_tracker
    success = False
    error_msg = None
    
    try:
        log(f"==========================================================")
        log(f"YouTube Tech Trend Scouter - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        log(f"==========================================================")
        
        all_videos = []
        rss_success = False
        search_success = False
        
        # Fetch channels from Notion
        if RSS_CONFIG['enabled']:
            log("📡 Fetching channels from Notion...")
            channels = fetch_channels_from_notion()
            if not channels:
                log("⚠️ No channels found in Notion! Using search only.", "WARNING")
            else:
                log(f"📡 Fetching from {len(channels)} channels...")
                rss_videos = []
                for channel_name, channel_id in channels.items():
                    videos = fetch_channel_rss_with_retry(channel_id, channel_name)
                    
                    # If name was a placeholder (Unknown-xxx), try to get actual name from RSS
                    display_name = channel_name
                    if videos:
                        # If name was a placeholder, update from RSS
                        if channel_name.startswith("Unknown-"):
                            actual_name = videos[0].get("channel", channel_name)
                            if actual_name != channel_name:
                                log(f"  📝 Updated name: {channel_name} → {actual_name}")
                                display_name = actual_name
                            # Update videos to use actual name
                            for v in videos:
                                v["channel"] = actual_name
                        rss_videos.extend(videos)
                        log(f"  ✓ {display_name}: {len(videos)} videos")
                    else:
                        log(f"  ✗ {display_name}: failed")
                    time.sleep(0.2)
                if rss_videos:
                    all_videos.extend(rss_videos)
                    rss_success = True
                    log(f"  → RSS: {len(rss_videos)} videos from {len(rss_videos)//OUTPUT_CONFIG['max_videos_per_channel']} channels")
        
        # Search by topics
        if SEARCH_CONFIG['enabled']:
            log(f"\n🔍 Search: {len(SEARCH_CONFIG['topics'])} topics")
            search_videos = []
            for query in SEARCH_CONFIG['topics']:
                videos = search_youtube(query)
                if videos:
                    search_videos.extend(videos)
                    log(f"  ✓ {query[:35]}... → {len(videos)}")
                else:
                    log(f"  ✗ {query[:35]}... → 0")
                time.sleep(0.5)
            if search_videos:
                all_videos.extend(search_videos)
                search_success = True
                log(f"  → Search: {len(search_videos)} videos")
        
        # Check results
        if not all_videos:
            log("⚠️ No videos from primary sources!", "WARNING")
            if FALLBACK_CONFIG.get('scrape_fallback', True) and SEARCH_CONFIG['topics']:
                log("  Trying emergency scrape fallback...")
                for query in SEARCH_CONFIG['topics'][:5]:
                    videos = search_youtube_scrape(query)
                    all_videos.extend(videos)
                    time.sleep(0.5)
            if not all_videos:
                log("❌ All sources failed. Check API quota, network, and channel IDs.", "ERROR")
                raise Exception("All sources failed - no videos found")
        
        log(f"\n📊 Total: {len(all_videos)} videos found")
        log(f"   RSS: {'✓' if rss_success else '✗'} | Search: {'✓' if search_success else '✗'}")
        
        history = load_video_history()
        unique_videos = deduplicate_videos(all_videos, history)
        log(f"🆕 Unique: {len(unique_videos)} videos")
        
        if not unique_videos:
            if test_mode:
                log("No unique videos found (all already in history)")
                success = True
                raise KeyboardInterrupt("Test mode - no new videos")
            log("⚠️ No new unique videos found", "WARNING")
        
        ranked = rank_videos(unique_videos)
        top_videos = ranked[:OUTPUT_CONFIG['top_videos_to_submit']]
        
        if test_mode:
            log(f"\nTEST MODE - Top {len(top_videos)}:")
            for i, v in enumerate(top_videos, 1):
                source = v.get("source", "unknown")
                channel = v.get("channel", "Unknown")
                query = v.get("query", "")
                query_str = f" | {query[:20]}..." if query else ""
                score = v.get('quality_score', 0)
                log(f"  {i}. {v['title'][:45]}... 📊 {score:.1f} | {source.upper()} | {channel}{query_str}")
            success = True
            raise KeyboardInterrupt("Test mode complete")
        
        log(f"\n📤 Submitting to Notion...")
        submitted = 0
        today = datetime.now().strftime("%Y-%m-%d")
        for video in top_videos:
            if create_notion_page(video):
                submitted += 1
                history["recommended_videos"].append({
                    "video_id": video["video_id"], "title": video["title"],
                    "url": video["url"], "recommended_date": today,
                    "topic": video.get("channel", "") or video.get("query", "")
                })
        save_video_history(history)
        
        log(f"\n✅ COMPLETED: {submitted}/{OUTPUT_CONFIG['top_videos_to_submit']} submitted")
        log(f"   RSS: {rss_success} | Search: {search_success} | Fallback: {failure_tracker.scrape_fallbacks > 0}")
        success = True
        
    except KeyboardInterrupt as e:
        log(f"\n⚠️ Interrupted: {e}", "WARNING")
        success = (test_mode and all_videos)
    except Exception as e:
        error_msg = str(e) + "\n" + traceback.format_exc()
        log(f"\n❌ ERROR: {e}", "ERROR")
        success = False
    finally:
        log("\n==========================================================")
        log("Saving logs and pushing to Notion...")
        save_log_to_file()
        push_log_to_notion(success, error_msg)
        log("==========================================================")
        
    return success

if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    try:
        success = main(test_mode=test_mode)
        sys.exit(0 if success else 1)
    except Exception as e:
        error_msg = str(e) + "\n" + traceback.format_exc()
        log(f"\n💥 CATASTROPHIC FAILURE: {e}", "CRITICAL")
        save_log_to_file()
        push_log_to_notion(False, error_msg)
        sys.exit(1)
