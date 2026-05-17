#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release 追踪：检测仓库新 Release"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from base_tracker import BaseTracker
from utils import log, parse_iso


def _get_field(obj, key: str, default=None):
    """兼容 dict 和 dataclass 的字段读取"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_within_window(published_at: str, window_start: str) -> bool:
    """判断 published_at 是否在 window_start 之后（使用 datetime 比较，避免字符串比较误差）"""
    pub_dt = parse_iso(published_at)
    win_dt = parse_iso(window_start)
    if not pub_dt or not win_dt:
        return False
    return pub_dt >= win_dt


def _is_newly_starred(item) -> bool:
    """判断项目是否是在最近 7 天内新 star 的（用于区分真正的新收录 vs 老项目首次检查 release）"""
    first_seen = _get_field(item, "first_seen", "")
    if not first_seen:
        return False
    fs_dt = parse_iso(first_seen)
    if not fs_dt:
        return False
    from datetime import timedelta
    return (datetime.now(timezone.utc) - fs_dt) <= timedelta(days=7)


class ReleaseTracker(BaseTracker):
    """检查仓库新 Release，支持订阅制和全量检查两种模式"""

    def check(self, db_items: list[dict]) -> list[dict]:
        """订阅制检查：只检查 subscribe_releases=true 的项目（向后兼容）"""
        candidates = [item for item in db_items if _get_field(item, "subscribe_releases")]
        return self._check_candidates(candidates, baseline_mode=False)

    def check_all(self, db_items: list[dict]) -> list[dict]:
        """全量检查：对所有项目检查 Release，新项目设为 baseline 不通知"""
        return self._check_candidates(db_items, baseline_mode=True)

    def _check_candidates(self, db_items: list[dict], baseline_mode: bool) -> list[dict]:
        mode_label = "全量" if baseline_mode else "订阅"
        log(f"检查 Release 更新 ({mode_label}): {len(db_items)} 个仓库...", "STEP")
        from datetime import datetime, timezone, timedelta

        def check_one(item: dict) -> tuple[dict | None, tuple[dict, dict] | None]:
            """返回 (update_dict, (item, fields_to_update))。不在并发中就地修改 item。"""
            try:
                full_name = _get_field(item, "full_name", "")
                if "/" not in full_name:
                    return None, None
                owner, _, repo = full_name.partition("/")
                releases = self.gh.list_releases(owner, repo, per_page=30)
                # 防御：API 可能返回非列表或包含 None 的列表
                if not isinstance(releases, list):
                    log(f"  {owner}/{repo} list_releases 返回非列表: {type(releases).__name__}", "WARN")
                    return None, None
                releases = [r for r in releases if isinstance(r, dict)]
                if not releases:
                    return None, None

                current_tag = _get_field(item, "last_release_tag")
                now = datetime.now(timezone.utc).isoformat()

                # 时间窗口：基于上次检查时间，而非固定 7 天，避免遗漏两次运行之间的 release
                last_checked = _get_field(item, "last_release_checked")
                if last_checked:
                    window_start = last_checked
                else:
                    window_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

                if baseline_mode and not current_tag:
                    # 首次发现：设为最新 baseline
                    latest_release = releases[0]
                    baseline_mutations = {
                        "last_release_tag": latest_release.get("tag_name"),
                        "last_release_checked": now,
                    }
                    # 只有真正最近新 star 的项目才标记为 is_new_repo
                    # 老项目首次检查 release 时只设 baseline，不产生 update
                    if _is_newly_starred(item) and _is_within_window(
                        latest_release.get("published_at", ""), window_start
                    ):
                        update = {
                            "full_name": _get_field(item, "full_name"),
                            "name": _get_field(item, "name"),
                            "owner": owner,
                            "old_tag": None,
                            "new_tag": latest_release.get("tag_name"),
                            "intermediate_tags": [],
                            "published_at": latest_release.get("published_at", ""),
                            "html_url": latest_release.get("html_url", ""),
                            "body": (latest_release.get("body") or "")[:2000],
                            "is_new_repo": True,
                        }
                        return update, (item, baseline_mutations)
                    return None, (item, baseline_mutations)

                # 定位 current_tag 在列表中的位置（list_releases 默认倒序：最新在前）
                current_idx = None
                for i, r in enumerate(releases):
                    if r.get("tag_name") == current_tag:
                        current_idx = i
                        break

                if current_idx is not None:
                    candidate_releases = releases[:current_idx]
                else:
                    candidate_releases = releases

                # 只保留时间窗口内的 release（使用 datetime 比较）
                new_releases = [
                    r for r in candidate_releases
                    if _is_within_window(r.get("published_at", ""), window_start)
                ]

                if new_releases:
                    latest = new_releases[0]
                    intermediate = [r.get("tag_name") for r in new_releases[1:]]
                    update = {
                        "full_name": _get_field(item, "full_name"),
                        "name": _get_field(item, "name"),
                        "owner": owner,
                        "old_tag": current_tag,
                        "new_tag": latest.get("tag_name"),
                        "intermediate_tags": intermediate,
                        "published_at": latest.get("published_at", ""),
                        "html_url": latest.get("html_url", ""),
                        "body": (latest.get("body") or "")[:2000],
                    }
                    mutations = {
                        "last_release_tag": latest.get("tag_name"),
                        "last_release_checked": now,
                    }
                    return update, (item, mutations)
            except Exception as e:
                log(f"检查 {_get_field(item, 'full_name', '?')} Release 失败: {e}", "WARN")
            return None, None

        updates: list[dict] = []
        mutations: list[tuple[dict, dict]] = []  # (item, fields_to_update)
        lock = threading.Lock()

        # 并发检查：GitHub API 认证用户限制 5000/hour，8 并发在 burst 安全范围内
        max_workers = min(8, len(db_items)) if db_items else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_one, item): item for item in db_items}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    with lock:
                        if result[0]:
                            updates.append(result[0])
                        if result[1]:
                            mutations.append(result[1])

        # 统一回写 mutations（兼容 dict 和 dataclass）
        for item, fields in mutations:
            for k, v in fields.items():
                if isinstance(item, dict):
                    item[k] = v
                else:
                    setattr(item, k, v)

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
                # P2 fix: 从 profile 读取 release_digest 场景的最大 tokens，避免 reasoning 模型不够
                max_tokens = llm.profile.get_max_tokens("release_digest") if getattr(llm, "profile", None) else 64
                summary = llm.summarize(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
                u["ai_digest"] = summary or ""
            except Exception as e:
                log(f"LLM 摘要 {u['full_name']} 失败: {e}", "WARN")
                u["ai_digest"] = ""
        log("Release Notes LLM 摘要完成", "OK")
        return updates

    def format_report(self, updates: list[dict]) -> str:
        new_count = sum(1 for u in updates if u.get("is_new_repo"))
        regular_count = len(updates) - new_count
        parts = []
        if new_count:
            parts.append(f"🆕 新收录动态 ({new_count})")
        if regular_count:
            parts.append(f"🚀 新 Release ({regular_count})")
        return self._truncate(updates, limit=10, title=" | ".join(parts) if parts else "Release 更新")

    def _format_item(self, item: dict) -> str:
        is_new = item.get("is_new_repo", False)
        prefix = "🆕 " if is_new else ""
        line = f"  {prefix}{item['owner']}/{item['name']}: {item['old_tag'] or '首次发现'} → {item['new_tag']}"
        intermediate = item.get("intermediate_tags")
        if intermediate:
            line += f" (还有 {', '.join(intermediate)})"
        return line
