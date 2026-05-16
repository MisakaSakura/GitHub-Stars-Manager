#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline 共享上下文：替代旧 Pipeline 的 self.* 属性，解耦各阶段"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PipelineContext:
    """流水线各阶段之间的共享状态容器"""

    args: Any

    db: Optional[Any] = None
    ai_db: Optional[Any] = None
    gh: Optional[Any] = None
    rule: Optional[Any] = None
    llm: Optional[Any] = None
    engine: Optional[Any] = None

    is_first_run: bool = False
    did_full_refresh: bool = False

    items: list[dict] = field(default_factory=list)
    stats: Optional[dict] = None
    new_keys: set[str] = field(default_factory=set)
    star_changes: dict[str, int] = field(default_factory=dict)
    classification_changes: dict[str, dict] = field(default_factory=dict)

    release_updates: list[dict] = field(default_factory=list)
    fork_updates: list[dict] = field(default_factory=list)

    release_tracker: Optional[Any] = None
    fork_tracker: Optional[Any] = None

    ecology_candidate_summary: list[dict] = field(default_factory=list)

    output_dir: str = "./docs"

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def set(self, key: str, value) -> None:
        setattr(self, key, value)
