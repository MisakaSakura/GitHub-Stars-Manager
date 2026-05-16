# 批次 1：核心架构与数据流审查

**审查范围**：入口 (classifier.py)、编排器 (orchestrator/)、数据模型 (models.py)、数据库层 (database.py / ai_database.py)、存储抽象 (repositories/)
**审查日期**：2026-05-17

---

## 1. classifier.py — CLI 入口

**模块职责**：参数解析 + 预设应用 + 模式映射 + 快捷修正命令。职责边界清晰。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 函数长度 | `parse_args()` 111 行，过长 | P1 |
| 函数长度 | `_do_correct()` 内嵌 `_correct_one()` 47 行，过长 | P1 |
| 嵌套深度 | `_correct_one()` 内多层条件判断，认知负荷高 | P1 |
| 导入结构 | 多处 `import` 散落在函数内部（如 `config_llm` 函数内导入），非顶层导入 | P1 |
| 类型注解 | `parse_args` 返回 `argparse.Namespace`，后续 `_apply_preset` 等直接修改属性，类型不安全 | P2 |
| 设计缺陷 | `CorrectCommand` 同时负责单条修正、批量修正、反馈记录、规则生成，违反 SRP | P1 |
| 设计缺陷 | 第 382 行使用 emoji `❌` 在 Windows 编码环境下可能出问题 | P2 |
| 设计缺陷 | `_parse_env_presets()` 中 `env` 变量名过于宽泛 | P2 |
| 设计缺陷 | `_apply_preset` 打印到 stdout 而非 log，与工具其余部分不一致 | P2 |

**改进建议**：
1. 将 `parse_args()` 拆分为子函数（基础参数 / 运行模式 / LLM / 通知等）
2. 将 `CorrectCommand` 提取为独立模块 `scripts/commands/correct.py`
3. 将函数内 `import` 移到文件顶部
4. 使用 `TypedDict` 或 `dataclass` 包装 `argparse.Namespace`，取代运行时属性修改

---

## 2. orchestrator/new_pipeline.py — Pipeline 编排

**模块职责**：阶段注册和依赖声明。非常薄，职责单一。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | 类名 `Pipeline` 与旧版同名，虽然旧版已移除，但导入路径相同，历史包袱 | P2 |
| 设计缺陷 | `_build_registry()` 中 16 个阶段全部硬编码导入，新增阶段需改两处（import + register） | P1 |
| 导入结构 | 第 23-38 行大量显式导入，虽不可避免但可考虑基于文件名的动态导入 | P2 |
| 设计缺陷 | `run()` 仅调用 `self.registry.run(self.context)`，无异常处理，异常由外层 `classifier.py main()` 捕获 | P2 |

**改进建议**：
1. 支持动态发现 stages/ 目录下的模块（如 `importlib.import_module`），减少注册样板代码
2. 或提供 `@stage("name", deps=[...])` 装饰器，让阶段模块自注册
3. 在 Pipeline 层面增加统一的异常包装和上下文清理

---

## 3. orchestrator/registry.py — 阶段注册器

**模块职责**：管理阶段注册和执行顺序。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | 依赖声明 `deps` 仅用于文档/阅读，未在 `run()` 中进行拓扑排序或验证 | P1 |
| 设计缺陷 | `StageFn = Callable[[Any], Any]` 类型过于宽泛，应使用 `Protocol` 或 `Callable[[PipelineContext], Any]` | P1 |
| 类型注解 | `run()` 参数 `context: Any` 应使用 `PipelineContext` | P1 |
| 设计缺陷 | `run()` 中 `result is True` 表示提前终止，布尔语义不够自解释 | P2 |
| 设计缺陷 | 阶段失败时 `raise` 异常，未提供失败后的回滚/清理机制 | P2 |

**改进建议**：
1. 实现依赖拓扑排序，运行前验证所有依赖是否满足
2. 定义 `StageResult` 枚举替代布尔返回值（`SUCCESS / SKIP / EARLY_EXIT / FAIL`）
3. 使用 `Callable[[PipelineContext], StageResult]` 替代 `Any`

---

## 4. orchestrator/context.py — 共享上下文

**模块职责**：流水线各阶段间的状态传递容器。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 类型注解 | `args: Any` 应为 `argparse.Namespace` | P1 |
| 类型注解 | 所有 `Optional[Any]` 字段（db, gh, llm 等）应使用具体类型 | P1 |
| 设计缺陷 | `get()`/`set()` 使用字符串键，无编译时检查，容易拼写错误 | P1 |
| 设计缺陷 | 上下文字段过多（20+），部分字段生命周期不明确（如 `star_changes` 仅 engine 使用） | P2 |
| 设计缺陷 | 无只读/写保护，任何阶段都可修改任何字段 | P2 |

**改进建议**：
1. 使用 `TypedDict` 或 `Protocol` 定义各阶段需要的上下文子集
2. 将阶段专用字段（如 `star_changes`, `ecology_candidate_summary`）移到对应阶段的返回结果中，而非全局上下文
3. 考虑使用 `@property` + `frozen` 提供只读视图

---

## 5. orchestrator/shared.py — 共享工具

**模块职责**：摘要文本构建工具函数。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `build_summary()` 和 `build_weekly_digest_text()` 直接访问 `ctx.db.values()`，依赖上下文字段结构，与 Context 耦合 | P2 |
| 设计缺陷 | 使用 emoji（🆕, 🔒, 📥, 🚀）直接输出，在 Windows 环境下可能编码问题 | P2 |
| 类型注解 | 参数 `ctx` 无类型注解 | P2 |

**改进建议**：
1. 接收具体数据参数而非整个 Context（如 `build_summary(db: Repository, stats: dict, ...)`）
2. 提供纯文本/emoji 两种输出模式，由调用者选择

---

## 6. models.py — 数据模型

**模块职责**：`StarItem` dataclass 定义。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | 模型臃肿（38 个字段），AI 相关字段（llm_status 等 6 个）已迁移但仍保留，导致序列化噪声 | P1 |
| 类型安全 | `first_seen: str` 和 `last_updated: str` 使用字符串而非 `datetime` | P2 |
| 类型注解 | `topics: List[str]` 使用 `List` 而非 `list[str]`（Python 3.9+） | P2 |
| 设计缺陷 | `from_dict()` 中 `known` 字段集合通过 `__dataclass_fields__` 反射获取，每次调用都计算，可缓存 | P2 |
| 设计缺陷 | `ecology_role` 默认值为 `"-"` 而非标准名称 `"其他 / Other"`，与其他字段默认值风格不一致 | P2 |
| 设计缺陷 | `LLMStatus` 枚举定义但 `llm_status` 字段类型为 `str` 而非 `LLMStatus` | P2 |

**改进建议**：
1. 将 AI 相关字段提取到独立的 `AIRecord` dataclass，实现零残留迁移
2. 使用 `datetime` 类型替代 `str` 时间字段
3. `ecology_role` 默认改为 `"其他 / Other"`，在序列化层处理为空的情况

---

## 7. database.py — 主数据库

**模块职责**：JSON 文件持久化 + 元数据管理。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 类型注解 | `get()` 返回 `StarItem | None`，但 `set()` 接受 `StarItem | dict`，调用者需防御式编程 | P1 |
| 设计缺陷 | `set()` 第 88-89 行自动将 dict 转为 `StarItem`，但 `get()` 可能返回 dict（如果直接访问 `self.data`），数据一致性风险 | P1 |
| 设计缺陷 | `set()` 第 91-93 行自动填充 `override_rules_version`，副作用与"设置"语义不符 | P1 |
| 设计缺陷 | `_serialize()` 是 `@staticmethod` 但引用 `StarsDB._AI_FIELDS`（类变量），应改为 `@classmethod` | P2 |
| 设计缺陷 | 元数据操作（`meta_get`/`meta_set`/`meta_save`）与主数据操作耦合在同一类中 | P2 |
| 设计缺陷 | `delete()` 方法缺失（Repository 接口要求，但 StarsDB 未实现） | P1 |
| 设计缺陷 | `items()` / `values()` 返回的是 `self.data` 的视图，调用者可能直接修改内部状态 | P2 |

**改进建议**：
1. `get()` 统一返回 `StarItem`，消除 dict 返回路径
2. 将元数据管理提取为 `MetaStore` 类
3. `set()` 的版本填充移到上层调用者（如 `CorrectCommand._correct_one()`）
4. 实现 `delete()` 方法

---

## 8. ai_database.py — AI 数据库

**模块职责**：AI 分析结果独立存储。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `update_from_llm_result()` 中大量 `llm_result.get(...)` 重复，可用 `**` 解包简化 | P2 |
| 类型注解 | `llm_status` 字段类型为 `str` 而非枚举 | P2 |
| 设计缺陷 | `migrate_from_stars_db()` 中大量使用 `hasattr`/`getattr` 双重兼容，说明上游数据不统一 | P1 |
| 设计缺陷 | `AIResult.from_dict()` 中 `__dataclass_fields__` 反射每次调用都计算 | P2 |
| 设计缺陷 | 无 `delete()` 方法 | P2 |

**改进建议**：
1. 统一上游数据类型，消除 `hasattr`/`getattr` 双重兼容
2. 使用 `dataclasses.fields()` 缓存已知字段集合

---

## 9. repositories/base.py — Repository 抽象

**模块职责**：存储后端抽象接口。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | 接口设计良好，但缺少 `close()` 方法（SQLite 后端需要） | P2 |
| 设计缺陷 | `set()` 签名接受 `Any` 类型的 value，无法约束为 `StarItem` | P2 |
| 设计缺陷 | `meta_save()` 与 `save()` 分离，调用者容易忘记调用 `meta_save()` | P2 |

**改进建议**：
1. 增加 `close()` 抽象方法
2. 使用泛型 `Repository[T]` 约束 value 类型

---

## 10. repositories/json_backend.py — JSON 适配器

**模块职责**：为 StarsDB / AIDatabase 提供 Repository 接口适配。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | 直接操作 `self._backend.data[key]` 绕过 `StarsDB.set()` 的校验逻辑 | P1 |
| 设计缺陷 | `JSONStarsRepository.delete()` 直接 `del self._backend.data[key]` 而非调用 `StarsDB` 方法 | P1 |
| 类型注解 | `get()` 返回 `Any | None`，实际应返回 `StarItem | None` | P2 |
| 设计缺陷 | `backend` 属性暴露底层 StarsDB，破坏封装 | P2 |
| 设计缺陷 | `JSONAIRepository` 的 `meta_get`/`meta_set`/`meta_save` 为空实现，语义不明确 | P2 |

**改进建议**：
1. `delete()` 应调用底层 `StarsDB` 的公开方法（如添加 `StarsDB.delete()`）
2. 移除 `backend` 属性，或通过 `typing.cast` 明确返回类型
3. `JSONAIRepository` 的 meta 操作应抛出 `NotImplementedError` 而非静默忽略

---

## 11. repositories/sqlite_backend.py — SQLite 实现

**模块职责**：SQLite 持久化实现。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `SCHEMA` 中 `stars` 表 24 个字段，新增字段需修改多处（SCHEMA + _row_to_item + _item_to_tuple + INSERT） | P1 |
| 设计缺陷 | `_item_to_tuple()` 与 INSERT 的 `?` 占位符数量需人工保持一致，容易遗漏 | P1 |
| 设计缺陷 | `_row_to_item()` 中所有字段都有 `or "默认"` 回退，这些回退应与 `StarItem` 的默认值单一来源 | P1 |
| 设计缺陷 | `topics` / `override_fields` 使用 JSON 字符串存储，查询时不利于索引 | P2 |
| 设计缺陷 | `ai_results` 表定义但从未使用（AI 数据存储在独立 JSON 文件中） | P2 |
| 设计缺陷 | `_ensure_schema()` 中 `ALTER TABLE` 放在构造函数中，每次连接都尝试执行 | P2 |
| 安全性 | 全部使用参数化查询（`?`），无 SQL 注入风险 | ✅ 安全 |

**改进建议**：
1. 使用反射或代码生成自动同步 `_row_to_item` / `_item_to_tuple` / SCHEMA
2. 将默认值集中定义在 `StarItem` 中，SQLite 层直接引用
3. 移除未使用的 `ai_results` 表，或提供迁移到独立 AI DB 的路径
4. 将 schema 迁移逻辑提取到独立的版本化管理器

---

## 12. repositories/migrate.py — 迁移脚本

**模块职责**：JSON → SQLite 数据迁移。

| 维度 | 问题 | 优先级 |
|------|------|--------|
| 设计缺陷 | `sys.path.insert(0, ...)` 修改全局路径，是临时方案 | P2 |
| 设计缺陷 | 第 37 行 `args.sqlite` 应为 `args.target`（参数名不一致） | P0 |
| 设计缺陷 | 无事务回滚机制，中途失败可能留下不完整数据 | P1 |

**改进建议**：
1. 修复 `args.sqlite` → `args.target`（当前会导致 AttributeError）
2. 使用 SQLite 事务包裹批量插入
3. 将脚本改为模块内可调用函数，避免 `sys.path` 操作

---

## 批次 1 总体评价

### 架构设计

**优点**：
1. **Pipeline 阶段化设计优秀**：`StageRegistry` + `PipelineContext` 实现插件化流水线，阶段间通过 Context 传递状态
2. **存储后端抽象**：JSON 和 SQLite 双后端支持，有迁移路径
3. **AI 数据分离**：将 LLM 元数据从主数据库分离到 `stars_ai.json`，避免主库膨胀

**缺陷**：
1. **Context 过于宽泛**：`Any` 类型 + 字符串键访问，无编译时检查
2. **数据模型双重性**：`StarItem` (dataclass) 和 `dict` 在多处混用（SQLite 后端返回 StarItem，但 JSON 后端可能返回 dict）
3. ** StarsDB 与 Repository 接口不对齐**：StarsDB 缺少 `delete()`，`meta_save()` 语义与 `save()` 分离

### 优先级汇总

| 优先级 | 数量 | 关键问题 |
|--------|------|----------|
| P0 | 1 | migrate.py `args.sqlite` 拼写错误 |
| P1 | 15 | Context 类型安全、Repository 接口不对齐、schema 同步、数据一致性 |
| P2 | 14 | emoji 编码、默认值来源不统一、AI 字段残留、反射性能 |
