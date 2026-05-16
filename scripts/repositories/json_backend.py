#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON 文件 Repository 实现 —— StarsDB / AIDatabase 的适配层"""

import os
from typing import Iterator, Any

from .base import Repository
from database import StarsDB
from ai_database import AIDatabase
from utils import log


class JSONStarsRepository(Repository):
    """StarsDB 的 Repository 适配器，提供统一接口"""

    def __init__(self, db_path: str):
        self._backend = StarsDB(db_path)

    def get(self, key: str) -> Any | None:
        return self._backend.get(key)

    def set(self, key: str, value: Any) -> None:
        self._backend.set(key, value)

    def delete(self, key: str) -> bool:
        return self._backend.delete(key)

    def keys(self) -> Iterator[str]:
        return iter(self._backend.keys())

    def values(self) -> Iterator[Any]:
        return iter(self._backend.values())

    def items(self) -> Iterator[tuple[str, Any]]:
        return iter(self._backend.items())

    def save(self) -> None:
        self._backend.save()

    def __len__(self) -> int:
        return len(self._backend)

    def meta_get(self, key: str, default=None):
        return self._backend.meta.get(key, default)

    def meta_set(self, key: str, value) -> None:
        self._backend.meta[key] = value

    def meta_save(self) -> None:
        self._backend.save_meta()

    # --- 向后兼容：暴露底层 StarsDB 的特殊方法 ---
    @property
    def backend(self) -> StarsDB:
        """获取底层 StarsDB（兼容旧代码，后续移除）"""
        return self._backend


class JSONAIRepository(Repository):
    """AIDatabase 的 Repository 适配器"""

    def __init__(self, db_path: str):
        self._backend = AIDatabase(db_path)

    def get(self, key: str) -> Any | None:
        return self._backend.get(key)

    def set(self, key: str, value: Any) -> None:
        self._backend.set(key, value)

    def delete(self, key: str) -> bool:
        if self._backend.get(key) is not None:
            del self._backend.data[key]
            return True
        return False

    def keys(self) -> Iterator[str]:
        return iter(self._backend.data.keys())

    def values(self) -> Iterator[Any]:
        return iter(self._backend.data.values())

    def items(self) -> Iterator[tuple[str, Any]]:
        return iter(self._backend.data.items())

    def save(self) -> None:
        self._backend.save()

    def __len__(self) -> int:
        return len(self._backend.data)

    def meta_get(self, key: str, default=None):
        # AI DB 无独立 meta，使用 data 中的特殊键
        return default

    def meta_set(self, key: str, value) -> None:
        pass

    def meta_save(self) -> None:
        pass

    @property
    def backend(self) -> AIDatabase:
        return self._backend
