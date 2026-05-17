#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setup 阶段：初始化数据库、检测首次运行"""

import os

from orchestrator.context import PipelineContext
from database import StarsDB
from ai_database import AIDatabase
from import_helper import FirstRunHelper
from utils import log, _safe_print


def setup_stage(ctx: PipelineContext) -> None:
    ctx.is_first_run = FirstRunHelper.detect_first_run(ctx.args.db)
    _safe_print("=" * 60)
    _safe_print("⭐ GitHub Stars 自动分类工具 v4")
    _safe_print("=" * 60)

    if ctx.is_first_run:
        _safe_print("\n🆕 检测到首次运行（数据库不存在）")
        _safe_print("   将创建新数据库并对所有项目执行全新分类。")
        if ctx.args.import_json or ctx.args.import_csv:
            _safe_print("   检测到导入参数，将先导入已有分类（自动保护），再处理剩余项目。\n")
        else:
            _safe_print("   提示: 如果你有已有分类想保留，使用 --import-json 或 --import-csv 导入")
            _safe_print("   导入的项目会被自动标记保护，不会被覆盖。\n")
    else:
        _safe_print(f"\n📂 加载已有数据库: {ctx.args.db}\n")

    # 存储后端选择
    storage = getattr(ctx.args, 'storage', 'json')
    if storage == 'sqlite':
        from repositories import SQLiteStarsRepository
        db_path = os.path.splitext(ctx.args.db)[0] + '.db'
        ctx.db = SQLiteStarsRepository(db_path)
        if ctx.is_first_run and os.path.exists(ctx.args.db):
            ctx.db.migrate_from_json(ctx.args.db)
        _safe_print(f"   [SQLite] 使用 SQLite 后端: {db_path}")
    else:
        ctx.db = StarsDB(ctx.args.db)

    ai_db_path = os.path.join(os.path.dirname(ctx.args.db), "stars_ai.json")
    ctx.ai_db = AIDatabase(ai_db_path)
    ctx.ai_db.migrate_from_stars_db(list(ctx.db.values()))
