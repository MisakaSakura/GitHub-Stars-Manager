#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline / Orchestrator：将 classifier.py 的协调逻辑抽取为可测试的阶段"""

import os
import sys
from collections import Counter

from utils import log
from github_api import GitHubAPI, GitHubAuthError, GitHubRateLimitError
from rule_classifier import RuleClassifier
from llm_classifier import LLMClassifier
from database import StarsDB
from ai_database import AIDatabase
from engine import IncrementalEngine
from import_helper import FirstRunHelper
from report import ReportGenerator
from notion import NotionExporter
from notify import Notifier
from lists_manager import ListsManager
from release_tracker import ReleaseTracker
from fork_tracker import ForkTracker

from config import NOTIFY_CONFIG


def _safe_print(msg: str) -> None:
    """安全打印，在编码不支持时回退 ASCII"""
    try:
        print(msg)
    except UnicodeEncodeError:
        ascii_msg = msg.encode("ascii", "replace").decode("ascii")
        print(ascii_msg)


class Pipeline:
    """分类工作流流水线，将 CLI 入口的协调逻辑封装为显式阶段"""

    def __init__(self, args: "argparse.Namespace"):
        self.args = args
        self.db: StarsDB | None = None
        self.gh: GitHubAPI | None = None
        self.rule: RuleClassifier | None = None
        self.llm: LLMClassifier | None = None
        self.engine: IncrementalEngine | None = None
        self.stats: dict | None = None
        self.items: list[dict] = []
        self.is_first_run = False
        self.release_updates: list[dict] = []
        self.fork_updates: list[dict] = []
        self.release_tracker: ReleaseTracker | None = None
        self.fork_tracker: ForkTracker | None = None
        self.ai_db: AIDatabase | None = None

    # ---------- 公开入口 ----------

    def run(self) -> None:
        self._setup()
        if self._import_and_early_exit():
            return
        self._auth()
        self._handle_lists()
        self._setup_llm()
        self._fetch()
        self._enrich()
        self._classify()
        self._save()
        self._sync_notion()
        self._track_releases()
        self._track_forks()
        # 报告生成必须在追踪之后，否则 Release/Fork 更新不会出现在周报中
        self._generate_reports()
        self._notify()
        self._print_summary()

    # ---------- 各阶段 ----------

    def _setup(self) -> None:
        self.is_first_run = FirstRunHelper.detect_first_run(self.args.db)
        _safe_print("=" * 60)
        _safe_print("⭐ GitHub Stars 自动分类工具 v4")
        _safe_print("=" * 60)

        if self.is_first_run:
            _safe_print("\n🆕 检测到首次运行（数据库不存在）")
            _safe_print("   将创建新数据库并对所有项目执行全新分类。")
            if self.args.import_json or self.args.import_csv:
                _safe_print("   检测到导入参数，将先导入已有分类（自动保护），再处理剩余项目。\n")
            else:
                _safe_print("   提示: 如果你有已有分类想保留，使用 --import-json 或 --import-csv 导入")
                _safe_print("   导入的项目会被自动标记保护，不会被覆盖。\n")
        else:
            _safe_print(f"\n📂 加载已有数据库: {self.args.db}\n")

        self.db = StarsDB(self.args.db)

        # 初始化 AI 数据库（与主数据库解耦）
        ai_db_path = os.path.splitext(self.args.db)[0] + "_ai.json"
        self.ai_db = AIDatabase(ai_db_path)
        # 向后兼容：从旧版主数据库迁移 AI 字段
        self.ai_db.migrate_from_stars_db(list(self.db.values()))

    def _import_and_early_exit(self) -> bool:
        """首次运行导入已有分类；若 --no-auto-classify 则提前退出。"""
        if not self.is_first_run:
            return False
        if self.args.import_json or self.args.import_csv:
            if self.args.import_json:
                FirstRunHelper.import_from_json(self.db, self.args.import_json)
            if self.args.import_csv:
                FirstRunHelper.import_from_csv(self.db, self.args.import_csv)
            self.db.save()
            log("导入完成，数据库已保存", "OK")

            if self.args.no_auto_classify:
                log("--no-auto-classify 已设置，跳过自动分类", "OK")
                _safe_print("\n" + "=" * 60)
                _safe_print(f"✅ 导入完成！共 {len(self.db)} 个项目（全部手动保护）")
                _safe_print("=" * 60)
                return True
        return False

    def _auth(self) -> None:
        try:
            self.gh = GitHubAPI(self.args.token)
        except GitHubAuthError as e:
            log(f"GitHub 认证失败: {e}", "ERROR")
            sys.exit(1)
        except GitHubRateLimitError as e:
            log(f"GitHub API 限制: {e}", "ERROR")
            sys.exit(1)
        self.rule = RuleClassifier()

    def _handle_lists(self) -> None:
        if not self.is_first_run:
            return
        lists_manager = ListsManager(self.gh)
        lists = lists_manager.detect_lists(self.args.user)
        if not lists:
            return

        summary = lists_manager.get_lists_summary(lists)
        _safe_print(f"\n📝 检测到你有 {len(summary)} 个 GitHub Lists：")
        _safe_print("   " + "-" * 42)
        _safe_print(f"   {'名称':<24} {'项目数':>10}")
        _safe_print("   " + "-" * 42)
        for s in summary:
            _safe_print(f"   {s['name']:<24} {s['count']:>10}")
        _safe_print("   " + "-" * 42)

        strategy = self.args.lists_strategy
        if strategy == "auto":
            strategy = "prompt" if sys.stdin.isatty() else "ignore"

        if strategy == "prompt":
            _safe_print("\n请选择处理方式：")
            _safe_print("  [1] 迁移：将已有 Lists 作为受保护的初始分类导入（推荐）")
            _safe_print("  [2] 重构：删除所有旧 Lists，用本工具的全新分类替代")
            _safe_print("  [3] 忽略：保留旧 Lists，本工具独立运行")
            while True:
                try:
                    choice = input("\n你的选择 [1/2/3]: ").strip()
                    if choice == "1":
                        lists_manager.migrate_lists_to_db(self.db, self.args.user)
                        self.db.save()
                        break
                    elif choice == "2":
                        lists_manager.clear_all_lists(self.args.user)
                        break
                    elif choice == "3":
                        log("已忽略 GitHub Lists", "INFO")
                        break
                    else:
                        print("请输入 1、2 或 3")
                except (EOFError, KeyboardInterrupt):
                    print("\n未收到输入，默认忽略 Lists")
                    break
        elif strategy == "migrate":
            lists_manager.migrate_lists_to_db(self.db, self.args.user)
            self.db.save()
        elif strategy == "replace":
            lists_manager.clear_all_lists(self.args.user)
        else:
            log("已忽略 GitHub Lists（--lists-strategy=ignore/auto 非 TTY）", "INFO")

    def _setup_llm(self) -> None:
        if not self.args.llm_key:
            return
        if not self.args.force_llm:
            last = self.db.meta.get("last_llm_classify_at", "")
            if last:
                from datetime import datetime, timezone, timedelta
                last_dt = datetime.fromisoformat(last)
                interval = timedelta(days=self.args.llm_interval_days)
                now = datetime.now(timezone.utc)
                if now - last_dt < interval:
                    days_left = (last_dt + interval - now).days
                    log(f"LLM 间隔保护：距上次分析还有 {days_left} 天，本次跳过（--force-llm 可强制启用）", "INFO")
                    return
        from config import LLM_CONFIG
        model = self.args.llm_model or LLM_CONFIG.get("model", "gpt-4o-mini")
        self.llm = LLMClassifier(
            api_key=self.args.llm_key,
            provider=self.args.llm_provider,
            api_base=self.args.llm_base,
            model=model
        )
        log(f"LLM 已启用: {self.args.llm_provider} / {model}")

    def _fetch(self) -> None:
        self.items = self.gh.fetch_all(self.args.user)

    def _enrich(self) -> None:
        if not self.llm:
            return
        log("获取 README 摘要用于 AI 分析...", "STEP")
        for item in self.items[:50]:
            try:
                readme = self.gh.get_readme(item["owner"]["login"], item["name"], max_length=1500)
                if readme:
                    item["readme_excerpt"] = readme
            except Exception:
                pass
        log("README 摘要获取完成", "OK")

    def _should_auto_refresh(self) -> bool:
        """判断是否需要自动全量刷新（增量模式下按间隔自动升级）"""
        if self.args.force_refresh:
            return False  # 用户已显式强制刷新
        if not self.args.incremental:
            return False  # 非增量模式本身就是全量
        last = self.db.meta.get("last_full_refresh_at", "")
        if not last:
            return True  # 从未全量刷新过
        from datetime import datetime, timezone, timedelta
        last_dt = datetime.fromisoformat(last)
        interval = timedelta(days=self.args.auto_refresh_days)
        if datetime.now(timezone.utc) - last_dt >= interval:
            return True
        return False

    def _classify(self) -> None:
        if self.is_first_run and self.args.subscribe_releases:
            log("已标记所有仓库订阅 Release", "OK")

        force_refresh = self.args.force_refresh
        if not force_refresh and self._should_auto_refresh():
            log(f"自动全量刷新：距离上次已超过 {self.args.auto_refresh_days} 天", "STEP")
            force_refresh = True

        self.engine = IncrementalEngine(self.db, self.rule, self.llm, self.ai_db)
        self.stats = self.engine.process(
            self.items,
            incremental=self.args.incremental,
            force_refresh=force_refresh,
            use_llm=bool(self.llm),
            retry_failed=self.args.retry_failed,
            subscribe_all_releases=self.args.subscribe_releases,
            llm_interval_days=self.args.llm_interval_days
        )

        # 记录本次是否为全量刷新（用于 _save 中更新时间戳）
        self._did_full_refresh = force_refresh
        self.new_keys = self.engine.new_keys
        self.star_changes = self.engine.star_changes
        self.classification_changes = self.engine.classification_changes

        # 将 LLM 结果同步到独立 AI 数据库
        if self.llm and self.ai_db:
            for key, result in self.engine.llm_results.items():
                if result:
                    self.ai_db.update_from_llm_result(key, result, status="success")

        # 从 AI 数据库回填 AI 字段到主数据库（供报告渲染使用）
        self._backfill_ai_fields()

    def _backfill_ai_fields(self) -> None:
        """从 AI 数据库回填 AI 字段到主数据库中的项目"""
        if not self.ai_db:
            return
        for key, item in self.db.items():
            ai = self.ai_db.get(key)
            if ai:
                item.llm_status = ai.llm_status
                item.llm_confidence = ai.llm_confidence
                item.llm_reason = ai.llm_reason
                item.ai_summary = ai.ai_summary
                item.ai_tags = ai.ai_tags
                item.ai_platforms = ai.ai_platforms

    def _save(self) -> None:
        if self.args.dry_run:
            log("试运行模式：数据库未保存", "WARN")
            return
        self.db.save()
        if self.ai_db:
            self.ai_db.save()
        if self.llm:
            from datetime import datetime, timezone
            self.db.meta["last_llm_classify_at"] = datetime.now(timezone.utc).isoformat()
            self.db.save_meta()
        if getattr(self, "_did_full_refresh", False):
            from datetime import datetime, timezone
            self.db.meta["last_full_refresh_at"] = datetime.now(timezone.utc).isoformat()
            self.db.save_meta()
        log("数据库已保存", "OK")

    def _generate_ai_summary(self) -> str:
        """综合生成本周动态总结。LLM 可用时用 AI 生成，否则用规则生成简洁文本。"""
        # 收集各项动态数据
        new_items_count = len(getattr(self, "new_keys", set()))
        star_changes = getattr(self, "star_changes", {})
        release_updates = self.release_updates or []
        classification_changes = getattr(self, "classification_changes", {})
        fork_updates = getattr(self, "fork_updates", [])

        has_any = (new_items_count or star_changes or release_updates or
                   classification_changes or fork_updates)
        if not has_any:
            return ""

        # 构建数据片段用于 LLM 或规则总结
        data_parts: list[str] = []
        if new_items_count:
            data_parts.append(f"新收录 {new_items_count} 个项目")
        if star_changes:
            top_names = [key for key, _ in sorted(star_changes.items(), key=lambda x: x[1], reverse=True)[:3]]
            data_parts.append(f"{len(star_changes)} 个项目 stars 增长显著（{', '.join(top_names)}）")
        if release_updates:
            release_names = [f"{ru['full_name']} {ru['old_tag']}→{ru['new_tag']}" for ru in release_updates[:3]]
            data_parts.append(f"{len(release_updates)} 个新 Release（{'; '.join(release_names)}）")
        if classification_changes:
            data_parts.append(f"{len(classification_changes)} 个项目分类被重新调整")
        if fork_updates:
            data_parts.append(f"{len(fork_updates)} 个 Fork 仓库上游有更新")

        # 无 LLM 时返回规则生成的简洁文本
        if not self.llm:
            return "本周动态：" + "；".join(data_parts) + "。"

        # LLM 可用时生成高质量总结
        llm_parts: list[str] = []
        if star_changes:
            top = sorted(star_changes.items(), key=lambda x: x[1], reverse=True)[:5]
            llm_parts.append("本周 Stars 增长最多的项目：")
            for key, delta in top:
                llm_parts.append(f"- {key}: +{delta} stars")
        if release_updates:
            llm_parts.append("\n本周新 Release：")
            for ru in release_updates:
                ai_digest = ru.get("ai_digest", "")
                line = f"- {ru['full_name']} {ru['old_tag']} → {ru['new_tag']}"
                if ai_digest:
                    line += f"（{ai_digest}）"
                llm_parts.append(line)
        if classification_changes:
            llm_parts.append("\n本周分类调整：")
            for key, changes in list(classification_changes.items())[:5]:
                change_str = ", ".join([f"{k} {v['from']}→{v['to']}" for k, v in changes.items()])
                llm_parts.append(f"- {key}: {change_str}")

        prompt = (
            "请根据以下本周 GitHub Stars 项目动态数据，用 3-5 句话生成一段简洁的中文总结。"
            "总结要突出重要更新和亮点，语气轻松自然，像技术周刊的开篇语。"
            "只输出总结内容，不要任何其他文字。\n\n"
            + "\n".join(llm_parts)
        )
        try:
            from config import LLM_SYSTEM_PROMPT
            summary = self.llm.summarize(prompt, system_prompt=LLM_SYSTEM_PROMPT, max_tokens=256)
            return summary or "本周动态：" + "；".join(data_parts) + "。"
        except Exception as e:
            log(f"AI 动态总结生成失败: {e}", "WARN")
            return "本周动态：" + "；".join(data_parts) + "。"

    def _generate_reports(self) -> None:
        if self.args.no_report or self.args.dry_run:
            if self.args.dry_run:
                log("试运行模式：报告未生成", "WARN")
            return
        report = ReportGenerator(self.db, ai_db=self.ai_db)
        # Build weekly digest data for HTML report
        # 使用 engine 记录的本次实际新增项目，避免 first_seen 被错误重置导致全部项目被视为新收录
        new_items = [self.db.get(k) for k in (getattr(self, "new_keys", None) or set()) if self.db.get(k)]
        ai_summary = self._generate_ai_summary()
        weekly_data = {
            "new_items": new_items,
            "release_updates": self.release_updates,
            "star_changes": getattr(self, "star_changes", {}),
            "fork_updates": getattr(self, "fork_updates", []),
            "classification_changes": getattr(self, "classification_changes", {}),
            "ai_summary": ai_summary,
        } if (new_items or self.release_updates or getattr(self, "star_changes", {}) or
              getattr(self, "fork_updates", []) or getattr(self, "classification_changes", {}) or ai_summary) else None
        report.generate_html(self.args.output, weekly_data=weekly_data)
        report.generate_csv(self.args.output)
        report.generate_json(self.args.output)
        # 生成独立的 Release 更新日志页面
        history_path = os.path.join(os.path.dirname(self.args.db), "releases_history.json")
        report.generate_releases_log(self.args.output, history_path=history_path)

    def _sync_notion(self) -> None:
        if not (self.args.notion_key and self.args.notion_db) or self.args.dry_run:
            return
        notion = NotionExporter(self.args.notion_key, self.args.notion_db)
        notion.sync(list(self.db.values()), clear_existing=self.args.notion_clear)

    def _track_releases(self) -> None:
        if self.args.dry_run:
            return
        if not self.args.check_releases and not self.args.check_all_releases:
            return
        self.release_tracker = ReleaseTracker(self.gh)
        items = list(self.db.values())
        if self.args.check_all_releases:
            self.release_updates = self.release_tracker.check_all(items)
        else:
            self.release_updates = self.release_tracker.check(items)
        if self.args.llm_release_digest and self.llm and self.release_updates:
            self.release_updates = self.release_tracker.digest_with_llm(self.release_updates, self.llm)
        if self.release_updates:
            self.db.save()
            self._save_release_history()

    def _save_release_history(self) -> None:
        """将本次检测到的 Release 追加到历史记录，按 full_name + new_tag 去重"""
        if not self.release_updates:
            return
        history_path = os.path.join(os.path.dirname(self.args.db), "releases_history.json")
        existing: list[dict] = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        seen = {(r.get("full_name"), r.get("new_tag")) for r in existing}
        for ru in self.release_updates:
            key = (ru.get("full_name"), ru.get("new_tag"))
            if key not in seen:
                existing.append({
                    "full_name": ru["full_name"],
                    "name": ru["name"],
                    "owner": ru["owner"],
                    "old_tag": ru["old_tag"],
                    "new_tag": ru["new_tag"],
                    "published_at": ru.get("published_at", ""),
                    "html_url": ru.get("html_url", ""),
                    "body": ru.get("body", ""),
                    "ai_digest": ru.get("ai_digest", ""),
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })
                seen.add(key)

        existing.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        # 保留最近 500 条
        existing = existing[:500]

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        log(f"Release 历史已更新: {len(existing)} 条记录", "OK")

    def _track_forks(self) -> None:
        if not self.args.check_forks or self.args.dry_run:
            return
        self.fork_tracker = ForkTracker(self.gh)
        forks = self.fork_tracker.get_user_forks(self.args.user)
        self.fork_updates = self.fork_tracker.check(forks)

    def _notify(self) -> None:
        if not self.args.notify or self.args.dry_run:
            return
        NOTIFY_CONFIG["enabled"] = True
        NOTIFY_CONFIG["channels"] = self.args.notify_channels.split(",")
        notifier = Notifier(NOTIFY_CONFIG)
        summary = self._build_summary()
        weekly_digest = self._build_weekly_digest_text()
        if weekly_digest:
            summary += "\n\n" + weekly_digest
        if self.release_updates and self.release_tracker:
            summary += "\n\n" + self.release_tracker.format_report(self.release_updates)
        if self.fork_updates and self.fork_tracker:
            summary += "\n\n" + self.fork_tracker.format_report(self.fork_updates)
        notifier.send("GitHub Stars 分类完成", summary, is_error=False)

    def _print_summary(self) -> None:
        _safe_print("\n" + "=" * 60)
        _safe_print(self._build_summary())
        _safe_print("=" * 60)

        if self.is_first_run and not self.args.import_json and not self.args.import_csv:
            _safe_print("\n💡 首次运行提示:")
            _safe_print('   1. 检查生成的报告，对不满意的项目修改 data/stars_db.json')
            _safe_print('   2. 给满意的项目添加 "manual_override": true 避免被覆盖')
            _safe_print("   3. 日常使用 --mode incremental 只处理新项目")
            _safe_print("   4. 如需重新分类所有项目，使用 --mode deep 或 --mode full")

    # ---------- 工具方法 ----------

    def _build_weekly_digest_text(self) -> str:
        """构建周报纯文本摘要，用于通知"""
        lines = []
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        week_ago = (now - timedelta(days=7)).isoformat()

        new_items = [r for r in self.db.values() if r.get("first_seen", "") >= week_ago]
        if new_items:
            lines.append(f"📦 本周新增项目: {len(new_items)} 个")
            for r in new_items[:5]:
                lines.append(f"  • {r['full_name']} | {r['ecology']} | {r['platform']} / {r['type']}")
            if len(new_items) > 5:
                lines.append(f"  ... 还有 {len(new_items) - 5} 个")

        if self.release_updates:
            lines.append(f"\n🚀 本周新 Release: {len(self.release_updates)} 个")
            for u in self.release_updates[:5]:
                digest = u.get("ai_digest", "")
                line = f"  • {u['full_name']}: {u['new_tag']}"
                if digest:
                    line += f" | {digest}"
                lines.append(line)
            if len(self.release_updates) > 5:
                lines.append(f"  ... 还有 {len(self.release_updates) - 5} 个")

        return "\n".join(lines) if lines else ""

    def _build_summary(self) -> str:
        lines = [
            "GitHub Stars 分类完成",
            "=" * 40,
        ]
        if self.is_first_run:
            lines.append("🆕 首次运行模式")
            lines.append("")
        lines.extend([
            f"数据库总计: {len(self.db)} 个项目",
            f"新增项目: {self.stats['new']}",
            f"重新分类: {self.stats['updated']}",
            f"元数据更新: {self.stats['skipped']}",
            f"手动保护: {self.stats['protected']}",
            f"LLM 分析: {self.stats['llm_enhanced']}",
            f"错误: {self.stats['error']}",
            "",
            "生态分布 Top 5:",
        ])
        eco_stats = Counter([r.get("ecology") for r in self.db.values()])
        for eco, count in eco_stats.most_common(5):
            lines.append(f"  {eco}: {count}")

        protected = sum(1 for r in self.db.values() if r.get("manual_override"))
        imported = sum(1 for r in self.db.values() if r.get("imported"))
        if protected:
            lines.append(f"\n🔒 手动保护项目: {protected} 个")
        if imported:
            lines.append(f"📥 导入项目: {imported} 个（已自动保护）")

        lines.append("\n报告已生成，请查看 GitHub Pages")
        return "\n".join(lines)
