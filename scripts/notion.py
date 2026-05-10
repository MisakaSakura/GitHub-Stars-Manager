#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notion 导出器，支持从配置动态映射属性"""

import json
import time

from http_client import HTTPClient
from utils import log


class NotionExporter:
    def __init__(self, api_key: str, database_id: str):
        self.api_key = api_key
        self.database_id = database_id
        self.base = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.client = HTTPClient()
        from config import NOTION_CONFIG
        self.property_map = NOTION_CONFIG.get("properties", {})

    def _build_properties(self, item: dict) -> dict:
        """根据 config.py 中的 NOTION_CONFIG['properties'] 动态构建 Notion properties"""
        properties = {}
        for prop_name, prop_config in self.property_map.items():
            prop_type = prop_config.get("type")
            key = prop_config.get("key")
            value = item.get(key)

            if prop_type == "title":
                properties[prop_name] = {"title": [{"text": {"content": str(value or "")}}]}
            elif prop_type == "rich_text":
                text = str(value or "")[:2000]
                properties[prop_name] = {"rich_text": [{"text": {"content": text}}]}
            elif prop_type == "url":
                properties[prop_name] = {"url": value or ""}
            elif prop_type == "select":
                properties[prop_name] = {"select": {"name": str(value or "-")}}
            elif prop_type == "number":
                properties[prop_name] = {"number": value if isinstance(value, (int, float)) else 0}
            elif prop_type == "multi_select":
                values = value if isinstance(value, list) else []
                properties[prop_name] = {"multi_select": [{"name": str(v)} for v in values[:20]]}
            elif prop_type == "checkbox":
                properties[prop_name] = {"checkbox": bool(value)}
        return properties

    def sync(self, items: list[dict], clear_existing: bool = False) -> tuple[int, int]:
        """同步项目到 Notion 数据库"""
        log("开始同步到 Notion...", "STEP")

        if clear_existing:
            self._clear_database()

        success = 0
        failed = 0
        for item in items:
            try:
                self._create_page(item)
                success += 1
                time.sleep(0.35)
            except Exception as e:
                log(f"Notion 同步失败 {item['full_name']}: {e}", "WARN")
                failed += 1

        log(f"Notion 同步完成: {success} 成功, {failed} 失败", "OK")
        return success, failed

    def _create_page(self, item: dict) -> None:
        url = f"{self.base}/pages"
        properties = self._build_properties(item)
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }
        code, body = self.client.post_json(url, payload, headers=self.headers)
        if code != 200:
            raise Exception(f"{code}: {body[:200]}")

    def _clear_database(self) -> None:
        """清空数据库（通过归档所有页面）"""
        log("清空 Notion 数据库...", "STEP")
        url = f"{self.base}/databases/{self.database_id}/query"
        code, body = self.client.post_json(url, {}, headers=self.headers)
        pages = json.loads(body).get("results", []) if code == 200 else []

        for page in pages:
            page_id = page["id"]
            archive_url = f"{self.base}/pages/{page_id}"
            self.client.request(archive_url, headers=self.headers, method="PATCH",
                                data=json.dumps({"archived": True}))
            time.sleep(0.35)
        log(f"已归档 {len(pages)} 个旧页面", "OK")
