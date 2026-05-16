#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reports 阶段：生成 HTML/CSV/JSON 报告和 Release 日志"""

import os

from orchestrator.context import PipelineContext
from report import ReportGenerator
from utils import log


def _generate_ai_summary(ctx: PipelineContext) -> str:
    """综合生成本周动态总结。LLM 可用时用 AI 生成，否则用规则生成简洁文本。"""
    new_items_count = len(ctx.new_keys)
    star_changes = ctx.star_changes
    release_updates = ctx.release_updates or []
    classification_changes = ctx.classification_changes
    fork_updates = ctx.fork_updates or []

    has_any = (new_items_count or star_changes or release_updates or
               classification_changes or fork_updates)
    if not has_any:
        return ""

    data_parts: list[str] = []
    if new_items_count:
        data_parts.append(f"新收录 {new_items_count} 个项目")
    if star_changes:
        top_names = [key for key, _ in sorted(star_changes.items(), key=lambda x: x[1], reverse=True)[:3]]
        data_parts.append(f"{len(star_changes)} 个项目 stars 增长显著（{', '.join(top_names)}）")
    if release_updates:
        release_names = [f"{ru['full_name']} {ru['old_tag']}→{ru['new_tag']}" for ru in release_updates[:3]]
        data_parts.append(f"{len(release_updates)} 个新 Release（{'; '.join(release_names)}）")
    if classification_changes:
        data_parts.append(f"{len(classification_changes)} 个项目分类被重新调整")
    if fork_updates:
        data_parts.append(f"{len(fork_updates)} 个 Fork 仓库上游有更新")

    if not ctx.llm:
        return "本周动态：" + "；".join(data_parts) + "。"

    llm_parts: list[str] = []
    if star_changes:
        top = sorted(star_changes.items(), key=lambda x: x[1], reverse=True)[:5]
        llm_parts.append("本周 Stars 增长最多的项目：")
        for key, delta in top:
            llm_parts.append(f"- {key}: +{delta} stars")
    if release_updates:
        llm_parts.append("\n本周新 Release：")
        for ru in release_updates:
            ai_digest = ru.get("ai_digest", "")
            line = f"- {ru['full_name']} {ru['old_tag']} → {ru['new_tag']}"
            if ai_digest:
                line += f"（{ai_digest}）"
            llm_parts.append(line)
    if classification_changes:
        llm_parts.append("\n本周分类调整：")
        for key, changes in list(classification_changes.items())[:5]:
            change_str = ", ".join([f"{k} {v['from']}→{v['to']}" for k, v in changes.items()])
            llm_parts.append(f"- {key}: {change_str}")

    from prompts import PromptLoader
    from config import LLM_SYSTEM_PROMPT
    prompt = PromptLoader.render("weekly_digest", data="\n".join(llm_parts))
    try:
        summary = ctx.llm.summarize(prompt, system_prompt=LLM_SYSTEM_PROMPT, max_tokens=256)
        return summary or "本周动态：" + "；".join(data_parts) + "。"
    except Exception as e:
        log(f"AI 动态总结生成失败: {e}", "WARN")
        return "本周动态：" + "；".join(data_parts) + "。"


def reports_stage(ctx: PipelineContext) -> None:
    if ctx.args.no_report or ctx.args.dry_run:
        if ctx.args.dry_run:
            log("试运行模式：报告未生成", "WARN")
        return

    report = ReportGenerator(ctx.db, ai_db=ctx.ai_db)
    new_items = [ctx.db.get(k).to_dict() for k in ctx.new_keys if ctx.db.get(k)]
    ai_summary = _generate_ai_summary(ctx)
    weekly_data = {
        "new_items": new_items,
        "release_updates": ctx.release_updates,
        "star_changes": ctx.star_changes,
        "fork_updates": ctx.fork_updates,
        "classification_changes": ctx.classification_changes,
        "ai_summary": ai_summary,
    } if (new_items or ctx.release_updates or ctx.star_changes or
          ctx.fork_updates or ctx.classification_changes or ai_summary) else None

    report.generate_html(ctx.args.output, weekly_data=weekly_data)
    report.generate_csv(ctx.args.output)
    report.generate_json(ctx.args.output)
    history_path = os.path.join(os.path.dirname(ctx.args.db), "releases_history.json")
    report.generate_releases_log(ctx.args.output, history_path=history_path)
