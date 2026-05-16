# GitHub Stars 自动分类工具 — 全面代码审查报告

## 一、逐文件审查

### 1. scripts/classifier.py — CLI 入口

**模块职责**: 参数解析 + 预设应用 + 模式映射 + 快捷修正。职责基本单一。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `_do_correct()` 104 行（含内嵌 `_correct_one()` 47 行），过长 | P1 |
| 嵌套深度 | `_do_correct()` 内嵌函数 + 多层条件，认知负荷高 | P1 |
| 导入结构 | 多处 `import` 散落在函数内部（第 243、244、246、291、315 行），非顶层导入 | P1 |
| 命名 | `_parse_env_presets` 中的 `env` 变量名过于宽泛 | P2 |
| 类型注解 | `parse_args` 返回 `argparse.Namespace`，但后续 `_apply_preset` 等函数直接修改其属性，类型不安全 | P2 |
| 设计缺陷 | `_do_correct()` 同时负责单条修正、批量修正、反馈记录、规则生成，违反 SRP | P1 |
| 设计缺陷 | 第 363 行使用 emoji `❌` 在 Windows 编码环境下可能出问题（虽然 utils.py 有 `_safe_print`，但这里用普通 print） | P2 |

**改进建议**: 将 `_do_correct` 拆分为 `CorrectCommand` 类或独立模块；将函数内 import 移到文件顶部。

---

### 2. scripts/orchestrator/new_pipeline.py — Pipeline 编排

**模块职责**: 阶段注册和依赖声明。非常薄，职责清晰。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 导入结构 | 第 23-38 行大量 `from .stages.xxx import xxx`，虽不可避免但可考虑动态导入 | P2 |
| 命名 | 类名 `NewPipeline` 含 "New" 是反模式，应直接叫 `Pipeline`；`__init__.py` 中已做 `Pipeline = NewPipeline` 别名，说明作者也意识到 | P1 |
| 设计缺陷 | `run()` 方法第 67 行 `sys.exit(1)` 在库代码中直接退出进程，不利于测试和复用 | P1 |
| 设计缺陷 | 异常处理与 `classifier.py` 的 `main()` 重复（都捕获 KeyboardInterrupt 和 Exception） | P1 |

**改进建议**: 重命名为 `Pipeline`；`run()` 抛出异常而非 `sys.exit()`；异常处理统一到 CLI 层。

---

### 3. scripts/engine.py — 增量更新引擎

**模块职责**: 项目分类的核心引擎，处理增量/全量/强制刷新逻辑。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `process()` 52 行，`_process_single()` 48 行，`_classify_item()` 42 行，均偏长 | P1 |
| 嵌套深度 | `_process_single()` 中 4 层嵌套条件（existing → manual_override → force_refresh → incremental） | P1 |
| 重复代码 | `_process_single()` 中 `force_refresh` 和 `非增量非强制刷新` 两个分支几乎相同（第 210-219 行 vs 235-239 行），仅 `manual_override` 和 `override_fields` 重置不同 | P1 |
| 类型注解 | 第 95 行 `process()` 参数列表过长（8 个参数），且 `items: list[dict]` 不够精确 | P1 |
| 导入结构 | 第 14、22、78 行有函数内 import（`from config import LOCKED_ECOLOGIES` 等） | P1 |
| 设计缺陷 | `needs_llm()` 同时是 `@staticmethod` 和实例方法 `_needs_llm()`（第 91-93 行），后者只是前者的薄包装。`classify_stage.py` 直接调用静态方法，说明实例方法已无用 | P1 |
| 设计缺陷 | `_apply_llm_override()` 是 `@staticmethod` 但接收 `target` 对象并修改其属性，副作用隐蔽 | P1 |
| 设计缺陷 | `_classify_item()` 中第 254 行再次查询 `existing = self.db.get(...)`，但调用者 `_process_single()` 已经查过了，重复查询 | P1 |

**改进建议**: 将 `_process_single()` 的条件分支提取为策略对象；删除冗余的 `_needs_llm()`；将 `_apply_llm_override()` 改为实例方法或纯函数返回新值。

---

### 4. scripts/models.py — 数据模型

**模块职责**: `StarItem` dataclass 定义。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 类型注解 | `stars: int = 0` 合理，但 `first_seen: str = ""` 和 `last_updated: str = ""` 用 `str` 而非 `datetime` 不够类型安全 | P2 |
| 设计缺陷 | 第 31-38 行注释说明 AI 字段已迁移，但仍在模型中保留（向后兼容），导致模型臃肿（45 个字段） | P1 |
| 设计缺陷 | `from_github_api()` 和 `from_dict()` 的字段映射逻辑分散，新增字段容易遗漏 | P2 |
| 设计缺陷 | `llm_status` 等字段用字符串字面量，无枚举约束 | P2 |

**改进建议**: 将 AI 相关字段提取到独立的 `AIRecord` 模型；使用 `datetime` 类型或至少用 `NewType` 包装时间字符串；定义 `LLMStatus` 枚举。

---

### 5. scripts/database.py — 数据库层

**模块职责**: JSON 文件持久化 + 元数据管理。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 命名 | `get`/`set` 方法名与 Python 内置 `dict.get`/`dict.set` 冲突认知，但这里不是子类化所以无实际冲突 | P2 |
| 类型注解 | `get()` 返回 `StarItem \| dict \| None`（第 80 行），返回类型不统一，调用者需要 `isinstance` 判断 | P1 |
| 设计缺陷 | `set()` 第 84-85 行自动将 dict 转为 `StarItem`，但 `get()` 可能返回 dict（如果之前 set 的是 dict），数据一致性风险 | P1 |
| 设计缺陷 | `set()` 第 88-90 行自动填充 `override_rules_version`，这是副作用，与"设置"操作语义不符 | P1 |
| 设计缺陷 | `_serialize()` 是 `@staticmethod` 但引用 `StarsDB._AI_FIELDS`（类变量），应改为 `@classmethod` 或直接实例方法 | P2 |
| 设计缺陷 | 元数据操作（`meta_get`/`meta_set`/`meta_save`）与主数据操作耦合在同一类中 | P2 |

**改进建议**: `get()` 统一返回 `StarItem`；将元数据管理提取为 `MetaStore` 类；`set()` 的自动版本填充移到上层调用者。

---

### 6. scripts/llm_classifier.py — LLM 分类器

**模块职责**: LLM 调用的 Facade，批量/单条分类 + 缓存。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `classify_batch()` 108 行，过长 | P1 |
| 嵌套深度 | `classify_batch()` 中并发/串行两个分支（第 105-141 行 vs 143-171 行），大量重复代码 | P1 |
| 重复代码 | 并发和串行分支的日志输出、成功/失败统计逻辑几乎完全相同（第 117-134 行 vs 146-164 行），只有 futures 处理不同 | P1 |
| 类型注解 | `classify_batch()` 参数 `items` 无类型注解；`fallback=False` 的布尔语义不够自解释 | P2 |
| 导入结构 | 第 86 行 `from config import LLM_CONFIG` 在函数内导入 | P2 |
| 设计缺陷 | `_make_cache_key()` 第 249-253 行处理 `owner` 可能是 dict 或 str 的逻辑，说明上游数据格式不统一 | P1 |
| 设计缺陷 | 第 103 行 `max_workers = 1 if self.batch_size >= 8 else 2` 的魔法数字，无配置化 | P2 |

**改进建议**: 提取并发/串行的公共逻辑为 `_process_batches()` 方法；将函数内 import 移到顶部；为 `batch_size` 阈值添加配置。

---

### 7. scripts/rule_classifier.py — 规则分类器

**模块职责**: 基于关键词匹配的分类器。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `classify_ecology()` 106 行，过长 | P1 |
| 嵌套深度 | `classify_ecology()` 中 4 层循环嵌套（生态 → 匹配类型 → pattern → topics） | P1 |
| 重复代码 | `_load_auto_ecologies()` 和 `_load_watchlist_rules()` 结构几乎相同（文件路径构造、JSON 加载、异常处理） | P1 |
| 导入结构 | 大量函数内 import（`from config_rules import ...` 在 3 个方法中重复） | P1 |
| 设计缺陷 | 类级缓存 `_learned_overrides`、`_auto_ecologies`、`_watchlist_rules` 用 `None` 哨兵值，非线程安全 | P2 |
| 设计缺陷 | `_load_learned_overrides()` 用 `ast.literal_eval` + 正则提取 Python 文件中的字典，过于脆弱。`learned_rules.py` 是机器生成的，应直接用 JSON | P1 |
| 设计缺陷 | `classify_platform`/`classify_type`/`classify_ecology` 三个方法都独立计算 `name`/`desc`/`topics`，重复提取 | P1 |
| 设计缺陷 | 评分逻辑（`score += X`）分散在多个嵌套块中，难以调试和单元测试 | P1 |

**改进建议**: 提取 `_load_json_rules()` 通用方法；将 `name`/`desc`/`topics` 提取为 `ItemFeatures` dataclass 一次性计算；评分逻辑提取为独立的 `ScoringEngine`；`learned_rules` 改用 JSON 格式。

---

### 8. scripts/config_rules.py — 分类规则配置

**模块职责**: 纯配置数据，无逻辑代码。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | 文件过长（806 行），所有规则在一个文件中，合并冲突风险高 | P1 |
| 设计缺陷 | `ECOLOGY_ALIASES` 中大量重复键（如 `"bilibili"` 出现 3 次，第 621、705 行），虽然 Python dict 后面覆盖前面，但维护困难 | P1 |
| 设计缺陷 | `ECOLOGY_STANDARD_NAMES`（第 802 行）与 `ECOLOGY_RULES.keys()` 不同步，新增生态容易遗漏 | P1 |
| 设计缺陷 | `TYPE_RULES` 中 `"应用 / App"` 和 `"Web 后端"` 都包含 `"server"` 关键词，会导致歧义匹配 | P2 |

**改进建议**: 将生态规则按文件拆分（`ecologies/clash.py`、`ecologies/vscode.py` 等）；`ECOLOGY_STANDARD_NAMES` 从 `ECOLOGY_RULES` 自动生成；消除重复别名键。

---

### 9. scripts/feedback_loop.py — 反馈循环

**模块职责**: 记录人工修正、统计模式、生成规则补丁、检测冲突。

**问题**:

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `scan_manual_overrides()` 52 行，`detect_override_conflicts()` 58 行，`generate_conflict_report()` 56 行 | P1 |
| 嵌套深度 | `scan_manual_overrides()` 中多层条件嵌套（item → manual_override → version → has_new_changes → has_diff） | P1 |
| 重复代码 | `scan_manual_overrides()` 和 `detect_override_conflicts()` 都调用 `rule.classify_platform`/`classify_type`/`classify_ecology` 获取规则分类结果，代码几乎相同（第 347-353 行 vs 386-392 行） | P1 |
| 类型注解 | `patterns` 字段类型 `dict[str, dict]` 过于宽泛，实际结构是 `field → old → new → count` 的四层嵌套 | P2 |
| 设计缺陷 | `generate_learned_overrides()` 第 247-265 行生成的否定/正向规则的 `topic_blacklist`/`desc_blacklist` 始终为空列表，因为反馈记录未存储原始项目的 topics/desc（第 247 行注释已承认） | P1 |
| 设计缺陷 | `write_learned_rules_file()` 用字符串替换 `true`→`True`、`false`→`False` 来生成 Python 代码，非常脆弱（第 297 行） | P1 |
| 设计缺陷 | `patterns` 的嵌套更新逻辑（第 99-108 行）过于复杂，可用 `collections.defaultdict` 简化 | P2 |

**改进建议**: 提取 `get_rule_classification(item_dict)` 通用函数；`learned_rules` 改用 JSON 格式输出；用 `defaultdict` 简化 patterns 更新。

---

### 10. scripts/orchestrator/stages/ 下的 Stage 文件

#### setup_stage.py
- **优点**: 简洁，职责单一
- **问题**: 第 33-38 行 SQLite 后端处理逻辑与 JSON 后端不对称；`_safe_print` 使用 emoji 在 stage 中直接输出

#### auth_stage.py
- **优点**: 极简洁，仅 22 行
- **问题**: `sys.exit(1)` 在 stage 中直接退出，不利于测试

#### fetch_stage.py
- **优点**: 极简，1 行逻辑
- **问题**: 无错误处理（`fetch_all` 的异常在 `GitHubAPI` 内部处理？）

#### classify_stage.py
- **优点**: 将 LLM 设置、数据增强、分类逻辑分离为 3 个函数
- **问题**: 
  - `enrich_stage()` 第 43 行硬编码 `candidates[:50]`，魔法数字
  - `classify_stage()` 第 62-75 行自动全量刷新逻辑与 `classifier.py` 的 `_apply_mode()` 中的模式映射重复
  - `enrich_stage()` 中 `getattr(ctx.args, 'llm_interval_days', 30)` 的默认值与 `classifier.py` 中 `argparse` 默认值 30 重复定义

#### save_stage.py
- **优点**: 简洁清晰
- **问题**: `ctx.db.meta_save()` 被调用两次（第 20 行和第 23 行），可合并

#### sync_notion_stage.py
- **优点**: 极简
- **问题**: `report._inject_ai_fields()` 调用私有方法（命名以下划线开头）

#### track_releases_stage.py
- **优点**: 历史记录去重逻辑清晰
- **问题**: `_save_release_history()` 函数过长（52 行）；文件 I/O 与业务逻辑耦合

#### track_forks_stage.py
- **优点**: 极简
- **问题**: 与 `track_releases_stage.py` 结构完全一致，可提取通用模式

#### discover_ecologies_stage.py
- **优点**: 四级状态机（candidate → watchlist → ai_reviewed → trusted）设计良好
- **问题**: 
  - 函数过长（107 行）
  - `_llm_review_watchlist()` 第 90 行直接访问 `ctx.llm.profile`，但 `llm` 对象可能没有 `profile` 属性（用 `getattr` 兜底说明作者也不确定）
  - 第 94 行 `re.search(r'\{[^}]+\}', result or "")` 的正则过于简单，无法匹配嵌套 JSON

#### check_consistency_stage.py
- **优点**: 自动修正逻辑清晰，有反馈记录
- **问题**: 
  - `_auto_fix_issues()` 中第 52-55 行对 dict 和 StarItem 的双重兼容，说明数据模型不统一
  - 第 91-94 行自动设置 `manual_override = True`，将自动修正标记为手动保护，语义矛盾

#### record_feedback_stage.py
- **优点**: 反馈闭环完整
- **问题**: 文件 I/O 重复（`os.makedirs` + `open` 出现 3 次）

#### reports_stage.py
- **优点**: AI 摘要生成逻辑有 fallback
- **问题**: `_generate_ai_summary()` 过长（70 行）；`weekly_data` 的条件判断过于复杂（第 90-92 行）

#### notify_stage.py
- **优点**: 简洁
- **问题**: 第 16 行直接修改全局配置 `NOTIFY_CONFIG["enabled"] = True`，副作用

#### print_summary_stage.py
- **优点**: 极简
- **问题**: 无

---

## 二、总体评价

### 架构设计

**优点**:
1. **Pipeline 阶段化设计优秀**: 使用 `StageRegistry` + `PipelineContext` 实现插件化流水线，阶段间通过 Context 传递状态，解耦良好
2. **存储后端抽象**: JSON 和 SQLite 双后端支持，有迁移路径
3. **AI 数据分离**: 将 LLM 元数据从主数据库分离到 `stars_ai.json`，避免主库膨胀
4. **反馈闭环**: 从 manual_override → feedback.json → learned_rules.py 的闭环设计有前瞻性

**缺陷**:
1. **Pipeline 异常处理不一致**: `classifier.py` 和 `new_pipeline.py` 都捕获异常并 `sys.exit()`，应在 CLI 层统一处理
2. **Stage 间隐式依赖**: 通过 `ctx` 属性传递，无编译时检查，容易出现 `AttributeError`
3. **数据模型双重性**: `StarItem` (dataclass) 和 `dict` 在多处混用（SQLite 后端返回 dict），导致大量 `isinstance` 判断

### 代码质量

| 指标 | 评分 | 说明 |
|------|------|------|
| 可读性 | B+ | 中文注释充分，但函数过长影响阅读 |
| 可测试性 | B | 静态方法多利于测试，但 `sys.exit()` 和全局状态影响 |
| 类型安全 | B | 有类型注解但不完整，`Any` 使用过多 |
| 错误处理 | B+ | 大部分 I/O 有 try/except，但日志后吞异常较多 |

### 模块耦合度

| 耦合点 | 问题 |
|--------|------|
| `config_rules.py` → 全模块 | 所有分类器都依赖，文件过大 |
| `engine.py` ↔ `classifier.py` | `needs_llm()` 静态方法被 stage 直接调用，破坏了 engine 的封装 |
| `feedback_loop.py` → `rule_classifier.py` | 循环导入风险（虽然当前无实际循环） |
| Stage → `PipelineContext` | 所有 stage 都依赖 Context，但 Context 使用 `Any` 类型，无接口约束 |

### 设计模式

| 模式 | 使用 | 评价 |
|------|------|------|
| **Facade** | `LLMClassifier` 组合 `LLMClient` + `ResponseParser` + `TTLCache` | 良好 |
| **Registry** | `StageRegistry` 管理 pipeline 阶段 | 良好，但依赖检查是声明性的未实际执行 |
| **Strategy** | 无显式使用，但 `_process_single()` 中的条件分支可用策略模式替换 | 建议引入 |
| **Command** | `_do_correct()` 有 Command 的影子但未显式化 | 建议提取 |

---

## 三、改进建议汇总

### P0 — 必须修复

1. **`config_rules.py` 中 `ECOLOGY_ALIASES` 的重复键**: 第 621 行 `"bilibili": "Bilibili"` 和第 705 行重复，虽然后覆盖前，但维护风险高
2. **`feedback_loop.py` 的 `generate_learned_overrides()` 生成空规则**: 第 247-265 行生成的 blacklist/whitelist 始终为空列表，功能不完整却生成文件，误导用户
3. **`database.py` 的 `set()` 返回类型不统一**: `get()` 返回 `StarItem | dict | None`，调用者需防御式编程

### P1 — 建议改进

1. **重命名 `NewPipeline` → `Pipeline`**: 消除 "New" 反模式
2. **消除 `sys.exit()` 在库代码中的使用**: 统一在 `classifier.py` 的 `main()` 中处理
3. **提取 `RuleClassifier` 的公共加载逻辑**: `_load_auto_ecologies()` 和 `_load_watchlist_rules()` 提取为 `_load_json_file()`
4. **简化 `engine.py` 的 `_process_single()`**: 将条件分支提取为策略对象或独立方法
5. **统一数据模型**: 消除 `StarItem` 和 `dict` 的混用，SQLite 后端也应返回 `StarItem`
6. **`learned_rules` 改用 JSON 格式**: 消除 `ast.literal_eval` + 字符串替换的脆弱解析
7. **将 `config_rules.py` 按生态拆分**: 降低合并冲突风险
8. **提取 `track_releases_stage.py` 和 `track_forks_stage.py` 的公共 I/O 模式**
9. **`llm_classifier.py` 的并发/串行分支消除重复代码**

### P2 — 可选优化

1. **`StarItem` 使用 `datetime` 类型替代 `str`**
2. **定义 `LLMStatus` 枚举替代字符串字面量**
3. **`PipelineContext` 使用 TypedDict 或 Protocol 替代 `Any`**
4. **`StageRegistry` 实际执行依赖检查**（当前仅声明未验证）
5. **为 `classify_batch()` 的 `fallback` 参数使用枚举替代布尔值**
6. **将 `_safe_print` 中的 emoji 使用限制在 CLI 层**
7. **添加 `py.typed` 文件以支持类型检查工具**

---

## 四、关键代码片段

**最严重的设计缺陷 — `feedback_loop.py` 生成空规则**:

```python
# 第 247-265 行：生成的规则 blacklist 始终为空
result["negative"][eco_name] = {
    "topic_blacklist": [],      # 永远为空！
    "desc_blacklist": [],       # 永远为空！
    "name_blacklist": [],       # 永远为空！
    "evidence": len(items),
    "examples": [i["full_name"] for i in items[:5]],
}
```

**最脆弱的代码 — `write_learned_rules_file()` 字符串替换**:

```python
# 第 297 行：用字符串替换生成 Python 代码
content = content.replace('true', 'True').replace('false', 'False').replace('null', 'None')
# 如果 JSON 中包含 "true" 作为字符串值（如 "is_true": "true"），会被错误替换
```

**最应该重构的函数 — `engine.py` 的 `_process_single()`**:

```python
# 48 行，4 层条件嵌套，2 个几乎相同的分支
if existing:
    if existing.manual_override: ...
    if force_refresh: ...      # 分支 A
    if incremental: ...        # 分支 B
    ...                        # 分支 C（与 A 几乎相同）
classification = ...           # 分支 D（新项目）
```

---

## 五、总结

该项目整体架构设计良好，Pipeline 阶段化和数据分离的思路清晰。主要问题集中在：

1. **代码膨胀**: 多个函数超过 50 行，嵌套过深
2. **数据模型不统一**: `StarItem`/`dict` 混用导致防御式代码遍布
3. **配置管理**: `config_rules.py` 过大，规则格式脆弱
4. **重复代码**: 并发/串行分支、规则加载、分类调用等处有明显重复

建议优先处理 P0 和 P1 级别的问题，特别是数据模型统一和 `learned_rules` 的 JSON 化，这两项改动会显著降低维护成本。

---

## 六、批次审查（按维度）

### 批次1：安全性审查（2026-05-17）

**审查范围**: 全部 Python 源文件、`scripts/` 及子目录、GitHub Actions Workflow、数据存储层（JSON + SQLite）、HTML 报告生成器。

| 安全类别 | 审查结果 | 说明 |
|---------|---------|------|
| SQL 注入 | **安全** | `sqlite_backend.py` 全部使用参数化查询（`?` 占位符），无字符串拼接 SQL |
| XSS | **安全** | `report.py` 使用 `html.escape()` 对所有用户数据（仓库名、描述、标签、链接文本）进行转义；Markdown 链接已过滤 `javascript:`/`data:`/`vbscript:` 危险协议 |
| 命令注入 | **安全** | 唯一的 `subprocess.run`（`classifier.py:49`）使用列表参数，无 `shell=True` |
| 反序列化 | **安全** | 全部使用 `json.load/s`，未使用 `pickle`/`eval`/`exec` |
| 路径遍历 | **安全** | 文件操作路径来自用户 CLI 参数或固定模板路径，无穿越系统敏感目录风险 |
| 密钥管理 | **安全** | GitHub Token / LLM Key 通过 CLI 参数或环境变量传入，代码中无硬编码凭证 |
| 数据暴露 | **安全** | 日志输出未包含敏感信息；JSON/CSV 导出仅包含公开仓库元数据 |

**结论**: 未发现置信度 >= 8 的安全漏洞。项目整体安全基线良好：数据流转清晰（GitHub API -> 本地存储 -> HTML 报告），所有对外输出均经过适当的转义或参数化处理。

**低风险注意项**（置信度 < 8，不视为漏洞）：
- `report.py:300-307` Markdown 链接的危险协议过滤使用 `re.match()` 前缀匹配，理论上存在绕过可能（如空白字符前缀），但 `strip()` 已预先处理，实际攻击面极窄
- `feedback_loop.py:271-302` 动态生成 Python 文件，若 `learned` 数据被污染存在代码注入可能，但数据来源为内部统计，攻击路径复杂

### 批次2：正确性审查（2026-05-17）

**审查范围**: 当前工作区全部变更（`override_rules_version` 机制引入 + 规则版本管理）。

**总体评价**: `override_rules_version` 机制的引入正确且完整。模型层、JSON 数据库层、SQLite 后端、反馈层、Pipeline Stage、CLI、GitHub Workflow 六层变更一致，无遗漏。

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 模型字段新增 | **正确** | `StarItem.override_rules_version: str = ""` 有默认值，向后兼容 |
| JSON 数据库自动填充 | **正确** | `StarsDB.set()` 仅在 `manual_override=True` 且版本为空时填充，避免误标记 |
| SQLite Schema 迁移 | **正确** | `ALTER TABLE ADD COLUMN` + `try/except sqlite3.OperationalError`，标准向后兼容做法 |
| SQL 参数匹配 | **正确** | INSERT VALUES `?` 数量（24个）与 `_item_to_tuple()` 元素数量一致，ON CONFLICT UPDATE 覆盖新列 |
| 强制刷新清除标记 | **正确** | `engine.py` `force_refresh` 分支设 `override_rules_version=""`，语义合理 |
| 反馈版本过滤逻辑 | **正确** | `get_correction()` 版本不一致时仅忽略 platform/type，保留 ecology/ecology_role；旧数据（无版本）视为兼容 |
| 冲突严重度分级 | **正确** | `critical` = 版本不匹配 + platform/type 冲突；`warn` = 版本匹配但有差异；`info` = 仅 ecology 差异 |
| CLI 修正设置版本 | **正确** | `_do_correct()` 设置 `override_rules_version = RULES_VERSION` |
| Workflow 修正设置版本 | **正确** | `process-feedback.yml` 同步设置版本并记录到反馈 |
| 冲突检测跳过非保护项 | **正确** | `detect_override_conflicts()` 只检查 `manual_override=True` 的项目 |

**问题发现**:

| 优先级 | 位置 | 问题 | 说明 |
|--------|------|------|------|
| P2 | `feedback_loop.py:297` | `content.replace('true', 'True')` 等字符串替换仍然脆弱 | 字符串值中包含 `"true"` 会被误替换为 `"True"`；本次 diff 仅移除了无意义的 `.replace('"', '"')` |
| P2 | `feedback_loop.py:scan_manual_overrides()` | 无条件更新 `override_rules_version` | 即使没有创建新的反馈记录也更新版本标记，版本标记与反馈记录可能不同步 |
| P2 | `test_feedback_loop.py:132-133` | `_make_item()` 假设 `full_name` 包含 `/` | 测试代码中 `full_name.split("/")` 无边界检查，不规范的测试数据会导致 `IndexError` |
| P2 | `.github/workflows/process-feedback.yml` | 仍使用已废弃的 `::set-output` 语法 | 第154-156行；不在本次 diff 范围内，但属于未修复的技术债务 |

**测试覆盖评价**:

`tests/test_feedback_loop.py`（新增，105行）覆盖了：
- 版本记录与持久化（`test_record_includes_rules_version`、`test_load_save_rules_version`）
- 版本一致/不一致时的修正返回策略（4个测试用例）
- 冲突检测三级严重度（`warn`/`critical`/`info`）
- 冲突报告 Markdown 生成
- `scan_manual_overrides` 版本更新（缺失版本、不同版本、相同版本、非保护项）
- `StarsDB.set()` 自动填充版本（保护项、非保护项、已有版本）

覆盖全面，边界条件考虑到位。

### 批次3：可维护性审查（2026-05-17）

**审查范围**: 当前工作区全部变更。

| 检查项 | 评分 | 说明 |
|--------|------|------|
| 命名一致性 | **A** | `override_rules_version` 命名清晰，跨 10+ 个文件保持一致；`_current_rules_version()` 封装了版本获取逻辑 |
| 职责分离 | **B+** | `detect_override_conflicts()` 和 `generate_conflict_report()` 分离良好；但 `scan_manual_overrides()` 同时负责扫描+版本更新，职责略多 |
| 重复代码 | **B** | `scan_manual_overrides()` 和 `detect_override_conflicts()` 都调用 `rule.classify_platform/type/ecology`，逻辑重复（约 8 行） |
| 导入结构 | **B** | `from config_rules import RULES_VERSION` 以函数内导入形式出现在 database.py、classifier.py、check_consistency_stage.py、feedback_loop.py 等 6 处，分散且重复 |
| 向后兼容 | **A** | SQLite ALTER TABLE、JSON 默认值、旧反馈数据兼容处理，迁移策略完整 |
| 测试结构 | **A** | `test_feedback_loop.py` 使用 `@patch` mock 版本号，测试独立可运行；`MockDB` 实现简洁 |

**问题发现**:

| 优先级 | 位置 | 问题 | 建议 |
|--------|------|------|------|
| P2 | `feedback_loop.py` | `scan_manual_overrides()` 和 `detect_override_conflicts()` 规则分类调用重复 | 提取 `_get_rule_classification(item_dict)` 通用函数 |
| P2 | 多文件 | `from config_rules import RULES_VERSION` 函数内导入分散在 6 处 | 在 `utils.py` 或 `config.py` 提供统一入口，或在模块顶部导入 |
| P2 | `feedback_loop.py:360-497` | `detect_override_conflicts()` + `generate_conflict_report()` 合计约 140 行，过大 | 冲突检测与报告生成分离已做，但 `detect_override_conflicts()` 内部字段对比循环可提取为 `_compare_classifications()` |
| P3 | `feedback_loop.py` | `load()` 中 `self.rules_version = ""` 在 4 个分支重复赋值 | 可在方法末尾统一设置默认值，减少重复 |
| P3 | `.github/workflows/process-feedback.yml` | Python 内联脚本（108行）过长，嵌入 YAML 中难以测试和复用 | 提取为独立 Python 脚本文件，workflow 中调用 |

**可维护性优点**:
- `_current_rules_version()` 静态方法的引入便于单元测试 mock，无需修改全局状态
- `FeedbackLoop` 的 `rules_version` 字段与 `entries`/`patterns` 同等对待，数据结构一致
- `detect_override_conflicts()` 返回结构化 dict 而非打印字符串，便于下游消费（生成报告、日志、CI 检查等）

### 批次4：可读性审查（2026-05-17）

**审查范围**: 当前工作区全部变更。

| 检查项 | 评分 | 说明 |
|--------|------|------|
| 注释质量 | **A** | `get_correction()` 注释明确说明版本不一致时的过滤策略；`detect_override_conflicts()` 注释说明返回结构；SQLite ALTER TABLE 注释说明意图 |
| 命名清晰性 | **A** | `override_rules_version`、`is_version_mismatch`、`conflict_fields`、`severity` 等变量名自描述；`critical`/`warn`/`info` 三级命名直观 |
| 代码结构 | **B+** | 新增函数职责分离良好；但 `scan_manual_overrides()` 中 for + if + if + if 形成 4 层嵌套，认知负荷较高 |
| 测试可读性 | **A** | 测试类按功能分组（VersionControl / DetectConflicts / GenerateReport / ScanOverrides / DBAutoFill），测试方法名描述性强 |

**问题发现**:

| 优先级 | 位置 | 问题 | 说明 |
|--------|------|------|------|
| P2 | `feedback_loop.py:305-362` | `scan_manual_overrides()` 嵌套过深 | for → if manual_override → if last_entry → if has_new_changes，4层嵌套；且首次记录分支与已有记录分支逻辑平行但视觉上不对称 |
| P3 | `feedback_loop.py:382-392` | `detect_override_conflicts()` 中 `item.to_dict()` 在循环内重复调用 | 每个 manual_override 项目都转换一次，可将转换逻辑提取到循环外或提取辅助函数 |
| P3 | `feedback_loop.py:440-497` | `generate_conflict_report()` 字符串拼接冗长 | 三段几乎相同的循环（critical/warn/info），只有前缀和项目不同，可提取为内部辅助函数 |

**可读性亮点**:
- `get_correction()` 的 docstring 用一句话清晰说明核心行为："版本不一致时忽略 platform/type，保留 ecology/ecology_role"
- `detect_override_conflicts()` 的严重程度判定逻辑（critical = 版本不匹配 + platform/type 冲突）自然流畅，无需额外注释即可理解
- `_ensure_schema()` 中 `pass  # 列已存在` 注释消除了读者对异常捕获意图的疑惑

### 批次5：可测试性审查（2026-05-17）

**审查范围**: 当前工作区全部变更。

| 检查项 | 评分 | 说明 |
|--------|------|------|
| 单元测试覆盖 | **B+** | `test_feedback_loop.py`（105行，18个测试方法）覆盖了版本控制、冲突检测、报告生成、扫描覆盖、DB自动填充 5 个维度 |
| Mock 策略 | **A** | `@patch("feedback_loop.FeedbackLoop._current_rules_version")` mock 策略正确，避免修改全局模块状态；`MockDB` 轻量有效 |
| 边界条件覆盖 | **A** | 版本一致/不一致/空值、仅 ecology 修正/仅 platform+type 修正、缺失版本/不同版本/相同版本、非保护项跳过 |
| 可测试性设计 | **A** | `_current_rules_version()` 提取为静态方法便于 mock；`detect_override_conflicts(db)` 接收 db 参数而非全局状态；`generate_conflict_report()` 为纯函数 |
| 缺失测试 | **B** | SQLite schema 迁移（`ALTER TABLE` 分支）、`import_helper.py` 导入设置版本、`lists_manager.py` Lists 迁移、GitHub Workflow 无自动化测试 |

**问题发现**:

| 优先级 | 位置 | 问题 | 建议 |
|--------|------|------|------|
| P2 | `tests/test_feedback_loop.py` | 缺少 SQLite 后端版本字段持久化测试 | 添加测试验证 SQLite `INSERT` + `SELECT` 后 `override_rules_version` 正确 |
| P2 | `tests/` | 缺少 `record_feedback_stage` 集成测试 | 该 stage 组合了 scan + learned rules + conflict detection，集成测试可捕获组合问题 |
| P3 | `tests/test_feedback_loop.py:112` | `test_get_correction_empty_version_treated_as_compatible` 的断言可强化 | 当前只断言返回完整修正，可额外断言不会触发版本过滤分支 |
| P3 | `.github/workflows/` | Workflow 无测试 | 可用 `act` 工具或提取脚本后做单元测试；当前仅能通过实际触发 issue 验证 |

**可测试性亮点**:
- `_current_rules_version()` 的设计使得 `RULES_VERSION` 的变更不会影响测试稳定性，测试用 mock 固定版本号
- `detect_override_conflicts()` 不依赖 `self` 的任何状态（除了导入的 `RULES_VERSION`），理论上可改为 `@staticmethod` 进一步提升可测试性
- `TestDetectOverrideConflicts` 使用 `@patch("config_rules.RULES_VERSION", "test-v2")` 直接 mock 模块常量，测试策略灵活
