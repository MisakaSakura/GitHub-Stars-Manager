#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTPClient 单元测试"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from http_client import HTTPClient


class TestHTTPClient(unittest.TestCase):
    def tearDown(self):
        # P1-54: 重置 _session，避免影响后续测试
        HTTPClient.close()

    @patch("http_client.HAS_REQUESTS", False)
    @patch("urllib.request.urlopen")
    def test_urllib_get_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        code, body = HTTPClient.request("https://example.com/api")
        self.assertEqual(code, 200)
        self.assertEqual(body, '{"ok": true}')

    @patch("http_client.HAS_REQUESTS", False)
    @patch("urllib.request.urlopen")
    def test_urllib_http_error(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        code, body = HTTPClient.request("https://example.com/api")
        self.assertEqual(code, 404)

    @patch("http_client.HAS_REQUESTS", True)
    def test_requests_post_json(self):
        import http_client as hc
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.text = "created"
        mock_session.request.return_value = mock_resp
        # 注入 mock session
        with patch.object(hc.HTTPClient, "_session", mock_session):
            code, body = HTTPClient.post_json("https://example.com", {"key": "val"})
        self.assertEqual(code, 201)
        self.assertEqual(body, "created")
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        self.assertEqual(call_args[0][0], "POST")
