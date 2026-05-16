#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P4: 生态自动发现 — 扫描未被规则覆盖的项目，发现潜在的新生态候选"""

import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import List

from utils import log


@dataclass
class EcologyCandidate:
    """候选生态"""
    name: str
    indicator_type: str          # "name_prefix" | "topic_cluster" | "description_keyword"
    indicator_value: str         # 具体指标值
    project_count: int
    confidence: float            # 0.0 ~ 1.0
    examples: List[str]          # 示例项目 full_name
    suggested_patterns: dict     # 建议的规则配置


class EcologyDiscovery:
    """自动发现潜在生态，减少"独立项目"比例"""

    # 常见通用前缀，不应作为生态候选（如 "my-", "go-", "py-"）
    NOISE_PREFIXES = {
        "my", "go", "py", "js", "ts", "node", "java", "rust", "cpp", "c",
        "simple", "easy", "fast", "tiny", "mini", "micro", "nano",
        "super", "hyper", "ultra", "mega", "auto", "tool",
        "test", "demo", "example", "sample", "template", "lib",
        "api", "app", "web", "cli", "gui", "server", "client",
        "core", "base", "common", "util", "utils", "helper", "helpers",
        "plugin", "ext", "extension", "addon", "module", "package",
    }

    # 常见通用 topics，不应作为生态聚类依据
    NOISE_TOPICS = {
        "python", "javascript", "typescript", "java", "rust", "go", "cpp", "c",
        "html", "css", "shell", "dockerfile", "viml",
        "github", "opensource", "awesome", "tutorial", "example",
        "hacktoberfest", "good-first-issue", "help-wanted",
    }

    def __init__(self, db, ecology_rules: dict):
        self.db = db
        self.ecology_rules = ecology_rules
        self.existing_names = {name.lower() for name in ecology_rules.keys()}

    def _get_standalone_items(self) -> list[dict]:
        """获取所有未被归入已知生态的项目"""
        items = []
        for item in self.db.values():
            eco = item.ecology
            if eco in ("独立项目", "独立项目 / Standalone", None, ""):
                items.append(item.to_dict() if hasattr(item, "to_dict") else dict(item))
        return items

    def _is_noise_prefix(self, prefix: str) -> bool:
        return prefix.lower() in self.NOISE_PREFIXES or len(prefix) <= 2

    def _discover_by_name_prefix(self, items: list[dict], min_count: int = 3) -> List[EcologyCandidate]:
        """通过命名前缀发现生态"""
        prefix_counter = Counter()
        prefix_projects: dict[str, list[dict]] = {}

        for item in items:
            name = item.get("name", "")
            # 提取连字符/下划线/点号分隔的前缀
            for sep in "-_":
                if sep in name:
                    prefix = name.split(sep)[0].lower()
                    if not self._is_noise_prefix(prefix):
                        prefix_counter[prefix] += 1
                        prefix_projects.setdefault(prefix, []).append(item)

        candidates = []
        for prefix, count in prefix_counter.most_common(20):
            if count < min_count:
                continue
            projects = prefix_projects[prefix]
            examples = [p["full_name"] for p in projects[:5]]

            # 收集相关 topics
            all_topics = []
            for p in projects:
                all_topics.extend(p.get("topics", []))
            common_topics = [t for t, c in Counter(all_topics).most_common(5) if c >= 2]

            # 收集描述中的高频词
            all_desc_words = []
            for p in projects:
                desc = p.get("description", "") or ""
                words = re.findall(r'\b[a-z]{3,}\b|[一-鿿]{2,}', desc.lower())
                all_desc_words.extend(words)
            common_words = [w for w, c in Counter(all_desc_words).most_common(5) if c >= 2]

            confidence = min(count / 10.0, 1.0)
            candidates.append(EcologyCandidate(
                name=prefix.capitalize(),
                indicator_type="name_prefix",
                indicator_value=prefix,
                project_count=count,
                confidence=confidence,
                examples=examples,
                suggested_patterns={
                    "name_patterns": [prefix, f"{prefix}-", f"{prefix}_"],
                    "desc_patterns": common_words[:3],
                    "topic_patterns": common_topics[:3],
                    "related_types": [],
                    "core_projects": [p["name"] for p in projects if p["name"].lower() == prefix][:1],
                }
            ))

        return candidates

    def _discover_by_topic_cluster(self, items: list[dict], min_count: int = 3) -> List[EcologyCandidate]:
        """通过 topics 聚类发现生态"""
        # 找出每个项目的主导 topic（排除噪声）
        topic_groups: dict[str, list[dict]] = {}
        for item in items:
            topics = [t.lower() for t in item.get("topics", []) if t.lower() not in self.NOISE_TOPICS]
            if len(topics) >= 2:
                # 取最常见的两个 topics 作为聚类键
                for t in topics[:2]:
                    topic_groups.setdefault(t, []).append(item)

        candidates = []
        for topic, projects in sorted(topic_groups.items(), key=lambda x: -len(x[1]))[:15]:
            count = len(projects)
            if count < min_count:
                continue
            # 检查是否已有生态覆盖此 topic
            if topic in self.existing_names:
                continue

            examples = [p["full_name"] for p in projects[:5]]
            confidence = min(count / 10.0, 1.0)
            candidates.append(EcologyCandidate(
                name=topic.capitalize(),
                indicator_type="topic_cluster",
                indicator_value=topic,
                project_count=count,
                confidence=confidence,
                examples=examples,
                suggested_patterns={
                    "name_patterns": [],
                    "desc_patterns": [topic],
                    "topic_patterns": [topic],
                    "related_types": [],
                    "core_projects": [],
                }
            ))

        return candidates

    def discover(self, top_n: int = 10) -> List[EcologyCandidate]:
        """主入口：返回候选生态列表，按置信度排序"""
        standalone = self._get_standalone_items()
        if not standalone:
            log("没有独立项目，无需生态发现", "OK")
            return []

        log(f"P4: 扫描 {len(standalone)} 个独立项目，发现潜在生态...", "STEP")

        prefix_candidates = self._discover_by_name_prefix(standalone)
        topic_candidates = self._discover_by_topic_cluster(standalone)

        # 合并去重（按名称）
        seen = set()
        all_candidates = []
        for c in sorted(prefix_candidates + topic_candidates, key=lambda x: -x.confidence):
            name_lower = c.name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                all_candidates.append(c)

        result = all_candidates[:top_n]

        if result:
            log(f"P4: 发现 {len(result)} 个候选生态", "OK")
            for c in result:
                log(f"  [{c.indicator_type}] {c.name}: {c.project_count} 个项目 (置信度 {c.confidence:.1%})")
                log(f"    示例: {', '.join(c.examples[:3])}")
        else:
            log("P4: 未发现高置信度候选生态", "OK")

        return result

    def generate_report(self, candidates: List[EcologyCandidate]) -> str:
        """生成 Markdown 格式的生态发现报告"""
        if not candidates:
            return ""

        lines = [
            "## 🌱 生态自动发现报告",
            "",
            f"基于 {len(self._get_standalone_items())} 个独立项目的分析，发现以下潜在生态候选：",
            "",
        ]

        for c in candidates:
            lines.extend([
                f"### {c.name}",
                f"- **发现方式**: {c.indicator_type} (`{c.indicator_value}`)",
                f"- **项目数量**: {c.project_count}",
                f"- **置信度**: {c.confidence:.0%}",
                f"- **示例项目**: {', '.join(c.examples)}",
                f"- **建议规则配置**:",
                "```json",
                json.dumps(c.suggested_patterns, ensure_ascii=False, indent=2),
                "```",
                "",
            ])

        lines.extend([
            "---",
            "**说明**: 以上候选生态基于命名前缀和 topics 聚类自动发现。",
            "如需采纳，请复制 `suggested_patterns` 到 `scripts/config_rules.py` 的 `ECOLOGY_RULES` 中。",
            "",
        ])

        return "\n".join(lines)
