#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据模型：统一的数据结构和 Schema 定义"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


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
    llm_status: str = "not_analyzed"
    llm_confidence: Optional[float] = None
    llm_reason: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_tags: Optional[List[str]] = None
    ai_platforms: Optional[List[str]] = None
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
            last_updated=now,
            is_fork=item.get("fork", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StarItem":
        """从字典创建 StarItem，忽略未知字段"""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})

    # --- dict 兼容层（迁移期间使用）---
    def __getitem__(self, key: str):
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def __setitem__(self, key: str, value) -> None:
        setattr(self, key, value)
