#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于规则的分类器 — P1 预分类增强版

增强点：
1. 平台/类型分类也利用 topics 字段（提升权重）
2. 模糊匹配：name 前缀/后缀匹配、topics 完全匹配增强
3. 生态角色判断增加 topics 独立权重
"""


class RuleClassifier:
    """基于关键词匹配的分类器，纯函数，无外部依赖"""

    # P1: topics 匹配的额外权重倍率
    TOPIC_WEIGHT_MULTIPLIER = 2
    # P1: name 前缀/后缀匹配的额外权重倍率
    NAME_PREFIX_WEIGHT = 3

    _learned_overrides: dict | None = None
    _auto_ecologies: dict | None = None
    _watchlist_rules: dict | None = None

    @classmethod
    def _load_watchlist_rules(cls, db_path: str = "") -> dict:
        """加载候选池中的 watchlist 规则（软应用）"""
        if cls._watchlist_rules is not None:
            return cls._watchlist_rules
        import os
        import json
        pool_path = os.path.join(os.path.dirname(__file__), "..", "data", "ecology_candidates.json")
        if db_path:
            pool_path = os.path.join(os.path.dirname(db_path), "ecology_candidates.json")
        pool_path = os.path.abspath(pool_path)
        if os.path.exists(pool_path):
            try:
                with open(pool_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                result = {}
                for name, data in raw.get("candidates", {}).items():
                    if data.get("status") == "watchlist":
                        result[name] = data.get("suggested_patterns", {})
                cls._watchlist_rules = result
            except Exception:
                cls._watchlist_rules = {}
        else:
            cls._watchlist_rules = {}
        return cls._watchlist_rules or {}

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
        import os
        # 尝试从 data 目录加载
        auto_path = os.path.join(os.path.dirname(__file__), "..", "data", "auto_ecologies.json")
        if db_path:
            auto_path = os.path.join(os.path.dirname(db_path), "auto_ecologies.json")
        auto_path = os.path.abspath(auto_path)
        if os.path.exists(auto_path):
            try:
                import json
                with open(auto_path, "r", encoding="utf-8") as f:
                    cls._auto_ecologies = json.load(f)
            except Exception:
                cls._auto_ecologies = {}
        else:
            cls._auto_ecologies = {}
        return cls._auto_ecologies or {}

    @staticmethod
    def _load_learned_overrides() -> dict:
        """延迟加载用户反馈生成的规则补丁"""
        import os
        import sys
        if RuleClassifier._learned_overrides is not None:
            return RuleClassifier._learned_overrides

        # 尝试从 data/learned_rules.py 加载
        learned_path = os.path.join(os.path.dirname(__file__), "..", "data", "learned_rules.py")
        learned_path = os.path.abspath(learned_path)
        if os.path.exists(learned_path):
            try:
                # 使用 import 机制加载
                import importlib.util
                spec = importlib.util.spec_from_file_location("learned_rules", learned_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                RuleClassifier._learned_overrides = getattr(mod, "LEARNED_OVERRIDES", {})
            except Exception:
                RuleClassifier._learned_overrides = {}
        else:
            RuleClassifier._learned_overrides = {}
        return RuleClassifier._learned_overrides

    @staticmethod
    def _apply_learned_overrides(eco_name: str, score: int, name: str, desc: str, topics: list[str]) -> int:
        """应用学习到的规则补丁（否定/正向规则）"""
        learned = RuleClassifier._load_learned_overrides()
        if not learned:
            return score

        # 否定规则：匹配黑名单特征的项目，直接排除该生态
        neg = learned.get("negative", {}).get(eco_name, {})
        if neg:
            for t in topics:
                if t in [p.lower() for p in neg.get("topic_blacklist", [])]:
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
            for p in pos.get("desc_boost", []):
                if p.lower() in desc:
                    score += 5
            for t in topics:
                if t in [p.lower() for p in pos.get("topic_boost", [])]:
                    score += 5

        return score

    @staticmethod
    def classify_platform(item: dict) -> str:
        return RuleClassifier._classify(item, "platform")

    @staticmethod
    def classify_type(item: dict) -> str:
        return RuleClassifier._classify(item, "type")

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
    def classify_ecology(item: dict) -> tuple[str | None, str | None]:
        from config_rules import ECOLOGY_RULES, ECOLOGY_ROLES

        name = item.get("name", "").lower()
        desc = (item.get("description") or "").lower()
        topics = [t.lower() for t in item.get("topics", [])]
        full_text = f"{name} {desc} {' '.join(topics)}"

        best_ecology = None
        best_score = 0

        # 合并代码内置规则、auto_ecologies.json 和 watchlist 规则
        all_rules = dict(ECOLOGY_RULES)
        auto_rules = RuleClassifier._load_auto_ecologies()
        if auto_rules:
            for eco_name, rules in auto_rules.items():
                if eco_name not in all_rules:
                    all_rules[eco_name] = rules
        watchlist_rules = RuleClassifier._load_watchlist_rules()
        if watchlist_rules:
            for eco_name, rules in watchlist_rules.items():
                if eco_name not in all_rules:
                    all_rules[eco_name] = rules

        for eco_name, rules in all_rules.items():
            score = 0
            # name 匹配：前缀/子串/核心项目
            for pattern in rules.get("name_patterns", []):
                pattern_lower = pattern.lower()
                if pattern_lower not in name:
                    continue
                cores = rules.get("core_projects", [])
                if any(name == c.lower() or name.endswith(f"-{c.lower()}") or name.startswith(f"{c.lower()}-") for c in cores):
                    score += 10
                elif name.startswith(pattern_lower) or name.endswith(pattern_lower):
                    # P1: 前缀/后缀匹配给予更高权重
                    score += RuleClassifier.NAME_PREFIX_WEIGHT
                else:
                    # 纯子串匹配：短 pattern（<=4字符）需要词边界，避免误匹配
                    if len(pattern_lower) <= 4:
                        if RuleClassifier._has_word_boundary(name, pattern_lower):
                            score += 5
                    else:
                        score += 5

            # desc 匹配
            for pattern in rules.get("desc_patterns", []):
                if pattern.lower() in desc:
                    score += 3

            # topic 匹配：完全匹配给予更高权重；短 pattern 子串匹配需词边界
            for pattern in rules.get("topic_patterns", []):
                pattern_lower = pattern.lower()
                if any(pattern_lower == t for t in topics):
                    # P1: topics 完全匹配权重更高
                    score += 4 * RuleClassifier.TOPIC_WEIGHT_MULTIPLIER
                else:
                    # 子串匹配：短 pattern（<=4字符）需要词边界，避免 "i3" 匹配 "winui3"
                    for t in topics:
                        if pattern_lower in t:
                            if len(pattern_lower) <= 4:
                                idx = t.find(pattern_lower)
                                before_ok = idx == 0 or not t[idx - 1].isalnum()
                                after_ok = idx + len(pattern_lower) == len(t) or not t[idx + len(pattern_lower)].isalnum()
                                if before_ok and after_ok:
                                    score += 4
                            else:
                                score += 4
                            break

            # related_types 在 name 中的匹配
            for rt in rules.get("related_types", []):
                if rt.lower() in name:
                    score += 2

            # 应用学习到的规则补丁（用户反馈自动生成的否定/正向规则）
            score = RuleClassifier._apply_learned_overrides(eco_name, score, name, desc, topics)

            if score > best_score:
                best_score = score
                best_ecology = eco_name

        if best_score < 3:
            return None, None

        best_role = "其他 / Other"
        best_role_score = 0
        for role_name, keywords in ECOLOGY_ROLES.items():
            role_score = 0
            for kw in keywords:
                kw_lower = kw.lower()
                # 在 full_text 中匹配
                if kw_lower in full_text:
                    role_score += 1
                # P1: topics 中完全匹配给予额外权重
                if any(kw_lower == t for t in topics):
                    role_score += 1
            if role_score > best_role_score:
                best_role_score = role_score
                best_role = role_name

        if best_ecology:
            cores = all_rules.get(best_ecology, {}).get("core_projects", [])
            if any(name == c.lower() for c in cores):
                best_role = "核心 / Core"

        return best_ecology, best_role

    @staticmethod
    def _classify(item: dict, rule_type: str) -> str:
        from config_rules import PLATFORM_RULES, TYPE_RULES
        rules = PLATFORM_RULES if rule_type == "platform" else TYPE_RULES
        name = item.get("name", "").lower()
        desc = (item.get("description") or "").lower()
        topics = [t.lower() for t in item.get("topics", [])]

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
