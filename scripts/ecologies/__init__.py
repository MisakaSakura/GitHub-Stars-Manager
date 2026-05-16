#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生态规则自动注册包

用法:
    from ecologies import ECOLOGY_RULES  # 加载全部生态规则

每个子模块通过 register_ecology() 注册自己的规则。
新增生态：在 ecologies/ 目录下新建 .py 文件即可，无需修改 config_rules.py。
"""

import importlib
import os

ECOLOGY_REGISTRY: dict[str, dict] = {}


def register_ecology(name: str, rules: dict) -> None:
    """注册一个生态的规则定义。子模块应在导入时调用。"""
    ECOLOGY_REGISTRY[name] = rules


# 自动导入 ecologies/ 目录下所有非下划线开头的 .py 模块
_current_dir = os.path.dirname(__file__)
for _filename in sorted(os.listdir(_current_dir)):
    if _filename.endswith(".py") and not _filename.startswith("_"):
        _mod_name = _filename[:-3]
        importlib.import_module(f".{_mod_name}", __package__)

# 导出统一的规则字典（保持与旧版 config_rules.ECOLOGY_RULES 完全兼容）
ECOLOGY_RULES: dict[str, dict] = dict(ECOLOGY_REGISTRY)
