#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Handle Lists 阶段：处理 GitHub Lists"""

import sys

from orchestrator.context import PipelineContext
from lists_manager import ListsManager
from utils import log, _safe_print


def handle_lists_stage(ctx: PipelineContext) -> None:
    if not ctx.is_first_run:
        return
    lists_manager = ListsManager(ctx.gh)
    lists = lists_manager.detect_lists(ctx.args.user)
    if not lists:
        return

    summary = lists_manager.get_lists_summary(lists)
    _safe_print(f"\n📝 检测到你有 {len(summary)} 个 GitHub Lists：")
    _safe_print("   " + "-" * 42)
    _safe_print(f"   {'名称':<24} {'项目数':>10}")
    _safe_print("   " + "-" * 42)
    for s in summary:
        _safe_print(f"   {s['name']:<24} {s['count']:>10}")
    _safe_print("   " + "-" * 42)

    strategy = ctx.args.lists_strategy
    if strategy == "auto":
        strategy = "prompt" if sys.stdin.isatty() else "ignore"

    if strategy == "prompt":
        _safe_print("\n请选择处理方式：")
        _safe_print("  [1] 迁移：将已有 Lists 作为受保护的初始分类导入（推荐）")
        _safe_print("  [2] 重构：删除所有旧 Lists，用本工具的全新分类替代")
        _safe_print("  [3] 忽略：保留旧 Lists，本工具独立运行")
        while True:
            try:
                choice = input("\n你的选择 [1/2/3]: ").strip()
                if choice == "1":
                    lists_manager.migrate_lists_to_db(ctx.db, ctx.args.user)
                    ctx.db.save()
                    break
                elif choice == "2":
                    lists_manager.clear_all_lists(ctx.args.user)
                    break
                elif choice == "3":
                    log("已忽略 GitHub Lists", "INFO")
                    break
                else:
                    print("请输入 1、2 或 3")
            except (EOFError, KeyboardInterrupt):
                print("\n未收到输入，默认忽略 Lists")
                break
    elif strategy == "migrate":
        lists_manager.migrate_lists_to_db(ctx.db, ctx.args.user)
        ctx.db.save()
    elif strategy == "replace":
        lists_manager.clear_all_lists(ctx.args.user)
    else:
        log("已忽略 GitHub Lists（--lists-strategy=ignore/auto 非 TTY）", "INFO")
