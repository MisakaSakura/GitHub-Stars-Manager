#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stars 数据库"""

import json
import os

from models import StarItem
from utils import log


class StarsDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.data = {}
        self.load()

    def load(self) -> None:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                if not isinstance(items, list):
                    raise ValueError(f"数据库格式错误: 期望 JSON 数组，实际为 {type(items).__name__}")
                self.data = {item["full_name"]: StarItem.from_dict(item) for item in items if isinstance(item, dict)}
                log(f"加载数据库: {len(self.data)} 个项目", "OK")
            except Exception as e:
                log(f"数据库损坏，将重建: {e}", "WARN")
                self.data = {}
        else:
            log("数据库不存在，将创建新数据库")
            self.data = {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        tmp_path = self.db_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump([self._serialize(item) for item in self.data.values()], f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.db_path)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise

    def get(self, key: str) -> StarItem | dict | None:
        return self.data.get(key)

    def set(self, key: str, value: StarItem | dict) -> None:
        if isinstance(value, dict) and {"full_name", "name", "owner"}.issubset(value):
            value = StarItem.from_dict(value)
        self.data[key] = value

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def __len__(self) -> int:
        return len(self.data)

    @staticmethod
    def _serialize(item: StarItem | dict) -> dict:
        return item.to_dict() if isinstance(item, StarItem) else item
