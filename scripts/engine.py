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
    def __init__(self, db, rule_classifier, llm_classifier=None):
        self.db = db
        self.rule = rule_classifier
        self.llm = llm_classifier
        self.stats = {
            "new": 0, "updated": 0, "skipped": 0,
            "protected": 0, "llm_enhanced": 0, "error": 0
        }

    def process(self, items: list[dict], incremental: bool = False, force_refresh: bool = False, use_llm: bool = False, retry_failed: bool = False, subscribe_all_releases: bool = False) -> dict:
        log(f"处理模式: {'强制刷新' if force_refresh else '增量更新' if incremental else '标准更新'}", "STEP")

        llm_results = {}
        if use_llm and self.llm:
            llm_candidates = []
            for item in items:
                key = f"{item['owner']['login']}/{item['name']}"
                existing = self.db.get(key)
                needs_llm = False
                if not existing:
                    needs_llm = True
                elif existing.get("manual_override"):
                    needs_llm = False
                elif force_refresh:
                    needs_llm = True
                elif retry_failed and existing.get("llm_status") == "failed":
                    needs_llm = True
                elif not incremental:
                    needs_llm = True

                if needs_llm:
                    llm_candidates.append(item)

            if llm_candidates:
                log(f"LLM 批量分类: {len(llm_candidates)} 个项目...", "STEP")
                llm_results = self.llm.classify_batch(llm_candidates)
                self.stats["llm_enhanced"] += len([r for r in llm_results.values() if r])

        for item in items:
            try:
                key = f"{item['owner']['login']}/{item['name']}"
                llm_result = llm_results.get(key)
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
        """对单个项目执行分类并返回 StarItem"""
        platform = self.rule.classify_platform(item)
        ptype = self.rule.classify_type(item)
        eco, role = self.rule.classify_ecology(item)
        language = item.get("language") or "文档 / 无代码"

        existing = self.db.get(f"{item['owner']['login']}/{item['name']}")
        existing_eco = existing.get("ecology") if existing else None
        ecology_locked = existing_eco and _is_ecology_locked(existing_eco)

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

        if llm_result:
            llm_status = "success"
        elif use_llm and self.llm and not llm_result:
            llm_status = "failed"
        else:
            llm_status = "not_analyzed"

        if existing and existing.get("manual_override") and llm_result:
            llm_status = "skipped"

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
            llm_status=llm_status,
            llm_confidence=llm_result.get("confidence") if llm_result else None,
            llm_reason=llm_result.get("reason") if llm_result else None,
            ai_summary=llm_result.get("ai_summary") if llm_result else None,
            ai_tags=llm_result.get("ai_tags") if llm_result else None,
            ai_platforms=llm_result.get("ai_platforms") if llm_result else None,
            subscribe_releases=(existing.get("subscribe_releases") if existing else False) or subscribe_all_releases,
            last_release_tag=existing.get("last_release_tag") if existing else None,
            is_fork=item.get("fork", False),
        )
