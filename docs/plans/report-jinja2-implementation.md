# Report Jinja2 模板化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `report.py` 的 `_build_html()` 从字符串 `replace` 替换改为 Jinja2 模板引擎渲染，消除 130+ 行内嵌 HTML 拼接逻辑。

**Architecture:** 保留所有现有 CSS/JS 和页面结构不变。将 `_render_row()`、`_build_eco_groups()`、`_build_fork_groups()`、`_build_weekly_digest()` 中的 HTML 拼接逻辑迁移到 `report_template.html` 的 Jinja2 语法中。`_build_html()` 仅负责准备纯数据上下文（dict/list）并调用 `jinja2.Template.render()`。

**Tech Stack:** Python 3.13, Jinja2>=3.1.0 (已在 requirements.txt 中)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/report_template.html` | 重写 | Jinja2 模板：包含所有 HTML 结构 + 数据循环渲染逻辑 |
| `scripts/report.py` | 修改 | 重写 `_build_html()` 为数据准备；保留 `_bar()`、`_opts()`、`_tag_badges()`、`_feedback_url()` 等辅助方法 |
| `tests/test_report.py` 或现有测试 | 验证 | 确保 HTML 输出结构等价，测试通过 |

---

## Task 1: 重写 report_template.html 为 Jinja2 语法

**Files:**
- Modify: `scripts/report_template.html`

**当前问题：** 模板使用 `{{PLACEHOLDER}}` 字符串替换，如 `{{ROWS}}`、`{{ECOLOGY_GROUPS}}` 等。这些占位符被替换为已经拼接好的 HTML 字符串，没有利用 Jinja2 的循环/条件/自动转义能力。

**修改策略：**

1. 将 `{{ROWS}}` 改为 Jinja2 循环：
   ```html
   {% for row in rows %}
   <tr data-p="{{ row.platform|e }}" ...>
     ...
   </tr>
   {% endfor %}
   ```

2. 将 `{{ECOLOGY_GROUPS}}` 改为嵌套循环：
   ```html
   {% for eco in ecology_groups %}
   <div class="eg">...
     {% for role in eco.roles %}
     ...
     {% endfor %}
   </div>
   {% endfor %}
   ```

3. 将 `{{FORK_GROUPS}}` 改为循环
4. 将 `{{WEEKLY_DIGEST}}` 改为完整的 tabs/sections 循环
5. 将 `{{*_OPTIONS}}` 改为循环生成 `<option>`
6. 将 `{{*_BARS}}` 改为循环生成统计条

**数据上下文设计（`_build_html()` 准备）：**

```python
context = {
    "total": total,
    "timestamp": timestamp,
    "rows": [...],  # list[dict]
    "platform_options": [...],  # list[str]
    "type_options": [...],
    "language_options": [...],
    "ecology_options": [...],
    "role_options": [...],
    "status_options": [...],
    "ecology_groups": [...],  # list[dict] with nested roles/items
    "fork_groups": [...],  # list[dict]
    "weekly_digest": {...} or None,
    "platform_bars": [...],  # list[(name, count, pct)]
    "type_bars": [...],
    "language_bars": [...],
    "ecology_bars": [...],
}
```

---

## Task 2: 重写 report.py 的 `_build_html()`

**Files:**
- Modify: `scripts/report.py`

**Step 1: 导入 jinja2**

在文件顶部添加：
```python
from jinja2 import Template
```

**Step 2: 重写 `_build_html()`**

```python
def _build_html(self, items: list, total: int, timestamp: str, stats: dict, weekly_data: dict | None = None) -> str:
    # 准备模板需要的数据（不再拼接 HTML 字符串）
    rows = [self._row_data(r) for r in sorted(items, key=lambda x: x["stars"], reverse=True)]
    ecology_groups = self._build_ecology_data(items, stats)
    fork_groups = self._build_fork_data(items)
    weekly_digest = self._build_weekly_data(weekly_data)

    bars = {
        k: [(name, count, (count / total * 100) if total else 0)
            for name, count in stats[k].most_common()]
        for k in ["platform", "type", "language", "ecology"]
    }

    context = {
        "total": total,
        "timestamp": timestamp,
        "rows": rows,
        "platform_options": sorted({r["platform"] for r in items}),
        "type_options": sorted({r["type"] for r in items}),
        "language_options": sorted({r["language"] for r in items}),
        "ecology_options": sorted({r["ecology"] for r in items}),
        "role_options": sorted({r["ecology_role"] for r in items if r["ecology_role"] != "-"}),
        "status_options": sorted({r.get("llm_status", "") for r in items if r.get("llm_status")}),
        "ecology_groups": ecology_groups,
        "fork_groups": fork_groups,
        "weekly_digest": weekly_digest,
        "platform_bars": bars["platform"],
        "type_bars": bars["type"],
        "language_bars": bars["language"],
        "ecology_bars": bars["ecology"],
    }

    with open(self.template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())

    return template.render(**context)
```

**Step 3: 创建 `_row_data()` 替代 `_render_row()`**

```python
def _row_data(self, r: dict) -> dict:
    """准备单行数据（供 Jinja2 模板渲染）"""
    fb_url = self._feedback_url(r["full_name"], r["ecology"])
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
        "feedback_url": fb_url,
        "eco_badge": r["ecology"] != "独立项目 / Standalone",
        "role_badge": r["ecology_role"] != "-",
    }
```

**Step 4: 创建 `_build_ecology_data()` 替代 `_build_eco_groups()`**

```python
def _build_ecology_data(self, items: list, stats: dict) -> list[dict]:
    """准备生态分组数据（供 Jinja2 模板渲染）"""
    result = []
    for eco_name, count in stats["ecology"].most_common():
        if eco_name == "独立项目 / Standalone":
            continue
        eco_items = [r for r in items if r["ecology"] == eco_name]
        from collections import Counter
        roles = Counter([r["ecology_role"] for r in eco_items])
        role_data = []
        for role_name, rc in roles.most_common():
            ri = sorted([r for r in eco_items if r["ecology_role"] == role_name],
                       key=lambda x: x["stars"], reverse=True)
            role_data.append({
                "name": role_name,
                "count": rc,
                "items": [self._eco_item_data(item) for item in ri],
            })
        result.append({
            "name": eco_name,
            "count": count,
            "roles": role_data,
        })

    standalone = sorted([r for r in items if r["ecology"] == "独立项目 / Standalone"],
                       key=lambda x: x["stars"], reverse=True)
    if standalone:
        result.append({
            "name": "独立项目 / Standalone",
            "count": len(standalone),
            "roles": [{"name": None, "count": len(standalone),
                      "items": [self._eco_item_data(item) for item in standalone]}],
            "is_standalone": True,
        })
    return result
```

**Step 5: 创建 `_eco_item_data()` 辅助方法**

```python
def _eco_item_data(self, item: dict) -> dict:
    fb_url = self._feedback_url(item["full_name"], item["ecology"])
    return {
        "url": item["url"],
        "owner": item["owner"],
        "name": item["name"],
        "description": item.get("ai_summary") or item["description"],
        "language": item["language"],
        "stars": item["stars"],
        "manual_override": item.get("manual_override"),
        "feedback_url": fb_url,
    }
```

**Step 6: 创建 `_build_fork_data()` 替代 `_build_fork_groups()`**

```python
def _build_fork_data(self, items: list) -> list[dict]:
    """准备 Fork 分组数据"""
    fork_items = [r for r in items if r.get("is_fork")]
    result = []
    for f in sorted(fork_items, key=lambda x: x["stars"], reverse=True):
        result.append({
            "url": f["url"],
            "full_name": f["full_name"],
            "owner": f["owner"],
            "name": f["name"],
            "description": f.get("ai_summary") or f["description"],
            "language": f["language"],
            "stars": f["stars"],
            "parent_full_name": f.get("parent_full_name"),
            "parent_pushed_at": (f.get("parent_pushed_at") or "未知")[:10],
        })
    return result
```

**Step 7: 创建 `_build_weekly_data()` 替代 `_build_weekly_digest()`**

```python
def _build_weekly_data(self, weekly_data: dict | None) -> dict | None:
    """准备周报数据"""
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
            "items": [_item_dict(it) for it in new_items],
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
            "items": hot_items,
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
            "items": change_items,
            "hidden_items": hidden_items,
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
            "items": release_items,
            "type": "release",
            "title_html": " | ".join(title_parts),
        })

    # 生态候选
    ecology_candidates = weekly_data.get("ecology_candidates", [])
    if ecology_candidates:
        tabs.append({
            "id": "eco",
            "label": f"🌱 候选 ({len(ecology_candidates)})",
            "items": ecology_candidates,
            "type": "eco_candidates",
        })

    # Fork 上游更新
    fork_updates = weekly_data.get("fork_updates", [])
    if fork_updates:
        tabs.append({
            "id": "fork",
            "label": f"🔱 Fork ({len(fork_updates)})",
            "items": fork_updates,
            "type": "fork_updates",
        })

    if not tabs:
        return None

    return {
        "tabs": tabs,
        "ai_summary": weekly_data.get("ai_summary", ""),
    }
```

**Step 8: 删除旧方法**

删除 `_render_row()`、`_build_eco_groups()`、`_build_fork_groups()`、`_build_weekly_digest()` 的旧 HTML 拼接版本。

保留：`_bar()`、`_opts()`、`_tag_badges()`、`_feedback_url()`、`_repo_slug()`、`_repo_slug_cached()`、`_inject_ai_fields()`、`_relative_time()`、`_render_release_body()`

---

## Task 3: 运行测试验证

**Files:**
- Test: 现有测试 `tests/test_*.py`

Run: `python -m pytest tests/ -x --tb=short`
Expected: 219 passed

---

## Self-Review Checklist

1. **Spec coverage:**
   - ✅ Jinja2 模板引擎替换字符串 replace
   - ✅ 自动转义（Jinja2 默认 `|e`）
   - ✅ `_repo_slug_cached()` 已缓存（之前就已完成）
   - ✅ `_build_html()` 行数 < 30 行
   - ✅ 删除内部嵌套函数

2. **Placeholder scan:** 无 TBD/TODO

3. **Type consistency:** 所有 dict key 命名统一

---

## 已知例外

`generate_releases_log()`（生成独立 `releases.html` 页面）**不在本计划范围内**，仍使用 `releases_template.html` 的 `{{PLACEHOLDER}}` 字符串替换方式。原因：
- Release 日志页面结构简单（仅列表渲染），Jinja2 收益有限
- 如需统一，可后续单独迁移
