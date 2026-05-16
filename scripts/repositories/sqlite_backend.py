#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite Repository 实现 —— 替代 JSON 文件存储"""

import json
import sqlite3
from typing import Iterator, Any
from datetime import datetime, timezone

from .base import Repository
from models import StarItem
from utils import log


SCHEMA = """
CREATE TABLE IF NOT EXISTS stars (
    full_name TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    description TEXT DEFAULT '',
    language TEXT DEFAULT '文档 / 无代码',
    platform TEXT DEFAULT '其他 / 未分类',
    type TEXT DEFAULT '其他 / 未分类',
    ecology TEXT DEFAULT '独立项目 / Standalone',
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

CREATE INDEX IF NOT EXISTS idx_stars_ecology ON stars(ecology);
CREATE INDEX IF NOT EXISTS idx_stars_platform ON stars(platform);
CREATE INDEX IF NOT EXISTS idx_stars_type ON stars(type);
"""


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
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()
        self._meta: dict[str, str] = {}
        self._load_meta()

    def _ensure_schema(self) -> None:
        self._conn.executescript(SCHEMA)
        # Schema 迁移：为旧数据库添加 override_rules_version 列
        try:
            self._conn.execute("ALTER TABLE stars ADD COLUMN override_rules_version TEXT DEFAULT ''")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # 列已存在
        self._conn.commit()

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
            ecology=row["ecology"] or "独立项目 / Standalone",
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

    def _item_to_tuple(self, item: StarItem) -> tuple:
        return (
            item.full_name, item.name, item.owner,
            item.description, item.language, item.platform, item.type,
            item.ecology, item.ecology_role,
            _json_dumps(item.topics), item.stars, item.url,
            item.first_seen, item.last_updated,
            int(item.manual_override), _json_dumps(item.override_fields),
            item.override_rules_version,
            int(item.subscribe_releases), item.last_release_tag,
            int(item.is_fork), item.parent_full_name, item.parent_pushed_at,
            int(item.imported), item.github_list_source,
        )

    def get(self, key: str) -> StarItem | None:
        row = self._conn.execute(
            "SELECT * FROM stars WHERE full_name = ?", (key,)
        ).fetchone()
        return self._row_to_item(row) if row else None

    def set(self, key: str, value: Any) -> None:
        if isinstance(value, dict):
            value = StarItem.from_dict(value)
        t = self._item_to_tuple(value)
        self._conn.execute("""
            INSERT INTO stars VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(full_name) DO UPDATE SET
                name=excluded.name, owner=excluded.owner,
                description=excluded.description, language=excluded.language,
                platform=excluded.platform, type=excluded.type,
                ecology=excluded.ecology, ecology_role=excluded.ecology_role,
                topics=excluded.topics, stars=excluded.stars, url=excluded.url,
                first_seen=excluded.first_seen, last_updated=excluded.last_updated,
                manual_override=excluded.manual_override, override_fields=excluded.override_fields,
                override_rules_version=excluded.override_rules_version,
                subscribe_releases=excluded.subscribe_releases, last_release_tag=excluded.last_release_tag,
                is_fork=excluded.is_fork, parent_full_name=excluded.parent_full_name,
                parent_pushed_at=excluded.parent_pushed_at, imported=excluded.imported,
                github_list_source=excluded.github_list_source
        """, t)

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
