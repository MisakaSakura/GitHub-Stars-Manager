#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新 Pipeline：基于阶段注册器的插件化实现（完全内联版）

所有 18 个阶段已独立为 stages/ 模块，不再依赖旧 Pipeline。
"""

import argparse

from .context import PipelineContext
from .registry import StageRegistry
from utils import log


class NewPipeline:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.registry = StageRegistry()
        self.context = PipelineContext(args=args)
        self._build_registry()

    def _build_registry(self):
        from .stages.setup_stage import setup_stage
        from .stages.import_stage import import_stage
        from .stages.auth_stage import auth_stage
        from .stages.handle_lists_stage import handle_lists_stage
        from .stages.classify_stage import setup_llm_stage, enrich_stage, classify_stage
        from .stages.fetch_stage import fetch_stage
        from .stages.save_stage import save_stage
        from .stages.sync_notion_stage import sync_notion_stage
        from .stages.track_releases_stage import track_releases_stage
        from .stages.track_forks_stage import track_forks_stage
        from .stages.discover_ecologies_stage import discover_ecologies_stage
        from .stages.check_consistency_stage import check_consistency_stage
        from .stages.record_feedback_stage import record_feedback_stage
        from .stages.reports_stage import reports_stage
        from .stages.notify_stage import notify_stage
        from .stages.print_summary_stage import print_summary_stage

        self.registry.register("setup", setup_stage, [])
        self.registry.register("import_and_early_exit", import_stage, ["setup"])
        self.registry.register("auth", auth_stage, ["setup"])
        self.registry.register("handle_lists", handle_lists_stage, ["auth"])
        self.registry.register("setup_llm", setup_llm_stage, ["auth"])
        self.registry.register("fetch", fetch_stage, ["auth", "setup_llm"])
        self.registry.register("enrich", enrich_stage, ["fetch", "setup_llm"])
        self.registry.register("classify", classify_stage, ["fetch", "enrich"])
        self.registry.register("save", save_stage, ["classify"])
        self.registry.register("sync_notion", sync_notion_stage, ["save"])
        self.registry.register("track_releases", track_releases_stage, ["save"])
        self.registry.register("track_forks", track_forks_stage, ["save"])
        self.registry.register("discover_ecologies", discover_ecologies_stage, ["save"])
        self.registry.register("check_consistency", check_consistency_stage, ["save"])
        self.registry.register("record_feedback", record_feedback_stage, ["save"])
        self.registry.register("generate_reports", reports_stage, ["track_releases", "track_forks"])
        self.registry.register("notify", notify_stage, ["generate_reports"])
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
