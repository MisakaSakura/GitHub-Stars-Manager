#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量更新引擎单元测试"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from engine import IncrementalEngine, EngineConfig, _is_ecology_locked, _safe_int
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
        self.assertFalse(_is_ecology_locked("独立项目"))


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
        stats = self.engine.process(EngineConfig(items=items))
        self.assertEqual(stats["new"], 1)
        # "Web 前端" 已移至 type，platform 现在只匹配操作系统/运行时
        self.assertEqual(self.db.data["user/react-starter"].platform, "其他 / 未分类")
        self.assertEqual(self.db.data["user/react-starter"].type, "Web 前端")

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
        stats = self.engine.process(EngineConfig(items=items, incremental=True))
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
        stats = self.engine.process(EngineConfig(items=items, force_refresh=True))
        self.assertEqual(stats["updated"], 1)
        # "AI / 机器学习" 已从 platform 移除，现 platform 只匹配操作系统/运行时
        self.assertEqual(self.db.data["user/repo"].platform, "其他 / 未分类")
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
        stats = self.engine.process(EngineConfig(items=items, incremental=True))
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
        stats = engine.process(EngineConfig(items=items, use_llm=True))
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
        stats = engine.process(EngineConfig(items=items, use_llm=True))
        self.assertEqual(stats["new"], 1)
        # AI 字段已迁移到独立 AI 数据库，不再写入 StarItem
        self.assertEqual(engine.llm_results, {})

    @patch("engine.LOCKED_ECOLOGIES", ["PyTorch"])
    def test_ecology_locked(self):
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
        stats = engine.process(EngineConfig(items=items, force_refresh=True, use_llm=True))
        self.assertEqual(self.db.data["user/repo"].ecology, "PyTorch")

    def test_llm_skips_existing_within_interval(self):
        """增量模式下，已有项目如果在 AI 间隔内，LLM 应跳过"""
        from ai_database import AIDatabase, AIResult
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
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
            stats = engine.process(EngineConfig(items=items, incremental=True, use_llm=True, llm_interval_days=30))
            self.assertEqual(stats["skipped"], 1)
            llm.classify_batch.assert_not_called()

    def test_llm_reanalyzes_existing_outside_interval(self):
        """增量模式下，已有项目如果超过 AI 间隔，LLM 应重新分析"""
        from ai_database import AIDatabase, AIResult
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
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
            stats = engine.process(EngineConfig(items=items, incremental=True, use_llm=True, llm_interval_days=30))
            # 增量模式下规则分类跳过，但 LLM 覆盖仍应用
            self.assertEqual(stats["skipped"], 1)
            self.assertEqual(self.db.data["user/repo"].platform, "AI")
            llm.classify_batch.assert_called_once()

    def test_error_handling(self):
        items = [{
            "name": "repo",
            "owner": None,  # will cause KeyError
        }]
        stats = self.engine.process(EngineConfig(items=items))
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
        stats = self.engine.process(EngineConfig(items=items, force_refresh=True))
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
        stats = self.engine.process(EngineConfig(items=items, incremental=True))
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(self.engine.star_changes.get("user/repo"), 50)

    def test_star_changes_not_tracked_when_no_growth(self):
        """stars 没有增长时不应记录"""
        self.db.set("user/repo", {
            "full_name": "user/repo", "name": "repo", "owner": "user",
            "stars": 100, "first_seen": "2024-01-01", "last_updated": "2024-01-01",
        })
        items = [_fake_item(name="repo", stars=100)]
        stats = self.engine.process(EngineConfig(items=items, incremental=True))
        self.assertEqual(stats["skipped"], 1)
        self.assertNotIn("user/repo", self.engine.star_changes)


class TestPreclassify(unittest.TestCase):
    """P1: 预分类增强测试"""

    def test_preclassify_with_topics_match(self):
        """topics 命中 PRECLASSIFY_RULES 时应返回对应生态"""
        item = _fake_item(name="my-plugin", topics=["neovim", "vim"])
        result = IncrementalEngine._preclassify_item(item)
        self.assertIn("ecology", result)
        self.assertEqual(result["ecology"], "Neovim")
        self.assertIn("type", result)
        self.assertEqual(result["type"], "编辑器 / IDE")

    def test_preclassify_with_name_match(self):
        """项目名精确命中 core_projects 时应返回对应生态"""
        item = _fake_item(name="alacritty", topics=["terminal"])
        result = IncrementalEngine._preclassify_item(item)
        self.assertIn("ecology", result)
        self.assertEqual(result["ecology"], "Alacritty")

    def test_preclassify_no_match_returns_empty(self):
        """无命中时应返回空 dict"""
        item = _fake_item(name="random-repo", topics=["unknown-topic"])
        result = IncrementalEngine._preclassify_item(item)
        self.assertEqual(result, {})

    def test_preclassify_case_insensitive(self):
        """topics 和名称匹配应大小写不敏感"""
        item = _fake_item(name="MY-APP", topics=["NEOVIM"])
        result = IncrementalEngine._preclassify_item(item)
        self.assertIn("ecology", result)
        self.assertEqual(result["ecology"], "Neovim")

    def test_attach_preclassify_sets_field(self):
        """_attach_preclassify 应正确设置 item['_preclassify']"""
        items = [
            _fake_item(name="nvim-treesitter", topics=["neovim"]),
            _fake_item(name="random", topics=["unknown"]),
        ]
        engine = IncrementalEngine(MockDB(), RuleClassifier())
        engine._attach_preclassify(items)

        self.assertIn("_preclassify", items[0])
        self.assertEqual(items[0]["_preclassify"]["ecology"], "Neovim")

        self.assertNotIn("_preclassify", items[1])

    def test_preclassify_does_not_override_manual(self):
        """预分类不影响 manual_override 项目的规则分类"""
        db = MockDB()
        db.set("user/nvim-plugin", {
            "full_name": "user/nvim-plugin", "name": "nvim-plugin", "owner": "user",
            "manual_override": True, "platform": "跨平台", "type": "插件 / Plugin",
            "ecology": "Neovim", "ecology_role": "插件 / Plugin",
            "first_seen": "2024-01-01",
        })
        engine = IncrementalEngine(db, RuleClassifier())
        items = [_fake_item(name="nvim-plugin", topics=["neovim"])]
        stats = engine.process(EngineConfig(items=items, incremental=True))
        self.assertEqual(stats["protected"], 1)
        self.assertEqual(db.data["user/nvim-plugin"].ecology, "Neovim")


class TestConsistencyCheck(unittest.TestCase):
    """P3: 分类一致性自检测试"""

    def test_editor_ecology_needs_desktop_platform(self):
        """编辑器生态但平台为 Web 时应标记可疑"""
        from config_rules import check_consistency
        item = {
            "ecology": "Neovim", "platform": "Web",
            "type": "编辑器 / IDE", "stars": 1000,
            "ecology_role": "核心 / Core", "name": "nvim-plugin",
            "topics": ["neovim"],
        }
        is_sus, flags = check_consistency(item)
        self.assertTrue(is_sus)
        self.assertTrue(any("编辑器" in f for f in flags))

    def test_editor_ecology_desktop_platform_ok(self):
        """编辑器生态 + 桌面平台不应标记"""
        from config_rules import check_consistency
        item = {
            "ecology": "Neovim", "platform": "跨平台",
            "type": "编辑器 / IDE", "stars": 1000,
            "ecology_role": "核心 / Core", "name": "nvim-plugin",
            "topics": ["neovim"],
        }
        is_sus, flags = check_consistency(item)
        self.assertFalse(is_sus)
        self.assertEqual(flags, [])

    def test_proxy_tool_needs_tool_type(self):
        """代理工具生态但类型为框架时应标记可疑"""
        from config_rules import check_consistency
        item = {
            "ecology": "Clash / Mihomo", "platform": "跨平台",
            "type": "框架 / Framework", "stars": 1000,
            "ecology_role": "核心 / Core", "name": "clash-core",
            "topics": ["clash"],
        }
        is_sus, flags = check_consistency(item)
        self.assertTrue(is_sus)
        self.assertTrue(any("工具生态" in f for f in flags))

    def test_framework_with_low_stars(self):
        """框架类型但 stars 过少应标记可疑"""
        from config_rules import check_consistency
        item = {
            "ecology": "独立项目", "platform": "跨平台",
            "type": "框架 / Framework", "stars": 10,
            "ecology_role": "-", "name": "tiny-lib",
            "topics": ["library"],
        }
        is_sus, flags = check_consistency(item)
        self.assertTrue(is_sus)
        self.assertTrue(any("stars 过少" in f for f in flags))

    def test_core_role_with_low_stars(self):
        """核心角色但 stars 过少应标记可疑"""
        from config_rules import check_consistency
        item = {
            "ecology": "Docker", "platform": "Linux",
            "type": "工具 / Tool", "stars": 20,
            "ecology_role": "核心 / Core", "name": "docker-lite",
            "topics": ["docker"],
        }
        is_sus, flags = check_consistency(item)
        self.assertTrue(is_sus)
        self.assertTrue(any("核心角色" in f for f in flags))

    def test_independent_but_name_matches_eco(self):
        """独立项目但名称命中生态规则应标记可疑"""
        from config_rules import check_consistency
        item = {
            "ecology": "独立项目", "platform": "跨平台",
            "type": "工具 / Tool", "stars": 500,
            "ecology_role": "-", "name": "alacritty-theme",
            "topics": ["terminal"],
        }
        is_sus, flags = check_consistency(item)
        self.assertTrue(is_sus)
        self.assertTrue(any("名称" in f for f in flags))

    def test_normal_item_not_suspicious(self):
        """正常项目不应被标记"""
        from config_rules import check_consistency
        item = {
            "ecology": "Neovim", "platform": "跨平台",
            "type": "插件 / Plugin", "stars": 500,
            "ecology_role": "插件 / Plugin", "name": "nvim-treesitter",
            "topics": ["neovim", "treesitter"],
        }
        is_sus, flags = check_consistency(item)
        self.assertFalse(is_sus)
        self.assertEqual(flags, [])
