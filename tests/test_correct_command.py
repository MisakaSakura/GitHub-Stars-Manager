#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CorrectCommand 单元测试"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from models import StarItem
from database import StarsDB
from correct_command import CorrectCommand


class TestCorrectCommand(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "stars_db.json")
        self.db = StarsDB(self.db_path)
        self.db.set("owner/existing", {
            "full_name": "owner/existing",
            "name": "existing",
            "owner": "owner",
            "platform": "其他 / 未分类",
            "type": "其他 / 未分类",
            "ecology": "独立项目 / Standalone",
            "ecology_role": "-",
        })
        self.db.save()

    def tearDown(self):
        meta_path = os.path.splitext(self.db_path)[0] + ".meta.json"
        lock_path = self.db_path + ".lock"
        for f in [self.db_path, self.db_path + ".tmp", meta_path, lock_path]:
            if os.path.exists(f):
                os.remove(f)
        feedback_path = os.path.join(self.tmpdir, "feedback.json")
        if os.path.exists(feedback_path):
            os.remove(feedback_path)
        learned_path = os.path.join(self.tmpdir, "learned_rules.json")
        if os.path.exists(learned_path):
            os.remove(learned_path)
        # 清理临时目录中的所有文件
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        if os.path.exists(self.tmpdir):
            os.rmdir(self.tmpdir)

    def _make_args(self, **kwargs):
        args = MagicMock()
        args.db = self.db_path
        args.correct = None
        args.correct_batch = None
        args.correct_platform = None
        args.correct_type = None
        args.correct_ecology = None
        args.correct_ecology_role = None
        for k, v in kwargs.items():
            setattr(args, k, v)
        return args

    def test_correct_single_platform(self):
        args = self._make_args(correct="owner/existing", correct_platform="Python")
        cmd = CorrectCommand(args)
        result = cmd.run()
        self.assertEqual(result, 0)

        db2 = StarsDB(self.db_path)
        item = db2.get("owner/existing")
        self.assertEqual(item.platform, "Python")
        self.assertTrue(item.manual_override)
        self.assertIn("platform", item.override_fields)
        self.assertNotEqual(item.override_rules_version, "")

    def test_correct_single_ecology(self):
        args = self._make_args(
            correct="owner/existing",
            correct_ecology="PyTorch",
            correct_ecology_role="工具 / Tool",
        )
        cmd = CorrectCommand(args)
        result = cmd.run()
        self.assertEqual(result, 0)

        db2 = StarsDB(self.db_path)
        item = db2.get("owner/existing")
        self.assertEqual(item.ecology, "PyTorch")
        self.assertEqual(item.ecology_role, "工具 / Tool")
        self.assertTrue(item.manual_override)

    def test_correct_nonexistent(self):
        args = self._make_args(correct="owner/missing", correct_platform="Python")
        cmd = CorrectCommand(args)
        result = cmd.run()
        self.assertEqual(result, 1)  # 没有任何项目被修正

    def test_correct_no_changes(self):
        args = self._make_args(correct="owner/existing")
        cmd = CorrectCommand(args)
        result = cmd.run()
        self.assertEqual(result, 1)  # 未提供任何修正字段

    def test_correct_batch(self):
        batch_path = os.path.join(self.tmpdir, "batch.csv")
        with open(batch_path, "w", encoding="utf-8") as f:
            f.write("owner/existing,PyTorch,工具 / Tool,Python,框架 / Framework\n")

        args = self._make_args(correct_batch=batch_path)
        cmd = CorrectCommand(args)
        result = cmd.run()
        self.assertEqual(result, 0)

        db2 = StarsDB(self.db_path)
        item = db2.get("owner/existing")
        self.assertEqual(item.platform, "Python")
        self.assertEqual(item.type, "框架 / Framework")
        self.assertEqual(item.ecology, "PyTorch")
        self.assertEqual(item.ecology_role, "工具 / Tool")
        self.assertTrue(item.manual_override)

    def test_correct_batch_skips_comments(self):
        batch_path = os.path.join(self.tmpdir, "batch.csv")
        with open(batch_path, "w", encoding="utf-8") as f:
            f.write("# this is a comment\n")
            f.write("owner/existing,PyTorch,,,\n")

        args = self._make_args(correct_batch=batch_path)
        cmd = CorrectCommand(args)
        result = cmd.run()
        self.assertEqual(result, 0)

    def test_feedback_recorded(self):
        args = self._make_args(correct="owner/existing", correct_platform="Python")
        cmd = CorrectCommand(args)
        cmd.run()

        feedback_path = os.path.join(self.tmpdir, "feedback.json")
        self.assertTrue(os.path.exists(feedback_path))
