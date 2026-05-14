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

    @staticmethod
    def classify_platform(item: dict) -> str:
        return RuleClassifier._classify(item, "platform")

    @staticmethod
    def classify_type(item: dict) -> str:
        return RuleClassifier._classify(item, "type")

    @staticmethod
    def classify_ecology(item: dict) -> tuple[str | None, str | None]:
        from config_rules import ECOLOGY_RULES, ECOLOGY_ROLES

        name = item.get("name", "").lower()
        desc = (item.get("description") or "").lower()
        topics = [t.lower() for t in item.get("topics", [])]
        full_text = f"{name} {desc} {' '.join(topics)}"

        best_ecology = None
        best_score = 0

        for eco_name, rules in ECOLOGY_RULES.items():
            score = 0
            # name 匹配：前缀/子串/核心项目
            for pattern in rules.get("name_patterns", []):
                pattern_lower = pattern.lower()
                if pattern_lower in name:
                    cores = rules.get("core_projects", [])
                    if any(name == c.lower() or name.endswith(f"-{c.lower()}") or name.startswith(f"{c.lower()}-") for c in cores):
                        score += 10
                    elif name.startswith(pattern_lower) or name.endswith(pattern_lower):
                        # P1: 前缀/后缀匹配给予更高权重
                        score += RuleClassifier.NAME_PREFIX_WEIGHT
                    else:
                        score += 5

            # desc 匹配
            for pattern in rules.get("desc_patterns", []):
                if pattern.lower() in desc:
                    score += 3

            # topic 匹配：完全匹配给予更高权重
            for pattern in rules.get("topic_patterns", []):
                pattern_lower = pattern.lower()
                if any(pattern_lower == t for t in topics):
                    # P1: topics 完全匹配权重更高
                    score += 4 * RuleClassifier.TOPIC_WEIGHT_MULTIPLIER
                elif any(pattern_lower in t for t in topics):
                    score += 4

            # related_types 在 name 中的匹配
            for rt in rules.get("related_types", []):
                if rt.lower() in name:
                    score += 2

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
            cores = ECOLOGY_RULES[best_ecology].get("core_projects", [])
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
