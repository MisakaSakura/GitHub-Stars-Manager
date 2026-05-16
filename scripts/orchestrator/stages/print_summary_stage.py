#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print Summary 阶段：打印运行摘要"""

from collections import Counter

from orchestrator.context import PipelineContext
from utils import log


def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        ascii_msg = msg.encode("ascii", "replace").decode("ascii")
        print(ascii_msg, flush=True)


def print_summary_stage(ctx: PipelineContext) -> None:
    lines = [
        "GitHub Stars 分类完成",
        "=" * 40,
    ]
    if ctx.is_first_run:
        lines.append("🆕 首次运行模式")
        lines.append("")
    stats = ctx.stats or {}
    lines.extend([
        f"数据库总计: {len(ctx.db)} 个项目",
        f"新增项目: {stats.get('new', 0)}",
        f"重新分类: {stats.get('updated', 0)}",
        f"元数据更新: {stats.get('skipped', 0)}",
        f"手动保护: {stats.get('protected', 0)}",
        f"LLM 分析: {stats.get('llm_enhanced', 0)}",
        f"错误: {stats.get('error', 0)}",
        "",
        "生态分布 Top 5:",
    ])
    eco_stats = Counter([r.ecology for r in ctx.db.values()])
    for eco, count in eco_stats.most_common(5):
        lines.append(f"  {eco}: {count}")

    protected = sum(1 for r in ctx.db.values() if r.manual_override)
    imported = sum(1 for r in ctx.db.values() if r.imported)
    if protected:
        lines.append(f"\n🔒 手动保护项目: {protected} 个")
    if imported:
        lines.append(f"📥 导入项目: {imported} 个（已自动保护）")

    lines.append("\n报告已生成，请查看 GitHub Pages")

    _safe_print("\n" + "=" * 60)
    _safe_print("\n".join(lines))
    _safe_print("=" * 60)

    if ctx.is_first_run and not getattr(ctx.args, 'import_json', None) and not getattr(ctx.args, 'import_csv', None):
        _safe_print("\n💡 首次运行提示:")
        _safe_print('   1. 检查生成的报告，对不满意的项目修改 data/stars_db.json')
        _safe_print('   2. 给满意的项目添加 "manual_override": true 避免被覆盖')
        _safe_print("   3. 日常使用 --mode incremental 只处理新项目")
        _safe_print("   4. 如需重新分类所有项目，使用 --mode deep 或 --mode full")
