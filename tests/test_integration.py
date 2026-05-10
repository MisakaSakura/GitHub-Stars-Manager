#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""集成测试：验证 StarItem 与 report / tracker 的真实交互"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from models import StarItem
from database import StarsDB
from report import ReportGenerator
from release_tracker import ReleaseTracker


class MockGitHubAPI:
    """模拟 GitHub API，用于 tracker 测试"""

    def __init__(self, releases=None, repo_info=None):
        self._releases = releases or {}
        self._repo_info = repo_info or {}

    def get_latest_release(self, owner, repo):
        return self._releases.get(f"{owner}/{repo}")

    def get_repo_info(self, owner, repo):
        return self._repo_info.get(f"{owner}/{repo}")


class TestReportGeneratorWithStarItem(unittest.TestCase):
    """验证 ReportGenerator 能正确处理真实的 StarItem 对象"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_db.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_item(self, **kwargs):
        defaults = {
            "full_name": "owner/repo",
            "name": "repo",
            "owner": "owner",
            "description": "A test repo",
            "language": "Python",
            "platform": "CLI / 终端",
            "type": "工具 / Tool",
            "ecology": "独立项目 / Standalone",
            "ecology_role": "-",
            "topics": ["cli", "tool"],
            "stars": 100,
            "url": "https://github.com/owner/repo",
            "first_seen": "2024-01-01T00:00:00+00:00",
            "last_updated": "2024-01-01T00:00:00+00:00",
        }
        defaults.update(kwargs)
        return StarItem(**defaults)

    def test_generate_html_with_stars_db(self):
        """HTML 报告：真实 StarsDB + StarItem 不崩溃"""
        db = StarsDB(self.db_path)
        db.set("owner/repo", self._make_item())
        db.set("owner/repo2", self._make_item(full_name="owner/repo2", name="repo2", stars=200))
        db.save()

        # 重新加载，验证数据库能正确反序列化
        db2 = StarsDB(self.db_path)
        report = ReportGenerator(db2)
        output_dir = os.path.join(self.tmpdir, "docs")
        path = report.generate_html(output_dir)

        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("owner/repo", html)
        self.assertIn("owner/repo2", html)

    def test_generate_csv_with_stars_db(self):
        """CSV 报告：真实 StarsDB + StarItem 不崩溃"""
        db = StarsDB(self.db_path)
        db.set("owner/repo", self._make_item())
        db.save()

        report = ReportGenerator(db)
        output_dir = os.path.join(self.tmpdir, "docs")
        path = report.generate_csv(output_dir)

        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("owner/repo", content)
        self.assertIn("Python", content)

    def test_generate_json_with_stars_db(self):
        """JSON 报告：真实 StarsDB + StarItem 可序列化"""
        db = StarsDB(self.db_path)
        db.set("owner/repo", self._make_item())
        db.save()

        report = ReportGenerator(db)
        output_dir = os.path.join(self.tmpdir, "docs")
        path = report.generate_json(output_dir)

        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["meta"]["total"], 1)
        self.assertEqual(len(data["repos"]), 1)
        self.assertEqual(data["repos"][0]["full_name"], "owner/repo")
        # 验证序列化后是普通 dict，不是 dataclass
        self.assertIsInstance(data["repos"][0], dict)

    def test_html_with_fork_and_llm_fields(self):
        """HTML 报告：含 Fork、LLM 字段的 StarItem 正确渲染"""
        db = StarsDB(self.db_path)
        db.set("owner/repo", self._make_item(
            is_fork=True,
            parent_full_name="upstream/original",
            parent_pushed_at="2024-06-01T00:00:00Z",
            llm_status="success",
            ai_summary="AI generated summary",
            ai_tags=["tag1", "tag2"],
            ai_platforms=["linux", "mac"],
        ))
        db.save()

        report = ReportGenerator(db)
        output_dir = os.path.join(self.tmpdir, "docs")
        path = report.generate_html(output_dir)

        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("upstream/original", html)
        self.assertIn("AI generated summary", html)
        # 验证 emoji 被正确渲染
        self.assertIn("🤖", html)


class TestReleaseTrackerWithStarItem(unittest.TestCase):
    """验证 ReleaseTracker 能正确修改真实的 StarItem 对象"""

    def test_check_updates_staritem_attributes(self):
        """ReleaseTracker 应能通过 dict 语法修改 StarItem"""
        item = StarItem(
            full_name="owner/repo",
            name="repo",
            owner="owner",
            subscribe_releases=True,
            last_release_tag="v1.0.0",
        )
        gh = MockGitHubAPI(releases={
            "owner/repo": {
                "tag_name": "v2.0.0",
                "published_at": "2024-06-01T00:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/v2.0.0",
            }
        })
        tracker = ReleaseTracker(gh)
        updates = tracker.check([item])

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["new_tag"], "v2.0.0")
        # 验证 StarItem 被正确修改（通过 __setitem__）
        self.assertEqual(item["last_release_tag"], "v2.0.0")
        self.assertEqual(item.last_release_tag, "v2.0.0")
        self.assertIsNotNone(item.get("last_release_checked"))

    def test_check_no_subscription_skips(self):
        """未订阅的 StarItem 应被跳过"""
        item = StarItem(
            full_name="owner/repo",
            name="repo",
            owner="owner",
            subscribe_releases=False,
        )
        tracker = ReleaseTracker(MockGitHubAPI())
        updates = tracker.check([item])
        self.assertEqual(len(updates), 0)


if __name__ == "__main__":
    unittest.main()
