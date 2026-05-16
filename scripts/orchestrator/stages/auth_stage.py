#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auth 阶段：GitHub API 认证 + 规则分类器初始化"""

import sys

from orchestrator.context import PipelineContext
from github_api import GitHubAPI, GitHubAuthError, GitHubRateLimitError
from rule_classifier import RuleClassifier
from utils import log


def auth_stage(ctx: PipelineContext) -> None:
    try:
        ctx.gh = GitHubAPI(ctx.args.token)
    except GitHubAuthError as e:
        log(f"GitHub 认证失败: {e}", "ERROR")
        sys.exit(1)
    except GitHubRateLimitError as e:
        log(f"GitHub API 限制: {e}", "ERROR")
        sys.exit(1)
    ctx.rule = RuleClassifier()
