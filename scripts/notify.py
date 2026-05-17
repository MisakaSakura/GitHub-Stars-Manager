#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多通道通知系统"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from http_client import HTTPClient
from utils import log


class Notifier:
    def __init__(self, config: dict):
        from config import EMAIL_CONFIG, TELEGRAM_CONFIG, WECOM_CONFIG, QQ_CONFIG
        self.config = config
        self.channels: list = []
        self.client = HTTPClient()
        for ch in config.get("channels", []):
            if ch == "email" and EMAIL_CONFIG.get("smtp_user"):
                self.channels.append(EmailNotifier())
            elif ch == "telegram" and TELEGRAM_CONFIG.get("bot_token"):
                self.channels.append(TelegramNotifier(self.client))
            elif ch == "wecom" and WECOM_CONFIG.get("webhook_url"):
                self.channels.append(WeComNotifier(self.client))
            elif ch == "qq" and QQ_CONFIG.get("api_url"):
                self.channels.append(QQNotifier(self.client))

    def send(self, title: str, message: str, is_error: bool = False) -> None:
        if not self.config.get("enabled") or not self.channels:
            return
        if is_error and not self.config.get("on_error"):
            return
        if not is_error and not self.config.get("on_success"):
            return

        for notifier in self.channels:
            try:
                notifier.send(title, message)
            except Exception as e:
                log(f"通知发送失败 ({notifier.__class__.__name__}): {e}", "WARN")


class EmailNotifier:
    def send(self, title: str, message: str) -> None:
        from config import EMAIL_CONFIG
        cfg = EMAIL_CONFIG
        if not cfg.get("smtp_user"):
            raise ValueError("邮件配置不完整: smtp_user 未设置")
        if not cfg.get("to_addrs"):
            raise ValueError("邮件配置不完整: to_addrs 未设置")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = cfg.get("from_addr") or cfg["smtp_user"]
        msg["To"] = ", ".join(cfg["to_addrs"])

        msg.attach(MIMEText(message, "plain", "utf-8"))
        msg.attach(MIMEText(f"<pre style='font-family:monospace'>{message}</pre>", "html", "utf-8"))

        server = None
        try:
            server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"])
            if cfg.get("use_tls"):
                server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(msg["From"], cfg["to_addrs"], msg.as_string())
            log("邮件通知已发送", "OK")
        except Exception as e:
            log(f"邮件发送失败: {e}", "WARN")
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass


class TelegramNotifier:
    def __init__(self, client: HTTPClient):
        self.client = client

    def send(self, title: str, message: str) -> None:
        from config import TELEGRAM_CONFIG
        cfg = TELEGRAM_CONFIG
        url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
        text = f"*{title}*\n\n```\n{message}\n```"
        payload = {
            "chat_id": cfg["chat_id"],
            "text": text,
            "parse_mode": "Markdown"
        }
        code, body = self.client.post_json(url, payload, timeout=10)
        if code != 200:
            raise RuntimeError(f"Telegram API 错误 {code}: {body[:200]}")
        log("Telegram 通知已发送", "OK")


class WeComNotifier:
    def __init__(self, client: HTTPClient):
        self.client = client

    def send(self, title: str, message: str) -> None:
        from config import WECOM_CONFIG
        cfg = WECOM_CONFIG
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"**{title}**\n> {message.replace(chr(10), chr(10)+'> ')}"
            }
        }
        code, body = self.client.post_json(cfg["webhook_url"], payload, timeout=10)
        if code != 200:
            raise RuntimeError(f"企业微信 API 错误 {code}: {body[:200]}")
        log("企业微信通知已发送", "OK")


class QQNotifier:
    def __init__(self, client: HTTPClient):
        self.client = client

    def send(self, title: str, message: str) -> None:
        from config import QQ_CONFIG
        cfg = QQ_CONFIG
        url = f"{cfg['api_url'].rstrip('/')}/send_msg"
        headers = {}
        if cfg.get("access_token"):
            headers["Authorization"] = f"Bearer {cfg['access_token']}"

        safe_message = message.replace("[CQ:", "&#91;CQ:").replace("]", "&#93;")
        payload = {
            "message": f"{title}\n{safe_message}",
            "auto_escape": True
        }
        if cfg.get("group_id"):
            payload["group_id"] = cfg["group_id"]
        elif cfg.get("user_id"):
            payload["user_id"] = cfg["user_id"]
        else:
            raise ValueError("QQ 通知需要设置 group_id 或 user_id")

        code, body = self.client.post_json(url, payload, headers=headers, timeout=10)
        if code != 200:
            raise RuntimeError(f"QQ API 错误 {code}: {body[:200]}")
        log("QQ 通知已发送", "OK")
