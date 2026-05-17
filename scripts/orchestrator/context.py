#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline 共享上下文：替代旧 Pipeline 的 self.* 属性，解耦各阶段"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ai_database import AIDatabase
    from database import StarsDB
    from engine import IncrementalEngine
    from fork_tracker import ForkTracker
    from github_api import GitHubAPI
    from llm_classifier import LLMClassifier
    from release_tracker import ReleaseTracker
    from rule_classifier import RuleClassifier


@dataclass
class PipelineContext:
    """流水线各阶段之间的共享状态容器"""

    args: argparse.Namespace

    db: Optional["StarsDB"] = None
    ai_db: Optional["AIDatabase"] = None
    gh: Optional["GitHubAPI"] = None
    rule: Optional["RuleClassifier"] = None
    llm: Optional["LLMClassifier"] = None
    engine: Optional["IncrementalEngine"] = None

    is_first_run: bool = False
    did_full_refresh: bool = False

    items: list[dict] = field(default_factory=list)
    stats: dict | None = None
    new_keys: set[str] = field(default_factory=set)
    star_changes: dict[str, int] = field(default_factory=dict)
    classification_changes: dict[str, dict] = field(default_factory=dict)

    release_updates: list[dict] = field(default_factory=list)
    fork_updates: list[dict] = field(default_factory=list)

    release_tracker: Optional["ReleaseTracker"] = None
    fork_tracker: Optional["ForkTracker"] = None

    ecology_candidate_summary: list[dict] = field(default_factory=list)

    output_dir: str = "./docs"

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def set(self, key: str, value) -> None:
        setattr(self, key, value)
