#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用工具函数"""

import os
from datetime import datetime, timezone


def log(msg: str, level: str = "INFO") -> None:
    """带时间戳和 emoji 的日志输出。CI 环境（CI=true）自动使用 ASCII 前缀。"""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # CI 环境或编码不支持时使用 ASCII 前缀
    if os.environ.get("CI", "").lower() == "true":
        prefix = {"INFO": "[I]", "OK": "[OK]", "WARN": "[W]", "ERROR": "[E]", "STEP": "[>"}.get(level, "[*]")
        print(f"[{ts}] {prefix} {msg}", flush=True)
        return
    prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "STEP": "🔄"}.get(level, "•")
    try:
        print(f"[{ts}] {prefix} {msg}", flush=True)
    except UnicodeEncodeError:
        prefix = {"INFO": "[I]", "OK": "[OK]", "WARN": "[W]", "ERROR": "[E]", "STEP": "[>"}.get(level, "[*]")
        print(f"[{ts}] {prefix} {msg}", flush=True)


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

    # 跨进程文件锁（Unix 用 fcntl，Windows 用 msvcrt）
    _lock_file = path + ".lock"
    lock_fd = None
    try:
        lock_fd = open(_lock_file, "w")
        _acquire_file_lock(lock_fd)
    except OSError as e:
        log(f"文件锁获取失败（将继续无锁写入）: {e}", "WARN")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            write_fn(f)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
    finally:
        if lock_fd:
            _release_file_lock(lock_fd)
            try:
                lock_fd.close()
            except OSError:
                pass


def _acquire_file_lock(fd) -> bool:
    """跨平台获取文件锁（独占锁）。P1-41: Windows 使用非阻塞模式 + 重试，避免无限阻塞。"""
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX)
        return True
    except ImportError:
        pass
    try:
        import msvcrt
        import time
        fd.seek(0)
        # 使用 LK_NBLCK 非阻塞模式，配合重试避免无限阻塞
        for _attempt in range(10):
            try:
                msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                time.sleep(0.05)
        log("Windows 文件锁获取超时（10次重试）", "WARN")
        return False
    except (ImportError, OSError):
        pass
    return False


def _release_file_lock(fd) -> None:
    """跨平台释放文件锁。"""
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)
    except ImportError:
        pass
    try:
        import msvcrt
        fd.seek(0)
        msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
    except (ImportError, OSError):
        pass


# ═══════════════════════════════════════════════════════════════
# GC-12: 统一时间解析函数
# ═══════════════════════════════════════════════════════════════

def parse_iso(ts: str) -> "datetime | None":
    """解析 ISO 8601 时间字符串为 aware datetime 对象。

    统一处理以下变体：
    - 带 Z 后缀: "2024-01-01T00:00:00Z"
    - 带 +00:00 后缀: "2024-01-01T00:00:00+00:00"
    - 无 tz 后缀（旧数据）: "2024-01-01T00:00:00" → 自动附加 timezone.utc

    Returns:
        aware datetime 对象，解析失败时返回 None
    """
    if not ts:
        return None
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None
