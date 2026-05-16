#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2: 反馈闭环 — 记录人工修正，统计高频模式，反哺规则优化"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

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
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and raw.get("version") == self.FEEDBACK_VERSION:
                    self.entries = raw.get("entries", {})
                    self.patterns = raw.get("patterns", {})
                else:
                    # 兼容旧格式或损坏文件
                    self.entries = {}
                    self.patterns = {}
                log(f"加载反馈数据: {len(self.entries)} 条记录", "OK")
            except Exception as e:
                log(f"反馈数据损坏，将重建: {e}", "WARN")
                self.entries = {}
                self.patterns = {}
        else:
            log("反馈数据不存在，将创建")
            self.entries = {}
            self.patterns = {}

    def save(self) -> None:
        from utils import atomic_write

        def _write(f):
            json.dump({
                "version": self.FEEDBACK_VERSION,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "entries": self.entries,
                "patterns": self.patterns,
            }, f, ensure_ascii=False, indent=2)

        atomic_write(self.path, _write)

    def record(self, full_name: str, original: dict, corrected: dict, source: str = "manual") -> bool:
        """记录一次人工修正"""
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

        self.entries[full_name] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original": original,
            "corrected": corrected,
            "source": source,
        }

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
        """查询某个项目的最新修正"""
        entry = self.entries.get(full_name)
        if entry:
            return entry["corrected"]
        return None

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
        from collections import defaultdict
        from config_rules import ECOLOGY_STANDARD_NAMES

        result = {"negative": {}, "positive": {}}

        # 1. 分析否定模式：原始生态 != 目标生态（且目标为 Standalone 或其他生态）
        # 收集每个 (原始生态) 被否定项目的共同特征
        neg_evidence = defaultdict(list)  # eco_name -> [item_dict, ...]
        pos_evidence = defaultdict(list)  # eco_name -> [item_dict, ...]

        for full_name, entry in self.entries.items():
            corrected = entry.get("corrected", {})
            original = entry.get("original", {})
            for field in ("ecology",):
                old = original.get(field)
                new = corrected.get(field)
                if old and new and old != new:
                    # 否定模式：old 生态被用户否定，改为 new
                    neg_evidence[old].append({
                        "full_name": full_name,
                        "corrected_ecology": new,
                        "original_ecology": old,
                    })
                    # 正向模式：new 生态被用户确认（从其他生态改过来的）
                    if new != "独立项目 / Standalone" and new != "独立项目":
                        pos_evidence[new].append({
                            "full_name": full_name,
                            "original_ecology": old,
                        })

        # 2. 生成否定规则：需要 min_count 次相同"原始生态被否定"的反馈
        for eco_name, items in neg_evidence.items():
            if len(items) < min_count:
                continue
            # 提取共同特征（从反馈条目中寻找 topics/desc 关键词）
            # 由于没有存储原始项目的 topics/desc，我们只能从 full_name 推断
            # 或者依赖外部传入 db
            result["negative"][eco_name] = {
                "topic_blacklist": [],
                "desc_blacklist": [],
                "name_blacklist": [],
                "evidence": len(items),
                "examples": [i["full_name"] for i in items[:5]],
            }

        # 3. 生成正向规则
        for eco_name, items in pos_evidence.items():
            if len(items) < min_count:
                continue
            result["positive"][eco_name] = {
                "desc_boost": [],
                "topic_boost": [],
                "evidence": len(items),
                "examples": [i["full_name"] for i in items[:5]],
            }

        return result

    @staticmethod
    def write_learned_rules_file(path: str, learned: dict) -> None:
        """将学习到的规则写入 Python 文件（便于 RuleClassifier 直接 import）"""
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        lines = [
            '#!/usr/bin/env python3',
            '# -*- coding: utf-8 -*-',
            '"""自动生成的规则补丁 —— 由 feedback_loop.py 根据用户反馈自动维护',
            '',
            '生成时间: {}',
            '数据来源: data/feedback.json',
            '更新触发: 每次 --correct 修正或 scan_manual_overrides 检测到新差异时',
            '',
            '注意：此文件为机器生成，不建议手动编辑。需要调整时，',
            '      直接在 stars_db.json 中修正分类并设置 manual_override=true，',
            '      下次运行会自动重新生成。',
            '"""',
            '',
            'LEARNED_OVERRIDES = {}',
            '',
        ]

        import json, datetime
        content = json.dumps(learned, ensure_ascii=False, indent=4)
        # 将 JSON 转为 Python dict 字面量格式
        content = content.replace('"', '"').replace('true', 'True').replace('false', 'False').replace('null', 'None')
        lines[8] = lines[8].format(datetime.datetime.now(datetime.timezone.utc).isoformat())
        lines[10] = f"LEARNED_OVERRIDES = {content}"

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def scan_manual_overrides(self, db) -> int:
        """扫描数据库中所有 manual_override=True 的项目，
        将其当前分类与规则分类结果对比，记录差异为人工修正。

        这是 P2 的核心检测逻辑：用户在本地手动修改了分类并设置
        manual_override=true，下次运行时会自动检测到差异并记录。
        """
        from rule_classifier import RuleClassifier

        count = 0
        rule = RuleClassifier()

        for full_name, item in db.items():
            if not item.manual_override:
                continue

            # 当前分类（用户手动修正后的结果）
            current = {
                "platform": item.platform,
                "type": item.type,
                "ecology": item.ecology,
                "ecology_role": item.ecology_role,
            }

            # 查询是否已有反馈记录
            last_entry = self.entries.get(full_name)
            if last_entry:
                last_corrected = last_entry["corrected"]
                # 如果当前分类与上次记录的不同，说明用户又修改了
                has_new_changes = any(
                    current[f] != last_corrected.get(f)
                    for f in current
                )
                if has_new_changes:
                    if self.record(full_name, last_corrected, current, source="auto_detect"):
                        count += 1
                continue

            # 首次记录：用规则重新分类作为 original
            item_dict = item.to_dict() if hasattr(item, "to_dict") else dict(item)
            original = {
                "platform": rule.classify_platform(item_dict),
                "type": rule.classify_type(item_dict),
                "ecology": rule.classify_ecology(item_dict)[0] or "独立项目 / Standalone",
                "ecology_role": rule.classify_ecology(item_dict)[1] or "其他 / Other",
            }

            has_diff = any(current[f] != original[f] for f in current)
            if has_diff:
                if self.record(full_name, original, current, source="auto_detect"):
                    count += 1

        if count > 0:
            log(f"P2: 自动检测并记录 {count} 条人工修正到反馈系统", "OK")
        return count
