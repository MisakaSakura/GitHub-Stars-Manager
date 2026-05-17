#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository 模式集成测试 —— 验证 JSON 后端与 StarsDB 行为一致"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from models import StarItem
from repositories import JSONStarsRepository, JSONAIRepository, SQLiteStarsRepository
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


class TestSQLiteStarsRepository(unittest.TestCase):
    """P1-49: SQLite 后端测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.sqlite")
        self.repo = SQLiteStarsRepository(self.db_path)

    def tearDown(self):
        self.repo.close()
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
        self.repo.save()
        got = self.repo.get(item.full_name)
        self.assertIsNotNone(got)
        self.assertEqual(got.name, "test-repo")
        self.assertEqual(got.owner, "testuser")

    def test_get_nonexistent(self):
        self.assertIsNone(self.repo.get("non/existent"))

    def test_delete(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.repo.save()
        self.assertTrue(self.repo.delete(item.full_name))
        self.assertIsNone(self.repo.get(item.full_name))
        self.assertFalse(self.repo.delete("non/existent"))

    def test_keys_values_items(self):
        item1 = self._make_item("repo1")
        item2 = self._make_item("repo2")
        self.repo.set(item1.full_name, item1)
        self.repo.set(item2.full_name, item2)
        self.repo.save()
        self.assertEqual(sorted(list(self.repo.keys())), sorted([item1.full_name, item2.full_name]))
        self.assertEqual(len(list(self.repo.values())), 2)
        self.assertEqual(len(list(self.repo.items())), 2)
        self.assertEqual(len(self.repo), 2)

    def test_update_existing(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.repo.save()

        item.stars = 100
        self.repo.set(item.full_name, item)
        self.repo.save()

        got = self.repo.get(item.full_name)
        self.assertEqual(got.stars, 100)

    def test_meta_operations(self):
        self.repo.meta_set("last_run", "2024-01-01")
        self.repo.meta_save()
        self.assertEqual(self.repo.meta_get("last_run"), "2024-01-01")
        self.assertIsNone(self.repo.meta_get("missing"))

        # 新实例加载验证
        repo2 = SQLiteStarsRepository(self.db_path)
        self.assertEqual(repo2.meta_get("last_run"), "2024-01-01")
        repo2.close()

    def test_persistence(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.repo.save()
        self.repo.close()

        repo2 = SQLiteStarsRepository(self.db_path)
        got = repo2.get(item.full_name)
        self.assertIsNotNone(got)
        self.assertEqual(got.name, item.name)
        repo2.close()

    def test_migrate_from_json(self):
        json_path = os.path.join(self.tmpdir, "legacy.json")
        with open(json_path, "w", encoding="utf-8") as f:
            import json
            json.dump([{
                "full_name": "owner/legacy",
                "name": "legacy",
                "owner": "owner",
                "description": "old data",
                "stars": 42,
            }], f)
        count = self.repo.migrate_from_json(json_path)
        self.assertEqual(count, 1)
        got = self.repo.get("owner/legacy")
        self.assertIsNotNone(got)
        self.assertEqual(got.stars, 42)

    def test_schema_auto_sync(self):
        """P1-13: schema 自动同步——创建旧 schema 数据库后打开应自动添加缺失列"""
        import sqlite3
        # 关闭 setUp 创建的 repo，释放数据库连接
        self.repo.close()
        os.remove(self.db_path)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE stars (
                full_name TEXT PRIMARY KEY,
                name TEXT,
                owner TEXT
            )
        """)
        conn.commit()
        conn.close()

        # 重新打开应自动同步 schema
        repo2 = SQLiteStarsRepository(self.db_path)
        item = self._make_item()
        repo2.set(item.full_name, item)
        repo2.save()
        got = repo2.get(item.full_name)
        self.assertIsNotNone(got)
        repo2.close()
