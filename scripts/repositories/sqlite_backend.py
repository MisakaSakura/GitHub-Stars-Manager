#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite Repository 实现 —— 替代 JSON 文件存储"""

import json
import re
import sqlite3
from typing import Iterator, Any
from datetime import datetime, timezone

from .base import Repository
from models import StarItem
from utils import log


SCHEMA_TABLES = """
CREATE TABLE IF NOT EXISTS stars (
    full_name TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    description TEXT DEFAULT '',
    language TEXT DEFAULT '文档 / 无代码',
    platform TEXT DEFAULT '其他 / 未分类',
    type TEXT DEFAULT '其他 / 未分类',
    ecology TEXT DEFAULT '独立项目',
    ecology_role TEXT DEFAULT '-',
    topics TEXT DEFAULT '[]',
    stars INTEGER DEFAULT 0,
    url TEXT DEFAULT '',
    first_seen TEXT DEFAULT '',
    last_updated TEXT DEFAULT '',
    manual_override INTEGER DEFAULT 0,
    override_fields TEXT DEFAULT '[]',
    override_rules_version TEXT DEFAULT '',
    subscribe_releases INTEGER DEFAULT 0,
    last_release_tag TEXT,
    is_fork INTEGER DEFAULT 0,
    parent_full_name TEXT,
    parent_pushed_at TEXT,
    imported INTEGER DEFAULT 0,
    github_list_source TEXT
);

CREATE TABLE IF NOT EXISTS ai_results (
    full_name TEXT PRIMARY KEY,
    analyzed_at TEXT DEFAULT '',
    llm_status TEXT DEFAULT 'not_analyzed',
    llm_confidence REAL,
    llm_reason TEXT,
    ai_summary TEXT,
    ai_tags TEXT DEFAULT '[]',
    ai_platforms TEXT DEFAULT '[]',
    ai_platform TEXT,
    ai_type TEXT,
    ai_ecology TEXT,
    ai_ecology_role TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS releases_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    name TEXT,
    owner TEXT,
    old_tag TEXT,
    new_tag TEXT,
    published_at TEXT,
    html_url TEXT,
    body TEXT,
    ai_digest TEXT,
    detected_at TEXT
);
"""

SCHEMA_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_stars_ecology ON stars(ecology);
CREATE INDEX IF NOT EXISTS idx_stars_platform ON stars(platform);
CREATE INDEX IF NOT EXISTS idx_stars_type ON stars(type);
"""

# 保留完整 SCHEMA 供 _parse_schema_columns 使用
SCHEMA = SCHEMA_TABLES + SCHEMA_INDEXES


def _json_dumps(obj: list) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s: str) -> list:
    try:
        return json.loads(s) if s else []
    except Exception:
        return []


class SQLiteStarsRepository(Repository):
    """SQLite 实现的 Stars 存储"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()
        self._meta: dict[str, str] = {}
        self._load_meta()

    @staticmethod
    def _parse_schema_columns(schema_sql: str) -> dict[str, str]:
        """从 CREATE TABLE 语句中提取列名和类型定义（P1-13: 用于自动同步）。
        过滤 ALTER TABLE ADD COLUMN 不支持的约束（PRIMARY KEY、NOT NULL）。"""
        columns = {}
        in_table = False
        for line in schema_sql.split('\n'):
            line = line.strip().rstrip(',')
            if 'CREATE TABLE' in line:
                in_table = True
                continue
            if in_table and line.startswith(')'):
                break
            if in_table and line and not line.startswith('--'):
                parts = line.split(None, 1)
                if len(parts) == 2:
                    col_name, col_def = parts
                    # ALTER TABLE ADD COLUMN 不支持 PRIMARY KEY / NOT NULL
                    col_def = col_def.replace('PRIMARY KEY', '').replace('NOT NULL', '').strip()
                    columns[col_name] = col_def
        return columns

    # P0-4: 列名白名单，防止 SQL 注入
    _VALID_COL_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def _ensure_schema(self) -> None:
        # 先创建表（IF NOT EXISTS 不会失败）
        self._conn.executescript(SCHEMA_TABLES)
        # P1-13: 自动同步缺失的列
        expected = self._parse_schema_columns(SCHEMA_TABLES)
        existing = {row[1] for row in self._conn.execute("PRAGMA table_info(stars)")}
        for col_name, col_def in expected.items():
            if col_name not in existing:
                if not self._VALID_COL_NAME.match(col_name):
                    log(f"跳过非法列名: {col_name}", "WARN")
                    continue
                try:
                    self._conn.execute(f"ALTER TABLE stars ADD COLUMN {col_name} {col_def}")
                except sqlite3.OperationalError:
                    pass  # 列已存在或其他错误
        self._conn.commit()
        # 最后创建索引（需要所有列都已存在）
        self._conn.executescript(SCHEMA_INDEXES)

    def _load_meta(self) -> None:
        cur = self._conn.execute("SELECT key, value FROM meta")
        self._meta = {row["key"]: row["value"] for row in cur.fetchall()}

    def _row_to_item(self, row: sqlite3.Row) -> StarItem:
        return StarItem(
            full_name=row["full_name"],
            name=row["name"],
            owner=row["owner"],
            description=row["description"] or "",
            language=row["language"] or "文档 / 无代码",
            platform=row["platform"] or "其他 / 未分类",
            type=row["type"] or "其他 / 未分类",
            ecology=row["ecology"] or "独立项目",
            ecology_role=row["ecology_role"] or "-",
            topics=_json_loads(row["topics"]),
            stars=row["stars"] or 0,
            url=row["url"] or "",
            first_seen=row["first_seen"] or "",
            last_updated=row["last_updated"] or "",
            manual_override=bool(row["manual_override"]),
            override_fields=_json_loads(row["override_fields"]),
            override_rules_version=row["override_rules_version"] or "",
            subscribe_releases=bool(row["subscribe_releases"]),
            last_release_tag=row["last_release_tag"],
            is_fork=bool(row["is_fork"]),
            parent_full_name=row["parent_full_name"],
            parent_pushed_at=row["parent_pushed_at"],
            imported=bool(row["imported"]),
            github_list_source=row["github_list_source"],
        )

    # GC-10: 列名与属性名的映射表（单一来源）
    _COLUMN_MAP: list[tuple[str, str]] = [
        ("full_name", "full_name"), ("name", "name"), ("owner", "owner"),
        ("description", "description"), ("language", "language"),
        ("platform", "platform"), ("type", "type"),
        ("ecology", "ecology"), ("ecology_role", "ecology_role"),
        ("topics", "topics"), ("stars", "stars"), ("url", "url"),
        ("first_seen", "first_seen"), ("last_updated", "last_updated"),
        ("manual_override", "manual_override"),
        ("override_fields", "override_fields"),
        ("override_rules_version", "override_rules_version"),
        ("subscribe_releases", "subscribe_releases"),
        ("last_release_tag", "last_release_tag"),
        ("is_fork", "is_fork"), ("parent_full_name", "parent_full_name"),
        ("parent_pushed_at", "parent_pushed_at"),
        ("imported", "imported"), ("github_list_source", "github_list_source"),
    ]

    def _item_to_tuple(self, item: StarItem) -> tuple:
        # GC-10: 通过映射表自动生成 tuple，避免列名与顺序人工同步
        result = []
        for col_name, attr_name in self._COLUMN_MAP:
            val = getattr(item, attr_name)
            if col_name in ("topics", "override_fields"):
                result.append(_json_dumps(val))
            elif col_name in ("manual_override", "subscribe_releases", "is_fork", "imported"):
                result.append(int(val))
            else:
                result.append(val)
        return tuple(result)

    def get(self, key: str) -> StarItem | None:
        row = self._conn.execute(
            "SELECT * FROM stars WHERE full_name = ?", (key,)
        ).fetchone()
        return self._row_to_item(row) if row else None

    def set(self, key: str, value: Any) -> None:
        if isinstance(value, dict):
            value = StarItem.from_dict(value)
        t = self._item_to_tuple(value)
        # GC-10: 列名从 _COLUMN_MAP 自动生成，避免人工同步
        col_names = [c for c, _ in self._COLUMN_MAP]
        placeholders = ",".join(["?"] * len(col_names))
        updates = ",".join([f"{c}=excluded.{c}" for c in col_names[1:]])  # 排除主键 full_name
        sql = f"""
            INSERT INTO stars ({','.join(col_names)})
            VALUES ({placeholders})
            ON CONFLICT(full_name) DO UPDATE SET {updates}
        """
        self._conn.execute(sql, t)

    def delete(self, key: str) -> bool:
        cur = self._conn.execute("DELETE FROM stars WHERE full_name = ?", (key,))
        return cur.rowcount > 0

    def keys(self) -> Iterator[str]:
        cur = self._conn.execute("SELECT full_name FROM stars")
        for row in cur:
            yield row[0]

    def values(self) -> Iterator[StarItem]:
        cur = self._conn.execute("SELECT * FROM stars")
        for row in cur:
            yield self._row_to_item(row)

    def items(self) -> Iterator[tuple[str, StarItem]]:
        for row in self._conn.execute("SELECT * FROM stars"):
            item = self._row_to_item(row)
            yield (item.full_name, item)

    def save(self) -> None:
        self._conn.commit()

    def __len__(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM stars").fetchone()
        return row[0] if row else 0

    def meta_get(self, key: str, default=None):
        return self._meta.get(key, default)

    def meta_set(self, key: str, value) -> None:
        self._meta[key] = value

    def meta_save(self) -> None:
        for k, v in self._meta.items():
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (k, str(v))
            )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.commit()
        except Exception:
            pass
        self._conn.close()

    def migrate_from_json(self, json_path: str) -> int:
        """从 JSON 文件导入数据"""
        import os
        if not os.path.exists(json_path):
            return 0
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return 0
        count = 0
        for raw in data:
            if not isinstance(raw, dict):
                continue
            try:
                item = StarItem.from_dict(raw)
                self.set(item.full_name, item)
                count += 1
            except Exception:
                continue
        self.save()
        log(f"SQLite 导入 {count} 条记录从 {json_path}", "OK")
        return count
