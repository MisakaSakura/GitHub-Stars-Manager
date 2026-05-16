#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快捷修正命令：修改数据库中的项目分类并设置 manual_override。（P1-3: 从 classifier.py 提取）"""

import argparse
import csv
import os

from config_rules import RULES_VERSION
from database import StarsDB
from feedback_loop import FeedbackLoop


class CorrectCommand:
    """快捷修正命令：修改数据库中的项目分类并设置 manual_override。"""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.db_path = args.db
        self.db = StarsDB(self.db_path)
        self.feedback_path = os.path.join(os.path.dirname(self.db_path), "feedback.json")
        self.fb = FeedbackLoop(self.feedback_path)
        self.changed = 0

    def run(self) -> int:
        if self.args.correct:
            self._correct_single()
        if self.args.correct_batch:
            self._correct_batch()
        return self._save()

    def _correct_single(self) -> None:
        if self._correct_one(
            self.args.correct,
            self.args.correct_ecology,
            self.args.correct_ecology_role,
            self.args.correct_platform,
            self.args.correct_type,
        ):
            self.changed += 1

    def _correct_batch(self) -> None:
        with open(self.args.correct_batch, "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) < 2 or row[0].startswith("#"):
                    continue
                full_name = row[0].strip()
                ecology = row[1].strip() if len(row) > 1 and row[1].strip() else None
                ecology_role = row[2].strip() if len(row) > 2 and row[2].strip() else None
                platform = row[3].strip() if len(row) > 3 and row[3].strip() else None
                type_ = row[4].strip() if len(row) > 4 and row[4].strip() else None
                if self._correct_one(full_name, ecology, ecology_role, platform, type_):
                    self.changed += 1

    def _correct_one(self, full_name: str, ecology: str | None, ecology_role: str | None,
                     platform: str | None, type_: str | None) -> bool:
        item = self.db.get(full_name)
        if not item:
            print(f"  [跳过] {full_name} 不在数据库中")
            return False

        original = {
            "platform": item.platform,
            "type": item.type,
            "ecology": item.ecology,
            "ecology_role": item.ecology_role,
        }

        updated = False
        if ecology is not None:
            item.ecology = ecology
            updated = True
        if ecology_role is not None:
            item.ecology_role = ecology_role
            updated = True
        if platform is not None:
            item.platform = platform
            updated = True
        if type_ is not None:
            item.type = type_
            updated = True

        if not updated:
            print(f"  [跳过] {full_name} 未提供任何修正字段")
            return False

        item.manual_override = True
        item.override_fields = [f for f, v in {
            "platform": platform, "type": type_,
            "ecology": ecology, "ecology_role": ecology_role,
        }.items() if v is not None]
        item.override_rules_version = RULES_VERSION

        corrected = {
            "platform": item.platform,
            "type": item.type,
            "ecology": item.ecology,
            "ecology_role": item.ecology_role,
        }
        item_features = {
            "name": item.name,
            "description": item.description,
            "topics": list(item.topics) if item.topics else [],
            "language": item.language,
        }
        self.fb.record(full_name, original, corrected, source="cli", item_features=item_features)
        self.db.set(full_name, item)
        print(f"  [修正] {full_name}: " + ", ".join(
            f"{k}: {original[k]} → {v}" for k, v in corrected.items() if original[k] != v
        ))
        return True

    def _save(self) -> int:
        if self.changed > 0:
            self.db.save()
            self.fb.save()
            learned = self.fb.generate_learned_overrides(min_count=2)
            if learned:
                self.fb.write_learned_rules_file(
                    os.path.join(os.path.dirname(self.db_path), "learned_rules.json"),
                    learned
                )
                print(f"[反馈] 已生成 learned_rules.json（{len(learned)} 条规则）")
            print(f"\n[OK] 共修正 {self.changed} 个项目，数据库已保存")
            return 0
        print("\n[WARN] 没有任何项目被修正")
        return 1


def _do_correct(args: argparse.Namespace) -> int:
    return CorrectCommand(args).run()
