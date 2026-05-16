#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量更新引擎"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from models import StarItem
from utils import log


def should_auto_refresh(force_refresh: bool, last_refresh_at: str, auto_refresh_days: int) -> bool:
    """判断是否需要自动全量刷新（P1-29: 提取为单一来源函数）。

    Returns:
        True 如果满足以下任一条件：
        - 用户显式要求 force_refresh
        - 从未全量刷新过（last_refresh_at 为空）
        - 距离上次全量刷新已超过 auto_refresh_days 天
        - last_refresh_at 时间戳格式无效
    """
    if force_refresh:
        return True
    if not last_refresh_at:
        return True
    try:
        last_dt = datetime.fromisoformat(last_refresh_at)
        interval = timedelta(days=auto_refresh_days)
        if datetime.now(timezone.utc) - last_dt >= interval:
            return True
    except ValueError:
        return True
    return False


@dataclass
class EngineConfig:
    """增量更新引擎的配置参数（P1-14: 替代过长的 process() 参数列表）。"""
    items: list[dict]
    incremental: bool = False
    force_refresh: bool = False
    use_llm: bool = False
    retry_failed: bool = False
    subscribe_all_releases: bool = False
    llm_interval_days: int = 30


def _is_ecology_locked(ecology_name: str | None) -> bool:
    """检查生态是否被用户锁定（不允许 AI 覆盖）"""
    from config import LOCKED_ECOLOGIES
    return ecology_name in LOCKED_ECOLOGIES


def _normalize_field(value: str | None, field: str) -> str | None:
    """将 LLM 返回的分类字段归一化为标准名称。
    field: platform | type | ecology | ecology_role
    """
    if not value:
        return value
    from config_rules import (
        PLATFORM_ALIASES, TYPE_ALIASES, ECOLOGY_ALIASES, ECOLOGY_ROLE_ALIASES
    )
    mapping = {
        "platform": PLATFORM_ALIASES,
        "type": TYPE_ALIASES,
        "ecology": ECOLOGY_ALIASES,
        "ecology_role": ECOLOGY_ROLE_ALIASES,
    }.get(field, {})
    key = value.strip().lower()
    return mapping.get(key, value)


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
        self.new_keys: set[str] = set()
        self.star_changes: dict[str, int] = {}
        self.classification_changes: dict[str, dict] = {}

    @staticmethod
    def needs_llm(key: str, existing, ai_db, force_refresh: bool, retry_failed: bool, llm_interval_days: int) -> bool:
        """判断项目是否需要 LLM 分析：独立增量策略，不受规则增量模式影响。
        提取为静态方法，供 Pipeline._enrich() 复用，避免重复实现筛选逻辑。"""
        if not existing:
            return True  # 新项目必须分析
        if existing.manual_override:
            return False  # 手动保护跳过
        if force_refresh:
            return True  # 强制刷新全部重分析

        # 从 AI 数据库查询上次分析状态
        ai_record = ai_db.get(key) if ai_db else None
        if retry_failed and ai_record and ai_record.llm_status == "failed":
            return True  # 重试之前失败的项目

        if not ai_record or not ai_record.analyzed_at:
            return True  # 从未分析过

        # 检查是否超过间隔天数
        from datetime import datetime, timezone, timedelta
        try:
            last_dt = datetime.fromisoformat(ai_record.analyzed_at)
            # 兼容无时区的旧时间戳
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - last_dt >= timedelta(days=llm_interval_days):
                return True  # 间隔已到，需要重新分析
        except Exception:
            return True  # 时间戳异常，重新分析

        return False  # 已有成功分析且在间隔内，跳过

    def process(self, config: EngineConfig) -> dict:
        log(f"处理模式: {'强制刷新' if config.force_refresh else '增量更新' if config.incremental else '标准更新'}", "STEP")

        self.llm_results: dict[str, dict] = {}
        llm_requested_keys: set[str] = set()
        if config.use_llm and self.llm:
            llm_candidates = []
            for item in config.items:
                key = f"{item['owner']['login']}/{item['name']}"
                existing = self.db.get(key)
                if self.needs_llm(key, existing, self.ai_db, config.force_refresh, config.retry_failed, config.llm_interval_days):
                    llm_candidates.append(item)
                    llm_requested_keys.add(key)

            if llm_candidates:
                max_rounds = 3
                for round_num in range(1, max_rounds + 1):
                    remaining = [item for item in llm_candidates
                                if f"{item['owner']['login']}/{item['name']}" not in self.llm_results]
                    if not remaining:
                        break

                    round_label = f"第 {round_num}/{max_rounds} 轮" if round_num > 1 else "第 1/3 轮"
                    round_results = self.llm.classify_batch(remaining, fallback=False, round_label=round_label)
                    self.llm_results.update(round_results)

                    # 记录本轮失败项到 AI DB
                    if self.ai_db:
                        for item in remaining:
                            key = f"{item['owner']['login']}/{item['name']}"
                            if key not in self.llm_results:
                                self.ai_db.update_from_llm_result(key, None, status="failed")

                # 最终统计
                total_requested = len(llm_candidates)
                total_success = len(self.llm_results)
                total_failed = total_requested - total_success
                if total_failed > 0:
                    log(f"LLM 最终: {total_success}/{total_requested} 成功, {total_failed}/{total_requested} 失败（已记录到 AI DB）", "WARN")
                else:
                    log(f"LLM 最终: {total_success}/{total_requested} 全部成功", "OK")

        for item in config.items:
            try:
                key = f"{item['owner']['login']}/{item['name']}"
                llm_result = self.llm_results.get(key)
                self._process_single(item, config, llm_result)
            except Exception as e:
                log(f"处理 {item.get('full_name', item.get('name'))} 失败: {e}", "ERROR")
                self.stats["error"] += 1

        return self.stats

    @staticmethod
    def _snapshot_classification(item) -> dict:
        """截取项目分类字段的快照，用于变更对比。item 必须为 StarItem（dict 直接传不入此方法）"""
        return {
            "platform": item.platform,
            "type": item.type,
            "ecology": item.ecology,
            "ecology_role": item.ecology_role,
        }

    def _record_classification_change(self, key: str, before, after) -> None:
        """记录分类字段变化，支持 dict 或 StarItem 作为 before/after"""
        old = before if isinstance(before, dict) else self._snapshot_classification(before)
        new = after if isinstance(after, dict) else self._snapshot_classification(after)
        changes = {}
        for field in ("platform", "type", "ecology", "ecology_role"):
            if old.get(field) != new.get(field):
                changes[field] = {"from": old.get(field), "to": new.get(field)}
        if changes:
            self.classification_changes[key] = changes

    @staticmethod
    def _apply_llm_override(target, llm_result: dict | None, existing_eco: str | None) -> dict:
        """根据 LLM 结果生成分类字段变更字典，不修改目标对象。
        返回: {"platform": ..., "type": ..., ...} 或空 dict（无变更时）"""
        changes: dict[str, str] = {}
        if not llm_result:
            return changes
        # P0 fix: confidence 可能为字符串，强制转换为 float
        raw_conf = llm_result.get("confidence", 0)
        try:
            confidence = float(raw_conf) if raw_conf is not None else 0.0
        except (ValueError, TypeError):
            confidence = 0.0
        if confidence < 0.8:
            return changes
        ecology_locked = existing_eco and _is_ecology_locked(existing_eco)
        # P1 fix: dict.get 值为 None 时返回 None，用 or 保证回退到原值
        new_platform = _normalize_field(llm_result.get("platform"), "platform")
        if new_platform and new_platform != target.platform:
            changes["platform"] = new_platform
        new_type = _normalize_field(llm_result.get("type"), "type")
        if new_type and new_type != target.type:
            changes["type"] = new_type
        if not ecology_locked:
            new_eco = _normalize_field(llm_result.get("ecology"), "ecology")
            if new_eco and new_eco != target.ecology:
                changes["ecology"] = new_eco
            new_role = _normalize_field(llm_result.get("ecology_role"), "ecology_role")
            if new_role and new_role != target.ecology_role:
                changes["ecology_role"] = new_role
        return changes

    def _replace_classification(self, key: str, item: dict, existing, config: EngineConfig, llm_result: dict | None, clear_override: bool = False) -> None:
        """重新分类已有项目并替换数据库中的记录。"""
        classification = self._classify_item(
            item, config.use_llm, llm_result, config.subscribe_all_releases, existing
        )
        classification.first_seen = existing.first_seen
        if clear_override:
            classification.manual_override = False
            classification.override_fields = []
            classification.override_rules_version = ""
        self._record_classification_change(key, existing, classification)
        self.db.set(key, classification)
        self.stats["updated"] += 1

    # ---------- P1-15: _process_single 策略拆分 ----------

    def _process_single(self, item: dict, config: EngineConfig, llm_result: dict | None = None) -> None:
        """调度器：根据项目状态选择处理策略（P1-15）。"""
        key = f"{item['owner']['login']}/{item['name']}"
        existing = self.db.get(key)

        if existing:
            if existing.manual_override:
                return self._process_protected(key, item, existing)

            self._track_star_change(key, item, existing)

            if config.force_refresh:
                return self._process_force_refresh(key, item, existing, config, llm_result)
            if config.incremental:
                return self._process_incremental(key, item, existing, config, llm_result)
            return self._process_standard_refresh(key, item, existing, config, llm_result)

        return self._process_new_item(key, item, config, llm_result)

    def _track_star_change(self, key: str, item: dict, existing) -> None:
        """记录 stars 增长（用于周报动态）。"""
        new_stars = item.get("stargazers_count", 0)
        if new_stars > existing.stars:
            self.star_changes[key] = new_stars - existing.stars

    def _process_protected(self, key: str, item: dict, existing) -> None:
        """策略：手动保护项目，只更新 stars 和 last_updated。"""
        existing.stars = item.get("stargazers_count", 0)
        existing.last_updated = item.get("pushed_at") or existing.last_updated
        self.stats["protected"] += 1

    def _process_force_refresh(self, key: str, item: dict, existing, config: EngineConfig, llm_result: dict | None) -> None:
        """策略：强制刷新，重新分类并清除 override 标记。"""
        self._replace_classification(key, item, existing, config, llm_result, clear_override=True)

    def _process_incremental(self, key: str, item: dict, existing, config: EngineConfig, llm_result: dict | None) -> None:
        """策略：增量更新，只更新元数据，应用 LLM 覆盖。"""
        existing.stars = item.get("stargazers_count", 0)
        existing.description = item.get("description") or ""
        existing.topics = item.get("topics", [])
        existing.last_updated = item.get("pushed_at") or existing.last_updated
        # 增量模式下规则分类跳过，但 LLM 覆盖仍然应用
        old_fields = self._snapshot_classification(existing)
        changes = self._apply_llm_override(existing, llm_result, existing.ecology)
        if changes:
            self.stats["llm_enhanced"] += 1
            for field, new_val in changes.items():
                setattr(existing, field, new_val)
        self._record_classification_change(key, old_fields, existing)
        self.stats["skipped"] += 1

    def _process_standard_refresh(self, key: str, item: dict, existing, config: EngineConfig, llm_result: dict | None) -> None:
        """策略：标准更新，重新分类已有项目。"""
        self._replace_classification(key, item, existing, config, llm_result)

    def _process_new_item(self, key: str, item: dict, config: EngineConfig, llm_result: dict | None) -> None:
        """策略：新项目，执行分类并入库。"""
        classification = self._classify_item(item, config.use_llm, llm_result, config.subscribe_all_releases)
        self.db.set(key, classification)
        self.new_keys.add(key)
        self.stats["new"] += 1

    def _classify_item(self, item: dict, use_llm: bool, llm_result: dict | None = None, subscribe_all_releases: bool = False, existing=None) -> StarItem:
        """对单个项目执行分类并返回 StarItem（AI 元数据不再写入 StarItem）。

        Args:
            existing: 已存在的 StarItem（避免重复查询数据库）
        """
        platform = self.rule.classify_platform(item)
        ptype = self.rule.classify_type(item)
        eco, role = self.rule.classify_ecology(item)
        language = item.get("language") or "文档 / 无代码"

        key = f"{item['owner']['login']}/{item['name']}"
        if existing is None:
            existing = self.db.get(key)
        existing_eco = existing.ecology if existing else None

        # 生态锁定：强制保留已有生态值
        if existing_eco and _is_ecology_locked(existing_eco):
            eco = existing_eco

        result = StarItem(
            full_name=key,
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
            last_updated=item.get("pushed_at") or datetime.now(timezone.utc).isoformat(),
            manual_override=False,
            override_fields=[],
            subscribe_releases=(existing.subscribe_releases if existing else False) or subscribe_all_releases,
            last_release_tag=existing.last_release_tag if existing else None,
            is_fork=item.get("fork", False),
        )

        # LLM 可以覆盖规则分类结果（分类决策本身是即时的，不依赖 AI DB）
        if use_llm and self.llm and llm_result:
            changes = self._apply_llm_override(result, llm_result, existing_eco)
            if changes:
                self.stats["llm_enhanced"] += 1
                for field, new_val in changes.items():
                    setattr(result, field, new_val)

        return result
