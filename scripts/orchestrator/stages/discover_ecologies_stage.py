#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discover Ecologies 阶段：生态自动发现 + 自动应用高置信度规则"""

import json
import os

from orchestrator.context import PipelineContext
from ecology_discovery import EcologyDiscovery
from config_rules import ECOLOGY_RULES
from utils import log


# 自动生态规则持久化路径（data 分支）
_AUTO_ECOLOGIES_FILENAME = "auto_ecologies.json"


def _get_auto_ecologies_path(ctx: PipelineContext) -> str:
    return os.path.join(os.path.dirname(ctx.args.db), _AUTO_ECOLOGIES_FILENAME)


def _load_auto_ecologies(ctx: PipelineContext) -> dict:
    """加载已保存的自动生态规则"""
    path = _get_auto_ecologies_path(ctx)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_auto_ecologies(ctx: PipelineContext, rules: dict) -> None:
    """保存自动生态规则到 data 分支"""
    path = _get_auto_ecologies_path(ctx)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        log(f"自动生态规则已保存: {path}", "OK")
    except Exception as e:
        log(f"自动生态规则保存失败: {e}", "WARN")


def _apply_auto_ecologies(ctx: PipelineContext, candidates: list) -> list[str]:
    """将高置信度候选生态添加到自动规则，返回已应用的生态名称列表"""
    existing_rules = _load_auto_ecologies(ctx)
    applied: list[str] = []

    for c in candidates:
        # 阈值：>= 5 个项目且置信度 >= 50%
        if c.project_count < 5 or c.confidence < 0.5:
            continue
        name = c.name
        if name in existing_rules:
            continue
        # 避免与已有生态规则冲突
        if name.lower() in {k.lower() for k in ECOLOGY_RULES.keys()}:
            continue

        existing_rules[name] = c.suggested_patterns
        applied.append(name)

    if applied:
        _save_auto_ecologies(ctx, existing_rules)

    return applied


def discover_ecologies_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run or not ctx.db:
        return
    discovery = EcologyDiscovery(ctx.db, ECOLOGY_RULES)
    candidates = discovery.discover(top_n=10)

    # 自动应用高置信度候选
    if candidates:
        auto_applied = _apply_auto_ecologies(ctx, candidates)
        if auto_applied:
            log(f"自动添加 {len(auto_applied)} 个生态规则: {', '.join(auto_applied)}", "OK")

    if candidates:
        md = discovery.generate_report(candidates)
        out_path = os.path.join(ctx.args.output, "ecology_discovery.md")
        try:
            os.makedirs(ctx.args.output, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md)
            log(f"生态发现报告已生成: {out_path}", "OK")
        except Exception as e:
            log(f"生态发现报告写入失败: {e}", "WARN")
