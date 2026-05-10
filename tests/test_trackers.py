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


class TestReleaseTracker(unittest.TestCase):
    def test_check_no_subscription(self):
        gh = MagicMock()
        tracker = ReleaseTracker(gh)
        items = [{"full_name": "a/b", "subscribe_releases": False}]
        result = tracker.check(items)
        self.assertEqual(result, [])
        gh.get_latest_release.assert_not_called()

    def test_check_new_release(self):
        gh = MagicMock()
        gh.get_latest_release.return_value = {
            "tag_name": "v2.0",
            "published_at": "2024-01-01T00:00:00Z",
            "html_url": "https://github.com/a/b/releases/v2.0",
        }
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
        gh.get_latest_release.return_value = {"tag_name": "v1.0"}
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
        gh = MagicMock()
        gh.get_repo_info.return_value = {
            "parent": {
                "full_name": "upstream/repo",
                "pushed_at": "2024-06-01T00:00:00Z",
            },
            "pushed_at": "2024-01-01T00:00:00Z",
        }
        tracker = ForkTracker(gh)
        forks = [{"full_name": "user/repo", "pushed_at": "2024-01-01T00:00:00Z"}]
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
