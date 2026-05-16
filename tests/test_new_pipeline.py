#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NewPipeline 插件化架构验证测试"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from orchestrator.new_pipeline import NewPipeline
from orchestrator.registry import StageRegistry
from orchestrator.context import PipelineContext


class TestStageRegistry(unittest.TestCase):
    def test_register_and_run(self):
        reg = StageRegistry()
        calls = []
        reg.register("a", lambda ctx: calls.append("a"))
        reg.register("b", lambda ctx: calls.append("b"))
        reg.run(MagicMock())
        self.assertEqual(calls, ["a", "b"])

    def test_run_early_exit(self):
        reg = StageRegistry()
        calls = []
        reg.register("a", lambda ctx: (calls.append("a") or True))
        reg.register("b", lambda ctx: False)  # 提前终止
        reg.register("c", lambda ctx: calls.append("c"))
        reg.run(MagicMock())
        self.assertEqual(calls, ["a"])

    def test_skip(self):
        reg = StageRegistry()
        calls = []
        reg.register("a", lambda ctx: calls.append("a"))
        reg.register("b", lambda ctx: calls.append("b"))
        reg.run(MagicMock(), skip={"a"})
        self.assertEqual(calls, ["b"])


class TestPipelineContext(unittest.TestCase):
    def test_get_set(self):
        ctx = PipelineContext(args=MagicMock())
        ctx.set("foo", "bar")
        self.assertEqual(ctx.get("foo"), "bar")
        self.assertIsNone(ctx.get("missing"))

    def test_default_values(self):
        ctx = PipelineContext(args=MagicMock())
        self.assertEqual(ctx.items, [])
        self.assertEqual(ctx.new_keys, set())


class TestNewPipelineStructure(unittest.TestCase):
    def test_registry_has_expected_stages(self):
        args = MagicMock()
        # 避免触发真实的 Pipeline 初始化
        with patch("pipeline.Pipeline") as mock_old:
            mock_instance = MagicMock()
            mock_instance._setup = MagicMock()
            mock_instance._import_and_early_exit = MagicMock(return_value=False)
            mock_instance._auth = MagicMock()
            mock_instance._handle_lists = MagicMock()
            mock_instance._setup_llm = MagicMock()
            mock_instance._fetch = MagicMock()
            mock_instance._enrich = MagicMock()
            mock_instance._classify = MagicMock()
            mock_instance._save = MagicMock()
            mock_instance._sync_notion = MagicMock()
            mock_instance._track_releases = MagicMock()
            mock_instance._track_forks = MagicMock()
            mock_instance._discover_ecologies = MagicMock()
            mock_instance._check_consistency = MagicMock()
            mock_instance._record_feedback = MagicMock()
            mock_instance._generate_reports = MagicMock()
            mock_instance._notify = MagicMock()
            mock_instance._print_summary = MagicMock()
            mock_old.return_value = mock_instance

            np = NewPipeline(args)
            names = np.registry.stage_names
            self.assertIn("setup", names)
            self.assertIn("classify", names)
            self.assertIn("generate_reports", names)
            self.assertIn("notify", names)

    def test_run_delegates_to_old_pipeline(self):
        args = MagicMock()
        with patch("pipeline.Pipeline") as mock_old:
            mock_instance = MagicMock()
            mock_instance._setup = MagicMock()
            mock_instance._import_and_early_exit = MagicMock(return_value=False)
            mock_instance._auth = MagicMock()
            mock_instance._fetch = MagicMock()
            mock_instance._classify = MagicMock()
            mock_instance._save = MagicMock()
            mock_instance._generate_reports = MagicMock()
            mock_instance._notify = MagicMock()
            mock_instance._print_summary = MagicMock()
            mock_instance._handle_lists = MagicMock()
            mock_instance._setup_llm = MagicMock()
            mock_instance._enrich = MagicMock()
            mock_instance._sync_notion = MagicMock()
            mock_instance._track_releases = MagicMock()
            mock_instance._track_forks = MagicMock()
            mock_instance._discover_ecologies = MagicMock()
            mock_instance._check_consistency = MagicMock()
            mock_instance._record_feedback = MagicMock()
            mock_old.return_value = mock_instance

            np = NewPipeline(args)
            np.run()

            # setup/auth/fetch/setup_llm/enrich/classify 已内联，不委托旧 Pipeline
            mock_instance._setup.assert_not_called()
            mock_instance._auth.assert_not_called()
            mock_instance._fetch.assert_not_called()
            mock_instance._classify.assert_not_called()
            # 其余阶段仍委托旧 Pipeline
            mock_instance._save.assert_called_once()
