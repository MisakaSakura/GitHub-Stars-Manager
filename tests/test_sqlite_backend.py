#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite Repository 集成测试"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from models import StarItem
from repositories.sqlite_backend import SQLiteStarsRepository


class TestSQLiteStarsRepository(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.repo = SQLiteStarsRepository(self.db_path)

    def tearDown(self):
        self.repo.close()
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def _make_item(self, name="repo", owner="user"):
        return StarItem(
            full_name=f"{owner}/{name}",
            name=name,
            owner=owner,
            description="test",
            topics=["python", "cli"],
        )

    def test_set_and_get(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.repo.save()
        got = self.repo.get(item.full_name)
        self.assertIsNotNone(got)
        self.assertEqual(got.name, "repo")
        self.assertEqual(got.topics, ["python", "cli"])

    def test_update_existing(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.repo.save()

        item.stars = 100
        item.ecology = "TestEco"
        self.repo.set(item.full_name, item)
        self.repo.save()

        got = self.repo.get(item.full_name)
        self.assertEqual(got.stars, 100)
        self.assertEqual(got.ecology, "TestEco")

    def test_delete(self):
        item = self._make_item()
        self.repo.set(item.full_name, item)
        self.repo.save()
        self.assertTrue(self.repo.delete(item.full_name))
        self.assertIsNone(self.repo.get(item.full_name))
        self.assertFalse(self.repo.delete(item.full_name))

    def test_keys_values_items_len(self):
        items = [self._make_item(f"repo{i}") for i in range(3)]
        for item in items:
            self.repo.set(item.full_name, item)
        self.repo.save()

        keys = list(self.repo.keys())
        self.assertEqual(len(keys), 3)
        self.assertEqual(len(list(self.repo.values())), 3)
        self.assertEqual(len(list(self.repo.items())), 3)
        self.assertEqual(len(self.repo), 3)

    def test_meta_operations(self):
        self.repo.meta_set("last_run", "2024-01-01")
        self.assertEqual(self.repo.meta_get("last_run"), "2024-01-01")
        self.repo.meta_save()
        self.repo.close()

        # 新实例验证持久化
        repo2 = SQLiteStarsRepository(self.db_path)
        self.assertEqual(repo2.meta_get("last_run"), "2024-01-01")
        repo2.close()

    def test_migrate_from_json(self):
        import json
        json_path = os.path.join(self.tmpdir, "test.json")
        data = [
            {
                "full_name": "user/repo1",
                "name": "repo1",
                "owner": "user",
                "description": "desc1",
                "stars": 10,
                "topics": ["a", "b"],
            },
            {
                "full_name": "user/repo2",
                "name": "repo2",
                "owner": "user",
                "description": "desc2",
                "stars": 20,
            },
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        count = self.repo.migrate_from_json(json_path)
        self.assertEqual(count, 2)
        self.assertEqual(len(self.repo), 2)

        got = self.repo.get("user/repo1")
        self.assertIsNotNone(got)
        self.assertEqual(got.stars, 10)
        self.assertEqual(got.topics, ["a", "b"])


class TestSQLiteJSONParity(unittest.TestCase):
    """验证 SQLite 后端与 JSON 后端行为一致"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.json_path = os.path.join(self.tmpdir, "stars_db.json")
        self.sqlite_path = os.path.join(self.tmpdir, "stars.db")

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_parity_with_json_backend(self):
        from repositories.json_backend import JSONStarsRepository

        item = StarItem(
            full_name="user/repo",
            name="repo",
            owner="user",
            description="test",
            language="Python",
            platform="CLI / 终端",
            type="工具 / Tool",
            ecology="TestEco",
            ecology_role="核心 / Core",
            topics=["t1", "t2"],
            stars=42,
            url="https://github.com/user/repo",
            manual_override=True,
            subscribe_releases=True,
            is_fork=False,
            imported=True,
        )

        # JSON 后端
        json_repo = JSONStarsRepository(self.json_path)
        json_repo.set(item.full_name, item)
        json_repo.save()
        json_got = json_repo.get(item.full_name)

        # SQLite 后端
        sqlite_repo = SQLiteStarsRepository(self.sqlite_path)
        sqlite_repo.set(item.full_name, item)
        sqlite_repo.save()
        sqlite_got = sqlite_repo.get(item.full_name)

        # 对比关键字段
        for field in ["full_name", "name", "owner", "description", "language",
                      "platform", "type", "ecology", "ecology_role",
                      "topics", "stars", "url", "manual_override",
                      "subscribe_releases", "is_fork", "imported"]:
            self.assertEqual(
                getattr(json_got, field), getattr(sqlite_got, field),
                f"字段 {field} 不一致"
            )

        sqlite_repo.close()
