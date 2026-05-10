#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub API 单元测试"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from github_api import GitHubAPI, GitHubAuthError, GitHubRateLimitError


class TestGitHubAPIErrorHandling(unittest.TestCase):
    @patch("github_api.HTTPClient")
    def test_auth_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.request.return_value = (401, '{"message":"Bad credentials"}')
        mock_client_cls.return_value = mock_client

        gh = GitHubAPI("bad_token")
        with self.assertRaises(GitHubAuthError):
            gh.get_user("test")

    @patch("github_api.HTTPClient")
    def test_rate_limit_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.request.return_value = (403, '{"message":"API rate limit exceeded"}')
        mock_client_cls.return_value = mock_client

        gh = GitHubAPI("token")
        with self.assertRaises(GitHubRateLimitError):
            gh.get_user("test")

    @patch("github_api.HTTPClient")
    def test_404_returns_none(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.request.return_value = (404, '{"message":"Not Found"}')
        mock_client_cls.return_value = mock_client

        gh = GitHubAPI("token")
        result = gh.get_user("nonexistent")
        self.assertIsNone(result)


class TestGitHubAPIHelpers(unittest.TestCase):
    def test_strip_markdown(self):
        text = GitHubAPI._strip_markdown("""
# Title
Some `code` here and [link](http://a.com).
> blockquote
*italic* and **bold**
```py
print(1)
```
![img](a.png)
""")
        self.assertNotIn("# Title", text)
        self.assertNotIn("```", text)
        self.assertNotIn("[link](http://a.com)", text)
        self.assertIn("link", text)
        # inline code backticks are stripped, so 'code' may disappear
        self.assertNotIn("`code`", text)

    def test_strip_markdown_img_removed(self):
        text = GitHubAPI._strip_markdown("![alt](url.png)")
        self.assertEqual(text, "")


class TestGitHubAPIPagination(unittest.TestCase):
    @patch("github_api.HTTPClient")
    def test_fetch_all_pages(self, mock_client_cls):
        mock_client = MagicMock()
        # First page 2 items, second page 1 item, third page empty
        mock_client.request.side_effect = [
            (200, '[{"name":"a"},{"name":"b"}]'),
            (200, '[{"name":"c"}]'),
            (200, '[]'),
        ]
        mock_client_cls.return_value = mock_client

        gh = GitHubAPI("token")
        result = gh.fetch_all("user", per_page=2)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["name"], "a")
        self.assertEqual(result[2]["name"], "c")

    @patch("github_api.HTTPClient")
    def test_get_user_repos_pagination(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.request.side_effect = [
            (200, '[{"name":"repo1","fork":true},{"name":"repo2","fork":false}]'),
            (200, '[]'),
        ]
        mock_client_cls.return_value = mock_client

        gh = GitHubAPI("token")
        result = gh.get_user_repos("user", repo_type="owner", per_page=100)
        self.assertEqual(len(result), 2)
