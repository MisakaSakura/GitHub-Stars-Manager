#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release 追踪：检测仓库新 Release"""

from datetime import datetime, timezone

from base_tracker import BaseTracker
from utils import log


class ReleaseTracker(BaseTracker):
    """检查仓库新 Release，支持订阅制和全量检查两种模式"""

    def check(self, db_items: list[dict]) -> list[dict]:
        """订阅制检查：只检查 subscribe_releases=true 的项目（向后兼容）"""
        candidates = [item for item in db_items if item.get("subscribe_releases")]
        return self._check_candidates(candidates, baseline_mode=False)

    def check_all(self, db_items: list[dict]) -> list[dict]:
        """全量检查：对所有项目检查 Release，新项目设为 baseline 不通知"""
        return self._check_candidates(db_items, baseline_mode=True)

    def _check_candidates(self, db_items: list[dict], baseline_mode: bool) -> list[dict]:
        updates: list[dict] = []
        mode_label = "全量" if baseline_mode else "订阅"
        log(f"检查 Release 更新 ({mode_label})...", "STEP")
        from datetime import datetime, timezone, timedelta
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        for item in db_items:
            try:
                owner, repo = item["full_name"].split("/")
                releases = self.gh.list_releases(owner, repo, per_page=30)
                if not releases:
                    continue

                current_tag = item.get("last_release_tag")
                now = datetime.now(timezone.utc).isoformat()

                if baseline_mode and not current_tag:
                    # 首次发现：设为最新 baseline，不产生通知
                    item["last_release_tag"] = releases[0].get("tag_name")
                    item["last_release_checked"] = now
                    continue

                # 定位 current_tag 在列表中的位置（list_releases 默认倒序：最新在前）
                current_idx = None
                for i, r in enumerate(releases):
                    if r.get("tag_name") == current_tag:
                        current_idx = i
                        break

                if current_idx is not None:
                    candidate_releases = releases[:current_idx]
                else:
                    # current_tag 不在最近 30 条内，取全部列表再过滤
                    candidate_releases = releases

                # 只保留一周内的 release
                new_releases = [
                    r for r in candidate_releases
                    if r.get("published_at", "") >= week_ago
                ]

                if new_releases:
                    latest = new_releases[0]  # 最新的一条
                    intermediate = [r.get("tag_name") for r in new_releases[1:]]
                    updates.append({
                        "full_name": item["full_name"],
                        "name": item["name"],
                        "owner": owner,
                        "old_tag": current_tag,
                        "new_tag": latest.get("tag_name"),
                        "intermediate_tags": intermediate,
                        "published_at": latest.get("published_at", ""),
                        "html_url": latest.get("html_url", ""),
                        "body": latest.get("body", "")[:2000],
                    })
                    item["last_release_tag"] = latest.get("tag_name")
                    item["last_release_checked"] = now
                    item["last_updated"] = now
            except Exception as e:
                log(f"检查 {item.get('full_name', '?')} Release 失败: {e}", "WARN")
        log(f"Release 检查完成: {len(updates)} 个仓库有新版本", "OK")
        return updates

    def digest_with_llm(self, updates: list[dict], llm) -> list[dict]:
        """对 Release Notes 生成 AI 摘要"""
        if not llm or not updates:
            return updates
        log(f"LLM 分析 {len(updates)} 个 Release Notes...", "STEP")
        system_prompt = "你是一个技术文档摘要专家。请用 20-30 字概括软件版本的更新要点。只输出概括内容，不要任何其他文字。"
        for u in updates:
            body = u.get("body", "")
            if not body:
                continue
            prompt = f"请根据以下 Release Notes，用 20-30 字概括这个版本的主要更新：\n\n{body[:1200]}"
            try:
                summary = llm.summarize(prompt, system_prompt=system_prompt, max_tokens=64)
                u["ai_digest"] = summary or ""
            except Exception as e:
                log(f"LLM 摘要 {u['full_name']} 失败: {e}", "WARN")
                u["ai_digest"] = ""
        log("Release Notes LLM 摘要完成", "OK")
        return updates

    def format_report(self, updates: list[dict]) -> str:
        return self._truncate(updates, limit=10, title="🚀 新 Release 提醒")

    def _format_item(self, item: dict) -> str:
        line = f"  {item['owner']}/{item['name']}: {item['old_tag'] or '无'} → {item['new_tag']}"
        intermediate = item.get("intermediate_tags")
        if intermediate:
            line += f" (还有 {', '.join(intermediate)})"
        return line
