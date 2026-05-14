#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单元测试"""

import sys
import os
import unittest

# 将 scripts 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from rule_classifier import RuleClassifier


class TestRuleClassifier(unittest.TestCase):
    def _make_item(self, name, description="", topics=None, language=""):
        return {
            "name": name,
            "description": description,
            "topics": topics or [],
            "owner": {"login": "test"},
            "language": language,
        }

    def test_classify_platform_web_frontend(self):
        item = self._make_item("react-hooks", "Awesome React hooks collection", ["react", "frontend", "hooks"])
        result = RuleClassifier.classify_platform(item)
        self.assertEqual(result, "Web 前端")

    def test_classify_platform_ai(self):
        item = self._make_item("stable-diffusion-webui", "A web interface for Stable Diffusion", ["stable-diffusion", "ai"])
        result = RuleClassifier.classify_platform(item)
        self.assertEqual(result, "AI / 机器学习")

    def test_classify_type_framework(self):
        item = self._make_item("my-framework", "A web framework", ["framework", "web"])
        result = RuleClassifier.classify_type(item)
        self.assertEqual(result, "框架 / Framework")

    def test_classify_type_awesome(self):
        item = self._make_item("awesome-python", "A curated list of Python resources", ["awesome", "python", "list"])
        result = RuleClassifier.classify_type(item)
        self.assertEqual(result, "资源合集 / Awesome")

    def test_classify_ecology_clash(self):
        item = self._make_item("clash-verge", "A Clash GUI client", ["clash", "proxy", "gui"], language="Rust")
        eco, role = RuleClassifier.classify_ecology(item)
        self.assertEqual(eco, "Clash / Mihomo")
        self.assertIn(role, ["GUI 前端 / Client", "其他 / Other"])

    def test_classify_ecology_core(self):
        item = self._make_item("mihomo", "The Mihomo core", ["proxy", "mihomo"], language="Go")
        eco, role = RuleClassifier.classify_ecology(item)
        self.assertEqual(eco, "Clash / Mihomo")
        self.assertEqual(role, "核心 / Core")

    def test_classify_ecology_no_match(self):
        item = self._make_item("random-tool", "Just a random tool", ["tool"], language="Python")
        eco, role = RuleClassifier.classify_ecology(item)
        self.assertIsNone(eco)
        self.assertIsNone(role)

    def test_classify_no_match_returns_default(self):
        item = self._make_item("xyz-abc", "No relevant keywords")
        platform = RuleClassifier.classify_platform(item)
        ptype = RuleClassifier.classify_type(item)
        self.assertEqual(platform, "其他 / 未分类")
        self.assertEqual(ptype, "其他 / 未分类")


if __name__ == "__main__":
    unittest.main()
