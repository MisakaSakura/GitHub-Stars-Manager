#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生态候选池管理：四级状态机 (candidate → watchlist → ai_reviewed → trusted)"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from utils import log


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
    ai_review: Optional[dict] = None
    rejected_reason: str = ""


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
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict) and raw.get("version") == self.VERSION:
                for name, data in raw.get("candidates", {}).items():
                    self.candidates[name] = EcologyCandidateState(**data)
            log(f"加载生态候选池: {len(self.candidates)} 个候选", "OK")
        except Exception as e:
            log(f"生态候选池加载失败，将重建: {e}", "WARN")
            self.candidates = {}

    def save(self) -> None:
        from utils import atomic_write

        def _write(f):
            json.dump({
                "version": self.VERSION,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "candidates": {k: asdict(v) for k, v in self.candidates.items()},
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

        # 2. 添加新发现的候选
        for cand in discovered:
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
                try:
                    last = datetime.fromisoformat(state.last_seen)
                    if (now - last).days > 30:
                        to_remove.append(name)
                except Exception:
                    pass
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
