#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository 模式集成测试 —— 验证 JSON 后端与 StarsDB 行为一致"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from models import StarItem
from repositories import JSONStarsRepository, JSONAIRepository
from database import StarsDB
from ai_database import AIDatabase


class TestJSONStarsRepository(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_db.json")
        self.repo = JSONStarsRepository(self.db_path)

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def _make_item(self, name="test-repo", owner="testuser"):
        return StarItem(
            full_name=f"{owner}/{name}",
            name=name,
            owner=owner,
            description="test",
        )

    def test_set_and_get(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        got = self.repo.get(item.full_name)
        self.assertIsNotNone(got)
        self.assertEqual(got.name, "test-repo")

    def test_get_nonexistent(self):
        self.assertIsNone(self.repo.get("non/existent"))

    def test_delete(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.assertTrue(self.repo.delete(item.full_name))
        self.assertIsNone(self.repo.get(item.full_name))
        self.assertFalse(self.repo.delete(item.full_name))

    def test_keys_values_items(self):
        item1 = self._make_item("repo1")
        item2 = self._make_item("repo2")
        self.repo.set(item1.full_name, item1)
        self.repo.set(item2.full_name, item2)
        self.assertEqual(sorted(list(self.repo.keys())), sorted([item1.full_name, item2.full_name]))
        self.assertEqual(len(list(self.repo.values())), 2)
        self.assertEqual(len(list(self.repo.items())), 2)
        self.assertEqual(len(self.repo), 2)

    def test_save_and_load(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.repo.save()
        # 新实例加载验证（StarsDB 加载时使用 full_name 作为 key）
        repo2 = JSONStarsRepository(self.db_path)
        got = repo2.get(item.full_name)
        self.assertIsNotNone(got)
        self.assertEqual(got.name, item.name)

    def test_meta_operations(self):
        self.repo.meta_set("last_run", "2024-01-01")
        self.assertEqual(self.repo.meta_get("last_run"), "2024-01-01")
        self.assertIsNone(self.repo.meta_get("missing"))
        self.repo.meta_save()
        repo2 = JSONStarsRepository(self.db_path)
        self.assertEqual(repo2.meta_get("last_run"), "2024-01-01")

    def test_backend_property(self):
        """兼容层：可以访问底层 StarsDB"""
        self.assertIsInstance(self.repo.backend, StarsDB)


class TestJSONAIRepository(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_ai.json")
        self.repo = JSONAIRepository(self.db_path)

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_set_and_get(self):
        from ai_database import AIResult
        rec = AIResult(full_name="user/repo", llm_status="success")
        self.repo.set("user/repo", rec)
        got = self.repo.get("user/repo")
        self.assertIsNotNone(got)
        self.assertEqual(got.llm_status, "success")

    def test_backend_property(self):
        from ai_database import AIDatabase
        self.assertIsInstance(self.repo.backend, AIDatabase)
