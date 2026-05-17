#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生态规则自动注册包

用法:
    from ecologies import ECOLOGY_RULES  # 从 YAML 加载全部生态规则

新增生态：修改 data/ecologies.yaml，无需新建 Python 文件。
"""

from typing import TypedDict
import os
import sys

import yaml


class EcologyRule(TypedDict):
    """生态规则的数据结构（P1-81: TypedDict 约束）。"""

    display_name: str
    name_patterns: list[str]
    desc_patterns: list[str]
    topic_patterns: list[str]
    related_types: list[str]
    core_projects: list[str]


ECOLOGY_REGISTRY: dict[str, EcologyRule] = {}


def _load_ecologies_from_yaml() -> dict[str, EcologyRule]:
    """从 data/ecologies.yaml 加载生态规则。"""
    # 查找 ecologies.yaml 路径（支持本地开发和 Actions 运行）
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "ecologies.yaml"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "ecologies.yaml"),
        os.path.join(os.getcwd(), "data", "ecologies.yaml"),
    ]
    yaml_path = None
    for c in candidates:
        if os.path.exists(c):
            yaml_path = c
            break

    if yaml_path is None:
        print("[WARN] 未找到 data/ecologies.yaml，生态规则为空", file=sys.stderr)
        return {}

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"[WARN] 生态规则 YAML 加载失败: {e}", file=sys.stderr)
        return {}

    if not isinstance(data, dict):
        print(f"[WARN] 生态规则 YAML 格式错误: 期望 dict，实际 {type(data).__name__}", file=sys.stderr)
        return {}

    registry: dict[str, EcologyRule] = {}
    seen_names: set[str] = set()

    for key, raw in data.items():
        if not isinstance(raw, dict):
            print(f"[WARN] 生态 {key} 格式错误，已跳过", file=sys.stderr)
            continue

        display_name = raw.get("display_name", key)

        # P1-82: 重复注册检测
        if display_name in seen_names:
            print(f"[WARN] 生态 '{display_name}' 重复定义，已跳过", file=sys.stderr)
            continue
        seen_names.add(display_name)

        # 验证必要字段
        name_patterns = raw.get("name_patterns", [])
        if not name_patterns:
            print(f"[WARN] 生态 '{display_name}' 的 name_patterns 为空，已跳过", file=sys.stderr)
            continue

        rule: EcologyRule = {
            "display_name": display_name,
            "name_patterns": name_patterns,
            "desc_patterns": raw.get("desc_patterns", []),
            "topic_patterns": raw.get("topic_patterns", []),
            "related_types": raw.get("related_types", []),
            "core_projects": raw.get("core_projects", []),
        }
        registry[display_name] = rule

    return registry


# 加载生态规则（替代原来的动态导入）
ECOLOGY_REGISTRY = _load_ecologies_from_yaml()

# 导出统一的规则字典（保持与旧版 config_rules.ECOLOGY_RULES 完全兼容）
ECOLOGY_RULES: dict[str, dict] = {k: dict(v) for k, v in ECOLOGY_REGISTRY.items()}
