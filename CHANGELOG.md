# 变更日志

所有重要变更均记录于此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

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

- **`docs/conventions.md` 全局一致性规范** — 涵盖数据模型、存储接口、分类器接口、异常处理、Pipeline 阶段、命名与导入、配置、日志等 9 大规范领域
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
