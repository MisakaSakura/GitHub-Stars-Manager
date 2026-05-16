#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""带 TTL 的 LLM 结果缓存"""

import json
import os
import time
from typing import Any

from utils import log


class TTLCache:
    """基于文件的键值缓存，支持 TTL（秒）和版本校验"""

    def __init__(self, cache_file: str = ".llm_cache.json", ttl_seconds: int = 0):
        """
        Args:
            cache_file: 缓存文件路径
            ttl_seconds: TTL，0 表示永不过期
        """
        self.cache_file = cache_file
        self.ttl = ttl_seconds
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    self._data = raw
                else:
                    log("LLM 缓存格式错误（期望 dict），已重置", "WARN")
                    self._data = {}
            except Exception:
                self._data = {}

    def _save(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log(f"LLM 缓存写入失败: {e}", "WARN")

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if self.ttl > 0:
            ts = entry.get("_ts", 0)
            if time.time() - ts > self.ttl:
                self._data.pop(key, None)
                return None
        return entry.get("value")

    def set(self, key: str, value: Any) -> None:
        self._data[key] = {"value": value, "_ts": time.time()}
        self._save()

    def clear(self) -> None:
        self._data.clear()
        self._save()

    def __len__(self) -> int:
        return len(self._data)
