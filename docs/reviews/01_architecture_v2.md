# 批次1审查报告：架构与数据层

## 审查范围

- `scripts/orchestrator/context.py`
- `scripts/orchestrator/registry.py`
- `scripts/orchestrator/new_pipeline.py`
- `scripts/orchestrator/shared.py`
- `scripts/orchestrator/stages/setup_stage.py`
- `scripts/orchestrator/stages/fetch_stage.py`
- `scripts/orchestrator/stages/classify_stage.py`
- `scripts/orchestrator/stages/import_stage.py`
- `scripts/orchestrator/stages/save_stage.py`
- `scripts/orchestrator/stages/sync_notion_stage.py`
- `scripts/orchestrator/stages/notify_stage.py`
- `scripts/orchestrator/stages/track_forks_stage.py`
- `scripts/orchestrator/stages/track_releases_stage.py`
- `scripts/orchestrator/stages/handle_lists_stage.py`
- `scripts/orchestrator/stages/check_consistency_stage.py`
- `scripts/orchestrator/stages/discover_ecologies_stage.py`
- `scripts/orchestrator/stages/reports_stage.py`
- `scripts/orchestrator/stages/record_feedback_stage.py`
- `scripts/models.py`
- `scripts/database.py`
- `scripts/repositories/base.py`
- `scripts/repositories/json_backend.py`
- `scripts/repositories/sqlite_backend.py`
- `scripts/repositories/migrate.py`

---

## P0 — 阻塞级（4项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P0-1 | `scripts/orchestrator/context.py` | 36-40 | `items: list[dict]` 与 `star_changes: dict[str, int]` 等字段使用 `dict` 泛型（Python 3.9+ 语法），但文件未声明 `from __future__ import annotations`，若项目需兼容 Python 3.8 将直接崩溃 | 运行时 SyntaxError（Python 3.8） | 添加 `from __future__ import annotations` 或改用 `Dict`、`List`、`Set` 等 typing 模块类型 |
| P0-2 | `scripts/orchestrator/stages/setup_stage.py` | 45 | `ctx.ai_db.migrate_from_stars_db(list(ctx.db.values()))` 在 `ctx.db` 为 `SQLiteStarsRepository` 时，`values()` 返回的是惰性迭代器而非列表，`list()` 包裹正确，但 `SQLiteStarsRepository.values()` 返回 `Iterator[StarItem]`，而 `migrate_from_stars_db` 参数类型为 `list`，内部通过 `hasattr(item, "full_name")` 判断是对象还是 dict。更严重的是：当 `ctx.db` 为 `StarsDB`（JSON 后端）时，`values()` 返回 `dict_values`，`list()` 转换后元素是 `StarItem`；但 `SQLiteStarsRepository.values()` 是生成器，消费一次后不可复用。此处 `list()` 已消费，无直接 bug，但 `migrate_from_stars_db` 的签名应改为 `Iterable` | 类型契约模糊，后续修改可能引入 bug | 将 `migrate_from_stars_db` 参数类型改为 `Iterable[StarItem \| dict]` |
| P0-3 | `scripts/orchestrator/stages/classify_stage.py` | 96-99 | `ctx.engine.llm_results` 访问在 `ctx.engine` 可能为 `None` 时（虽然前面已创建），但 `llm_results` 属性是否存在取决于 `IncrementalEngine` 的实现。如果 `process()` 内部异常或返回的引擎对象未设置该属性，将导致 `AttributeError` | 运行时 AttributeError | 添加 `hasattr(ctx.engine, 'llm_results')` 检查，或使用 `getattr(ctx.engine, 'llm_results', {})` |
| P0-4 | `scripts/repositories/sqlite_backend.py` | 141 | `ALTER TABLE stars ADD COLUMN {col_name} {col_def}` 使用字符串拼接构造 SQL，虽然 `col_name` 和 `col_def` 来自内部常量 `SCHEMA_TABLES`，但如果未来从外部输入引入列名，存在 SQL 注入风险。当前 `_parse_schema_columns` 未对列名做任何验证 | 潜在的 SQL 注入（当前风险低，但架构上不安全） | 添加列名白名单验证，仅允许已知列名通过 |

---

## P1 — 重要（18项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P1-1 | `scripts/orchestrator/registry.py` | 55-70 | `run()` 方法中阶段失败时 `log` 后 `raise`，但异常未携带上下文（哪个阶段、什么参数），调用方难以定位问题 | 错误排查困难 | 自定义 `PipelineStageError` 异常类，包含阶段名、原始异常、上下文快照 |
| P1-2 | `scripts/orchestrator/registry.py` | 64-67 | 阶段返回 `True` 时提前终止，但已执行的阶段副作用（如数据库修改）不会回滚，缺乏事务语义 | 部分执行后中断可能导致数据不一致 | 文档化此行为，或考虑两阶段提交模式（先准备再确认） |
| P1-3 | `scripts/orchestrator/new_pipeline.py` | 44-50 | `_build_registry()` 使用 `importlib.import_module` 动态导入，如果模块不存在或函数不存在，异常信息不友好（`AttributeError: module has no attribute 'xxx'`） | 调试困难 | 包装导入异常，提供清晰的阶段注册失败信息 |
| P1-4 | `scripts/orchestrator/context.py` | 52-56 | `get()`/`set()` 使用 `getattr`/`setattr`，无类型安全，IDE 无法推断，且访问不存在的属性时静默返回 `default` | 类型信息丢失、隐藏拼写错误 | 为常用属性提供显式 typed property，或弃用 `get`/`set` 改为直接访问 |
| P1-5 | `scripts/orchestrator/stages/setup_stage.py` | 33-38 | SQLite 后端选择逻辑硬编码 `.json` 替换为 `.db`，如果用户传入的路径不含 `.json` 后缀（如 `.db.json` 或自定义扩展），替换结果不符合预期 | 路径解析错误 | 使用 `os.path.splitext` 正确处理多层扩展名，或要求显式传入 SQLite 路径 |
| P1-6 | `scripts/orchestrator/stages/setup_stage.py` | 37-38 | `migrate_from_json` 在首次运行且旧 JSON 存在时自动迁移，但迁移后未删除旧 JSON 文件，可能导致用户误以为数据仍在 JSON 中 | 数据重复、用户困惑 | 迁移成功后删除或重命名旧 JSON 文件，并记录日志 |
| P1-7 | `scripts/orchestrator/stages/classify_stage.py` | 46-49 | `needs_llm` 调用时 `key` 构造在循环内重复，且 `existing = ctx.db.get(key)` 对每个 item 都查一次数据库，如果 `ctx.db` 是 SQLite 后端，这是 N+1 查询 | 性能下降（大量项目时明显） | 预加载所有 existing 记录到字典，批量判断 |
| P1-8 | `scripts/orchestrator/stages/classify_stage.py` | 53-59 | README 获取使用 `try/except Exception: pass` 吞没所有异常，包括网络超时、认证失败等，无法区分问题 | 错误被静默吞没，难以排查 | 至少区分 `GitHubAuthError`、`GitHubRateLimitError` 和一般异常，分别记录日志 |
| P1-9 | `scripts/orchestrator/stages/track_releases_stage.py` | 20-25 | `_save_release_history` 读取历史文件时 `except Exception: existing = []` 吞没所有异常，包括 JSON 解析错误、权限错误等 | 数据丢失风险（如文件损坏时静默重置为空列表） | 区分异常类型：JSON 解析错误记录警告并备份旧文件；权限错误直接抛出 |
| P1-10 | `scripts/orchestrator/stages/discover_ecologies_stage.py` | 108-123 | LLM 审查结果解析使用 `re.search(r'\{[^}]+\}', result)`，此正则无法匹配嵌套 JSON 对象（如包含 `}` 的字符串值），会导致解析失败 | 复杂 JSON 响应解析失败 | 使用 `json.loads` 配合 `extract_json` 辅助函数，或要求 LLM 严格输出 JSON |
| P1-11 | `scripts/orchestrator/stages/discover_ecologies_stage.py` | 109 | `max_tokens = ctx.llm.profile.get_max_tokens(...)` 假设 `ctx.llm` 一定有 `profile` 属性，但 `LLMClassifier` 可能未设置该属性 | AttributeError | 使用 `getattr(ctx.llm, 'profile', None)` 安全访问 |
| P1-12 | `scripts/orchestrator/stages/check_consistency_stage.py` | 28 | `out_path = os.path.join(ctx.args.output, "consistency_report.md")` 假设 `ctx.args.output` 一定存在，但 `PipelineContext` 中 `output_dir` 默认值为 `"./docs"`，而 `ctx.args.output` 可能未定义 | AttributeError | 使用 `getattr(ctx.args, 'output', ctx.output_dir)` 提供默认值 |
| P1-13 | `scripts/orchestrator/stages/notify_stage.py` | 18 | `ctx.args.notify_channels.split(",")` 假设 `notify_channels` 属性一定存在且为字符串，若未设置则为 `None`，调用 `split` 将抛出 `AttributeError` | 运行时崩溃 | 使用 `getattr(ctx.args, 'notify_channels', '')` 提供默认值 |
| P1-14 | `scripts/models.py` | 74-76 | `to_dict()` 使用 `asdict(self)` 会深拷贝所有字段，对于大列表（topics 等）有性能开销，且会暴露内部可变状态 | 性能开销、外部可修改内部状态 | 返回 `asdict(self)` 的浅拷贝，或改用 `dataclasses.fields` 手动构建字典 |
| P1-15 | `scripts/database.py` | 92-95 | `set()` 方法接受 `StarItem | dict`，但仅在 `dict` 包含特定键时才转换，如果传入的 `dict` 缺少键则直接存入，后续 `save()` 时 `_serialize` 调用 `item.to_dict()` 会失败 | 数据类型不一致导致序列化错误 | 严格类型检查：非 `StarItem` 且非完整 `dict` 时抛出 `TypeError` |
| P1-16 | `scripts/repositories/sqlite_backend.py` | 104-105 | `sqlite3.connect(db_path)` 未设置 `check_same_thread=False`，在多线程环境（如 Web 服务）中会抛出异常 | 多线程使用受限 | 添加 `check_same_thread=False` 参数，或文档说明仅支持单线程 |
| P1-17 | `scripts/repositories/sqlite_backend.py` | 200-219 | `set()` 方法中 `INSERT INTO stars VALUES (...)` 未指定列名，依赖列顺序与 `_item_to_tuple` 完全一致。如果 schema 变更（如新增列），此语句会失败 | schema 变更后插入失败 | 显式指定列名：`INSERT INTO stars (col1, col2, ...) VALUES (...)` |
| P1-18 | `scripts/repositories/sqlite_backend.py` | 264-285 | `migrate_from_json` 与 `JSONStarsRepository` 的适配逻辑重复，且未处理 `last_release_checked` 等 schema 中未定义的字段（schema 中无此列，但 `StarItem` 有） | 数据丢失（迁移时忽略部分字段） | 同步 schema 与 `StarItem` 字段定义，确保所有字段都有对应列 |

---

## P2 — 建议（22项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P2-1 | `scripts/orchestrator/registry.py` | 39-53 | `visit()` 函数嵌套在 `_validate_deps` 内，且使用闭包访问外部变量，可读性较差 | 可维护性降低 | 将拓扑排序提取为独立方法或工具函数 |
| P2-2 | `scripts/orchestrator/registry.py` | 55 | `skip: set[str] | None = None` 参数类型正确，但默认值 `None` 后未立即处理为 `set()`，而是在方法内第57行处理，符合规范但可简化 | 微小 | 使用 `skip: set[str] = None` 后 `skip = skip or set()` 即可 |
| P2-3 | `scripts/orchestrator/new_pipeline.py` | 24-43 | `_STAGE_REGISTRY` 硬编码18个阶段的元组列表，新增阶段需要修改此处和新增文件，容易遗漏 | 扩展性受限 | 考虑使用 `__init__.py` 中的 `__all__` 自动发现，或文件命名约定自动注册 |
| P2-4 | `scripts/orchestrator/context.py` | 20-50 | `PipelineContext` 包含20+个字段，部分字段（如 `output_dir`）与 `ctx.args` 中对应字段重复 | 数据冗余、状态不一致风险 | 统一从 `args` 获取配置，或明确区分运行时状态与配置 |
| P2-5 | `scripts/orchestrator/shared.py` | 16-17 | `build_summary` 中使用 emoji（`\U0001f195`），在部分终端可能显示为方框 | 显示问题 | 已通过 `_safe_print` 处理，但摘要文本本身含 emoji，建议提供纯文本版本 |
| P2-6 | `scripts/orchestrator/shared.py` | 30-32 | `eco_stats.most_common(5)` 每次调用都遍历整个数据库，如果项目数很大有性能开销 | 性能（微小） | 预计算或在数据库层聚合 |
| P2-7 | `scripts/orchestrator/stages/setup_stage.py` | 14-44 | 函数长度30行，功能混合（检测首次运行、打印横幅、选择存储后端、初始化 AI DB） | SRP 违反 | 拆分为 `_detect_first_run`、`_select_backend`、`_init_ai_db` 三个子函数 |
| P2-8 | `scripts/orchestrator/stages/classify_stage.py` | 63-99 | `classify_stage` 函数过长（36行），混合了规则刷新、订阅标记、刷新判断、引擎创建、结果处理 | 可维护性 | 拆分为 `_prepare_engine`、`_run_classification`、`_save_llm_results` |
| P2-9 | `scripts/orchestrator/stages/discover_ecologies_stage.py` | 78-123 | `_llm_review_watchlist` 函数过长（45行），嵌套在模块级别但逻辑独立 | 可维护性 | 提取为独立模块或类 |
| P2-10 | `scripts/orchestrator/stages/discover_ecologies_stage.py` | 103-106 | prompt 字符串使用三引号内联，包含格式化占位符，难以维护 | 可读性 | 使用模板文件或 `string.Template` |
| P2-11 | `scripts/orchestrator/stages/reports_stage.py` | 12-70 | `_generate_ai_summary` 函数过长（58行），混合了规则生成和 LLM 生成逻辑 | 可维护性 | 拆分为 `_build_summary_data`、`_generate_with_llm`、`_fallback_summary` |
| P2-12 | `scripts/orchestrator/stages/reports_stage.py` | 80 | `new_items = [ctx.db.get(k).to_dict() for k in ctx.new_keys if ctx.db.get(k)]` 对同一 key 调用 `get` 两次 | 性能（微小） | 使用临时变量：`item = ctx.db.get(k); return item.to_dict() if item else None` |
| P2-13 | `scripts/orchestrator/stages/record_feedback_stage.py` | 12-51 | 函数混合了扫描、生成规则、检测冲突、生成报告四个职责 | SRP 违反 | 拆分为四个独立函数，由 stage 函数编排 |
| P2-14 | `scripts/models.py` | 27-28 | `language` 和 `platform` 默认值使用中文（"文档 / 无代码"、"其他 / 未分类"），与代码其他部分混用中英文 | 一致性 | 统一使用英文内部表示，仅在展示层翻译 |
| P2-15 | `scripts/models.py` | 40-46 | AI 相关字段标记为"向后兼容"，但已迁移到独立数据库，应设置 deprecation 警告或计划移除 | 技术债务 | 添加 `warnings.warn` 在访问这些字段时提示弃用 |
| P2-16 | `scripts/database.py` | 66-68 | 数据库损坏时重建（`self.data = {}`），但会丢失所有历史数据，无备份机制 | 数据丢失风险 | 损坏时将旧文件重命名为 `.bak` 后再重建 |
| P2-17 | `scripts/database.py` | 110-117 | `_AI_FIELDS` 硬编码 AI 字段列表，与 `models.py` 中 `StarItem` 定义重复 | DRY 违反 | 从 `StarItem` 的 `__dataclass_fields__` 动态推导，或共享常量 |
| P2-18 | `scripts/repositories/base.py` | 12-63 | `Repository` 抽象基类未定义 `close()` 方法，但 `SQLiteStarsRepository` 实现了它，`JSONStarsRepository` 没有 | 接口不一致 | 在基类中添加 `close()` 抽象方法，所有实现统一 |
| P2-19 | `scripts/repositories/json_backend.py` | 54-57 | `backend` property 注释说"后续移除"，但代码中仍在使用（如 `setup_stage.py` 通过 `ctx.db` 直接访问底层） | 技术债务 | 移除 `backend` property，确保所有访问通过 Repository 接口 |
| P2-20 | `scripts/repositories/json_backend.py` | 66-76 | `JSONAIRepository.delete()` 直接操作 `self._backend.data`，绕过 `AIDatabase` 的封装 | 封装破坏 | 使用 `self._backend.set(key, None)` 或要求 `AIDatabase` 提供 `delete` 方法 |
| P2-21 | `scripts/repositories/migrate.py` | 13 | `sys.path.insert(0, ...)` 修改全局 `sys.path`，影响其他模块导入 | 副作用 | 使用相对导入或将脚本改为 `python -m` 方式运行 |
| P2-22 | `scripts/repositories/migrate.py` | 22-23 | `repo.close()` 在成功迁移后调用，但如果迁移过程中异常，`repo` 可能未正确关闭 | 资源泄漏 | 使用 `with` 语句或 `try/finally` 确保关闭 |

---

## 按模块汇总

| 模块 | P0 | P1 | P2 | 关键问题 |
|------|-----|-----|-----|----------|
| `orchestrator/context.py` | 1 | 1 | 1 | Python 3.8 兼容性（dict 泛型）、get/set 无类型安全 |
| `orchestrator/registry.py` | 0 | 2 | 1 | 异常上下文缺失、缺乏事务语义 |
| `orchestrator/new_pipeline.py` | 0 | 1 | 1 | 动态导入异常信息不友好、硬编码阶段列表 |
| `orchestrator/shared.py` | 0 | 0 | 2 | emoji 显示、重复遍历 |
| `orchestrator/stages/setup_stage.py` | 1 | 2 | 1 | 路径硬编码替换、迁移后未清理旧文件、函数过长 |
| `orchestrator/stages/fetch_stage.py` | 0 | 0 | 0 | 简洁，无问题 |
| `orchestrator/stages/classify_stage.py` | 1 | 2 | 1 | N+1查询、异常吞没、llm_results 属性安全访问 |
| `orchestrator/stages/import_stage.py` | 0 | 0 | 0 | 简洁，无问题 |
| `orchestrator/stages/save_stage.py` | 0 | 0 | 0 | 简洁，无问题 |
| `orchestrator/stages/sync_notion_stage.py` | 0 | 0 | 0 | 简洁，无问题 |
| `orchestrator/stages/notify_stage.py` | 0 | 1 | 0 | notify_channels 属性可能不存在 |
| `orchestrator/stages/track_forks_stage.py` | 0 | 0 | 0 | 简洁，无问题 |
| `orchestrator/stages/track_releases_stage.py` | 0 | 1 | 0 | 异常吞没导致数据丢失风险 |
| `orchestrator/stages/handle_lists_stage.py` | 0 | 0 | 0 | 简洁，无问题 |
| `orchestrator/stages/check_consistency_stage.py` | 0 | 1 | 0 | ctx.args.output 可能不存在 |
| `orchestrator/stages/discover_ecologies_stage.py` | 0 | 2 | 2 | JSON 解析正则缺陷、profile 属性安全访问、函数过长 |
| `orchestrator/stages/reports_stage.py` | 0 | 0 | 2 | 函数过长、重复 get 调用 |
| `orchestrator/stages/record_feedback_stage.py` | 0 | 0 | 1 | 函数职责过多 |
| `models.py` | 0 | 1 | 2 | to_dict 深拷贝开销、AI 字段技术债务 |
| `database.py` | 0 | 1 | 2 | set() 类型检查不严、数据损坏无备份、AI 字段重复定义 |
| `repositories/base.py` | 0 | 0 | 1 | 缺少 close() 抽象方法 |
| `repositories/json_backend.py` | 0 | 0 | 2 | backend property 技术债务、delete 封装破坏 |
| `repositories/sqlite_backend.py` | 1 | 3 | 0 | SQL 注入风险（架构层面）、多线程限制、INSERT 未指定列名、schema 与模型不同步 |
| `repositories/migrate.py` | 0 | 0 | 2 | sys.path 副作用、资源泄漏 |
| **合计** | **4** | **18** | **22** | |

---

## 关键问题总结

### 最高优先级（P0）

1. **Python 3.8 兼容性**：`context.py` 使用 `list[dict]`、`dict[str, int]` 等 Python 3.9+ 泛型语法，未添加 `from __future__ import annotations`，在 Python 3.8 下直接 SyntaxError。

2. **SQLite 后端 schema 同步**：`sqlite_backend.py` 的 `stars` 表缺少 `last_release_checked` 列（`StarItem` 有定义），导致迁移时数据丢失。同时 `INSERT` 未指定列名，schema 变更后必崩。

3. **属性访问不安全**：`classify_stage.py` 中 `ctx.engine.llm_results` 和 `discover_ecologies_stage.py` 中 `ctx.llm.profile` 均假设属性一定存在，缺乏防御性编程。

### 架构层面（P1）

1. **Repository 接口不完整**：`base.py` 缺少 `close()` 方法，导致 `SQLiteStarsRepository` 的资源释放无统一契约。

2. **Pipeline 缺乏事务语义**：`registry.py` 的阶段提前终止不会回滚已执行阶段的副作用，在数据库修改后中断可能导致不一致状态。

3. **N+1 查询**：`classify_stage.py` 的 `enrich_stage` 对每个项目单独查询数据库判断是否需要 LLM，SQLite 后端下性能显著下降。

4. **异常吞没模式**：多个 stage 使用 `except Exception: pass` 或类似模式，隐藏了真正的错误信息。
