#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3: 一致性自检 — 扫描数据库，发现分类矛盾或异常的项目"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List

from utils import log


@dataclass
class ConsistencyIssue:
    """单个一致性异常"""
    full_name: str
    issue_type: str           # "ecology_mismatch" | "isolated_ecology" | "dominant_other" | "platform_outlier"
    ecology: str
    current: dict
    expected: str | dict | None = None
    confidence: float = 0.0   # 异常置信度
    reason: str = ""


class ConsistencyChecker:
    """分类一致性检查器"""

    # 同一生态内，某 platform/type 占比超过此阈值时，不同值视为异常
    DOMINANT_THRESHOLD = 0.6
    # 最小样本数才进行一致性检查
    MIN_SAMPLE_SIZE = 3

    def __init__(self, db):
        self.db = db
        self.issues: List[ConsistencyIssue] = []

    def _group_by_ecology(self) -> dict[str, list[dict]]:
        """按生态分组"""
        groups = defaultdict(list)
        for item in self.db.values():
            d = item.to_dict() if hasattr(item, "to_dict") else dict(item)
            eco = d.get("ecology", "独立项目")
            groups[eco].append(d)
        return groups

    def check(self) -> List[ConsistencyIssue]:
        """执行全量一致性检查"""
        self.issues = []
        groups = self._group_by_ecology()

        for eco, items in groups.items():
            if eco == "独立项目":
                continue
            self._check_ecology_consistency(eco, items)

        # 孤立生态检查（只有1个项目的生态）
        for eco, items in groups.items():
            if eco != "独立项目" and len(items) == 1:
                self.issues.append(ConsistencyIssue(
                    full_name=items[0]["full_name"],
                    issue_type="isolated_ecology",
                    ecology=eco,
                    current={"platform": items[0].get("platform"), "type": items[0].get("type")},
                    expected=None,
                    confidence=0.3,
                    reason=f"生态 '{eco}' 只有 1 个项目，可能是误判"
                ))

        # 生态角色"其他"占比过高的生态
        for eco, items in groups.items():
            if eco == "独立项目" or len(items) < self.MIN_SAMPLE_SIZE:
                continue
            other_count = sum(1 for i in items if i.get("ecology_role") == "其他 / Other")
            ratio = other_count / len(items)
            if ratio > 0.7:
                examples = [i["full_name"] for i in items if i.get("ecology_role") == "其他 / Other"][:3]
                self.issues.append(ConsistencyIssue(
                    full_name=examples[0] if examples else items[0]["full_name"],
                    issue_type="dominant_other",
                    ecology=eco,
                    current={"role_other_ratio": f"{ratio:.0%}"},
                    expected=None,
                    confidence=ratio,
                    reason=f"生态 '{eco}' 中 {ratio:.0%} 的项目角色为'其他'，建议补充角色规则"
                ))

        log(f"P3: 一致性自检完成，发现 {len(self.issues)} 处异常", "OK" if not self.issues else "WARN")
        return self.issues

    def _check_ecology_consistency(self, eco: str, items: list[dict]) -> None:
        """检查单个生态内部的分类一致性"""
        if len(items) < self.MIN_SAMPLE_SIZE:
            return

        # platform 分布
        platforms = Counter(i.get("platform", "其他 / 未分类") for i in items)
        dominant_platform, dominant_p_count = platforms.most_common(1)[0]
        p_ratio = dominant_p_count / len(items)

        # type 分布
        types = Counter(i.get("type", "其他 / 未分类") for i in items)
        dominant_type, dominant_t_count = types.most_common(1)[0]
        t_ratio = dominant_t_count / len(items)

        for item in items:
            platform = item.get("platform", "其他 / 未分类")
            ptype = item.get("type", "其他 / 未分类")

            # platform 异常
            if p_ratio >= self.DOMINANT_THRESHOLD and platform != dominant_platform:
                self.issues.append(ConsistencyIssue(
                    full_name=item["full_name"],
                    issue_type="platform_outlier",
                    ecology=eco,
                    current={"platform": platform, "type": ptype},
                    expected={"platform": dominant_platform},
                    confidence=p_ratio,
                    reason=f"生态 '{eco}' 中 {p_ratio:.0%} 为 '{dominant_platform}'，此项目却是 '{platform}'"
                ))

            # type 异常
            if t_ratio >= self.DOMINANT_THRESHOLD and ptype != dominant_type:
                self.issues.append(ConsistencyIssue(
                    full_name=item["full_name"],
                    issue_type="type_outlier",
                    ecology=eco,
                    current={"platform": platform, "type": ptype},
                    expected={"type": dominant_type},
                    confidence=t_ratio,
                    reason=f"生态 '{eco}' 中 {t_ratio:.0%} 为 '{dominant_type}'，此项目却是 '{ptype}'"
                ))

    def generate_report(self) -> str:
        """生成 Markdown 格式的一致性报告"""
        if not self.issues:
            return "## ✅ 一致性自检报告\n\n所有生态分类一致，未发现异常。\n"

        lines = [
            "## ⚠️ 一致性自检报告",
            "",
            f"发现 **{len(self.issues)}** 处潜在分类异常，建议人工复核：",
            "",
        ]

        # 按类型分组
        by_type = defaultdict(list)
        for issue in self.issues:
            by_type[issue.issue_type].append(issue)

        type_labels = {
            "platform_outlier": "🎯 Platform 异常",
            "type_outlier": "📦 Type 异常",
            "isolated_ecology": "🌱 孤立生态",
            "dominant_other": "❓ 角色未明确",
        }

        for issue_type, issues in sorted(by_type.items()):
            label = type_labels.get(issue_type, issue_type)
            lines.append(f"### {label} ({len(issues)})")
            lines.append("")
            for issue in issues:
                lines.append(f"- **{issue.full_name}** | {issue.ecology}")
                lines.append(f"  - 当前: {issue.current}")
                if issue.expected:
                    lines.append(f"  - 建议: {issue.expected}")
                lines.append(f"  - 原因: {issue.reason}")
                lines.append("")

        lines.extend([
            "---",
            "**处理建议**: 对确认有误的项目，在 `stars_db.json` 中手动修正并设置 `manual_override: true`。",
            "修正后下次运行会自动记录到反馈系统，用于优化规则。",
            "",
        ])

        return "\n".join(lines)
