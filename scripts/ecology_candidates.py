#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生态候选池管理：四级状态机 (candidate → watchlist → ai_reviewed → trusted)"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

from config_rules import PLATFORM_RULES, TYPE_RULES
from utils import log, parse_iso


@dataclass
class EcologyCandidateState:
    """单个生态候选的完整状态"""
    status: str = "candidate"          # candidate | watchlist | ai_reviewed | trusted | expired | rejected
    first_seen: str = ""
    last_seen: str = ""
    appear_count: int = 0
    consecutive_runs: int = 0          # 连续出现的次数
    missed_runs: int = 0               # 连续缺失的次数
    confidence_history: list[float] = field(default_factory=list)
    project_count_history: list[int] = field(default_factory=list)
    suggested_patterns: dict = field(default_factory=dict)
    example_projects: set[str] = field(default_factory=set)  # 累积所有批次匹配到的项目
    ai_review: Optional[dict] = None
    rejected_reason: str = ""

    def to_dict(self) -> dict:
        # set 不能直接 JSON 序列化，转成 list
        result = {k: getattr(self, k) for k in self.__dataclass_fields__}
        result["example_projects"] = sorted(result["example_projects"])
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "EcologyCandidateState":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        # example_projects 从 list 恢复为 set
        if "example_projects" in filtered:
            filtered["example_projects"] = set(filtered["example_projects"])
        return cls(**filtered)


class EcologyCandidatePool:
    """生态候选池：持久化 + 状态流转管理"""

    VERSION = 1
    # 升级到 watchlist 所需的连续出现次数
    WATCHLIST_THRESHOLD = 3
    # 降级到 expired 所需的连续缺失次数
    EXPIRE_THRESHOLD = 5
    # watchlist 软应用的 score bonus
    WATCHLIST_BONUS = 2

    def __init__(self, pool_path: str):
        self.path = pool_path
        self.candidates: dict[str, EcologyCandidateState] = {}
        self.blocklist: set[str] = self._load_blocklist()
        # 仅手动 blocklist（ecology_blocklist.yaml），用于判断是否需要创建 issue
        self._manual_blocklist: set[str] = self._load_manual_blocklist()
        # 已创建 blocklist issue 的记录: {indicator: proposed_at}
        self._proposed_blocklist: dict[str, str] = {}
        self.load()
        # 初始化时清理已被 blocklist 的历史候选
        self._cleanup_blocklisted()

    @staticmethod
    def _load_blocklist() -> set[str]:
        """加载 blocklist： ecology_blocklist.yaml + 自动从规则推导"""
        from config_rules import PLATFORM_RULES, TYPE_RULES, ECOLOGY_STANDARD_NAMES, ECOLOGY_ALIASES
        from ecologies import ECOLOGY_RULES

        noise: set[str] = set()

        # 1. 从平台/类型/生态规则自动推导
        for keywords in PLATFORM_RULES.values():
            noise.update(k.lower() for k in keywords)
        for keywords in TYPE_RULES.values():
            noise.update(k.lower() for k in keywords)
        noise.update(name.lower() for name in ECOLOGY_RULES.keys())
        noise.update(name.lower() for name in ECOLOGY_STANDARD_NAMES)
        noise.update(k.lower() for k in ECOLOGY_ALIASES.keys())
        noise.update(v.lower() for v in ECOLOGY_ALIASES.values())

        # 2. 手动 blocklist
        blocklist_path = os.path.join(os.path.dirname(__file__), "ecology_blocklist.yaml")
        if os.path.exists(blocklist_path):
            try:
                import yaml
                with open(blocklist_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                noise.update(k.lower() for k in data.get("topics", []))
                noise.update(k.lower() for k in data.get("name_prefixes", []))
            except (OSError, yaml.YAMLError) as e:
                log(f"Blocklist 加载失败: {e}", "WARN")

        return noise

    @staticmethod
    def _load_manual_blocklist() -> set[str]:
        """仅加载手动 blocklist（ecology_blocklist.yaml），不包含自动推导。"""
        blocklist_path = os.path.join(os.path.dirname(__file__), "ecology_blocklist.yaml")
        noise: set[str] = set()
        if os.path.exists(blocklist_path):
            try:
                import yaml
                with open(blocklist_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                noise.update(k.lower() for k in data.get("topics", []))
                noise.update(k.lower() for k in data.get("name_prefixes", []))
            except (OSError, yaml.YAMLError) as e:
                log(f"手动 blocklist 加载失败: {e}", "WARN")
        return noise

    def _cleanup_blocklisted(self) -> None:
        """将已被 blocklist 的候选标记为 rejected"""
        for name, state in list(self.candidates.items()):
            if name.lower() in self.blocklist and state.status not in ("rejected", "expired"):
                state.status = "rejected"
                state.rejected_reason = "blocklist"
                log(f"  [{name}] 被 blocklist 排除，标记为 rejected", "OK")
        self.save()

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict) and raw.get("version") == self.VERSION:
                for name, data in raw.get("candidates", {}).items():
                    self.candidates[name] = EcologyCandidateState.from_dict(data)
                self._proposed_blocklist = raw.get("proposed_blocklist", {})
            log(f"加载生态候选池: {len(self.candidates)} 个候选", "OK")
        except json.JSONDecodeError as e:
            log(f"生态候选池 JSON 损坏: {e}", "WARN")
            self._reset_state()
        except OSError as e:
            log(f"生态候选池读取失败: {e}", "WARN")
            self._reset_state()

    def _reset_state(self) -> None:
        """重置候选池状态（加载失败时调用）。"""
        self.candidates = {}
        self._proposed_blocklist = {}

    def save(self) -> None:
        from utils import atomic_write

        def _write(f):
            json.dump({
                "version": self.VERSION,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "candidates": {k: v.to_dict() for k, v in self.candidates.items()},
                "proposed_blocklist": self._proposed_blocklist,
            }, f, ensure_ascii=False, indent=2)

        atomic_write(self.path, _write)

    def update_from_discovery(self, discovered: list) -> list[tuple[str, str, str]]:
        """
        根据本次生态发现结果更新候选池。
        返回状态变更列表: [(name, old_status, new_status), ...]
        """
        now = datetime.now(timezone.utc).isoformat()
        discovered_names = {c.name for c in discovered}
        changes: list[tuple[str, str, str]] = []

        # 1. 更新已存在的候选
        for name, state in self.candidates.items():
            old_status = state.status
            if name in discovered_names:
                # 本次被发现
                cand = next((c for c in discovered if c.name == name), None)
                if cand is None:
                    continue
                state.last_seen = now
                state.appear_count += 1
                state.consecutive_runs += 1
                state.missed_runs = 0
                state.confidence_history.append(round(cand.confidence, 2))
                state.project_count_history.append(cand.project_count)
                state.example_projects.update(cand.examples)
                # 保留最新 patterns
                state.suggested_patterns = cand.suggested_patterns

                # 状态流转
                new_status = self._transition(state)
                if new_status != old_status:
                    state.status = new_status
                    changes.append((name, old_status, new_status))
            else:
                # 本次未被发现
                state.missed_runs += 1
                state.consecutive_runs = 0
                if state.status == "watchlist" and state.missed_runs >= self.EXPIRE_THRESHOLD:
                    state.status = "expired"
                    changes.append((name, old_status, "expired"))

        # 2. 添加新发现的候选（blocklist 中的直接拒绝）
        for cand in discovered:
            if cand.name.lower() in self.blocklist:
                if cand.name not in self.candidates:
                    self.candidates[cand.name] = EcologyCandidateState(
                        status="rejected",
                        first_seen=now,
                        last_seen=now,
                        appear_count=1,
                        rejected_reason="blocklist",
                    )
                    log(f"  [{cand.name}] 新发现但被 blocklist 排除，直接标记为 rejected", "OK")
                continue
            if cand.name not in self.candidates:
                self.candidates[cand.name] = EcologyCandidateState(
                    status="candidate",
                    first_seen=now,
                    last_seen=now,
                    appear_count=1,
                    consecutive_runs=1,
                    missed_runs=0,
                    confidence_history=[round(cand.confidence, 2)],
                    project_count_history=[cand.project_count],
                    suggested_patterns=cand.suggested_patterns,
                    example_projects=set(cand.examples),
                )

        # 3. 清理过期候选
        self._cleanup_expired()

        if changes:
            for name, old, new in changes:
                log(f"  [{name}] {old} → {new}", "OK" if new in ("watchlist", "ai_reviewed", "trusted") else "WARN")

        self.save()
        return changes

    def _transition(self, state: EcologyCandidateState) -> str:
        """根据当前状态判断是否需要升级/降级"""
        current = state.status

        if current == "candidate":
            if state.consecutive_runs >= self.WATCHLIST_THRESHOLD:
                latest_conf = state.confidence_history[-1] if state.confidence_history else 0
                if latest_conf >= 0.5:
                    return "watchlist"

        elif current == "watchlist":
            # watchlist 不会自动升级到 ai_reviewed，需要 LLM 审查
            pass

        elif current == "ai_reviewed":
            # AI 审查通过后连续 2 次稳定才升级到 trusted
            if state.consecutive_runs >= 2:
                return "trusted"

        return current

    def _cleanup_expired(self) -> None:
        """删除过期超过 30 天的候选"""
        now = datetime.now(timezone.utc)
        to_remove = []
        for name, state in self.candidates.items():
            if state.status == "expired":
                last = parse_iso(state.last_seen)
                if last and (now - last).days > 30:
                    to_remove.append(name)
        for name in to_remove:
            del self.candidates[name]
            log(f"  [{name}] 过期超过30天，已从候选池移除", "OK")

    def get_watchlist_rules(self) -> dict:
        """获取 watchlist 状态的候选规则（用于软应用）"""
        result = {}
        for name, state in self.candidates.items():
            if state.status == "watchlist":
                result[name] = state.suggested_patterns
        return result

    def get_trusted_rules(self) -> dict:
        """获取 trusted 状态的候选规则（用于全量应用）"""
        result = {}
        for name, state in self.candidates.items():
            if state.status == "trusted":
                result[name] = state.suggested_patterns
        return result

    def get_all_active_rules(self) -> dict:
        """获取 watchlist + trusted 的所有规则（用于分类器合并）"""
        result = {}
        for name, state in self.candidates.items():
            if state.status in ("watchlist", "trusted"):
                result[name] = state.suggested_patterns
        return result

    def mark_ai_reviewed(self, name: str, approved: bool, llm_confidence: float, reason: str) -> bool:
        """标记 LLM 审查结果"""
        state = self.candidates.get(name)
        if not state or state.status != "watchlist":
            return False

        now = datetime.now(timezone.utc).isoformat()
        state.ai_review = {
            "reviewed_at": now,
            "approved": approved,
            "llm_confidence": llm_confidence,
            "llm_reason": reason,
        }

        if approved and llm_confidence >= 0.85:
            state.status = "ai_reviewed"
            state.consecutive_runs = 0  # 重置，需要再稳定 2 次才到 trusted
            log(f"  [{name}] LLM 审查通过 ({llm_confidence:.0%})，升级为 ai_reviewed", "OK")
        else:
            state.status = "candidate"
            state.consecutive_runs = 0
            log(f"  [{name}] LLM 审查未通过 ({llm_confidence:.0%})，退回 candidate", "WARN")

        self.save()
        return True

    def generate_summary(self) -> list[dict]:
        """生成候选池摘要，用于周报展示"""
        result = []
        for name, state in self.candidates.items():
            if state.status in ("expired", "rejected"):
                continue
            latest_conf = state.confidence_history[-1] if state.confidence_history else 0
            latest_count = state.project_count_history[-1] if state.project_count_history else 0
            progress = ""
            if state.status == "candidate":
                progress = f"需再观察 {self.WATCHLIST_THRESHOLD - state.consecutive_runs} 次"
            elif state.status == "watchlist":
                progress = "等待 LLM 审查"
            elif state.status == "ai_reviewed":
                progress = f"再稳定 {2 - state.consecutive_runs} 次即可生效"
            elif state.status == "trusted":
                progress = "已生效"

            result.append({
                "name": name,
                "status": state.status,
                "count": latest_count,
                "confidence": latest_conf,
                "progress": progress,
                "consecutive": state.consecutive_runs,
            })
        return sorted(result, key=lambda x: (-x["confidence"], -x["count"]))

    def get_blocklist_proposals(self) -> list[dict]:
        """检查候选池中应加入 blocklist 但尚未 blocklist 的项，返回提议列表。

        触发条件（同时满足）：
        1. 候选状态为 candidate 或 watchlist
        2. 出现次数 >= 3（排除偶发噪声）
        3. 候选名或 topic 命中 PLATFORM_RULES / TYPE_RULES 等已确认噪声源
        4. 该 indicator 当前不在 blocklist 中
        5. 过去 7 天内未对同一 indicator 创建过 issue
        """
        proposals: list[dict] = []
        now = datetime.now(timezone.utc)

        # 构建已确认噪声关键词集合（除手动 blocklist 外）
        noise_keywords: set[str] = set()
        for keywords in PLATFORM_RULES.values():
            noise_keywords.update(k.lower() for k in keywords)
        for keywords in TYPE_RULES.values():
            noise_keywords.update(k.lower() for k in keywords)

        for name, state in self.candidates.items():
            if state.status not in ("candidate", "watchlist"):
                continue
            if state.appear_count < 3:
                continue

            name_lower = name.lower()

            # 检查候选名本身是否在噪声列表中
            if name_lower in noise_keywords and name_lower not in self._manual_blocklist:
                if not self._was_recently_proposed(name_lower):
                    proposals.append({
                        "indicator": name,
                        "indicator_type": "topic",
                        "candidate_name": name,
                        "appear_count": state.appear_count,
                        "project_count": state.project_count_history[-1] if state.project_count_history else 0,
                        "example_projects": sorted(state.example_projects),
                        "reason": f"'{name}' 属于平台/类型关键词，不应被识别为独立生态",
                    })
                continue

            # 检查 topic_patterns 中是否有噪声关键词
            patterns = state.suggested_patterns or {}
            for topic in patterns.get("topic_patterns", []):
                topic_lower = topic.lower()
                if topic_lower in noise_keywords and topic_lower not in self._manual_blocklist:
                    if not self._was_recently_proposed(topic_lower):
                        proposals.append({
                            "indicator": topic,
                            "indicator_type": "topic",
                            "candidate_name": name,
                            "appear_count": state.appear_count,
                            "project_count": state.project_count_history[-1] if state.project_count_history else 0,
                        "example_projects": sorted(state.example_projects),
                            "reason": f"'{topic}' 属于平台/类型关键词，不应被识别为独立生态",
                        })

            # 检查 name_prefixes 中的通用前缀
            for prefix in patterns.get("name_patterns", []):
                prefix_lower = prefix.lower()
                if prefix_lower in {"go", "py", "js", "my", "simple", "test", "mini"} and prefix_lower not in self._manual_blocklist:
                    if not self._was_recently_proposed(prefix_lower):
                        proposals.append({
                            "indicator": prefix,
                            "indicator_type": "name_prefix",
                            "candidate_name": name,
                            "appear_count": state.appear_count,
                            "project_count": state.project_count_history[-1] if state.project_count_history else 0,
                        "example_projects": sorted(state.example_projects),
                            "reason": f"'{prefix}' 是常见通用前缀，不应被识别为独立生态",
                        })

        return proposals

    def _was_recently_proposed(self, indicator: str, days: int = 7) -> bool:
        """检查 indicator 是否在指定天数内已提议过 blocklist。"""
        proposed_at = self._proposed_blocklist.get(indicator.lower())
        if not proposed_at:
            return False
        dt = parse_iso(proposed_at)
        if dt and (datetime.now(timezone.utc) - dt).days < days:
            return True
        return False

    def record_blocklist_proposal(self, indicator: str) -> None:
        """记录已创建的 blocklist issue，防止重复。"""
        self._proposed_blocklist[indicator.lower()] = datetime.now(timezone.utc).isoformat()
