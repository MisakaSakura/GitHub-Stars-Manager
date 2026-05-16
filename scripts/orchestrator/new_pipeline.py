#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新 Pipeline：基于阶段注册器的插件化实现

架构：
  - 核心阶段（setup/auth/fetch/classify）已内联为独立模块
  - 剩余阶段仍委托旧 Pipeline，逐步迁移中
"""

import argparse

from .context import PipelineContext
from .registry import StageRegistry
from utils import log


def _make_stage_fn(method_name: str):
    """工厂：创建委托到旧 Pipeline 方法的阶段函数"""
    def stage_fn(ctx):
        old_pipeline = getattr(ctx, '_old_pipeline', None)
        if old_pipeline is None:
            raise RuntimeError(f"阶段 {method_name} 需要旧 Pipeline 实例")
        method = getattr(old_pipeline, method_name)
        _sync_to_old(ctx, old_pipeline)
        result = method()
        _sync_from_old(ctx, old_pipeline)
        if method_name == "_import_and_early_exit" and result is True:
            return False
        return True
    return stage_fn


def _sync_to_old(ctx, old):
    old.db = ctx.db
    old.ai_db = ctx.ai_db
    old.gh = ctx.gh
    old.rule = ctx.rule
    old.llm = ctx.llm
    old.engine = ctx.engine
    old.stats = ctx.stats
    old.items = ctx.items
    old.is_first_run = ctx.is_first_run
    old.release_updates = ctx.release_updates
    old.fork_updates = ctx.fork_updates
    old.release_tracker = ctx.release_tracker
    old.fork_tracker = ctx.fork_tracker
    old.new_keys = ctx.new_keys
    old.star_changes = ctx.star_changes
    old.classification_changes = ctx.classification_changes


def _sync_from_old(ctx, old):
    ctx.db = old.db
    ctx.ai_db = old.ai_db
    ctx.gh = old.gh
    ctx.rule = old.rule
    ctx.llm = old.llm
    ctx.engine = old.engine
    ctx.stats = old.stats
    ctx.items = old.items
    ctx.is_first_run = old.is_first_run
    ctx.new_keys = getattr(old, 'new_keys', set())
    ctx.star_changes = getattr(old, 'star_changes', {})
    ctx.classification_changes = getattr(old, 'classification_changes', {})
    ctx.release_updates = old.release_updates
    ctx.fork_updates = old.fork_updates
    ctx.release_tracker = old.release_tracker
    ctx.fork_tracker = old.fork_tracker


class NewPipeline:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.registry = StageRegistry()
        self.context = PipelineContext(args=args)
        self._old_pipeline = None
        self._build_registry()

    def _build_registry(self):
        from pipeline import Pipeline as OldPipeline
        self._old_pipeline = OldPipeline(self.args)
        self.context._old_pipeline = self._old_pipeline

        # 已内联的独立阶段
        from .stages.setup_stage import setup_stage
        from .stages.auth_stage import auth_stage
        from .stages.fetch_stage import fetch_stage
        from .stages.classify_stage import setup_llm_stage, enrich_stage, classify_stage
        from .stages.save_stage import save_stage
        from .stages.reports_stage import reports_stage
        from .stages.print_summary_stage import print_summary_stage

        # 注册阶段：独立阶段优先，其余委托旧 Pipeline
        self.registry.register("setup", setup_stage, [])
        self.registry.register("import_and_early_exit", _make_stage_fn("_import_and_early_exit"), ["setup"])
        self.registry.register("auth", auth_stage, ["setup"])
        self.registry.register("handle_lists", _make_stage_fn("_handle_lists"), ["auth"])
        self.registry.register("setup_llm", setup_llm_stage, ["auth"])
        self.registry.register("fetch", fetch_stage, ["auth", "setup_llm"])
        self.registry.register("enrich", enrich_stage, ["fetch", "setup_llm"])
        self.registry.register("classify", classify_stage, ["fetch", "enrich"])
        self.registry.register("save", save_stage, ["classify"])
        self.registry.register("sync_notion", _make_stage_fn("_sync_notion"), ["save"])
        self.registry.register("track_releases", _make_stage_fn("_track_releases"), ["save"])
        self.registry.register("track_forks", _make_stage_fn("_track_forks"), ["save"])
        self.registry.register("discover_ecologies", _make_stage_fn("_discover_ecologies"), ["save"])
        self.registry.register("check_consistency", _make_stage_fn("_check_consistency"), ["save"])
        self.registry.register("record_feedback", _make_stage_fn("_record_feedback"), ["save"])
        self.registry.register("generate_reports", reports_stage, ["track_releases", "track_forks"])
        self.registry.register("notify", _make_stage_fn("_notify"), ["generate_reports"])
        self.registry.register("print_summary", print_summary_stage, ["notify", "generate_reports"])

    def run(self) -> None:
        log("[NewPipeline] 启动插件化流水线", "STEP")
        try:
            self.registry.run(self.context)
        except KeyboardInterrupt:
            import sys
            print("\n操作已取消")
            sys.exit(130)
        except Exception as e:
            import sys
            print(f"\n运行失败: {e}")
            sys.exit(1)
