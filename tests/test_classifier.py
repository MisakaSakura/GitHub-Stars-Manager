#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 CLI 入口 classifier.py 的 mode 映射逻辑"""

import sys
import unittest
from unittest.mock import patch

# 将 scripts 目录加入路径
sys.path.insert(0, "scripts")

from classifier import _apply_mode


class FakeArgs:
    """模拟 argparse.Namespace"""
    def __init__(self, **kwargs):
        self.mode = kwargs.get("mode", "incremental")
        self.incremental = kwargs.get("incremental", False)
        self.force_refresh = kwargs.get("force_refresh", False)
        self.check_all_releases = kwargs.get("check_all_releases", False)
        self.check_forks = kwargs.get("check_forks", False)
        self.subscribe_releases = kwargs.get("subscribe_releases", False)
        self.llm_key = kwargs.get("llm_key", None)
        self.force_llm = kwargs.get("force_llm", False)
        self.no_report = kwargs.get("no_report", False)


class TestApplyMode(unittest.TestCase):
    """测试 _apply_mode 的模式映射"""

    def test_incremental_mode(self):
        args = FakeArgs(mode="incremental")
        result = _apply_mode(args)
        self.assertTrue(result.incremental)
        self.assertFalse(result.force_refresh)
        self.assertFalse(result.check_all_releases)
        self.assertFalse(result.check_forks)

    def test_deep_mode(self):
        args = FakeArgs(mode="deep")
        result = _apply_mode(args)
        self.assertTrue(result.incremental)
        self.assertTrue(result.force_refresh)
        self.assertTrue(result.check_all_releases)
        self.assertTrue(result.check_forks)
        self.assertFalse(result.subscribe_releases)

    def test_full_mode(self):
        args = FakeArgs(mode="full")
        result = _apply_mode(args)
        self.assertFalse(result.incremental)
        self.assertTrue(result.force_refresh)
        self.assertTrue(result.check_all_releases)
        self.assertTrue(result.check_forks)
        self.assertTrue(result.subscribe_releases)

    def test_custom_mode_does_not_modify(self):
        """custom 模式下任何参数都不应被修改"""
        args = FakeArgs(
            mode="custom",
            incremental=True,
            force_refresh=False,
            check_all_releases=False,
        )
        result = _apply_mode(args)
        self.assertTrue(result.incremental)
        self.assertFalse(result.force_refresh)
        self.assertFalse(result.check_all_releases)
        self.assertFalse(result.check_forks)

    def test_custom_mode_preserves_explicit_values(self):
        """custom 模式下显式传入的值保持不变"""
        args = FakeArgs(
            mode="custom",
            incremental=False,
            force_refresh=True,
            check_all_releases=True,
            check_forks=True,
            subscribe_releases=True,
        )
        result = _apply_mode(args)
        self.assertFalse(result.incremental)
        self.assertTrue(result.force_refresh)
        self.assertTrue(result.check_all_releases)
        self.assertTrue(result.check_forks)
        self.assertTrue(result.subscribe_releases)

    def test_full_mode_auto_force_llm(self):
        """full 模式下配置了 llm_key 应自动启用 force_llm"""
        args = FakeArgs(mode="full", llm_key="sk-test", force_llm=False)
        result = _apply_mode(args)
        self.assertTrue(result.force_llm)

    def test_full_mode_does_not_auto_force_llm_without_key(self):
        """full 模式下没有 llm_key 不应自动启用 force_llm"""
        args = FakeArgs(mode="full", llm_key=None, force_llm=False)
        result = _apply_mode(args)
        self.assertFalse(result.force_llm)

    def test_full_mode_respects_existing_force_llm(self):
        """full 模式下用户已显式启用 force_llm 不应重复设置"""
        args = FakeArgs(mode="full", llm_key="sk-test", force_llm=True)
        result = _apply_mode(args)
        self.assertTrue(result.force_llm)

    def test_deep_mode_does_not_auto_force_llm(self):
        """deep 模式下不应自动启用 force_llm"""
        args = FakeArgs(mode="deep", llm_key="sk-test", force_llm=False)
        result = _apply_mode(args)
        self.assertFalse(result.force_llm)

    def test_mode_does_not_override_unrelated_params(self):
        """mode 不应覆盖与模式无关的参数如 no_report"""
        args = FakeArgs(mode="deep", no_report=True)
        result = _apply_mode(args)
        self.assertTrue(result.no_report)


class TestRelativeTime(unittest.TestCase):
    """测试 report.py 的 _relative_time 函数"""

    def setUp(self):
        sys.path.insert(0, "scripts")
        from report import ReportGenerator
        self._relative_time = ReportGenerator._relative_time

    def test_just_now(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        self.assertEqual(self._relative_time(now), "刚刚")

    def test_minutes_ago(self):
        from datetime import datetime, timezone, timedelta
        dt = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        self.assertEqual(self._relative_time(dt), "5分钟前")

    def test_hours_ago(self):
        from datetime import datetime, timezone, timedelta
        dt = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        self.assertEqual(self._relative_time(dt), "3小时前")

    def test_days_ago(self):
        from datetime import datetime, timezone, timedelta
        dt = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        self.assertEqual(self._relative_time(dt), "2天前")

    def test_empty_string(self):
        self.assertEqual(self._relative_time(""), "")

    def test_invalid_string(self):
        self.assertEqual(self._relative_time("not-a-date"), "")


class TestRenderReleaseBody(unittest.TestCase):
    """测试 report.py 的 _render_release_body 函数"""

    def setUp(self):
        sys.path.insert(0, "scripts")
        from report import ReportGenerator
        self._render = ReportGenerator._render_release_body

    def test_empty_text(self):
        self.assertEqual(self._render(""), "")

    def test_plain_text(self):
        result = self._render("Hello world")
        self.assertIn("Hello world", result)

    def test_heading(self):
        result = self._render("## Title\nbody")
        self.assertIn("<h2>Title</h2>", result)

    def test_inline_code(self):
        result = self._render("use `pip install`")
        self.assertIn("<code>pip install</code>", result)

    def test_bold(self):
        result = self._render("**bold** text")
        self.assertIn("<strong>bold</strong>", result)

    def test_link(self):
        result = self._render("[link](https://example.com)")
        self.assertIn('<a href="https://example.com"', result)
        self.assertIn(">link</a>", result)

    def test_code_block(self):
        text = "```\ncode line\n```"
        result = self._render(text)
        self.assertIn("<pre", result)
        self.assertIn("<code>code line</code>", result)

    def test_unclosed_code_block(self):
        text = "```\ncode line\n"
        result = self._render(text)
        self.assertIn("<pre", result)


if __name__ == "__main__":
    unittest.main()
