#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auth 阶段：GitHub API 认证 + 规则分类器初始化"""

from orchestrator.context import PipelineContext
from github_api import GitHubAPI, GitHubAuthError, GitHubRateLimitError
from rule_classifier import RuleClassifier


class PipelineAuthError(Exception):
    """Pipeline 认证/限制异常，由上层统一处理"""
    pass


def auth_stage(ctx: PipelineContext) -> None:
    try:
        ctx.gh = GitHubAPI(ctx.args.token)
    except GitHubAuthError as e:
        raise PipelineAuthError(f"GitHub 认证失败: {e}") from e
    except GitHubRateLimitError as e:
        raise PipelineAuthError(f"GitHub API 限制: {e}") from e
    ctx.rule = RuleClassifier()
