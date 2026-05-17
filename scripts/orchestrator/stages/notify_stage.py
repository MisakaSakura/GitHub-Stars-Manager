#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notify 阶段：发送通知"""

from orchestrator.context import PipelineContext
from orchestrator.shared import build_summary, build_weekly_digest_text
from notify import Notifier
from utils import log


def notify_stage(ctx: PipelineContext) -> None:
    if not ctx.args.notify or ctx.args.dry_run:
        return

    from config import NOTIFY_CONFIG
    notify_cfg = dict(NOTIFY_CONFIG)
    notify_cfg["enabled"] = True
    raw_channels = getattr(ctx.args, 'notify_channels', '').split(",") if getattr(ctx.args, 'notify_channels', None) else []
    notify_cfg["channels"] = [c.strip() for c in raw_channels if c.strip()]
    notifier = Notifier(notify_cfg)

    summary = build_summary(ctx)
    weekly_digest = build_weekly_digest_text(ctx)
    if weekly_digest:
        summary += "\n\n" + weekly_digest
    if ctx.release_updates and ctx.release_tracker:
        summary += "\n\n" + ctx.release_tracker.format_report(ctx.release_updates)
    if ctx.fork_updates and ctx.fork_tracker:
        summary += "\n\n" + ctx.fork_tracker.format_report(ctx.fork_updates)
    notifier.send("GitHub Stars 分类完成", summary, is_error=False)
