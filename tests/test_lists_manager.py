#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ListsManager 单元测试"""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from lists_manager import ListsManager


class MockDB:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


class TestListsManager(unittest.TestCase):
    def test_detect_lists_returns_none_on_exception(self):
        gh = MagicMock()
        gh.get_lists.side_effect = Exception("API Error")
        mgr = ListsManager(gh)
        result = mgr.detect_lists("user")
        self.assertIsNone(result)

    def test_detect_lists_returns_lists(self):
        gh = MagicMock()
        gh.get_lists.return_value = [{"id": 1, "name": "List1"}]
        mgr = ListsManager(gh)
        result = mgr.detect_lists("user")
        self.assertEqual(len(result), 1)

    def test_get_lists_summary(self):
        gh = MagicMock()
        gh.get_list_items.return_value = [{"id": 1}, {"id": 2}]
        mgr = ListsManager(gh)
        lists = [{"id": 1, "name": "Frontend"}, {"id": 2, "name": "Backend"}]
        summary = mgr.get_lists_summary(lists)
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]["count"], 2)

    def test_migrate_skips_existing(self):
        gh = MagicMock()
        gh.get_lists.return_value = [{"id": 1, "name": "MyList"}]
        gh.get_list_items.return_value = [
            {"repository": {"full_name": "owner/repo", "name": "repo", "owner": {"login": "owner"}}}
        ]
        db = MockDB()
        db.set("owner/repo", {"full_name": "owner/repo", "name": "repo", "owner": "owner"})
        mgr = ListsManager(gh)
        migrated = mgr.migrate_lists_to_db(db, "user")
        self.assertEqual(migrated, 0)

    def test_migrate_imports_new(self):
        gh = MagicMock()
        gh.get_lists.return_value = [{"id": 1, "name": "MyList"}]
        gh.get_list_items.return_value = [
            {"repository": {"full_name": "owner/repo", "name": "repo", "owner": {"login": "owner"}, "description": "desc", "language": "Python", "topics": ["web"], "stargazers_count": 10, "html_url": "https://github.com/owner/repo"}}
        ]
        db = MockDB()
        mgr = ListsManager(gh)
        migrated = mgr.migrate_lists_to_db(db, "user")
        self.assertEqual(migrated, 1)
        self.assertEqual(db.data["owner/repo"]["ecology"], "MyList")
        self.assertTrue(db.data["owner/repo"]["manual_override"])

    def test_clear_all_lists(self):
        gh = MagicMock()
        gh.get_lists.return_value = [{"id": 1, "name": "L1"}, {"id": 2, "name": "L2"}]
        gh.delete_list.return_value = True
        mgr = ListsManager(gh)
        deleted = mgr.clear_all_lists("user")
        self.assertEqual(deleted, 2)

    def test_clear_no_lists(self):
        gh = MagicMock()
        gh.get_lists.return_value = []
        mgr = ListsManager(gh)
        deleted = mgr.clear_all_lists("user")
        self.assertEqual(deleted, 0)
