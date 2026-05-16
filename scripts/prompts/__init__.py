#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prompt 模板加载器"""

import os
from typing import Callable


class PromptLoader:
    """从文件加载 prompt 模板，支持字符串格式化替换"""

    _cache: dict[str, str] = {}

    @classmethod
    def load(cls, name: str) -> str:
        """加载指定名称的 prompt 模板文件"""
        if name in cls._cache:
            return cls._cache[name]

        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, f"{name}.txt")
        with open(path, "r", encoding="utf-8") as f:
            template = f.read()
        cls._cache[name] = template
        return template

    @classmethod
    def render(cls, name: str, **kwargs) -> str:
        """加载模板并替换变量"""
        template = cls.load(name)
        return template.format(**kwargs)

    @classmethod
    def clear_cache(cls) -> None:
        """清除模板缓存（支持热重载）"""
        cls._cache.clear()
