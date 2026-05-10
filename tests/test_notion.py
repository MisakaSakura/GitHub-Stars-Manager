#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NotionExporter 单元测试"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from notion import NotionExporter


class TestNotionExporter(unittest.TestCase):
    @patch("config.NOTION_CONFIG", {
        "properties": {
            "Name": {"type": "title", "key": "name"},
            "Platform": {"type": "select", "key": "platform"},
            "Stars": {"type": "number", "key": "stars"},
            "Topics": {"type": "multi_select", "key": "topics"},
            "Manual Override": {"type": "checkbox", "key": "manual_override"},
        }
    })
    def test_build_properties(self):
        exporter = NotionExporter("key", "dbid")
        item = {
            "name": "test-repo",
            "platform": "Web 前端",
            "stars": 42,
            "topics": ["react", "frontend"],
            "manual_override": True,
        }
        props = exporter._build_properties(item)
        self.assertEqual(props["Name"]["title"][0]["text"]["content"], "test-repo")
        self.assertEqual(props["Platform"]["select"]["name"], "Web 前端")
        self.assertEqual(props["Stars"]["number"], 42)
        self.assertEqual(len(props["Topics"]["multi_select"]), 2)
        self.assertTrue(props["Manual Override"]["checkbox"])

    @patch("config.NOTION_CONFIG", {"properties": {}})
    @patch("notion.HTTPClient")
    def test_create_page_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.post_json.return_value = (200, '{"id":"page1"}')
        mock_client_cls.return_value = mock_client

        exporter = NotionExporter("key", "dbid")
        exporter._create_page({"name": "repo"})
        mock_client.post_json.assert_called_once()
        args, kwargs = mock_client.post_json.call_args
        payload = kwargs.get("payload") or args[1]
        self.assertIn("dbid", payload["parent"]["database_id"])

    @patch("config.NOTION_CONFIG", {"properties": {}})
    @patch("notion.HTTPClient")
    def test_create_page_failure_raises(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.post_json.return_value = (400, "Bad Request")
        mock_client_cls.return_value = mock_client

        exporter = NotionExporter("key", "dbid")
        with self.assertRaises(Exception):
            exporter._create_page({"name": "repo"})

    @patch("config.NOTION_CONFIG", {"properties": {}})
    @patch("notion.HTTPClient")
    def test_sync_counts_success_and_failure(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.post_json.side_effect = [
            (200, '{"id":"page1"}'),
            (400, "error"),
        ]
        mock_client_cls.return_value = mock_client

        exporter = NotionExporter("key", "dbid")
        items = [{"name": "repo1", "full_name": "a/b"}, {"name": "repo2", "full_name": "c/d"}]
        success, failed = exporter.sync(items)
        self.assertEqual(success, 1)
        self.assertEqual(failed, 1)

    @patch("config.NOTION_CONFIG", {"properties": {}})
    @patch("notion.HTTPClient")
    def test_clear_database_archives_pages(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.post_json.return_value = (200, '{"results":[{"id":"p1"},{"id":"p2"}]}')
        mock_client.request.return_value = (200, "")
        mock_client_cls.return_value = mock_client

        exporter = NotionExporter("key", "dbid")
        exporter._clear_database()
        self.assertEqual(mock_client.request.call_count, 2)
