#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release 追踪：检测仓库新 Release"""

from datetime import datetime, timezone

from base_tracker import BaseTracker
from utils import log


class ReleaseTracker(BaseTracker):
    """检查订阅了 Release 的仓库是否有新版本"""

    def check(self, db_items: list[dict]) -> list[dict]:
        updates: list[dict] = []
        log("检查 Release 更新...", "STEP")
        for item in db_items:
            if not item.get("subscribe_releases"):
                continue
            try:
                owner, repo = item["full_name"].split("/")
                latest = self.gh.get_latest_release(owner, repo)
                if not latest:
                    continue
                latest_tag = latest.get("tag_name")
                current_tag = item.get("last_release_tag")
                if latest_tag and latest_tag != current_tag:
                    updates.append({
                        "full_name": item["full_name"],
                        "name": item["name"],
                        "owner": owner,
                        "old_tag": current_tag,
                        "new_tag": latest_tag,
                        "published_at": latest.get("published_at", ""),
                        "html_url": latest.get("html_url", ""),
                    })
                    item["last_release_tag"] = latest_tag
                    item["last_release_checked"] = datetime.now(timezone.utc).isoformat()
                    item["last_updated"] = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                log(f"检查 {item['full_name']} Release 失败: {e}", "WARN")
        log(f"Release 检查完成: {len(updates)} 个仓库有新版本", "OK")
        return updates

    def format_report(self, updates: list[dict]) -> str:
        return self._truncate(updates, limit=10, title="🚀 新 Release 提醒")

    def _format_item(self, item: dict) -> str:
        return f"  {item['owner']}/{item['name']}: {item['old_tag'] or '无'} → {item['new_tag']}"
