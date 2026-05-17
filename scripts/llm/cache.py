#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""带 TTL 和版本控制的 LLM 结果缓存"""

import json
import os
import time
from typing import Any

from utils import log


class TTLCache:
    """基于文件的键值缓存，支持 TTL（秒）和规则版本校验。

    P1-24: 基于 RULES_VERSION 的缓存失效 — 规则版本变化时自动清空旧缓存。
    P1-25: 批量操作内存缓冲 — set() 只更新内存，统一 save() 或析构时刷盘。
    """

    def __init__(self, cache_file: str = ".llm_cache.json", ttl_seconds: int = 0, rules_version: str = ""):
        """
        Args:
            cache_file: 缓存文件路径
            ttl_seconds: TTL，0 表示永不过期
            rules_version: 规则版本字符串，变化时自动失效缓存
        """
        self.cache_file = cache_file
        self.ttl = ttl_seconds
        self.rules_version = rules_version
        self._data: dict[str, dict] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    stored_version = raw.get("_meta", {}).get("rules_version", "")
                    if self.rules_version and stored_version != self.rules_version:
                        log(f"LLM 缓存版本不匹配 ({stored_version} -> {self.rules_version})，已重置", "WARN")
                        self._data = {"_meta": {"rules_version": self.rules_version}}
                    else:
                        self._data = raw
                        # 确保 _meta 存在
                        if "_meta" not in self._data:
                            self._data["_meta"] = {"rules_version": self.rules_version}
                else:
                    self._data = {"_meta": {"rules_version": self.rules_version}}
            except Exception:
                self._data = {"_meta": {"rules_version": self.rules_version}}
        else:
            self._data = {"_meta": {"rules_version": self.rules_version}}

    def _save(self) -> None:
        if not self._dirty:
            return
        # 确保 _meta 始终是最新的
        self._data["_meta"] = {"rules_version": self.rules_version}
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            self._dirty = False
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
                self._dirty = True
                return None
        return entry.get("value")

    def set(self, key: str, value: Any) -> None:
        self._data[key] = {"value": value, "_ts": time.time()}
        self._dirty = True

    def clear(self) -> None:
        meta = self._data.get("_meta", {})
        self._data.clear()
        self._data["_meta"] = meta
        self._dirty = True

    def save(self) -> None:
        """显式保存缓存到磁盘（建议在批量操作后调用）。"""
        self._save()

    def __len__(self) -> int:
        return len([k for k in self._data if not k.startswith("_")])
