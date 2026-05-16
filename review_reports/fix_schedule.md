# P0/P1 问题修复排期计划

**制定日期**：2026-05-17  
**总问题数**：1 P0 + 55 P1 = 56 项  
**排期周期**：5 个批次，约 3-4 周完成全部 P0+P1

---

## 批次 1：紧急修复（Week 1）— 6 项

**目标**：P0 + 影响可用性/安全性的核心问题

| # | 原编号 | 文件 | 问题 | 预计工作量 |
|---|--------|------|------|-----------|
| 1 | P0-1 | `repositories/migrate.py` | `args.sqlite` → `args.target` | 1 行 |
| 2 | P1-11 | `database.py` | 实现 `delete()` 方法 | 5 行 |
| 3 | P1-12 | `repositories/json_backend.py` | 修复 `delete()` 绕过 StarsDB | 5 行 |
| 4 | P1-28 | `stages/auth_stage.py` | `sys.exit()` → 抛出异常 | 5 行 |
| 5 | P1-54 | `.github/workflows/process-feedback.yml` | `::set-output` → `$GITHUB_OUTPUT` | 3 行 |
| 6 | P1-50 | `.github/workflows/classify-stars.yml` | `ARGS` 数组传递修复 | 3 行 |

**完成标准**：P0 修复 + 6 项 P1 全部修改 + 测试通过

---

## 批次 2：数据流 + 引擎（Week 1）— 8 项

**目标**：消除引擎核心缺陷 + 统一数据模型

| # | 原编号 | 文件 | 问题 |
|---|--------|------|------|
| 7 | P1-16 | `engine.py` | 删除 `_needs_llm()` 冗余实例方法 |
| 8 | P1-17 | `engine.py` | `_apply_llm_override()` 改为返回变更字典 |
| 9 | P1-18 | `engine.py` | `_classify_item()` 参数传入 `existing` |
| 10 | P1-10 | `database.py` | `set()` 版本填充移到上层调用者 |
| 11 | P1-32 | `stages/check_consistency_stage.py` | dict/StarItem 统一为 StarItem |
| 12 | P1-33 | `stages/check_consistency_stage.py` | 区分 `auto_override` 与 `manual_override` |
| 13 | P1-43 | `tests/test_classifier.py` | `CUSTOM_PRESETS` 隔离（`copy.deepcopy`） |
| 14 | P1-44 | `tests/test_classifier.py` | `os.environ` 隔离（`mock.patch.dict`） |

**完成标准**：engine 测试全部通过 + check_consistency 测试通过 + 全局状态隔离

---

## 批次 3：LLM 层 + 分类器（Week 2）— 8 项

**目标**：消除重试叠加 + 缓存版本控制 + 提示词同步

| # | 原编号 | 文件 | 问题 |
|---|--------|------|------|
| 15 | P1-23 | `llm/client.py` | 统一重试到单层（移除 Provider 层重试） |
| 16 | P1-22 | `llm/client.py` | 缓存反馈上下文，TTL 刷新 |
| 17 | P1-24 | `llm/cache.py` | 基于 `RULES_VERSION` 的缓存失效 |
| 18 | P1-25 | `llm/cache.py` | 批量操作内存缓冲，最后统一 save |
| 19 | P1-19 | `rule_classifier.py` | 移除 `ast.literal_eval` 回退逻辑 |
| 20 | P1-20 | `config_llm.py` | 动态从 `config_rules.py` 生成系统提示词 |
| 21 | P1-21 | `llm_classifier.py` | 统一 `_make_cache_key()` 上游数据格式 |
| 22 | P1-46 | `tests/test_engine.py` | `LOCKED_ECOLOGIES` 隔离（patch） |

**完成标准**：LLM 相关测试通过 + 缓存 TTL/版本测试通过

---

## 批次 4：工具模块 + CI（Week 2-3）— 10 项

**目标**：修复工具模块核心缺陷 + 提升 CI 健壮性

| # | 原编号 | 文件 | 问题 |
|---|--------|------|------|
| 23 | P1-41 | `report.py` | `_build_html()` 拆分内嵌 HTML 为模板文件 |
| 24 | P1-42 | `report.py` | 替换字符串 `replace` 为模板占位符 |
| 25 | P1-37 | `github_api.py` | `fetch_all()` 拆分为子函数 |
| 26 | P1-38 | `github_api.py` | `get_readme()` 缓存提取为独立层 |
| 27 | P1-39 | `http_client.py` | 统一重试到单层 |
| 28 | P1-34 | `stages/discover_ecologies_stage.py` | 函数拆分为子函数 |
| 29 | P1-56 | `.github/workflows/process-feedback.yml` | 内联脚本提取为独立文件 |
| 30 | P1-55 | `.github/workflows/process-feedback.yml` | `override_fields` 动态设置 |
| 31 | P1-52 | `.github/workflows/classify-stars.yml` | custom 模式默认值与代码统一 |
| 32 | P1-53 | `.github/workflows/classify-stars.yml` | git rebase 冲突检测 |

**完成标准**：工具模块测试通过 + CI workflow 语法校验通过

---

## 批次 5：架构改进（Week 3-4）— 11 项

**目标**：类型安全 + Pipeline 依赖验证 + 数据模型清理

| # | 原编号 | 文件 | 问题 |
|---|--------|------|------|
| 33 | P1-7 | `orchestrator/context.py` | 替换 `Any` 为具体类型 |
| 34 | P1-5 | `orchestrator/registry.py` | `StageFn` 使用 `Protocol` |
| 35 | P1-6 | `orchestrator/registry.py` | 依赖拓扑排序和验证 |
| 36 | P1-4 | `orchestrator/new_pipeline.py` | 阶段动态发现 |
| 37 | P1-8 | `models.py` | 提取 `AIRecord` dataclass |
| 38 | P1-9 | `database.py` | `get()` 统一返回 `StarItem` |
| 39 | P1-13 | `repositories/sqlite_backend.py` | schema 自动同步 |
| 40 | P1-14 | `engine.py` | `process()` 参数包装为 dataclass |
| 41 | P1-15 | `engine.py` | `_process_single()` 策略对象 |
| 42 | P1-29 | `stages/classify_stage.py` | 自动全量刷新逻辑单一来源 |
| 43 | P1-51 | `.github/workflows/classify-stars.yml` | LLM 模式映射逻辑单一来源 |

**完成标准**：Pipeline 测试通过 + 类型检查通过 + 架构测试通过

---

## 批次 6：测试补强（Month 2）— 12 项

**目标**：提升测试覆盖率和质量

| # | 原编号 | 文件 | 问题 |
|---|--------|------|------|
| 44 | P1-47 | `test_new_pipeline.py` | 移除 `try/except/pass` 掩盖 |
| 45 | — | `test_new_pipeline.py` | 阶段依赖验证测试 |
| 46 | — | `test_new_pipeline.py` | 阶段失败异常传播测试 |
| 47 | P1-48 | `test_database.py` | `get()` 返回 dict 测试 |
| 48 | P1-48 | `test_database.py` | `set()` 自动版本填充测试 |
| 49 | P1-49 | `test_repositories.py` | SQLite 后端测试 |
| 50 | — | `tests/` | `CorrectCommand` 测试 |
| 51 | — | `tests/` | 阶段失败异常传播测试 |
| 52 | P1-30 | `stages/classify_stage.py` | `candidates[:50]` 参数化 |
| 53 | P1-31 | `stages/classify_stage.py` | `ecology_review` 场景或 fallback |
| 54 | P1-40 | `utils.py` | Windows 文件锁 |
| 55 | P1-2 | `classifier.py` | `parse_args()` 拆分 |
| 56 | P1-3 | `classifier.py` | `CorrectCommand` 提取为模块 |

---

## 进度追踪

| 批次 | 问题数 | 状态 | 完成日期 | PR |
|------|--------|------|----------|-----|
| 批次 1 | 6 | ✅ 已完成 | 2026-05-17 | — |
| 批次 2 | 8 | 待开始 | — | — |
| 批次 3 | 8 | 待开始 | — | — |
| 批次 4 | 10 | 待开始 | — | — |
| 批次 5 | 11 | 待开始 | — | — |
| 批次 6 | 12 | 待开始 | — | — |
| **合计** | **56** | — | — | — |
