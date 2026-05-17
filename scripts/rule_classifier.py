#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于规则的分类器 — P1 预分类增强版

增强点：
1. 平台/类型分类也利用 topics 字段（提升权重）
2. 模糊匹配：name 前缀/后缀匹配、topics 完全匹配增强
3. 生态角色判断增加 topics 独立权重
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ItemFeatures:
    """项目特征的一次性提取，避免在多个分类方法中重复计算。"""

    name: str
    desc: str
    topics: tuple[str, ...]
    full_text: str

    @classmethod
    def from_item(cls, item: dict) -> ItemFeatures:
        name = item.get("name", "").lower()
        desc = (item.get("description") or "").lower()
        topics = tuple(t.lower() for t in item.get("topics", []))
        full_text = f"{name} {desc} {' '.join(topics)}"
        return cls(name, desc, topics, full_text)


class RuleClassifier:
    """基于关键词匹配的分类器，纯函数，无外部依赖"""

    # P1: topics 匹配的额外权重倍率
    TOPIC_WEIGHT_MULTIPLIER = 2
    # P1: name 前缀/后缀匹配的额外权重倍率
    NAME_PREFIX_WEIGHT = 3

    _learned_overrides: dict | None = None
    _auto_ecologies: dict | None = None
    _watchlist_rules: dict | None = None

    @staticmethod
    def _load_json(path: str) -> dict:
        """安全加载 JSON 文件，失败或不存在时返回空 dict。"""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def _resolve_data_path(filename: str, db_path: str = "") -> str:
        """构造 data 目录下的文件绝对路径。"""
        path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
        if db_path:
            path = os.path.join(os.path.dirname(db_path), filename)
        return os.path.abspath(path)

    @classmethod
    def _load_watchlist_rules(cls, db_path: str = "") -> dict:
        """加载候选池中的 watchlist 规则（软应用）"""
        if cls._watchlist_rules is not None:
            return cls._watchlist_rules

        raw = cls._load_json(cls._resolve_data_path("ecology_candidates.json", db_path))
        result = {}
        for name, data in raw.get("candidates", {}).items():
            if data.get("status") == "watchlist":
                result[name] = data.get("suggested_patterns", {})
        cls._watchlist_rules = result
        return result

    @classmethod
    def refresh_cache(cls) -> None:
        """强制刷新所有规则缓存（在每次运行前调用）"""
        cls._learned_overrides = None
        cls._auto_ecologies = None
        cls._watchlist_rules = None

    @classmethod
    def _load_auto_ecologies(cls, db_path: str = "") -> dict:
        """加载自动发现的生态规则（data/auto_ecologies.json）"""
        if cls._auto_ecologies is not None:
            return cls._auto_ecologies

        cls._auto_ecologies = cls._load_json(
            cls._resolve_data_path("auto_ecologies.json", db_path)
        )
        return cls._auto_ecologies

    @staticmethod
    def _load_learned_overrides() -> dict:
        """加载用户反馈生成的规则补丁。优先 JSON 格式，回退旧版 .py 格式。"""
        if RuleClassifier._learned_overrides is not None:
            return RuleClassifier._learned_overrides

        base = RuleClassifier._resolve_data_path("learned_rules")
        result = RuleClassifier._load_json(base + ".json")
        RuleClassifier._learned_overrides = result
        return result

    @staticmethod
    def _apply_learned_overrides(eco_name: str, score: int, name: str, desc: str, topics: list[str]) -> int:
        """应用学习到的规则补丁（否定/正向规则）"""
        learned = RuleClassifier._load_learned_overrides()
        if not learned:
            return score

        # 否定规则：匹配黑名单特征的项目，直接排除该生态
        neg = learned.get("negative", {}).get(eco_name, {})
        if neg:
            topic_blacklist = [p.lower() for p in neg.get("topic_blacklist", [])]
            for t in topics:
                if t in topic_blacklist:
                    return 0
            for p in neg.get("desc_blacklist", []):
                if p.lower() in desc:
                    return 0
            for p in neg.get("name_blacklist", []):
                if p.lower() in name:
                    return 0

        # 正向规则：匹配 boost 特征的项目，额外加分
        pos = learned.get("positive", {}).get(eco_name, {})
        if pos:
            topic_boost = [p.lower() for p in pos.get("topic_boost", [])]
            for p in pos.get("desc_boost", []):
                if p.lower() in desc:
                    score += 5
            for t in topics:
                if t in topic_boost:
                    score += 5

        return score

    @staticmethod
    def classify_platform(item: dict) -> str:
        features = ItemFeatures.from_item(item)
        return RuleClassifier._classify_features(features, "platform")

    @staticmethod
    def classify_type(item: dict) -> str:
        features = ItemFeatures.from_item(item)
        return RuleClassifier._classify_features(features, "type")

    @staticmethod
    def _has_word_boundary(text: str, pattern: str) -> bool:
        """检查 pattern 在 text 中是否以词边界形式出现（前后非字母数字或字符串边界）"""
        idx = text.find(pattern)
        if idx == -1:
            return False
        before_ok = idx == 0 or not text[idx - 1].isalnum()
        after_ok = idx + len(pattern) == len(text) or not text[idx + len(pattern)].isalnum()
        return before_ok and after_ok

    @staticmethod
    def _get_all_ecology_rules() -> dict:
        """合并代码内置规则、auto_ecologies.json 和 watchlist 规则。"""
        from config_rules import ECOLOGY_RULES

        all_rules = dict(ECOLOGY_RULES)
        auto_rules = RuleClassifier._load_auto_ecologies()
        for eco_name, rules in auto_rules.items():
            if eco_name not in all_rules:
                all_rules[eco_name] = rules
        watchlist_rules = RuleClassifier._load_watchlist_rules()
        for eco_name, rules in watchlist_rules.items():
            if eco_name not in all_rules:
                all_rules[eco_name] = rules
        return all_rules

    @staticmethod
    def _score_name(features: ItemFeatures, rules: dict) -> int:
        """根据 name 匹配计算分数。"""
        score = 0
        name = features.name
        for pattern in rules.get("name_patterns", []):
            pattern_lower = pattern.lower()
            if pattern_lower not in name:
                continue
            cores = rules.get("core_projects", [])
            if any(
                name == c.lower()
                or name.endswith(f"-{c.lower()}")
                or name.startswith(f"{c.lower()}-")
                for c in cores
            ):
                score += 10
            elif name.startswith(pattern_lower) or name.endswith(pattern_lower):
                score += RuleClassifier.NAME_PREFIX_WEIGHT
            else:
                # 纯子串匹配：短 pattern（<=4字符）需要词边界，避免误匹配
                if len(pattern_lower) <= 4:
                    if RuleClassifier._has_word_boundary(name, pattern_lower):
                        score += 5
                else:
                    score += 5
        return score

    @staticmethod
    def _score_desc(features: ItemFeatures, rules: dict) -> int:
        """根据 description 匹配计算分数。"""
        score = 0
        desc = features.desc
        for pattern in rules.get("desc_patterns", []):
            if pattern.lower() in desc:
                score += 3
        return score

    @staticmethod
    def _score_topics(features: ItemFeatures, rules: dict) -> int:
        """根据 topics 匹配计算分数。"""
        score = 0
        topics = features.topics
        for pattern in rules.get("topic_patterns", []):
            pattern_lower = pattern.lower()
            if any(pattern_lower == t for t in topics):
                score += 4 * RuleClassifier.TOPIC_WEIGHT_MULTIPLIER
                continue
            # 子串匹配：短 pattern（<=4字符）需要词边界，复用 _has_word_boundary
            for t in topics:
                if pattern_lower in t:
                    if len(pattern_lower) <= 4:
                        if RuleClassifier._has_word_boundary(t, pattern_lower):
                            score += 4
                    else:
                        score += 4
                    break
        return score

    @staticmethod
    def _score_related_types(features: ItemFeatures, rules: dict) -> int:
        """根据 related_types 在 name 中的匹配计算分数。"""
        score = 0
        name = features.name
        for rt in rules.get("related_types", []):
            if rt.lower() in name:
                score += 2
        return score

    @staticmethod
    def _find_best_ecology(features: ItemFeatures, all_rules: dict) -> tuple[str | None, int]:
        """遍历所有生态规则，找到匹配度最高的生态。"""
        best_ecology = None
        best_score = 0

        for eco_name, rules in all_rules.items():
            score = (
                RuleClassifier._score_name(features, rules)
                + RuleClassifier._score_desc(features, rules)
                + RuleClassifier._score_topics(features, rules)
                + RuleClassifier._score_related_types(features, rules)
            )
            score = RuleClassifier._apply_learned_overrides(
                eco_name, score, features.name, features.desc, list(features.topics)
            )
            if score > best_score:
                best_score = score
                best_ecology = eco_name

        return best_ecology, best_score

    @staticmethod
    def _find_best_role(features: ItemFeatures, best_ecology: str | None, all_rules: dict) -> str:
        """根据项目特征和最佳生态，确定生态角色。"""
        from config_rules import ECOLOGY_ROLES

        # 核心项目强制设为 "核心 / Core"
        if best_ecology:
            cores = all_rules.get(best_ecology, {}).get("core_projects", [])
            if any(features.name == c.lower() for c in cores):
                return "核心 / Core"

        best_role = "其他 / Other"
        best_role_score = 0
        full_text = features.full_text
        topics = features.topics

        for role_name, keywords in ECOLOGY_ROLES.items():
            role_score = 0
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in full_text:
                    role_score += 1
                if any(kw_lower == t for t in topics):
                    role_score += 1
            if role_score > best_role_score:
                best_role_score = role_score
                best_role = role_name

        return best_role

    @staticmethod
    def classify_ecology(item: dict) -> tuple[str | None, str | None]:
        """对项目执行生态分类，返回 (ecology, ecology_role) 元组。"""
        features = ItemFeatures.from_item(item)
        all_rules = RuleClassifier._get_all_ecology_rules()

        best_ecology, best_score = RuleClassifier._find_best_ecology(features, all_rules)
        if best_score < 3:
            return None, None

        best_role = RuleClassifier._find_best_role(features, best_ecology, all_rules)
        return best_ecology, best_role

    @staticmethod
    def _classify_features(features: ItemFeatures, rule_type: str) -> str:
        from config_rules import PLATFORM_RULES, TYPE_RULES

        rules = PLATFORM_RULES if rule_type == "platform" else TYPE_RULES
        name = features.name
        desc = features.desc
        topics = features.topics

        scores: dict[str, int] = {}
        for category, keywords in rules.items():
            score = 0
            for kw in keywords:
                kw_lower = kw.lower()
                # name 中匹配（前缀/子串）
                if kw_lower in name:
                    if name.startswith(kw_lower) or name.endswith(kw_lower):
                        score += RuleClassifier.NAME_PREFIX_WEIGHT
                    else:
                        score += 1
                # desc 中匹配
                if kw_lower in desc:
                    score += 1
                # P1: topics 中匹配（完全匹配权重更高）
                for t in topics:
                    if kw_lower == t:
                        score += RuleClassifier.TOPIC_WEIGHT_MULTIPLIER
                    elif kw_lower in t:
                        score += 1
            if score > 0:
                scores[category] = score

        return max(scores, key=scores.get) if scores else "其他 / 未分类"
