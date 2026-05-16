#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ReleaseTracker / ForkTracker 单元测试"""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from release_tracker import ReleaseTracker
from fork_tracker import ForkTracker


def _future_date(days: int = 1) -> str:
    """生成动态未来日期，避免硬编码 2099 年时间炸弹"""
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")


class TestReleaseTracker(unittest.TestCase):
    def test_check_no_subscription(self):
        gh = MagicMock()
        tracker = ReleaseTracker(gh)
        items = [{"full_name": "a/b", "subscribe_releases": False}]
        result = tracker.check(items)
        self.assertEqual(result, [])
        gh.list_releases.assert_not_called()

    def test_check_new_release(self):
        gh = MagicMock()
        gh.list_releases.return_value = [
            {"tag_name": "v2.0", "published_at": _future_date(), "html_url": "https://github.com/a/b/releases/v2.0"},
        ]
        tracker = ReleaseTracker(gh)
        items = [{
            "full_name": "a/b",
            "name": "b",
            "subscribe_releases": True,
            "last_release_tag": "v1.0",
        }]
        result = tracker.check(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["new_tag"], "v2.0")
        self.assertEqual(result[0]["old_tag"], "v1.0")

    def test_check_no_change(self):
        gh = MagicMock()
        gh.list_releases.return_value = [
            {"tag_name": "v1.0", "published_at": _future_date()},
        ]
        tracker = ReleaseTracker(gh)
        items = [{
            "full_name": "a/b",
            "name": "b",
            "subscribe_releases": True,
            "last_release_tag": "v1.0",
        }]
        result = tracker.check(items)
        self.assertEqual(result, [])

    def test_format_report(self):
        gh = MagicMock()
        tracker = ReleaseTracker(gh)
        updates = [{"owner": "a", "name": "b", "old_tag": "v1", "new_tag": "v2"}]
        text = tracker.format_report(updates)
        self.assertIn("v1", text)
        self.assertIn("v2", text)

    def test_check_multiple_releases_in_week(self):
        """一周内多次发布应全部捕获，intermediate_tags 记录中间版本"""
        gh = MagicMock()
        gh.list_releases.return_value = [
            {"tag_name": "v1.3", "published_at": _future_date(3), "html_url": "https://github.com/a/b/releases/v1.3"},
            {"tag_name": "v1.2", "published_at": _future_date(2), "html_url": "https://github.com/a/b/releases/v1.2"},
            {"tag_name": "v1.1", "published_at": _future_date(1), "html_url": "https://github.com/a/b/releases/v1.1"},
            {"tag_name": "v1.0", "published_at": "2024-01-01T00:00:00Z", "html_url": "https://github.com/a/b/releases/v1.0"},
        ]
        tracker = ReleaseTracker(gh)
        items = [{
            "full_name": "a/b",
            "name": "b",
            "subscribe_releases": True,
            "last_release_tag": "v1.0",
        }]
        result = tracker.check(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["new_tag"], "v1.3")
        self.assertEqual(result[0]["old_tag"], "v1.0")
        self.assertEqual(result[0]["intermediate_tags"], ["v1.2", "v1.1"])

    # --- check_all tests ---

    def test_check_all_ignores_subscription_flag(self):
        gh = MagicMock()
        gh.list_releases.return_value = [
            {"tag_name": "v2.0", "published_at": _future_date(), "html_url": "https://github.com/a/b/releases/v2.0"},
        ]
        tracker = ReleaseTracker(gh)
        items = [{
            "full_name": "a/b",
            "name": "b",
            "subscribe_releases": False,
            "last_release_tag": "v1.0",
        }]
        result = tracker.check_all(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["new_tag"], "v2.0")

    def test_check_all_baseline_first_discovery(self):
        """首次发现的项目，最新 release 在窗口内时，应作为新收录动态展示"""
        gh = MagicMock()
        gh.list_releases.return_value = [
            {"tag_name": "v1.0", "published_at": _future_date(), "html_url": "https://github.com/a/b/releases/v1.0"},
        ]
        from datetime import datetime, timezone
        tracker = ReleaseTracker(gh)
        items = [{
            "full_name": "a/b",
            "name": "b",
            "subscribe_releases": False,
            "first_seen": datetime.now(timezone.utc).isoformat(),
        }]
        result = tracker.check_all(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["new_tag"], "v1.0")
        self.assertEqual(result[0]["old_tag"], None)
        self.assertEqual(result[0]["is_new_repo"], True)
        self.assertEqual(items[0]["last_release_tag"], "v1.0")

    def test_check_all_baseline_old_release_not_in_window(self):
        """首次发现的项目，最新 release 不在窗口内时，不产生 update"""
        import datetime as dt
        from datetime import timezone
        old_date = (dt.datetime.now(timezone.utc) - dt.timedelta(days=30)).isoformat()
        gh = MagicMock()
        gh.list_releases.return_value = [
            {"tag_name": "v1.0", "published_at": old_date, "html_url": "https://github.com/a/b/releases/v1.0"},
        ]
        tracker = ReleaseTracker(gh)
        items = [{
            "full_name": "a/b",
            "name": "b",
        }]
        result = tracker.check_all(items)
        self.assertEqual(result, [])
        self.assertEqual(items[0]["last_release_tag"], "v1.0")

    def test_check_all_no_change(self):
        gh = MagicMock()
        gh.list_releases.return_value = [
            {"tag_name": "v1.0", "published_at": _future_date()},
        ]
        tracker = ReleaseTracker(gh)
        items = [{
            "full_name": "a/b",
            "name": "b",
            "last_release_tag": "v1.0",
        }]
        result = tracker.check_all(items)
        self.assertEqual(result, [])


class TestForkTracker(unittest.TestCase):
    def test_get_user_forks(self):
        gh = MagicMock()
        gh.get_user_repos.return_value = [
            {"name": "f1", "fork": True},
            {"name": "f2", "fork": False},
        ]
        tracker = ForkTracker(gh)
        result = tracker.get_user_forks("user")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "f1")

    def test_check_upstream_update(self):
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        gh = MagicMock()
        gh.get_repo_info.return_value = {
            "parent": {
                "full_name": "upstream/repo",
                "pushed_at": recent,
            },
            "pushed_at": old,
        }
        tracker = ForkTracker(gh)
        forks = [{"full_name": "user/repo", "pushed_at": old}]
        result = tracker.check(forks)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["parent_full_name"], "upstream/repo")

    def test_check_no_parent(self):
        gh = MagicMock()
        gh.get_repo_info.return_value = {"parent": None}
        tracker = ForkTracker(gh)
        forks = [{"full_name": "user/repo"}]
        result = tracker.check(forks)
        self.assertEqual(result, [])

    def test_check_no_update(self):
        gh = MagicMock()
        gh.get_repo_info.return_value = {
            "parent": {"full_name": "upstream/repo", "pushed_at": "2024-01-01T00:00:00Z"},
            "pushed_at": "2024-06-01T00:00:00Z",
        }
        tracker = ForkTracker(gh)
        forks = [{"full_name": "user/repo", "pushed_at": "2024-06-01T00:00:00Z"}]
        result = tracker.check(forks)
        self.assertEqual(result, [])

    def test_format_report(self):
        gh = MagicMock()
        tracker = ForkTracker(gh)
        updates = [{"full_name": "user/repo", "parent_full_name": "upstream/repo", "parent_pushed_at": "2024-06-01T00:00:00Z"}]
        text = tracker.format_report(updates)
        self.assertIn("upstream/repo", text)
