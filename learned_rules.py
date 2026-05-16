#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动生成的规则补丁 —— 由 feedback_loop.py 根据用户反馈自动维护

生成时间: {}
数据来源: data/feedback.json
更新触发: 每次 --correct 修正或 scan_manual_overrides 检测到新差异时

注意：此文件为机器生成，不建议手动编辑。需要调整时，
      直接在 stars_db.json 中修正分类并设置 manual_override=true，
LEARNED_OVERRIDES = {
    "negative": {},
    "positive": {}
}
"""

LEARNED_OVERRIDES = {}
