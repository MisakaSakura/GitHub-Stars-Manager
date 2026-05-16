#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段注册器：支持插件化注册和执行"""

from typing import Callable, Any
from utils import log


StageFn = Callable[[Any], Any]


class StageRegistry:
    """流水线阶段注册器：按注册顺序执行，支持依赖声明"""

    def __init__(self):
        self._stages: list[tuple[str, StageFn, list[str]]] = []

    def register(self, name: str, fn: StageFn, deps: list[str] | None = None) -> "StageRegistry":
        self._stages.append((name, fn, deps or []))
        return self

    def run(self, context: Any, skip: set[str] | None = None) -> None:
        skip = skip or set()
        for name, fn, deps in self._stages:
            if name in skip:
                log(f"[Pipeline] 跳过阶段: {name}", "INFO")
                continue
            try:
                log(f"[Pipeline] 执行阶段: {name}", "STEP")
                result = fn(context)
                if result is False:
                    log(f"[Pipeline] 阶段 {name} 要求提前终止", "INFO")
                    break
            except Exception as e:
                log(f"[Pipeline] 阶段 {name} 失败: {e}", "ERROR")
                raise

    @property
    def stage_names(self) -> list[str]:
        return [name for name, _, _ in self._stages]
