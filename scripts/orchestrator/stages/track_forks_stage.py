#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track Forks 阶段：检测 Fork 上游更新"""

from orchestrator.context import PipelineContext
from fork_tracker import ForkTracker


def track_forks_stage(ctx: PipelineContext) -> None:
    if not ctx.args.check_forks or ctx.args.dry_run:
        return
    ctx.fork_tracker = ForkTracker(ctx.gh)
    forks = ctx.fork_tracker.get_user_forks(ctx.args.user)
    ctx.fork_updates = ctx.fork_tracker.check(forks)
