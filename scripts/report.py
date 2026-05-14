#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告生成器，支持 HTML/CSV/JSON 导出"""

import csv
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
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

    def generate_releases_log(self, output_dir: str, history_path: str | None = None) -> str | None:
        """生成独立的 Release 更新日志页面"""
        if not history_path or not os.path.exists(history_path):
            return None
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
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

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Release 更新日志</title>
<style>
:root{{--bg-body:#0d1117;--bg-card:#161b22;--bg-inner:#21262d;--border:#30363d;--text-primary:#c9d1d9;--text-secondary:#8b949e;--text-muted:#484f58;--accent:#58a6ff;--accent-bg:#1f6feb22;--accent-border:#1f6feb44;--success:#3fb950;--success-bg:#23863622;--success-border:#23863644;--purple:#a371f7;--purple-bg:#8957e522;--warning:#e3b341;}}
@media(prefers-color-scheme:light){{:root{{--bg-body:#ffffff;--bg-card:#f6f8fa;--bg-inner:#eef1f5;--border:#d0d7de;--text-primary:#1f2328;--text-secondary:#656d76;--text-muted:#8c959f;--accent:#0969da;--accent-bg:#0969da15;--accent-border:#0969da30;--success:#1a7f37;--success-bg:#1a7f3715;--success-border:#1a7f3730;--purple:#8250df;--purple-bg:#8250df15;--warning:#9a6700;}}}}
html[data-theme="dark"]{{--bg-body:#0d1117;--bg-card:#161b22;--bg-inner:#21262d;--border:#30363d;--text-primary:#c9d1d9;--text-secondary:#8b949e;--text-muted:#484f58;--accent:#58a6ff;--accent-bg:#1f6feb22;--accent-border:#1f6feb44;--success:#3fb950;--success-bg:#23863622;--success-border:#23863644;--purple:#a371f7;--purple-bg:#8957e522;--warning:#e3b341;}}
html[data-theme="light"]{{--bg-body:#ffffff;--bg-card:#f6f8fa;--bg-inner:#eef1f5;--border:#d0d7de;--text-primary:#1f2328;--text-secondary:#656d76;--text-muted:#8c959f;--accent:#0969da;--accent-bg:#0969da15;--accent-border:#0969da30;--success:#1a7f37;--success-bg:#1a7f3715;--success-border:#1a7f3730;--purple:#8250df;--purple-bg:#8250df15;--warning:#9a6700;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg-body);color:var(--text-primary);padding:24px;max-width:900px;margin:0 auto}}
h1{{color:var(--accent);margin-bottom:8px;font-size:24px}}
.sub{{color:var(--text-secondary);margin-bottom:24px;font-size:14px}}
.back{{display:inline-block;margin-bottom:20px;color:var(--accent);text-decoration:none;font-size:14px}}
.back:hover{{text-decoration:underline}}
.rl-item{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:16px 20px;margin-bottom:14px}}
.rl-meta{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
.rl-repo{{color:var(--accent);font-weight:600;font-size:14px;text-decoration:none}}
.rl-repo:hover{{text-decoration:underline}}
.rl-tag{{background:var(--success-bg);color:var(--success);border:1px solid var(--success-border);padding:2px 8px;border-radius:10px;font-size:11px}}
.rl-date{{color:var(--text-secondary);font-size:12px;margin-left:auto}}
.rl-ai{{color:var(--purple);font-size:12px;font-style:italic;border-left:2px solid var(--purple);padding-left:8px;margin-bottom:8px}}
.rl-body{{color:var(--text-secondary);font-size:12px;line-height:1.7;max-height:200px;overflow:hidden;position:relative;white-space:pre-wrap;word-break:break-word}}
.rl-body.expanded{{max-height:none}}
.rl-body h1,.rl-body h2,.rl-body h3,.rl-body h4{{color:var(--warning);margin:8px 0 4px}}
.rl-body code{{background:var(--bg-inner);padding:1px 4px;border-radius:3px;color:var(--purple);font-family:monospace}}
.rl-body a{{color:var(--accent)}}
.rl-body ul{{margin:4px 0 4px 16px}}
.rl-body li{{margin:2px 0}}
.rl-toggle{{color:var(--accent);font-size:12px;cursor:pointer;margin-top:6px;display:inline-block}}
.ft{{margin-top:30px;padding-top:16px;border-top:1px solid var(--border);color:var(--text-muted);font-size:12px;text-align:center}}
.theme-toggle{{position:fixed;top:16px;right:16px;background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:12px;cursor:pointer;color:var(--text-secondary);z-index:100}}
.theme-toggle:hover{{color:var(--text-primary);border-color:var(--text-muted)}}
</style>
</head>
<body>
<button class="theme-toggle" id="theme-btn" onclick="toggleTheme()">🌙</button>
<a class="back" href="index.html">← 返回分类报告</a>
<h1>🚀 Release 更新日志</h1>
<p class="sub">生成时间：{timestamp} · 共 {len(history)} 条记录</p>
{''.join(rows)}
<div class="ft">Generated by GitHub Stars Classifier v4</div>
<script>
function rlt(el){{var b=el.previousElementSibling;if(!b)return;b.classList.toggle('expanded');el.textContent=b.classList.contains('expanded')?'收起':'展开更多';}}
document.querySelectorAll('.rl-body').forEach(function(b){{if(b.scrollHeight>200){{var t=document.createElement('span');t.className='rl-toggle';t.textContent='展开更多';t.onclick=function(){{rlt(t);}};b.parentNode.appendChild(t);}}}});
function toggleTheme(){{const html=document.documentElement;const btn=document.getElementById('theme-btn');const current=html.getAttribute('data-theme');let next;if(current==='light'){{next='dark';btn.textContent='🌙';}}else if(current==='dark'){{next='light';btn.textContent='☀️';}}else{{const prefersDark=window.matchMedia('(prefers-color-scheme: dark)').matches;next=prefersDark?'light':'dark';btn.textContent=next==='dark'?'🌙':'☀️';}}html.setAttribute('data-theme',next);localStorage.setItem('gh-stars-theme',next);}}
(function(){{const saved=localStorage.getItem('gh-stars-theme');if(saved){{document.documentElement.setAttribute('data-theme',saved);document.getElementById('theme-btn').textContent=saved==='dark'?'🌙':'☀️';}}}})();
</script>
</body>
</html>'''

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
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
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
        except Exception:
            return ""

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
                # 链接 [text](url)
                line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', line)
                # 粗体 **text**
                line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)

            result.append(line)

        # 如果代码块未闭合
        if in_code and code_lines:
            result.append(f'<pre style="background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:10px;font-size:11px;overflow-x:auto"><code>{"<br>".join(code_lines)}</code></pre>')

        return '<br>'.join(result)

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
            star_changes = weekly_data.get("star_changes", {})
            fork_updates = weekly_data.get("fork_updates", [])
            classification_changes = weekly_data.get("classification_changes", {})
            ai_summary = weekly_data.get("ai_summary", "")

            # 构建各区域 tab 内容
            tabs_html: list[str] = []
            contents_html: list[str] = []
            first_tab = True

            def add_tab(tab_id: str, label: str, content: str) -> None:
                nonlocal first_tab
                active = "active" if first_tab else ""
                tabs_html.append(f'<button class="wd-tab {active}" onclick="wst(this,\'{tab_id}\')">{label}</button>')
                contents_html.append(f'<div id="wd-tab-{tab_id}" class="wd-tab-content {active}">{content}</div>')
                first_tab = False

            # 新收录
            if new_items:
                ni_parts: list[str] = []
                ni_parts.append(f'<div class="wd-section"><h3>🆕 新收录 ({len(new_items)})</h3><div class="wd-list">')
                for it in new_items:
                    url = it.get("url") or it.get("html_url", "#")
                    ni_parts.append(f'<div class="wd-item"><a href="{url}" target="_blank">{it["full_name"]}</a><span class="wd-eco">{it["ecology"]}</span></div>')
                ni_parts.append('</div></div>')
                add_tab("new", f"🆕 新收录 ({len(new_items)})", "".join(ni_parts))

            # 本周热门
            if star_changes:
                sc_parts: list[str] = []
                top_changes = sorted(star_changes.items(), key=lambda x: x[1], reverse=True)[:10]
                sc_parts.append(f'<div class="wd-section"><h3>🔥 本周热门 (Stars +)</h3><div class="wd-list">')
                for key, delta in top_changes:
                    item = self.db.get(key)
                    if item:
                        url = item.get("url") or "#"
                        sc_parts.append(f'<div class="wd-item"><a href="{url}" target="_blank">{item["full_name"]}</a><span class="wd-tag">+{delta:,} ⭐</span></div>')
                sc_parts.append('</div></div>')
                add_tab("hot", f"🔥 热门 ({len(star_changes)})", "".join(sc_parts))

            # 分类变更（前10个默认显示，其余折叠）
            if classification_changes:
                cc_parts: list[str] = []
                all_changes = list(classification_changes.items())
                visible = all_changes[:10]
                hidden = all_changes[10:]
                cc_parts.append(f'<div class="wd-section"><h3>📝 分类变更 ({len(classification_changes)})</h3><div class="wd-list">')
                for key, changes in visible:
                    item = self.db.get(key)
                    if item:
                        url = item.get("url") or "#"
                        change_str = ", ".join([f"{k}: {v['from']} → {v['to']}" for k, v in changes.items()])
                        cc_parts.append(f'<div class="wd-item"><a href="{url}" target="_blank">{item["full_name"]}</a><span class="wd-tag">{change_str}</span></div>')
                if hidden:
                    cc_parts.append('<div class="wd-list-hidden" style="display:none;flex-direction:column;gap:6px">')
                    for key, changes in hidden:
                        item = self.db.get(key)
                        if item:
                            url = item.get("url") or "#"
                            change_str = ", ".join([f"{k}: {v['from']} → {v['to']}" for k, v in changes.items()])
                            cc_parts.append(f'<div class="wd-item"><a href="{url}" target="_blank">{item["full_name"]}</a><span class="wd-tag">{change_str}</span></div>')
                    cc_parts.append('</div>')
                    cc_parts.append(f'<span class="wd-expand-toggle" onclick="wet(this)">展开全部 ({len(hidden)} 个) ▼</span>')
                cc_parts.append('</div></div>')
                add_tab("classify", f"📝 分类变更 ({len(classification_changes)})", "".join(cc_parts))

            # 新 Release（卡片式布局，类似 GitHub Feed）
            if release_updates:
                ru_parts: list[str] = []
                ru_parts.append(f'<div class="wd-section"><h3>🚀 新 Release ({len(release_updates)})</h3>')
                for ru in release_updates:
                    owner = ru["full_name"].split("/")[0]
                    avatar_url = f"https://github.com/{owner}.png?size=48"
                    rel_time = self._relative_time(ru.get("published_at", ""))
                    # 版本跳转链接：如果有多个中间版本，链接到第一个中间版本或最新版本
                    version_url = ru["html_url"]
                    ru_parts.append(
                        f'<div class="wd-release-card">'
                        f'  <div class="wd-release-header">'
                        f'    <img class="wd-release-avatar" src="{avatar_url}" alt="{owner}" loading="lazy" onerror="this.style.display=\'none\'">'
                        f'    <div class="wd-release-meta">'
                        f'      <a href="https://github.com/{ru["full_name"]}" target="_blank">{ru["full_name"]}</a> released'
                        f'      <span class="wd-release-time">{rel_time}</span>'
                        f'    </div>'
                        f'  </div>'
                        f'  <div class="wd-release-version">'
                        f'    <a href="{version_url}" target="_blank">{ru["new_tag"]}</a>'
                        f'  </div>'
                    )
                    # Release Notes
                    body = ru.get("body", "")
                    if body:
                        body_html = self._render_release_body(body)
                        ru_parts.append(
                            f'  <div class="wd-release-body">{body_html}</div>'
                            f'  <span class="wd-release-toggle" onclick="wtn(this)">展开</span>'
                        )
                    else:
                        ru_parts.append(f'  <div class="wd-release-empty">无更新日志</div>')
                    # AI 摘要
                    ai_digest = ru.get("ai_digest", "")
                    if ai_digest:
                        ru_parts.append(f'  <div class="wd-ai-digest">🤖 {escape(ai_digest)}</div>')
                    ru_parts.append('</div>')
                # 链接到完整 Release 日志页面
                ru_parts.append(f'<div style="margin-top:10px;text-align:right"><a href="releases.html" target="_blank" style="color:#58a6ff;font-size:12px;text-decoration:none">查看完整 Release 日志 →</a></div>')
                ru_parts.append('</div>')
                add_tab("release", f"🚀 Release ({len(release_updates)})", "".join(ru_parts))

            # Fork 上游更新
            if fork_updates:
                fu_parts: list[str] = []
                fu_parts.append(f'<div class="wd-section"><h3>🔱 Fork 上游更新 ({len(fork_updates)})</h3><div class="wd-list">')
                for fu in fork_updates:
                    parent_url = f"https://github.com/{fu['parent_full_name']}"
                    fu_parts.append(f'<div class="wd-item"><a href="{parent_url}" target="_blank">{fu["full_name"]}</a><span class="wd-tag">← {fu["parent_full_name"]} ({fu["parent_pushed_at"][:10]})</span></div>')
                fu_parts.append('</div></div>')
                add_tab("fork", f"🔱 Fork ({len(fork_updates)})", "".join(fu_parts))

            if tabs_html:
                wd_parts.append('<div class="weekly-digest" id="wd-main">')
                wd_parts.append('<div class="wd-header"><h2>📅 本周摘要</h2><button class="wd-toggle" onclick="tw()">收起 ▲</button></div>')
                wd_parts.append('<div id="wd-body">')
                # AI 总结卡片
                if ai_summary:
                    wd_parts.append(f'<div class="wd-summary-card"><div class="wd-summary-title">🤖 本周动态总结</div><div class="wd-summary-body">{escape(ai_summary)}</div></div>')
                wd_parts.append('<div class="wd-tabs">')
                wd_parts.extend(tabs_html)
                wd_parts.append('</div>')
                wd_parts.extend(contents_html)
                wd_parts.append('</div></div>')
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
