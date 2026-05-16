#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import 阶段：首次运行导入已有分类"""

from orchestrator.context import PipelineContext
from import_helper import FirstRunHelper
from utils import log, _safe_print


def import_stage(ctx: PipelineContext) -> bool:
    """首次运行导入已有分类；若 --no-auto-classify 则提前退出。返回 True 表示提前终止"""
    if not ctx.is_first_run:
        return False
    if ctx.args.import_json or ctx.args.import_csv:
        if ctx.args.import_json:
            FirstRunHelper.import_from_json(ctx.db, ctx.args.import_json)
        if ctx.args.import_csv:
            FirstRunHelper.import_from_csv(ctx.db, ctx.args.import_csv)
        ctx.db.save()
        log("导入完成，数据库已保存", "OK")

        if ctx.args.no_auto_classify:
            log("--no-auto-classify 已设置，跳过自动分类", "OK")
            _safe_print("\n" + "=" * 60)
            _safe_print(f"✅ 导入完成！共 {len(ctx.db)} 个项目（全部手动保护）")
            _safe_print("=" * 60)
            return True
    return False
