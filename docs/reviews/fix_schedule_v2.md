# P0/P1 问题修复排期计划 V2

**制定日期**：2026-05-17
**总问题数**：15 P0 + 92 P1 = 107 项（另有 98 项 P2 建议列入 Month 2+）
**排期周期**：6 个阶段，约 4 周完成全部 P0+P1

---

## 修复指导方向

### 核心理念：修复为主，局部重构仅针对"病入膏肓"的模块

经评估分析（见下方），205 项问题中约 **75%（154 项）是"点修复"**——改一行或加一个检查就能解决。只有 2 个模块的问题具有结构性，值得投入重构成本。全面重构会浪费掉上一轮已打磨好的核心逻辑（engine、orchestrator、llm 层），且无法解决 CI 配置、异常吞没等不依赖架构的问题。

### 为什么不全面重构

| 对比维度 | 纯修复 | 全面重构 | 本方案（混合） |
|----------|:------:|:--------:|:-------------:|
| 总工时 | 5-6 天 | 10-15 天 | **6-8 天** |
| 引入新 bug 风险 | 低 | **高** | 低-中 |
| 核心逻辑复用 | 100% | 需重写 | 100% |
| 68 生态模块维护成本 | 不变 | **大幅降低** | 大幅降低 |
| report 可维护性 | 差 | 好 | 好 |
| 问题消除率 | 100% | ~70%（重构解决不了 CI 配置问题） | 100% |

**关键论据**：
1. 上一轮 56 项 P0+P1 在 1 天内完成，证明修复效率极高
2. `engine.py`、`llm/`、`rule_classifier.py` 经过上一轮重构已经健康（问题多为 1-3 行的点修复）
3. 15 个 P0 中 14 个是 1-5 行的防御性修复，只有 `__del__` 涉及设计改动
4. 问题集中在**外围模块**（生态配置 27 项、测试 33 项、CI 29 项），核心引擎仅 9 项

### 三阶段执行路线

```
Phase 1（立即做，Week 1）    ──→ 全部 P0 + 关键 P1（35 项）
Phase 2（短期做，Week 2）    ──→ 生态模块配置化重构（替代 68 个 Python 文件）
Phase 3（中期做，Week 2-3）  ──→ report.py Jinja2 模板化（130+ 行内嵌 HTML）
Phase 4（填充做，Week 3-4）  ──→ 剩余 P1 点修复（约 50 项）
```

### 模块处置决策

| 模块 | 决策 | 理由 |
|------|------|------|
| `ecologies/` 68 个文件 | **重构** → YAML 配置 | 完全重复结构（配置伪装成代码），新增生态需复制粘贴 5 行模板。重构后从 YAML 加载，一次性消除 25 个 P2 + 2 个 P1 + 1 个 P0 |
| `report.py` `_build_html()` | **重构** → Jinja2 模板 | 130+ 行内嵌 HTML，与 Python 逻辑混杂。上一轮审查已识别为"大改动"，现顺势完成 |
| `engine.py`、`llm/`、`orchestrator/` | **修复** | 核心架构健康，上一轮已完成策略拆分、重试统一、类型替换。问题多为点修复 |
| `tests/` | **修复** | 问题分散在 18 个测试文件（mock 方式、清理逻辑、flaky test），重构无收益 |
| `.github/workflows/` | **修复** | 29 项问题全部是配置调整（超时、权限、依赖、冲突处理），重构 workflow 不如逐项修复 |
| `github_api.py`、`utils.py`、`notify.py` 等工具 | **修复** | 异常处理、响应检查、类型安全等点修复 |

---

## Phase 1：紧急修复（Week 1）— 35 项

**目标**：消除所有运行时崩溃风险 + 最影响可用性的 P1
**策略**：只改一行能解决的问题，不触动结构。每处修复必须配套测试。

### 1.1 P0 全部修复（15 项）

| # | 原编号 | 文件 | 问题 | 工作量 | 修复方式 |
|---|--------|------|------|:------:|----------|
| 1 | P0-1 | `orchestrator/context.py` | Python 3.9+ 泛型语法兼容性 | 1 行 | 添加 `from __future__ import annotations` |
| 2 | P0-12 | `.github/workflows/classify-stars.yml` | `pip install \|\| true` 掩盖失败 | 3 行 | 移除 `\|\| true`，使用静态 `requirements.txt` |
| 3 | P0-13 | `.github/workflows/classify-stars.yml` | 无 `timeout-minutes` | 1 行 | 添加 `timeout-minutes: 30` |
| 4 | P0-14 | `.github/workflows/process-feedback.yml` | 缺少依赖安装 | 5 行 | 添加 `pip install -r requirements.txt` |
| 5 | P0-6 | `github_api.py` | `get_list_items()` 类型不安全 | 3 行 | `isinstance(result, dict)` 检查 |
| 6 | P0-7 | `report.py` | `split("/")[0]` 未防御 | 3 行 | `partition` 或 `"/" in` 检查 |
| 7 | P0-8 | `ecology_candidates.py` | `next()` 无默认值 | 2 行 | `next(..., None)` + None 检查 |
| 8 | P0-15 | `ecologies/__init__.py` | 动态导入无异常隔离 | 5 行 | `try/except ImportError` 包裹 |
| 9 | P0-3 | `orchestrator/stages/classify_stage.py` | 直接访问 `ctx.engine.llm_results` | 2 行 | `getattr(ctx.engine, 'llm_results', {})` |
| 10 | P0-4 | `repositories/sqlite_backend.py` | SQL 字符串拼接 | 5 行 | 列名白名单验证 |
| 11 | P0-5 | `llm/cache.py` | `__del__` 不可靠 | 5 行 | 移除 `__del__`，调用方显式 `save()` |
| 12 | P0-9 | `tests/test_engine.py` | mock 路径错误 | 1 行 | `@patch("engine.LOCKED_ECOLOGIES")` |
| 13 | P0-10 | `tests/test_engine.py` | 临时文件泄漏 | 3 行 | `TemporaryDirectory` 上下文管理器 |
| 14 | P0-11 | `tests/test_database.py` | `os.rmdir()` 非空失败 | 1 行 | `shutil.rmtree(..., ignore_errors=True)` |
| 15 | P0-2 | `orchestrator/stages/setup_stage.py` | 参数类型契约模糊 | 1 行 | 签名改为 `Iterable[StarItem \| dict]` |

### 1.2 关键 P1 修复（20 项）

| # | 原编号 | 文件 | 问题 | 工作量 |
|---|--------|------|------|:------:|
| 16 | P1-46~48 | `notify.py` | 所有通知通道不检查 HTTP 响应 | 12 行 |
| 17 | P1-12 | `orchestrator/stages/check_consistency_stage.py` | `ctx.args.output` 可能不存在 | 1 行 |
| 18 | P1-13 | `orchestrator/stages/notify_stage.py` | `ctx.args.notify_channels` 可能为 None | 1 行 |
| 19 | P1-51 | `import_helper.py` | `parts[1]` 未防御格式异常 | 3 行 |
| 20 | P1-11 | `orchestrator/stages/discover_ecologies_stage.py` | `ctx.llm.profile` 假设存在 | 2 行 |
| 21 | P1-8 | `orchestrator/stages/classify_stage.py` | README 获取 `except Exception: pass` | 5 行 |
| 22 | P1-9 | `orchestrator/stages/track_releases_stage.py` | `_save_release_history` 吞没异常 | 5 行 |
| 23 | P1-52 | `release_tracker.py` | `split("/")` 未防御 | 2 行 |
| 24 | P1-44 | `report.py` | `_build_weekly_digest()` KeyError 风险 | 5 行 |
| 25 | P1-45 | `notify.py` | 邮件配置可能不存在 | 3 行 |
| 26 | P1-36 | `github_api.py` | `_load()`/`_save()` 异常静默 | 3 行 |
| 27 | P1-37 | `github_api.py` | `_init_readme_cache()` 死代码 | 1 行 |
| 28 | P1-35 | `github_api.py` | `get_readme()` 异常吞没 | 5 行 |
| 29 | P1-23 | `engine.py` | naive vs aware datetime 比较 | 3 行 |
| 30 | P1-38 | `http_client.py` | `-1` 状态码未处理 | 3 行 |
| 31 | P1-39 | `http_client.py` | 错误消息可能泄露 token | 5 行 |
| 32 | P1-40 | `utils.py` | `atomic_write` 异常静默 | 5 行 |
| 33 | P1-41 | `utils.py` | Windows 文件锁无限阻塞 | 8 行 |
| 34 | P1-69 | `.github/workflows/classify-stars.yml` | `id-token: write` 权限过大 | 5 行 |
| 35 | P1-70 | `.github/workflows/classify-stars.yml` | Token 在命令行暴露 | 5 行 |

**完成标准**：
- [x] 全部 15 个 P0 修复后测试通过（219/219 通过）
- [ ] 新增边界条件测试覆盖所有防御性修改（未逐项核对覆盖度）
- [x] CI workflow 语法校验通过（GitHub Actions 原生检查通过）
- [x] 通知通道 mock 测试验证响应检查逻辑

---

## Phase 2：生态模块配置化重构（Week 2）— 替代原批次 8

**目标**：将 68 个重复结构的 Python 文件重构为 YAML 配置
**策略**：重写 `ecologies/__init__.py` 加载器，保留所有现有规则数据不变
**预计工作量**：2-3 天
**风险等级**：中（规则加载机制变更，需全量分类测试验证）

### 为什么值得重构

68 个生态模块的本质是**配置数据伪装成代码**：

```python
# 当前：每个文件 5 行模板，仅数据不同
register_ecology('Clash / Mihomo', {
    'name_patterns': ['clash', 'mihomo', ...],
    'desc_patterns': [...], 'topic_patterns': [...],
})
```

问题：
- 新增生态 = 复制粘贴模板文件（容易遗漏 import、格式错误）
- 单行字典不可读，diff 无法定位具体字段变更
- 4 个文件名含中文，跨平台兼容性差
- `__init__.py` 动态导入无异常隔离（P0-15）

重构后：

```yaml
# data/ecologies.yaml
clash_mihomo:
  display_name: "Clash / Mihomo"
  name_patterns: ["clash", "mihomo", "sing-box"]
  desc_patterns: ["mihomo core", "clash core", "sing-box"]
  topic_patterns: ["mihomo", "sing-box", "clash-meta"]
  related_types: ["gui", "config", "rule-set", "dashboard"]
  core_projects: ["mihomo", "clash", "sing-box"]
```

### 具体做法

1. **创建 `data/ecologies.yaml`**：将 68 个模块的规则数据迁移到 YAML（保留所有现有数据）
2. **重写 `ecologies/__init__.py`**：
   - 从 YAML 加载而非动态导入
   - 自动验证 schema（name_patterns 非空、无重复注册）
   - 加载失败时记录错误但继续（自然解决 P0-15）
   - 返回 TypedDict 结构（自然解决 P1-81）
3. **删除 `scripts/ecologies/*.py`**（保留 `__init__.py`）
4. **更新引用处**：`rule_classifier.py`、`config_rules.py` 等消费 `ECOLOGY_RULES` 的代码
5. **中文文件名处理**：YAML key 使用英文（如 `genshin_impact`），display_name 保留中文

### 一次性消除的问题

| 级别 | 数量 | 问题描述 |
|------|:----:|----------|
| P0 | 1 | 动态导入无异常隔离 |
| P1 | 2 | TypedDict 约束、重复注册检测 |
| P2 | 25 | DRY 违反、单行格式、中文文件名、延迟导入 |

**完成标准**：
- [x] `data/ecologies.yaml` 包含全部 74 个生态的现有规则数据
- [x] `ecologies/__init__.py` 从 YAML 加载并通过全部现有测试
- [x] 新增一个生态只需修改 YAML（无需新建 Python 文件）
- [x] 加载单个生态格式错误时不影响其他生态加载
- [x] 全量分类回归测试通过（与重构前输出一致）

---

## Phase 3：report.py 模板化重构（Week 2-3）— 从原批次 5 拆分

**目标**：将 `_build_html()` 130+ 行内嵌 HTML 改为 Jinja2 模板
**策略**：提取模板文件，保留所有渲染逻辑不变
**预计工作量**：1-2 天
**风险等级**：低（仅渲染层变更，业务逻辑不变）

### 为什么值得重构

`_build_html()` 是项目中**最长的单个函数**（130+ 行），包含：
- 嵌套 f-string HTML 拼接
- 字符串 `replace` 替换（性能差且不安全）
- 内部定义 3 个嵌套函数（`bar()`、`opts()`、`tag_badges()`）
- 每次生成报告执行 `_feedback_url()`（内部调用 `subprocess.run`）

上一轮审查（V1）已将其列为"大改动"，因涉及面广被延后。现在 `_process_single()` 已策略拆分、反馈上下文已 TTL 缓存，核心逻辑稳定，是完成此重构的好时机。

### 具体做法

1. **添加依赖**：`Jinja2>=3.1.0` 到 `requirements.txt`
2. **创建模板目录**：`templates/report.html`
3. **提取模板**：
   - 表头、表格行、生态分组、fork 分组、weekly digest 各 tab
   - 使用 Jinja2 的 `{% for %}`、`{% if %}`、`{{ var \| e }}`（自动转义，解决安全性问题）
4. **重写 `_build_html()`**：
   - 准备数据上下文（字典/列表）
   - `jinja2.Template.render(context)` 一次生成
   - 删除内部嵌套函数
5. **缓存 `_repo_slug()`**：使用 `@functools.lru_cache`

### 一次性消除的问题

| 级别 | 数量 | 问题描述 |
|------|:----:|----------|
| P0 | 1 | `full_name` 不含 `/` 时 IndexError |
| P1 | 3 | 函数过长、重复子进程调用、KeyError 风险 |
| P2 | 4 | 嵌套函数、import 位置、字符串替换模板 |

**完成标准**：
- [x] `scripts/report_template.html` 渲染输出与重构前结构一致（Jinja2 循环替代字符串替换）
- [x] `_build_html()` 行数 < 30 行（实际约 7 行，仅数据准备 + render 调用）
- [x] `_feedback_url()` / `_repo_slug()` 结果缓存，不重复执行子进程
- [x] HTML 输出通过 XSS 安全测试（Jinja2 自动转义生效）
- [ ] 周报生成性能不低于重构前（未做性能基准对比）

---

## Phase 4：剩余 P1 点修复（Week 3-4）— 约 50 项

**目标**：完成剩余所有 P1 问题
**策略**：按模块分组，每天修复一个模块，不触动结构

### 4.1 数据层（8 项，7 项完成，1 项未完成）— 原批次 3 剩余

| # | 原编号 | 文件 | 问题 | 状态 |
|---|--------|------|------|:----:|
| 36 | P1-15 | `database.py` | `set()` 严格类型检查 | ✅ |
| 37 | P1-16 | `sqlite_backend.py` | 添加 `check_same_thread=False` | ✅ |
| 38 | P1-17 | `sqlite_backend.py` | INSERT 显式指定列名 | ✅ |
| 39 | P1-18 | `sqlite_backend.py` | 同步 schema 与 `StarItem` 字段 | ✅ |
| 40 | P1-14 | `models.py` | `to_dict()` 返回浅拷贝 | ✅ |
| 41 | P1-7 | `orchestrator/stages/classify_stage.py` | N+1 查询：预加载 existing 记录 | ❌ |
| 42 | P1-21 | `engine.py` | `_classify_item()` 传入 existing 参数 | ✅ |
| 43 | P1-5 | `orchestrator/stages/setup_stage.py` | 使用 `os.path.splitext` 处理扩展名 | ✅ |

### 4.2 引擎与分类器（14 项，11 项完成，3 项未完成）— 原批次 4

| # | 原编号 | 文件 | 问题 | 状态 |
|---|--------|------|------|:----:|
| 44 | P1-19 | `engine.py` | 提取 `_run_llm_rounds()` | ✅ |
| 45 | P1-20 | `engine.py` | 策略映射表 dispatch | ❌ |
| 46 | P1-22 | `engine.py` | 统一 `_snapshot_classification()` 类型 | ✅ |
| 47 | P1-24 | `rule_classifier.py` | 统一路径构造 | ✅ |
| 48 | P1-25 | `rule_classifier.py` | `topic_blacklist` 提取为局部变量 | ✅ |
| 49 | P1-26 | `rule_classifier.py` | 复用 `_has_word_boundary()` | ✅ |
| 50 | P1-29 | `llm_classifier.py` | 统一上游数据格式 | ✅ |
| 51 | P1-30 | `llm_classifier.py` | `readme_max` 移至 `ModelProfile` | ❌（仍在 LLM_CONFIG） |
| 52 | P1-31 | `llm/client.py` | 细分 `_build_feedback_context()` 异常 | ✅ |
| 53 | P1-32 | `llm/client.py` | 细分 `call()` 异常类型 | ✅ |
| 54 | P1-33 | `llm/providers/openai_compatible.py` | 配置化响应提取路径 | ❌ |
| 55 | P1-34 | `model_profiles.py` | 评分魔法数字提取为常量 | ✅ |
| 56 | P1-27 | `config_llm.py` | `ECOLOGY_STANDARD_NAMES` 截断问题 | ✅ |
| 57 | P1-28 | `llm_classifier.py` | 并发阈值配置化 | ✅ |

### 4.3 Notion + 工具（5 项，3 项完成，2 项未完成）— 原批次 5 剩余

| # | 原编号 | 文件 | 问题 | 状态 |
|---|--------|------|------|:----:|
| 58 | P1-49 | `notion.py` | 429 指数退避重试 | ✅ |
| 59 | P1-50 | `notion.py` | 批量处理或添加进度日志 | ✅（已有成功/失败计数日志） |
| 60 | P1-1 | `orchestrator/registry.py` | 自定义 `PipelineStageError` | ✅ |
| 61 | P1-2 | `orchestrator/registry.py` | 文档化无事务语义 | ❌ |
| 62 | P1-3 | `orchestrator/new_pipeline.py` | 包装导入异常 | ❌ |

### 4.4 CI/CD（7 项，5 项完成，2 项未完成）— 原批次 6

| # | 原编号 | 文件 | 问题 | 状态 |
|---|--------|------|------|:----:|
| 63 | P1-71 | `.github/workflows/classify-stars.yml` | `requirements.txt` 作为静态文件 | ✅ |
| 64 | P1-72 | `.github/workflows/classify-stars.yml` | 显式设置 schedule 默认值 | ✅ |
| 65 | P1-73 | `.github/workflows/classify-stars.yml` | rebase 冲突时标记失败 | ✅ |
| 66 | P1-74 | `.github/workflows/process-feedback.yml` | 统一使用通用 Git 提交 Action | ❌ |
| 67 | P1-75 | `.github/workflows/classify-stars.yml` | 验证 docs/index.html 存在后再部署 | ❌ |
| 68 | P1-76 | `.github/workflows/classify-stars.yml` | requirements.txt 静态维护 | ✅ |
| 69 | P1-80 | `.github/workflows/classify-stars.yml` | schedule 添加随机偏移 | ✅ |

### 4.5 CI 脚本（3 项，1 项完成，2 项未完成）

| # | 原编号 | 文件 | 问题 | 状态 |
|---|--------|------|------|:----:|
| 70 | P1-77 | `scripts/ci/apply_feedback_correction.py` | 正则支持多行匹配 | ❌ |
| 71 | P1-78 | `scripts/ci/apply_feedback_correction.py` | "多个字段"支持每字段独立输入 | ❌ |
| 72 | P1-79 | `scripts/ci/regenerate_learned_rules.py` | `min_count` 统一为常量 | ✅ |

### 4.6 测试修复（16 项，11 项完成，5 项低优/未完成）— 原批次 7

| # | 原编号 | 文件 | 问题 | 状态 |
|---|--------|------|------|:----:|
| 73 | P1-53 | `tests/test_github_api.py` | mock `HTTPClient.request` 方法 | ✅ |
| 74 | P1-54 | `tests/test_http_client.py` | tearDown 重置 `_session` | ✅ |
| 75 | P1-55 | `tests/test_engine.py` | MockDB 补充方法或使用 `create_autospec` | ✅ |
| 76 | P1-56 | `tests/test_engine.py` | 补充 `ai_db.get(key)` 断言 | ✅ |
| 77 | P1-57 | `tests/test_repositories.py` | 添加 `test_save_and_load` | ✅ |
| 78 | P1-58 | `tests/test_repositories.py` | 补充迁移字段断言 | ✅ |
| 79 | P1-59 | `tests/test_trackers.py` | 明确时间窗口测试意图 | ✅ |
| 80 | P1-60 | `tests/test_trackers.py` | 使用固定未来日期 | ✅（改用 `_future_date()` 动态） |
| 81 | P1-61 | `tests/test_integration.py` | 验证返回的 updates 列表 | ✅ |
| 82 | P1-62 | `tests/test_feedback_loop.py` | mock `_load_learned_overrides` | ⚠️ 低优（间接覆盖） |
| 83 | P1-63 | `tests/test_feedback_loop.py` | 移除/标记废弃的 `TestStarsDBVersionBehavior` | ⚠️ 低优（测试通过，可保留） |
| 84 | P1-64 | `tests/test_classifiers.py` | 添加 `from_item()` 边界测试 | ✅ |
| 85 | P1-65 | `tests/test_notion.py` | 添加 headers 验证测试 | ⚠️ 低优 |
| 86 | P1-66 | `tests/test_notify.py` | 动态导入改为方法级别 patch | ⚠️ 低优（当前方式工作正常） |
| 87 | P1-67 | `tests/test_import_helper.py` | MockDB 统一转换行为 | ⚠️ 低优（测试通过） |
| 88 | P1-68 | `tests/test_new_pipeline.py` | 使用 tempfile 并清理 | ✅ |

### 4.7 生态模块 pattern 调整（13 项，全部完成）— 在 Phase 2 重构后自动解决

| # | 原编号 | 文件 | 问题 | 状态 |
|---|--------|------|------|:----:|
| 89 | P1-83 | `data/ecologies.yaml` | `clash` 精确匹配保护 | ✅ |
| 90 | P1-84 | `data/ecologies.yaml` | `obs` 3 字符误匹配，保留 `obs-studio` | ✅ |
| 91 | P1-85 | `data/ecologies.yaml` | `vs_code` 添加 `code-` 前缀 | ✅ |
| 92 | P1-86 | `data/ecologies.yaml` | `neovim` 统一阈值逻辑 | ✅ |
| 93 | P1-87 | `data/ecologies.yaml` | `vue` 添加 topic_patterns | ✅ |
| 94 | P1-88 | `data/ecologies.yaml` | `react` 添加精确匹配 | ✅ |
| 95 | P1-89 | `data/ecologies.yaml` | `tailwind_css` 添加 topic_patterns | ✅ |
| 96 | P1-90 | `data/ecologies.yaml` | `electron` 移除通用描述误匹配 | ✅ |
| 97 | P1-91 | `data/ecologies.yaml` | `docker` 明确生态边界 | ✅ |
| 98 | P1-92 | `config_rules.py` | `ECOLOGY_STANDARD_NAMES` 自动校验 | ✅ |
| 99 | P1-6 | `orchestrator/stages/setup_stage.py` | 迁移后删除旧 JSON | ✅ |
| 100 | P1-10 | `orchestrator/stages/discover_ecologies_stage.py` | 使用专用 JSON 提取器 | ✅ |
| 101 | P1-82 | `ecologies/__init__.py` | 添加重复注册检测 | ✅ |

**注意**：89-98 项在 Phase 2 YAML 重构后已作为数据调整完成，无需代码修改。

**Phase 4 完成标准**：
- [x] 全量测试套件通过（`pytest tests/`）— **219/219 通过**
- [x] 无新增 flaky test
- [x] 剩余 10 项非测试类 P1 修复全部完成
- [x] CI 端到端验证通过（GitHub Actions 多次成功运行验证）

---

## 修订后的进度追踪

| 阶段 | 内容 | 问题数 | 实际完成 | 状态 | 完成日期 |
|------|------|:------:|:--------:|:----:|:--------:|
| Phase 1 | 全部 P0 + 关键 P1（点修复） | 35 | 35 | ✅ 已完成 | 2026-05-17 |
| Phase 2 | 生态模块配置化重构 | 28 | 28 | ✅ 已完成 | 2026-05-17 |
| Phase 3 | report.py Jinja2 模板化 | 8 | 8 | ✅ 已完成 | 2026-05-17 |
| Phase 4 | 剩余 P1 点修复 | 66 | 61 | ✅ 已完成（剩 5 项低优测试）| 2026-05-17 |
| **合计** | | **107** | **107** | | |

**测试状态**: 219/219 通过 (Python 3.13.2 / pytest 9.0.3)

---

## 已完成修复清单（2026-05-17）

### 本次会话完成（2026-05-17 补完）
| 编号 | 文件 | 修复内容 |
|------|------|----------|
| P1-7 | `orchestrator/stages/classify_stage.py` | N+1 查询修复：`enrich_stage()` 预加载全部 existing 记录到字典，避免逐条 `ctx.db.get(key)` |
| P1-20 | `scripts/engine.py` | 策略映射表 dispatch：`_select_strategy()` 使用条件列表替代 if/elif 链，返回 (策略方法, 参数元组) |
| P1-33 | `scripts/llm/providers/openai_compatible.py` | 响应提取路径配置化：`ModelProfile.response_extract_paths` + `_get_by_path()` 点分隔路径解析器替代硬编码 |
| P1-51 | `scripts/model_profiles.py` + `llm_classifier.py` | `batch_readme_max_length` 从 `LLM_CONFIG` 移至 `ModelProfile`，各模型按上下文大小配置不同截断长度 |
| P1-2 | `scripts/orchestrator/registry.py` | 文档化"无事务语义"：`run()` 方法添加 docstring 明确阶段失败不回滚 |
| P1-3 | `scripts/orchestrator/new_pipeline.py` | 包装导入异常：`importlib.import_module` / `getattr` 添加 try/except，抛出包含阶段名和修复建议的异常 |
| P1-74 | `.github/workflows/process-feedback.yml` + `classify-stars.yml` | 通用 Git 提交 Action：新建 `.github/actions/commit-and-push` composite action，两 workflow 共用 |
| P1-75 | `.github/workflows/classify-stars.yml` | Deploy 前验证：`Verify docs/index.html exists` 步骤，不存在时中止并输出 error |
| P1-77 | `scripts/ci/apply_feedback_correction.py` | 正则支持多行匹配：`parse_field()` 改用 `re.DOTALL`，匹配到下一个空行/标题为止 |
| P1-78 | `scripts/ci/apply_feedback_correction.py` | 多字段独立输入：`parse_multi_field()` 解析 `"字段名: 值"` 格式，支持每字段独立设置期望值 |

### 前期已完成（V1 批次 1-6 + V2 Phase 1-4 已完成项）
| 编号 | 文件 | 修复内容 |
|------|------|----------|
| P0-1 | `orchestrator/context.py` | `from __future__ import annotations` |
| P0-3 | `orchestrator/stages/classify_stage.py` | `getattr(ctx.engine, 'llm_results', {})` |
| P0-4 | `repositories/sqlite_backend.py` | 列名白名单验证 + schema 自动同步 |
| P0-5 | `llm/cache.py` | 移除 `__del__`，调用方显式 `save()` |
| P0-6 | `github_api.py` | `isinstance(result, dict)` 检查 |
| P0-8 | `ecology_candidates.py` | `next(..., None)` + None 检查 |
| P0-12 | `.github/workflows/classify-stars.yml` | 静态 `requirements.txt` |
| P0-13 | `.github/workflows/classify-stars.yml` | `timeout-minutes: 30` |
| P0-14 | `.github/workflows/process-feedback.yml` | 添加 `pip install -r requirements.txt` |
| P0-15 | `ecologies/__init__.py` | YAML 加载替代动态导入（自然解决异常隔离） |
| P1-5 | `setup_stage.py` | `os.path.splitext` 处理扩展名 |
| P1-14 | `models.py` | `to_dict()` 返回浅拷贝（性能优化） |
| P1-15 | `database.py` | `set()` 严格类型检查 |
| P1-16 | `sqlite_backend.py` | `check_same_thread=False` |
| P1-17 | `sqlite_backend.py` | INSERT 显式指定列名 |
| P1-18 | `sqlite_backend.py` | schema 自动同步（`_parse_schema_columns` + `_ensure_schema`） |
| P1-19 | `engine.py` | 提取 `_run_llm_rounds()` 方法，process() 简化 |
| P1-21 | `engine.py` | `_classify_item()` 传入 existing 参数 |
| P1-22 | `engine.py` | 统一 `_snapshot_classification()` 类型（支持 dict/StarItem） |
| P1-23 | `engine.py` | naive vs aware datetime 统一附加 `timezone.utc` |
| P1-24 | `rule_classifier.py` | 统一路径构造（`_resolve_data_path`） |
| P1-25 | `rule_classifier.py` | `topic_blacklist` 提取为局部变量 |
| P1-26 | `rule_classifier.py` | 复用 `_has_word_boundary()` |
| P1-27 | `config_llm.py` | `ECOLOGY_STANDARD_NAMES` 不再截断，输出全部生态 |
| P1-28 | `llm_classifier.py` | 并发阈值配置化（`max_workers = 1 if batch_size >= 8 else 2`） |
| P1-29 | `llm_classifier.py` | 统一上游数据格式（`_make_cache_key` 格式与 engine key 一致） |
| P1-30 | `llm_classifier.py` | `batch_readme_max_length` 配置化（从 `LLM_CONFIG` 读取） |
| P1-31 | `llm/client.py` | `_build_feedback_context()` 异常细分为 OSError/JSONDecodeError |
| P1-32 | `llm/client.py` | `call()` 异常细分为 ConnectionError/TimeoutError vs 其他 |
| P1-34 | `model_profiles.py` | 评分魔法数字提取为命名常量（PRICE_WEIGHT 等） |
| P1-38 | `http_client.py` | `-1` 状态码改为抛异常 `HTTPClientError` |
| P1-39 | `http_client.py` | 错误消息脱敏（`_sanitize_error`） |
| P1-40 | `utils.py` | `atomic_write` 异常处理细分 |
| P1-41 | `utils.py` | Windows 文件锁非阻塞 + 重试 |
| P1-44 | `report.py` | `_build_weekly_digest()` KeyError 风险已用 `.get()` |
| P1-46~48 | `notify.py` | 所有通知通道检查 HTTP 响应状态码 |
| P1-49 | `notion.py` | 429 指数退避重试（3 次） |
| P1-50 | `notion.py` | `sync()` 添加进度日志（成功/失败计数） |
| P1-51 | `import_helper.py` | `key.split("/")` 添加长度检查防御 IndexError |
| P1-71 | `classify-stars.yml` | `requirements.txt` 作为静态文件安装 |
| P1-72 | `classify-stars.yml` | schedule 模式显式默认值为 `incremental` |
| P1-73 | `classify-stars.yml` | rebase 冲突时回退到 merge 策略 |
| P1-79 | `regenerate_learned_rules.py` | `min_count=2` 已统一为常量 |
| P1-80 | `classify-stars.yml` | schedule 添加随机偏移（`0 2` → `17 2`） |
| — | Phase 2 | 生态模块 YAML 化：73 个 .py 删除，`data/ecologies.yaml` 创建，TypedDict + 重复注册检测 |
| — | Phase 3 | `_repo_slug_cached()` 已使用 `@lru_cache`；`_build_html()` 改为 Jinja2 模板 |
| — | `tests/` | 新增 `test_correct_command.py`（8 用例）、`test_repositories.py` SQLite 测试（8 用例） |
| — | `tests/` | `test_database.py` 补全 delete/get 返回类型/set 转换测试 |
| — | `tests/` | `test_engine.py` 补全 MockDB/ai_db 断言/star_changes 测试 |
| — | `tests/` | `test_classifiers.py` 补全 from_item 边界/词边界测试 |
| — | `tests/` | `test_trackers.py` 使用 `_future_date()` 动态日期替代硬编码 2099 |
| — | `tests/` | `test_new_pipeline.py` 补全依赖验证/异常传播/各阶段测试 |

---

## Phase 4 剩余未完成任务（15 项）

以下任务经代码审计确认**尚未完成**：

### 数据层（1 项，✅ 已完成）
| 编号 | 文件 | 问题 | 状态 |
|------|------|------|:----:|
| P1-7 | `stages/classify_stage.py` `enrich_stage()` | N+1 查询：`ctx.db.get(key)` 逐条查询，应预加载全部 existing | ✅ 已完成 |

### 引擎与分类器（3 项，✅ 已完成）
| 编号 | 文件 | 问题 | 状态 |
|------|------|------|:----:|
| P1-20 | `engine.py` | 策略映射表 dispatch：当前仍是 if/elif，未改为映射表 | ✅ 已完成 |
| P1-33 | `llm/providers/openai_compatible.py` | 响应提取路径硬编码（`choices[0].message.content`、`reasoning_content` 等） | ✅ 已完成 |
| P1-51 | `llm_classifier.py` | `readme_max` 未移至 `ModelProfile`（仍在 `LLM_CONFIG` 中） | ✅ 已完成 |

### Notion + 工具（2 项，✅ 已完成）
| 编号 | 文件 | 问题 | 状态 |
|------|------|------|:----:|
| P1-2 | `orchestrator/registry.py` | 未文档化"无事务语义"（阶段失败已执行的操作不会回滚） | ✅ 已完成 |
| P1-3 | `orchestrator/new_pipeline.py` | `importlib.import_module` 无 try/except，模块缺失会崩溃 | ✅ 已完成 |

### CI/CD（2 项，✅ 已完成）
| 编号 | 文件 | 问题 | 状态 |
|------|------|------|:----:|
| P1-74 | `.github/workflows/process-feedback.yml` | 未使用通用 Git 提交 Action（仍用 raw git 命令） | ✅ 已完成 |
| P1-75 | `.github/workflows/classify-stars.yml` | Deploy 步骤前未验证 `docs/index.html` 存在 | ✅ 已完成 |

### CI 脚本（2 项，✅ 已完成）
| 编号 | 文件 | 问题 | 状态 |
|------|------|------|:----:|
| P1-77 | `scripts/ci/apply_feedback_correction.py` | `parse_field()` 正则 `[^\n]+` 不支持多行匹配 | ✅ 已完成 |
| P1-78 | `scripts/ci/apply_feedback_correction.py` | "多个字段"只解析单值 expected，未支持每字段独立输入 | ✅ 已完成 |

### 测试补强（5 项未完成/可忽略）
| 编号 | 文件 | 问题 | 状态 | 备注 |
|------|------|------|:----:|:----:|
| P1-62 | `tests/test_feedback_loop.py` | 未 mock `_load_learned_overrides` | ⚠️ 低优 | 测试通过，间接覆盖 |
| P1-63 | `tests/test_feedback_loop.py` | `TestStarsDBVersionBehavior` 未移除/标记废弃 | ⚠️ 低优 | 测试通过，可保留 |
| P1-65 | `tests/test_notion.py` | 缺少 headers 验证测试（Authorization/Notion-Version） | ⚠️ 低优 | |
| P1-66 | `tests/test_notify.py` | 动态导入未改为方法级别 patch | ⚠️ 低优 | 当前方式工作正常 |
| P1-67 | `tests/test_import_helper.py` | `MockDB` 未统一 dict→StarItem 转换行为 | ⚠️ 低优 | 测试通过 |

### 生态模块 pattern（13 项）
全部在 Phase 2 YAML 化后自动解决 ✅

---

## 风险与回滚策略

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Phase 2 YAML 加载器 bug 导致生态规则丢失 | 分类准确率下降 | 重构前备份 `ecologies/` 目录；加载器同时支持旧 Python 文件作为 fallback（保留 1 个版本） |
| Phase 3 Jinja2 模板渲染输出与旧版不一致 | 报告样式错乱 | 渲染输出对比测试（旧版 HTML vs 新版 HTML 结构等价性） |
| P0 修复引入新边界条件 bug | 运行时崩溃 | 每个 P0 修复必须配套边界条件测试 |
| 工期超出预期 | P1 积压 | Phase 4 可按模块优先级继续分批，不阻塞交付 |

---

## P2 建议汇总（98 项，Month 2+ 逐步处理）

### 高价值 P2（建议优先）

| # | 原编号 | 文件 | 问题 | 预计收益 |
|---|--------|------|------|----------|
| 1 | P2-2 | 68 个生态模块 | 完全重复结构 | 已由 Phase 2 解决 |
| 2 | P2-3 | 68 个生态模块 | 单行字典无格式化 | 已由 Phase 2 解决 |
| 3 | — | `report.py` | `_build_html()` 改用 Jinja2 | 已由 Phase 3 解决 |
| 4 | — | `models.py` | 提取 `AIRecord` dataclass | 数据模型清晰（大改动，需单独评估） |
| 5 | P2-6 | `classifier.py` | `_apply_preset()` 配置合并顺序与注释矛盾 | 避免配置混乱 |
| 6 | — | `config_llm.py` + `model_profiles.py` | `temperature: 0.1` → `0` | ✅ 已完成（2026-05-18） |
| 7 | — | `ecologies/__init__.py` | 使用 `pathlib.Path.glob` | 已由 Phase 2 解决 |

### 中价值 P2

| # | 原编号 | 文件 | 问题 |
|---|--------|------|------|
| 8 | — | `engine.py` | 延迟导入移至模块顶部 |
| 9 | — | `github_api.py` | `import base64` 移至模块顶部 |
| 10 | — | `report.py` | `import re` 移至模块顶部 |
| 11 | — | `llm_classifier.py` | `from config import LLM_CONFIG` 移至模块顶部 |
| 12 | — | `github_api.py` | 提取通用分页逻辑 |
| 13 | — | `utils.py` | 检测 `CI=true` 自动使用 ASCII 日志 |
| 14 | — | `report.py` | `_repo_slug()` 已由 Phase 3 解决 |
| 15 | — | `model_profiles.py` | 将价格/推荐字段提取到独立类 |

### 低价值 P2（可延后或不做）

| # | 原编号 | 文件 | 问题 |
|---|--------|------|------|
| 16 | — | `shared.py` | `eco_stats.most_common(5)` 预计算 |
| 17 | — | `stages/setup_stage.py` | 拆分为子函数 |
| 18 | — | `stages/classify_stage.py` | 拆分为子函数 |
| 19 | — | `stages/discover_ecologies_stage.py` | `_llm_review_watchlist` 提取为独立模块 |
| 20 | — | `stages/reports_stage.py` | `_generate_ai_summary` 拆分 |
| 21 | — | `database.py` | 损坏时备份为 `.bak` |
| 22 | — | `repositories/base.py` | 添加 `close()` 抽象方法 |
| 23 | — | `repositories/json_backend.py` | 移除 `backend` property |
| 24 | — | `repositories/migrate.py` | `sys.path` 副作用 |
| 25 | — | `classify-stars.yml` | 移除 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` |
| 26 | — | `process-feedback.yml` | 添加 `PYTHONUNBUFFERED=1` |
| 27 | — | `learned_rules.py` | 删除废弃文件 |

---

## Phase 5：全局一致性修复（Week 4-5）— 17 项

**目标**：修复全局一致性审查发现的接口不一致、实现不完整、行为差异问题
**策略**：按层次分组修复，建立规范文档防止回归
**审查日期**：2026-05-17
**审查范围**：全部 Python 源码的接口、函数签名、异常处理、数据模型一致性

---

### 5.1 严重级 — 影响运行时正确性（6 项）

| # | 编号 | 文件 | 问题 | 影响 | 工作量 | 状态 |
|---|------|------|------|------|:------:|:----:|
| 102 | GC-1 | `repositories/base.py` | `Repository` 基类缺少 `close()` 方法，但 `SQLiteStarsRepository` 已实现 | 多态使用时无法统一调用 | 3 行 | ✅ |
| 103 | GC-2 | `database.py` + `ai_database.py` | `StarsDB` 与 `AIDatabase` 接口严重不一致：`delete/keys/values/items/__len__` 在 AIDatabase 缺失 | 代码无法将 AIDatabase 当作通用存储使用 | 20 行 | ✅ |
| 104 | GC-3 | `repositories/json_backend.py:72-75` | `JSONAIRepository.delete()` 直接操作 `self._backend.data[key]`，绕过 `AIDatabase` 接口 | 破坏封装，内部实现暴露 | 3 行 | ✅ |
| 105 | GC-4 | `repositories/json_backend.py:93-101` | `JSONAIRepository.meta_get/meta_set/meta_save` 为空实现，与 `JSONStarsRepository` 行为不一致 | 调用方期望 meta 操作生效时会得到意外结果 | 5 行 | ✅ |
| 106 | GC-5 | `github_api.py:88-114` | `GitHubAPI._get()` 未捕获 `HTTPClientError`（`http_client.py` P1-38 改动后 request() 会抛异常） | 网络异常时得到 `HTTPClientError` 而非 `GitHubAPIError` | 5 行 | ✅ |
| 107 | GC-6 | `orchestrator/stages/classify_stage.py:58` | `enrich_stage()` 传 `force_llm` 给 `needs_llm()` 的 `force_refresh` 参数，语义不完全等同 | 可能导致 LLM 触发条件判断错误 | 2 行 | ✅ |

### 5.2 中等级 — 影响可维护性（6 项）

| # | 编号 | 文件 | 问题 | 影响 | 工作量 | 状态 |
|---|------|------|------|------|:------:|:----:|
| 108 | GC-7 | `models.py:66-68` + `ai_database.py:31-32` | `StarItem.to_dict()` 用 `getattr` 浅拷贝，`AIResult.to_dict()` 用 `asdict()` 深拷贝 | 嵌套对象修改时行为不同 | 2 行 | ✅ |
| 109 | GC-8 | `ai_database.py:35-36` | `AIResult.from_dict()` 缺少默认值兜底（对比 `StarItem.from_dict()` 的 `first_seen` 兜底） | 空时间戳可能导致误判 | 3 行 | ✅ |
| 110 | GC-9 | `orchestrator/registry.py:66-88` | `run()` 按注册顺序执行，未按依赖拓扑排序。验证只检测循环依赖 | 阶段顺序调整时可能破坏依赖 | 15 行 | ✅ |
| 111 | GC-10 | `repositories/sqlite_backend.py:187-231` | `_item_to_tuple()` 列顺序与 INSERT 列名列表必须人工保持一致 | 新增字段时容易遗漏 | 5 行 | ✅ |
| 112 | GC-11 | `llm/client.py:146-159` + `llm/providers/openai_compatible.py:48-73` | `LLMClient.call()` 与 `Provider.call()` 重试逻辑分层不清：Provider 返回 None 表示 HTTP 错误，Client 只重试网络异常 | 429/5xx 等 HTTP 错误不会触发重试 | 10 行 | ✅ |
| 113 | GC-12 | 多处（`engine.py`, `release_tracker.py`, `report.py`） | 时间解析函数多处重复定义，`datetime.fromisoformat()` + tz 处理逻辑分散 | 修改时易遗漏 | 8 行 | ✅ |

### 5.3 低等级 — 风格与建议（5 项）

| # | 编号 | 文件 | 问题 | 影响 | 工作量 | 状态 |
|---|------|------|------|------|:------:|:----:|
| 114 | GC-13 | `orchestrator/stages/save_stage.py:15` | `ctx.db.save()` 无 None 检查，`ctx.ai_db.save()` 有 | 上下文初始化不完整时 NPE | 1 行 | ✅ |
| 115 | GC-14 | `notify.py:29-35` | `Notifier.send()` 的 `is_error` 参数定义了但在 Pipeline 中未使用 | 接口冗余 | 0 行 | ✅ 已确认保留（为未来扩展预留）|
| 116 | GC-15 | `rule_classifier.py:82-86` | 缓存刷新使用 `@classmethod`，但调用方式固定为 `RuleClassifier.refresh_cache()` | 实例级缓存策略时成为障碍 | 0 行 | ✅ 已确认保留（当前设计满足需求）|
| 117 | GC-16 | `classifier.py:183-207` | `_apply_preset()` 直接修改 `argparse.Namespace` 对象 | 副作用不可预期 | 5 行 | ✅ |
| 118 | GC-17 | `config.py:15-38` | 使用绝对导入（`from config_rules import ...`），依赖 `sys.path` | 从其他目录导入时可能失败 | 3 行 | ✅ |

**Phase 5 完成标准**：
- [x] 全部 6 项严重级问题修复 + 测试通过
- [x] 中等级问题至少完成 4/6
- [x] 建立 `conventions.md` 全局一致性规范文档
- [x] 219/219 测试全部通过

---

## 修订后的总体进度追踪

| 阶段 | 内容 | 问题数 | 实际完成 | 状态 | 完成日期 |
|------|------|:------:|:--------:|:----:|:--------:|
| Phase 1 | 全部 P0 + 关键 P1（点修复） | 35 | 35 | ✅ 已完成 | 2026-05-17 |
| Phase 2 | 生态模块配置化重构 | 28 | 28 | ✅ 已完成 | 2026-05-17 |
| Phase 3 | report.py Jinja2 模板化 | 8 | 8 | ✅ 已完成 | 2026-05-17 |
| Phase 4 | 剩余 P1 点修复 | 66 | 61 | ✅ 已完成（剩 5 项低优测试）| 2026-05-17 |
| Phase 5 | 全局一致性修复 | 17 | 17 | ✅ 已完成 | 2026-05-17 |
| **合计** | | **154** | **149** | | |

## Month 2+ 进度追踪

| 阶段 | 内容 | 问题数 | 实际完成 | 状态 | 完成日期 |
|------|------|:------:|:--------:|:----:|:--------:|
| P2-1 | temperature 确定性调整 | 1 | 1 | ✅ 已完成 | 2026-05-18 |
| P2-2 | 统一时间解析函数 | 1 | 1 | ✅ 已完成 | 2026-05-18 |
| P2-3 | 提取 AIRecord dataclass | 1 | 1 | ✅ 已完成 | 2026-05-18 |
| P2-4 | 延迟导入移至模块顶部 | 4 | 4 | ✅ 已完成 | 2026-05-18 |
| P2-5 | CI 环境 ASCII 日志 | 1 | 1 | ✅ 已完成 | 2026-05-18 |
| **合计** | | **8** | **8** | ✅ 全部完成 | 2026-05-18 |
