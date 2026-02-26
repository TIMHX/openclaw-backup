#!/usr/bin/env python3
"""
GitHub Trending Scouter V2 - 支持全量查重与自动更新 Star 数
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ====== CONFIG (建议使用环境变量或外部 yaml) ======
NOTION_TOKEN = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DATABASE_ID = "2f855a34-9949-8020-83b5-cc37c2f54df5"  # 知识中心 database_id
DATA_SOURCE_ID = "2f855a34-9949-806b-888c-000bf8c77d79"  # data_source_id for queries
CATEGORY = "Github"


class NotionClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2025-09-03",  # 使用最新的 API 版本
            "Content-Type": "application/json",
        }

    def _request(self, url, method="POST", data=None):
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode() if data else None,
            headers=self.headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def get_all_existing_repos(self):
        """分页获取数据库中所有 Repo URL 及其对应的 Page ID"""
        url = f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query"
        existing_map = {}
        has_more = True
        next_cursor = None

        print("[INFO] 正在同步 Notion 已有数据...")
        while has_more:
            payload = {"page_size": 100}
            if next_cursor:
                payload["start_cursor"] = next_cursor

            data = self._request(url, data=payload)
            for page in data.get("results", []):
                repo_url = page["properties"].get("URL", {}).get("url")
                if repo_url:
                    existing_map[repo_url] = page["id"]

            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return existing_map

    def create_page(self, repo, category):
        """创建新页面"""
        url = "https://api.notion.com/v1/pages"
        name = repo["full_name"]
        stars = repo["stargazers_count"]
        desc = repo.get("description") or "No description"
        link = repo["html_url"]
        lang = repo.get("language") or "N/A"

        payload = {
            "parent": {"database_id": DATABASE_ID},
            "properties": {
                "Goal name": {"title": [{"text": {"content": f"{name} ⭐ {stars}"}}]},
                "Category": {"select": {"name": category}},
                "Insert_date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
                "URL": {"url": link},
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": f"📌 {desc}"}}]},
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": f"⭐ {stars} | 💻 {lang}"}}]
                    },
                },
            ],
        }
        return self._request(url, method="POST", data=payload)

    def update_page(self, page_id, repo):
        """更新已存在页面的 Star 数和日期"""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        name = repo["full_name"]
        stars = repo["stargazers_count"]

        payload = {
            "properties": {
                "Goal name": {"title": [{"text": {"content": f"{name} ⭐ {stars}"}}]},
                "Insert_date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
            }
        }
        return self._request(url, method="PATCH", data=payload)


def fetch_github_trending():
    """获取最近 20 天内创建的、Star 最多的项目"""
    days_ago = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
    query = f"created:>{days_ago}"
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page=15"

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode()).get("items", [])


def main():
    if not NOTION_TOKEN:
        print("[ERROR] 缺少 NOTION_TOKEN 环境变量")
        return

    notion = NotionClient(NOTION_TOKEN)

    try:
        # 1. 获取 Notion 中已有的 URL 映射
        existing_repos = notion.get_all_existing_repos()
        print(f"[INFO] 数据库中已记录 {len(existing_repos)} 个项目")

        # 2. 获取 GitHub 趋势
        print("[INFO] 正在抓取 GitHub Trending...")
        repos = fetch_github_trending()

        # 3. 执行 Upsert
        new_count = 0
        update_count = 0

        for repo in repos:
            repo_url = repo["html_url"]
            repo_name = repo["full_name"]

            if repo_url in existing_repos:
                # 更新旧项目
                page_id = existing_repos[repo_url]
                notion.update_page(page_id, repo)
                print(f"🔄 更新项目: {repo_name}")
                update_count += 1
            else:
                # 插入新项目
                notion.create_page(repo, CATEGORY)
                print(f"✨ 新增项目: {repo_name}")
                new_count += 1

            # 避免请求过快触发 Notion 速率限制
            time.sleep(0.3)

        print(f"\n📊 运行结束: 新增 {new_count} 个, 更新 {update_count} 个。")

    except Exception as e:
        print(f"[FATAL ERROR] {e}")


if __name__ == "__main__":
    main()
