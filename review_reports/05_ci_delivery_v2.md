# 批次5审查报告：CI/CD与交付链路

## 审查范围

| # | 文件 | 说明 |
|---|------|------|
| 1 | `.github/workflows/classify-stars.yml` | 主分类工作流（定时+手动触发） |
| 2 | `.github/workflows/process-feedback.yml` | 反馈处理工作流（Issue触发） |
| 3 | `scripts/ci/regenerate_learned_rules.py` | 从feedback生成学习规则（新增未跟踪） |
| 4 | `scripts/ci/apply_feedback_correction.py` | 从Issue解析并应用分类修正 |
| 5 | `scripts/classifier.py` | CLI入口，被workflow调用 |
| 6 | `scripts/config.py` | 配置聚合入口 |
| 7 | `scripts/config_rules.py` | 分类规则配置 |
| 8 | `scripts/config_notion.py` | Notion导出配置 |
| 9 | `scripts/config_notify.py` | 通知通道配置 |
| 10 | `scripts/config_llm.py` | LLM配置 |
| 11 | `scripts/feedback_loop.py` | 反馈闭环逻辑 |
| 12 | `scripts/ecologies/__init__.py` | 生态规则自动注册包 |
| 13 | `requirements.txt` | 依赖声明 |

---

## P0 — 阻塞级（3项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P0-1 | `classify-stars.yml` | 134-137 | `pip install requests || true` 使用 `|| true` 掩盖安装失败，且运行时动态生成 `requirements.txt` 导致缓存key在首次运行时失效（`hashFiles('requirements.txt')` 在缓存步骤执行时文件尚不存在） | 若pip安装失败仍继续执行，运行时因缺少依赖崩溃；缓存永远miss | 1. 移除 `|| true`；2. 将 `requirements.txt` 提前提交到仓库；3. 或改用 `pip install -r requirements.txt` 并在install步骤前生成文件 |
| P0-2 | `classify-stars.yml` | 139-221 | `Run classifier` 步骤无超时设置，且LLM分类可能因网络/API问题无限挂起 | 工作流可能运行数小时消耗大量Action分钟，API Key被持续消耗 | 添加 `timeout-minutes: 30`（或根据模式调整：incremental=30, deep/full=60） |
| P0-3 | `process-feedback.yml` | 45-52 | `Parse issue and apply correction` 和 `Regenerate learned rules` 步骤缺少依赖安装，直接调用 `python3 scripts/ci/apply_feedback_correction.py` 和 `python3 scripts/ci/regenerate_learned_rules.py` | 若运行环境缺少 `requests` 或其他依赖（如 feedback_loop.py 依赖的模块），脚本会因 ImportError 失败 | 添加 `Install dependencies` 步骤，与 classify-stars.yml 保持一致 |

---

## P1 — 重要（12项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P1-1 | `classify-stars.yml` | 76-79 | `permissions` 声明在workflow级别而非job级别，且 `id-token: write` 仅 Pages 部署需要，但授予了所有步骤 | 违反最小权限原则；若其他步骤被注入恶意代码，可利用 id-token | 将 `permissions` 下移到 job 级别，并拆分为两个 job：classify（只需 contents:write）和 deploy（需要 pages + id-token） |
| P1-2 | `classify-stars.yml` | 106 | `REPO_URL` 使用 `https://x-access-token:${GITHUB_TOKEN}@github.com/...` 在 shell 中拼接，Token 会出现在 `ps` 输出和错误日志中 | GITHUB_TOKEN 可能在日志中泄露（尽管 GitHub 有脱敏，但子进程/崩溃转储可能暴露） | 使用 `actions/checkout` 的 `token` 参数，或设置 `GIT_ASKPASS` + 凭证辅助脚本，避免在命令行中嵌入Token |
| P1-3 | `classify-stars.yml` | 128-132 | `actions/cache@v4` 缓存 pip 依赖，但 `hashFiles('requirements.txt')` 在运行时动态生成文件，首次运行缓存key不可预测 | 缓存行为不一致，可能导致依赖版本漂移或缓存污染 | 将 `requirements.txt` 作为静态文件提交到仓库，确保缓存key稳定 |
| P1-4 | `classify-stars.yml` | 160-163 | `MODE` 变量从 `${{ github.event.inputs.mode }}` 读取，但 `schedule` 触发时 `github.event.inputs` 为空，回退逻辑正确但 `${{ github.event.inputs.mode }}` 在shell中展开为空字符串 | 低危：逻辑正确但依赖shell的空值处理，若 GitHub 表达式行为变更可能引入bug | 显式处理：`MODE="${{ github.event.inputs.mode || 'incremental' }}"` 在 workflow 表达式层面设置默认值 |
| P1-5 | `classify-stars.yml` | 237-242 | git rebase/merge 冲突处理使用 `|| true` 和 `git push origin data || git push -u origin data`，冲突时可能静默失败或推送不完整历史 | 数据分支历史可能混乱，反馈修正可能丢失 | 1. 冲突时标记workflow失败而非静默继续；2. 使用 `git push --force-with-lease` 防止覆盖；3. 或改用 `actions/checkout` 的 ref 机制处理并发 |
| P1-6 | `process-feedback.yml` | 67-72 | 与 classify-stars.yml 相同的 rebase/merge 冲突处理问题，且两个workflow可能并发操作 data 分支 | 竞态条件导致数据丢失或冲突静默忽略 | 统一使用一个通用的 Git 数据提交 Action，或添加 `concurrency` 跨workflow协调（当前 concurrency 只在单workflow内生效） |
| P1-7 | `classify-stars.yml` | 277-279 | `Deploy to GitHub Pages` 在分类失败时仍会执行（无 `if: success()` 限制，但默认行为是成功才执行后续步骤——实际上若 `Run classifier` 失败，后续步骤不会执行。但 `Deploy` 步骤本身无独立条件判断） | 若 docs/ 生成失败但步骤exit 0（如异常被捕获），会部署空/损坏页面 | 添加 `if: success() && steps.deployment.outcome != 'failure'` 或验证 docs/index.html 存在后再部署 |
| P1-8 | `classify-stars.yml` | 247-258 | `Commit requirements.txt` 步骤在 main 分支上直接 push，无 PR 流程，且可能与其他提交冲突 | 直接推送到 main 分支违反保护分支最佳实践；冲突时 `git push` 会失败 | 1. 将 requirements.txt 作为静态文件维护，不自动提交；2. 或创建 PR 而非直接推送 |
| P1-9 | `apply_feedback_correction.py` | 20-22 | `parse_field` 使用正则 `re.search(rf"{re.escape(label)}\s*\n\s*([^\n]+)", body)` 只匹配单行值，若修正字段值包含换行（如多行描述）会截断 | 多行修正值被错误截断，导致数据损坏 | 修改正则支持多行匹配，或改用更健壮的解析方式（如 YAML frontmatter） |
| P1-10 | `apply_feedback_correction.py` | 64-82 | 修正逻辑中 `field_type` 为 `"多个字段"` 时所有字段使用同一个 `expected` 值，但不同字段（platform/type/ecology）的值域完全不同 | 用户意图修正多个字段时，所有字段被设为同一个不可能的值（如 ecology="Web" 或 platform="Clash"） | 修改 Issue 模板支持每字段独立输入，或在 `"多个字段"` 时拒绝处理并提示用户分条提交 |
| P1-11 | `regenerate_learned_rules.py` | 22 | `generate_learned_overrides(min_count=2)` 的 min_count 硬编码为 2，与 `feedback_loop.py` 默认的 3 不一致 | 规则生成阈值不一致，可能导致学习规则过于敏感（低置信度规则被采纳） | 统一使用常量或从配置读取，建议与 `feedback_loop.py` 默认的 `min_count=3` 保持一致 |
| P1-12 | `classify-stars.yml` | 18-20 | `schedule` 触发器使用 `cron: '0 2 * * 1'`（周一 2:00 UTC），无随机偏移 | 大量用户的 Actions 在同一时刻触发，可能导致 GitHub API 限流 | 添加随机偏移，如 `cron: '17 2 * * 1'`（偏移17分钟） |

---

## P2 — 建议（14项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P2-1 | `classify-stars.yml` | 86-87 | `env` 中 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` 是 GitHub 的临时迁移标志，可能在未来被移除 | 过时配置导致警告或未来兼容性问题 | 确认是否仍需此标志，若 Actions 已运行在 Node24 可移除 |
| P2-2 | `classify-stars.yml` | 81-83 | `concurrency.group: "pages"` 命名过于通用，若仓库有其他 Pages 部署workflow会冲突 | 不必要的排队延迟 | 使用更具体的 group 名，如 `"classify-stars-pages"` |
| P2-3 | `classify-stars.yml` | 260-267 | `Debug docs contents` 步骤仅用于调试，不应常驻生产 workflow | 增加不必要的运行时间和日志噪音 | 移除或改为 `if: failure()` 仅在失败时执行 |
| P2-4 | `classify-stars.yml` | 136 | `echo "requests>=2.31.0" > requirements.txt` 硬编码依赖版本，未使用仓库中的 requirements.txt | 依赖版本管理分散，难以统一升级 | 统一使用仓库根目录的 `requirements.txt`，CI中只执行 `pip install -r requirements.txt` |
| P2-5 | `classify-stars.yml` | 141-156 | 大量 secrets 通过 `env` 注入，即使未使用的通知 secrets 也会被设置到环境变量中 | 环境变量污染，增加意外泄露风险 | 按条件动态设置 env，或使用 `env` 的 `if` 语法（GitHub Actions 不支持，但可通过 shell 条件避免传递未使用的 secrets） |
| P2-6 | `process-feedback.yml` | 1-80 | workflow 无 `env` 节设置 `PYTHONUNBUFFERED`，Python 输出可能缓冲 | 日志输出不及时，调试困难 | 添加 `env: PYTHONUNBUFFERED: 1` |
| P2-7 | `process-feedback.yml` | 75-79 | `Close issue with comment` 使用 `gh issue close`，但 workflow 的 `permissions` 已包含 `issues: write` | 低危：权限正确，但 `gh` CLI 需要 `GITHUB_TOKEN` 环境变量显式传递（已传递） | 无修复必要，但可考虑在关闭前验证修正是否成功应用 |
| P2-8 | `classifier.py` | 51 | `--token` 参数 `required=True`，但 workflow 中通过 `GH_TOKEN` 环境变量传递后由脚本读取——实际上脚本并未从环境变量读取 `GH_TOKEN` | 脚本只能接收 CLI 参数，环境变量方式不工作（但 workflow 通过 CLI 参数传递了，所以当前可用） | 在 `classifier.py` 中为 `--token` 添加 `default=os.environ.get("GH_TOKEN", "")`，支持环境变量回退 |
| P2-9 | `config_llm.py` | 69 | `max_tokens: 256` 对于 batch 输出可能不足（5个项目各需约50 tokens JSON） | LLM 输出被截断，导致 JSON 解析失败 | 根据 batch_size 动态计算：`max_tokens = 100 + batch_size * 80` |
| P2-10 | `config_llm.py` | 71 | `temperature: 0.1` 非零，LLM 输出仍有随机性 | 相同项目多次运行可能产生不同分类，影响一致性 | 设为 `0` 以获得确定性输出（若API支持） |
| P2-11 | `config_rules.py` | 7 | `RULES_VERSION` 使用日期字符串 `"2026-05-17-platform-refactor"`，每次规则变更需手动更新 | 开发者可能忘记更新版本号，导致 feedback 版本校验失效 | 使用自动化版本生成（如 git commit hash + 日期），或在 CI 中校验版本号是否已更新 |
| P2-12 | `ecologies/__init__.py` | 25-28 | `os.listdir(_current_dir)` 遍历目录时无异常处理，若目录权限问题会崩溃 | 极端情况下的健壮性问题 | 添加 `try/except` 包裹目录遍历逻辑 |
| P2-13 | `classify-stars.yml` | 93-99 | `actions/checkout@v4` 使用 `fetch-depth: 0` 拉取完整历史，但主工作流只需最新代码 | 增加不必要的 checkout 时间和存储 | 改为 `fetch-depth: 1`（除非有特定原因需要完整历史） |
| P2-14 | `classify-stars.yml` | 173-176 | `schedule` 触发时自动添加 `--check-all-releases`，但无环境变量或输入控制此行为 | 无法在不修改 workflow 文件的情况下禁用 schedule 的 release 检查 | 添加 `vars.CHECK_RELEASES_ON_SCHEDULE` 变量控制，默认启用但允许用户关闭 |

---

## 按模块汇总

| 模块 | P0 | P1 | P2 | 关键问题 |
|------|----|----|----|----------|
| `classify-stars.yml` | 2 | 7 | 9 | 超时缺失、权限过大、缓存失效、Token暴露、main分支直接推送 |
| `process-feedback.yml` | 1 | 2 | 2 | 缺少依赖安装、跨workflow竞态条件 |
| `scripts/ci/` | 0 | 3 | 0 | 多字段修正逻辑错误、min_count不一致、单行解析缺陷 |
| `scripts/classifier.py` | 0 | 0 | 1 | GH_TOKEN环境变量未作为fallback |
| `scripts/config*.py` | 0 | 0 | 3 | temperature非零、max_tokens不足、RULES_VERSION手动维护 |
| `scripts/ecologies/` | 0 | 0 | 1 | 目录遍历无异常处理 |
| **合计** | **3** | **12** | **14** | |

---

## 关键问题详解

### 1. 超时缺失（P0-2）

`classify-stars.yml` 的 `Run classifier` 步骤没有 `timeout-minutes`，这是最严重的问题之一。当 LLM API 响应缓慢或网络中断时，工作流可能运行数小时：

```yaml
# 修复建议
- name: Run classifier
  timeout-minutes: 30  # 或 60 for deep/full mode
  env:
    ...
```

### 2. 依赖安装掩盖失败（P0-1）

```yaml
# 当前（危险）
- name: Install dependencies
  run: |
    pip install requests || true
    echo "requests>=2.31.0" > requirements.txt

# 修复建议
- name: Install dependencies
  run: |
    pip install -r requirements.txt
```

同时 `requirements.txt` 应作为静态文件提交到仓库，而非运行时生成。

### 3. process-feedback 缺少依赖安装（P0-3）

`process-feedback.yml` 直接调用 Python 脚本但没有安装依赖：

```yaml
# 修复建议：在 Setup Python 后添加
- name: Install dependencies
  run: |
    pip install -r requirements.txt
```

### 4. 跨 Workflow 竞态条件（P1-6）

两个 workflow 都可能同时修改 `data` 分支。当前每个 workflow 有自己的 `concurrency` group，但 **跨 workflow 没有协调**。建议：

```yaml
# 两个 workflow 使用相同的 concurrency group
concurrency:
  group: "data-branch-write"
  cancel-in-progress: false
```

### 5. 多字段修正逻辑错误（P1-10）

`apply_feedback_correction.py` 中 `"多个字段"` 的处理：

```python
# 当前逻辑（错误）：所有字段设为同一个 expected 值
if "生态归属" in field_type or "多个字段" in field_type:
    target["ecology"] = expected  # expected 可能是 "Web"
if "平台" in field_type or "多个字段" in field_type:
    target["platform"] = expected  # 同样是 "Web"！
```

这会导致 platform 被设为 ecology 的值，或反之。需要修改 Issue 模板支持多字段独立输入。

### 6. 权限最小化（P1-1）

当前 workflow 级别的权限：

```yaml
permissions:
  contents: write   # classify 和 commit 需要
  pages: write      # 仅 deploy 需要
  id-token: write   # 仅 deploy 需要
```

建议拆分为两个 job：

```yaml
jobs:
  classify:
    permissions:
      contents: write
    # ... 运行分类和提交 data 分支

  deploy:
    needs: classify
    permissions:
      pages: write
      id-token: write
    # ... 部署 Pages
```
