#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline 阶段共享工具函数"""

from collections import Counter
from datetime import datetime, timezone, timedelta


def build_summary(ctx) -> str:
    """构建运行摘要文本"""
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
    return "\n".join(lines)


def build_weekly_digest_text(ctx) -> str:
    """构建周报纯文本摘要，用于通知"""
    lines = []
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()

    new_items = [r for r in ctx.db.values() if r.first_seen >= week_ago]
    if new_items:
        lines.append(f"📦 本周新增项目: {len(new_items)} 个")
        for r in new_items[:5]:
            lines.append(f"  • {r.full_name} | {r.ecology} | {r.platform} / {r.type}")
        if len(new_items) > 5:
            lines.append(f"  ... 还有 {len(new_items) - 5} 个")

    if ctx.release_updates:
        lines.append(f"\n🚀 本周新 Release: {len(ctx.release_updates)} 个")
        for u in ctx.release_updates[:5]:
            digest = u.get("ai_digest", "")
            line = f"  • {u['full_name']}: {u['new_tag']}"
            if digest:
                line += f" | {digest}"
            lines.append(line)
        if len(ctx.release_updates) > 5:
            lines.append(f"  ... 还有 {len(ctx.release_updates) - 5} 个")

    return "\n".join(lines) if lines else ""
