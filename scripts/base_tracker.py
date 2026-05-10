#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracker 抽象基类，统一 ReleaseTracker 和 ForkTracker 的接口"""

from abc import ABC, abstractmethod
from utils import log


class BaseTracker(ABC):
    """追踪器基类：检测更新并格式化报告"""

    def __init__(self, github_api: "GitHubAPI"):
        self.gh = github_api

    @abstractmethod
    def check(self, *args, **kwargs):
        """执行检查，返回更新列表"""
        pass

    @abstractmethod
    def format_report(self, updates: list[dict]) -> str:
        """将更新列表格式化为纯文本报告"""
        pass

    def _truncate(self, items: list[dict], limit: int = 10, title: str = "") -> str:
        """通用截断格式化辅助"""
        if not items:
            return ""
        lines = [title, "-" * 30]
        for u in items[:limit]:
            lines.append(self._format_item(u))
        if len(items) > limit:
            lines.append(f"  ... 还有 {len(items) - limit} 个")
        return "\n".join(lines)

    @abstractmethod
    def _format_item(self, item: dict) -> str:
        pass
