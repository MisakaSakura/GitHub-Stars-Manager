#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check Consistency 阶段：一致性自检"""

import os

from orchestrator.context import PipelineContext
from consistency_checker import ConsistencyChecker
from utils import log


def check_consistency_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run or not ctx.db:
        return
    checker = ConsistencyChecker(ctx.db)
    issues = checker.check()
    md = checker.generate_report()
    out_path = os.path.join(ctx.args.output, "consistency_report.md")
    try:
        os.makedirs(ctx.args.output, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        log(f"一致性报告已生成: {out_path}", "OK")
    except Exception as e:
        log(f"一致性报告写入失败: {e}", "WARN")
