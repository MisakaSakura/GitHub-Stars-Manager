#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classify 阶段：规则分类 + LLM 增强"""

from orchestrator.context import PipelineContext
from llm_classifier import LLMClassifier
from engine import IncrementalEngine
from utils import log


def setup_llm_stage(ctx: PipelineContext) -> None:
    if not ctx.args.llm_key:
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
    candidates = []
    for item in ctx.items:
        key = f"{item['owner']['login']}/{item['name']}"
        existing = ctx.db.get(key)
        if IncrementalEngine.needs_llm(key, existing, ctx.ai_db, force_llm, retry_failed, llm_interval):
            candidates.append(item)
    log(f"获取 README 摘要用于 AI 分析... (共 {len(candidates)} 个候选项目)", "STEP")
    for item in candidates[:50]:
        try:
            readme = ctx.gh.get_readme(item["owner"]["login"], item["name"], max_length=1500)
            if readme:
                item["readme_excerpt"] = readme
        except Exception:
            pass
    log("README 摘要获取完成", "OK")


def classify_stage(ctx: PipelineContext) -> None:
    # 刷新规则缓存，确保每次运行都加载最新的自动规则和 watchlist 规则
    from rule_classifier import RuleClassifier
    RuleClassifier.refresh_cache()

    if ctx.is_first_run and ctx.args.subscribe_releases:
        log("已标记所有仓库订阅 Release", "OK")

    force_refresh = ctx.args.force_refresh
    if not force_refresh:
        last = ctx.db.meta_get("last_full_refresh_at", "")
        if last:
            from datetime import datetime, timezone, timedelta
            try:
                last_dt = datetime.fromisoformat(last)
                interval = timedelta(days=ctx.args.auto_refresh_days)
                if datetime.now(timezone.utc) - last_dt >= interval:
                    log(f"自动全量刷新：距离上次已超过 {ctx.args.auto_refresh_days} 天", "STEP")
                    force_refresh = True
            except ValueError:
                force_refresh = True
        else:
            force_refresh = True

    ctx.engine = IncrementalEngine(ctx.db, ctx.rule, ctx.llm, ctx.ai_db)
    ctx.stats = ctx.engine.process(
        ctx.items,
        incremental=ctx.args.incremental,
        force_refresh=force_refresh,
        use_llm=bool(ctx.llm),
        retry_failed=ctx.args.retry_failed,
        subscribe_all_releases=ctx.args.subscribe_releases,
        llm_interval_days=ctx.args.llm_interval_days
    )

    ctx.did_full_refresh = force_refresh
    ctx.new_keys = ctx.engine.new_keys
    ctx.star_changes = ctx.engine.star_changes
    ctx.classification_changes = ctx.engine.classification_changes

    if ctx.llm and ctx.ai_db:
        for key, result in ctx.engine.llm_results.items():
            if result:
                ctx.ai_db.update_from_llm_result(key, result, status="success")
