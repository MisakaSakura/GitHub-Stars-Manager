#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Save 阶段：持久化数据库和元数据"""

from datetime import datetime, timezone

from orchestrator.context import PipelineContext
from utils import log


def save_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run:
        log("试运行模式：数据库未保存", "WARN")
        return
    # GC-13: 添加 None 检查，与 ctx.ai_db 保持一致
    if ctx.db:
        ctx.db.save()
        if ctx.llm:
            ctx.db.meta_set("last_llm_classify_at", datetime.now(timezone.utc).isoformat())
        if ctx.did_full_refresh:
            ctx.db.meta_set("last_full_refresh_at", datetime.now(timezone.utc).isoformat())
        ctx.db.meta_save()
    if ctx.ai_db:
        ctx.ai_db.save()
    log("数据库已保存", "OK")
