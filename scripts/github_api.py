#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub API 封装"""

import json
import time
import urllib.parse

from concurrent.futures import ThreadPoolExecutor, as_completed
from http_client import HTTPClient
from utils import log


class GitHubAPIError(Exception):
    """GitHub API 相关错误"""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """API 速率限制"""
    pass


class GitHubAuthError(GitHubAPIError):
    """认证失败"""
    pass


class GitHubServerError(GitHubAPIError):
    """GitHub 服务端错误（5xx）"""
    pass


class GitHubAPI:
    def __init__(self, token: str):
        self.token = token
        self.base = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Stars-Classifier-v4"
        }
        self.client = HTTPClient()

    def _get(self, endpoint: str, params: dict | None = None) -> dict | None:
        url = f"{self.base}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        code, body = self.client.request(url, headers=self.headers)
        if code == 200:
            if not body:
                log("API 返回空响应体", "WARN")
                return None
            try:
                return json.loads(body)
            except json.JSONDecodeError as e:
                log(f"API 返回无效 JSON: {e}", "ERROR")
                return None
        elif code == 401:
            raise GitHubAuthError("Token 无效或已过期")
        elif code == 403:
            raise GitHubRateLimitError("API 速率限制，请稍后再试")
        elif code == 404:
            log("资源不存在", "ERROR")
            return None
        elif code >= 500:
            # P1 fix: 服务端错误不应被静默吞没
            raise GitHubServerError(f"GitHub 服务端错误 {code}: {body[:200]}")
        else:
            log(f"API 错误 {code}: {body[:200]}", "ERROR")
            return None

    def get_user(self, username: str) -> dict | None:
        return self._get(f"/users/{username}")

    def get_starred(self, username: str, page: int = 1, per_page: int = 100) -> dict | None:
        params = {"page": page, "per_page": per_page}
        return self._get(f"/users/{username}/starred", params)

    def get_lists(self, username: str) -> list:
        return self._get(f"/users/{username}/lists") or []

    def get_list_items(self, list_id) -> list:
        result = self._get(f"/lists/{list_id}/items")
        if result and "items" in result:
            return result["items"]
        return []

    def delete_list(self, list_id) -> bool:
        url = f"{self.base}/lists/{list_id}"
        code, _ = self.client.request(url, headers=self.headers, method="DELETE")
        return code == 204

    def get_readme(self, owner: str, repo: str, max_length: int = 2000) -> str:
        import base64
        import json
        import os
        import time

        cache_key = f"{owner}/{repo}"
        # 缓存文件放在数据库所在目录，避免随工作目录变化
        cache_dir = os.path.dirname(os.path.abspath(__file__))
        cache_file = os.path.join(cache_dir, ".readme_cache.json")
        cache_ttl = 7 * 86400  # 7 天

        # 尝试读取缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                entry = cache.get(cache_key)
                if entry and time.time() - entry.get("ts", 0) < cache_ttl:
                    return entry.get("text", "")[:max_length]
            except Exception:
                cache = {}
        else:
            cache = {}

        data = self._get(f"/repos/{owner}/{repo}/readme")
        if not data:
            return ""
        content = (data.get("content") or "").replace("\n", "")
        try:
            decoded = base64.b64decode(content).decode("utf-8")
            text = self._strip_markdown(decoded)
            result = text[:max_length]
            # 写入缓存
            cache[cache_key] = {"text": result, "ts": time.time()}
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return result
        except Exception:
            return ""

    @staticmethod
    def _strip_markdown(text: str) -> str:
        import re
        text = re.sub(r'```[\s\S]*?```', ' ', text)
        text = re.sub(r'`[^`]*`', ' ', text)
        # 先移除图片，再处理链接，避免 ![alt](url) 被误解析为链接
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def get_latest_release(self, owner: str, repo: str) -> dict | None:
        return self._get(f"/repos/{owner}/{repo}/releases/latest")

    def list_releases(self, owner: str, repo: str, per_page: int = 10) -> list[dict]:
        """获取仓库最近 releases 列表（用于捕获一周内的多次发布）"""
        return self._get(f"/repos/{owner}/{repo}/releases?per_page={per_page}") or []

    def get_repo_info(self, owner: str, repo: str) -> dict | None:
        return self._get(f"/repos/{owner}/{repo}")

    def get_user_repos(self, username: str, repo_type: str = "owner", per_page: int = 100) -> list:
        all_repos = []
        page = 1
        while True:
            params = {"type": repo_type, "per_page": per_page, "page": page}
            url = f"{self.base}/users/{username}/repos?" + urllib.parse.urlencode(params)
            code, body = self.client.request(url, headers=self.headers)
            if code != 200:
                break
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                log(f"GitHub API 返回无效 JSON: {body[:200]}", "WARN")
                break
            if not data:
                break
            all_repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
            time.sleep(0.3)
        return all_repos

    def fetch_all(self, username: str, per_page: int = 100, max_workers: int = 4) -> list:
        """全量获取 Star 项目，支持并发分页（max_workers 控制并发度）"""
        log(f"全量获取 {username} 的所有 Star 项目...", "STEP")

        # 第1页串行获取（验证认证和基础参数）
        first_page = self.get_starred(username, page=1, per_page=per_page)
        if not first_page:
            log("全量获取完成: 0 个项目", "OK")
            return []

        all_pages = {1: first_page}
        log(f"  第 1 页: {len(first_page)} 个")

        if len(first_page) < per_page:
            log(f"全量获取完成: {len(first_page)} 个项目", "OK")
            return first_page

        # 并发获取后续页
        next_page = 2
        while True:
            batch_pages = range(next_page, next_page + max_workers)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.get_starred, username, p, per_page): p
                    for p in batch_pages
                }
                batch_done = False
                for future in as_completed(futures):
                    page_num = futures[future]
                    try:
                        data = future.result()
                    except Exception as e:
                        log(f"  第 {page_num} 页获取失败: {e}", "WARN")
                        continue
                    if data:
                        all_pages[page_num] = data
                        log(f"  第 {page_num} 页: {len(data)} 个")
                        if len(data) < per_page:
                            batch_done = True
                    else:
                        batch_done = True

            if batch_done:
                break
            next_page += max_workers
            time.sleep(0.3)

        # 按页码排序合并
        all_stars = []
        for p in sorted(all_pages.keys()):
            all_stars.extend(all_pages[p])

        log(f"全量获取完成: {len(all_stars)} 个项目", "OK")
        return all_stars
