#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Stars 自动分类工具 v4 — CLI 入口
======================================
支持：规则分类、LLM 智能增强、增量更新、手动修正保护、
      Notion 导出、多通道通知、HTML 报告、Release/Fork 追踪

用法：
  模式运行：python classifier.py --token ghp_xxx --user yourname --mode incremental
  深度整理：python classifier.py --token ghp_xxx --user yourname --mode deep --llm-key sk-xxx
  全量刷新：python classifier.py --token ghp_xxx --user yourname --mode full --llm-key sk-xxx
  启用通知：python classifier.py --token ghp_xxx --user yourname --mode incremental --notify
"""

import argparse
import os
import sys

import config_llm
from correct_command import _do_correct
from orchestrator import Pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GitHub Stars 自动分类工具 v4",
        epilog="""
首次运行说明:
  1. 首次运行（数据库不存在）会自动创建新数据库，对所有项目执行全新分类
  2. 如果你有已有分类想保留，使用 --import-json 或 --import-csv 导入
  3. 导入的项目会自动标记 manual_override，不会被后续自动分类覆盖
  4. 首次运行后，建议检查分类结果，对不满意的项目手动修正并标记保护

示例:
  # 首次运行（全新分类）
  python classifier.py --token ghp_xxx --user yourname

  # 首次运行 + 导入已有分类（保留旧标签）
  python classifier.py --token ghp_xxx --user yourname --import-json ./old_tags.json

  # 首次运行 + LLM 增强
  python classifier.py --token ghp_xxx --user yourname --llm-key sk-xxx
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 基础参数
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--user", required=True, help="GitHub 用户名")
    parser.add_argument("--db", default="./data/stars_db.json", help="数据库路径")
    parser.add_argument("--storage", default="json", choices=["json", "sqlite"],
                        help="存储后端: json (默认) / sqlite (实验性)")
    parser.add_argument("--output", default="./docs", help="输出目录")

    # 运行模式
    parser.add_argument("--mode", default="incremental",
                        choices=["incremental", "deep", "full", "custom"],
                        help="""运行模式：
  incremental: 增量更新（日常用）— 只处理新项目，检查 Release
  deep: 深度整理 — 增量 + 强制刷新规则分类 + Release + Fork
  full: 全量刷新 — 非增量拉取 + 强制刷新 + Release + Fork + 订阅标记
  custom: 自定义 — 完全由其他开关控制，适合高级用户
                        """)
    parser.add_argument("--incremental", action="store_true",
                        help="增量模式：只处理新 star 的项目（--mode custom 时可用）")
    parser.add_argument("--force-refresh", action="store_true",
                        help="强制刷新：重新分类所有项目（--mode custom 时可用）")
    parser.add_argument("--auto-refresh-days", type=int, default=90,
                        help="自动全量刷新间隔天数（默认 90，增量模式下到期自动升级）")

    # 首次运行/导入
    parser.add_argument("--import-json", metavar="PATH", help="从 JSON 文件导入已有分类")
    parser.add_argument("--import-csv", metavar="PATH", help="从 CSV 文件导入已有分类")
    parser.add_argument("--no-auto-classify", action="store_true",
                        help="导入已有分类后，不对新项目自动分类")

    # GitHub Lists 处理策略
    parser.add_argument("--lists-strategy", default="ignore",
                        choices=["auto", "prompt", "migrate", "replace", "ignore"],
                        help="GitHub Lists 处理策略（默认 ignore，避免误操作）")

    # LLM
    parser.add_argument("--llm-key", help="LLM API Key（启用智能分类增强）")
    parser.add_argument("--llm-preset",
                        help="LLM 预设（同时设置 provider+base+model）：openai/moonshot/deepseek/openrouter/xiaomimimo")
    parser.add_argument("--llm-provider", default=None,
                        help="LLM 提供商: openai/moonshot/deepseek/openrouter（可被 preset 覆盖）")
    parser.add_argument("--llm-model", help="LLM 模型名称（可被 preset 覆盖）")
    parser.add_argument("--llm-base", help="LLM API Base URL（可被 preset 覆盖）")
    parser.add_argument("--llm-interval-days", type=int, default=30,
                        help="LLM 分类最小间隔天数（默认 30，节省 Token）")
    parser.add_argument("--force-llm", action="store_true",
                        help="无视间隔强制启用 LLM 分类")

    # Notion
    parser.add_argument("--notion-key", help="Notion API Key")
    parser.add_argument("--notion-db", help="Notion Database ID")
    parser.add_argument("--notion-clear", action="store_true",
                        help="导出前清空 Notion 数据库")

    # Release / Fork 追踪
    parser.add_argument("--check-releases", action="store_true",
                        help="检查已订阅仓库是否有新 Release")
    parser.add_argument("--check-all-releases", action="store_true",
                        help="检查所有仓库的新 Release（生成周报，无需 subscribe_releases）")
    parser.add_argument("--check-forks", action="store_true",
                        help="检查 Fork 仓库的上游是否有更新")
    parser.add_argument("--subscribe-releases", action="store_true",
                        help="将所有仓库标记为订阅 Release（首次运行时有效）")
    parser.add_argument("--llm-release-digest", action="store_true",
                        help="对 Release Notes 生成 AI 摘要（需要配置 LLM）")

    # 通知
    parser.add_argument("--notify", action="store_true", help="启用通知")
    parser.add_argument("--notify-channels", default="email",
                        help="通知通道，逗号分隔: email,telegram,wecom,qq")

    # 其他
    parser.add_argument("--no-report", action="store_true", help="不生成 HTML 报告")
    parser.add_argument("--dry-run", action="store_true",
                        help="试运行：显示将要执行的操作但不保存数据库和报告")
    parser.add_argument("--retry-failed", action="store_true",
                        help="重新对之前 AI 分析失败的项目进行分类")

    # 快捷修正（双向反馈入口）
    correct_group = parser.add_argument_group("快捷修正（不运行完整流水线）")
    correct_group.add_argument("--correct", metavar="OWNER/REPO",
                               help="修正指定项目的分类，格式: owner/repo")
    correct_group.add_argument("--correct-ecology", help="设置生态归属")
    correct_group.add_argument("--correct-ecology-role", help="设置生态角色")
    correct_group.add_argument("--correct-platform", help="设置平台")
    correct_group.add_argument("--correct-type", help="设置类型")
    correct_group.add_argument("--correct-batch", metavar="PATH",
                               help="批量修正文件，格式: full_name,ecology,ecology_role,platform,type（CSV）")

    return parser.parse_args(argv)


def _parse_env_presets() -> dict:
    """从 LLM_PRESETS 环境变量解析动态预设。
    格式：name|provider|base|model[;name|provider|base|model...]
    示例：mycompany|openai|https://llm.mycompany.com/v1|company-v1
    """
    env = os.environ.get("LLM_PRESETS", "")
    if not env:
        return {}
    presets = {}
    for entry in env.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("|")
        if len(parts) == 4:
            name, provider, base, model = (p.strip() for p in parts)
            presets[name] = {"provider": provider, "api_base": base, "model": model}
    return presets


def _apply_preset(args: argparse.Namespace) -> argparse.Namespace:
    """根据 --llm-preset 自动填充 provider / base / model"""

    # 三层预设合并：环境变量 > 代码自定义 > 内置（同名后者覆盖前者）
    env_presets = _parse_env_presets()
    all_presets = {**config_llm.PROVIDER_PRESETS, **config_llm.CUSTOM_PRESETS, **env_presets}

    preset_name = args.llm_preset or os.environ.get("LLM_PRESET", "")
    if not preset_name:
        return args

    preset = all_presets.get(preset_name)
    if not preset:
        print(f"[警告] 未知 LLM preset: {preset_name}，可用: {', '.join(all_presets.keys())}")
        return args

    # preset 填充默认值；CLI 显式参数优先级高于 preset
    if not args.llm_provider:
        args.llm_provider = preset["provider"]
    if not args.llm_base:
        args.llm_base = preset["api_base"]
    if not args.llm_model:
        args.llm_model = preset["model"]
    print(f"[Preset] {preset_name} → provider={args.llm_provider}, base={args.llm_base}, model={args.llm_model}")
    return args


def _ensure_defaults(args: argparse.Namespace) -> argparse.Namespace:
    """在 preset 应用后，为未设置的参数补上默认值"""
    if not args.llm_provider:
        args.llm_provider = "openai"
    return args


def _apply_mode(args: argparse.Namespace) -> argparse.Namespace:
    """根据 mode 自动设置对应的开关组合"""
    if args.mode == "custom":
        return args

    mode_configs = {
        "incremental": {
            "incremental": True,
            "check_all_releases": True,
        },
        "deep": {
            "incremental": True,
            "force_refresh": True,
            "check_all_releases": True,
            "check_forks": True,
        },
        "full": {
            "force_refresh": True,
            "check_all_releases": True,
            "check_forks": True,
            "subscribe_releases": True,
        },
    }

    config = mode_configs.get(args.mode, {})
    for key, value in config.items():
        setattr(args, key, value)

    # 全量模式：如果配置了 llm_key，自动 force_llm（彻底梳理）
    if args.mode == "full" and args.llm_key and not args.force_llm:
        args.force_llm = True
        print("[自动启用] --force-llm（全量模式默认全库 LLM 分析）")

    # 日志输出模式说明
    mode_desc = {
        "incremental": "增量更新（日常）",
        "deep": "深度整理（规则梳理 + LLM 增强）",
        "full": "全量刷新（全库重新分类）",
    }
    print(f"[模式] {args.mode}: {mode_desc.get(args.mode, '')}")
    enabled = [k for k, v in config.items() if v]
    if enabled:
        print(f"[自动启用] {', '.join(enabled)}")

    return args


def main() -> None:
    args = parse_args()

    # 快捷修正模式：不运行完整流水线
    if args.correct or args.correct_batch:
        sys.exit(_do_correct(args))

    args = _apply_preset(args)
    args = _ensure_defaults(args)
    args = _apply_mode(args)
    pipeline = Pipeline(args)
    try:
        pipeline.run()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
