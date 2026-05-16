#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用工具函数"""

import os
import sys
from datetime import datetime, timezone


def log(msg: str, level: str = "INFO") -> None:
    """带时间戳和 emoji 的日志输出，在编码不支持时自动回退 ASCII"""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "STEP": "🔄"}.get(level, "•")
    try:
        print(f"[{ts}] {prefix} {msg}", flush=True)
    except UnicodeEncodeError:
        prefix_ascii = {"INFO": "[I]", "OK": "[OK]", "WARN": "[W]", "ERROR": "[E]", "STEP": "[>"}.get(level, "[*]")
        print(f"[{ts}] {prefix_ascii} {msg}", flush=True)


def _safe_print(msg: str) -> None:
    """安全打印，在编码不支持时回退 ASCII，强制 flush 保证 Actions 中实时可见"""
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        ascii_msg = msg.encode("ascii", "replace").decode("ascii")
        print(ascii_msg, flush=True)


def atomic_write(path: str, write_fn) -> None:
    """原子写入：先写临时文件再替换，带跨进程文件锁保护

    Args:
        path: 目标文件路径
        write_fn: 接收已打开文件对象的回调函数，负责实际写入
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp_path = path + ".tmp"

    # 跨进程文件锁（Unix 用 fcntl，Windows 跳过）
    _lock_file = path + ".lock"
    lock_fd = None
    try:
        lock_fd = open(_lock_file, "w")
        try:
            import fcntl
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        except ImportError:
            pass  # Windows 无 fcntl，依赖 workflow concurrency 控制
    except Exception:
        pass

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            write_fn(f)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise
    finally:
        if lock_fd:
            try:
                import fcntl
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except ImportError:
                pass
            try:
                lock_fd.close()
            except Exception:
                pass
