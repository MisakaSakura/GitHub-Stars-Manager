#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用工具函数"""

import sys
from datetime import datetime, timezone


def log(msg: str, level: str = "INFO") -> None:
    """带时间戳和 emoji 的日志输出，在编码不支持时自动回退 ASCII"""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "STEP": "🔄"}.get(level, "•")
    try:
        print(f"[{ts}] {prefix} {msg}")
    except UnicodeEncodeError:
        prefix_ascii = {"INFO": "[I]", "OK": "[OK]", "WARN": "[W]", "ERROR": "[E]", "STEP": "[>"}.get(level, "[*]")
        print(f"[{ts}] {prefix_ascii} {msg}")
