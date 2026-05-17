#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 feedback.json 重新生成 learned_rules.json（P1-56: 从 workflow 内联脚本提取）。"""

import os
import sys

sys.path.insert(0, "scripts")

from feedback_loop import FeedbackLoop


def main() -> int:
    fb_path = "data/feedback.json"
    lr_path = "data/learned_rules.json"

    if not os.path.exists(fb_path):
        print("feedback.json 不存在，跳过规则生成")
        return 0

    fb = FeedbackLoop(fb_path)
    learned = fb.generate_learned_overrides(min_count=2)
    if learned and (learned.get("negative") or learned.get("positive")):
        fb.write_learned_rules_file(lr_path, learned)
        print(f"已生成 learned_rules.json（{len(learned)} 条规则）")
    else:
        print("反馈数量不足，未生成规则补丁")

    return 0


if __name__ == "__main__":
    sys.exit(main())
