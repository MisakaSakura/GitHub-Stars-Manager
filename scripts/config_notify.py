#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通知配置：通用开关与各通道参数"""

NOTIFY_CONFIG = {
    "enabled": False,
    "channels": [],  # 可选: "email", "telegram", "wecom", "qq"
    "on_success": True,
    "on_error": True,
    "summary_only": True,  # 只发送摘要，不发完整列表
}

# 邮件通知
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": None,
    "smtp_password": None,
    "from_addr": None,
    "to_addrs": [],  # 收件人列表
    "use_tls": True,
}

# Telegram 通知
TELEGRAM_CONFIG = {
    "bot_token": None,
    "chat_id": None,
    "parse_mode": "Markdown",
}

# 企业微信通知
WECOM_CONFIG = {
    "webhook_url": None,
}

# QQ 通知（通过 go-cqhttp HTTP API）
QQ_CONFIG = {
    "api_url": None,  # 如 http://127.0.0.1:5700
    "user_id": None,  # QQ 号
    "group_id": None,  # 群号（二选一）
    "access_token": None,
}
