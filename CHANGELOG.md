# 变更日志

所有重要变更均记录于此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [v4.2.6] - 2026-05-19

### 🐛 修复

- **Release 时间窗口因 `last_release_checked` 丢失而重置** — deep/force_refresh 模式下 `_classify_item()` 重新分类时遗漏 `existing.last_release_checked`，导致下次 release 检查窗口退回到 7 天前，旧 release 被误判为新 release。`engine.py:410` 补全字段保留
- **`sqlite_backend.py` 缺少 `last_release_checked` 列** — SQLite schema、`_COLUMN_MAP`、`_row_to_item` 均未包含该字段，使用 SQLite 后端时 `last_release_checked` 完全无法持久化。三处一并补齐；`_ensure_schema` 会自动 ALTER TABLE 添加新列
- **`import_helper.py` / `lists_manager.py` 导入时遗漏 release 字段** — JSON/CSV 导入和 Lists 迁移未设置 `last_release_tag` / `last_release_checked` / `subscribe_releases`，导入后首次 release 检查窗口错误回退
- **候选进度提示误导** — `consecutive_runs >= WATCHLIST_THRESHOLD` 但置信度不足时仍显示"需再观察 0 次"，用户误以为即将升级。改为"次数达标但置信度不足 (X% < 50%)"
- **Release 区域文案误导** — 新收录项目的 release 显示为"收录于 X天前"，但 X天前是 release 发布时间而非收录时间。统一改为"released X天前 🆕 新收录"，时间语义清晰
- **规范审查修复** — 全局一致性审查发现 7 项不符合 conventions.md 的问题
  - `discover_ecologies_stage.py` 4 处 `except Exception` 未按 §4.3 细分（`_save_auto_ecologies`/`_get_repo_slug`/`_propose_blocklist_via_issue`/`discover_ecologies_stage`）
  - `blocklist_command.py` / `ecology_blocklist.py` 函数内延迟导入违反 §6.2，移至文件顶部
  - `ecology_blocklist.py` `NOISE_WORDS` 定义后从未使用（死代码），整合到 `_infer_indicator` 优先排除逻辑

### 🆕 新增

- **Phase 7 分类修正简化** — 用户只需提供最小信息，系统自动补全当前分类
  - 新建 `scripts/ci/enrich_correction_issue.py`：解析 issue 中的 `full_name`，读取数据库获取当前分类，在 issue 下自动评论补全信息供审核参考
  - `.github/workflows/process-feedback.yml` 在 apply_feedback_correction.py 之前增加 enrich 步骤

### 🔧 改进

- **分类修正 Issue 模板精简** — `.github/ISSUE_TEMPLATE/classification-correction.yml` 去掉"当前分类"输入（改为 Action 自动补全），"修正字段"改为复选框多选，"建议分类"改为 textarea + markdown 格式约定
- **报告修正链接预填充格式** — `report.py` `_feedback_url()` body 预填充 markdown 代码块格式，与新版模板对齐

---

## [v4.2.5] - 2026-05-19

### 🆕 新增

- **Phase 6 生态排除统一化** — 用户只需提供候选生态名称，系统自动从候选池推断待排除项并更新 blocklist
  - 新建 `scripts/ecology_blocklist.py`：统一核心 `exclude_ecology()` + `apply_exclusion()`，本地 CLI 与 GitHub Action 共用
  - 新建 `scripts/blocklist_command.py`：参照 `correct_command.py` 模式，支持 `--exclude-ecology 候选名`
  - `scripts/classifier.py` 新增 `--exclude-ecology` 参数，快捷排除不运行完整流水线
  - 新建 `.github/workflows/process-ecology-blocklist.yml`：监听 `生态-blocklist` label，自动调用核心逻辑更新 yaml 并关闭 issue
  - 新建 `scripts/ci/apply_ecology_blocklist.py`：解析 issue body 中的候选名，调用 `exclude_ecology()`

### 🔧 改进

- **生态 Blocklist Issue 模板简化** — `.github/ISSUE_TEMPLATE/ecology-blocklist.yml` 精简为只保留"候选生态名称" + 可选补充说明
- **报告 blocklist 链接预填充** — `report.py` 🚫 链接正文预填充候选名称，方便一键创建 issue
- **`ecology_candidates.py` 修复负数显示** — `consecutive_runs > threshold` 时进度文本显示负数，改为 `max(..., 0)`

---

## [v4.2.4] - 2026-05-19

### 🔧 改进

- **异常捕获细化（6 处）** — 按 `roadmap-pending.md` 任务四完成遗留代码的异常类型细分，遵守 `conventions.md` §8.2 / §4.2
  - `llm_classifier.py` `classify()` / `_classify_batch()`：`except Exception` → `except (json.JSONDecodeError, ValueError[, KeyError])`
  - `engine.py` `process()`：`except Exception` → `except (KeyError, ValueError, TypeError)`
  - `ecology_discovery.py` `_load_blocklist()`：`except Exception: pass` → `except (OSError, yaml.YAMLError)` + log
  - `discover_ecologies_stage.py` `_load_auto_ecologies()` / `_llm_review_watchlist()`：同上细分 + 补充日志

---

## [v4.2.2] - 2026-05-18

### 🆕 新增

- **P1 预分类增强** — 调用 LLM 前基于 topics + 项目名做语义预分类，结果注入 prompt 供 LLM 参考修正。从 `ecologies.yaml` 的 `topic_patterns`/`core_projects` 自动推导映射 + 30+ 条手动覆盖（Neovim/VS Code/MPV/Clash/Docker 等）
- **生态 Blocklist 远程自动提交** — 当噪声候选（如 `android`/`cli` 等平台/类型关键词）满足条件时，自动创建 GitHub Issue 提议加入 `ecology_blocklist.yaml`，7 天防重复
- **P3 分类一致性自检** — 报告渲染时自动检查分类逻辑一致性，命中规则（编辑器生态但平台非桌面端、代理工具但类型非工具、框架 stars 过少、核心角色 stars 过少、独立项目但名称/topics 命中生态规则）的项目在生态列显示 ⚠️ 标记，悬停显示具体原因

### 🔧 改进

- **文档同步更新** — README 文件树补全 `docs/plans/` 和 `docs/reviews/`、`docs/conventions.md` 路径修正、review 报告内部链接更新
- **项目版本号去 V4** — README 标题、CLI 描述、User-Agent、模板页脚等去掉显式 v4 标注，保留 CHANGELOG 历史记录
- **计划文档状态修正** — `classification_optimization.md` 从虚假"全部完成"修正为各子项真实状态

### 🐛 修复

- **`ecology_candidates.py` 重复定义** — `save()` / `load()` 各定义两次，第二个覆盖第一个导致 `proposed_blocklist` 持久化逻辑丢失。合并为单一实现
- **`EcologyCandidateState` 序列化规范** — 缺少 `to_dict()` / `from_dict()`，`save()` 直接使用 `asdict()` 违反 §1.2。添加标准序列化方法，改用 `v.to_dict()`
- **时间戳 naive/aware 比较** — `_was_recently_proposed` 和 `_cleanup_expired` 解析 ISO 时间戳后未检查 `tzinfo is None`，与 `datetime.now(timezone.utc)` 做减法会抛出 `TypeError`。统一添加 `tzinfo is None → replace(tzinfo=timezone.utc)` 处理
- **异常捕获过于宽泛** — 多处 `except Exception: pass` 和 `except Exception as e` 未细分异常类型，违反 §8.2。细分为 `OSError` / `json.JSONDecodeError` / `ValueError` / `TypeError`
- **局部导入清理** — `_load_blocklist` / `_load_manual_blocklist` / `_row_data` 中的局部 `import os` 和 `from config_rules import ...` 移到模块顶部
- **`check_consistency` 逻辑错误** — 使用不存在的 platform 值 `"桌面端"`（PLATFORM_RULES 中无此值）。删除该值，仅保留有效 platform

### 🏗 架构

- **生态候选反馈闭环** — 周报 HTML 和 `ecology_discovery.md` 中每个候选添加 🚫 反馈图标，点击直达 `ecology-blocklist.yml` Issue 模板

---

## [v4.2.3] - 2026-05-18

### 🆕 新增

- **生态候选展开查看全部示例项目** — 周报 HTML 中生态候选默认显示前 3 个示例项目，超过 3 个时显示"展开全部 (N) ▼"按钮，点击展开查看剩余全部项目（复用现有 `wet()` JS 函数）

### 🔧 改进

- **生态候选示例项目展示** — `ecology_discovery.md` 示例项目从纯文本改为可点击的 GitHub 链接列表；候选池状态表格新增"示例项目"列显示前 3 个项目

---

## [v4.2.1] - 2026-05-17

### 🐛 修复

- **`config.py` 导入错误** — 相对导入 `from .config_rules import ...` 在直接运行 `python scripts/classifier.py` 时因无包上下文而失败，改为绝对导入
- **`ai_database.py` StarItem 兼容性** — `migrate_from_stars_db()` 使用 `hasattr/else item.get()` 模式，当 `StarItem` 无目标字段时 fallthrough 到 `.get()` 报错（`'StarItem' object has no attribute 'get'`）。统一为 `_get()` helper，通过 `isinstance(obj, dict)` 判断后分别使用 `dict.get()` / `getattr()`

### 🔧 改进

- **统一「独立项目」生态名称** — 消除 `独立项目 / Standalone` 与 `独立项目` 的重复。`StarItem` 默认值、`ECOLOGY_ALIASES` 目标值、`ECOLOGY_STANDARD_NAMES` 全部统一为 `独立项目`，涉及 14 个文件
- **生态发现噪声过滤** — `ecology_discovery.py` 的 `NOISE_TOPICS` 从硬编码改为自动推导：从 `PLATFORM_RULES`、`TYPE_RULES`、`ecology_rules`、`ECOLOGY_STANDARD_NAMES`、`ECOLOGY_ALIASES` 自动提取关键词。Android / Dart / Cli 等平台/类型/已有生态不再被误识别为候选生态
- **生态发现手动 blocklist** — 新增 `scripts/ecology_blocklist.yaml`，支持手动补充排除特定 topic/前缀。修改后随代码提交，Actions 自动生效
- **候选池 blocklist 清理** — `ecology_candidates.py` 的持久化候选池 `ecology_candidates.json` 也加载 blocklist，初始化时自动将历史遗留的误识别候选（Android / Dart / Cli 等）标记为 `rejected`，不再出现在报告中

---

## [v4.2.0] - 2026-05-17

### 🆕 新增

- **`conventions.md` 全局一致性规范** — 涵盖数据模型、存储接口、分类器接口、异常处理、Pipeline 阶段、命名与导入、配置、日志等 9 大规范领域
- **生态规则 YAML 化** — 73 个重复结构的 Python 生态文件迁移到 `data/ecologies.yaml`，新增生态只需修改 YAML，无需新建 .py 文件
- **Jinja2 模板引擎** — `report.py` 内嵌 300+ 行 HTML 字符串改为 `report_template.html` 模板渲染，代码-视图分离
- **Pipeline 拓扑排序** — `StageRegistry` 使用 Kahn 算法按依赖关系排序执行，新增/调整阶段顺序不再破坏依赖
- **通用 Git 提交 Action** — `.github/actions/commit-and-push/action.yml`，多 workflow 共用

### 🔧 改进

- **Repository 接口统一** — `Repository` ABC 新增 `close()` 方法；`AIDatabase` 补齐 `delete/keys/values/items/__len__`；`JSONAIRepository` 添加独立 meta 存储
- **异常处理链修复** — `HTTPClientError`（底层）→ `GitHubServerError`（中层）分层转换，调用方始终收到语义清晰的异常
- **时间解析统一** — 提取 `utils.parse_iso()` 统一处理 ISO 8601 / Z 后缀 / naive datetime，替换 4 处重复代码
- **序列化方式统一** — `StarItem` 与 `AIResult` 的 `to_dict()` 统一为浅拷贝 `getattr`；`from_dict()` 统一添加默认值兜底
- **LLM 重试统一** — Provider 层抛 `RuntimeError` 表示 HTTP 错误，Client 层统一捕获并重试（覆盖 429/5xx/网络错误）
- **SQLite 列名解耦** — `_COLUMN_MAP` 映射表替代人工同步的列名列表和 tuple 顺序，新增字段零风险
- **apply_preset 无副作用** — 使用 `copy.copy(args)` 避免修改原始参数对象
- **config.py 相对导入** — 绝对导入改为相对导入，支持从任意目录导入
- **219 个测试通过** — 新增 `test_correct_command.py`（8 用例）、SQLite 后端测试（8 用例）、Pipeline 依赖验证测试等

### 🗑 遗留清理

- **删除 `data/learned_rules.py`** — 旧 .py 格式规则补丁，代码已只使用 .json 格式
- **清理未使用导入** — `sys`（utils.py）、`asdict`（models.py、ai_database.py）、`Counter`（engine.py）
- **更新过时注释** — config_rules.py（生态 YAML 化说明）、rule_classifier.py（移除 .py 回退说明）
- **统一 re 导入位置** — github_api.py 中 `import re` 从方法内部移至模块顶部
- **删除过时 V1 审查报告** — 5 个文件已被 V2 完全替代
- **为 `06_ecologies_v2.md` 添加 YAML 化历史注明**

### 🏗 架构

- **存储层完整性** — 全部 4 个 Repository 实现（StarsDB / AIDatabase / JSONStarsRepository / JSONAIRepository / SQLiteStarsRepository）接口对齐，支持 `close()` 统一释放

---

## [v4.1.0] - 2026-05-14

### 🆕 新增

- **模型配置中心 `model_profiles.py`** — 独立模块管理所有 AI 提供商模型参数。新增模型只需注册一行，零侵入业务代码
- **xiaomimimo 多模型预设** — 新增 `xiaomimimo-v2.5`（¥14/1M）和 `xiaomimimo-pro`（¥21/1M）预设，默认 `xiaomimimo` 改为性价比最高的 `mimo-v2-flash`（¥2.1/1M）
- **Reasoning 模型兼容** — 自动识别 reasoning/thinking 模型，content 为空时从 `reasoning_content` 提取 JSON；system prompt 自动追加"不要思考过程"指令
- **Actions 实时进度** — `PYTHONUNBUFFERED=1` + `flush=True`，LLM batch 进度在 Actions 日志中实时可见
- **3 轮 batch 重试策略** — batch 失败不回退到单条，统一收集失败后集中重试，最多 3 轮，避免调用次数爆炸
- **连续失败保护** — 单轮内连续 3 个 batch 失败自动终止，防止无底洞式 token 消耗

### 🔧 改进

- **max_tokens 大幅提升** — batch: 640→8192 / single: 256→4096 / summarize: 128→2048（针对 reasoning 模型 thinking 过程预留空间）
- **System prompt 精简** — 去掉可选值列表（节省约 500 tokens），减少 prompt 占用
- **全局间隔下放** — 移除 `_setup_llm` 中的全局间隔大闸，由 `_needs_llm()` 按项目级策略全权决定
- **失败状态持久化** — LLM 失败项目写入 `stars_ai.json` 并标记 `status="failed"`，避免下次重复浪费 token
- **llm_enhanced 统计修正** — 从"batch 返回数"改为"实际被 `_apply_llm_override` 覆盖的项目数"
- **API 指数退避重试** — 429/5xx 时自动重试 3 次，间隔 1s→2s→4s
- **Notion/CSV AI 字段注入** — 同步前自动注入 AI 数据库字段
- **Release 展开按钮修复** — `onclick="wrt(this)"` → `onclick="wtn(this)"`，函数名对齐
- **Actions deep 模式联动** — `auto` 模式下 deep 模式也自动启用 LLM（之前只有 full）

## [v4.0.0] - 2026-05-10

### 🆕 新增

- **周报 Tab 化** — 周报从单一折叠面板改为顶部 Tab 切换：新收录 / 本周热门 / 分类变更 / Release / Fork，每个区域独立统计和导航
- **Release Notes 展开显示** — 每个 Release 下方直接显示 body 前 300 字，点击"展开"查看完整内容，无需 LLM 也能了解更新内容
- **独立 Release 历史页面** — 新增 `releases.html`，汇总所有检测到的历史 Release，支持按时间排序、显示 Markdown 渲染后的更新日志
- **本周热门** — 追踪已有项目 stars 增长量 Top 10，在周报中展示增长幅度
- **分类变更追踪** — 自动检测项目的 platform / type / ecology / ecology_role 变化并在周报中高亮
- **Fork 上游更新** — 自动检测 Fork 仓库是否有上游推送更新，7 天内的新更新才纳入周报
- **Release 周报** — 全量监控已 Star 仓库的新版本发布，支持一周内同一仓库多次发布的捕获
- **AI 动态总结** — LLM 可用时生成自然语言周报摘要；不可用时自动回退为规则文本总结（如"本周新收录 3 个；5 个 stars 增长；1 个 Release"）

### 🔧 改进

- **LLM Preset 预设** — 新增 `--llm-preset` / `LLM_PRESET`，一行同时绑定 provider + base + model，换服务商只需改一个值。内置 `openai` / `moonshot` / `deepseek` / `openrouter` / `xiaomimimo` 5 个预设
- **无 LLM 场景优化** — LLM 不可用时，Release 区域仍保留完整的 body 展开阅读；AI 摘要栏自动隐藏；总结栏使用规则文本代替
- **新收录判定修复** — 不再依赖 `first_seen` 时间戳（存在误判），改为通过 `engine.new_keys` 记录本次实际新增项目
- **Fork 7 天过滤** — 只检测最近 7 天内的上游更新，避免显示过时数据
- **执行顺序修复** — `_track_releases` / `_track_forks` 移至 `_generate_reports` 之前，确保数据收集完成后才生成报告
- **Release Notes 渲染** — 简单的 Markdown → HTML 转换器（ headings / lists / code / links / bold ）

### 🏗 架构

- **双库架构** — 规则分类 (`stars_db.json`) 与 AI 分析 (`stars_ai.json`) 完全解耦，报告渲染时动态合并
- **三层时间控制** —
  1. `auto_refresh_days` (90天): 自动全量刷新规则分类
  2. `llm_interval_days` (30天): 全局 LLM 启用间隔
  3. `ai_db.analyzed_at`: 单项目 LLM 分析追踪
- **AI 数据库独立** — `scripts/ai_database.py`（`AIResult` + `AIDatabase`），LLM 字段从主库完全解耦
- **向后兼容** — `AIDatabase.migrate_from_stars_db()` 自动迁移旧数据；`StarItem.from_dict()` 忽略未知字段

## [v3.0.0] - 2026-04-25

### 🆕 新增

- **LLM 全局介入** — 不再受 `--incremental` 限制，新项目 + 间隔到期老项目均重新分析
- **自动全量刷新** — `--auto-refresh-days` (默认 90)，增量模式运行到期自动升级为全量刷新
- **Release Digest** — 可选 LLM 对 Release body 生成 20-30 字 AI 摘要
- **Actions 行为一致性** — `workflow_dispatch` 默认值优化；`schedule` 默认 `--check-all-releases`

### 🔧 改进

- **LLM 间隔控制** — `--llm-interval-days` (默认 30) + `--force-llm`，全局元数据记录时间戳
- **CLI 参数补全** — 补缺失的 `--check-all-releases` / `--llm-release-digest` 参数
- **代码清理** — 全局审查后消除重复逻辑与脆弱代码

## [v2.0.0] - 2026-04-10

### 🆕 新增

- **增量更新引擎** — `scripts/engine.py`，支持新/旧/保护/强制刷新四种处理模式
- **手动修正保护** — `manual_override` 标记的项目永久不被覆盖
- **Notion 导出** — 一键同步到 Notion 数据库
- **多通道通知** — 邮件 / Telegram / 企业微信 / QQ（go-cqhttp）
- **GitHub Lists 导入** — 首次运行时可从 GitHub Lists 迁移已有分类
- **Release 跟踪** — 基础版本检测和通知
- **Fork 跟踪** — 基础上游更新检测

### 🔧 改进

- **数据模型** — `StarItem` dataclass，支持 dict 兼容层
- **原子写入** — `database.py` JSON 持久化防止写入损坏
- **HTTP 双后端** — requests / urllib 自动降级

## [v1.0.0] - 2026-03-20

### 🆕 新增

- **基础分类** — 平台 / 类型 / 语言 / 生态归属四维规则分类
- **HTML 报告** — 暗色主题交互式页面，支持筛选
- **GitHub Actions 定时执行** — 每周一自动运行
