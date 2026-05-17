#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classify 阶段：规则分类 + LLM 增强"""

from orchestrator.context import PipelineContext
from llm_classifier import LLMClassifier
from engine import IncrementalEngine
from utils import log


def _should_setup_llm(args) -> bool:
    """根据 llm_mode 判断是否应该创建 LLM 客户端（P1-51: 单一来源）。"""
    if args.llm_mode == "off" or not args.llm_key:
        return False
    # auto: 保持向后兼容，只要有 llm_key 就启用
    return True


def setup_llm_stage(ctx: PipelineContext) -> None:
    if not _should_setup_llm(ctx.args):
        return
    from model_profiles import get_preset_default_model
    default_model = get_preset_default_model(ctx.args.llm_preset or "")
    model = ctx.args.llm_model or default_model
    ctx.llm = LLMClassifier(
        api_key=ctx.args.llm_key,
        provider=ctx.args.llm_provider,
        api_base=ctx.args.llm_base,
        model=model
    )
    if not ctx.args.llm_model:
        log(f"LLM 使用 provider 默认模型: {ctx.args.llm_provider} / {model}")
    else:
        log(f"LLM 已启用: {ctx.args.llm_provider} / {model}")


def enrich_stage(ctx: PipelineContext) -> None:
    if not ctx.llm:
        return
    from engine import IncrementalEngine
    llm_interval = getattr(ctx.args, 'llm_interval_days', 30)
    force_llm = getattr(ctx.args, 'force_llm', False)
    retry_failed = ctx.args.retry_failed

    # P1-7: 预加载所有 existing 记录，避免 N+1 查询
    existing_map: dict[str, Any] = {}
    if hasattr(ctx.db, 'items') and callable(ctx.db.items):
        try:
            for key, val in ctx.db.items():
                existing_map[key] = val
        except Exception:
            pass

    candidates = []
    for item in ctx.items:
        key = f"{item['owner']['login']}/{item['name']}"
        existing = existing_map.get(key)
        # GC-6: 统一参数语义 — force_llm 对应 needs_llm 的 force_refresh
        if IncrementalEngine.needs_llm(key, existing, ctx.ai_db, force_refresh=force_llm, retry_failed=retry_failed, llm_interval_days=llm_interval):
            candidates.append(item)
    from config import LLM_CONFIG
    readme_max_candidates = LLM_CONFIG.get("enrich_readme_max_candidates", 50)
    log(f"获取 README 摘要用于 AI 分析... (共 {len(candidates)} 个候选项目，最多处理 {readme_max_candidates} 个)", "STEP")
    for item in candidates[:readme_max_candidates]:
        try:
            readme = ctx.gh.get_readme(item["owner"]["login"], item["name"], max_length=1500)
            if readme:
                item["readme_excerpt"] = readme
        except Exception as e:
            log(f"README 获取失败 {item.get('full_name', '?')}: {e}", "WARN")
    log("README 摘要获取完成", "OK")


def classify_stage(ctx: PipelineContext) -> None:
    # 刷新规则缓存，确保每次运行都加载最新的自动规则和 watchlist 规则
    from rule_classifier import RuleClassifier
    RuleClassifier.refresh_cache()

    if ctx.is_first_run and ctx.args.subscribe_releases:
        log("已标记所有仓库订阅 Release", "OK")

    from engine import EngineConfig, should_auto_refresh
    force_refresh = should_auto_refresh(
        ctx.args.force_refresh,
        ctx.db.meta_get("last_full_refresh_at", ""),
        ctx.args.auto_refresh_days,
    )
    if force_refresh and not ctx.args.force_refresh:
        log(f"自动全量刷新：距离上次已超过 {ctx.args.auto_refresh_days} 天", "STEP")

    ctx.engine = IncrementalEngine(ctx.db, ctx.rule, ctx.llm, ctx.ai_db)
    ctx.stats = ctx.engine.process(EngineConfig(
        items=ctx.items,
        incremental=ctx.args.incremental,
        force_refresh=force_refresh,
        use_llm=bool(ctx.llm),
        retry_failed=ctx.args.retry_failed,
        subscribe_all_releases=ctx.args.subscribe_releases,
        llm_interval_days=ctx.args.llm_interval_days
    ))

    ctx.did_full_refresh = force_refresh
    ctx.new_keys = ctx.engine.new_keys
    ctx.star_changes = ctx.engine.star_changes
    ctx.classification_changes = ctx.engine.classification_changes

    if ctx.llm and ctx.ai_db:
        llm_results = getattr(ctx.engine, 'llm_results', {})
        for key, result in llm_results.items():
            if result:
                ctx.ai_db.update_from_llm_result(key, result, status="success")
