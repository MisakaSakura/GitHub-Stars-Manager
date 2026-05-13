#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据模型单元测试"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from models import StarItem


class TestStarItem(unittest.TestCase):
    def test_from_github_api(self):
        api_item = {
            "name": "repo",
            "owner": {"login": "user"},
            "description": "A test repo",
            "language": "Python",
            "topics": ["web", "api"],
            "stargazers_count": 100,
            "html_url": "https://github.com/user/repo",
            "fork": False,
        }
        star = StarItem.from_github_api(api_item)
        self.assertEqual(star.full_name, "user/repo")
        self.assertEqual(star.name, "repo")
        self.assertEqual(star.owner, "user")
        self.assertEqual(star.language, "Python")
        self.assertEqual(star.stars, 100)
        self.assertFalse(star.is_fork)

    def test_from_github_api_empty_description(self):
        api_item = {
            "name": "repo",
            "owner": {"login": "user"},
            "description": None,
            "language": None,
            "topics": [],
            "stargazers_count": 0,
            "html_url": "",
            "fork": True,
        }
        star = StarItem.from_github_api(api_item)
        self.assertEqual(star.description, "")
        self.assertEqual(star.language, "文档 / 无代码")
        self.assertTrue(star.is_fork)

    def test_roundtrip_dict(self):
        star = StarItem(
            full_name="a/b",
            name="b",
            owner="a",
            ai_summary="test",
            ai_tags=["tag1"],
        )
        d = star.to_dict()
        star2 = StarItem.from_dict(d)
        self.assertEqual(star2.full_name, "a/b")
        self.assertEqual(star2.ai_summary, "test")
        self.assertEqual(star2.ai_tags, ["tag1"])

    def test_from_dict_ignores_unknown_fields(self):
        d = {"full_name": "a/b", "name": "b", "owner": "a", "unknown_field": 123}
        star = StarItem.from_dict(d)
        self.assertEqual(star.full_name, "a/b")
        self.assertFalse(hasattr(star, "unknown_field"))

    def test_from_dict_fallback_first_seen(self):
        """旧数据没有 first_seen 时应兜底为很早时间，避免被误判为新收录"""
        d = {"full_name": "a/b", "name": "b", "owner": "a"}
        star = StarItem.from_dict(d)
        self.assertTrue(star.first_seen)
        self.assertEqual(star.first_seen, "1970-01-01T00:00:00+00:00")

    def test_from_dict_preserves_existing_first_seen(self):
        """已有 first_seen 时应保留原值"""
        d = {"full_name": "a/b", "name": "b", "owner": "a", "first_seen": "2024-06-01T00:00:00+00:00"}
        star = StarItem.from_dict(d)
        self.assertEqual(star.first_seen, "2024-06-01T00:00:00+00:00")
