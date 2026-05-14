# 变更日志

所有重要变更均记录于此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

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
