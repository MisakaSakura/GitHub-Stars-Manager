# GitHub Stars 自动分类工具 v4

自动为你的 GitHub Stars 按 **平台、类型、语言、生态归属** 四维分类，支持 LLM 智能增强、增量更新、手动修正保护、Notion 导出、多通道通知、Release 跟踪、Fork 上游跟踪。

🔗 **在线报告**: 部署后访问 `https://你的用户名.github.io/你的仓库名/`

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 🌿 **生态归属** | 自动识别项目族谱（Clash、MPV、VS Code、Neovim 等 15+ 生态） |
| 🤖 **LLM 智能增强** | 支持 OpenAI / Moonshot / DeepSeek / OpenRouter，自动补全规则分类盲区 |
| 📦 **增量更新** | 只处理新 star 的项目，已有分类保持不变 |
| 🔒 **手动修正保护** | `manual_override` 标记的项目永久不被覆盖 |
| 📝 **Notion 导出** | 一键同步到 Notion 数据库 |
| 📧 **多通道通知** | 邮件 / Telegram / 企业微信 / QQ（go-cqhttp） |
| 📋 **GitHub Lists 集成** | 自动检测、迁移或替换 GitHub 原生 Lists |
| 🔔 **Release 跟踪** | 监控订阅仓库的新版本发布 |
| 🍴 **Fork 上游跟踪** | 检测 Fork 项目是否有上游更新 |
| ⏰ **定时自动执行** | GitHub Actions 每周自动运行 |
| 📊 **可视化报告** | 暗色主题交互式 HTML，支持筛选和生态视图 |
| 🧪 **测试覆盖** | 91 个单元测试覆盖核心逻辑 |

---

## 快速开始

### 1. 创建仓库

新建 GitHub 仓库，复制以下文件结构：

```
.
├── .github/workflows/classify-stars.yml   ← 定时工作流
├── scripts/
│   ├── classifier.py          ← CLI 入口（参数解析）
│   ├── pipeline.py            ← 16 阶段执行编排
│   ├── engine.py              ← 增量更新引擎
│   ├── models.py              ← StarItem 数据模型
│   ├── database.py            ← JSON 持久化（原子写入）
│   ├── github_api.py          ← GitHub REST API 封装
│   ├── http_client.py         ← HTTP 客户端（requests / urllib 双后端）
│   ├── rule_classifier.py     ← 规则分类器
│   ├── llm_classifier.py      ← LLM 分类器
│   ├── report.py              ← HTML / CSV / JSON 报告生成
│   ├── notion.py              ← Notion 数据库导出
│   ├── notify.py              ← 多通道通知分发
│   ├── lists_manager.py       ← GitHub Lists 管理
│   ├── release_tracker.py     ← Release 发布跟踪
│   ├── fork_tracker.py        ← Fork 上游跟踪
│   ├── base_tracker.py        ← 跟踪器基类
│   ├── import_helper.py       ← JSON / CSV 导入工具
│   ├── config.py              ← 向后兼容配置总入口
│   ├── config_rules.py        ← 分类规则配置
│   ├── config_llm.py          ← LLM 配置
│   ├── config_notion.py       ← Notion 配置
│   ├── config_notify.py       ← 通知配置
│   ├── utils.py               ← 工具函数
│   └── requirements.txt       ← 依赖
├── data/
│   └── stars_db.json          ← 持久化数据库（首次运行后生成）
└── docs/
    └── index.html             ← 报告（首次运行后生成）
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

> 💡 **GH_TOKEN 获取**: [GitHub Settings → Tokens](https://github.com/settings/tokens) → Generate new token (classic) → 无需勾选任何 scope

### 3. 启用 GitHub Pages

仓库 → **Settings → Pages** → Source 选择 **GitHub Actions**

### 4. 首次运行

进入 **Actions → Auto Classify GitHub Stars → Run workflow**

---

## ⚠️ 首次运行行为说明（重要）

### 场景 A：全新开始（没有已有分类）

**行为**：首次运行会自动创建 `stars_db.json`，对**所有 star 项目执行全新分类**。

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
# 强制刷新所有项目（但 manual_override 项目仍被保护）
python scripts/classifier.py --token ghp_xxx --user yourname --force-refresh
```

---

## 日常使用模式

### 增量更新（推荐日常用）

每周一自动执行，只拉取最近 star 的 300 个项目：
- **新项目** → 自动分类
- **已有项目** → 只更新 stars 数，分类不变
- **手动保护项目** → 完全跳过

```bash
python scripts/classifier.py --token ghp_xxx --user yourname --incremental
```

### 强制全量刷新

调整分类规则后，想让所有项目重新分类：

```bash
python scripts/classifier.py --token ghp_xxx --user yourname --force-refresh
```

> ⚠️ 强制刷新会覆盖所有**未保护**的自动分类，但 `manual_override = true` 的项目仍然跳过。

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

commit 后，下次自动运行会**完全跳过**这个项目。

报告中的 🔒 标记表示手动保护，🤖 标记表示 LLM 增强。

---

## 自定义生态规则

编辑 `scripts/config_rules.py` 中的 `ECOLOGY_RULES`：

```python
"你的工具链生态": {
    "name_patterns": ["工具名"],
    "desc_patterns": ["描述关键词"],
    "topic_patterns": ["topic标签"],
    "related_types": ["config", "gui", "plugin"],
    "core_projects": ["核心项目名"],
},
```

如需覆盖 `LOCKED_ECOLOGIES`（LLM 不能修改的生态），也在 `config_rules.py` 中修改。

---

## LLM 配置

编辑 `scripts/config_llm.py` 中的 `LLM_CONFIG`：

```python
LLM_CONFIG = {
    "enabled": True,
    "provider": "moonshot",  # openai / moonshot / deepseek / openrouter
    "api_key": None,  # 或通过 --llm-key 参数传入
    "model": "moonshot-v1-8k",
    "api_base": "https://api.moonshot.cn/v1",
}
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
| `llm_status` | LLM 分析状态（`not_analyzed` / `success` / `failed` / `skipped`） |
| `llm_confidence` / `llm_reason` | LLM 置信度和理由 |
| `ai_summary` / `ai_tags` / `ai_platforms` | LLM 生成的摘要和标签 |
| `subscribe_releases` | 是否订阅 Release 通知 |
| `last_release_tag` | 最后记录的 Release 标签 |
| `is_fork` | 是否为 Fork 仓库 |
| `parent_full_name` | 上游仓库名称 |
| `parent_pushed_at` | 上游最后推送时间 |
| `github_list_source` | 来源 GitHub List 名称 |

---

## 开发

### 运行测试

项目包含 91 个单元测试，覆盖所有核心模块：

```bash
# 运行全部测试
python -m unittest discover -s tests -v
```

### 架构概览

```
classifier.py (CLI 入口)
    │
    ▼
pipeline.py (16 阶段 Pipeline)
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
A: 如果数据库不存在，首次运行会**全新分类所有项目**。如果你有已有分类，使用 `--import-json` 或 `--import-csv` 导入，导入的项目会被**自动保护**不被覆盖。

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

---

## License

MIT
