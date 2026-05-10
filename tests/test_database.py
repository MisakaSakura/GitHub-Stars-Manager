#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""StarsDB 单元测试"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from database import StarsDB


class TestStarsDB(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_db.json")

    def tearDown(self):
        meta_path = os.path.splitext(self.db_path)[0] + ".meta.json"
        for f in [self.db_path, self.db_path + ".tmp", meta_path]:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(self.tmpdir):
            os.rmdir(self.tmpdir)

    def test_load_nonexistent(self):
        db = StarsDB(self.db_path)
        self.assertEqual(len(db), 0)

    def test_save_and_load(self):
        db = StarsDB(self.db_path)
        db.set("owner/repo", {"full_name": "owner/repo", "name": "repo", "owner": "owner"})
        db.save()

        db2 = StarsDB(self.db_path)
        self.assertEqual(len(db2), 1)
        self.assertEqual(db2.get("owner/repo")["name"], "repo")

    def test_corrupted_file_rebuilds(self):
        with open(self.db_path, "w") as f:
            f.write("not valid json")
        db = StarsDB(self.db_path)
        self.assertEqual(len(db), 0)

    def test_atomic_write_leaves_no_tmp(self):
        db = StarsDB(self.db_path)
        db.set("a/b", {"full_name": "a/b", "name": "b", "owner": "a"})
        db.save()
        self.assertTrue(os.path.exists(self.db_path))
        self.assertFalse(os.path.exists(self.db_path + ".tmp"))

    def test_update_existing(self):
        db = StarsDB(self.db_path)
        db.set("x/y", {"full_name": "x/y", "name": "y", "owner": "x", "stars": 10})
        db.save()

        db.set("x/y", {"full_name": "x/y", "name": "y", "owner": "x", "stars": 20})
        db.save()

        db2 = StarsDB(self.db_path)
        self.assertEqual(db2.get("x/y")["stars"], 20)

    def test_meta_save_and_load(self):
        db = StarsDB(self.db_path)
        db.meta["last_llm_classify_at"] = "2024-01-01T00:00:00+00:00"
        db.save_meta()

        db2 = StarsDB(self.db_path)
        self.assertEqual(db2.meta.get("last_llm_classify_at"), "2024-01-01T00:00:00+00:00")
