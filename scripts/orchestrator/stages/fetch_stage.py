#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch 阶段：获取所有 Starred 项目"""

from orchestrator.context import PipelineContext


def fetch_stage(ctx: PipelineContext) -> None:
    ctx.items = ctx.gh.fetch_all(ctx.args.user)
