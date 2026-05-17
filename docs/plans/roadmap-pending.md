# 待办排期 — P1 / P3 / 生态 Blocklist 远程提交

> 创建日期: 2026-05-18
> 状态: P1 ✅ 已完成 / P3 ✅ 已完成 / Blocklist ✅ 已完成 — 排期全部完成

---

## 排期概览

| 优先级 | 任务 | 工作量 | 前置依赖 | 建议启动时机 |
|--------|------|--------|----------|-------------|
| **P0** | P1 预分类增强 | 2.5-3.5h | 无 | ✅ 2026-05-18 完成 |
| **P1** | P3 分类一致性自检 | 1.5-2h | **P1 运行稳定后** | ✅ 2026-05-18 完成 |
| **P2** | 生态 Blocklist 远程自动提交 | 2-3h | 无 | ✅ 2026-05-18 完成 |

**总计**: 6-8.5h，建议分 2 次迭代完成

---

## 任务一：P1 预分类增强

### 目标
调用 LLM 前，先用 topics + README 前 500 字做一轮语义预分类，把结果写入 LLM prompt 作为参考。

### 现状
当前 LLM 仅凭项目名 + 短描述推断，对冷门项目准确率有限（如 OBS 插件看到 "plugin"+"video" 就猜游戏）。

### 设计实现

**1. `config_rules.py` — 新增 `PRECLASSIFY_RULES`**

```python
PRECLASSIFY_RULES: dict[str, dict] = {
    # topic 关键词 → 预分类提示
    "obs-studio": {"ecology": "OBS Studio", "platform": "桌面端"},
    "neovim": {"ecology": "Neovim", "type": "编辑器 / IDE"},
    "mpv": {"ecology": "MPV", "platform": "跨平台"},
    # ... 动态从 ECOLOGY_RULES 推导核心项目对应的 topic 映射
}
```

- 优先从 `ecologies.yaml` 的 `core_projects` 和 `topic_patterns` 自动推导映射
- 手动补充边缘 case（约 20-30 条）

**2. `engine.py` — 新增 `_pre_classify(item)`**

```python
def _pre_classify(self, item: dict) -> dict:
    """返回预分类建议，供 LLM prompt 参考"""
    result = {}
    topics = [t.lower() for t in item.get("topics", [])]
    for topic in topics:
        if topic in PRECLASSIFY_RULES:
            result.update(PRECLASSIFY_RULES[topic])
    # README 关键词扫描（前 500 字）
    readme = item.get("readme_section", "")[:500].lower()
    for keyword, suggestion in README_KEYWORD_MAP.items():
        if keyword in readme:
            result.update(suggestion)
    return result
```

在 `_process_single()` 中 LLM 调用前执行，结果写入 `item["_pre_classify"]`。

**3. `llm_classifier.py` / `prompts/` — Prompt 注入参考分类**

在 batch/single prompt 中增加一节：

```
参考分类（基于 topics 和 README 自动推导，仅供参考）：
- 生态: {pre_classify.ecology or "未推断"}
- 平台: {pre_classify.platform or "未推断"}
- 类型: {pre_classify.type or "未推断"}

注意：如参考分类与项目实际不符，请以实际内容为准进行修正。
```

**4. `tests/test_engine.py` — 新增预分类逻辑测试**

- `test_pre_classify_with_topics_match`：topics 命中规则
- `test_pre_classify_with_readme_keywords`：README 关键词命中
- `test_pre_classify_no_match_returns_empty`：无命中返回空
- `test_pre_classify_does_not_override_manual`：不覆盖 manual_override

### 工作量
**2.5-3.5h**

| 模块 | 时间 | 说明 |
|------|------|------|
| `PRECLASSIFY_RULES` 设计 + 数据 | 0.5h | 从 ECOLOGY_RULES 推导 + 手动补充 |
| `_pre_classify()` 实现 | 0.5h | topics + README 扫描 |
| Prompt 模板修改 | 0.5h | batch + single 两个模板 |
| 测试编写 | 0.5-1h | 4-6 个用例 |
| 联调验证 | 0.5-1h | 跑一批真实数据对比准确率变化 |

### 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| batch prompt 变长 → token +10-20% | 成本微增 | 当前月增 ¥0.16，+20% ≈ +¥0.03，可忽略 |
| 预分类错误误导 LLM | 准确率反而下降 | prompt 中加 "仅供参考，请以实际内容为准修正" |
| 规则维护成本 | 新增生态需同步 | 优先从 ECOLOGY_RULES 自动推导，减少手动维护 |

---

## 任务二：P3 分类一致性自检

### 目标
自动标记逻辑矛盾的可疑分类，辅助人工发现规则/LLM 错误。

### 设计实现

**1. `engine.py` — 新增 `_check_consistency()`**

```python
CONSISTENCY_RULES = [
    # (描述, 检查函数, 权重)
    ("生态为编辑器但平台不是桌面/跨平台", lambda i: i.ecology in EDITOR_ECOLOGIES and i.platform not in {"桌面端", "跨平台", "macOS", "Windows", "Linux"}, 0.8),
    ("生态为代理工具但类型不是工具/应用", lambda i: i.ecology in PROXY_ECOLOGIES and i.type not in {"工具 / Tool", "应用 / App"}, 0.6),
    ("生态角色为核心但 stars < 100", lambda i: i.ecology_role == "核心 / Core" and i.stars < 100, 0.5),
    ("类型为框架但 stars < 50", lambda i: i.type == "框架 / Framework" and i.stars < 50, 0.4),
    ("标注独立项目但 topics 命中生态规则", lambda i: i.ecology == "独立项目" and any(t in ECOLOGY_TOPICS for t in i.topics), 0.7),
]

def _check_consistency(self, item: StarItem) -> tuple[bool, float, str]:
    """返回 (是否可疑, 置信度, 原因描述)"""
    matched = [(desc, weight) for desc, check, weight in CONSISTENCY_RULES if check(item)]
    if not matched:
        return False, 0.0, ""
    total_weight = sum(w for _, w in matched)
    reasons = "; ".join(desc for desc, _ in matched)
    return True, min(total_weight, 1.0), reasons
```

**2. `ai_database.py` — 扩展状态**

```python
# llm_status 新增枚举值
"suspicious"  # 规则分类与一致性检查冲突
```

在 `AIResult` 中新增字段：
- `consistency_flags: list[str]` — 命中的规则描述列表
- `consistency_score: float` — 综合可疑度（0.0-1.0）

**3. `report.py` / `report_template.html` — ⚠️ 标记**

```html
{% if row.llm_status == 'suspicious' %}
  <span title="{{ row.consistency_reason }}" style="color:var(--warning)">⚠️</span>
{% endif %}
```

鼠标悬停显示具体原因。

**4. `tests/` — 一致性规则测试**

- `test_consistency_editor_without_desktop_platform`：编辑器生态但平台不匹配
- `test_consistency_core_with_low_stars`：核心角色但 stars 过低
- `test_consistency_independent_but_matches_eco_topic`：独立项目但 topics 命中生态

### 工作量
**1.5-2h**

### 关键决策：规则调参

P3 最大的成本不是实现，而是**调参避免误报**。建议策略：
1. 先实现硬编码规则（5-8 条）
2. 在 P1 运行一段时间后的真实数据上观察误报率
3. 误报率 > 20% 时收紧阈值，< 5% 时放宽

**因此 P3 应排在 P1 之后**——P1 先提升准确率，P3 再在更干净的数据上检测异常。

---

## 任务三：生态 Blocklist 远程自动提交

### 背景与问题

当前流程：
1. 生态发现扫描出候选 → 写入 `ecology_candidates.json`
2. 生成 `docs/ecology_discovery.md` 报告
3. **用户手动查看报告 → 手动编辑 `ecology_blocklist.yaml` → commit → push**

痛点：
- 用户不会每周去看 ecology_discovery 报告
- 等发现误识别时，噪声候选已经积累多轮
- 手动编辑 YAML 的门槛虽低，但需要记住流程

### 目标
发现高置信度噪声候选时，**自动创建 GitHub Issue 提议加入 blocklist**，沿用现有的 `classification-correction.yml` Issue 反馈机制。

### 设计实现

**1. 新增 `.github/ISSUE_TEMPLATE/ecology-blocklist.yml`**

```yaml
name: "🚫 生态 Blocklist 提议"
description: "提议将某个 topic 或前缀加入生态发现排除列表"
title: "[生态Blocklist] "
labels: ["生态-blocklist"]
body:
  - type: input
    id: indicator
    attributes:
      label: "待排除项"
      placeholder: "如: android, cli, apk"
  - type: dropdown
    id: indicator_type
    attributes:
      label: "类型"
      options: ["topic", "name_prefix"]
  - type: textarea
    id: reason
    attributes:
      label: "理由"
      placeholder: "如: 'android' 是平台关键词，不应被识别为生态"
  - type: input
    id: triggered_by
    attributes:
      label: "触发的候选生态"
      placeholder: "如: Android 生态 (3个项目)"
```

**2. `ecology_candidates.py` — 新增自动 issue 提交逻辑**

```python
def propose_blocklist(self, candidate_name: str, indicator_type: str, indicator_value: str) -> bool:
    """对确认为噪声的候选，自动创建 GitHub Issue 提议 blocklist

    触发条件（同时满足）：
    1. 候选状态为 candidate 或 watchlist
    2. 出现次数 >= 3 次（排除偶发噪声）
    3. indicator_value 不在现有 blocklist 中
    4. 自动推导的噪声列表已确认（PLATFORM_RULES / TYPE_RULES 覆盖）
    5. 过去 7 天内未对同一 indicator 创建过 issue（防重复）
    """
```

**3. `github_api.py` — 新增 `create_issue()`**

```python
def create_issue(self, title: str, body: str, labels: list[str] = None) -> dict | None:
    """创建 GitHub Issue，返回创建结果"""
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    return self._post(f"/repos/{self.repo_slug}/issues", payload)
```

**4. `scripts/orchestrator/stages/discover_ecologies_stage.py` — 集成**

在 `discover_ecologies_stage` 阶段结束后：
1. 遍历所有 `candidate` / `watchlist` 状态候选
2. 对每个候选调用 `candidate_pool.should_propose_blocklist()`
3. 满足条件的调用 `github_api.create_issue()`
4. 记录已创建 issue 的 indicator 到 `ecology_candidates.json`（防重复）

**5. `tests/` — 新增测试**

- `test_blocklist_proposal_skips_existing_blocklist`：已 blocklist 的不重复
- `test_blocklist_proposal_dedup_within_7_days`：7 天内不重复创建
- `test_blocklist_proposal_requires_min_occurrence`：少于 3 次不创建

### 触发策略（关键设计）

| 场景 | 行为 | 原因 |
|------|------|------|
| 候选来自自动推导噪声（如 `android` topic） | ✅ 自动创建 issue | 确定性高，人工复核成本低 |
| 候选来自 name_prefix（如 `go-` 开头） | ✅ 自动创建 issue | 通用前缀误识别概率高 |
| 候选置信度 > 0.8 且项目数 > 5 | ✅ 自动创建 issue | 高置信度噪声 |
| 候选与现有生态名称相似（编辑距离 < 3） | ⚠️ 跳过，人工判断 | 可能是新生态而非噪声 |
| Actions 环境无 GH_TOKEN 写权限 | ❌ 静默跳过 | 避免失败中断主流程 |

### 工作量
**2-3h**

| 模块 | 时间 |
|------|------|
| Issue 模板设计 | 0.25h |
| `github_api.create_issue()` | 0.25h |
| `EcologyCandidatePool.propose_blocklist()` | 0.5h |
| 触发条件 + 防重复逻辑 | 0.5h |
| Stage 集成 | 0.25h |
| 测试 | 0.5h |

### 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Issue 泛滥（噪声候选多） | 仓库 issue 爆炸 | 7 天防重复 + 仅高置信度触发 |
| 误判（真实生态被 block） | 漏识别新生态 | Issue 标题明确标注"提议"，需人工审核后关闭/合并 |
| GH_TOKEN 权限不足 | Actions 失败 | 写权限检查，无权限时静默跳过 |

---

## 实施建议

### 推荐顺序

```
迭代 1（单次 3-4h）
├── P1 预分类增强
└── 生态 Blocklist 远程提交（可并行，无依赖）
        ↓ 运行 1-2 周观察效果
迭代 2（单次 1.5-2h）
└── P3 分类一致性自检（依赖 P1 后的干净数据）
```

### 为什么不一次做完

1. **P1 和 P3 有数据依赖**：P3 的调参需要 P1 先稳定后的分类数据作为基准
2. **Blocklist 独立**：与 P1/P3 无数据依赖，可以并行，但分开做便于单独验证 issue 创建频率
3. **控制变更节奏**：三个任务都触及核心分类流程，一次全改出问题难定位

### 验收标准

**P1 验收**：
- [ ] batch/single prompt 中均包含"参考分类"一节
- [ ] 同一批 50 个新项目，LLM 生态准确率提升 > 10%（人工抽样验证）
- [ ] token 消耗增加在 20% 以内

**P3 验收**：
- [ ] 可疑项目行显示 ⚠️ 标记，悬停显示原因
- [ ] 误报率 < 20%（抽查 50 个标记项目）
- [ ] 不阻塞正常分类流程

**Blocklist 验收**：
- [ ] 高置信度噪声候选自动创建 issue（测试仓库验证）
- [ ] 同一 indicator 7 天内不重复创建
- [ ] 无 GH_TOKEN 写权限时静默跳过，不报错
