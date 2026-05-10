#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于规则的分类器"""


class RuleClassifier:
    """基于关键词匹配的分类器，纯函数，无外部依赖"""

    @staticmethod
    def classify_platform(item: dict) -> str:
        return RuleClassifier._classify(item, "platform")

    @staticmethod
    def classify_type(item: dict) -> str:
        return RuleClassifier._classify(item, "type")

    @staticmethod
    def classify_ecology(item: dict) -> tuple[str | None, str | None]:
        from config import ECOLOGY_RULES, ECOLOGY_ROLES

        name = item.get("name", "").lower()
        desc = (item.get("description") or "").lower()
        topics = [t.lower() for t in item.get("topics", [])]
        full_text = f"{name} {desc} {' '.join(topics)}"

        best_ecology = None
        best_score = 0

        for eco_name, rules in ECOLOGY_RULES.items():
            score = 0
            for pattern in rules.get("name_patterns", []):
                if pattern.lower() in name:
                    cores = rules.get("core_projects", [])
                    if any(name == c.lower() or name.endswith(f"-{c.lower()}") or name.startswith(f"{c.lower()}-") for c in cores):
                        score += 10
                    else:
                        score += 5
            for pattern in rules.get("desc_patterns", []):
                if pattern.lower() in desc:
                    score += 3
            for pattern in rules.get("topic_patterns", []):
                if any(pattern.lower() in t for t in topics):
                    score += 4
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
            role_score = sum(1 for kw in keywords if kw.lower() in full_text)
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
        from config import PLATFORM_RULES, TYPE_RULES
        rules = PLATFORM_RULES if rule_type == "platform" else TYPE_RULES
        text = f"{item.get('name', '')} {item.get('description') or ''} {' '.join(item.get('topics', []))}".lower()
        scores: dict[str, int] = {}
        for category, keywords in rules.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                scores[category] = score
        return max(scores, key=scores.get) if scores else "其他 / 未分类"
