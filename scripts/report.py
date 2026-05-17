#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告生成器，支持 HTML/CSV/JSON 导出"""

import csv
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from html import escape

from jinja2 import Template
from utils import log


class ReportGenerator:
    def __init__(self, db, template_path: str | None = None, ai_db=None):
        self.db = db
        self.ai_db = ai_db
        self.template_path = template_path or os.path.join(
            os.path.dirname(__file__), "report_template.html"
        )

    def _inject_ai_fields(self, items: list) -> list[dict]:
        """将 AI 数据库中的字段注入到项目 dict 中供渲染使用"""
        if not self.ai_db:
            return [r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in items]
        result = []
        for item in items:
            d = item.to_dict() if hasattr(item, "to_dict") else dict(item)
            ai = self.ai_db.get(d.get("full_name"))
            if ai:
                d["llm_status"] = ai.llm_status
                d["llm_confidence"] = ai.llm_confidence
                d["llm_reason"] = ai.llm_reason
                d["ai_summary"] = ai.ai_summary
                d["ai_tags"] = ai.ai_tags
                d["ai_platforms"] = ai.ai_platforms
            result.append(d)
        return result

    @staticmethod
    @lru_cache(maxsize=1)
    def _repo_slug_cached() -> str:
        """获取当前仓库的 owner/repo（缓存结果，避免重复执行子进程）。"""
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if repo and "/" in repo:
            return repo
        try:
            import subprocess
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5
            )
            url = result.stdout.strip()
            if url and "github.com" in url:
                parts = url.replace(":", "/").split("/")
                if len(parts) >= 2:
                    return f"{parts[-2]}/{parts[-1].replace('.git', '')}"
        except Exception:
            pass
        return ""

    def _repo_slug(self) -> str:
        """获取当前仓库的 owner/repo（兼容旧接口，实际调用缓存版本）。"""
        return self._repo_slug_cached()

    def _feedback_url(self, full_name: str, current_eco: str) -> str:
        """生成预填充的 GitHub Issue 反馈链接"""
        repo = self._repo_slug()
        if not repo:
            return ""
        title = f"[分类修正] {full_name}"
        body = f"**项目地址**: {full_name}\n\n**修正字段**: 生态归属 (ecology)\n\n**当前分类（错误）**: {current_eco}\n\n**建议分类（正确）**: \n\n**理由**: "
        return f"https://github.com/{repo}/issues/new?template=classification-correction.yml&title={escape(title)}&body={escape(body)}"

    def generate_html(self, output_dir: str, weekly_data: dict | None = None) -> str:
        items = self._inject_ai_fields(list(self.db.values()))
        total = len(items)
        now_utc = datetime.now(timezone.utc)
        now_cst = now_utc.astimezone(timezone(timedelta(hours=8)))
        timestamp = now_utc.strftime("%Y-%m-%d %H:%M UTC") + " / " + now_cst.strftime("%m-%d %H:%M CST")

        stats = {
            "platform": Counter([r["platform"] for r in items]),
            "type": Counter([r["type"] for r in items]),
            "language": Counter([r["language"] for r in items]),
            "ecology": Counter([r["ecology"] for r in items]),
        }

        html = self._build_html(items, total, timestamp, stats, weekly_data)
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "index.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        log(f"HTML 报告: {path}", "OK")
        return path

    def generate_csv(self, output_dir: str) -> str:
        items = self._inject_ai_fields(list(self.db.values()))
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "stars_data.csv")
        fieldnames = [
            "full_name", "name", "owner", "description", "language",
            "platform", "type", "ecology", "ecology_role",
            "topics", "stars", "url", "manual_override"
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                row = item.to_dict() if hasattr(item, "to_dict") else dict(item)
                row["topics"] = ", ".join(row.get("topics", []))
                writer.writerow(row)
        log(f"CSV 导出: {path}", "OK")
        return path

    def generate_json(self, output_dir: str) -> str:
        items = self._inject_ai_fields(list(self.db.values()))
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "stars_data.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total": len(items),
                    "version": "1.0"
                },
                "stats": {
                    k: dict(v.most_common()) for k, v in {
                        "platform": Counter([r["platform"] for r in items]),
                        "type": Counter([r["type"] for r in items]),
                        "language": Counter([r["language"] for r in items]),
                        "ecology": Counter([r["ecology"] for r in items]),
                    }.items()
                },
                "repos": [
                    item.to_dict() if hasattr(item, "to_dict") else dict(item)
                    for item in items
                ]
            }, f, ensure_ascii=False, indent=2)
        log(f"JSON 导出: {path}", "OK")
        return path

    def generate_releases_log(self, output_dir: str, history_path: str | None = None) -> str | None:
        """生成独立的 Release 更新日志页面"""
        if not history_path or not os.path.exists(history_path):
            return None
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            return None
        # P0 fix: 防御文件被外部编辑为 dict 等非 list 类型
        if not isinstance(history, list):
            return None
        if not history:
            return None

        now_utc = datetime.now(timezone.utc)
        now_cst = now_utc.astimezone(timezone(timedelta(hours=8)))
        timestamp = now_utc.strftime("%Y-%m-%d %H:%M UTC") + " / " + now_cst.strftime("%m-%d %H:%M CST")
        rows: list[str] = []
        for r in history[:200]:  # 最多显示最近 200 条
            body = r.get("body", "")
            body_html = self._render_release_body(body) if body else "<em style='color:#484f58'>无更新日志</em>"
            ai_digest = r.get("ai_digest", "")
            ai_html = f'<div class="rl-ai">🤖 {escape(ai_digest)}</div>' if ai_digest else ""
            pub = r.get("published_at", "")[:10]
            rows.append(
                f'<div class="rl-item">'
                f'<div class="rl-meta">'
                f'<a class="rl-repo" href="{escape(r.get("html_url", "#"))}" target="_blank">{escape(r["full_name"])}</a>'
                f'<span class="rl-tag">{escape(r.get("old_tag") or "首次")} → {escape(r["new_tag"])}</span>'
                f'<span class="rl-date">{pub}</span>'
                f'</div>'
                f'{ai_html}'
                f'<div class="rl-body">{body_html}</div>'
                f'</div>'
            )

        releases_template_path = os.path.join(os.path.dirname(__file__), "releases_template.html")
        try:
            with open(releases_template_path, "r", encoding="utf-8") as f:
                template = f.read()
        except FileNotFoundError:
            log(f"Release 模板文件不存在: {releases_template_path}", "ERROR")
            raise

        replacements = {
            "{{TIMESTAMP}}": timestamp,
            "{{RECORD_COUNT}}": str(len(history)),
            "{{ROWS}}": "".join(rows),
        }
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
        html = template

        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "releases.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        log(f"Release 日志: {path}", "OK")
        return path

    @staticmethod
    def _relative_time(iso_str: str) -> str:
        """ISO 时间转中文相对时间（如 3小时前）"""
        if not iso_str:
            return ""
        from datetime import datetime, timezone
        from utils import parse_iso
        dt = parse_iso(iso_str)
        if dt is None:
            return ""
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.days >= 1:
            return f"{delta.days}天前"
        hours = delta.seconds // 3600
        if hours >= 1:
            return f"{hours}小时前"
        minutes = delta.seconds // 60
        if minutes >= 1:
            return f"{minutes}分钟前"
        return "刚刚"

    @staticmethod
    def _render_release_body(text: str) -> str:
        """简单渲染 Release Notes 为 HTML（保留格式 + 简单 Markdown）"""
        if not text:
            return ""
        import re
        lines = text.split('\n')
        result: list[str] = []
        in_code = False
        code_lines: list[str] = []

        for raw_line in lines:
            line = escape(raw_line)
            # 代码块 ```
            if raw_line.lstrip().startswith('```'):
                if in_code:
                    result.append(f'<pre style="background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:10px;font-size:11px;overflow-x:auto"><code>{"<br>".join(code_lines)}</code></pre>')
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                continue

            if in_code:
                code_lines.append(line)
                continue

            # 标题
            if raw_line.startswith('#### '):
                line = f'<h4>{escape(raw_line[5:])}</h4>'
            elif raw_line.startswith('### '):
                line = f'<h3>{escape(raw_line[4:])}</h3>'
            elif raw_line.startswith('## '):
                line = f'<h2>{escape(raw_line[3:])}</h2>'
            elif raw_line.startswith('# '):
                line = f'<h1>{escape(raw_line[2:])}</h1>'
            else:
                # 行内代码
                line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
                # 链接 [text](url) — P1 fix: 防御 XSS（过滤危险协议 + escape URL）
                def _link_repl(m):
                    text = escape(m.group(1))
                    url = m.group(2).strip()
                    # 过滤危险协议
                    if re.match(r'^(javascript|data|vbscript):', url, re.IGNORECASE):
                        url = '#'
                    return f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{text}</a>'
                line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _link_repl, line)
                # 粗体 **text**
                line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)

            result.append(line)

        # 如果代码块未闭合
        if in_code and code_lines:
            result.append(f'<pre style="background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:10px;font-size:11px;overflow-x:auto"><code>{"<br>".join(code_lines)}</code></pre>')

        return '<br>'.join(result)

    @staticmethod
    def _bar(name, count, total, cs="#58a6ff", ce="#a371f7") -> str:
        pct = (count / total * 100) if total else 0
        return f'<div class="si"><span>{escape(str(name))}</span><span style="font-weight:600">{count}</span></div><div class="sbg"><div class="sf" style="width:{pct:.1f}%;background:linear-gradient(90deg,{cs},{ce})"></div></div>'

    @staticmethod
    def _opts(items_list) -> str:
        return "\n".join([f'<option value="{escape(str(x))}">{escape(str(x))}</option>' for x in sorted(set(items_list))])

    @staticmethod
    def _tag_badges(tags) -> str:
        if not tags:
            return ""
        return "".join([f'<span class="btg">{escape(str(t))}</span>' for t in tags[:5]])

    def _build_html(self, items: list, total: int, timestamp: str, stats: dict, weekly_data: dict | None = None) -> str:
        context = self._prepare_template_context(items, total, timestamp, stats, weekly_data)

        with open(self.template_path, "r", encoding="utf-8") as f:
            template = Template(f.read())

        return template.render(**context)

    def _prepare_template_context(self, items: list, total: int, timestamp: str, stats: dict, weekly_data: dict | None = None) -> dict:
        """准备 Jinja2 模板渲染所需的纯数据上下文。"""

        def _bar_data(counter, total_count: int) -> list[dict]:
            """将 Counter 转为条形图数据列表。"""
            return [
                {"name": name, "count": count, "pct": (count / total_count * 100) if total_count else 0}
                for name, count in counter.most_common()
            ]

        return {
            "total": total,
            "timestamp": timestamp,
            "rows": [self._row_data(r) for r in sorted(items, key=lambda x: x["stars"], reverse=True)],
            "platform_options": sorted({r["platform"] for r in items}),
            "type_options": sorted({r["type"] for r in items}),
            "language_options": sorted({r["language"] for r in items}),
            "ecology_options": sorted({r["ecology"] for r in items}),
            "role_options": sorted({r["ecology_role"] for r in items if r["ecology_role"] != "-"}),
            "status_options": sorted({r.get("llm_status", "") for r in items if r.get("llm_status")}),
            "ecology_groups": self._build_ecology_data(items, stats),
            "fork_groups": self._build_fork_data(items),
            "weekly_digest": self._build_weekly_data(weekly_data),
            "platform_bars": _bar_data(stats["platform"], total),
            "type_bars": _bar_data(stats["type"], total),
            "language_bars": _bar_data(stats["language"], total),
            "ecology_bars": _bar_data(stats["ecology"], total),
        }

    def _row_data(self, r: dict) -> dict:
        """准备单行数据（供 Jinja2 模板渲染）。"""
        raw_topics = r.get("topics", [])
        if isinstance(raw_topics, str):
            raw_topics = [raw_topics]
        raw_ai_tags = r.get("ai_tags") or []
        if isinstance(raw_ai_tags, str):
            raw_ai_tags = [raw_ai_tags]
        raw_plat = r.get("ai_platforms") or []
        if isinstance(raw_plat, str):
            raw_plat = [raw_plat]
        llm_status = r.get("llm_status", "")

        # P3: 一致性自检
        from config_rules import check_consistency
        is_suspicious, consistency_flags = check_consistency(r)

        return {
            "platform": r["platform"],
            "type": r["type"],
            "language": r["language"],
            "ecology": r["ecology"],
            "ecology_role": r["ecology_role"],
            "stars": r["stars"],
            "url": r["url"],
            "owner": r["owner"],
            "name": r["name"],
            "description": r.get("ai_summary") or r["description"],
            "topics": raw_topics,
            "manual_override": r.get("manual_override"),
            "llm_status": llm_status,
            "llm_icon": {"success": " 🤖", "failed": " ⚠️", "skipped": " ✏️"}.get(llm_status, ""),
            "ai_tags": raw_ai_tags[:5],
            "ai_platforms": raw_plat,
            "feedback_url": self._feedback_url(r["full_name"], r["ecology"]),
            "has_eco_badge": r["ecology"] != "独立项目",
            "has_role_badge": r["ecology_role"] != "-",
            "is_suspicious": is_suspicious,
            "consistency_flags": consistency_flags,
            "suspicious_icon": " ⚠️" if is_suspicious else "",
        }

    def _build_ecology_data(self, items: list, stats: dict) -> list[dict]:
        """准备生态分组数据（供 Jinja2 模板渲染）。"""
        result = []
        for eco_name, count in stats["ecology"].most_common():
            if eco_name == "独立项目":
                continue
            eco_items = [r for r in items if r["ecology"] == eco_name]
            roles = Counter([r["ecology_role"] for r in eco_items])
            role_data = []
            for role_name, rc in roles.most_common():
                ri = sorted([r for r in eco_items if r["ecology_role"] == role_name],
                           key=lambda x: x["stars"], reverse=True)
                role_data.append({
                    "name": role_name,
                    "count": rc,
                    "entries": [self._eco_item_data(item) for item in ri],
                })
            result.append({
                "name": eco_name,
                "count": count,
                "roles": role_data,
                "is_standalone": False,
            })

        standalone = sorted([r for r in items if r["ecology"] == "独立项目"],
                           key=lambda x: x["stars"], reverse=True)
        if standalone:
            result.append({
                "name": "独立项目",
                "count": len(standalone),
                "roles": [{"name": None, "count": len(standalone),
                          "items": [self._eco_item_data(item) for item in standalone]}],
                "is_standalone": True,
            })
        return result

    def _eco_item_data(self, item: dict) -> dict:
        return {
            "url": item["url"],
            "owner": item["owner"],
            "name": item["name"],
            "description": item.get("ai_summary") or item["description"],
            "language": item["language"],
            "stars": item["stars"],
            "manual_override": item.get("manual_override"),
            "feedback_url": self._feedback_url(item["full_name"], item["ecology"]),
        }

    def _build_fork_data(self, items: list) -> dict | None:
        """准备 Fork 分组数据。"""
        fork_items = [r for r in items if r.get("is_fork")]
        if not fork_items:
            return None
        return {
            "count": len(fork_items),
            "entries": [
                {
                    "url": f["url"],
                    "full_name": f["full_name"],
                    "owner": f["owner"],
                    "name": f["name"],
                    "description": f.get("ai_summary") or f["description"],
                    "language": f["language"],
                    "stars": f["stars"],
                    "parent_full_name": f.get("parent_full_name"),
                    "parent_pushed_at": (f.get("parent_pushed_at") or "未知")[:10],
                }
                for f in sorted(fork_items, key=lambda x: x["stars"], reverse=True)
            ],
        }

    def _build_weekly_data(self, weekly_data: dict | None) -> dict | None:
        """准备周报数据。"""
        if not weekly_data:
            return None

        def _item_dict(item):
            return item.to_dict() if hasattr(item, "to_dict") else dict(item)

        tabs = []

        # 新收录
        new_items = weekly_data.get("new_items", [])
        if new_items:
            tabs.append({
                "id": "new",
                "label": f"🆕 新收录 ({len(new_items)})",
                "entries": [_item_dict(it) for it in new_items],
                "type": "new_items",
            })

        # 本周热门
        star_changes = weekly_data.get("star_changes", {})
        if star_changes:
            top_changes = sorted(star_changes.items(), key=lambda x: x[1], reverse=True)[:10]
            hot_items = []
            for key, delta in top_changes:
                raw = self.db.get(key)
                if raw:
                    d = _item_dict(raw)
                    hot_items.append({"full_name": d["full_name"], "url": d.get("url", "#"), "delta": delta})
            tabs.append({
                "id": "hot",
                "label": f"🔥 热门 ({len(star_changes)})",
                "entries": hot_items,
                "type": "hot",
            })

        # 分类变更
        classification_changes = weekly_data.get("classification_changes", {})
        if classification_changes:
            all_changes = list(classification_changes.items())
            visible = all_changes[:10]
            hidden = all_changes[10:]
            change_items = []
            for key, changes in visible:
                raw = self.db.get(key)
                if raw:
                    d = _item_dict(raw)
                    change_str = ", ".join([f"{k}: {v['from']} → {v['to']}" for k, v in changes.items()])
                    change_items.append({"full_name": d["full_name"], "url": d.get("url", "#"), "change": change_str})
            hidden_items = []
            for key, changes in hidden:
                raw = self.db.get(key)
                if raw:
                    d = _item_dict(raw)
                    change_str = ", ".join([f"{k}: {v['from']} → {v['to']}" for k, v in changes.items()])
                    hidden_items.append({"full_name": d["full_name"], "url": d.get("url", "#"), "change": change_str})
            tabs.append({
                "id": "classify",
                "label": f"📝 分类变更 ({len(classification_changes)})",
                "entries": change_items,
                "hidden_entries": hidden_items,
                "type": "classify",
            })

        # 新 Release
        release_updates = weekly_data.get("release_updates", [])
        if release_updates:
            new_repo_count = sum(1 for ru in release_updates if ru.get("is_new_repo"))
            regular_count = len(release_updates) - new_repo_count
            release_items = []
            for ru in release_updates:
                full_name = ru.get("full_name", "")
                owner, _, _ = full_name.partition("/")
                release_items.append({
                    "full_name": full_name,
                    "owner": owner,
                    "avatar_url": f"https://github.com/{owner}.png?size=48" if owner else "",
                    "new_tag": ru.get("new_tag", "未知"),
                    "html_url": ru.get("html_url", "#"),
                    "is_new_repo": ru.get("is_new_repo", False),
                    "published_at": ru.get("published_at", ""),
                    "rel_time": self._relative_time(ru.get("published_at", "")),
                    "body": ru.get("body", ""),
                    "body_html": self._render_release_body(ru.get("body", "")) if ru.get("body") else None,
                    "ai_digest": ru.get("ai_digest", ""),
                })
            title_parts = []
            if new_repo_count:
                title_parts.append(f"🆕 新收录动态 ({new_repo_count})")
            if regular_count:
                title_parts.append(f"🚀 新 Release ({regular_count})")
            tab_label = f"🚀 Release ({len(release_updates)})"
            if new_repo_count:
                tab_label = f"🚀 Release ({regular_count}) + 🆕 ({new_repo_count})"
            tabs.append({
                "id": "release",
                "label": tab_label,
                "entries": release_items,
                "type": "release",
                "title_html": " | ".join(title_parts),
            })

        # 生态候选
        ecology_candidates = weekly_data.get("ecology_candidates", [])
        if ecology_candidates:
            for c in ecology_candidates:
                c["status_icon"] = {
                    "candidate": "🔍",
                    "watchlist": "👀",
                    "ai_reviewed": "🤖",
                    "trusted": "✅",
                }.get(c.get("status"), "❓")
            tabs.append({
                "id": "eco",
                "label": f"🌱 候选 ({len(ecology_candidates)})",
                "entries": ecology_candidates,
                "type": "eco_candidates",
            })

        # Fork 上游更新
        fork_updates = weekly_data.get("fork_updates", [])
        if fork_updates:
            tabs.append({
                "id": "fork",
                "label": f"🔱 Fork ({len(fork_updates)})",
                "entries": fork_updates,
                "type": "fork_updates",
            })

        if not tabs:
            return None

        return {
            "tabs": tabs,
            "ai_summary": weekly_data.get("ai_summary", ""),
        }

