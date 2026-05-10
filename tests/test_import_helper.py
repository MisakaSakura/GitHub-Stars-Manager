#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FirstRunHelper 单元测试"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from import_helper import FirstRunHelper, _safe_int


class MockDB:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        pass


class TestSafeInt(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(_safe_int("42"), 42)

    def test_empty(self):
        self.assertEqual(_safe_int(None), 0)
        self.assertEqual(_safe_int(""), 0)

    def test_invalid(self):
        self.assertEqual(_safe_int("abc"), 0)


class TestDetectFirstRun(unittest.TestCase):
    def test_missing_file(self):
        self.assertTrue(FirstRunHelper.detect_first_run("/nonexistent/path.json"))

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("[]")
            path = f.name
        try:
            self.assertTrue(FirstRunHelper.detect_first_run(path))
        finally:
            os.remove(path)

    def test_non_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write('[{"full_name":"a/b"}]')
            path = f.name
        try:
            self.assertFalse(FirstRunHelper.detect_first_run(path))
        finally:
            os.remove(path)

    def test_corrupted_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("not json")
            path = f.name
        try:
            self.assertTrue(FirstRunHelper.detect_first_run(path))
        finally:
            os.remove(path)


class TestImportFromJson(unittest.TestCase):
    def test_imports_items(self):
        db = MockDB()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            import json
            json.dump([
                {"full_name": "owner/repo1", "platform": "Web"},
                {"full_name": "owner/repo2", "platform": "AI"},
            ], f)
            path = f.name
        try:
            count = FirstRunHelper.import_from_json(db, path)
            self.assertEqual(count, 2)
            self.assertTrue(db.data["owner/repo1"]["manual_override"])
            self.assertEqual(db.data["owner/repo1"]["name"], "repo1")
            self.assertEqual(db.data["owner/repo1"]["owner"], "owner")
        finally:
            os.remove(path)

    def test_skips_missing_full_name(self):
        db = MockDB()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            import json
            json.dump([{"platform": "Web"}], f)
            path = f.name
        try:
            count = FirstRunHelper.import_from_json(db, path)
            self.assertEqual(count, 0)
        finally:
            os.remove(path)


class TestImportFromCsv(unittest.TestCase):
    def test_imports_rows(self):
        db = MockDB()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8-sig", newline="") as f:
            f.write("full_name,name,owner,platform,type,ecology,stars\n")
            f.write("owner/repo1,repo1,owner,Web,Tool,,10\n")
            f.write("owner/repo2,repo2,owner,AI,App,,20\n")
            path = f.name
        try:
            count = FirstRunHelper.import_from_csv(db, path)
            self.assertEqual(count, 2)
            self.assertEqual(db.data["owner/repo1"]["stars"], 10)
            self.assertEqual(db.data["owner/repo2"]["stars"], 20)
            self.assertTrue(db.data["owner/repo1"]["manual_override"])
        finally:
            os.remove(path)

    def test_skips_invalid_key(self):
        db = MockDB()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8-sig", newline="") as f:
            f.write("full_name,name,owner\n")
            f.write("bad-key-no-slash,repo1,owner\n")
            path = f.name
        try:
            count = FirstRunHelper.import_from_csv(db, path)
            self.assertEqual(count, 0)
        finally:
            os.remove(path)
