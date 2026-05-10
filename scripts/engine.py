#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量更新引擎"""

from collections import Counter
from datetime import datetime, timezone

from models import StarItem
from utils import log


def _is_ecology_locked(ecology_name: str | None) -> bool:
    """检查生态是否被用户锁定（不允许 AI 覆盖）"""
    from config import LOCKED_ECOLOGIES
    return ecology_name in LOCKED_ECOLOGIES


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


class IncrementalEngine:
    def __init__(self, db, rule_classifier, llm_classifier=None, ai_db=None):
        self.db = db
        self.rule = rule_classifier
        self.llm = llm_classifier
        self.ai_db = ai_db
        self.stats = {
            "new": 0, "updated": 0, "skipped": 0,
            "protected": 0, "llm_enhanced": 0, "error": 0
        }

    def _needs_llm(self, key: str, existing, force_refresh: bool, retry_failed: bool, llm_interval_days: int) -> bool:
        """判断项目是否需要 LLM 分析：独立增量策略，不受规则增量模式影响"""
        if not existing:
            return True  # 新项目必须分析
        if existing.get("manual_override"):
            return False  # 手动保护跳过
        if force_refresh:
            return True  # 强制刷新全部重分析

        # 从 AI 数据库查询上次分析状态
        ai_record = self.ai_db.get(key) if self.ai_db else None
        if retry_failed and ai_record and ai_record.llm_status == "failed":
            return True  # 重试之前失败的项目

        if not ai_record or not ai_record.analyzed_at:
            return True  # 从未分析过

        # 检查是否超过间隔天数
        from datetime import datetime, timezone, timedelta
        try:
            last_dt = datetime.fromisoformat(ai_record.analyzed_at)
            if datetime.now(timezone.utc) - last_dt >= timedelta(days=llm_interval_days):
                return True  # 间隔已到，需要重新分析
        except Exception:
            return True  # 时间戳异常，重新分析

        return False  # 已有成功分析且在间隔内，跳过

    def process(self, items: list[dict], incremental: bool = False, force_refresh: bool = False, use_llm: bool = False, retry_failed: bool = False, subscribe_all_releases: bool = False, llm_interval_days: int = 30) -> dict:
        log(f"处理模式: {'强制刷新' if force_refresh else '增量更新' if incremental else '标准更新'}", "STEP")

        self.llm_results: dict[str, dict] = {}
        if use_llm and self.llm:
            llm_candidates = []
            for item in items:
                key = f"{item['owner']['login']}/{item['name']}"
                existing = self.db.get(key)
                if self._needs_llm(key, existing, force_refresh, retry_failed, llm_interval_days):
                    llm_candidates.append(item)

            if llm_candidates:
                log(f"LLM 批量分类: {len(llm_candidates)} 个项目...", "STEP")
                self.llm_results = self.llm.classify_batch(llm_candidates)
                self.stats["llm_enhanced"] += len([r for r in self.llm_results.values() if r])

        for item in items:
            try:
                key = f"{item['owner']['login']}/{item['name']}"
                llm_result = self.llm_results.get(key)
                self._process_single(item, incremental, force_refresh, use_llm, llm_result, subscribe_all_releases)
            except Exception as e:
                log(f"处理 {item.get('full_name', item.get('name'))} 失败: {e}", "ERROR")
                self.stats["error"] += 1

        return self.stats

    def _process_single(self, item: dict, incremental: bool, force_refresh: bool, use_llm: bool, llm_result: dict | None = None, subscribe_all_releases: bool = False) -> None:
        key = f"{item['owner']['login']}/{item['name']}"
        existing = self.db.get(key)

        if existing:
            if existing.get("manual_override"):
                existing.stars = item.get("stargazers_count", 0)
                existing.last_updated = datetime.now(timezone.utc).isoformat()
                self.stats["protected"] += 1
                return

            if force_refresh:
                classification = self._classify_item(item, use_llm, llm_result, subscribe_all_releases)
                classification.first_seen = existing.first_seen
                classification.manual_override = False
                classification.override_fields = []
                self.db.set(key, classification)
                self.stats["updated"] += 1
                return

            if incremental:
                existing.stars = item.get("stargazers_count", 0)
                existing.description = item.get("description") or ""
                existing.topics = item.get("topics", [])
                existing.last_updated = datetime.now(timezone.utc).isoformat()
                # 增量模式下规则分类跳过，但 LLM 覆盖仍然应用（修正已有项目分类）
                if llm_result and llm_result.get("confidence", 0) > 0.7:
                    existing_eco = existing.get("ecology")
                    ecology_locked = existing_eco and _is_ecology_locked(existing_eco)
                    existing.platform = llm_result.get("platform", existing.platform)
                    existing.type = llm_result.get("type", existing.type)
                    if not ecology_locked:
                        if llm_result.get("ecology"):
                            existing.ecology = llm_result["ecology"]
                        if llm_result.get("ecology_role"):
                            existing.ecology_role = llm_result["ecology_role"]
                self.stats["skipped"] += 1
                return

            classification = self._classify_item(item, use_llm, llm_result, subscribe_all_releases)
            classification.first_seen = existing.first_seen
            self.db.set(key, classification)
            self.stats["updated"] += 1
            return

        classification = self._classify_item(item, use_llm, llm_result, subscribe_all_releases)
        self.db.set(key, classification)
        self.stats["new"] += 1

    def _classify_item(self, item: dict, use_llm: bool, llm_result: dict | None = None, subscribe_all_releases: bool = False) -> StarItem:
        """对单个项目执行分类并返回 StarItem（AI 元数据不再写入 StarItem）"""
        platform = self.rule.classify_platform(item)
        ptype = self.rule.classify_type(item)
        eco, role = self.rule.classify_ecology(item)
        language = item.get("language") or "文档 / 无代码"

        existing = self.db.get(f"{item['owner']['login']}/{item['name']}")
        existing_eco = existing.get("ecology") if existing else None
        ecology_locked = existing_eco and _is_ecology_locked(existing_eco)

        # LLM 可以覆盖规则分类结果（分类决策本身是即时的，不依赖 AI DB）
        if use_llm and self.llm and llm_result:
            if llm_result.get("confidence", 0) > 0.7:
                platform = llm_result.get("platform", platform)
                ptype = llm_result.get("type", ptype)
                if not ecology_locked:
                    if llm_result.get("ecology"):
                        eco = llm_result["ecology"]
                    if llm_result.get("ecology_role"):
                        role = llm_result["ecology_role"]
                else:
                    eco = existing_eco

        return StarItem(
            full_name=f"{item['owner']['login']}/{item['name']}",
            name=item["name"],
            owner=item["owner"]["login"],
            description=item.get("description") or "",
            language=language,
            platform=platform,
            type=ptype,
            ecology=eco or "独立项目 / Standalone",
            ecology_role=role or "-",
            topics=item.get("topics", []),
            stars=item.get("stargazers_count", 0),
            url=item["html_url"],
            first_seen=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
            manual_override=False,
            override_fields=[],
            subscribe_releases=(existing.get("subscribe_releases") if existing else False) or subscribe_all_releases,
            last_release_tag=existing.get("last_release_tag") if existing else None,
            is_fork=item.get("fork", False),
        )
