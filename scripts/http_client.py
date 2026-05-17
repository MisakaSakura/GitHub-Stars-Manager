#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一 HTTP 客户端，自动回退到 urllib"""

import json
import urllib.request
import urllib.error

from utils import log

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


import re


def _sanitize_error(msg: str) -> str:
    """脱敏错误消息，移除可能泄露的 token/API key。"""
    # 移除 URL 中可能包含的 token 参数
    msg = re.sub(r'(token|key|api[_-]?key|access[_-]?token)=[^&\s]+', r'\1=***', msg, flags=re.IGNORECASE)
    # 移除 Bearer token
    msg = re.sub(r'Bearer\s+\S+', 'Bearer ***', msg)
    return msg


class HTTPClientError(Exception):
    """HTTP 请求失败异常（含重试耗尽后的错误）"""
    pass


class HTTPClient:
    """统一 HTTP 请求封装，优先使用 requests（带连接池），回退到 urllib"""

    _session = None

    @classmethod
    def _get_session(cls):
        """延迟初始化并复用 requests.Session，启用连接池"""
        if cls._session is None and HAS_REQUESTS:
            cls._session = requests.Session()
        return cls._session

    @classmethod
    def close(cls) -> None:
        """关闭底层 Session，释放连接池资源"""
        if cls._session is not None:
            cls._session.close()
            cls._session = None

    @staticmethod
    def request(url: str, headers: dict | None = None, method: str = "GET", data=None, timeout: int = 30, retries: int = 0) -> tuple[int, str]:
        """发送 HTTP 请求，返回 (status_code, body_text)。

        Args:
            retries: 重试次数，0 表示不重试（由上层调用方统一处理重试逻辑）。
                     GitHub API 等无上层重试的调用方应传入 >0。
        """
        import time
        last_error = ""
        for attempt in range(retries + 1):
            if HAS_REQUESTS:
                code, body = HTTPClient._request_requests(url, headers, method, data, timeout)
            else:
                code, body = HTTPClient._request_urllib(url, headers, method, data, timeout)
            # 2xx 成功，或 4xx 客户端错误（除 429 外）不重试
            if (200 <= code < 300) or (400 <= code < 500 and code != 429):
                return code, body
            last_error = body
            # 指数退避：0.5s, 1s, 2s...
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
        # P1-38: 重试耗尽后抛出异常而非返回 (-1, error)，避免调用方遗漏处理
        raise HTTPClientError(f"HTTP 请求失败（已重试 {retries} 次）: {last_error}")

    @staticmethod
    def _request_requests(url: str, headers, method: str, data, timeout: int) -> tuple[int, str]:
        session = HTTPClient._get_session()
        try:
            kwargs = {"headers": headers or {}, "timeout": timeout}
            if isinstance(data, dict):
                resp = session.request(method, url, json=data, **kwargs)
            elif data:
                resp = session.request(method, url, data=data, **kwargs)
            else:
                resp = session.request(method, url, **kwargs)
            return resp.status_code, resp.text
        except requests.RequestException as e:
            # P1-39: 脱敏，避免 token 泄露到错误消息
            msg = _sanitize_error(str(e))
            return -1, msg

    @staticmethod
    def _request_urllib(url: str, headers, method: str, data, timeout: int) -> tuple[int, str]:
        req = urllib.request.Request(url, headers=headers or {}, method=method)
        if data:
            if isinstance(data, dict):
                req.data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            else:
                req.data = data.encode("utf-8") if isinstance(data, str) else data
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            return e.code, body
        except Exception as e:
            # P1-39: 脱敏，避免 token 泄露到错误消息
            msg = _sanitize_error(str(e))
            return -1, msg

    @staticmethod
    def post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 30) -> tuple[int, str]:
        """POST JSON 数据"""
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        return HTTPClient.request(url, headers=h, method="POST", data=payload, timeout=timeout)
