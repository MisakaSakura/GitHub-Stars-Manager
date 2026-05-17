# GitHub Stars 自动分类工具 v4

自动为你的 GitHub Stars 按 **平台、类型、语言、生态归属** 四维分类，生成可搜索的 HTML 报告和周报摘要，支持 LLM 智能增强、增量更新、手动修正保护、Notion 导出、多通道通知、Release 跟踪、Fork 上游跟踪。

> 📌 **设计目标说明**：本工具是 **本地分类报告生成器**，不是 GitHub Lists 的同步客户端。分类结果存储在仓库的 `data/stars_db.json` 中，并通过 GitHub Pages 部署为 HTML 报告。由于 GitHub 目前未公开 Lists 的写入 API，工具 **不会自动修改你账号中的 GitHub Lists**（Lists 仅作为可选的初始导入源）。

🔗 **在线报告**: 部署后访问 `https://你的用户名.github.io/你的仓库名/`

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 🌿 **生态归属** | 自动识别项目族谱（Clash、MPV、VS Code、Neovim 等 74+ 生态，YAML 配置） |
| 🤖 **LLM 智能增强** | 支持 OpenAI / Moonshot / DeepSeek / xiaomimimo / OpenRouter，自动补全规则分类盲区 |
| 📦 **增量更新** | 只处理新 star 的项目，已有分类保持不变 |
| 🔒 **手动修正保护** | `manual_override` 标记的项目永久不被覆盖 |
| 📝 **Notion 导出** | 一键同步到 Notion 数据库 |
| 📧 **多通道通知** | 邮件 / Telegram / 企业微信 / QQ（go-cqhttp） |
| 📋 **GitHub Lists 导入** | 首次运行时可从 GitHub Lists 迁移已有分类（单向导入，不反向同步） |
| 🔔 **Release 周报** | 全量监控已 Star 仓库的新版本发布，按生态/平台聚合周报 |
| 🍴 **Fork 上游跟踪** | 检测 Fork 项目是否有上游更新 |
| ⏰ **定时自动执行** | GitHub Actions 每周自动运行 |
| 📊 **可视化报告** | 暗色主题交互式 HTML，支持筛选和生态视图 |
| 🧪 **测试覆盖** | 219 个测试覆盖核心逻辑，全部通过 |

---

## 快速开始

### 1. 创建仓库

新建 GitHub 仓库，复制以下文件结构：

```
.
├── .github/workflows/classify-stars.yml   ← 定时工作流
├── .github/workflows/process-feedback.yml ← 反馈处理工作流
├── scripts/
│   ├── classifier.py              ← CLI 入口（参数解析）
│   ├── orchestrator/
│   │   ├── new_pipeline.py        ← 18 阶段插件化流水线
│   │   ├── context.py             ← Pipeline 共享上下文
│   │   ├── registry.py            ← 阶段注册器（拓扑排序）
│   │   └── stages/                ← 18 个独立阶段模块
│   ├── engine.py                  ← 增量更新引擎
│   ├── models.py                  ← StarItem 数据模型
│   ├── database.py                ← Stars 主数据库（JSON）
│   ├── ai_database.py             ← AI 分析结果独立数据库
│   ├── repositories/
│   │   ├── base.py                ← Repository 抽象基类
│   │   ├── json_backend.py        ← JSON 存储适配器
│   │   └── sqlite_backend.py      ← SQLite 存储适配器（实验性）
│   ├── github_api.py              ← GitHub REST API 封装
│   ├── http_client.py             ← HTTP 客户端（requests / urllib 双后端）
│   ├── rule_classifier.py         ← 规则分类器
│   ├── llm_classifier.py          ← LLM 分类器 Facade
│   ├── llm/                       ← LLM 分层子包
│   │   ├── client.py              ← LLM 统一客户端
│   │   ├── parser.py              ← 响应解析器
│   │   ├── cache.py               ← TTL 缓存
│   │   └── providers/             ← Provider 实现
│   ├── ecologies/                 ← 生态规则（YAML 加载）
│   ├── report.py                  ← HTML / CSV / JSON 报告生成
│   ├── notion.py                  ← Notion 数据库导出
│   ├── notify.py                  ← 多通道通知分发
│   ├── lists_manager.py           ← GitHub Lists 管理
│   ├── release_tracker.py         ← Release 发布跟踪
│   ├── fork_tracker.py            ← Fork 上游跟踪
│   ├── base_tracker.py            ← 跟踪器基类
│   ├── import_helper.py           ← JSON / CSV 导入工具
│   ├── model_profiles.py          ← AI 模型配置中心
│   ├── consistency_checker.py     ← 分类一致性检查
│   ├── feedback_loop.py           ← 反馈循环系统
│   ├── correct_command.py         ← 快捷修正命令
│   ├── ecology_discovery.py       ← 生态自动发现（P4）
│   ├── ecology_blocklist.yaml     ← 生态发现手动排除列表
│   ├── config.py                  ← 向后兼容配置总入口
│   ├── config_rules.py            ← 分类规则配置
│   ├── config_llm.py              ← LLM 配置
│   ├── config_notion.py           ← Notion 配置
│   ├── config_notify.py           ← 通知配置
│   └── utils.py                   ← 工具函数
├── data/
│   ├── stars_db.json              ← 持久化数据库（首次运行后生成）
│   ├── stars_ai.json              ← AI 分析结果数据库（与主库解耦）
│   ├── ecologies.yaml             ← 生态规则配置（74+ 生态）
│   └── learned_rules.json         ← 用户反馈学习规则
├── docs/
│   ├── index.html                 ← 报告（首次运行后生成）
│   ├── releases.html              ← Release 历史页面
├── conventions.md                 ← 全局一致性规范文档
└── tests/                         ← 测试目录（219 个测试）
```

### 2. 配置 Secrets

在仓库 **Settings → Secrets and variables → Actions** 中添加：

| Secret | 必填 | 说明 |
|--------|------|------|
| `GH_TOKEN` | ✅ | GitHub Personal Access Token（无需额外权限） |
| `LLM_KEY` | ❌ | LLM API Key（启用智能分类） |
| `NOTION_KEY` | ❌ | Notion Integration Token |
| `NOTION_DB` | ❌ | Notion Database ID |
| `EMAIL_USER` | ❌ | SMTP 用户名（邮件通知） |
| `EMAIL_PASS` | ❌ | SMTP 密码/应用专用密码 |
| `TG_BOT_TOKEN` | ❌ | Telegram Bot Token |
| `TG_CHAT_ID` | ❌ | Telegram Chat ID |
| `WECOM_WEBHOOK` | ❌ | 企业微信机器人 Webhook URL |
| `QQ_API_URL` | ❌ | go-cqhttp API 地址 |
| `QQ_GROUP_ID` | ❌ | QQ 群号（通知用） |

> 💡 **GH_TOKEN 获取**: [GitHub Settings → Tokens](https://github.com/settings/tokens) → Generate new token (classic) → 无需勾选任何 scope，建议选 **No expiration**（无限期）

### 3. 启用 GitHub Pages

仓库 → **Settings → Pages** → 在 **Build and deployment** 区块中，Source 下拉菜单选择 **GitHub Actions**

### 4. 配置 Actions 写入权限

仓库 → **Settings → Actions → General** → 页面最下方 **Workflow permissions** → 选择 **✅ Read and write permissions** → 点击 **Save**

> ⚠️ 这一步是必须的，否则 Actions 无法提交数据库更新到仓库。

### 5. 首次运行

进入 **Actions → Auto Classify GitHub Stars → Run workflow**

> 💡 **报告范围说明**：
> - 首次运行：全量分类你所有的 Stars，生成 **完整报告**（显示所有项目）
> - 后续增量运行：只处理新 Star 的项目，但报告仍然是 **全量重新生成** 的
> - 每周变化（新增项目 + 新 Release）会在报告的 "本周摘要" 区块中高亮显示
> - 如需查看纯增量变化，可查看通知消息或 Git commit diff

### Actions 运行模式

工具提供 **4 种运行模式**，通过 `mode` 参数一键切换。你不再需要手动组合 `--incremental`、`--force-refresh`、`--check-all-releases` 等细碎开关。

| 模式 | 作用 | 自动启用的功能 | LLM 行为 | 建议频率 | 耗时 |
|------|------|---------------|---------|---------|------|
| **`incremental`** ⭐ | 日常增量更新 | 增量拉取 + Release 检查 | 按间隔控制（需手动启用） | 每周（自动运行） | 3-5 min |
| **`deep`** | 深度整理 | 增量拉取 + **强制刷新规则** + Release + Fork | 按间隔控制（需手动启用） | 每月/每季度 | 15-25 min |
| **`full`** | 全量刷新 | **全量拉取** + 强制刷新 + Release + Fork + 订阅标记 | **auto 模式下自动启用 LLM** | 首次/年度/大幅调整规则后 | 20-35 min |
| **`custom`** | 自定义 | 完全由其他开关控制 | 完全手动控制 | 按需 | 不定 |

**模式详解**：

- **incremental（增量）**：只拉取最近 star 的项目，已有项目只更新 stars 数，分类不变。检查所有仓库的 Release 生成周报。**日常自动运行就是这个模式。**
- **deep（深度）**：在增量基础上，**对所有未保护项目重新执行规则分类**（`force-refresh`），同时检查 Release + Fork。适合验证规则是否有遗漏、分类是否合理。**⚠️ 未保护项目会被重新分类，如有满意的项目请先标记 `manual_override: true`。**
- **full（全量）**：**非增量拉取**（确保没有遗漏任何 Stars），对所有未保护项目重新规则分类，检查 Release + Fork，并标记所有仓库订阅 Release。适合首次运行、年度大扫除、或规则大幅调整后的全库梳理。
- **custom（自定义）**：保留给高级用户，可以单独控制 `--incremental`、`--force-refresh`、`--check-all-releases`、`--check-forks`、`--subscribe-releases` 等每个开关。

### 自动执行计划

每天 **10:17（北京时间）** 检查一次，按日期自动选择模式，**同一天只运行最高优先级模式**：

| 触发条件 | 模式 | 说明 | 耗时 | LLM |
|---------|------|------|------|-----|
| **每季度1日**（1月/4月/7月/10月） | `full` | 全量刷新：全量拉取 + 重新分类 + LLM 全量分析 + 订阅标记 | 20-35 min | ✅ 自动启用 |
| **每月1日**（非季度首月） | `deep` | 深度整理：增量拉取 + force_refresh 重新分类 + Fork 检查 | 15-25 min | ❌ 不启用 |
| **每周一**（非1日） | `incremental` | 日常增量：只处理新 star 项目 + Release 周报 | 3-5 min | ❌ 不启用 |
| **其他日子** | — | 跳过，不执行 | — | — |

**调度互斥**：同一天不会运行多次。如 1月1日是周一，只会运行 `full`（优先级最高），不会额外运行 incremental。

> 时间固定为北京时间 10:17（UTC 2:17），使用随机偏移避免 Actions 集群峰值。

**自动运行与手动运行的区别**：
- **自动运行**：按日期自动选择模式，无需人工干预
- **手动运行**：默认 `incremental`，可在 Actions 页面切换为 `deep` / `full` / `custom`

### Actions 手动运行选项说明

| 选项 | 默认值 | 用途 |
|------|--------|------|
| `mode` | **incremental** | 运行模式：`incremental` / `deep` / `full` / `custom` |
| `llm_mode` | auto | `auto` = 按 mode 联动；`off` = 关闭；`force` = 无视间隔 |
| `send_notify` | false | 发送通知到邮箱/QQ/TG/企业微信 |
| `sync_notion` | false | 同步到 Notion 数据库 |
| `lists_strategy` | ignore | 首次运行时处理 GitHub Lists |
| `retry_failed` | false | 重试之前 LLM 分析失败的项目 |

> 💡 **custom 模式专属开关**：`force_refresh`、`check_all_releases`、`check_forks`、`subscribe_releases`。其他模式下这些开关由 `mode` 自动控制。

---

### 🤖 Actions LLM 部署指南

#### 1. 选择 LLM 提供商

| 提供商 | 推荐模型 | 特点 | 适用场景 |
|--------|----------|------|----------|
| **xiaomimimo** | `mimo-v2-flash` | ¥2.1/1M，全系 reasoning，max_tokens 需设大 | 🇨🇳 国内性价比首选（flash 版） |
| **Moonshot (Kimi)** | `moonshot-v1-8k` | 国内访问稳定，中文理解好 | 🇨🇳 国内用户备选 |
| **DeepSeek** | `deepseek-chat` | ¥2/1M，reasoning 模型，价格便宜 | 💰 性价比备选 |
| **OpenAI** | `gpt-4o-mini` | 速度快，分类准确，非 reasoning | 🌐 有海外访问条件 |
| **OpenRouter** | `anthropic/claude-3.5-sonnet` 等 | 聚合平台，可自由切换模型 | 🔧 需要灵活切换 |
| **兼容 OpenAI 的服务** | 视服务商而定 | 复用 OpenAI SDK，只需改 Base URL | 🔌 已有 API 代理或私有化部署 |

> ⚠️ **Reasoning 模型注意**：xiaomimimo 全系（flash/v2.5/pro）和 DeepSeek-R1 都是 reasoning 模型，会在 `reasoning_content` 中进行链式思考。如果 `max_tokens` 不够大，思考过程会耗尽额度导致 `content` 为空。工具已自动适配：batch 8192 / single 4096 / summarize 2048。

#### 2. 获取 API Key

| 提供商 | 获取地址 | 免费额度 |
|--------|----------|----------|
| Moonshot | [platform.moonshot.cn](https://platform.moonshot.cn) → API Key 管理 | 新用户有 ¥15 赠送 |
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) → API Keys | 新用户有 ¥10 赠送 |
| OpenAI | [platform.openai.com](https://platform.openai.com) → API keys | 需绑卡，按量计费 |
| OpenRouter | [openrouter.ai/keys](https://openrouter.ai/keys) | 部分模型有免费额度 |

#### 3. 配置 Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**：

| Secret | 值 |
|--------|-----|
| `LLM_KEY` | 你的 API Key（完整字符串，不要加引号） |

> ⚠️ **安全提示**：Secret 一旦保存不可查看，只能删除后重新添加。建议先在本地文本编辑器确认 Key 正确再粘贴。

#### 3.5 配置 LLM 预设（推荐）

`LLM_BASE` 和 `LLM_MODEL` 总是一一对应、同时生效、同时废弃，分开管理没有意义。使用 **Preset（预设）** 一行同时搞定 provider + base + model：

**方式 A：Repository Variable `LLM_PRESET`（最推荐）**

进入仓库 **Settings → Secrets and variables → Actions → Variables → New repository variable**：

| Variable | 值 | 说明 |
|----------|-----|------|
| `LLM_PRESET` | `xiaomimimo` | 预设名称，自动映射到对应的 provider / base / model |

可用预设：

| Preset | Provider | Base URL | Model |
|--------|----------|----------|-------|
| `openai` | openai | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `moonshot` | moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| `deepseek` | deepseek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| `openrouter` | openrouter | `https://openrouter.ai/api/v1` | `openrouter/auto` |
| `xiaomimimo` ⭐ | openai | `https://api.xiaomimimo.com/v1` | `mimo-v2-flash` |

配置了 `LLM_PRESET` 后，无论是手动触发还是自动运行，都会自动使用该预设的完整配置，无需每次填写。

**方式 B：通过 Variable 创建多个自定义预设（不修改代码）**

如果内置预设不够用，可以在同一个 Variable 里定义多个自己的预设：

| Variable | 值示例 | 说明 |
|----------|--------|------|
| `LLM_PRESETS` | `mycompany\|openai\|https://llm.mycompany.com/v1\|company-v1;azure\|openai\|https://xxx.azure.com/v1\|gpt-4o` | 多个预设，用 `;` 分隔，格式为 `名称\|provider\|base\|model` |

定义后通过 `LLM_PRESET=mycompany` 或 Actions 输入 `mycompany` 直接使用。格式规则：
- 多个预设用 `;` 分隔
- 每个预设格式：`名称|provider|base_url|model`
- 示例：`mycompany|openai|https://llm.mycompany.com/v1|company-v1;azure|openai|https://xxx.azure.com/v1|gpt-4o`

**方式 C：单独配置（向后兼容）**

如果你需要覆盖 preset 中的某个字段，仍可单独配置：

| Variable | 值 | 说明 |
|----------|-----|------|
| `LLM_BASE` | `https://api.xxx.com/v1` | 兼容服务 Base URL，**必须** 以 `/v1` 结尾 |
| `LLM_MODEL` | `model-name` | 默认模型 |

**优先级**（从高到低）：
1. **`LLM_PRESETS`** Variable 中的自定义预设
2. `config_llm.py` 中的 `CUSTOM_PRESETS`
3. 内置预设（`PROVIDER_PRESETS`）
4. `LLM_BASE` / `LLM_MODEL` Variable（向后兼容）
5. `config_llm.py` 中的 `LLM_CONFIG`
6. Provider 内置默认值

#### 4. 首次启用 LLM

进入 **Actions → Auto Classify GitHub Stars → Run workflow**，按以下配置：

| 参数 | 推荐设置 | 说明 |
|------|----------|------|
| `mode` | **`full`** | 首次运行建议全量模式，自动启用所有必要检查 |
| `llm_mode` | **`auto`** | `auto` = 按 mode 联动（full 自动启用）；`off` = 关闭；`force` = 无视间隔 |
| `llm_preset` | 你的预设 | `xiaomimimo` / `deepseek` / `openai` 等；也可输入自定义预设名 |
| `retry_failed` | `true`（可选） | 重试之前 AI 分析失败的项目 |
| `sync_notion` | `false` | `true` = 同步；`clear` = 先清空再同步（危险） |
| `notify` | `false` | `email` / `telegram` / `wecom` / `qq` / `all` |
| `lists_strategy` | `migrate`（如有 Lists） | 从 GitHub Lists 迁移已有分类 |

点击 **Run workflow** 后等待 5-10 分钟（取决于项目数量）。运行成功后：
1. 查看 Commit → 确认 `stars_db.json` 和 `stars_ai.json` 有更新
2. 查看 Pages 报告 → 项目卡片上会出现 🤖 标记表示 LLM 增强
3. 检查分类结果 → 不满意的手动编辑 `stars_db.json` 并设置 `manual_override: true`

#### 5. 日常使用模式

| 场景 | mode | LLM | 频率 | 耗时 |
|------|------|-----|------|------|
| **自动周报** | `incremental`（自动） | ❌ | 每周 | 3-5 min |
| **LLM 维护** | `incremental` | `llm_mode=force` | 每月 1 次 | 8-15 min |
| **深度整理** | `deep` | `llm_mode=force` | 每季度或调整规则后 | 15-25 min |
| **首次/年度大扫除** | `full` | **自动启用**（配置了 LLM_KEY 时） | 首次/每年 | 20-35 min |

> 💡 **LLM 模式简化**：`auto` 按 mode 自动判断；`off` 明确关闭；`force` 无视间隔强制分析。无需再纠结 use_llm + force_llm 的组合。
> 💡 **全量模式自动 AI**：`full` + `auto` 模式下如果配置了 `LLM_KEY` 会自动启用 LLM。

> 💡 **为什么自动运行默认不启用 LLM？** LLM 调用消耗 Token，而大部分用户的 Stars 变化量很小（每周几个新项目），自动启用会造成不必要的费用。建议每月手动触发一次 LLM 维护即可。

#### 6. Token 消耗与费用估算

> 工具已内置 **模型配置中心**（`scripts/model_profiles.py`），自动根据模型 ID 匹配最优 `max_tokens`、`batch_size`、`temperature`。新增模型只需注册一行，零侵入业务代码。

**各场景 max_tokens 自动匹配**：

| 场景 | 非 reasoning（gpt-4o-mini） | reasoning（mimo-v2-flash / deepseek-chat） |
|------|---------------------------|------------------------------------------|
| batch 分类（5个项目） | 2048 | **8192** |
| 单条分类 | 1024 | **4096** |
| 文本摘要 | 512 | **2048** |
| Release 摘要 | 512 | **2048** |

以 **400 个项目** 为例（首次全量分析）：

| 提供商 | 估算 Token | 参考费用 |
|--------|-----------|----------|
| DeepSeek (`deepseek-chat`) | ~80K | ~¥0.5 |
| Moonshot (`moonshot-v1-8k`) | ~80K | ~¥0.8 |
| OpenAI (`gpt-4o-mini`) | ~80K | ~$0.05 |

**后续增量费用**（每月 10 个新项目 + 30 天到期的 100 个老项目重新分析）：

| 场景 | 估算 Token | DeepSeek 费用 |
|------|-----------|---------------|
| 新项目（10 个） | ~2K | ~¥0.01 |
| 到期重分析（100 个） | ~20K | ~¥0.15 |
| **每月总计** | ~22K | **~¥0.16** |

> 💰 **省钱技巧**：`llm_interval_days` 默认 30 天，已分析成功的老项目不会每次都被重新调用。首次分析后，后续每月费用通常不到 ¥1。
>
> 📊 **全量分析 412 项目预估成本**：
> - `mimo-v2-flash`（¥2.1/1M）：~¥1.0-1.5
> - `deepseek-chat`（¥2/1M）：~¥0.9-1.3
> - `gpt-4o-mini`（~¥4.4/1M）：~¥2.0-3.0
> - `mimo-v2.5`（¥14/1M）：~¥6-8
> - `moonshot-v1-8k`（~¥12/1M）：~¥5-7

---

## ⚠️ 首次运行行为说明（重要）

### 场景 A：全新开始（没有已有分类）

**行为**：首次运行会自动创建 `stars_db.json`，对 **所有 star 项目执行全新分类**。

```bash
# 首次运行 - 全新分类所有项目
python scripts/classifier.py --token ghp_xxx --user yourname
```

**结果**：
- 所有项目按规则 + LLM（如果启用）自动分类
- 生成 `data/stars_db.json` 持久化存储
- **没有项目被保护**，后续运行可能根据规则变化重新分类

**建议**：首次运行后检查报告，对满意的项目手动添加保护：

```json
// 编辑 data/stars_db.json
{
  "full_name": "owner/repo",
  "manual_override": true,
  "override_fields": ["platform", "type", "ecology", "ecology_role"]
}
```

---

### 场景 B：已有分类，想保留旧标签

**行为**：使用 `--import-json` 或 `--import-csv` 导入已有分类，**导入的项目自动标记保护**，不会被覆盖。

```bash
# 方式 1: 从 JSON 导入（推荐）
python scripts/classifier.py   --token ghp_xxx --user yourname   --import-json ./my_old_tags.json

# 方式 2: 从 CSV 导入
python scripts/classifier.py   --token ghp_xxx --user yourname   --import-csv ./my_old_tags.csv

# 方式 3: 只导入，不自动分类新项目
python scripts/classifier.py   --token ghp_xxx --user yourname   --import-json ./my_old_tags.json   --no-auto-classify
```

**导入文件格式示例**：

**JSON 格式** (`my_old_tags.json`)：
```json
[
  {
    "full_name": "MetaCubeX/mihomo",
    "name": "mihomo",
    "owner": "MetaCubeX",
    "platform": "网络 / 代理",
    "type": "工具 / Tool",
    "ecology": "Clash / Mihomo 生态",
    "ecology_role": "核心 / Core",
    "language": "Go"
  }
]
```

**CSV 格式** (`my_old_tags.csv`)：
```csv
full_name,name,owner,platform,type,ecology,ecology_role,language
MetaCubeX/mihomo,mihomo,MetaCubeX,网络 / 代理,工具 / Tool,Clash / Mihomo 生态,核心 / Core,Go
```

**导入后行为**：
- ✅ 导入的项目：`manual_override = true`，**永久保护**
- ✅ 新增的项目：自动分类，**不受导入影响**
- ✅ 后续增量更新：导入项目永远跳过，新项目正常处理

---

### 场景 C：首次运行后，规则调整想重新分类

```bash
# 深度整理：重新规则分类所有未保护项目 + Release + Fork 检查
python scripts/classifier.py --token ghp_xxx --user yourname --mode deep

# 深度整理 + LLM 全量分析（验证规则盲区）
python scripts/classifier.py --token ghp_xxx --user yourname --mode deep --llm-key sk-xxx --force-llm
```

---

## 日常使用模式

### 增量更新（推荐日常用）

每周一自动执行，只拉取最近 star 的 300 个项目：
- **新项目** → 自动分类
- **已有项目** → 只更新 stars 数，分类不变
- **手动保护项目** → 完全跳过

```bash
# 等价于 --mode incremental（默认）
python scripts/classifier.py --token ghp_xxx --user yourname
```

### 深度整理

调整分类规则后，验证规则是否有遗漏，同时 LLM 增强：

```bash
python scripts/classifier.py --token ghp_xxx --user yourname --mode deep --llm-key sk-xxx --force-llm

# 或使用预设
python scripts/classifier.py --token ghp_xxx --user yourname --mode deep --llm-key sk-xxx --llm-preset xiaomimimo --force-llm
```

### 全量刷新

年度大扫除或规则大幅调整后，全库重新梳理：

```bash
python scripts/classifier.py --token ghp_xxx --user yourname --mode full --llm-key sk-xxx --force-llm
```

> ⚠️ `deep` / `full` 模式会覆盖所有 **未保护** 的自动分类，但 `manual_override = true` 的项目仍然跳过。

### GitHub Lists 集成

如果账号中存在 GitHub Lists，可以通过策略参数控制行为：

```bash
# 自动检测 Lists 并交互式提示（默认，仅在终端可用）
python scripts/classifier.py --token ghp_xxx --user yourname --lists-strategy auto

# 将 Lists 作为生态来源导入到数据库（跳过已存在的）
python scripts/classifier.py --token ghp_xxx --user yourname --lists-strategy migrate

# 清空所有 Lists，用数据库分类重建
python scripts/classifier.py --token ghp_xxx --user yourname --lists-strategy replace

# 忽略 Lists，不做任何操作
python scripts/classifier.py --token ghp_xxx --user yourname --lists-strategy ignore
```

---

## 手动修正分类

编辑 `data/stars_db.json`，找到项目并修改：

```json
{
  "full_name": "MetaCubeX/mihomo",
  "name": "mihomo",
  "ecology": "Clash / Mihomo 生态",
  "ecology_role": "核心 / Core",
  "platform": "网络 / 代理",
  "type": "工具 / Tool",
  "manual_override": true,
  "override_fields": ["ecology", "ecology_role", "platform", "type"]
}
```

commit 后，下次自动运行会 **完全跳过** 这个项目。

报告中的 🔒 标记表示手动保护，🤖 标记表示 LLM 增强。

---

## 分类体系参考

工具使用 **四个维度** 对项目进行归类：

```
┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   平台      │  │   类型      │  │   生态归属      │  │   生态角色      │
│  Platform   │  │   Type      │  │   Ecology       │  │   Ecology Role  │
└─────────────┘  └─────────────┘  └─────────────────┘  └─────────────────┘
     ↓                ↓                   ↓                    ↓
  操作系统/        应用形态 +         项目所属的           在生态中的
  运行时环境       功能角色            技术族谱             功能定位
```

### 平台（Platform）

项目运行的**操作系统或运行时环境**：

| 平台 | 关键词匹配 |
|------|-----------|
| **Android** | android, apk, aar, android-app |
| **iOS** | ios, swift, objective-c, objc, iphone, ipad, ipa |
| **Windows** | windows, win32, win64, uwp, wsl, winforms, wpf |
| **Linux** | linux, ubuntu, debian, fedora, arch, gentoo, redhat |
| **macOS** | macos, mac-os, osx, darwin, apple |
| **Web** | browser, web, html5, pwa, webapp |
| **跨平台** | cross-platform, multi-platform, electron, tauri, qt, flutter, react-native, xamarin |
| **其他 / 未分类** | 无匹配时 fallback |

> 平台 ≠ 生态。一个跨平台 GUI 工具（如 Electron 应用）平台为「跨平台」，生态可能属于「VS Code」或某个具体工具链。

### 类型（Type）

项目的**应用形态 + 功能角色**：

| 类型 | 说明 | 关键词匹配 |
|------|------|-----------|
| **框架 / Framework** | 供其他项目依赖的库/SDK | framework, library, sdk, runtime, engine |
| **工具 / Tool** | 单一用途的实用程序 | tool, utility, generator, builder, scaffold |
| **应用 / App** | 面向终端用户的完整应用 | app, application, client, service, portal |
| **Web 前端** | 浏览器端/UI 层技术 | frontend, react, vue, angular, svelte, webpack, vite |
| **Web 后端** | 服务端/API/数据库层 | backend, api, server, rest, graphql, fastapi, django |
| **移动端 App** | 手机/平板原生或混合应用 | mobile, ios-app, android-app, apk, cordova, capacitor |
| **桌面 GUI** | 桌面图形界面程序 | desktop, gui, nw.js, wxwidgets, gtk, native-app |
| **CLI / 终端** | 命令行工具 | cli, terminal, shell, command-line, bash, zsh, tmux |
| **游戏** | 游戏引擎、游戏本体、模拟器 | game, unity, unreal, godot, emulator, retroarch |
| **编辑器 / IDE** | 代码/文本编辑工具 | editor, ide, vscode, vim, neovim, emacs, text-editor |
| **资源合集 / Awesome** |  curated 列表、awesome 系列 | awesome, list, curated, resources, cheatsheet |
| **语言 / Compiler** | 编程语言/编译器/解释器 | language, compiler, interpreter, transpiler |
| **监控 / 可视化** | Dashboard、指标、图表 | monitoring, dashboard, visualization, metrics, grafana |
| **自动化 / 工作流** | 自动化脚本、CI/CD、机器人 | automation, workflow, integration, bot, cron, scheduler |
| **笔记 / 知识管理** | 笔记工具、Wiki、文档系统 | notes, knowledge, wiki, markdown, second-brain |
| **算法 / 学习** | 教程、面试题、学习资源 | algorithm, leetcode, interview, tutorial, course |
| **配置 / Dotfiles** | 个人配置、预设、RC 文件 | dotfiles, config, configuration, settings, preset |
| **其他 / 未分类** | 无明确匹配 | fallback |

### 生态归属（Ecology）

项目所属的**技术族谱或工具链生态**。例如 Clash / Mihomo 生态下的项目包括核心代理、GUI 前端、配置订阅、规则集等。

生态规则存储在 `data/ecologies.yaml`，当前定义了 74+ 生态。常见生态包括：

- **Clash / Mihomo**、**V2Ray**、**Sing-box** — 代理工具生态
- **MPV**、**Obsidian**、**Neovim**、**VS Code** — 编辑器/播放器生态
- **Docker**、**Kubernetes** — 容器生态
- **Flutter**、**Electron**、**React**、**Vue** — 开发框架生态
- **Magisk**、**KernelSU**、**LSPosed** — Android  root 生态
- **独立项目** — 不属于任何已知生态的项目

> 新增生态：直接编辑 `data/ecologies.yaml`，无需修改代码。

### 生态角色（Ecology Role）

项目在所属生态中的**功能定位**：

| 角色 | 说明 | 示例 |
|------|------|------|
| **核心 / Core** | 生态的核心引擎/主程序 | Clash.Meta 核心 |
| **GUI 前端 / Client** | 图形界面客户端 | Clash Verge Rev, Mihomo Party |
| **配置 / Config** | 预设配置、Dotfiles | 个人 Clash 配置仓库 |
| **脚本 / Script** | 自动化脚本 | 自动更新规则脚本 |
| **主题 / Theme** | 外观/颜色方案 | VS Code 主题 |
| **插件 / Plugin** | 扩展/插件 | VS Code 插件 |
| **规则集 / Rules** | 过滤规则、列表 | Clash 规则集 |
| **Web UI / Dashboard** | 网页管理面板 | Yacd, Meta Cube |
| **API 封装 / Wrapper** | SDK、绑定库 | Python Clash 封装 |
| **教程 / Guide** | 教程、Awesome 列表 | Clash 使用指南 |
| **其他 / Other** | 无明确角色 | fallback |

### 分类修正示例

编辑 `data/stars_db.json` 修正某个项目的分类：

```json
{
  "full_name": "owner/repo",
  "platform": "跨平台",
  "type": "工具 / Tool",
  "ecology": "Clash / Mihomo",
  "ecology_role": "GUI 前端 / Client",
  "manual_override": true,
  "override_fields": ["platform", "type", "ecology", "ecology_role"]
}
```

---

## 自定义生态规则

编辑 `data/ecologies.yaml` 添加新生态：

```yaml
your_tool_eco:
  display_name: 你的工具链生态
  name_patterns:
    - 工具名
  desc_patterns:
    - 描述关键词
  topic_patterns:
    - topic标签
  related_types:
    - config
    - gui
    - plugin
  core_projects:
    - 核心项目名
```

如需覆盖 `LOCKED_ECOLOGIES`（LLM 不能修改的生态），在 `scripts/config_rules.py` 中修改。

### 生态发现与 blocklist

每次运行会自动扫描独立项目，通过命名前缀和 topics 聚类发现潜在生态候选，生成 `docs/ecology_discovery.md` 报告。

如果某些 topic/前缀被误识别为生态候选（如平台词 `android`、类型词 `cli`），编辑 `scripts/ecology_blocklist.yaml` 添加排除项：

```yaml
topics:
  - android   # 平台，不应作为生态
  - cli       # 类型，不应作为生态

name_prefixes:
  - apk       # 文件格式前缀
```

修改后提交到 main 分支，下次 Actions 运行自动生效。

---

## LLM 配置

### 预设（推荐）

代码中已内置常用服务商的完整配置，只需一个 preset 名称：

| Preset | Provider | Base URL | Model |
|--------|----------|----------|-------|
| `openai` | openai | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `moonshot` | moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| `deepseek` | deepseek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| `openrouter` | openrouter | `https://openrouter.ai/api/v1` | `openrouter/auto` |
| `xiaomimimo` ⭐ | openai | `https://api.xiaomimimo.com/v1` | `mimo-v2-flash` |

使用方式：
- CLI：`--llm-preset xiaomimimo`
- 环境变量：`LLM_PRESET=xiaomimimo`
- Actions：`llm_preset` input 或 `LLM_PRESET` Repository Variable

**自定义预设**：编辑 `scripts/config_llm.py` 中的 `CUSTOM_PRESETS`，添加你自己的服务商：

```python
CUSTOM_PRESETS = {
    "mycompany": {
        "provider": "openai",
        "api_base": "https://llm.mycompany.com/v1",
        "model": "company-model-v1",
    },
    "azure": {
        "provider": "openai",
        "api_base": "https://my-resource.openai.azure.com/openai/deployments/my-deployment/chat/completions?api-version=2024-02-01",
        "model": "gpt-4o",
    },
}
```

自定义预设与同名的内置预设合并，**自定义优先覆盖**。添加后通过 `--llm-preset mycompany` 直接使用。

**优先级**：CLI 显式参数 (`--llm-provider`/`--llm-base`/`--llm-model`) > **自定义 preset** > **内置 preset** > `LLM_BASE`/`LLM_MODEL` Variable > `config_llm.py` > 内置默认值。

### 手动配置

如需覆盖 preset 或使用未内置的服务，编辑 `scripts/config_llm.py`：

```python
LLM_CONFIG = {
    "provider": "moonshot",  # openai / moonshot / deepseek / openrouter
    "api_key": None,  # 或通过 --llm-key 参数传入
    "model": "moonshot-v1-8k",
    "api_base": "https://api.moonshot.cn/v1",
}
```

### LLM 间隔控制（节省 Token）

默认情况下，即使配置了 `--llm-key`，系统也会控制 LLM 分析的频率，避免每次运行都消耗 Token：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--llm-interval-days` | `30` | 两次 LLM 全量分析的最小间隔天数 |
| `--force-llm` | 否 | 无视间隔，强制启用 LLM 分析 |

**工作原理**：系统有两层控制：

1. **全局开关**（`stars_db.meta.json`）：记录上次 LLM 运行时间。若不足间隔天数，完全不调用 LLM API。
2. **项目级追踪**（`stars_ai.json`）：每个项目独立记录 `analyzed_at`。即使全局启用 LLM，间隔内已成功分析的项目也会跳过，只分析 **新项目** 和 **间隔到期的老项目**。

这意味着：
- **规则分类** 遵循 `--incremental`：已有项目只更新 Stars/描述等元数据
- **LLM 分析** 走独立策略：**全局介入**，既处理新项目，也按间隔重新分析已有项目并修正其分类

```bash
# 每月一次 LLM 全局分析（默认 30 天）
python scripts/classifier.py --token <TOKEN> --user <USER> --llm-key <KEY>

# 每季度一次
python scripts/classifier.py --llm-key <KEY> --llm-interval-days 90

# 临时强制启用（手动修正分类时）
python scripts/classifier.py --llm-key <KEY> --force-llm
```

LLM 分类结果有 4 种状态：

| 状态 | 含义 |
|------|------|
| `not_analyzed` | 未进行 LLM 分析 |
| `success` | LLM 成功返回有效分类 |
| `failed` | LLM 调用失败或返回无效数据 |
| `skipped` | 因置信度低或生态锁定而跳过 |

---

## 通知配置

编辑 `scripts/config_notify.py` 中的对应配置：

```python
# 邮件
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "your@gmail.com",
    "smtp_password": "app_password",
    "from_addr": "your@gmail.com",
    "to_addrs": ["recipient@example.com"],
}

# Telegram
TELEGRAM_CONFIG = {
    "bot_token": "123456:ABC-DEF...",
    "chat_id": "-1001234567890",
}

# 企业微信
WECOM_CONFIG = {
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
}

# QQ（需要部署 go-cqhttp）
QQ_CONFIG = {
    "api_url": "http://127.0.0.1:5700",
    "group_id": "123456789",
    "access_token": "your_token",
}
```

---

## 数据库结构

`data/stars_db.json` 每个项目包含：

| 字段 | 说明 |
|------|------|
| `full_name` | 唯一标识 `owner/repo` |
| `platform` / `type` / `language` | 三维分类 |
| `ecology` / `ecology_role` | 生态归属 |
| `stars` / `topics` / `description` | 元数据 |
| `first_seen` / `last_updated` | 时间戳 |
| `manual_override` | 手动保护标记 |
| `override_fields` | 被保护的字段 |
| `imported` | 是否从外部导入 |
| `subscribe_releases` | 是否订阅 Release 通知 |
| `last_release_tag` | 最后记录的 Release 标签 |
| `is_fork` | 是否为 Fork 仓库 |
| `parent_full_name` | 上游仓库名称 |
| `parent_pushed_at` | 上游最后推送时间 |
| `github_list_source` | 来源 GitHub List 名称 |

### AI 数据库结构

`data/stars_ai.json` 是独立的 AI 分析结果存储，与主数据库完全解耦：

| 字段 | 说明 |
|------|------|
| `llm_status` | LLM 分析状态（`not_analyzed` / `success` / `failed` / `skipped`） |
| `llm_confidence` / `llm_reason` | LLM 置信度和理由 |
| `ai_summary` / `ai_tags` / `ai_platforms` | LLM 生成的摘要和标签 |
| `ai_platform` / `ai_type` / `ai_ecology` | AI 建议的分类（可与规则不同） |
| `analyzed_at` | 本次 AI 分析时间戳 |

**为什么分离？**
- 规则分类每次运行都更新，AI 分类按间隔控制，两者生命周期不同
- 分离后规则更新不会覆盖之前的 AI 分析结果
- 向后兼容：首次运行自动从旧版主数据库迁移 AI 字段到 `stars_ai.json`
- 主数据库不再保存 AI 字段（保存时自动过滤），确保双库独立持久化

---

## 开发

### 运行测试

项目包含 219 个测试：

```bash
# 运行全部测试
python -m unittest discover -s tests -v
```

### 已知限制与测试范围

**已覆盖（有测试）**：
- 规则分类器（平台 / 类型 / 生态关键词匹配）
- 增量更新引擎（新/旧/保护/强制刷新/LLM 增强状态机）
- 数据库 JSON 持久化（原子写入、损坏重建、加载/保存）
- GitHub API 封装（分页、错误处理、Markdown 清洗）
- HTTP 客户端（requests / urllib 双后端、POST JSON）
- 导入工具（CSV / JSON、首次运行检测）
- GitHub Lists 管理（检测、迁移、清理）
- StarItem 数据模型（roundtrip dict、字段过滤）
- 通知系统（邮件 / Telegram / 企业微信 / QQ，含 CQ 代码转义）
- Notion 导出（属性映射、清空归档、错误处理）
- Pipeline 编排（阶段顺序、dry-run、LLM 开关、通知组装）
- Release / Fork 跟踪器（检测逻辑、报告格式化）
- **集成测试**：真实 `StarsDB` + `StarItem` → HTML/CSV/JSON 报告生成、`ReleaseTracker` dict 赋值

**未覆盖 / 已知限制**：
- LLM 分类器的实际 API 调用（测试使用 mock 响应，未测试真实 OpenAI/Moonshot/DeepSeek 接口）
- 大规模仓库性能（> 1000 个 Stars 时的内存和 API 速率管理）
- Notion 大规模同步（> 1000 条记录时的逐条创建性能）
- 报告 HTML 模板在极端数据下的渲染（如全为空描述、特殊字符仓库名）
- Windows GBK 编码回退的实际终端测试（代码中有 fallback 逻辑，但未在 GBK 终端验证）
- GitHub Lists 的 TTY 交互式提示（仅在非 CI 环境可用，依赖 `sys.stdin.isatty()`）

### 架构概览

```
classifier.py (CLI 入口)
    │
    ▼
orchestrator/new_pipeline.py (18 阶段插件化 Pipeline)
    ├── setup / auth
    ├── GitHub Lists 处理
    ├── fetch (github_api.py)
    ├── enrich (http_client.py)
    ├── classify (rule_classifier.py + llm_classifier.py)
    │   └── engine.py (增量更新引擎)
    ├── save (database.py)
    ├── report (report.py)
    ├── sync_notion (notion.py)
    ├── track_releases (release_tracker.py)
    ├── track_forks (fork_tracker.py)
    └── notify (notify.py)
```

核心数据模型为 `StarItem`（`models.py`），支持 dict 兼容层以兼容旧数据格式。数据库层自动在 dict 和 `StarItem` 之间转换。

---

## 常见问题

**Q: 首次运行会覆盖我之前的分类吗？**
A: 如果数据库不存在，首次运行会 **全新分类所有项目**。如果你有已有分类，使用 `--import-json` 或 `--import-csv` 导入，导入的项目会被 **自动保护** 不被覆盖。

**Q: 私有仓库的 Stars 需要什么权限？**
A: Token 需要勾选 `repo` 权限。

**Q: LLM 分类会覆盖我的手动修正吗？**
A: 不会。`manual_override = true` 的项目 LLM 和规则分类都会跳过。此外，属于 `LOCKED_ECOLOGIES` 的项目，其生态字段不会被 LLM 修改。

**Q: 可以部署到自己的服务器吗？**
A: 可以。`docs/index.html` 是纯静态文件，任何静态托管都可以。

**Q: 增量模式会漏掉项目吗？**
A: 默认拉取最近 300 个。如果你一周 star 超过 300 个，修改工作流 `--pages` 参数。

**Q: Notion 导出会重复创建吗？**
A: 使用 `--notion-clear` 会先归档旧页面再创建新页面，但谨慎使用。

**Q: 试运行模式是什么？**
A: 加 `--dry-run` 可以预览分类结果但不保存数据库和报告，适合测试规则调整效果。

**Q: Release 跟踪如何使用？**
A: 在数据库中将项目的 `subscribe_releases` 设为 `true`，下次运行时会检查是否有新版本发布并纳入通知。

**Q: Fork 上游跟踪会做什么？**
A: 自动检测所有 `is_fork = true` 的项目，比较上游仓库的最后推送时间。如果有更新，会在通知中提醒。

**Q: Actions 运行时报 "Process completed with exit code 1" 怎么办？**
A: 常见原因：
1. **Workflow permissions 未开启** → 去 Settings → Actions → General 开启 Read and write permissions
2. **GH_TOKEN 无效** → 检查 Secret 是否已添加，Token 是否被撤销
3. **GitHub API 速率限制** → 免费账户每小时 5000 次请求，Star 项目过多时可能触发，等一小时再试

**Q: 为什么 Pages 报告页面没有 Source 选项？**
A: GitHub 更新了界面。路径是：Settings → Pages → Build and deployment → Source 下拉菜单选择 GitHub Actions。

**Q: 为什么我的 GitHub Lists 没有自动更新分类？**
A: 本工具 **不会修改你的 GitHub Lists**。原因：GitHub 目前没有公开稳定的 Lists 写入 REST API（无法通过 API 创建 List 或添加项目）。工具的核心价值是生成本地 HTML 报告。如果你想在 GitHub 上使用分类，可以手动参考报告中的分类结果创建 Lists。

**Q: 调整分类规则后，如何让已有项目重新分类？**
A: 运行一次 `--mode deep`：
```bash
python scripts/classifier.py --token ghp_xxx --user yourname --mode deep
```
这会重新分类所有 **未保护**（`manual_override=false`）的项目，同时检查 Release 和 Fork。已保护的项目不受影响。如需 LLM 全量分析，加 `--llm-key sk-xxx --force-llm`。

---

## License

MIT
