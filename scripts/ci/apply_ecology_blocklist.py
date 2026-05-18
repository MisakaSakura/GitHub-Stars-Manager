#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 GitHub Issue 解析生态 Blocklist 提议并应用。

由 process-ecology-blocklist.yml workflow 调用。
环境变量:
    ISSUE_BODY: Issue 正文
    ISSUE_NUMBER: Issue 编号
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def parse_candidate_name(body: str) -> str:
    """从 Issue body 解析候选生态名称。"""
    # 新版简化模板：候选生态名称
    m = re.search(r"候选生态名称\s*\n\s*(.+?)(?=\n\s*\n|\n[A-Z]|$)", body, re.DOTALL)
    if m:
        return m.group(1).strip().splitlines()[0].strip()
    # 旧版模板兼容：从 triggered_candidate 或 indicator 中提取
    m = re.search(r"触发的候选生态\s*\n\s*(.+?)(?=\n\s*\n|\n[A-Z]|$)", body, re.DOTALL)
    if m:
        line = m.group(1).strip().splitlines()[0].strip()
        # 格式: "候选名 (涉及N个项目)" → 取候选名
        return line.split("(")[0].strip()
    # 兜底：从标题中提取
    return ""


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    issue_num = os.environ.get("ISSUE_NUMBER", "")

    candidate_name = parse_candidate_name(body)
    if not candidate_name:
        print("无法从 Issue 解析候选生态名称，跳过")
        return 1

    # 构建路径
    script_dir = os.path.dirname(os.path.dirname(__file__))
    pool_path = os.path.join(script_dir, "data", "ecology_candidates.json")
    yaml_path = os.path.join(script_dir, "ecology_blocklist.yaml")

    # 候选池可能不存在（首次运行时）
    if not os.path.exists(pool_path):
        print(f"候选池不存在: {pool_path}")
        # 仍然尝试直接更新 yaml（如果用户提供了 indicator）
        print("提示: 候选池缺失，无法自动推断。建议手动编辑 ecology_blocklist.yaml。")
        return 1

    from ecology_blocklist import exclude_ecology

    result = exclude_ecology(candidate_name, pool_path, yaml_path)
    if result is None:
        print(f"排除 '{candidate_name}' 失败：候选不存在或已排除")
        return 1

    print(f"已排除 {candidate_name}: indicator={result['indicator']}, type={result['indicator_type']}")

    # 写入 GITHUB_OUTPUT
    gh_out = os.environ.get("GITHUB_OUTPUT", "")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"candidate_name={candidate_name}\n")
            f.write(f"indicator={result['indicator']}\n")
            f.write(f"indicator_type={result['indicator_type']}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
