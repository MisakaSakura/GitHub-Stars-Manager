#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discover Ecologies 阶段：生态自动发现"""

import os

from orchestrator.context import PipelineContext
from ecology_discovery import EcologyDiscovery
from config_rules import ECOLOGY_RULES
from utils import log


def discover_ecologies_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run or not ctx.db:
        return
    discovery = EcologyDiscovery(ctx.db, ECOLOGY_RULES)
    candidates = discovery.discover(top_n=10)
    if candidates:
        md = discovery.generate_report(candidates)
        out_path = os.path.join(ctx.args.output, "ecology_discovery.md")
        try:
            os.makedirs(ctx.args.output, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md)
            log(f"生态发现报告已生成: {out_path}", "OK")
        except Exception as e:
            log(f"生态发现报告写入失败: {e}", "WARN")
