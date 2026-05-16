#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync Notion 阶段：同步到 Notion"""

from orchestrator.context import PipelineContext
from report import ReportGenerator
from notion import NotionExporter


def sync_notion_stage(ctx: PipelineContext) -> None:
    if not (ctx.args.notion_key and ctx.args.notion_db) or ctx.args.dry_run:
        return
    report = ReportGenerator(ctx.db, ai_db=ctx.ai_db)
    items = report._inject_ai_fields(list(ctx.db.values()))
    notion = NotionExporter(ctx.args.notion_key, ctx.args.notion_db)
    notion.sync(items, clear_existing=ctx.args.notion_clear)
