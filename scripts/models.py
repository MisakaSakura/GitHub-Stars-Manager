#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据模型：统一的数据结构和 Schema 定义"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any


class LLMStatus(str, Enum):
    """LLM 分析状态枚举（向后兼容字符串比较）"""
    NOT_ANALYZED = "not_analyzed"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StarItem:
    """GitHub Star 项目的统一数据模型"""
    full_name: str
    name: str
    owner: str
    description: str = ""
    language: str = "文档 / 无代码"
    platform: str = "其他 / 未分类"
    type: str = "其他 / 未分类"
    ecology: str = "独立项目 / Standalone"
    ecology_role: str = "-"
    topics: List[str] = field(default_factory=list)
    stars: int = 0
    url: str = ""
    first_seen: str = ""
    last_updated: str = ""
    manual_override: bool = False
    override_fields: List[str] = field(default_factory=list)
    override_rules_version: str = ""  # 设置 manual_override 时的规则版本
    subscribe_releases: bool = False
    last_release_tag: Optional[str] = None
    last_release_checked: Optional[str] = None
    is_fork: bool = False
    parent_full_name: Optional[str] = None
    parent_pushed_at: Optional[str] = None
    imported: bool = False
    github_list_source: Optional[str] = None

    @classmethod
    def from_github_api(cls, item: Dict[str, Any]) -> "StarItem":
        """从 GitHub API 响应创建 StarItem"""
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            full_name=f"{item['owner']['login']}/{item['name']}",
            name=item["name"],
            owner=item["owner"]["login"],
            description=item.get("description") or "",
            language=item.get("language") or "文档 / 无代码",
            topics=item.get("topics", []),
            stars=item.get("stargazers_count", 0),
            url=item.get("html_url", ""),
            first_seen=now,
            last_updated=item.get("pushed_at") or now,
            is_fork=item.get("fork", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。返回浅拷贝，避免 asdict 深拷贝开销。"""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StarItem":
        """从字典创建 StarItem，忽略未知字段"""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        # 兜底：旧数据可能没有 first_seen，避免被误判为新收录
        if not filtered.get("first_seen"):
            filtered["first_seen"] = filtered.get("last_updated") or "1970-01-01T00:00:00+00:00"
        return cls(**filtered)

