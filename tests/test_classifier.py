#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 CLI 入口 classifier.py 的 mode 映射逻辑"""

import os
import sys
import unittest
from unittest.mock import patch

# 将 scripts 目录加入路径
sys.path.insert(0, "scripts")

from classifier import _apply_mode, _apply_preset, _ensure_defaults, _parse_env_presets


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
        self.llm_preset = kwargs.get("llm_preset", None)
        self.llm_provider = kwargs.get("llm_provider", None)
        self.llm_model = kwargs.get("llm_model", None)
        self.llm_base = kwargs.get("llm_base", None)


class TestApplyMode(unittest.TestCase):
    """测试 _apply_mode 的模式映射"""

    def test_incremental_mode(self):
        args = FakeArgs(mode="incremental")
        result = _apply_mode(args)
        self.assertTrue(result.incremental)
        self.assertFalse(result.force_refresh)
        self.assertTrue(result.check_all_releases)
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


class TestApplyPreset(unittest.TestCase):
    """测试 _apply_preset 的预设映射"""

    def test_no_preset_does_nothing(self):
        """无 preset 时不修改任何参数"""
        args = FakeArgs(llm_preset=None, llm_provider=None, llm_model=None, llm_base=None)
        result = _apply_preset(args)
        self.assertIsNone(result.llm_provider)
        self.assertIsNone(result.llm_model)
        self.assertIsNone(result.llm_base)

    def test_preset_fills_all_fields(self):
        """有效 preset 自动填充 provider/base/model"""
        args = FakeArgs(llm_preset="xiaomimimo", llm_provider=None, llm_model=None, llm_base=None)
        result = _apply_preset(args)
        self.assertEqual(result.llm_provider, "openai")
        self.assertEqual(result.llm_model, "mimo-v2-flash")  # 默认改为性价比最高的 flash
        self.assertEqual(result.llm_base, "https://api.xiaomimimo.com/v1")

    def test_preset_deepseek(self):
        """deepseek preset 使用正确的 provider 和 base"""
        args = FakeArgs(llm_preset="deepseek", llm_provider=None, llm_model=None, llm_base=None)
        result = _apply_preset(args)
        self.assertEqual(result.llm_provider, "deepseek")
        self.assertEqual(result.llm_model, "deepseek-chat")
        self.assertEqual(result.llm_base, "https://api.deepseek.com/v1")

    def test_preset_does_not_override_explicit_args(self):
        """CLI 显式参数优先级高于 preset"""
        args = FakeArgs(
            llm_preset="xiaomimimo",
            llm_provider="moonshot",  # 显式覆盖
            llm_model="custom-model",  # 显式覆盖
            llm_base="https://custom.com/v1",  # 显式覆盖
        )
        result = _apply_preset(args)
        self.assertEqual(result.llm_provider, "moonshot")
        self.assertEqual(result.llm_model, "custom-model")
        self.assertEqual(result.llm_base, "https://custom.com/v1")

    def test_preset_partial_override(self):
        """部分显式参数覆盖 preset，其余使用 preset 默认值"""
        args = FakeArgs(
            llm_preset="xiaomimimo",
            llm_provider=None,
            llm_model="my-model",
            llm_base=None,
        )
        result = _apply_preset(args)
        self.assertEqual(result.llm_provider, "openai")  # from preset
        self.assertEqual(result.llm_model, "my-model")   # explicit
        self.assertEqual(result.llm_base, "https://api.xiaomimimo.com/v1")  # from preset

    def test_unknown_preset_warns_and_leaves_args(self):
        """未知 preset 给出警告但不修改参数"""
        args = FakeArgs(llm_preset="nonexistent", llm_provider=None, llm_model=None, llm_base=None)
        result = _apply_preset(args)
        self.assertIsNone(result.llm_provider)
        self.assertIsNone(result.llm_model)
        self.assertIsNone(result.llm_base)

    def test_ensure_defaults_after_preset(self):
        """preset 后 _ensure_defaults 正确补全 provider 默认值"""
        args = FakeArgs(llm_preset="deepseek", llm_provider=None)
        args = _apply_preset(args)
        args = _ensure_defaults(args)
        self.assertEqual(args.llm_provider, "deepseek")  # preset 已填充，ensure 不覆盖

    def test_ensure_defaults_without_preset(self):
        """无 preset 时 _ensure_defaults 补上 openai 默认值"""
        args = FakeArgs(llm_preset=None, llm_provider=None)
        args = _apply_preset(args)
        args = _ensure_defaults(args)
        self.assertEqual(args.llm_provider, "openai")

    def test_custom_preset_overrides_builtin(self):
        """CUSTOM_PRESETS 中的同名预设覆盖内置预设"""
        import copy
        import config_llm
        original_custom = copy.deepcopy(config_llm.CUSTOM_PRESETS)
        try:
            config_llm.CUSTOM_PRESETS["deepseek"] = {
                "provider": "openai",
                "api_base": "https://custom.deepseek.com/v1",
                "model": "custom-deepseek",
            }
            args = FakeArgs(llm_preset="deepseek", llm_provider=None, llm_model=None, llm_base=None)
            result = _apply_preset(args)
            self.assertEqual(result.llm_provider, "openai")  # 被自定义覆盖
            self.assertEqual(result.llm_model, "custom-deepseek")
            self.assertEqual(result.llm_base, "https://custom.deepseek.com/v1")
        finally:
            config_llm.CUSTOM_PRESETS = original_custom

    def test_custom_preset_new_name(self):
        """CUSTOM_PRESETS 中添加的新预设可用"""
        import copy
        import config_llm
        original_custom = copy.deepcopy(config_llm.CUSTOM_PRESETS)
        try:
            config_llm.CUSTOM_PRESETS["mycompany"] = {
                "provider": "openai",
                "api_base": "https://llm.mycompany.com/v1",
                "model": "company-v1",
            }
            args = FakeArgs(llm_preset="mycompany", llm_provider=None, llm_model=None, llm_base=None)
            result = _apply_preset(args)
            self.assertEqual(result.llm_provider, "openai")
            self.assertEqual(result.llm_model, "company-v1")
            self.assertEqual(result.llm_base, "https://llm.mycompany.com/v1")
        finally:
            config_llm.CUSTOM_PRESETS = original_custom

    @patch.dict(os.environ, {"LLM_PRESETS": "mycompany|openai|https://llm.mycompany.com/v1|company-v1;azure|openai|https://xxx.azure.com/v1|gpt-4o"})
    def test_env_presets_parsing(self):
        """LLM_PRESETS 环境变量解析为多个预设"""
        presets = _parse_env_presets()
        self.assertIn("mycompany", presets)
        self.assertIn("azure", presets)
        self.assertEqual(presets["mycompany"]["provider"], "openai")
        self.assertEqual(presets["mycompany"]["api_base"], "https://llm.mycompany.com/v1")
        self.assertEqual(presets["mycompany"]["model"], "company-v1")
        self.assertEqual(presets["azure"]["model"], "gpt-4o")

    @patch.dict(os.environ, {"LLM_PRESETS": "deepseek|openai|https://custom.deepseek.com/v1|custom-model"})
    def test_env_preset_overrides_builtin(self):
        """LLM_PRESETS 环境变量中的预设覆盖内置预设"""
        args = FakeArgs(llm_preset="deepseek", llm_provider=None, llm_model=None, llm_base=None)
        result = _apply_preset(args)
        self.assertEqual(result.llm_provider, "openai")  # 被环境变量覆盖
        self.assertEqual(result.llm_model, "custom-model")
        self.assertEqual(result.llm_base, "https://custom.deepseek.com/v1")

    @patch.dict(os.environ, {"LLM_PRESETS": "solo|moonshot|https://solo.com/v1|solo-model"})
    def test_env_preset_single_entry(self):
        """LLM_PRESETS 只定义一个预设"""
        args = FakeArgs(llm_preset="solo", llm_provider=None, llm_model=None, llm_base=None)
        result = _apply_preset(args)
        self.assertEqual(result.llm_provider, "moonshot")
        self.assertEqual(result.llm_model, "solo-model")
        self.assertEqual(result.llm_base, "https://solo.com/v1")


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
