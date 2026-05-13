#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fork 管理：检测 Fork 的上游更新"""

from datetime import datetime, timezone, timedelta

from base_tracker import BaseTracker
from utils import log


class ForkTracker(BaseTracker):
    """检测用户 Fork 仓库的上游更新"""

    def get_user_forks(self, username: str) -> list[dict]:
        """获取用户的所有 Fork 仓库"""
        repos = self.gh.get_user_repos(username, repo_type="owner")
        forks = [r for r in repos if r.get("fork")]
        log(f"发现 {len(forks)} 个 Fork 仓库", "OK")
        return forks

    def check(self, forks: list[dict], days: int = 7) -> list[dict]:
        """检查每个 Fork 的上游最近 N 天内是否有更新"""
        log("检查 Fork 上游更新...", "STEP")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        outdated = []
        for fork in forks:
            try:
                full_name = fork.get("full_name")
                if not full_name or "/" not in full_name:
                    continue
                owner, repo = full_name.split("/")
                detail = self.gh.get_repo_info(owner, repo)
                if not detail or not detail.get("parent"):
                    continue
                parent = detail["parent"]
                fork_pushed = fork.get("pushed_at") or detail.get("pushed_at")
                parent_pushed = parent.get("pushed_at")
                # 只检测最近 N 天内有更新的上游
                if (fork_pushed and parent_pushed and
                        parent_pushed > fork_pushed and
                        parent_pushed >= cutoff):
                    outdated.append({
                        "full_name": full_name,
                        "parent_full_name": parent.get("full_name"),
                        "parent_pushed_at": parent_pushed,
                    })
            except Exception as e:
                log(f"检查 {fork.get('full_name', '?')} 失败: {e}", "WARN")
        log(f"Fork 检查完成: {len(outdated)} 个仓库上游有更新", "OK")
        return outdated

    def format_report(self, updates: list[dict]) -> str:
        return self._truncate(updates, limit=10, title="🔱 Fork 上游更新提醒")

    def _format_item(self, item: dict) -> str:
        return f"  {item['full_name']} ← {item['parent_full_name']} (上游更新于 {item['parent_pushed_at'][:10]})"
