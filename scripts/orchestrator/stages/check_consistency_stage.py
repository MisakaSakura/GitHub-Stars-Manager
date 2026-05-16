#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check Consistency 阶段：一致性自检 + 自动修正"""

import os

from orchestrator.context import PipelineContext
from consistency_checker import ConsistencyChecker
from utils import log


def check_consistency_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run or not ctx.db:
        return
    checker = ConsistencyChecker(ctx.db)
    issues = checker.check()

    # 自动修正非 manual_override 的项目
    auto_fixed = _auto_fix_issues(ctx, issues)
    if auto_fixed:
        log(f"自动修正 {len(auto_fixed)} 处一致性异常", "OK")
        for item_name, changes in auto_fixed:
            log(f"  {item_name}: {changes}")
        ctx.db.save()

    md = checker.generate_report()
    out_path = os.path.join(ctx.args.output, "consistency_report.md")
    try:
        os.makedirs(ctx.args.output, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        log(f"一致性报告已生成: {out_path}", "OK")
    except Exception as e:
        log(f"一致性报告写入失败: {e}", "WARN")


def _auto_fix_issues(ctx: PipelineContext, issues: list) -> list[tuple[str, str]]:
    """自动修正一致性异常，返回 [(项目名, 变更描述), ...]"""
    from feedback_loop import FeedbackLoop
    from datetime import datetime, timezone

    auto_fixed: list[tuple[str, str]] = []
    feedback_path = os.path.join(os.path.dirname(ctx.args.db), "feedback.json")
    fb = FeedbackLoop(feedback_path)

    for issue in issues:
        item = ctx.db.get(issue.full_name)
        if not item:
            continue
        # 跳过手动保护的项目
        if getattr(item, "manual_override", False):
            continue

        original = {
            "platform": getattr(item, "platform", ""),
            "type": getattr(item, "type", ""),
            "ecology": getattr(item, "ecology", ""),
            "ecology_role": getattr(item, "ecology_role", ""),
        }
        corrected = dict(original)
        changed_fields: list[str] = []

        if issue.issue_type == "platform_outlier" and issue.expected:
            expected_platform = issue.expected.get("platform")
            if expected_platform and original["platform"] != expected_platform:
                item.platform = expected_platform
                corrected["platform"] = expected_platform
                changed_fields.append(f"platform: {original['platform']} → {expected_platform}")

        elif issue.issue_type == "type_outlier" and issue.expected:
            expected_type = issue.expected.get("type")
            if expected_type and original["type"] != expected_type:
                item.type = expected_type
                corrected["type"] = expected_type
                changed_fields.append(f"type: {original['type']} → {expected_type}")

        elif issue.issue_type == "isolated_ecology":
            if original["ecology"] not in ("独立项目 / Standalone", "独立项目", ""):
                item.ecology = "独立项目 / Standalone"
                item.ecology_role = "-"
                corrected["ecology"] = "独立项目 / Standalone"
                corrected["ecology_role"] = "-"
                changed_fields.append(f"ecology: {original['ecology']} → 独立项目 / Standalone")

        if changed_fields:
            item.manual_override = True
            item.override_fields = [f.split(":")[0] for f in changed_fields]
            auto_fixed.append((issue.full_name, ", ".join(changed_fields)))
            fb.record(issue.full_name, original, corrected, source="auto_fix")

    if auto_fixed:
        fb.save()

    return auto_fixed
