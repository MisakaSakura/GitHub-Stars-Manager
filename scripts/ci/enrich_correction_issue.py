#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在分类修正 Issue 下自动评论当前分类信息。

由 process-feedback.yml workflow 在 apply_feedback_correction.py 之前调用。
环境变量:
    ISSUE_BODY: Issue 正文
    ISSUE_NUMBER: Issue 编号
    GITHUB_TOKEN: GitHub API Token
"""

import json
import os
import re
import subprocess
import sys


def parse_full_name(body: str) -> str:
    """从 Issue body 解析项目地址。"""
    # 新版模板: 项目地址字段
    m = re.search(r"项目地址\s*\n\s*(.+?)(?=\n\s*\n|\n[A-Z]|$)", body, re.DOTALL)
    if m:
        return m.group(1).strip().splitlines()[0].strip()
    # 旧版兼容: **项目地址**: xxx
    m = re.search(r"\*\*项目地址\*\*:\s*(.+?)(?=\n|$)", body)
    if m:
        return m.group(1).strip()
    return ""


def get_current_classification(full_name: str, db_path: str) -> dict | None:
    """从数据库读取项目当前分类。"""
    if not os.path.exists(db_path):
        return None
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    for item in data:
        if item.get("full_name") == full_name:
            return {
                "platform": item.get("platform", "-"),
                "type": item.get("type", "-"),
                "ecology": item.get("ecology", "-"),
                "ecology_role": item.get("ecology_role", "-"),
                "stars": item.get("stars", 0),
                "description": item.get("description", "-"),
                "topics": item.get("topics", []),
                "manual_override": item.get("manual_override", False),
            }
    return None


def post_comment(issue_number: str, body: str) -> bool:
    """使用 gh CLI 在 issue 下发表评论。"""
    try:
        subprocess.run(
            ["gh", "issue", "comment", issue_number, "--body", body],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    issue_num = os.environ.get("ISSUE_NUMBER", "")

    full_name = parse_full_name(body)
    if not full_name:
        print("无法从 Issue 解析项目地址，跳过补全")
        return 0  # 不阻断后续流程

    db_path = "data/stars_db.json"
    current = get_current_classification(full_name, db_path)
    if not current:
        print(f"项目 {full_name} 不在数据库中，无法补全")
        return 0

    comment_body = (
        f"🤖 **当前分类信息**（供审核参考）\n\n"
        f"| 字段 | 当前值 |\n"
        f"|------|--------|\n"
        f"| 生态归属 | {current['ecology']} |\n"
        f"| 平台 | {current['platform']} |\n"
        f"| 类型 | {current['type']} |\n"
        f"| 生态角色 | {current['ecology_role']} |\n"
        f"| Stars | {current['stars']:,} |\n"
        f"\n"
        f"**描述**: {current['description'][:200]}{'...' if len(current['description']) > 200 else ''}\n"
        f"**Topics**: {', '.join(current['topics'][:10]) if current['topics'] else '-'}\n"
    )
    if current["manual_override"]:
        comment_body += "\n⚠️ **注意**: 该项目已被标记 manual_override，修正将被直接应用。"

    if post_comment(issue_num, comment_body):
        print(f"已在 issue #{issue_num} 下评论 {full_name} 的当前分类")
    else:
        print(f"评论发布失败（gh CLI 不可用或无权限），继续执行")

    return 0


if __name__ == "__main__":
    sys.exit(main())
