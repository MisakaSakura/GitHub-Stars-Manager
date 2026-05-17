#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discover Ecologies 阶段：生态自动发现 + 备选清单状态机"""

import json
import os

from orchestrator.context import PipelineContext
from ecology_discovery import EcologyDiscovery
from ecology_candidates import EcologyCandidatePool
from config_rules import ECOLOGY_RULES
from utils import log


# 自动生态规则持久化路径（data 分支）
_AUTO_ECOLOGIES_FILENAME = "auto_ecologies.json"


def _get_auto_ecologies_path(ctx: PipelineContext) -> str:
    return os.path.join(os.path.dirname(ctx.args.db), _AUTO_ECOLOGIES_FILENAME)


def _load_auto_ecologies(ctx: PipelineContext) -> dict:
    """加载已保存的自动生态规则（trusted 状态）"""
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


def _sync_trusted_to_auto_ecologies(ctx: PipelineContext, pool: EcologyCandidatePool) -> None:
    """将 trusted 状态的候选同步到 auto_ecologies.json（向后兼容）"""
    trusted = pool.get_trusted_rules()
    existing = _load_auto_ecologies(ctx)
    updated = False
    for name, rules in trusted.items():
        if name not in existing:
            existing[name] = rules
            updated = True
    if updated:
        _save_auto_ecologies(ctx, existing)


def _generate_discovery_report(ctx: PipelineContext, candidates: list, summary: list) -> str:
    """生成生态发现 Markdown 报告。"""
    from ecology_discovery import EcologyDiscovery
    discovery = EcologyDiscovery(ctx.db, ECOLOGY_RULES)
    md = discovery.generate_report(candidates) if candidates else ""
    md += "\n\n## 🌱 生态候选池状态\n\n"
    md += "| 生态 | 状态 | 项目数 | 置信度 | 进度 |\n"
    md += "|------|------|--------|--------|------|\n"
    for s in summary:
        status_icon = {
            "candidate": "🔍",
            "watchlist": "👀",
            "ai_reviewed": "🤖",
            "trusted": "✅",
        }.get(s["status"], "❓")
        md += f"| {s['name']} | {status_icon} {s['status']} | {s['count']} | {s['confidence']:.0%} | {s['progress']} |\n"
    return md


def _llm_review_watchlist(ctx: PipelineContext, pool: EcologyCandidatePool) -> None:
    """对 watchlist 状态的候选进行 LLM 审查"""
    if not ctx.llm:
        return

    watchlist = [
        (name, state) for name, state in pool.candidates.items()
        if state.status == "watchlist"
    ]
    if not watchlist:
        return

    log(f"LLM 审查 {len(watchlist)} 个 watchlist 候选...", "STEP")
    system_prompt = (
        "你是一个技术生态分类专家。判断给定项目列表是否属于同一个明确的技术生态。"
        "只回复 JSON 格式: {\"is_valid\": bool, \"confidence\": 0.0-1.0, \"reason\": \"一句话理由\"}"
    )

    for name, state in watchlist:
        # 收集示例项目信息
        examples = state.suggested_patterns.get("core_projects", [])[:5]
        if not examples:
            # 从 name_patterns 推断示例
            examples = state.suggested_patterns.get("name_patterns", [])[:3]

        prompt = f"""生态候选名称: {name}
匹配特征: name_patterns={state.suggested_patterns.get('name_patterns', [])}, topic_patterns={state.suggested_patterns.get('topic_patterns', [])}
问题: 这个生态候选的边界是否清晰、稳定？是否适合作为正式生态规则？
要求: 回复 JSON {{"is_valid": bool, "confidence": 0.0-1.0, "reason": "一句话理由"}}"""

        try:
            max_tokens = ctx.llm.profile.get_max_tokens("ecology_review") if getattr(ctx.llm, "profile", None) else 128
            result = ctx.llm.summarize(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
            # 尝试解析 JSON
            import re
            json_match = re.search(r'\{[^}]+\}', result or "")
            if json_match:
                review = json.loads(json_match.group())
                approved = review.get("is_valid", False)
                conf = float(review.get("confidence", 0))
                reason = review.get("reason", "")
                pool.mark_ai_reviewed(name, approved, conf, reason)
            else:
                log(f"  [{name}] LLM 返回无法解析: {result}", "WARN")
        except Exception as e:
            log(f"  [{name}] LLM 审查失败: {e}", "WARN")


def _get_repo_slug() -> str:
    """获取当前仓库的 owner/repo，用于创建 issue。"""
    import subprocess
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo and "/" in repo:
        return repo
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        url = result.stdout.strip()
        if url and "github.com" in url:
            parts = url.replace(":", "/").split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1].replace('.git', '')}"
    except Exception:
        pass
    return ""


def _propose_blocklist_via_issue(ctx: PipelineContext, pool: EcologyCandidatePool) -> int:
    """自动创建 GitHub Issue 提议加入 blocklist。返回创建的 issue 数量。"""
    proposals = pool.get_blocklist_proposals()
    if not proposals:
        return 0

    # 需要 GitHub API 和仓库信息
    gh = getattr(ctx, "gh", None)
    if not gh:
        log("跳过 blocklist issue 创建: 无 GitHub API 实例", "WARN")
        return 0

    repo_slug = _get_repo_slug()
    if not repo_slug or "/" not in repo_slug:
        log("跳过 blocklist issue 创建: 无法获取仓库标识", "WARN")
        return 0

    owner, repo = repo_slug.split("/", 1)
    created = 0

    for prop in proposals:
        indicator = prop["indicator"]
        indicator_type = prop["indicator_type"]
        candidate_name = prop["candidate_name"]
        reason = prop["reason"]

        title = f"[生态Blocklist] 提议排除 '{indicator}' ({indicator_type})"
        body = (
            f"## 自动检测到的噪声候选\n\n"
            f"- **待排除项**: `{indicator}`\n"
            f"- **类型**: {indicator_type}\n"
            f"- **触发的候选生态**: {candidate_name}\n"
            f"- **出现次数**: {prop['appear_count']}\n"
            f"- **涉及项目数**: {prop['project_count']}\n"
            f"- **理由**: {reason}\n\n"
            f"---\n"
            f"此 Issue 由生态自动发现流程自动创建。"
            f"如确认应加入 blocklist，请编辑 `scripts/ecology_blocklist.yaml` 后关闭此 Issue。"
        )

        try:
            issue = gh.create_issue(owner, repo, title, body, labels=["生态-blocklist"])
            if issue:
                pool.record_blocklist_proposal(indicator)
                created += 1
                log(f"  Blocklist issue 已创建: {issue.get('html_url', '')}", "OK")
        except Exception as e:
            log(f"  创建 blocklist issue 失败 ({indicator}): {e}", "WARN")

    if created > 0:
        pool.save()
        log(f"Blocklist 提议: 创建 {created}/{len(proposals)} 个 issue", "OK")

    return created


def discover_ecologies_stage(ctx: PipelineContext) -> None:
    if ctx.args.dry_run or not ctx.db:
        return

    pool_path = os.path.join(os.path.dirname(ctx.args.db), "ecology_candidates.json")
    pool = EcologyCandidatePool(pool_path)

    discovery = EcologyDiscovery(ctx.db, ECOLOGY_RULES)
    candidates = discovery.discover(top_n=10)

    # 更新候选池状态
    if candidates:
        changes = pool.update_from_discovery(candidates)
        if changes:
            log(f"候选池状态变更: {len(changes)} 个", "OK")

    # LLM 审查 watchlist
    _llm_review_watchlist(ctx, pool)

    # 自动创建 blocklist issue
    _propose_blocklist_via_issue(ctx, pool)

    # 同步 trusted 到 auto_ecologies.json
    _sync_trusted_to_auto_ecologies(ctx, pool)

    # 生成报告
    summary = pool.generate_summary()
    if summary:
        md = _generate_discovery_report(ctx, candidates, summary)
        out_path = os.path.join(ctx.args.output, "ecology_discovery.md")
        try:
            os.makedirs(ctx.args.output, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md)
            log(f"生态发现报告已生成: {out_path}", "OK")
        except Exception as e:
            log(f"生态发现报告写入失败: {e}", "WARN")

    # 把候选池摘要存入 ctx 供周报使用
    ctx.ecology_candidate_summary = summary
