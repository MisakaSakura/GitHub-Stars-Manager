#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FeedbackLoop 单元测试"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from feedback_loop import FeedbackLoop
from models import StarItem


class MockDB:
    """内存数据库 mock"""
    def __init__(self, items=None):
        self._data = items or {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value

    def items(self):
        return self._data.items()


@patch("feedback_loop.FeedbackLoop._current_rules_version", return_value="test-v1")
class TestFeedbackLoopVersionControl(unittest.TestCase):
    """测试规则版本控制核心逻辑"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.fb_path = os.path.join(self.tmpdir, "feedback.json")

    def tearDown(self):
        for f in [self.fb_path, self.fb_path + ".tmp", self.fb_path + ".lock"]:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(self.tmpdir):
            os.rmdir(self.tmpdir)

    def test_record_includes_rules_version(self, _mock):
        fb = FeedbackLoop(self.fb_path)
        fb.record(
            "user/repo",
            {"platform": "old", "type": "old"},
            {"platform": "new", "type": "new"},
            source="manual"
        )
        entry = fb.entries["user/repo"]
        self.assertEqual(entry["rules_version"], "test-v1")

    def test_load_save_rules_version(self, _mock):
        fb = FeedbackLoop(self.fb_path)
        fb.record("user/repo", {"platform": "old"}, {"platform": "new"})
        fb.save()

        fb2 = FeedbackLoop(self.fb_path)
        self.assertEqual(fb2.rules_version, "test-v1")
        self.assertEqual(fb2.entries["user/repo"]["rules_version"], "test-v1")

    def test_get_correction_same_version_returns_full(self, _mock):
        fb = FeedbackLoop(self.fb_path)
        fb.record(
            "user/repo",
            {"platform": "old", "type": "old", "ecology": "old"},
            {"platform": "new", "type": "new", "ecology": "new"},
        )
        result = fb.get_correction("user/repo")
        self.assertEqual(result, {"platform": "new", "type": "new", "ecology": "new"})

    def test_get_correction_version_mismatch_removes_platform_type(self, _mock):
        """版本不一致时，platform/type 修正应被忽略"""
        fb = FeedbackLoop(self.fb_path)
        fb.entries["user/repo"] = {
            "corrected": {"platform": "new", "type": "new", "ecology": "new"},
            "rules_version": "old-version",
        }
        result = fb.get_correction("user/repo")
        self.assertEqual(result, {"ecology": "new"})

    def test_get_correction_version_mismatch_ecology_preserved(self, _mock):
        """版本不一致时，ecology 修正应被保留"""
        fb = FeedbackLoop(self.fb_path)
        fb.entries["user/repo"] = {
            "corrected": {"ecology": "new", "ecology_role": "new_role"},
            "rules_version": "old-version",
        }
        result = fb.get_correction("user/repo")
        self.assertEqual(result, {"ecology": "new", "ecology_role": "new_role"})

    def test_get_correction_version_mismatch_only_pt_returns_none(self, _mock):
        """版本不一致且只有 platform/type 修正时，应返回 None"""
        fb = FeedbackLoop(self.fb_path)
        fb.entries["user/repo"] = {
            "corrected": {"platform": "new", "type": "new"},
            "rules_version": "old-version",
        }
        result = fb.get_correction("user/repo")
        self.assertIsNone(result)

    def test_get_correction_no_entry_returns_none(self, _mock):
        fb = FeedbackLoop(self.fb_path)
        self.assertIsNone(fb.get_correction("nonexistent/repo"))

    def test_get_correction_empty_version_treated_as_compatible(self, _mock):
        """旧反馈条目（无 rules_version）视为兼容，返回完整修正"""
        fb = FeedbackLoop(self.fb_path)
        fb.entries["user/repo"] = {
            "corrected": {"platform": "new", "type": "new"},
            "rules_version": "",
        }
        result = fb.get_correction("user/repo")
        self.assertEqual(result, {"platform": "new", "type": "new"})


@patch("feedback_loop.FeedbackLoop._current_rules_version", return_value="test-v2")
@patch("config_rules.RULES_VERSION", "test-v2")
class TestDetectOverrideConflicts(unittest.TestCase):
    """测试 manual_override 冲突检测"""

    def _make_item(self, full_name, platform="其他 / 未分类", type_="其他 / 未分类",
                   ecology="独立项目", ecology_role="其他 / Other",
                   manual_override=True, override_rules_version="test-v1"):
        return StarItem(
            full_name=full_name, name=full_name.split("/")[1],
            owner=full_name.split("/")[0],
            platform=platform, type=type_,
            ecology=ecology, ecology_role=ecology_role,
            manual_override=manual_override,
            override_rules_version=override_rules_version,
        )

    def test_no_conflicts_when_all_match(self, _mock):
        fb = FeedbackLoop("/dev/null")
        db = MockDB({
            "user/repo": self._make_item(
                "user/repo",
                platform="其他 / 未分类", type_="其他 / 未分类",
                ecology="独立项目", ecology_role="其他 / Other",
            )
        })
        conflicts = fb.detect_override_conflicts(db)
        self.assertEqual(len(conflicts), 0)

    def test_warn_when_version_matches_but_fields_differ(self, _mock):
        """版本一致但存在差异 → warn"""
        fb = FeedbackLoop("/dev/null")
        db = MockDB({
            "user/repo": self._make_item(
                "user/repo",
                platform="Windows", type_="工具 / Tool",
                ecology="独立项目",
                override_rules_version="test-v2",  # 与当前版本一致
            )
        })
        conflicts = fb.detect_override_conflicts(db)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["severity"], "warn")
        self.assertFalse(conflicts[0]["is_version_mismatch"])
        # 确认有 platform 冲突
        fields = [f["field"] for f in conflicts[0]["conflict_fields"]]
        self.assertIn("platform", fields)

    def test_critical_when_version_mismatch_and_pt_conflict(self, _mock):
        """版本不一致 + platform/type 冲突 → critical"""
        fb = FeedbackLoop("/dev/null")
        db = MockDB({
            "user/repo": self._make_item(
                "user/repo",
                platform="Windows", type_="工具 / Tool",
                ecology="独立项目",
                override_rules_version="test-v1",
            )
        })
        conflicts = fb.detect_override_conflicts(db)
        critical = [c for c in conflicts if c["severity"] == "critical"]
        self.assertEqual(len(critical), 1)
        self.assertTrue(critical[0]["is_version_mismatch"])
        fields = [f["field"] for f in critical[0]["conflict_fields"]]
        self.assertIn("platform", fields)

    def test_info_when_version_mismatch_and_only_ecology_conflict(self, _mock):
        """版本不一致但仅 ecology 冲突 → info"""
        fb = FeedbackLoop("/dev/null")
        db = MockDB({
            "user/repo": self._make_item(
                "user/repo",
                platform="其他 / 未分类", type_="其他 / 未分类",
                ecology="CustomEco",
                override_rules_version="test-v1",
            )
        })
        conflicts = fb.detect_override_conflicts(db)
        info_conflicts = [c for c in conflicts if c["severity"] == "info"]
        self.assertEqual(len(info_conflicts), 1)
        self.assertTrue(info_conflicts[0]["is_version_mismatch"])
        fields = [f["field"] for f in info_conflicts[0]["conflict_fields"]]
        self.assertEqual(fields, ["ecology"])

    def test_skips_non_manual_override(self, _mock):
        fb = FeedbackLoop("/dev/null")
        db = MockDB({
            "user/repo": self._make_item(
                "user/repo",
                manual_override=False,
            )
        })
        conflicts = fb.detect_override_conflicts(db)
        self.assertEqual(len(conflicts), 0)


class TestGenerateConflictReport(unittest.TestCase):
    """测试冲突报告生成"""

    def test_empty_conflicts_returns_empty(self):
        fb = FeedbackLoop("/dev/null")
        self.assertEqual(fb.generate_conflict_report([]), "")

    def test_generates_markdown_with_all_severities(self):
        fb = FeedbackLoop("/dev/null")
        conflicts = [
            {
                "full_name": "user/critical",
                "current": {"platform": "Windows"},
                "rules_suggest": {"platform": "跨平台"},
                "conflict_fields": [{"field": "platform", "current": "Windows", "rules_suggest": "跨平台"}],
                "rules_version": "v1",
                "is_version_mismatch": True,
                "severity": "critical",
            },
            {
                "full_name": "user/warn",
                "current": {"type": "工具 / Tool"},
                "rules_suggest": {"type": "应用 / App"},
                "conflict_fields": [{"field": "type", "current": "工具 / Tool", "rules_suggest": "应用 / App"}],
                "rules_version": "v2",
                "is_version_mismatch": False,
                "severity": "warn",
            },
            {
                "full_name": "user/info",
                "current": {"ecology": "Custom"},
                "rules_suggest": {"ecology": "独立项目"},
                "conflict_fields": [{"field": "ecology", "current": "Custom", "rules_suggest": "独立项目"}],
                "rules_version": "v1",
                "is_version_mismatch": True,
                "severity": "info",
            },
        ]
        report = fb.generate_conflict_report(conflicts)
        self.assertIn("## ⚠️ Manual Override 冲突检测", report)
        self.assertIn("### 🔴 严重", report)
        self.assertIn("user/critical", report)
        self.assertIn("### 🟡 警告", report)
        self.assertIn("user/warn", report)
        self.assertIn("### 🟢 提示", report)
        self.assertIn("user/info", report)
        self.assertIn("规则版本: `v1`", report)


@patch("feedback_loop.FeedbackLoop._current_rules_version", return_value="test-v2")
class TestScanManualOverrides(unittest.TestCase):
    """测试 scan_manual_overrides 版本更新"""

    def _make_item(self, **kwargs):
        defaults = {
            "full_name": "user/repo",
            "name": "repo",
            "owner": "user",
            "platform": "其他 / 未分类",
            "type": "其他 / 未分类",
            "ecology": "独立项目",
            "ecology_role": "其他 / Other",
            "manual_override": True,
            "override_rules_version": "",
        }
        defaults.update(kwargs)
        return StarItem(**defaults)

    def test_updates_missing_version(self, _mock):
        fb = FeedbackLoop("/dev/null")
        item = self._make_item(override_rules_version="")
        db = MockDB({"user/repo": item})
        fb.scan_manual_overrides(db)
        self.assertEqual(item.override_rules_version, "test-v2")

    def test_updates_different_version(self, _mock):
        fb = FeedbackLoop("/dev/null")
        item = self._make_item(override_rules_version="test-v1")
        db = MockDB({"user/repo": item})
        fb.scan_manual_overrides(db)
        self.assertEqual(item.override_rules_version, "test-v2")

    def test_skips_same_version(self, _mock):
        fb = FeedbackLoop("/dev/null")
        item = self._make_item(override_rules_version="test-v2")
        db = MockDB({"user/repo": item})
        fb.scan_manual_overrides(db)
        self.assertEqual(item.override_rules_version, "test-v2")

    def test_skips_non_manual_override(self, _mock):
        fb = FeedbackLoop("/dev/null")
        item = self._make_item(manual_override=False, override_rules_version="")
        db = MockDB({"user/repo": item})
        fb.scan_manual_overrides(db)
        self.assertEqual(item.override_rules_version, "")


@patch("database.RULES_VERSION", "test-v1")
class TestStarsDBVersionBehavior(unittest.TestCase):
    """测试 StarsDB.set() 不再自动填充规则版本（P1-10: 版本填充已移到上层调用者）"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_db.json")

    def tearDown(self):
        for f in [self.db_path, self.db_path + ".tmp"]:
            if os.path.exists(f):
                os.remove(f)
        meta = os.path.splitext(self.db_path)[0] + ".meta.json"
        if os.path.exists(meta):
            os.remove(meta)
        if os.path.exists(self.tmpdir):
            os.rmdir(self.tmpdir)

    def test_does_not_auto_fill_version(self):
        """set() 不再自动填充版本，上层调用者负责设置"""
        from database import StarsDB
        db = StarsDB(self.db_path)
        item = {
            "full_name": "user/repo", "name": "repo", "owner": "user",
            "manual_override": True,
        }
        db.set("user/repo", item)
        self.assertEqual(db.get("user/repo").override_rules_version, "")

    def test_preserves_empty_version(self):
        """非保护项目也不自动填充版本"""
        from database import StarsDB
        db = StarsDB(self.db_path)
        item = {
            "full_name": "user/repo", "name": "repo", "owner": "user",
            "manual_override": False,
        }
        db.set("user/repo", item)
        self.assertEqual(db.get("user/repo").override_rules_version, "")

    def test_preserves_existing_version(self):
        """已有版本不会被覆盖"""
        from database import StarsDB
        db = StarsDB(self.db_path)
        item = StarItem(
            full_name="user/repo", name="repo", owner="user",
            manual_override=True, override_rules_version="existing-version",
        )
        db.set("user/repo", item)
        self.assertEqual(db.get("user/repo").override_rules_version, "existing-version")


if __name__ == "__main__":
    unittest.main()
