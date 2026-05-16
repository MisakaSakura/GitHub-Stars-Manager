#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Lists 管理：检测、迁移、清理"""

from datetime import datetime, timezone

from utils import log


class ListsManager:
    def __init__(self, github_api: "GitHubAPI"):
        self.gh = github_api

    def detect_lists(self, username: str) -> list | None:
        """检测用户是否有 GitHub Lists"""
        try:
            lists = self.gh.get_lists(username)
            return lists if lists else None
        except Exception as e:
            log(f"检测 GitHub Lists 失败: {e}", "WARN")
            return None

    def get_lists_summary(self, lists: list[dict]) -> list[dict]:
        """获取 Lists 的摘要信息（用于展示），接收 detect_lists 的结果避免重复 API 调用"""
        summary = []
        for lst in lists:
            list_id = lst.get("id")
            name = lst.get("name", "未命名")
            items = self.gh.get_list_items(list_id)
            summary.append({
                "id": list_id,
                "name": name,
                "count": len(items),
            })
        return summary

    def migrate_lists_to_db(self, db, username: str) -> int:
        """将 Lists 迁移到数据库，List 名称作为 ecology 并标记手动保护"""
        log("开始迁移 GitHub Lists 到数据库...", "STEP")
        lists = self.gh.get_lists(username)
        migrated = 0
        skipped = 0

        for lst in lists:
            list_name = lst.get("name", "未命名")
            list_id = lst.get("id")
            items = self.gh.get_list_items(list_id)

            for item in items:
                repo = item.get("repository", {})
                if not repo:
                    continue

                full_name = repo.get("full_name")
                if not full_name:
                    continue

                # 如果数据库中已有（比如从 CSV/JSON 导入过），跳过避免覆盖
                if db.get(full_name):
                    skipped += 1
                    continue

                db_item = {
                    "full_name": full_name,
                    "name": repo.get("name", full_name.split("/")[1]),
                    "owner": repo.get("owner", {}).get("login", full_name.split("/")[0]),
                    "description": repo.get("description") or "",
                    "language": repo.get("language") or "文档 / 无代码",
                    "platform": "其他 / 未分类",
                    "type": "其他 / 未分类",
                    "ecology": list_name,
                    "ecology_role": "-",
                    "topics": repo.get("topics", []),
                    "stars": repo.get("stargazers_count", 0),
                    "url": repo.get("html_url", f"https://github.com/{full_name}"),
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "manual_override": True,
                    "override_fields": ["ecology", "platform", "type"],
                    "override_rules_version": "",  # 将在保存前由 StarsDB 自动填充当前版本
                    "imported": True,
                    "github_list_source": list_name,
                }
                db.set(full_name, db_item)
                migrated += 1

        log(f"Lists 迁移完成: {migrated} 个导入, {skipped} 个跳过（已存在）", "OK")
        return migrated

    def clear_all_lists(self, username: str) -> int:
        """删除用户的所有 GitHub Lists"""
        log("开始清理 GitHub Lists...", "STEP")
        lists = self.gh.get_lists(username)
        if not lists:
            log("没有找到 Lists，无需清理", "OK")
            return 0

        deleted = 0
        for lst in lists:
            list_id = lst.get("id")
            name = lst.get("name", "未命名")
            if self.gh.delete_list(list_id):
                log(f"  已删除 List: {name}", "OK")
                deleted += 1
            else:
                log(f"  删除 List 失败: {name}（可能没有足够权限）", "WARN")

        log(f"共删除 {deleted}/{len(lists)} 个 Lists", "OK")
        return deleted
