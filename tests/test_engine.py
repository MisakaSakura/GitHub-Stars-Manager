#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量更新引擎单元测试"""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from engine import IncrementalEngine, _is_ecology_locked, _safe_int
from models import StarItem
from rule_classifier import RuleClassifier


def _fake_item(name="repo", owner="user", desc="", topics=None, lang="Python", stars=10):
    return {
        "name": name,
        "owner": {"login": owner},
        "description": desc,
        "topics": topics or [],
        "language": lang,
        "stargazers_count": stars,
        "html_url": f"https://github.com/{owner}/{name}",
        "fork": False,
    }


class TestSafeInt(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(_safe_int("42"), 42)
        self.assertEqual(_safe_int(7), 7)

    def test_empty(self):
        self.assertEqual(_safe_int(None), 0)
        self.assertEqual(_safe_int(""), 0)

    def test_invalid(self):
        self.assertEqual(_safe_int("abc"), 0)
        self.assertEqual(_safe_int([1, 2]), 0)

    def test_default(self):
        self.assertEqual(_safe_int("x", default=-1), -1)


class TestEcologyLock(unittest.TestCase):
    def test_unlocked_by_default(self):
        self.assertFalse(_is_ecology_locked("独立项目 / Standalone"))


class MockDB:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        if isinstance(value, dict):
            value = StarItem.from_dict(value)
        self.data[key] = value

    def __len__(self):
        return len(self.data)


class TestIncrementalEngine(unittest.TestCase):
    def setUp(self):
        self.db = MockDB()
        self.rule = RuleClassifier()
        self.engine = IncrementalEngine(self.db, self.rule)

    def test_process_new_item(self):
        items = [_fake_item(name="react-starter", desc="A React starter kit", topics=["react"], lang="JavaScript")]
        stats = self.engine.process(items)
        self.assertEqual(stats["new"], 1)
        self.assertEqual(self.db.data["user/react-starter"].platform, "Web 前端")

    def test_process_existing_protected(self):
        self.db.set("user/repo", {
            "full_name": "user/repo",
            "name": "repo",
            "owner": "user",
            "manual_override": True,
            "stars": 5,
            "first_seen": "2024-01-01",
            "last_updated": "2024-01-01",
        })
        items = [_fake_item(name="repo", stars=100)]
        stats = self.engine.process(items, incremental=True)
        self.assertEqual(stats["protected"], 1)
        self.assertEqual(self.db.data["user/repo"].stars, 100)

    def test_force_refresh_updates(self):
        self.db.set("user/repo", {
            "full_name": "user/repo",
            "name": "repo",
            "owner": "user",
            "manual_override": False,
            "stars": 5,
            "first_seen": "2024-01-01",
            "last_updated": "2024-01-01",
            "platform": "旧分类",
            "type": "旧类型",
            "ecology": "旧生态",
        })
        items = [_fake_item(name="repo", desc="AI model training toolkit", topics=["pytorch", "machine-learning"], lang="Python")]
        stats = self.engine.process(items, force_refresh=True)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(self.db.data["user/repo"].platform, "AI / 机器学习")
        self.assertEqual(self.db.data["user/repo"].type, "工具 / Tool")

    def test_incremental_skip(self):
        self.db.set("user/repo", {
            "full_name": "user/repo",
            "name": "repo",
            "owner": "user",
            "manual_override": False,
            "stars": 5,
            "first_seen": "2024-01-01",
            "last_updated": "2024-01-01",
            "platform": "保留分类",
        })
        items = [_fake_item(name="repo", stars=200, desc="new desc", topics=["new"])]
        stats = self.engine.process(items, incremental=True)
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(self.db.data["user/repo"].stars, 200)
        self.assertEqual(self.db.data["user/repo"].platform, "保留分类")

    def test_llm_enhanced(self):
        llm = MagicMock()
        llm.classify_batch.return_value = {
            "user/repo": {
                "confidence": 0.9,
                "platform": "AI / 人工智能",
                "type": "模型 / Model",
                "ecology": "PyTorch",
                "ecology_role": "核心",
            }
        }
        engine = IncrementalEngine(self.db, self.rule, llm)
        items = [_fake_item(name="repo", desc="Neural net")]
        stats = engine.process(items, use_llm=True)
        self.assertEqual(stats["new"], 1)
        self.assertEqual(stats["llm_enhanced"], 1)
        self.assertEqual(self.db.data["user/repo"].platform, "AI / 人工智能")
        # AI 字段已迁移到独立 AI 数据库，不再写入 StarItem
        self.assertIn("user/repo", engine.llm_results)

    def test_llm_failed(self):
        llm = MagicMock()
        llm.classify_batch.return_value = {}
        engine = IncrementalEngine(self.db, self.rule, llm)
        items = [_fake_item(name="repo")]
        stats = engine.process(items, use_llm=True)
        self.assertEqual(stats["new"], 1)
        # AI 字段已迁移到独立 AI 数据库，不再写入 StarItem
        self.assertEqual(engine.llm_results, {})

    def test_ecology_locked(self):
        import config
        original = config.LOCKED_ECOLOGIES.copy()
        config.LOCKED_ECOLOGIES.append("PyTorch")
        try:
            llm = MagicMock()
            llm.classify_batch.return_value = {
                "user/repo": {
                    "confidence": 0.9,
                    "ecology": "TensorFlow",  # should be ignored
                    "platform": "AI / 人工智能",
                }
            }
            engine = IncrementalEngine(self.db, self.rule, llm)
            self.db.set("user/repo", {
                "full_name": "user/repo",
                "name": "repo",
                "owner": "user",
                "ecology": "PyTorch",
                "manual_override": False,
                "first_seen": "2024-01-01",
            })
            items = [_fake_item(name="repo")]
            stats = engine.process(items, force_refresh=True, use_llm=True)
            self.assertEqual(self.db.data["user/repo"].ecology, "PyTorch")
        finally:
            config.LOCKED_ECOLOGIES[:] = original

    def test_llm_skips_existing_within_interval(self):
        """增量模式下，已有项目如果在 AI 间隔内，LLM 应跳过"""
        from ai_database import AIDatabase, AIResult
        import tempfile
        tmpdir = tempfile.mkdtemp()
        ai_db = AIDatabase(os.path.join(tmpdir, "ai.json"))
        ai_db.set("user/repo", AIResult(
            full_name="user/repo",
            analyzed_at="2099-01-01T00:00:00+00:00",  # 未来时间，一定在间隔内
            llm_status="success",
        ))
        llm = MagicMock()
        engine = IncrementalEngine(self.db, self.rule, llm, ai_db)
        self.db.set("user/repo", {
            "full_name": "user/repo", "name": "repo", "owner": "user",
            "platform": "保留", "first_seen": "2024-01-01",
        })
        items = [_fake_item(name="repo")]
        stats = engine.process(items, incremental=True, use_llm=True, llm_interval_days=30)
        self.assertEqual(stats["skipped"], 1)
        llm.classify_batch.assert_not_called()

    def test_llm_reanalyzes_existing_outside_interval(self):
        """增量模式下，已有项目如果超过 AI 间隔，LLM 应重新分析"""
        from ai_database import AIDatabase, AIResult
        import tempfile
        tmpdir = tempfile.mkdtemp()
        ai_db = AIDatabase(os.path.join(tmpdir, "ai.json"))
        ai_db.set("user/repo", AIResult(
            full_name="user/repo",
            analyzed_at="2020-01-01T00:00:00+00:00",  # 很久以前，一定超过间隔
            llm_status="success",
        ))
        llm = MagicMock()
        llm.classify_batch.return_value = {"user/repo": {"confidence": 0.9, "platform": "AI"}}
        engine = IncrementalEngine(self.db, self.rule, llm, ai_db)
        self.db.set("user/repo", {
            "full_name": "user/repo", "name": "repo", "owner": "user",
            "platform": "旧分类", "first_seen": "2024-01-01",
        })
        items = [_fake_item(name="repo")]
        stats = engine.process(items, incremental=True, use_llm=True, llm_interval_days=30)
        # 增量模式下规则分类跳过，但 LLM 覆盖仍应用
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(self.db.data["user/repo"].platform, "AI")
        llm.classify_batch.assert_called_once()

    def test_error_handling(self):
        items = [{
            "name": "repo",
            "owner": None,  # will cause KeyError
        }]
        stats = self.engine.process(items)
        self.assertEqual(stats["error"], 1)

    def test_new_keys_tracks_only_new_items(self):
        """new_keys 应只包含本次运行实际新增的项目"""
        self.db.set("user/old", {
            "full_name": "user/old", "name": "old", "owner": "user",
            "first_seen": "2024-01-01", "last_updated": "2024-01-01",
        })
        items = [
            _fake_item(name="old"),  # 已有项目
            _fake_item(name="new"),  # 新项目
        ]
        stats = self.engine.process(items, force_refresh=True)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["new"], 1)
        self.assertEqual(self.engine.new_keys, {"user/new"})
        self.assertNotIn("user/old", self.engine.new_keys)

    def test_star_changes_tracked_for_existing(self):
        """star_changes 应记录已有项目的 stars 增长"""
        self.db.set("user/repo", {
            "full_name": "user/repo", "name": "repo", "owner": "user",
            "stars": 100, "first_seen": "2024-01-01", "last_updated": "2024-01-01",
        })
        items = [_fake_item(name="repo", stars=150)]
        stats = self.engine.process(items, incremental=True)
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(self.engine.star_changes.get("user/repo"), 50)

    def test_star_changes_not_tracked_when_no_growth(self):
        """stars 没有增长时不应记录"""
        self.db.set("user/repo", {
            "full_name": "user/repo", "name": "repo", "owner": "user",
            "stars": 100, "first_seen": "2024-01-01", "last_updated": "2024-01-01",
        })
        items = [_fake_item(name="repo", stars=100)]
        stats = self.engine.process(items, incremental=True)
        self.assertEqual(stats["skipped"], 1)
        self.assertNotIn("user/repo", self.engine.star_changes)
