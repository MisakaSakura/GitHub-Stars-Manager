#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生态排除快捷命令：一键将候选生态加入 blocklist。（Phase 6）"""

import argparse
import os

from ecology_blocklist import exclude_ecology
from ecology_candidates import EcologyCandidatePool


class BlocklistCommand:
    """生态排除命令：根据候选名自动推断并更新 blocklist。"""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.db_dir = os.path.dirname(args.db)
        self.pool_path = os.path.join(self.db_dir, "ecology_candidates.json")
        self.yaml_path = os.path.join(
            os.path.dirname(__file__), "ecology_blocklist.yaml"
        )

    def run(self) -> int:
        candidate_name = self.args.exclude_ecology
        result = exclude_ecology(candidate_name, self.pool_path, self.yaml_path)
        if result is None:
            # 检查候选是否根本不存在
            pool = EcologyCandidatePool(self.pool_path)
            if candidate_name not in pool.candidates:
                print(f"  [跳过] '{candidate_name}' 不在候选池中")
                return 1
            print(f"  [跳过] '{candidate_name}' 已被排除或 indicator 已存在")
            return 1

        print(f"  [排除] {result['candidate_name']}")
        print(f"         indicator: {result['indicator']} ({result['indicator_type']})")
        print(f"         涉及项目: {result['appear_count']} 次出现")
        if result["example_projects"]:
            print(f"         示例项目: {', '.join(result['example_projects'][:5])}")
        print(f"\n[OK] blocklist 已更新: {self.yaml_path}")
        print("     请记得提交 ecology_blocklist.yaml 到仓库以生效。")
        return 0


def _do_exclude(args: argparse.Namespace) -> int:
    return BlocklistCommand(args).run()
