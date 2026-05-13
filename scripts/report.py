#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告生成器，支持 HTML/CSV/JSON 导出"""

import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape

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

    def generate_html(self, output_dir: str, weekly_data: dict | None = None) -> str:
        items = self._inject_ai_fields(list(self.db.values()))
        total = len(items)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

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
                    "version": "4.0"
                },
                "stats": {
                    k: dict(v.most_common()) for k, v in {
                        "platform": Counter([r["platform"] for r in items]),
                        "type": Counter([r["type"] for r in items]),
                        "language": Counter([r["language"] for r in items]),
                        "ecology": Counter([r["ecology"] for r in items]),
                    }.items()
                },
                "repos": [item.to_dict() if hasattr(item, "to_dict") else item for item in items]
            }, f, ensure_ascii=False, indent=2)
        log(f"JSON 导出: {path}", "OK")
        return path

    def _build_html(self, items: list, total: int, timestamp: str, stats: dict, weekly_data: dict | None = None) -> str:
        def bar(name, count, total, cs="#58a6ff", ce="#a371f7"):
            pct = (count / total * 100) if total else 0
            return f'<div class="si"><span>{escape(str(name))}</span><span style="font-weight:600">{count}</span></div><div class="sbg"><div class="sf" style="width:{pct:.1f}%;background:linear-gradient(90deg,{cs},{ce})"></div></div>'

        def opts(items_list):
            return "\n".join([f'<option value="{escape(str(x))}">{escape(str(x))}</option>' for x in sorted(set(items_list))])

        def tag_badges(tags):
            if not tags:
                return ""
            return "".join([f'<span class="btg">{escape(str(t))}</span>' for t in tags[:5]])

        pb = "\n".join([bar(k, v, total, "#58a6ff", "#79c0ff") for k, v in stats["platform"].most_common()])
        tb = "\n".join([bar(k, v, total, "#3fb950", "#56d364") for k, v in stats["type"].most_common()])
        lb = "\n".join([bar(k, v, total, "#a371f7", "#bc8cff") for k, v in stats["language"].most_common()])
        eb = "\n".join([bar(k, v, total, "#f85149", "#ff7b72") for k, v in stats["ecology"].most_common()])

        rows_parts = []
        for r in sorted(items, key=lambda x: x["stars"], reverse=True):
            stars = f"⭐ {r['stars']:,}"
            topics = "".join([f'<span class="tt">{escape(str(t))}</span>' for t in r.get("topics", [])])
            eco_badge = f'<span class="be">{escape(r["ecology"])}</span>' if r["ecology"] != "独立项目 / Standalone" else '<span style="color:#484f58;font-size:11px">-</span>'
            role_badge = f'<span class="br">{escape(r["ecology_role"])}</span>' if r["ecology_role"] != "-" else '<span style="color:#484f58;font-size:11px">-</span>'
            lock = ' 🔒' if r.get("manual_override") else ''
            llm_status = r.get("llm_status", "")
            if llm_status == "success":
                llm_icon = ' 🤖'
            elif llm_status == "failed":
                llm_icon = ' ⚠️'
            elif llm_status == "skipped":
                llm_icon = ' ✏️'
            else:
                llm_icon = ''
            display_desc = r.get("ai_summary") or r["description"]
            tags_html = tag_badges(r.get("ai_tags"))
            plat_html = "".join([f'<span class="bpl">{escape(str(p))}</span>' for p in (r.get("ai_platforms") or [])])
            rows_parts.append(f'<tr data-p="{escape(r["platform"])}" data-t="{escape(r["type"])}" data-l="{escape(r["language"])}" data-e="{escape(r["ecology"])}" data-r="{escape(r["ecology_role"])}" data-s="{escape(llm_status)}"><td><a class="rn" href="{escape(r["url"])}" target="_blank">{escape(r["owner"])}/{escape(r["name"])}</a>{lock}{llm_icon}<div class="rd">{escape(display_desc)}</div><div class="tg">{tags_html}</div><div class="tc">{topics}</div></td><td>{eco_badge}</td><td>{role_badge}</td><td><span class="bp">{escape(r["platform"])}</span></td><td><span class="bt">{escape(r["type"])}</span></td><td><span class="bl">{escape(r["language"])}</span></td><td>{plat_html}</td><td class="st">{stars}</td></tr>')
        rows = "".join(rows_parts)

        eco_group_parts = []
        for eco_name, count in stats["ecology"].most_common():
            if eco_name == "独立项目 / Standalone":
                continue
            eco_items = [r for r in items if r["ecology"] == eco_name]
            roles = Counter([r["ecology_role"] for r in eco_items])
            rs_parts = []
            for role_name, rc in roles.most_common():
                ri = sorted([r for r in eco_items if r["ecology_role"] == role_name], key=lambda x: x["stars"], reverse=True)
                ih_parts = []
                for item in ri:
                    stars = f"⭐ {item['stars']:,}"
                    lock = ' 🔒' if item.get("manual_override") else ''
                    ih_parts.append(f'<div class="ri"><div class="rii"><a class="rin" href="{escape(item["url"])}" target="_blank">{escape(item["owner"])}/{escape(item["name"])}</a>{lock}<div class="rid">{escape(item.get("ai_summary") or item["description"])}</div></div><div class="rim"><span class="bl">{escape(item["language"])}</span><span class="st">{stars}</span></div></div>')
                rs_parts.append(f'<div class="rs"><div class="rh">🔸 {escape(role_name)} <span style="color:#8b949e;font-weight:400">({rc})</span></div><div class="rl">{"".join(ih_parts)}</div></div>')
            eco_group_parts.append(f'<div class="eg"><div class="eh" onclick="te(this)"><div class="et">🌿 {escape(eco_name)}</div><span class="ec">{count} 个项目</span></div><div class="eb">{"".join(rs_parts)}</div></div>')

        standalone = sorted([r for r in items if r["ecology"] == "独立项目 / Standalone"], key=lambda x: x["stars"], reverse=True)
        if standalone:
            ih_parts = []
            for item in standalone:
                stars = f"⭐ {item['stars']:,}"
                lock = ' 🔒' if item.get("manual_override") else ''
                ih_parts.append(f'<div class="ri"><div class="rii"><a class="rin" href="{escape(item["url"])}" target="_blank">{escape(item["owner"])}/{escape(item["name"])}</a>{lock}<div class="rid">{escape(item.get("ai_summary") or item["description"])}</div></div><div class="rim"><span class="bp">{escape(item["platform"])}</span><span class="bt">{escape(item["type"])}</span><span class="bl">{escape(item["language"])}</span><span class="st">{stars}</span></div></div>')
            eco_group_parts.append(f'<div class="eg"><div class="eh" onclick="te(this)"><div class="et" style="color:#8b949e">📦 独立项目 / Standalone</div><span class="ec" style="background:#30363d;color:#8b949e">{len(standalone)} 个项目</span></div><div class="eb collapsed"><div class="rs"><div class="rl">{"".join(ih_parts)}</div></div></div></div>')
        eco_groups = "".join(eco_group_parts)

        fork_items = [r for r in items if r.get("is_fork")]
        if fork_items:
            fh_parts = []
            for f in sorted(fork_items, key=lambda x: x["stars"], reverse=True):
                stars = f"⭐ {f['stars']:,}"
                parent_info = ""
                if f.get("parent_full_name"):
                    ppa = (f.get("parent_pushed_at") or "未知")[:10]
                    parent_info = f'<div style="color:#8b949e;font-size:11px">← {escape(f["parent_full_name"])} (上游更新: {escape(ppa)})</div>'
                sync_btn = f'<a href="https://github.com/{escape(f["full_name"])}/sync" target="_blank" style="color:#58a6ff;font-size:11px;text-decoration:none">[Sync]</a>'
                fh_parts.append(f'<div class="ri"><div class="rii"><a class="rin" href="{escape(f["url"])}" target="_blank">{escape(f["owner"])}/{escape(f["name"])}</a>{sync_btn}<div class="rid">{escape(f.get("ai_summary") or f["description"])}</div>{parent_info}</div><div class="rim"><span class="bl">{escape(f["language"])}</span><span class="st">{stars}</span></div></div>')
            fork_groups = f'<div class="eg"><div class="eh"><div class="et">🔱 我的 Forks</div><span class="ec">{len(fork_items)} 个</span></div><div class="eb"><div class="rs"><div class="rl">{"".join(fh_parts)}</div></div></div></div>'
        else:
            fork_groups = '<div class="sn">暂无 Fork 仓库数据，使用 --check-forks 可检测上游更新。</div>'

        # Weekly Digest Block
        wd_parts: list[str] = []
        if weekly_data:
            new_items = weekly_data.get("new_items", [])
            release_updates = weekly_data.get("release_updates", [])
            if new_items or release_updates:
                wd_parts.append('<div class="weekly-digest">')
                wd_parts.append('<h2>📅 本周摘要</h2>')
                if new_items:
                    wd_parts.append(f'<div class="wd-section"><h3>🆕 新收录 ({len(new_items)})</h3><div class="wd-list">')
                    for it in new_items:
                        url = it.get("url") or it.get("html_url", "#")
                        wd_parts.append(f'<div class="wd-item"><a href="{url}" target="_blank">{it["full_name"]}</a><span class="wd-eco">{it["ecology"]}</span></div>')
                    wd_parts.append('</div></div>')
                if release_updates:
                    wd_parts.append(f'<div class="wd-section"><h3>🚀 新 Release ({len(release_updates)})</h3><div class="wd-list">')
                    for ru in release_updates:
                        wd_parts.append(f'<div class="wd-item"><a href="{ru["html_url"]}" target="_blank">{ru["full_name"]}</a><span class="wd-tag">{ru["old_tag"]} → {ru["new_tag"]}</span></div>')
                    wd_parts.append('</div></div>')
                wd_parts.append('</div>')
        weekly_digest = "".join(wd_parts) if wd_parts else ""

        with open(self.template_path, "r", encoding="utf-8") as f:
            template = f.read()

        replacements = {
            "{{TOTAL}}": str(total),
            "{{TIMESTAMP}}": timestamp,
            "{{PLATFORM_OPTIONS}}": opts([r["platform"] for r in items]),
            "{{TYPE_OPTIONS}}": opts([r["type"] for r in items]),
            "{{LANGUAGE_OPTIONS}}": opts([r["language"] for r in items]),
            "{{ECOLOGY_OPTIONS}}": opts([r["ecology"] for r in items]),
            "{{ROLE_OPTIONS}}": opts([r["ecology_role"] for r in items if r["ecology_role"] != "-"]),
            "{{STATUS_OPTIONS}}": opts([r.get("llm_status", "") for r in items if r.get("llm_status")]),
            "{{ROWS}}": rows,
            "{{ECOLOGY_GROUPS}}": eco_groups,
            "{{FORK_GROUPS}}": fork_groups,
            "{{WEEKLY_DIGEST}}": weekly_digest,
            "{{PLATFORM_BARS}}": pb,
            "{{TYPE_BARS}}": tb,
            "{{LANGUAGE_BARS}}": lb,
            "{{ECOLOGY_BARS}}": eb,
        }
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
        return template
