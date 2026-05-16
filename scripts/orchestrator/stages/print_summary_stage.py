#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print Summary 阶段：打印运行摘要"""

from orchestrator.context import PipelineContext
from orchestrator.shared import build_summary
from utils import _safe_print


def print_summary_stage(ctx: PipelineContext) -> None:
    _safe_print("\n" + "=" * 60)
    _safe_print(build_summary(ctx))
    _safe_print("=" * 60)

    if ctx.is_first_run and not getattr(ctx.args, 'import_json', None) and not getattr(ctx.args, 'import_csv', None):
        _safe_print("\n💡 首次运行提示:")
        _safe_print('   1. 检查生成的报告，对不满意的项目修改 data/stars_db.json')
        _safe_print('   2. 给满意的项目添加 "manual_override": true 避免被覆盖')
        _safe_print("   3. 日常使用 --mode incremental 只处理新项目")
        _safe_print("   4. 如需重新分类所有项目，使用 --mode deep 或 --mode full")
