# 批次2审查报告：核心引擎与分类器

## 审查范围

| # | 文件 | 说明 |
|---|------|------|
| 1 | `scripts/engine.py` | 增量更新引擎（核心调度器） |
| 2 | `scripts/classifier.py` | CLI 入口与参数解析 |
| 3 | `scripts/rule_classifier.py` | 基于规则的分类器 |
| 4 | `scripts/llm/__init__.py` | LLM 模块导出 |
| 5 | `scripts/llm/parser.py` | LLM 响应解析器 |
| 6 | `scripts/llm/providers/base.py` | Provider 抽象基类 |
| 7 | `scripts/llm/providers/__init__.py` | Provider 模块导出 |
| 8 | `scripts/config_llm.py` | LLM 配置与系统提示词 |
| 9 | `scripts/llm_classifier.py` | LLM 分类器 Facade |
| 10 | `scripts/model_profiles.py` | 模型参数画像 |

**关联文件（引用审查）**：`scripts/llm/client.py`, `scripts/llm/cache.py`, `scripts/llm/providers/openai_compatible.py`, `scripts/models.py`, `scripts/config.py`, `scripts/config_rules.py`

**审查日期**：2026-05-17
**代码版本**：批次2-6重构后（commit fc7035c）

---

## P0 — 阻塞级（1项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P0-1 | `scripts/llm/cache.py` | 94-95 | `__del__` 中调用 `_save()` 可能在解释器关闭时执行，此时模块（如 `json`、`os`）可能已被卸载，导致 `AttributeError` 或静默失败 | 缓存丢失、潜在的崩溃、不可预测的刷盘行为 | 移除 `__del__`，改用上下文管理器（`with cache:`）或在 `classify_batch()` 等批量操作结束时显式 `save()` |

---

## P1 — 重要（16项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P1-1 | `scripts/engine.py` | 128-178 | `process()` 方法 51 行，LLM 多轮重试逻辑与主循环耦合，职责过重 | 维护困难、测试复杂 | 将 LLM 多轮重试逻辑提取为独立方法 `_run_llm_rounds()` |
| P1-2 | `scripts/engine.py` | 250-267 | `_process_single()` 仍包含 4 层条件嵌套（existing → manual_override → force_refresh → incremental），策略拆分后嵌套深度未降低 | 可读性差、分支遗漏风险 | 改用策略模式：构建策略映射表 `dict[str, Callable]`，根据条件直接 dispatch |
| P1-3 | `scripts/engine.py` | 323-326 | `_classify_item()` 中再次 `self.db.get(key)` 查询已有记录，但调用者 `_process_single()` 已查询过 `existing`，造成重复查询 | N+1 查询、性能下降 | 将 `existing` 作为参数传入 `_classify_item()` |
| P1-4 | `scripts/engine.py` | 181-200 | `_snapshot_classification()` 强制要求 `StarItem`，但 `_record_classification_change()` 用 `isinstance(before, dict)` 兼容 dict，接口语义不一致 | 类型混乱、调用者困惑 | 统一为 `StarItem` 类型，或两个方法都支持 dict |
| P1-5 | `scripts/engine.py` | 13-34 | `should_auto_refresh()` 使用 `datetime.now(timezone.utc)` 与 `fromisoformat()` 解析的时间做比较，但 `fromisoformat()` 解析无时区字符串会生成 naive datetime，比较可能抛出异常 | 运行时崩溃（TypeError: can't compare offset-naive and offset-aware datetimes） | 统一在 `fromisoformat()` 后检查 `tzinfo`，无时区则附加 `timezone.utc` |
| P1-6 | `scripts/rule_classifier.py` | 100-108 | `_load_learned_overrides()` 使用 `RuleClassifier._resolve_data_path("learned_rules")` 但拼接的是 `"learned_rules"` 而非 `"learned_rules.json"`，路径构造不一致 | 文件找不到、规则补丁不生效 | 统一路径构造：`"learned_rules.json"` 或检查路径生成逻辑 |
| P1-7 | `scripts/rule_classifier.py` | 111-140 | `_apply_learned_overrides()` 中 `topic_blacklist` 的 `[p.lower() for p in neg.get("topic_blacklist", [])]` 在每次循环中重建 | 性能浪费（O(n*m) 额外开销） | 将列表推导提取为方法局部变量 |
| P1-8 | `scripts/rule_classifier.py` | 220-238 | `_score_topics()` 中词边界检查逻辑（行 231-232）与 `_has_word_boundary()` 几乎相同但独立实现，违反 DRY | 维护困难、修复遗漏 | 复用 `_has_word_boundary()` 方法 |
| P1-9 | `scripts/config_llm.py` | 80-108 | `_build_system_prompt()` 动态生成提示词，但 `ECOLOGY_STANDARD_NAMES[:30]` 截断可能导致 LLM 对第 31+ 个生态自由发挥 | 分类不一致、生态漂移 | 改为输出全部生态列表，或明确提示"仅限以下生态，其他填 null" |
| P1-10 | `scripts/llm_classifier.py` | 136-170 | `classify_batch()` 中并发逻辑（`ThreadPoolExecutor`）与串行逻辑重复，且 `max_workers = 1 if self.batch_size >= 8 else 2` 魔法数字无解释 | 维护困难、并发行为不可预测 | 将并发阈值配置化，提取统一的 batch 处理循环 |
| P1-11 | `scripts/llm_classifier.py` | 258-262 | `_make_cache_key()` 处理 `owner` 为 dict 的情况，说明上游数据格式不统一，防御性编程掩盖了数据问题 | 隐藏数据质量问题、缓存键可能冲突 | 统一上游数据格式，在入口处做数据校验和规范化 |
| P1-12 | `scripts/llm_classifier.py` | 181-227 | `_classify_batch()` 中 `readme_max` 从 `LLM_CONFIG` 读取（业务参数），但 `LLM_CONFIG` 应只含 API 参数 | 配置职责混乱 | 将 `readme_max` 移至 `ModelProfile` 或独立的 prompt 配置 |
| P1-13 | `scripts/llm/client.py` | 69-120 | `_build_feedback_context()` 虽然加了 60 秒缓存，但首次调用和缓存过期时仍读文件，且异常时吞掉所有错误（`except Exception`） | 反馈上下文加载失败静默、调试困难 | 细分异常处理，记录具体错误类型；考虑使用文件监听或定时刷新替代 TTL |
| P1-14 | `scripts/llm/client.py` | 122-156 | `call()` 中重试逻辑（3 次指数退避）与 `OpenAICompatibleProvider.call()` 无重试逻辑，但注释说"重试由 LLMClient 统一处理"，实际 Provider 中确实无重试——但 `_build_feedback_context()` 的异常吞掉了可能导致无限循环的条件 | 重试逻辑正确但异常处理过于宽泛 | 将 `except Exception` 细化为 `FileNotFoundError`、`json.JSONDecodeError` 等 |
| P1-15 | `scripts/llm/providers/openai_compatible.py` | 52-81 | `_extract_content()` 硬编码字段名（`content`, `reasoning_content`, `reasoning`），新增厂商时需改代码 | 扩展性差 | 将响应提取路径配置化为 `response_content_paths` 列表 |
| P1-16 | `scripts/model_profiles.py` | 292-320 | `recommend_model()` 评分函数魔法数字（50、20、10）无文档说明，权重不透明 | 推荐逻辑不可解释、难以调整 | 将权重提取为命名常量或配置参数 |

---

## P2 — 建议（18项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P2-1 | `scripts/engine.py` | 49-52 | `_is_ecology_locked()` 在函数内 `from config import LOCKED_ECOLOGIES` 延迟导入 | 代码异味、循环依赖风险 | 移至模块顶部导入，或重构为配置注入 |
| P2-2 | `scripts/engine.py` | 55-71 | `_normalize_field()` 在函数内 `from config_rules import ...` 延迟导入 | 同上 | 移至模块顶部导入 |
| P2-3 | `scripts/engine.py` | 74-78 | `_safe_int()` 全局函数但仅被 `_apply_llm_override()` 使用（行 210-214 已内联处理），存在重复 | 代码冗余 | 统一使用 `_safe_int()` 或内联处理，删除未使用的函数 |
| P2-4 | `scripts/engine.py` | 250 | `_process_single()` 返回 `None`，但所有策略方法也返回 `None`，返回值无意义 | 接口语义不清 | 明确返回类型为 `None` 或改为无返回值（删除 `return`） |
| P2-5 | `scripts/classifier.py` | 50-159 | 参数解析拆分为 9 个 `_add_*_args()` 函数，但 `_add_correct_args()` 创建了独立的 argument_group 而其他没有，风格不一致 | 代码风格不一致 | 统一使用 `add_argument_group` 为每组参数添加分组标题 |
| P2-6 | `scripts/classifier.py` | 183-207 | `_apply_preset()` 中 `all_presets = {**config_llm.PROVIDER_PRESETS, **config_llm.CUSTOM_PRESETS, **env_presets}` 合并顺序导致 `env_presets` 覆盖 `CUSTOM_PRESETS`，与注释"同名后者覆盖前者"矛盾 | 配置优先级与注释不符 | 修正合并顺序或更新注释以反映实际优先级 |
| P2-7 | `scripts/classifier.py` | 210-214 | `_ensure_defaults()` 仅设置 `llm_provider` 默认值，过于单薄 | 职责不清 | 合并到 `_apply_preset()` 或扩展为完整的默认值填充 |
| P2-8 | `scripts/rule_classifier.py` | 44-46 | 类级缓存 `_learned_overrides`、`_auto_ecologies`、`_watchlist_rules` 使用 `None` 哨兵值，非线程安全 | 并发环境下可能重复加载 | 使用 `functools.lru_cache` 或线程锁保护 |
| P2-9 | `scripts/rule_classifier.py` | 49-57 | `_load_json()` 吞掉所有异常（`except Exception: pass`），文件损坏时静默返回 `{}` | 调试困难 | 记录警告日志，至少输出异常信息 |
| P2-10 | `scripts/config_llm.py` | 62-78 | `LLM_CONFIG` 中 `"enabled"` 字段注释说已废弃但字段仍在 | 配置冗余 | 移除废弃字段 |
| P2-11 | `scripts/config_llm.py` | 33-47 | `xiaomimimo` 预设的 `provider` 为 `"openai"`，但 API 基址是 `xiaomimimo`，provider 名不一致 | 语义混淆 | 统一 provider 名称为 `"xiaomimimo"`，或在 `OpenAICompatibleProvider` 中做映射 |
| P2-12 | `scripts/llm_classifier.py` | 62 | `classify_batch()` 参数 `fallback=False` 布尔语义不够自解释 | 可读性 | 使用枚举 `FallbackMode.DISABLED` / `FallbackMode.ENABLED` |
| P2-13 | `scripts/llm_classifier.py` | 86-89 | `from config import LLM_CONFIG` 在函数内导入 | 代码异味 | 移至模块顶部 |
| P2-14 | `scripts/llm/__init__.py` | 1-9 | 仅做导出，无实际逻辑，但 `LLMClient` 和 `ResponseParser` 的循环导入风险未处理 | 潜在循环依赖 | 添加 `TYPE_CHECKING` 保护或文档说明 |
| P2-15 | `scripts/llm/providers/base.py` | 1-19 | `LLMProvider` 抽象基类仅定义 2 个方法，但 `OpenAICompatibleProvider` 实现了更多行为（如 header 处理、响应提取），抽象不够完整 | 接口契约不完整 | 扩展基类方法（如 `supports_streaming`、`get_headers`）或添加文档说明 |
| P2-16 | `scripts/model_profiles.py` | 16-46 | `ModelProfile` 字段 15 个，部分字段（`price_cny_per_1m_output`、`recommendation`）仅用于排序推荐，与分类核心逻辑无关 | 类职责不单一 | 将价格/推荐字段提取到独立的 `ModelRecommendation` 类 |
| P2-17 | `scripts/model_profiles.py` | 331-339 | `PRESET_DEFAULT_MODELS` 与 `config_llm.PROVIDER_PRESETS` 中的 `model` 字段重复定义 | 维护困难、不同步风险 | 统一单一来源：从 `MODEL_PROFILES` 或 `PROVIDER_PRESETS` 自动生成 |
| P2-18 | `scripts/llm/parser.py` | 28-60 | `extract_json_from_text()` 排序逻辑 `candidates.sort(key=lambda x: (len(x), x.startswith("[")), reverse=True)` 偏好最长匹配，但不一定最准确 | 可能提取错误的 JSON 片段 | 增加结构化评分（如优先匹配代码块内的 JSON） |

---

## 按模块汇总

| 模块 | P0 | P1 | P2 | 关键问题 |
|------|-----|-----|-----|----------|
| `scripts/engine.py` | 0 | 5 | 4 | 嵌套深度、重复查询、类型不一致、时区比较 |
| `scripts/classifier.py` | 0 | 0 | 3 | 参数分组风格不一致、配置优先级与注释矛盾 |
| `scripts/rule_classifier.py` | 0 | 3 | 2 | DRY 违反、列表推导重复重建、异常吞没 |
| `scripts/llm/__init__.py` | 0 | 0 | 1 | 循环导入风险 |
| `scripts/llm/parser.py` | 0 | 0 | 1 | JSON 提取排序策略 |
| `scripts/llm/providers/base.py` | 0 | 0 | 1 | 抽象接口不完整 |
| `scripts/llm/providers/__init__.py` | 0 | 0 | 0 | — |
| `scripts/config_llm.py` | 0 | 1 | 2 | 生态列表截断、废弃字段、provider 名不一致 |
| `scripts/llm_classifier.py` | 0 | 3 | 3 | 并发魔法数字、数据格式不统一、配置职责混乱 |
| `scripts/model_profiles.py` | 0 | 1 | 2 | 评分魔法数字、字段过多、重复定义 |
| `scripts/llm/cache.py` | 1 | 0 | 0 | `__del__` 不可靠 |
| `scripts/llm/client.py` | 0 | 2 | 0 | 异常吞没、反馈上下文加载 |
| `scripts/llm/providers/openai_compatible.py` | 0 | 1 | 0 | 响应字段硬编码 |
| **合计** | **1** | **16** | **18** | |

---

## 与批次2初版审查对比

### 已修复的问题（批次2-6重构）

| 原问题 | 状态 | 说明 |
|--------|------|------|
| `process()` 52 行过长 | 部分修复 | 提取 `EngineConfig`，但方法仍 51 行 |
| `_process_single()` 48 行 | 已修复 | 拆分为 6 个策略方法（P1-15） |
| `_process_single()` 4 层嵌套 | 部分修复 | 策略拆分后嵌套仍在 dispatch 层 |
| `needs_llm()` 静态+实例方法重复 | 已修复 | 删除 `_needs_llm()`，统一使用静态方法 |
| `_apply_llm_override()` 副作用隐蔽 | 已修复 | 改为返回变更字典（P1-51） |
| `_classify_item()` 重复查询 existing | 未修复 | 仍为 P1-3 |
| 反馈上下文 I/O 频繁 | 已修复 | 增加 60 秒 TTL 缓存（P1-22） |
| 缓存无版本校验 | 已修复 | 增加 `RULES_VERSION` 缓存失效（P1-24） |
| 缓存批量写文件 | 已修复 | `set()` 只更新内存，`save()` 统一刷盘（P1-25） |
| Provider 重试逻辑重复 | 已修复 | Provider 无重试，LLMClient 统一处理 |
| `_load_learned_overrides()` ast.literal_eval | 已修复 | 改用 JSON 格式（P1-23） |

### 新增发现的问题

1. **P0-1**: `TTLCache.__del__` 不可靠 — 析构时模块可能已卸载
2. **P1-5**: `should_auto_refresh()` 时区比较风险 — naive vs aware datetime
3. **P1-6**: `_load_learned_overrides()` 路径构造不一致 — `"learned_rules"` vs `"learned_rules.json"`
4. **P1-14**: `LLMClient.call()` 异常处理过于宽泛 — `except Exception` 吞掉所有错误
5. **P2-6**: `_apply_preset()` 配置合并顺序与注释矛盾
