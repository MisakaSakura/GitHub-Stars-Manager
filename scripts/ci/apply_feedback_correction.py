#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 GitHub Issue 解析分类修正并应用到数据库。

由 process-feedback.yml workflow 调用。
环境变量:
    ISSUE_BODY: Issue 正文
    ISSUE_NUMBER: Issue 编号
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config_rules import RULES_VERSION


def parse_field(body: str, label: str) -> str:
    m = re.search(rf"{re.escape(label)}\s*\n\s*([^\n]+)", body)
    return m.group(1).strip() if m else ""


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    issue_num = os.environ.get("ISSUE_NUMBER", "")

    full_name = parse_field(body, "项目地址")
    field_type = parse_field(body, "修正字段")
    expected = parse_field(body, "建议分类（正确）")

    if not full_name or not expected:
        print("无法解析 Issue 内容，跳过")
        return 1

    # 检查数据库
    db_path = "data/stars_db.json"
    if not os.path.exists(db_path):
        print("数据库不存在")
        return 1

    with open(db_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    target = None
    for item in items:
        if item.get("full_name") == full_name:
            target = item
            break

    if not target:
        print(f"项目 {full_name} 不在数据库中")
        return 1

    original = {
        "platform": target.get("platform", ""),
        "type": target.get("type", ""),
        "ecology": target.get("ecology", ""),
        "ecology_role": target.get("ecology_role", ""),
    }

    # 应用修正（P1-55: 根据实际修改的字段动态设置 override_fields）
    updated = False
    changed_fields: list[str] = []

    if "生态归属" in field_type or "多个字段" in field_type:
        if expected and target.get("ecology") != expected:
            target["ecology"] = expected
            updated = True
            changed_fields.append("ecology")
    if "平台" in field_type or "多个字段" in field_type:
        if expected and target.get("platform") != expected:
            target["platform"] = expected
            updated = True
            changed_fields.append("platform")
    if "类型" in field_type or "多个字段" in field_type:
        if expected and target.get("type") != expected:
            target["type"] = expected
            updated = True
            changed_fields.append("type")

    if not updated:
        print("没有需要应用的修正")
        return 1

    target["manual_override"] = True
    target["override_fields"] = changed_fields  # P1-55: 动态设置
    target["override_rules_version"] = RULES_VERSION

    # 保存数据库
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # 记录反馈到 feedback.json
    fb_path = "data/feedback.json"
    fb = {"version": 1, "entries": {}, "patterns": {}}
    if os.path.exists(fb_path):
        try:
            with open(fb_path, "r", encoding="utf-8") as f:
                fb = json.load(f)
        except Exception:
            pass

    from datetime import datetime, timezone
    fb["entries"][full_name] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original": original,
        "corrected": {
            "platform": target["platform"],
            "type": target["type"],
            "ecology": target["ecology"],
            "ecology_role": target["ecology_role"],
        },
        "source": f"issue#{issue_num}",
        "rules_version": RULES_VERSION,
    }

    with open(fb_path, "w", encoding="utf-8") as f:
        json.dump(fb, f, ensure_ascii=False, indent=2)

    print(f"已修正 {full_name}: {original['ecology']} -> {target['ecology']}")

    # 写入 GITHUB_OUTPUT
    gh_out = os.environ.get("GITHUB_OUTPUT", "")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"full_name={full_name}\n")
            f.write(f"original={original.get('ecology', '')}\n")
            f.write(f"corrected={target['ecology']}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
