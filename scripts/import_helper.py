#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首次运行辅助：数据导入"""

import csv
import json
import os
from datetime import datetime, timezone

from config_rules import RULES_VERSION
from utils import log


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


class FirstRunHelper:
    """帮助用户从已有分类导入或平滑过渡到新系统"""

    @staticmethod
    def detect_first_run(db_path: str) -> bool:
        """检测是否是首次运行（数据库不存在或为空）"""
        if not os.path.exists(db_path):
            return True
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return len(data) == 0
        except Exception:
            return True

    @staticmethod
    def import_from_json(db, import_path: str, skip_reclassify: bool = False) -> int:
        """从外部 JSON 导入已有分类"""
        log(f"从 {import_path} 导入已有分类...", "STEP")
        with open(import_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        imported = 0
        for item in items:
            key = item.get("full_name")
            if not key:
                continue
            parts = key.split("/")
            if len(parts) >= 2 and all(parts):
                item.setdefault("name", parts[1])
                item.setdefault("owner", parts[0])
            item["manual_override"] = True
            item["override_fields"] = ["platform", "type", "ecology", "ecology_role", "language"]
            item["override_rules_version"] = RULES_VERSION
            item["first_seen"] = datetime.now(timezone.utc).isoformat()
            item["last_updated"] = item["first_seen"]
            item["imported"] = True
            db.set(key, item)
            imported += 1

        log(f"已导入 {imported} 个项目（标记为手动保护）", "OK")
        return imported

    @staticmethod
    def import_from_csv(db, import_path: str) -> int:
        """从 CSV 导入已有分类"""
        log(f"从 {import_path} 导入已有分类...", "STEP")
        imported = 0
        with open(import_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("full_name") or f"{row.get('owner')}/{row.get('name')}"
                if not key or "/" not in key:
                    continue

                parts = key.split("/")
                item = {
                    "full_name": key,
                    "name": row.get("name", parts[1] if len(parts) >= 2 else ""),
                    "owner": row.get("owner", parts[0] if len(parts) >= 1 else ""),
                    "description": row.get("description", ""),
                    "language": row.get("language", "文档 / 无代码"),
                    "platform": row.get("platform", "其他 / 未分类"),
                    "type": row.get("type", "其他 / 未分类"),
                    "ecology": row.get("ecology", "独立项目 / Standalone"),
                    "ecology_role": row.get("ecology_role", "-"),
                    "topics": row.get("topics", "").split(", ") if row.get("topics") else [],
                    "stars": _safe_int(row.get("stars"), 0),
                    "url": row.get("url", ""),
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "manual_override": True,
                    "override_fields": ["platform", "type", "ecology", "ecology_role", "language"],
                    "imported": True,
                }
                db.set(key, item)
                imported += 1

        log(f"已导入 {imported} 个项目（标记为手动保护）", "OK")
        return imported
