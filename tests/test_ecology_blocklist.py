#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生态 Blocklist 远程自动提交测试"""

import os
import sys
import unittest
import tempfile
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ecology_candidates import EcologyCandidatePool, EcologyCandidateState


class MockGitHubAPI:
    """模拟 GitHubAPI.create_issue"""
    def __init__(self):
        self.issues_created = []

    def create_issue(self, owner, repo, title, body, labels=None):
        self.issues_created.append({
            "owner": owner, "repo": repo, "title": title,
            "body": body, "labels": labels,
        })
        return {"number": len(self.issues_created), "html_url": f"https://github.com/{owner}/{repo}/issues/{len(self.issues_created)}"}


class TestBlocklistProposals(unittest.TestCase):
    """Blocklist 自动提议测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pool_path = os.path.join(self.tmpdir, "ecology_candidates.json")
        self.pool = EcologyCandidatePool(self.pool_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _add_candidate(self, name: str, status: str, appear_count: int, topics: list[str] = None):
        """Helper: 添加一个候选到池中"""
        now = datetime.now(timezone.utc).isoformat()
        self.pool.candidates[name] = EcologyCandidateState(
            status=status,
            first_seen=now,
            last_seen=now,
            appear_count=appear_count,
            consecutive_runs=appear_count,
            missed_runs=0,
            confidence_history=[0.6],
            project_count_history=[5],
            suggested_patterns={
                "topic_patterns": topics or [name.lower()],
                "name_patterns": [],
            },
        )

    def test_noise_platform_keyword_proposed(self):
        """平台关键词作为生态候选时应被提议 blocklist"""
        self._add_candidate("Android", "candidate", 5, topics=["android"])
        proposals = self.pool.get_blocklist_proposals()
        self.assertTrue(any(p["indicator"].lower() == "android" for p in proposals))

    def test_noise_type_keyword_proposed(self):
        """类型关键词作为生态候选时应被提议 blocklist"""
        self._add_candidate("CLI", "watchlist", 4, topics=["cli"])
        proposals = self.pool.get_blocklist_proposals()
        self.assertTrue(any(p["indicator"].lower() == "cli" for p in proposals))

    def test_below_threshold_not_proposed(self):
        """出现次数 < 3 时不应提议"""
        self._add_candidate("Android", "candidate", 2, topics=["android"])
        proposals = self.pool.get_blocklist_proposals()
        self.assertEqual(len(proposals), 0)

    def test_already_blocklisted_not_proposed(self):
        """已在手动 blocklist 中的不应重复提议"""
        self._add_candidate("android", "candidate", 5, topics=["android"])
        # 手动加入 blocklist
        self.pool._manual_blocklist.add("android")
        proposals = self.pool.get_blocklist_proposals()
        self.assertEqual(len(proposals), 0)

    def test_recently_proposed_not_duplicated(self):
        """7 天内已提议过的不应重复"""
        self._add_candidate("Android", "candidate", 5, topics=["android"])
        self.pool.record_blocklist_proposal("android")
        proposals = self.pool.get_blocklist_proposals()
        self.assertEqual(len(proposals), 0)

    def test_rejected_candidate_not_proposed(self):
        """rejected 状态的候选不应被提议"""
        self._add_candidate("Android", "rejected", 5, topics=["android"])
        proposals = self.pool.get_blocklist_proposals()
        self.assertEqual(len(proposals), 0)

    def test_record_proposal_prevents_duplicate(self):
        """record_blocklist_proposal 后 _was_recently_proposed 应返回 True"""
        self.pool.record_blocklist_proposal("test-indicator")
        self.assertTrue(self.pool._was_recently_proposed("test-indicator"))
        self.assertTrue(self.pool._was_recently_proposed("TEST-INDICATOR"))  # 大小写不敏感

    def test_proposal_data_structure(self):
        """提议列表的数据结构应包含必要字段"""
        self._add_candidate("Android", "candidate", 5, topics=["android"])
        proposals = self.pool.get_blocklist_proposals()
        self.assertEqual(len(proposals), 1)
        p = proposals[0]
        self.assertIn("indicator", p)
        self.assertIn("indicator_type", p)
        self.assertIn("candidate_name", p)
        self.assertIn("appear_count", p)
        self.assertIn("reason", p)

    def test_pool_persistence_with_proposals(self):
        """候选池保存和加载应包含 proposed_blocklist"""
        self._add_candidate("Test", "candidate", 5)
        self.pool.record_blocklist_proposal("test-topic")
        self.pool.save()

        # 重新加载
        pool2 = EcologyCandidatePool(self.pool_path)
        self.assertTrue(pool2._was_recently_proposed("test-topic"))


if __name__ == "__main__":
    unittest.main()
