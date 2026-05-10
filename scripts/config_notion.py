#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notion 导出配置"""

NOTION_CONFIG = {
    "enabled": False,
    "api_key": None,
    "database_id": None,
    "properties": {
        "Name": {"type": "title", "key": "name"},
        "Owner": {"type": "rich_text", "key": "owner"},
        "URL": {"type": "url", "key": "url"},
        "Platform": {"type": "select", "key": "platform"},
        "Type": {"type": "select", "key": "type"},
        "Language": {"type": "select", "key": "language"},
        "Ecology": {"type": "select", "key": "ecology"},
        "Ecology Role": {"type": "select", "key": "ecology_role"},
        "Stars": {"type": "number", "key": "stars"},
        "Topics": {"type": "multi_select", "key": "topics"},
        "Description": {"type": "rich_text", "key": "description"},
        "Manual Override": {"type": "checkbox", "key": "manual_override"},
    }
}
