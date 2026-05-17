#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通知系统单元测试"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from notify import Notifier, EmailNotifier, TelegramNotifier, WeComNotifier, QQNotifier


class TestNotifierDispatch(unittest.TestCase):
    @patch("config.EMAIL_CONFIG", {"smtp_user": "user@example.com"})
    @patch("config.TELEGRAM_CONFIG", {"bot_token": "bot123"})
    @patch("config.WECOM_CONFIG", {"webhook_url": "https://wecom"})
    @patch("config.QQ_CONFIG", {"api_url": "http://qq"})
    def test_init_creates_channels(self):
        config = {"enabled": True, "channels": ["email", "telegram", "wecom", "qq"], "on_success": True, "on_error": True}
        notifier = Notifier(config)
        self.assertEqual(len(notifier.channels), 4)

    @patch("config.EMAIL_CONFIG", {})
    def test_init_skips_unconfigured_channels(self):
        config = {"enabled": True, "channels": ["email"], "on_success": True, "on_error": True}
        notifier = Notifier(config)
        self.assertEqual(len(notifier.channels), 0)

    def test_send_disabled(self):
        config = {"enabled": False, "channels": ["email"], "on_success": True}
        notifier = Notifier(config)
        with patch.object(notifier, "channels", [MagicMock()]):
            notifier.send("title", "msg")
            notifier.channels[0].send.assert_not_called()

    def test_send_respects_on_success(self):
        config = {"enabled": True, "channels": ["email"], "on_success": False, "on_error": True}
        notifier = Notifier(config)
        mock_ch = MagicMock()
        notifier.channels = [mock_ch]
        notifier.send("title", "msg", is_error=False)
        mock_ch.send.assert_not_called()

    def test_send_dispatches_to_all_channels(self):
        config = {"enabled": True, "channels": ["email"], "on_success": True, "on_error": True}
        notifier = Notifier(config)
        mock_ch1 = MagicMock()
        mock_ch2 = MagicMock()
        notifier.channels = [mock_ch1, mock_ch2]
        notifier.send("title", "msg")
        mock_ch1.send.assert_called_once_with("title", "msg")
        mock_ch2.send.assert_called_once_with("title", "msg")


class TestEmailNotifier(unittest.TestCase):
    @patch("config.EMAIL_CONFIG", {
        "smtp_server": "smtp.test.com",
        "smtp_port": 587,
        "smtp_user": "user@test.com",
        "smtp_password": "pass",
        "from_addr": "from@test.com",
        "to_addrs": ["to@test.com"],
        "use_tls": True,
    })
    @patch("notify.smtplib.SMTP")
    def test_send_email(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server
        notifier = EmailNotifier()
        notifier.send("Test Title", "Test Message")
        mock_smtp_cls.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "pass")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()


class TestTelegramNotifier(unittest.TestCase):
    @patch("config.TELEGRAM_CONFIG", {"bot_token": "bot123", "chat_id": "chat456"})
    def test_send_telegram(self):
        client = MagicMock()
        client.post_json.return_value = (200, "{}")
        notifier = TelegramNotifier(client)
        notifier.send("Title", "Body")
        client.post_json.assert_called_once()
        args, kwargs = client.post_json.call_args
        payload = kwargs.get("payload") or args[1]
        self.assertIn("bot123", args[0])
        self.assertIn("chat456", payload["chat_id"])


class TestWeComNotifier(unittest.TestCase):
    @patch("config.WECOM_CONFIG", {"webhook_url": "https://wecom.hook"})
    def test_send_wecom(self):
        client = MagicMock()
        client.post_json.return_value = (200, "{}")
        notifier = WeComNotifier(client)
        notifier.send("Title", "Line1\nLine2")
        client.post_json.assert_called_once()
        args, kwargs = client.post_json.call_args
        payload = kwargs.get("payload") or args[1]
        self.assertEqual(args[0], "https://wecom.hook")
        self.assertIn("Line1", payload["markdown"]["content"])


class TestQQNotifier(unittest.TestCase):
    @patch("config.QQ_CONFIG", {"api_url": "http://127.0.0.1:5700", "group_id": "12345"})
    def test_send_qq_group(self):
        client = MagicMock()
        client.post_json.return_value = (200, "{}")
        notifier = QQNotifier(client)
        notifier.send("Title", "Hello")
        client.post_json.assert_called_once()
        args, kwargs = client.post_json.call_args
        payload = kwargs.get("payload") or args[1]
        self.assertEqual(payload["group_id"], "12345")
        self.assertTrue(payload["auto_escape"])
        self.assertIn("Hello", payload["message"])

    @patch("config.QQ_CONFIG", {"api_url": "http://127.0.0.1:5700", "user_id": "98765"})
    def test_send_qq_user(self):
        client = MagicMock()
        client.post_json.return_value = (200, "{}")
        notifier = QQNotifier(client)
        notifier.send("Title", "Hello")
        args, kwargs = client.post_json.call_args
        payload = kwargs.get("payload") or args[1]
        self.assertEqual(payload["user_id"], "98765")

    @patch("config.QQ_CONFIG", {"api_url": "http://127.0.0.1:5700"})
    def test_send_qq_no_target_raises(self):
        client = MagicMock()
        notifier = QQNotifier(client)
        with self.assertRaises(ValueError):
            notifier.send("Title", "Hello")

    @patch("config.QQ_CONFIG", {"api_url": "http://127.0.0.1:5700", "group_id": "1", "access_token": "tok"})
    def test_send_qq_escapes_cq(self):
        client = MagicMock()
        client.post_json.return_value = (200, "{}")
        notifier = QQNotifier(client)
        notifier.send("Title", "[CQ:at,qq=123]")
        args, kwargs = client.post_json.call_args
        payload = kwargs.get("payload") or args[1]
        self.assertNotIn("[CQ:", payload["message"])
