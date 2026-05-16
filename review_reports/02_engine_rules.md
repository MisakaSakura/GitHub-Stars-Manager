# 批次 2：核心算法与业务规则审查

**审查范围**：引擎 (engine.py)、规则分类器 (rule_classifier.py)、LLM 分类器 (llm_classifier.py + llm/)、规则配置 (config_rules.py / config.py / config_llm.py / model_profiles.py)、反馈闭环 (feedback_loop.py)、生态规则包 (ecologies/)
**审查日期**：2026-05-17

---

## 1. engine.py — 增量更新引擎

**模块职责**：项目分类的核心引擎，处理增量/全量/强制刷新逻辑。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `process()` 52 行，`_process_single()` 48 行，`_classify_item()` 42 行，均偏长 | P1 |
| 嵌套深度 | `_process_single()` 中 4 层嵌套条件（existing → manual_override → force_refresh → incremental） | P1 |
| 重复代码 | `_process_single()` 中 `force_refresh` 和 `非增量非强制刷新` 两个分支几乎相同（第 222-224 行 vs 第 240 行），仅 `clear_override` 不同 | P1 |
| 类型注解 | `process()` 参数列表过长（8 个参数），且 `items: list[dict]` 不够精确 | P1 |
| 导入结构 | 第 14 行 `from config import LOCKED_ECOLOGIES` 在函数内导入 | P1 |
| 设计缺陷 | `needs_llm()` 同时是 `@staticmethod` 和实例方法 `_needs_llm()`（第 91-93 行），后者只是薄包装 | P1 |
| 设计缺陷 | `_apply_llm_override()` 是 `@staticmethod` 但接收 `target` 对象并修改其属性，副作用隐蔽 | P1 |
| 设计缺陷 | `_classify_item()` 中第 255 行再次查询 `existing = self.db.get(...)`，但调用者 `_process_single()` 已经查过了，重复查询 | P1 |
| 设计缺陷 | `_snapshot_classification()` 强制要求 `StarItem`，但 `_record_classification_change()` 用 `isinstance(before, dict)` 兼容 dict，不一致 | P1 |
| 设计缺陷 | `_replace_classification()` 与 `_process_single()` 中 `existing.stars = new_stars` 等元数据更新逻辑分散 | P2 |

**改进建议**：
1. 将 `_process_single()` 的条件分支提取为策略对象（`ForceRefreshStrategy`, `IncrementalStrategy`, `StandardStrategy`）
2. 删除冗余的 `_needs_llm()`，统一使用静态方法
3. 将 `_classify_item()` 中的 `existing` 查询改为参数传入
4. `_apply_llm_override()` 改为返回新对象或纯函数返回变更字典

---

## 2. rule_classifier.py — 规则分类器

**模块职责**：基于关键词匹配的分类器，纯函数，无外部依赖。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 导入结构 | `from config_rules import ...` 在 3 个方法中重复出现（第 183、293、335 行） | P2 |
| 设计缺陷 | 类级缓存 `_learned_overrides`、`_auto_ecologies`、`_watchlist_rules` 用 `None` 哨兵值，非线程安全 | P2 |
| 设计缺陷 | `_load_learned_overrides()` 用 `ast.literal_eval` + 正则提取 Python 文件中的字典，过于脆弱 | P1 |
| 设计缺陷 | `_apply_learned_overrides()` 中 `topic_blacklist` 的 `[p.lower() for p in ...]` 在每次循环中重建 | P2 |
| 设计缺陷 | `_score_topics()` 中词边界检查逻辑与 `_has_word_boundary()` 几乎相同，但独立实现 | P2 |
| 设计缺陷 | `_find_best_role()` 中 `full_text = features.full_text` 和 `topics = features.topics` 局部变量复制，无必要 | P3 |
| 安全性 | 无文件系统安全问题（JSON 加载 + `os.path.exists` 检查） | ✅ 安全 |

**改进建议**：
1. `_load_learned_overrides()` 的 Python 文件回退已废弃，可移除
2. 将 `_apply_learned_overrides()` 中的列表推导缓存为局部变量
3. 统一词边界检查逻辑，复用 `_has_word_boundary()`
4. 考虑使用 `functools.lru_cache` 替代手动的 `None` 哨兵缓存

---

## 3. config_rules.py — 分类规则配置

**模块职责**：纯配置数据，无逻辑代码。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `ECOLOGY_ALIASES` 中大量重复键的字面量定义（虽 Python dict 后覆盖前，但维护困难） | P1 |
| 设计缺陷 | `TYPE_RULES` 中 `"应用 / App"` 和 `"Web 后端"` 都包含 `"server"` 关键词，会导致歧义匹配 | P2 |
| 设计缺陷 | `ECOLOGY_RULES` 从 `ecologies` 包导入，但 `ECOLOGY_STANDARD_NAMES` 仍需手动补充不在规则中的独立生态（第 286-288 行） | P2 |
| 设计缺陷 | `PLATFORM_RULES["跨平台"]` 包含 `"electron"`，但 `Electron` 也是独立生态，会导致双重匹配 | P2 |
| 设计缺陷 | 无规则冲突检测机制，新增规则时可能引入关键词重叠 | P2 |

**改进建议**：
1. `ECOLOGY_STANDARD_NAMES` 完全自动化生成，移除手动补充列表
2. 添加规则冲突检测脚本（检测关键词在多个类别中的重叠）
3. 为 `TYPE_RULES` 中的 `"server"` 歧义添加排除规则或细化关键词

---

## 4. config.py — 配置聚合

**模块职责**：向后兼容的配置聚合入口。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | 仅做 `from X import *` 聚合，无实际逻辑，但提供了冗余的导入路径 | P2 |
| 设计缺陷 | 导入了 `ECOLOGY_RULES`，但 `config_rules.py` 中的 `ECOLOGY_RULES` 又从 `ecologies` 包导入，形成间接依赖链 | P2 |

**改进建议**：
1. 添加 `__all__` 明确导出内容
2. 考虑逐步废弃此文件，引导调用者直接从子模块导入

---

## 5. config_llm.py — LLM 配置

**模块职责**：LLM API 参数与系统提示词。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `LLM_CONFIG` 中 `"enabled"` 字段注释说已废弃，但字段仍在（第 63 行） | P2 |
| 设计缺陷 | `LLM_SYSTEM_PROMPT` 硬编码为 93 行多行字符串，包含过时的平台/类型枚举（与 `config_rules.py` 不同步） | P1 |
| 设计缺陷 | 系统提示词中的平台列表（第 87 行）与 `PLATFORM_RULES` 不同（多了 "AI / 机器学习"、"DevOps / 运维" 等，少了 "跨平台"） | P1 |
| 设计缺陷 | 系统提示词中的类型列表（第 89 行）与 `TYPE_RULES` 不同（少了 "Web 前端"、"移动端 App"、"桌面 GUI"、"CLI / 终端"、"游戏" 等） | P1 |
| 设计缺陷 | `xiaomimimo` 预设的 `provider` 为 `"openai"`（第 34、39、44 行），但 API 基址是 `xiaomimimo`， provider 名应一致 | P2 |

**改进建议**：
1. 系统提示词中的枚举应动态从 `config_rules.py` 生成，避免与规则不同步
2. 移除废弃的 `"enabled"` 字段
3. 统一 `xiaomimimo` 的 provider 名称

---

## 6. model_profiles.py — 模型画像

**模块职责**：各 LLM 模型的参数配置。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `ModelProfile` 字段过多（15 个），部分字段（如 `price_cny_per_1m_output`）仅用于排序推荐，与分类核心逻辑无关 | P2 |
| 设计缺陷 | `recommend_model()` 的评分函数（第 306-315 行）魔法数字（50、20、10）无解释 | P2 |
| 类型注解 | `get_profile()` 返回 `Optional[ModelProfile]`，但调用者（如 `LLMClient`）经常不检查 `None` | P2 |
| 设计缺陷 | `PRESET_DEFAULT_MODELS` 与 `config_llm.PROVIDER_PRESETS` 中的 model 字段重复定义 | P2 |
| 设计缺陷 | `no_system_role` 字段名与实际语义（`system_prompt_mode` 中的 `"no_system_role"`）不完全对应 | P3 |

**改进建议**：
1. 将价格/推荐相关字段提取到独立的 `ModelRecommendation` 类
2. 评分函数的权重参数化
3. `PRESET_DEFAULT_MODELS` 与 `config_llm` 统一单一来源

---

## 7. llm_classifier.py — LLM 分类器 Facade

**模块职责**：LLM 调用的 Facade，批量/单条分类 + 缓存。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `classify_batch()` 重构后约 80 行，仍偏长 | P2 |
| 类型注解 | `classify_batch()` 参数 `items` 无类型注解；`fallback=False` 的布尔语义不够自解释 | P2 |
| 导入结构 | 第 86 行 `from config import LLM_CONFIG` 在函数内导入 | P2 |
| 设计缺陷 | `_make_cache_key()` 第 257-260 行处理 `owner` 可能是 dict 或 str 的逻辑，说明上游数据格式不统一 | P1 |
| 设计缺陷 | 第 136 行 `max_workers = 1 if self.batch_size >= 8 else 2` 的魔法数字，无配置化 | P2 |
| 设计缺陷 | `_classify_batch()` 中 `readme_max` 从 `LLM_CONFIG` 读取，但属于业务参数而非 API 参数 | P2 |
| 设计缺陷 | `classify()` 和 `classify_batch()` 的缓存键生成逻辑略有不同（后者通过 `key = f"..."` 直接构造），不一致 | P2 |

**改进建议**：
1. 将 `batch_size >= 8` 阈值配置化
2. 统一上游数据格式，消除 `owner` 的 dict/str 双重兼容
3. `readme_max` 移至 `ModelProfile` 或独立的 prompt 配置
4. 缓存键生成提取为统一方法

---

## 8. llm/client.py — LLM 统一客户端

**模块职责**：封装 API 调用、重试、模型参数管理。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `call()` 38 行，`_build_feedback_context()` 36 行，均偏长 | P1 |
| 嵌套深度 | `_build_feedback_context()` 中 4 层嵌套（try → with → for → if） | P1 |
| 导入结构 | 第 106 行 `from config import LLM_CONFIG, LLM_SYSTEM_PROMPT` 在方法内导入 | P2 |
| 导入结构 | 第 67-68 行 `import os` / `import json` 在方法内导入 | P2 |
| 设计缺陷 | `_build_feedback_context()` 直接读取文件系统（`feedback.json`），在每次 LLM 调用时执行，I/O 开销大 | P1 |
| 设计缺陷 | `call()` 中重试逻辑（3 次指数退避）与 `OpenAICompatibleProvider.call()` 中的重试逻辑（3 次）叠加，最多 9 次重试 | P1 |
| 设计缺陷 | 反馈上下文拼接使用字符串 `+`，每次调用都重新构建完整系统提示词 | P2 |
| 设计缺陷 | `no_system_role` 模式下将 system + user 合并为单条 user message，但 `content` 格式未标准化 | P2 |

**改进建议**：
1. 缓存反馈上下文，避免每次调用都读文件
2. 统一重试逻辑：LLMClient 负责重试，Provider 只负责原始调用
3. 使用 `io.StringIO` 或列表 `join` 替代字符串拼接
4. 反馈上下文改为懒加载 + TTL 刷新

---

## 9. llm/cache.py — TTL 缓存

**模块职责**：基于文件的 LLM 结果缓存。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `get()` 中过期检查触发 `_save()`（第 55 行 `self._data.pop(key, None)` 后未保存，但第 54 行已删除），但 `set()` 每次都写文件，I/O 频繁 | P1 |
| 设计缺陷 | `_save()` 在 `set()` 时同步写文件，批量分类时频繁 I/O | P1 |
| 设计缺陷 | 无缓存版本校验：当规则变更时，旧缓存结果可能仍被使用 | P1 |
| 设计缺陷 | 缓存文件路径 `.llm_cache.json` 使用相对路径，取决于运行时 CWD | P2 |

**改进建议**：
1. 批量操作时使用内存缓冲，最后统一 `save()`
2. 添加缓存版本校验（如基于 `RULES_VERSION` 的缓存失效）
3. 使用绝对路径或基于 `db_path` 的相对路径

---

## 10. llm/parser.py — 响应解析器

**模块职责**：从 LLM 原始响应中提取结构化分类结果。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `extract_json_from_text()` 中多个正则 + 字符串查找，逻辑复杂，边界情况多 | P1 |
| 设计缺陷 | `parse_single()` 和 `parse_batch()` 中 `json.loads` 异常后直接抛 `ValueError`，未保留原始响应用于调试 | P1 |
| 设计缺陷 | `_extract_fields()` 中 `ai_tags` 和 `ai_platforms` 的类型检查重复（`isinstance(..., list)`） | P2 |
| 设计缺陷 | `extract_json_from_text()` 的排序逻辑 `candidates.sort(key=lambda x: (len(x), x.startswith("[")), reverse=True)` 偏好最长匹配，但不一定是最准确的 | P2 |

**改进建议**：
1. 异常时记录原始响应的前 N 个字符到日志
2. 使用更鲁棒的 JSON 提取策略（如 `json5` 库或专用的 Markdown JSON 提取器）
3. 为 `extract_json_from_text()` 添加单元测试覆盖更多边界情况

---

## 11. llm/providers/base.py / openai_compatible.py — Provider 层

**模块职责**：LLM 提供商抽象与 OpenAI 兼容实现。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `LLMProvider` 抽象基类只有两个方法，但 `OpenAICompatibleProvider` 实现了 8 个逻辑，抽象不够 | P2 |
| 设计缺陷 | `OpenAICompatibleProvider.call()` 49 行，过长 | P1 |
| 设计缺陷 | `call()` 中重试逻辑（第 45-68 行）与 `LLMClient.call()` 中的重试逻辑重复 | P1 |
| 设计缺陷 | `_extract_content()` 中硬编码的字段名（`content`, `reasoning_content`, `reasoning`）是厂商特定知识，应配置化 | P2 |
| 设计缺陷 | OpenRouter 的特殊 header 处理（第 32-34 行）硬编码在通用 Provider 中 | P2 |
| 安全性 | API Key 通过 `Authorization: Bearer` 头部传输，标准做法，无泄漏风险 | ✅ 安全 |

**改进建议**：
1. 将重试逻辑提取到中间件/装饰器，Provider 只负责原始 HTTP 调用
2. 响应提取字段配置化（如 `response_content_paths = ["choices.0.message.content", ...]`）
3. OpenRouter 特殊处理提取为子类 `OpenRouterProvider`

---

## 12. feedback_loop.py — 反馈闭环

**模块职责**：记录人工修正、统计模式、生成规则补丁、检测冲突。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `scan_manual_overrides()` 重构后约 55 行，`detect_override_conflicts()` 58 行，`generate_conflict_report()` 56 行 | P1 |
| 嵌套深度 | `scan_manual_overrides()` 中多层条件嵌套（item → manual_override → version → has_new_changes） | P1 |
| 重复代码 | `scan_manual_overrides()` 和 `detect_override_conflicts()` 都调用 `rule.classify_platform`/`classify_type`/`classify_ecology`，约 8 行重复 | P1 |
| 类型注解 | `patterns` 字段类型 `dict[str, dict]` 过于宽泛 | P2 |
| 设计缺陷 | `_extract_features_from_evidence()` 中 `re.findall` 的正则 `[a-zA-Z一-鿿]` 中文字符范围不精确（鿿是 U+9FFF，但中文实际到 U+9FA5） | P2 |
| 设计缺陷 | `generate_learned_overrides()` 生成的 `topic_blacklist` 等列表无去重，可能包含重复项 | P2 |
| 设计缺陷 | `load()` 中 `self.rules_version = ""` 在 4 个分支重复赋值 | P3 |
| 设计缺陷 | `patterns` 的嵌套更新逻辑（第 124-130 行）可用 `collections.defaultdict` 简化 | P2 |
| 安全性 | `write_learned_rules_file()` 已改用 `json.dump`，消除了之前字符串替换的脆弱性 | ✅ 已改进 |

**改进建议**：
1. 提取 `_get_rule_classification()` 为通用函数（已在 `_get_rule_classification` 静态方法中部分实现，但调用处仍有重复）
2. 使用 `defaultdict` 简化 patterns 更新
3. 修正中文字符正则范围为 `[一-龥]`
4. `load()` 中的重复赋值提取为方法末尾的统一处理

---

## 13. ecologies/__init__.py — 生态规则包

**模块职责**：生态规则自动注册与加载。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `importlib.import_module` 在模块加载时执行，如果某个生态模块有语法错误，会导致整个包导入失败 | P1 |
| 设计缺陷 | 无生态规则冲突检测：两个模块可能注册同名生态，后者静默覆盖前者 | P1 |
| 设计缺陷 | 模块导入顺序依赖文件系统排序（`sorted(os.listdir)`），不稳定 | P2 |
| 设计缺陷 | `ECOLOGY_RULES` 和 `ECOLOGY_REGISTRY` 是同一个 dict 的副本，修改其中一个不会影响另一个 | P2 |

**改进建议**：
1. 添加导入异常捕获和日志，单个模块失败不影响整体
2. 注册同名生态时发出警告或报错
3. 使用 `importlib.metadata` 或显式排序替代文件系统排序
4. 移除 `ECOLOGY_REGISTRY` 的冗余副本，直接导出 `ECOLOGY_RULES`

---

## 批次 2 总体评价

### 算法设计

**优点**：
1. **规则分类器纯函数化**：`RuleClassifier` 全静态方法，无状态，易于测试
2. **ItemFeatures 提取**：将 `name`/`desc`/`topics` 一次性提取，消除多处重复计算
3. **策略模式重构**：`classify_ecology()` 将评分逻辑提取为独立方法，可测试性提升
4. **LLM 分层清晰**：Client → Provider → Parser → Cache 四层分离良好

**缺陷**：
1. **规则与提示词不同步**：`config_rules.py` 与 `config_llm.LLM_SYSTEM_PROMPT` 中的枚举不一致
2. **缓存无版本校验**：规则变更后旧缓存仍有效
3. **重试逻辑重复**：Client 和 Provider 各有一层重试，可能过度重试
4. **反馈上下文 I/O 频繁**：每次 LLM 调用都读文件

### 优先级汇总

| 优先级 | 数量 | 关键问题 |
|--------|------|----------|
| P0 | 0 | — |
| P1 | 18 | 引擎条件分支复杂、重试叠加、缓存无版本、反馈 I/O、解析鲁棒性 |
| P2 | 20 | 规则不同步、类型注解、导入结构、魔法数字、字符范围 |
