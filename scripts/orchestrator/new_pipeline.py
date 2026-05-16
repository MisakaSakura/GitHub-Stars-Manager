#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新 Pipeline：基于阶段注册器的插件化实现（过渡期）"""

import argparse

from .context import PipelineContext
from .registry import StageRegistry
from utils import log


def _make_stage_fn(method_name: str):
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

        stages = [
            ("setup", "_setup", []),
            ("import_and_early_exit", "_import_and_early_exit", ["setup"]),
            ("auth", "_auth", ["setup"]),
            ("handle_lists", "_handle_lists", ["auth"]),
            ("setup_llm", "_setup_llm", ["auth"]),
            ("fetch", "_fetch", ["auth", "setup_llm"]),
            ("enrich", "_enrich", ["fetch", "setup_llm"]),
            ("classify", "_classify", ["fetch", "enrich"]),
            ("save", "_save", ["classify"]),
            ("sync_notion", "_sync_notion", ["save"]),
            ("track_releases", "_track_releases", ["save"]),
            ("track_forks", "_track_forks", ["save"]),
            ("discover_ecologies", "_discover_ecologies", ["save"]),
            ("check_consistency", "_check_consistency", ["save"]),
            ("record_feedback", "_record_feedback", ["save"]),
            ("generate_reports", "_generate_reports", ["track_releases", "track_forks"]),
            ("notify", "_notify", ["generate_reports"]),
            ("print_summary", "_print_summary", ["notify", "generate_reports"]),
        ]
        for name, method, deps in stages:
            self.registry.register(name, _make_stage_fn(method), deps)

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
