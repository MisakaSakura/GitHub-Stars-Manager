#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段注册器：支持插件化注册和执行"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from utils import log


class PipelineStageError(Exception):
    """Pipeline 阶段执行失败的自定义异常，包含阶段名称和原始异常。"""
    def __init__(self, stage_name: str, original: Exception | None = None):
        self.stage_name = stage_name
        self.original = original
        msg = f"Pipeline 阶段 '{stage_name}' 执行失败"
        if original:
            msg += f": {original}"
        super().__init__(msg)


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

    def _topological_sort(self) -> list[tuple[str, StageFn, list[str]]]:
        """GC-9: 按依赖关系进行拓扑排序，返回排序后的阶段列表。"""
        # 构建邻接表和入度表
        in_degree: dict[str, int] = {}
        stage_map: dict[str, tuple[StageFn, list[str]]] = {}
        dependents: dict[str, list[str]] = {}

        for name, fn, deps in self._stages:
            in_degree[name] = len(deps)
            stage_map[name] = (fn, deps)
            for dep in deps:
                dependents.setdefault(dep, []).append(name)

        # Kahn 算法
        queue = [name for name, deg in in_degree.items() if deg == 0]
        result: list[tuple[str, StageFn, list[str]]] = []

        while queue:
            name = queue.pop(0)
            fn, deps = stage_map[name]
            result.append((name, fn, deps))
            for dependent in dependents.get(name, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._stages):
            raise ValueError("Pipeline 阶段拓扑排序失败，可能存在未检测到的循环依赖")

        return result

    def run(self, context: Any, skip: set[str] | None = None) -> None:
        """按依赖拓扑排序后的顺序执行各阶段。

        .. note:: 无事务语义
            本注册器**不提供事务回滚**。某个阶段失败后，此前已执行的阶段
            副作用（如数据库写入、文件生成、通知发送）**不会自动撤销**。
            调用方如需补偿，应在捕获 PipelineStageError 后自行处理。
        """
        self._validate_deps()
        sorted_stages = self._topological_sort()
        skip = skip or set()
        for name, fn, deps in sorted_stages:
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
