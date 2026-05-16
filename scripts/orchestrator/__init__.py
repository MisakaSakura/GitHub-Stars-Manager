#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline 插件化模块（orchestrator）：阶段注册器 + 共享上下文"""

from .context import PipelineContext
from .registry import StageRegistry
from .new_pipeline import Pipeline

__all__ = ["PipelineContext", "StageRegistry", "Pipeline"]
