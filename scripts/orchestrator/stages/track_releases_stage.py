#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track Releases 阶段：检测仓库新 Release"""

import json
import os
from datetime import datetime, timezone

from orchestrator.context import PipelineContext
from release_tracker import ReleaseTracker
from utils import log


def _save_release_history(ctx: PipelineContext) -> None:
    """将本次检测到的 Release 追加到历史记录，按 full_name + new_tag 去重"""
    if not ctx.release_updates:
        return
    history_path = os.path.join(os.path.dirname(ctx.args.db), "releases_history.json")
    existing: list[dict] = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            log(f"Release 历史 JSON 损坏，将重建: {history_path}", "WARN")
            existing = []
        except OSError as e:
            log(f"Release 历史读取失败: {e}", "WARN")
            existing = []
    if not isinstance(existing, list):
        existing = []

    seen = {(r.get("full_name"), r.get("new_tag")) for r in existing}
    for ru in ctx.release_updates:
        key = (ru.get("full_name"), ru.get("new_tag"))
        if key not in seen:
            existing.append({
                "full_name": ru["full_name"],
                "name": ru["name"],
                "owner": ru["owner"],
                "old_tag": ru["old_tag"],
                "new_tag": ru["new_tag"],
                "published_at": ru.get("published_at", ""),
                "html_url": ru.get("html_url", ""),
                "body": ru.get("body", ""),
                "ai_digest": ru.get("ai_digest", ""),
                "is_new_repo": ru.get("is_new_repo", False),
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })
            seen.add(key)

    existing.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    existing = existing[:500]

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    log(f"Release 历史已更新: {len(existing)} 条记录", "OK")


def track_releases_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run:
        return
    if not ctx.args.check_releases and not ctx.args.check_all_releases:
        return
    ctx.release_tracker = ReleaseTracker(ctx.gh)
    items = list(ctx.db.values())
    if ctx.args.check_all_releases:
        ctx.release_updates = ctx.release_tracker.check_all(items)
    else:
        ctx.release_updates = ctx.release_tracker.check(items)
    if ctx.args.llm_release_digest and ctx.llm and ctx.release_updates:
        ctx.release_updates = ctx.release_tracker.digest_with_llm(ctx.release_updates, ctx.llm)
    if ctx.release_updates:
        ctx.db.save()
        _save_release_history(ctx)
