#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新 Pipeline：基于阶段注册器的插件化实现（完全内联版）

所有 18 个阶段已独立为 stages/ 模块，不再依赖旧 Pipeline。
"""

import argparse

from .context import PipelineContext
from .registry import StageRegistry
from utils import log


class Pipeline:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.registry = StageRegistry()
        self.context = PipelineContext(args=args)
        self._build_registry()

    # 阶段注册表：名称 -> (模块路径, 函数名, 依赖列表)
    # P1-4: 集中定义阶段配置，便于动态发现和调整顺序
    _STAGE_REGISTRY = [
        ("setup", ".stages.setup_stage", "setup_stage", []),
        ("import_and_early_exit", ".stages.import_stage", "import_stage", ["setup"]),
        ("auth", ".stages.auth_stage", "auth_stage", ["setup"]),
        ("handle_lists", ".stages.handle_lists_stage", "handle_lists_stage", ["auth"]),
        ("setup_llm", ".stages.classify_stage", "setup_llm_stage", ["auth"]),
        ("fetch", ".stages.fetch_stage", "fetch_stage", ["auth", "setup_llm"]),
        ("enrich", ".stages.classify_stage", "enrich_stage", ["fetch", "setup_llm"]),
        ("classify", ".stages.classify_stage", "classify_stage", ["fetch", "enrich"]),
        ("save", ".stages.save_stage", "save_stage", ["classify"]),
        ("sync_notion", ".stages.sync_notion_stage", "sync_notion_stage", ["save"]),
        ("track_releases", ".stages.track_releases_stage", "track_releases_stage", ["save"]),
        ("track_forks", ".stages.track_forks_stage", "track_forks_stage", ["save"]),
        ("discover_ecologies", ".stages.discover_ecologies_stage", "discover_ecologies_stage", ["save"]),
        ("check_consistency", ".stages.check_consistency_stage", "check_consistency_stage", ["save"]),
        ("record_feedback", ".stages.record_feedback_stage", "record_feedback_stage", ["save"]),
        ("generate_reports", ".stages.reports_stage", "reports_stage", ["track_releases", "track_forks"]),
        ("notify", ".stages.notify_stage", "notify_stage", ["generate_reports"]),
        ("print_summary", ".stages.print_summary_stage", "print_summary_stage", ["notify", "generate_reports"]),
    ]

    def _build_registry(self):
        import importlib
        for name, module_path, fn_name, deps in self._STAGE_REGISTRY:
            module = importlib.import_module(module_path, __package__)
            fn = getattr(module, fn_name)
            self.registry.register(name, fn, deps)

    def run(self) -> None:
        log("[NewPipeline] 启动插件化流水线", "STEP")
        self.registry.run(self.context)
