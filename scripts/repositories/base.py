#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository 抽象基类"""

from abc import ABC, abstractmethod
from typing import Iterator, Any


class Repository(ABC):
    """统一的数据访问接口，屏蔽底层存储差异（JSON / SQLite / 内存）"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """根据 key 获取记录，不存在返回 None"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """保存或更新记录"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除记录，返回是否成功"""
        pass

    @abstractmethod
    def keys(self) -> Iterator[str]:
        """返回所有 key 的迭代器"""
        pass

    @abstractmethod
    def values(self) -> Iterator[Any]:
        """返回所有 value 的迭代器"""
        pass

    @abstractmethod
    def items(self) -> Iterator[tuple[str, Any]]:
        """返回所有 (key, value) 的迭代器"""
        pass

    @abstractmethod
    def save(self) -> None:
        """将内存中的变更持久化到存储"""
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass

    @abstractmethod
    def meta_get(self, key: str, default=None):
        """获取元数据字段"""
        pass

    @abstractmethod
    def meta_set(self, key: str, value) -> None:
        """设置元数据字段"""
        pass

    @abstractmethod
    def meta_save(self) -> None:
        """保存元数据"""
        pass