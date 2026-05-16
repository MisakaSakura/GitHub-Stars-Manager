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
    def request(url: str, headers: dict | None = None, method: str = "GET", data=None, timeout: int = 30) -> tuple[int, str]:
        """发送 HTTP 请求，返回 (status_code, body_text)"""
        if HAS_REQUESTS:
            return HTTPClient._request_requests(url, headers, method, data, timeout)
        return HTTPClient._request_urllib(url, headers, method, data, timeout)

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
            return -1, str(e)

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
            return -1, str(e)

    @staticmethod
    def post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 30) -> tuple[int, str]:
        """POST JSON 数据"""
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        return HTTPClient.request(url, headers=h, method="POST", data=payload, timeout=timeout)
