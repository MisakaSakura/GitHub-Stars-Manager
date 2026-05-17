#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub API 封装"""

import json
import os
import re
import time
import urllib.parse

from concurrent.futures import ThreadPoolExecutor, as_completed
from http_client import HTTPClient
from utils import log


class ReadmeCache:
    """README 内容缓存层（P1-38：从 GitHubAPI 提取为独立类）。"""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 7 * 86400):
        self.cache_dir = cache_dir or os.path.join(os.path.expanduser("~"), ".cache", "github-stars-classifier")
        self.ttl = ttl_seconds
        self.cache_file = os.path.join(self.cache_dir, "readme_cache.json")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._cache: dict = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except json.JSONDecodeError as e:
                log(f"README 缓存 JSON 损坏，将重建: {e}", "WARN")
                self._cache = {}
            except OSError as e:
                log(f"README 缓存读取失败: {e}", "WARN")
                self._cache = {}

    def _save(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except OSError as e:
            log(f"README 缓存写入失败: {e}", "WARN")

    def get(self, key: str, max_length: int = 2000) -> str | None:
        entry = self._cache.get(key)
        if entry and time.time() - entry.get("ts", 0) < self.ttl:
            return entry.get("text", "")[:max_length]
        return None

    def set(self, key: str, text: str) -> None:
        self._cache[key] = {"text": text, "ts": time.time()}
        self._save()


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
            "User-Agent": "GitHub-Stars-Classifier"
        }
        self.client = HTTPClient()
        self._readme_cache = ReadmeCache()

    def _get(self, endpoint: str, params: dict | None = None) -> dict | None:
        url = f"{self.base}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        try:
            code, body = self.client.request(url, headers=self.headers, retries=3)
        except HTTPClientError as e:
            # GC-5: 将底层 HTTPClientError 转换为 GitHubAPIError
            log(f"GitHub API 网络请求失败: {e}", "ERROR")
            raise GitHubServerError(f"无法连接到 GitHub API: {e}") from e
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
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        return []

    def delete_list(self, list_id) -> bool:
        url = f"{self.base}/lists/{list_id}"
        code, _ = self.client.request(url, headers=self.headers, method="DELETE")
        return code == 204

    def get_readme(self, owner: str, repo: str, max_length: int = 2000) -> str:
        """获取仓库 README，带缓存（TTL 7 天）。"""
        import base64

        cache_key = f"{owner}/{repo}"
        cached = self._readme_cache.get(cache_key, max_length)
        if cached is not None:
            return cached

        data = self._get(f"/repos/{owner}/{repo}/readme")
        if not data:
            return ""
        content = (data.get("content") or "").replace("\n", "")
        try:
            decoded = base64.b64decode(content).decode("utf-8")
            text = self._strip_markdown(decoded)
            result = text[:max_length]
            self._readme_cache.set(cache_key, result)
            return result
        except (ValueError, UnicodeDecodeError) as e:
            log(f"README 解码失败 {owner}/{repo}: {e}", "WARN")
            return ""
        except Exception as e:
            log(f"README 处理失败 {owner}/{repo}: {e}", "WARN")
            return ""


    @staticmethod
    def _strip_markdown(text: str) -> str:
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

    def create_issue(self, owner: str, repo: str, title: str, body: str, labels: list[str] | None = None) -> dict | None:
        """创建 GitHub Issue。

        Returns:
            创建成功的 issue dict（含 number, html_url 等），失败时返回 None。
        """
        url = f"{self.base}/repos/{owner}/{repo}/issues"
        payload: dict = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        code, response_body = self.client.request(url, headers=self.headers, method="POST", data=json.dumps(payload))
        if code == 201 and response_body:
            try:
                return json.loads(response_body)
            except json.JSONDecodeError:
                pass
        log(f"创建 Issue 失败 ({code}): {title[:60]}...", "WARN")
        return None

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
            code, body = self.client.request(url, headers=self.headers, retries=3)
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
        """全量获取 Star 项目，支持并发分页（max_workers 控制并发度）。"""
        log(f"全量获取 {username} 的所有 Star 项目...", "STEP")

        first_page = self._fetch_first_page(username, per_page)
        if first_page is None:
            return []
        if len(first_page) < per_page:
            return first_page

        all_pages = {1: first_page}
        failed_pages = self._fetch_remaining_pages(username, per_page, max_workers, all_pages)
        self._retry_failed_pages(username, per_page, failed_pages, all_pages)

        return self._merge_pages(all_pages)

    def _fetch_first_page(self, username: str, per_page: int) -> list | None:
        """串行获取第1页（验证认证和基础参数）。"""
        first_page = self.get_starred(username, page=1, per_page=per_page)
        if not first_page:
            log("全量获取完成: 0 个项目", "OK")
            return None
        log(f"  第 1 页: {len(first_page)} 个")
        return first_page

    def _fetch_remaining_pages(self, username: str, per_page: int, max_workers: int, all_pages: dict) -> list[int]:
        """并发获取后续分页，返回失败页码列表。"""
        failed_pages: list[int] = []
        next_page = 2
        while True:
            batch_pages = range(next_page, next_page + max_workers)
            batch_done = self._fetch_page_batch(username, per_page, batch_pages, all_pages, failed_pages)
            if batch_done:
                break
            next_page += max_workers
            time.sleep(0.3)
        return failed_pages

    def _fetch_page_batch(self, username: str, per_page: int, batch_pages: range, all_pages: dict, failed_pages: list) -> bool:
        """并发获取一批页面，返回是否已到达末尾。"""
        batch_done = False
        with ThreadPoolExecutor(max_workers=len(batch_pages)) as executor:
            futures = {
                executor.submit(self.get_starred, username, p, per_page): p
                for p in batch_pages
            }
            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    data = future.result()
                except Exception as e:
                    log(f"  第 {page_num} 页获取失败: {e}", "WARN")
                    failed_pages.append(page_num)
                    continue
                if data:
                    all_pages[page_num] = data
                    log(f"  第 {page_num} 页: {len(data)} 个")
                    if len(data) < per_page:
                        batch_done = True
                else:
                    batch_done = True
        return batch_done

    def _retry_failed_pages(self, username: str, per_page: int, failed_pages: list[int], all_pages: dict) -> None:
        """重试之前失败的页面。"""
        if not failed_pages:
            return
        log(f"重试 {len(failed_pages)} 个失败页面...", "STEP")
        for page_num in failed_pages:
            try:
                data = self.get_starred(username, page_num, per_page)
                if data:
                    all_pages[page_num] = data
                    log(f"  第 {page_num} 页重试成功: {len(data)} 个")
            except Exception as e:
                log(f"  第 {page_num} 页重试仍失败: {e}", "ERROR")

    @staticmethod
    def _merge_pages(all_pages: dict[int, list]) -> list:
        """按页码排序合并所有页面。"""
        all_stars = []
        for p in sorted(all_pages.keys()):
            all_stars.extend(all_pages[p])
        log(f"全量获取完成: {len(all_stars)} 个项目", "OK")
        return all_stars
