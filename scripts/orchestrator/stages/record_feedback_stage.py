#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Record Feedback 阶段：反馈闭环"""

import os

from orchestrator.context import PipelineContext
from feedback_loop import FeedbackLoop
from utils import log


def record_feedback_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run or not ctx.db:
        return
    feedback_path = os.path.join(os.path.dirname(ctx.args.db), "feedback.json")
    fb = FeedbackLoop(feedback_path)
    count = fb.scan_manual_overrides(ctx.db)
    if count > 0:
        fb.save()
        log(f"反馈数据已保存: {feedback_path}", "OK")

    # 自动生成 learned rules（即使本次没有新修正，也重新生成以捕获模式变化）
    learned = fb.generate_learned_overrides(min_count=3)
    if learned:
        rules_path = os.path.join(os.path.dirname(ctx.args.db), "learned_rules.json")
        fb.write_learned_rules_file(rules_path, learned)
        log(f"已生成 learned_rules.json（{len(learned.get('negative', {}))} 条否定 + {len(learned.get('positive', {}))} 条正向）", "OK")

    # 检测 manual_override 与新规则的冲突
    conflicts = fb.detect_override_conflicts(ctx.db)
    if conflicts:
        log(f"检测到 {len(conflicts)} 个 manual_override 项目与新规则存在冲突", "WARN")
        conflict_md = fb.generate_conflict_report(conflicts)
        conflict_path = os.path.join(ctx.args.output, "override_conflicts.md")
        try:
            os.makedirs(ctx.args.output, exist_ok=True)
            with open(conflict_path, "w", encoding="utf-8") as f:
                f.write(conflict_md)
            log(f"冲突报告已生成: {conflict_path}", "OK")
        except Exception as e:
            log(f"冲突报告写入失败: {e}", "WARN")

    md = fb.generate_report()
    out_path = os.path.join(ctx.args.output, "feedback_report.md")
    try:
        os.makedirs(ctx.args.output, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        log(f"反馈报告已生成: {out_path}", "OK")
    except Exception as e:
        log(f"反馈报告写入失败: {e}", "WARN")
