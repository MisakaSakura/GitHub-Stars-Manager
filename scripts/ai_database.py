#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 分析结果数据库：与主数据库解耦，独立存储 LLM 分类结果"""

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field, asdict
from typing import Optional, List

from utils import log


@dataclass
class AIResult:
    """单个项目的 AI 分析结果"""
    full_name: str
    analyzed_at: str = ""
    llm_status: str = "not_analyzed"
    llm_confidence: Optional[float] = None
    llm_reason: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_tags: Optional[List[str]] = None
    ai_platforms: Optional[List[str]] = None
    # AI 建议的分类（可与规则分类不同，用于报告展示）
    ai_platform: Optional[str] = None
    ai_type: Optional[str] = None
    ai_ecology: Optional[str] = None
    ai_ecology_role: Optional[str] = None

    def to_dict(self) -> dict:
        # GC-7: 统一为浅拷贝，与 StarItem.to_dict() 保持一致
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict) -> "AIResult":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        # GC-8: 兜底默认值（向后兼容）
        if not filtered.get("analyzed_at"):
            from datetime import datetime, timezone
            filtered["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        if not filtered.get("llm_status"):
            filtered["llm_status"] = "not_analyzed"
        return cls(**filtered)


class AIDatabase:
    """AI 分析结果存储，与主数据库完全解耦"""

    def __init__(self, ai_db_path: str):
        self.path = ai_db_path
        self.data: dict[str, AIResult] = {}
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    self.data = {
                        k: AIResult.from_dict(v) if isinstance(v, dict) else AIResult(full_name=k)
                        for k, v in raw.items()
                    }
                log(f"加载 AI 数据库: {len(self.data)} 条记录", "OK")
            except Exception as e:
                log(f"AI 数据库损坏，将重建: {e}", "WARN")
                self.data = {}
        else:
            log("AI 数据库不存在，将创建新数据库")
            self.data = {}

    def save(self) -> None:
        from utils import atomic_write

        def _write(f):
            json.dump(
                {k: v.to_dict() for k, v in self.data.items()},
                f, ensure_ascii=False, indent=2
            )

        atomic_write(self.path, _write)

    def get(self, full_name: str) -> AIResult | None:
        return self.data.get(full_name)

    def set(self, full_name: str, result: AIResult) -> None:
        self.data[full_name] = result

    def update_from_llm_result(self, full_name: str, llm_result: dict | None, status: str = "success") -> None:
        """从 LLM classify_batch 的结果更新记录"""
        from datetime import datetime, timezone
        analyzed_at = None
        if llm_result:
            analyzed_at = llm_result.get("analyzed_at")
        if not analyzed_at:
            analyzed_at = datetime.now(timezone.utc).isoformat()
        result = AIResult(
            full_name=full_name,
            analyzed_at=analyzed_at,
            llm_status=status,
            llm_confidence=llm_result.get("confidence") if llm_result else None,
            llm_reason=llm_result.get("reason") if llm_result else None,
            ai_summary=llm_result.get("ai_summary") if llm_result else None,
            ai_tags=llm_result.get("ai_tags") if llm_result else None,
            ai_platforms=llm_result.get("ai_platforms") if llm_result else None,
            ai_platform=llm_result.get("platform") if llm_result else None,
            ai_type=llm_result.get("type") if llm_result else None,
            ai_ecology=llm_result.get("ecology") if llm_result else None,
            ai_ecology_role=llm_result.get("ecology_role") if llm_result else None,
        )
        self.data[full_name] = result

    def delete(self, key: str) -> bool:
        """删除记录，返回是否成功。"""
        if key in self.data:
            del self.data[key]
            return True
        return False

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def __len__(self) -> int:
        return len(self.data)

    def migrate_from_stars_db(self, db_items: Iterable) -> int:
        """从主数据库迁移旧的 AI 字段到 AI 数据库，返回迁移数量"""
        migrated = 0
        for item in db_items:
            key = item.full_name if hasattr(item, "full_name") else item.get("full_name")
            if not key:
                continue
            # 如果已有 AI 记录，跳过
            if key in self.data:
                continue
            # 只有当项目有 AI 字段时才迁移
            llm_status = item.llm_status if hasattr(item, "llm_status") else item.get("llm_status")
            if llm_status and llm_status != "not_analyzed":
                self.data[key] = AIResult(
                    full_name=key,
                    analyzed_at=item.last_updated if hasattr(item, "last_updated") else item.get("last_updated", ""),
                    llm_status=llm_status,
                    llm_confidence=item.llm_confidence if hasattr(item, "llm_confidence") else item.get("llm_confidence"),
                    llm_reason=item.llm_reason if hasattr(item, "llm_reason") else item.get("llm_reason"),
                    ai_summary=item.ai_summary if hasattr(item, "ai_summary") else item.get("ai_summary"),
                    ai_tags=item.ai_tags if hasattr(item, "ai_tags") else item.get("ai_tags"),
                    ai_platforms=item.ai_platforms if hasattr(item, "ai_platforms") else item.get("ai_platforms"),
                )
                migrated += 1
        if migrated:
            log(f"从主数据库迁移 {migrated} 条 AI 记录到 AI 数据库", "OK")
            self.save()
        return migrated
