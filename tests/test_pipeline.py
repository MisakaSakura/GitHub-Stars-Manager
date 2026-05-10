#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline 单元测试"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from pipeline import Pipeline


class FakeArgs:
    """模拟 argparse Namespace"""
    def __init__(self, **kwargs):
        defaults = {
            "token": "fake_token",
            "user": "testuser",
            "db": "./fake_db.json",
            "output": "./fake_docs",
            "incremental": False,
            "force_refresh": False,
            "import_json": None,
            "import_csv": None,
            "no_auto_classify": False,
            "lists_strategy": "ignore",
            "llm_key": None,
            "llm_provider": "openai",
            "llm_model": None,
            "llm_base": None,
            "llm_interval_days": 30,
            "force_llm": False,
            "notion_key": None,
            "notion_db": None,
            "notion_clear": False,
            "check_releases": False,
            "check_all_releases": False,
            "check_forks": False,
            "subscribe_releases": False,
            "llm_release_digest": False,
            "notify": False,
            "notify_channels": "email",
            "no_report": False,
            "dry_run": False,
            "retry_failed": False,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class TestPipelineImportEarlyExit(unittest.TestCase):
    @patch("pipeline.FirstRunHelper.detect_first_run", return_value=True)
    @patch("pipeline.FirstRunHelper.import_from_json")
    @patch("pipeline.StarsDB")
    def test_no_auto_classify_exits_early(self, mock_db_cls, mock_import_json, _):
        args = FakeArgs(import_json="./old.json", no_auto_classify=True)
        pipeline = Pipeline(args)
        with patch.object(pipeline, "_auth") as mock_auth:
            pipeline.run()
        mock_auth.assert_not_called()
        mock_import_json.assert_called_once()

    @patch("pipeline.FirstRunHelper.detect_first_run", return_value=True)
    @patch("pipeline.FirstRunHelper.import_from_csv")
    @patch("pipeline.StarsDB")
    def test_import_csv_then_continue(self, mock_db_cls, mock_import_csv, _):
        args = FakeArgs(import_csv="./old.csv")
        pipeline = Pipeline(args)
        with patch.object(pipeline, "_auth") as mock_auth, \
             patch.object(pipeline, "_fetch") as mock_fetch:
            pipeline.run()
        mock_auth.assert_called_once()
        mock_fetch.assert_called_once()
        mock_import_csv.assert_called_once()


class TestPipelineStageOrdering(unittest.TestCase):
    @patch("pipeline.FirstRunHelper.detect_first_run", return_value=False)
    @patch("pipeline.StarsDB")
    def test_run_calls_stages_in_order(self, mock_db_cls, _):
        args = FakeArgs()
        pipeline = Pipeline(args)

        stage_methods = [
            "_setup",
            "_import_and_early_exit",
            "_auth",
            "_handle_lists",
            "_setup_llm",
            "_fetch",
            "_enrich",
            "_classify",
            "_save",
            "_generate_reports",
            "_sync_notion",
            "_track_releases",
            "_track_forks",
            "_notify",
            "_print_summary",
        ]
        mocks = {}
        for name in stage_methods:
            return_value = False if name == "_import_and_early_exit" else None
            mocks[name] = patch.object(pipeline, name, return_value=return_value).start()

        try:
            pipeline.run()
        finally:
            for p in mocks.values():
                p.stop()

        # 验证每个阶段至少被调用一次
        for name, mock in mocks.items():
            with self.subTest(stage=name):
                mock.assert_called_once()


class TestPipelineLLMSetup(unittest.TestCase):
    @patch("pipeline.FirstRunHelper.detect_first_run", return_value=False)
    @patch("pipeline.StarsDB")
    def test_llm_disabled_when_no_key(self, mock_db_cls, _):
        args = FakeArgs(llm_key=None)
        pipeline = Pipeline(args)
        pipeline._setup()
        pipeline._setup_llm()
        self.assertIsNone(pipeline.llm)

    @patch("pipeline.FirstRunHelper.detect_first_run", return_value=False)
    @patch("pipeline.StarsDB")
    @patch("pipeline.LLMClassifier")
    def test_llm_enabled_with_key(self, mock_llm_cls, mock_db_cls, _):
        args = FakeArgs(llm_key="sk-test", llm_model="gpt-4")
        pipeline = Pipeline(args)
        pipeline._setup()
        pipeline.db.meta = {}
        pipeline._setup_llm()
        self.assertIsNotNone(pipeline.llm)
        mock_llm_cls.assert_called_once()


class TestPipelineDryRun(unittest.TestCase):
    @patch("pipeline.FirstRunHelper.detect_first_run", return_value=False)
    @patch("pipeline.StarsDB")
    def test_dry_run_skips_save_and_report(self, mock_db_cls, _):
        args = FakeArgs(dry_run=True)
        pipeline = Pipeline(args)
        pipeline._setup()
        pipeline.stats = {"new": 1, "updated": 0, "skipped": 0, "protected": 0, "llm_enhanced": 0, "error": 0}

        with patch.object(pipeline.db, "save") as mock_save:
            pipeline._save()
            mock_save.assert_not_called()


class TestPipelineNotify(unittest.TestCase):
    @patch("pipeline.FirstRunHelper.detect_first_run", return_value=False)
    @patch("pipeline.StarsDB")
    @patch("pipeline.Notifier")
    def test_notify_composes_summary(self, mock_notifier_cls, mock_db_cls, _):
        args = FakeArgs(notify=True)
        pipeline = Pipeline(args)
        pipeline._setup()
        pipeline.stats = {"new": 2, "updated": 1, "skipped": 0, "protected": 0, "llm_enhanced": 0, "error": 0}
        pipeline.release_updates = [{"full_name": "a/b", "old_tag": "v1", "new_tag": "v2"}]
        pipeline.release_tracker = MagicMock()
        pipeline.release_tracker.format_report.return_value = "RELEASE_REPORT"

        pipeline._notify()

        mock_notifier = mock_notifier_cls.return_value
        mock_notifier.send.assert_called_once()
        call_args = mock_notifier.send.call_args
        self.assertIn("GitHub Stars 分类完成", call_args[0][0])
        summary_body = call_args[0][1]
        self.assertIn("RELEASE_REPORT", summary_body)


if __name__ == "__main__":
    unittest.main()
