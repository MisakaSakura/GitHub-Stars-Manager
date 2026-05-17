#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2: 反馈闭环 — 记录人工修正，统计高频模式，反哺规则优化"""

import json
import os
import pprint
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

from config_rules import ECOLOGY_STANDARD_NAMES, RULES_VERSION
from utils import log


class FeedbackLoop:
    """人工反馈记录与统计

    数据文件: data/feedback.json（随 data 分支持久化）
    """

    FEEDBACK_VERSION = 1

    def __init__(self, feedback_path: str):
        self.path = feedback_path
        self.entries: dict[str, dict] = {}
        self.patterns: dict[str, dict] = defaultdict(lambda: defaultdict(Counter))
        self.rules_version: str = ""
        self.load()

    @staticmethod
    def _current_rules_version() -> str:
        return RULES_VERSION

    @staticmethod
    def _get_rule_classification(rule, item_dict: dict) -> dict:
        """使用规则分类器获取项目的标准分类结果。"""
        eco, role = rule.classify_ecology(item_dict)
        return {
            "platform": rule.classify_platform(item_dict),
            "type": rule.classify_type(item_dict),
            "ecology": eco or "独立项目",
            "ecology_role": role or "其他 / Other",
        }

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and raw.get("version") == self.FEEDBACK_VERSION:
                    self.entries = raw.get("entries", {})
                    self.patterns = raw.get("patterns", {})
                    self.rules_version = raw.get("rules_version", "")
                else:
                    # 兼容旧格式或损坏文件
                    self.entries = {}
                    self.patterns = {}
                    self.rules_version = ""
                log(f"加载反馈数据: {len(self.entries)} 条记录", "OK")
            except Exception as e:
                log(f"反馈数据损坏，将重建: {e}", "WARN")
                self.entries = {}
                self.patterns = {}
                self.rules_version = ""
        else:
            log("反馈数据不存在，将创建")
            self.entries = {}
            self.patterns = {}
            self.rules_version = ""

    def save(self) -> None:
        from utils import atomic_write

        def _write(f):
            json.dump({
                "version": self.FEEDBACK_VERSION,
                "rules_version": self._current_rules_version(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "entries": self.entries,
                "patterns": self.patterns,
            }, f, ensure_ascii=False, indent=2)

        atomic_write(self.path, _write)

    def record(self, full_name: str, original: dict, corrected: dict,
               source: str = "manual", item_features: dict | None = None) -> bool:
        """记录一次人工修正。

        Args:
            item_features: 项目原始特征（name/topics/description/language），
                          用于生成有意义的 learned_rules blacklist/whitelist。
        """
        if not original or not corrected:
            return False

        # 只记录实际发生变化的字段
        changed = {}
        for field in ("platform", "type", "ecology", "ecology_role"):
            old = original.get(field)
            new = corrected.get(field)
            if old != new:
                changed[field] = {"from": old, "to": new}

        if not changed:
            return False

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original": original,
            "corrected": corrected,
            "source": source,
            "rules_version": self._current_rules_version(),
        }
        if item_features:
            entry["item_features"] = item_features

        self.entries[full_name] = entry

        # 更新模式统计
        for field, delta in changed.items():
            old_val = delta["from"]
            new_val = delta["to"]
            if field not in self.patterns:
                self.patterns[field] = {}
            if old_val not in self.patterns[field]:
                self.patterns[field][old_val] = {}
            if new_val not in self.patterns[field][old_val]:
                self.patterns[field][old_val][new_val] = 0
            self.patterns[field][old_val][new_val] += 1

        return True

    def get_correction(self, full_name: str) -> Optional[dict]:
        """查询某个项目的最新修正。
        如果 rules_version 与当前不一致，忽略 platform/type 修正（规则已变更），
        但保留 ecology/ecology_role 修正（生态规则未变）。
        """
        entry = self.entries.get(full_name)
        if not entry:
            return None

        corrected = dict(entry["corrected"])
        entry_version = entry.get("rules_version", "")
        current_version = self._current_rules_version()

        if entry_version and entry_version != current_version:
            # 规则版本不一致：platform/type 可能已失效，清空
            for field in ("platform", "type"):
                if field in corrected:
                    del corrected[field]
            if not corrected:
                return None

        return corrected

    def get_high_confidence_patterns(self, min_count: int = 3) -> dict:
        """获取高频修正模式（出现次数 >= min_count）"""
        result = {}
        for field, mapping in self.patterns.items():
            field_patterns = []
            for old_val, new_counter in mapping.items():
                for new_val, count in new_counter.items():
                    if count >= min_count:
                        field_patterns.append({
                            "from": old_val,
                            "to": new_val,
                            "count": count,
                            "confidence": min(count / 10, 1.0),
                        })
            if field_patterns:
                result[field] = sorted(field_patterns, key=lambda x: -x["count"])
        return result

    def generate_report(self) -> str:
        """生成反馈统计报告"""
        lines = [
            "## 📝 反馈闭环统计",
            "",
            f"累计记录 **{len(self.entries)}** 条人工修正。",
            "",
        ]

        patterns = self.get_high_confidence_patterns(min_count=2)
        if patterns:
            lines.append("### 高频修正模式（可用于优化规则）")
            lines.append("")
            for field, field_patterns in patterns.items():
                lines.append(f"**{field}**:")
                for p in field_patterns:
                    lines.append(f"- `{p['from']}` → `{p['to']}` （{p['count']} 次）")
                lines.append("")
        else:
            lines.append("> 暂无任何高频修正模式（需要至少 2 次相同修正才会显示）。")
            lines.append("> 在 `stars_db.json` 中手动修正分类并设置 `manual_override: true`，下次运行会自动记录。")
            lines.append("")

        if self.entries:
            lines.append("### 最近修正")
            lines.append("")
            recent = sorted(self.entries.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True)[:10]
            for full_name, entry in recent:
                changed = []
                for field in ("platform", "type", "ecology", "ecology_role"):
                    orig = entry["original"].get(field)
                    corr = entry["corrected"].get(field)
                    if orig != corr:
                        changed.append(f"{field}: {orig}→{corr}")
                lines.append(f"- **{full_name}** ({entry.get('timestamp', '')[:10]}): {', '.join(changed)}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _extract_features_from_evidence(items: list[dict]) -> dict:
        """从证据列表中提取高频特征。

        返回:
            {
                "topics": Counter({"topic": count, ...}),
                "desc_words": Counter({"word": count, ...}),
                "name_words": Counter({"word": count, ...}),
            }
        """
        import re

        topic_counter: Counter = Counter()
        desc_counter: Counter = Counter()
        name_counter: Counter = Counter()

        for item in items:
            features = item.get("item_features", {})
            # topics
            for t in features.get("topics", []):
                topic_counter[t.lower()] += 1
            # description 分词（简单空格/标点分割，过滤太短和纯数字的词）
            desc = features.get("description", "")
            for word in re.findall(r"[a-zA-Z一-鿿][a-zA-Z0-9一-鿿\-_/]*", desc):
                w = word.lower()
                if len(w) >= 3 and not w.isdigit():
                    desc_counter[w] += 1
            # name 分词
            name = features.get("name", "")
            for word in re.findall(r"[a-zA-Z一-鿿][a-zA-Z0-9一-鿿\-_/]*", name):
                w = word.lower()
                if len(w) >= 2 and not w.isdigit():
                    name_counter[w] += 1

        return {
            "topics": topic_counter,
            "desc_words": desc_counter,
            "name_words": name_counter,
        }

    def generate_learned_overrides(self, min_count: int = 3) -> dict:
        """分析反馈记录，生成自动规则补丁。

        返回格式:
        {
            "negative": {  # 否定规则：匹配这些特征的项目，排除指定生态
                "Docker": {
                    "topic_blacklist": ["music", "pdf"],
                    "desc_blacklist": ["privacy first", "小爱音箱"],
                    "evidence": 5,
                }
            },
            "positive": {  # 正向规则：匹配这些特征的项目，额外加分
                "Bilibili": {
                    "desc_boost": ["b 站体验"],
                    "evidence": 3,
                }
            }
        }
        """
        result = {"negative": {}, "positive": {}}

        # 1. 分析否定模式：原始生态 != 目标生态
        neg_evidence = defaultdict(list)  # eco_name -> [item_dict, ...]
        pos_evidence = defaultdict(list)  # eco_name -> [item_dict, ...]

        for full_name, entry in self.entries.items():
            corrected = entry.get("corrected", {})
            original = entry.get("original", {})
            old = original.get("ecology")
            new = corrected.get("ecology")
            if old and new and old != new:
                # 否定模式：old 生态被用户否定，改为 new
                evidence = {
                    "full_name": full_name,
                    "corrected_ecology": new,
                    "original_ecology": old,
                    "item_features": entry.get("item_features", {}),
                }
                neg_evidence[old].append(evidence)
                # 正向模式：new 生态被用户确认（从其他生态改过来的）
                if new != "独立项目":
                    pos_evidence[new].append(evidence)

        # 2. 生成否定规则
        for eco_name, items in neg_evidence.items():
            if len(items) < min_count:
                continue
            features = self._extract_features_from_evidence(items)
            result["negative"][eco_name] = {
                "topic_blacklist": [
                    t for t, c in features["topics"].items() if c >= min_count
                ],
                "desc_blacklist": [
                    w for w, c in features["desc_words"].items() if c >= min_count
                ],
                "name_blacklist": [
                    w for w, c in features["name_words"].items() if c >= min_count
                ],
                "evidence": len(items),
                "examples": [i["full_name"] for i in items[:5]],
            }

        # 3. 生成正向规则
        for eco_name, items in pos_evidence.items():
            if len(items) < min_count:
                continue
            features = self._extract_features_from_evidence(items)
            result["positive"][eco_name] = {
                "desc_boost": [
                    w for w, c in features["desc_words"].items() if c >= min_count
                ],
                "topic_boost": [
                    t for t, c in features["topics"].items() if c >= min_count
                ],
                "evidence": len(items),
                "examples": [i["full_name"] for i in items[:5]],
            }

        return result

    @staticmethod
    def write_learned_rules_file(path: str, learned: dict) -> None:
        """将学习到的规则写入 JSON 文件（RuleClassifier 读取）"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        # 统一使用 .json 扩展名
        if path.endswith(".py"):
            path = path[:-3] + ".json"
        elif not path.endswith(".json"):
            path += ".json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(learned, f, ensure_ascii=False, indent=2)

    def scan_manual_overrides(self, db) -> int:
        """扫描数据库中所有 manual_override=True 的项目，
        将其当前分类与规则分类结果对比，记录差异为人工修正。

        同时更新项目的 override_rules_version 为当前版本。
        """
        from rule_classifier import RuleClassifier

        count = 0
        rule = RuleClassifier()
        current_version = self._current_rules_version()

        def _update_version(item) -> None:
            if getattr(item, "override_rules_version", "") != current_version:
                item.override_rules_version = current_version

        def _record_if_changed(
            full_name: str, original: dict, corrected: dict, item
        ) -> bool:
            has_diff = any(corrected[f] != original.get(f) for f in corrected)
            if not has_diff:
                return False
            item_features = {
                "name": getattr(item, "name", ""),
                "description": getattr(item, "description", "") or "",
                "topics": list(getattr(item, "topics", [])) if getattr(item, "topics", None) else [],
                "language": getattr(item, "language", "") or "",
            }
            return self.record(
                full_name, original, corrected,
                source="auto_detect", item_features=item_features,
            )

        for full_name, item in db.items():
            if not item.manual_override:
                continue

            _update_version(item)

            current = {
                "platform": item.platform,
                "type": item.type,
                "ecology": item.ecology,
                "ecology_role": item.ecology_role,
            }

            last_entry = self.entries.get(full_name)
            if last_entry:
                if _record_if_changed(full_name, last_entry["corrected"], current, item):
                    count += 1
                continue

            item_dict = item.to_dict() if hasattr(item, "to_dict") else dict(item)
            original = self._get_rule_classification(rule, item_dict)
            if _record_if_changed(full_name, original, current, item):
                count += 1

        if count > 0:
            log(f"P2: 自动检测并记录 {count} 条人工修正到反馈系统", "OK")
        return count

    def detect_override_conflicts(self, db) -> list[dict]:
        """检测 manual_override 项目与新规则的潜在冲突。

        返回冲突列表，每项包含:
        - full_name: 项目名
        - current: 当前分类（用户覆盖后的）
        - rules_suggest: 当前规则建议的分类
        - conflicts: 冲突字段列表
        - rules_version: 设置 override 时的规则版本
        - is_version_mismatch: 规则版本是否不一致
        """
        from rule_classifier import RuleClassifier

        rule = RuleClassifier()
        current_version = self._current_rules_version()
        conflicts = []

        for full_name, item in db.items():
            if not item.manual_override:
                continue

            item_dict = item.to_dict() if hasattr(item, "to_dict") else dict(item)
            rules_suggest = self._get_rule_classification(rule, item_dict)

            current = {
                "platform": item.platform,
                "type": item.type,
                "ecology": item.ecology,
                "ecology_role": item.ecology_role,
            }

            conflict_fields = []
            for field in ("platform", "type", "ecology", "ecology_role"):
                if current[field] != rules_suggest[field]:
                    conflict_fields.append({
                        "field": field,
                        "current": current[field],
                        "rules_suggest": rules_suggest[field],
                    })

            if not conflict_fields:
                continue

            item_version = getattr(item, "override_rules_version", "")
            is_version_mismatch = bool(item_version and item_version != current_version)

            # 按严重程度排序：版本不一致 + platform/type 冲突最严重
            severity = "warn"
            if is_version_mismatch:
                pt_conflicts = [c for c in conflict_fields if c["field"] in ("platform", "type")]
                if pt_conflicts:
                    severity = "critical"
                else:
                    severity = "info"

            conflicts.append({
                "full_name": full_name,
                "current": current,
                "rules_suggest": rules_suggest,
                "conflict_fields": conflict_fields,
                "rules_version": item_version,
                "is_version_mismatch": is_version_mismatch,
                "severity": severity,
            })

        # 按严重程度排序
        severity_order = {"critical": 0, "warn": 1, "info": 2}
        conflicts.sort(key=lambda x: severity_order.get(x["severity"], 99))
        return conflicts

    def generate_conflict_report(self, conflicts: list[dict]) -> str:
        """生成 manual_override 冲突检测报告"""
        if not conflicts:
            return ""

        lines = [
            "## ⚠️ Manual Override 冲突检测",
            "",
            f"发现 **{len(conflicts)}** 个 manual_override 项目与当前规则存在差异。",
            "",
            "> **说明**：规则版本不一致时，platform/type 的覆盖可能已经过时，",
            "> 建议重新审查；ecology 的覆盖通常更稳定，可保留。",
            "",
        ]

        severity_groups = {
            "critical": ("### 🔴 严重（规则版本变更 + platform/type 冲突）", True),
            "warn": ("### 🟡 警告（规则一致但存在差异）", False),
            "info": ("### 🟢 提示（仅 ecology 差异，可忽略）", True),
        }
        grouped = {s: [c for c in conflicts if c["severity"] == s] for s in severity_groups}

        for sev, items in grouped.items():
            if not items:
                continue
            heading, show_version = severity_groups[sev]
            lines.append(heading)
            lines.append("")
            for c in items:
                version_note = f" (规则版本: `{c['rules_version'] or '未记录'}`)" if show_version else ""
                lines.append(f"- **{c['full_name']}**{version_note}")
                for f in c["conflict_fields"]:
                    lines.append(f"  - `{f['field']}`: `{f['current']}` → 规则建议: `{f['rules_suggest']}`")
            lines.append("")

        lines.append("### 处理建议")
        lines.append("")
        lines.append("```bash")
        lines.append("# 如需修正某个项目的分类")
        lines.append("python scripts/classifier.py --db data/stars_db.json --correct <full_name> --correct-platform <平台> --correct-type <类型>")
        lines.append("")
        lines.append("# 如需取消某个项目的 manual_override 并重新分类")
        lines.append("# 编辑 stars_db.json，将该项目的 manual_override 设为 false")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)
