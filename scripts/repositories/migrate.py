#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据迁移脚本：JSON → SQLite

用法:
    python -m scripts.repositories.migrate --from ./data/stars_db.json --to ./data/stars.db
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from repositories.sqlite_backend import SQLiteStarsRepository
from utils import log


def migrate_stars_db(json_path: str, sqlite_path: str) -> int:
    """迁移主数据库"""
    repo = SQLiteStarsRepository(sqlite_path)
    count = repo.migrate_from_json(json_path)
    repo.close()
    return count


def main():
    parser = argparse.ArgumentParser(description="JSON → SQLite 迁移工具")
    parser.add_argument("--from", dest="source", required=True, help="源 JSON 文件路径")
    parser.add_argument("--to", dest="target", required=True, help="目标 SQLite 文件路径")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"错误: 源文件不存在: {args.source}")
        sys.exit(1)

    log(f"开始迁移: {args.source} → {args.sqlite}", "STEP")
    count = migrate_stars_db(args.source, args.target)
    log(f"迁移完成: {count} 条记录", "OK")


if __name__ == "__main__":
    main()
