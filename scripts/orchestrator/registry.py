#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段注册器：支持插件化注册和执行"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from utils import log


@runtime_checkable
class StageFn(Protocol):
    """Pipeline 阶段函数协议：接收 PipelineContext，返回任意值或 None。"""
    def __call__(self, ctx: Any) -> Any: ...


class StageRegistry:
    """流水线阶段注册器：按注册顺序执行，支持依赖声明和验证。"""

    def __init__(self):
        self._stages: list[tuple[str, StageFn, list[str]]] = []

    def register(self, name: str, fn: StageFn, deps: list[str] | None = None) -> StageRegistry:
        self._stages.append((name, fn, deps or []))
        return self

    def _validate_deps(self) -> None:
        """验证依赖：检查所有依赖是否已注册、无循环依赖。"""
        registered = {name for name, _, _ in self._stages}
        # 检查依赖是否存在
        for name, _, deps in self._stages:
            for dep in deps:
                if dep not in registered:
                    raise ValueError(f"阶段 '{name}' 依赖 '{dep}' 未注册")
        # 拓扑排序检测循环依赖
        visited: set[str] = set()
        temp: set[str] = set()

        def visit(n: str) -> None:
            if n in temp:
                raise ValueError(f"Pipeline 阶段存在循环依赖，涉及: {n}")
            if n in visited:
                return
            temp.add(n)
            for stage_name, _, deps in self._stages:
                if stage_name == n:
                    for d in deps:
                        visit(d)
            temp.remove(n)
            visited.add(n)

        for name, _, _ in self._stages:
            visit(name)

    def run(self, context: Any, skip: set[str] | None = None) -> None:
        self._validate_deps()
        skip = skip or set()
        for name, fn, deps in self._stages:
            if name in skip:
                log(f"[Pipeline] 跳过阶段: {name}", "INFO")
                continue
            try:
                log(f"[Pipeline] 执行阶段: {name}", "STEP")
                result = fn(context)
                if result is True:
                    log(f"[Pipeline] 阶段 {name} 要求提前终止", "INFO")
                    break
            except Exception as e:
                log(f"[Pipeline] 阶段 {name} 失败: {e}", "ERROR")
                raise

    @property
    def stage_names(self) -> list[str]:
        return [name for name, _, _ in self._stages]
