#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 分析结果数据库：与主数据库解耦，独立存储 LLM 分类结果"""

import json
import os
from collections.abc import Iterable
from models import AIResult
from utils import log


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

        def _get(obj, field: str, default=None):
            return obj.get(field, default) if isinstance(obj, dict) else getattr(obj, field, default)

        migrated = 0
        for item in db_items:
            key = _get(item, "full_name")
            if not key:
                continue
            # 如果已有 AI 记录，跳过
            if key in self.data:
                continue
            # 只有当项目有 AI 字段时才迁移
            llm_status = _get(item, "llm_status")
            if llm_status and llm_status != "not_analyzed":
                self.data[key] = AIResult(
                    full_name=key,
                    analyzed_at=_get(item, "last_updated", ""),
                    llm_status=llm_status,
                    llm_confidence=_get(item, "llm_confidence"),
                    llm_reason=_get(item, "llm_reason"),
                    ai_summary=_get(item, "ai_summary"),
                    ai_tags=_get(item, "ai_tags"),
                    ai_platforms=_get(item, "ai_platforms"),
                )
                migrated += 1
        if migrated:
            log(f"从主数据库迁移 {migrated} 条 AI 记录到 AI 数据库", "OK")
            self.save()
        return migrated
