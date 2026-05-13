#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub API 封装"""

import json
import time
import urllib.parse

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
            return json.loads(body)
        elif code == 401:
            raise GitHubAuthError("Token 无效或已过期")
        elif code == 403:
            raise GitHubRateLimitError("API 速率限制，请稍后再试")
        elif code == 404:
            log("资源不存在", "ERROR")
            return None
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
        import re
        data = self._get(f"/repos/{owner}/{repo}/readme")
        if not data:
            return ""
        content = data.get("content", "").replace("\n", "")
        try:
            decoded = base64.b64decode(content).decode("utf-8")
            text = self._strip_markdown(decoded)
            return text[:max_length]
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
            data = json.loads(body)
            if not data:
                break
            all_repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
            time.sleep(0.3)
        return all_repos

    def fetch_all(self, username: str, per_page: int = 100) -> list:
        all_stars = []
        page = 1
        log(f"全量获取 {username} 的所有 Star 项目...", "STEP")
        while True:
            data = self.get_starred(username, page=page, per_page=per_page)
            if not data:
                break
            all_stars.extend(data)
            log(f"  第 {page} 页: {len(data)} 个 (累计 {len(all_stars)})")
            if len(data) < per_page:
                break
            page += 1
            time.sleep(0.3)
        log(f"全量获取完成: {len(all_stars)} 个项目", "OK")
        return all_stars
