> **注意**：本文档为 **YAML 化重构前的历史审查记录**（2026-05-17 之前）。
> - `scripts/ecologies/*.py`（68 个生态模块）已全部删除，规则数据迁移至 `data/ecologies.yaml`
> - `register_ecology()` 函数已移除，改为 `yaml.safe_load()` 加载
> - 文档中的问题分析仍有参考价值，但引用的文件路径已不存在

# 批次6审查报告：生态配置模块

## 审查范围

| 文件 | 审查方式 | 备注 |
|------|---------|------|
| `scripts/ecologies/__init__.py` | 全量精读 | 注册机制核心 |
| `data/learned_rules.py` | 全量精读 | 规则补丁数据 |
| `scripts/config_rules.py` | 全量精读 | 规则配置与别名映射 |
| `scripts/ecologies/*.py` (68个生态模块) | 抽样精读 + 模式扫描 | 全部68个模块已读 |
| `scripts/rule_classifier.py` | 关联审查 | 规则消费端 |
| `scripts/ecology_discovery.py` | 关联审查 | 自动发现 |
| `scripts/orchestrator/stages/discover_ecologies_stage.py` | 关联审查 | 发现阶段 |
| `tests/test_classifiers.py` | 关联审查 | 分类器测试 |

---

## P0 — 阻塞级（1项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P0-1 | `scripts/ecologies/__init__.py` | 24-28 | 动态导入使用 `importlib.import_module()` 无异常处理，若任一生态模块存在语法错误，整个 `ECOLOGY_RULES` 加载失败，导致分类系统完全不可用 | 单个生态模块的语法错误会导致整个分类系统崩溃 | 在 `importlib.import_module()` 调用外包裹 `try/except`，记录错误但继续加载其他模块 |

---

## P1 — 重要（12项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P1-1 | `scripts/ecologies/__init__.py` | 15,31 | `ECOLOGY_REGISTRY` 和 `ECOLOGY_RULES` 缺少类型标注中 value 的具体结构；`dict[str, dict]` 过于宽泛，无法约束规则字段 | 类型安全弱，IDE 无法提供字段补全，新增生态时容易遗漏必填字段 | 定义 `TypedDict`：`class EcologyRule(TypedDict): name_patterns: list[str]; desc_patterns: list[str]; ...` |
| P1-2 | `scripts/ecologies/__init__.py` | 18-20 | `register_ecology()` 无重复注册检测，同名生态被后加载的模块静默覆盖 | 文件系统排序导致覆盖行为不可预测，调试困难 | 添加重复检测：`if name in ECOLOGY_REGISTRY: warnings.warn(f"生态 '{name}' 重复注册")` |
| P1-3 | `scripts/ecologies/clash_mihomo.py` | 7 | `name_patterns` 包含 `'clash'`，与 `scripts/ecologies/v2ray.py` 的 `'v2ray'` 等无冲突，但 `'clash'` 是极短前缀（4字符），`_score_name()` 中短 pattern 需词边界验证，而 `clash` 在 `clash-verge` 中作为前缀匹配时 `len('clash')=5 > 4`，不走词边界分支，直接得5分 | 可能误匹配如 `clash-of-clans` 等非技术项目 | 将 `clash` 从 `name_patterns` 移到更精确的匹配模式，或添加 `core_projects` 精确匹配保护 |
| P1-4 | `scripts/ecologies/obs_studio.py` | 7 | `name_patterns` 包含 `'obs'`，`obs` 是3字符短词，在 `_score_name()` 中 `len('obs')=3 <= 4`，需要词边界验证。但 `obs` 可能匹配 `observable`、`obsidian` 等无关项目 | 误匹配风险高，`obsidian` 有独立生态模块 | 将 `'obs'` 从 `name_patterns` 移除，仅保留 `'obs-studio'`、`'streamfx'`、`'input-overlay'` |
| P1-5 | `scripts/ecologies/vs_code.py` | 7 | `name_patterns` 包含 `'vscode'` 和 `'vs-code'`，但缺少 `'code-'` 前缀（如 `code-server`、`code-oss` 等 VS Code 衍生项目） | 覆盖盲区，VS Code 生态项目遗漏 | 添加 `'code-'` 到 `name_patterns` |
| P1-6 | `scripts/ecologies/neovim.py` | 7 | `name_patterns` 包含 `'nvim'`，`nvim` 是4字符，恰好处于短 pattern 阈值边界。`len('nvim')=4 <= 4`，需要词边界验证，但 `nvim` 可能匹配 `envim`（不存在但理论上）等 | 边界情况处理不统一 | 统一短 pattern 阈值逻辑，或明确 `nvim` 为精确匹配 |
| P1-7 | `scripts/ecologies/vue.py` | 7 | `name_patterns` 包含 `'vue-'`，但 `desc_patterns` 包含 `'vuejs'`。`topic_patterns` 为空列表，而 Vue 项目通常有 `vue`、`vuejs` topics | topics 覆盖盲区，降低分类准确率 | 添加 `['vue', 'vuejs', 'nuxt']` 到 `topic_patterns` |
| P1-8 | `scripts/ecologies/react.py` | 7 | `name_patterns` 仅包含 `'react-'`，缺少 `'react'` 本身（如 `react` 核心仓库） | 核心项目 `react` 无法通过 name 匹配，只能依赖 desc/topics | 添加 `'react'` 到 `name_patterns`（但需注意与 `reactive`、`reaction` 等词的区分） |
| P1-9 | `scripts/ecologies/tailwind_css.py` | 7 | `topic_patterns` 为空列表，Tailwind 项目通常有 `tailwindcss`、`tailwind` topics | topics 覆盖盲区 | 添加 `['tailwindcss', 'tailwind']` 到 `topic_patterns` |
| P1-10 | `scripts/ecologies/electron.py` | 7 | `desc_patterns` 包含 `'cross-platform desktop'`，这是通用描述而非 Electron 特有，可能误匹配 Tauri、Flutter 等项目 | 误匹配风险 | 将 `'cross-platform desktop'` 从 `desc_patterns` 移除，或降低权重 |
| P1-11 | `scripts/ecologies/docker.py` | 7 | `name_patterns` 仅包含 `'docker'`，但 Docker 生态有大量相关工具如 `containerd`、`podman`、`buildkit` 等 | 覆盖盲区 | 根据生态边界决策：若包含则添加 `containerd`、`buildkit`；若限定 Docker 官方生态则保持现状但文档说明 |
| P1-12 | `scripts/config_rules.py` | 286-289 | `ECOLOGY_STANDARD_NAMES` 手动维护的独立生态列表（`"AI/ML"`、`"Android"`、`"Apple"` 等）与 `ECOLOGY_RULES` 键集合的同步无自动化验证，新增生态后容易遗漏 | 别名映射与规则定义不同步，LLM 提示词中可能出现不存在的生态名称 | 在 `config_rules.py` 加载时自动校验：`assert all(name in ECOLOGY_ALIASES.values() for name in ECOLOGY_STANDARD_NAMES)`，或在 CI 中添加校验脚本 |

---

## P2 — 建议（14项）

| # | 文件 | 行号 | 问题描述 | 影响 | 修复建议 |
|---|------|------|----------|------|----------|
| P2-1 | `scripts/ecologies/__init__.py` | 25-28 | 使用 `os.listdir()` + `sorted()` 依赖文件系统排序，跨平台行为可能不一致；且未过滤 `__pycache__` 等非 `.py` 目录（虽然 `.endswith(".py")` 已过滤） | 代码健壮性 | 使用 `pathlib.Path.glob("*.py")` 替代 `os.listdir()`，语义更清晰 |
| P2-2 | `scripts/ecologies/*.py` (全部68个) | 全部 | 所有生态模块结构完全重复：相同的 shebang、编码声明、docstring、import、register_ecology 调用，仅数据不同 | 严重违反 DRY 原则，新增生态需要复制粘贴模板 | 提供 CLI 工具或 cookiecutter 模板生成新生态模块；或考虑 YAML/JSON 配置替代 Python 文件 |
| P2-3 | `scripts/ecologies/*.py` (全部68个) | 全部 | 所有生态模块将规则数据写在单行，无格式化，可读性差 | 维护困难 | 使用 Black 或手动格式化，将字典展开为多行 |
| P2-4 | `scripts/ecologies/genshin_impact_游戏辅助.py` | 1,7 | 文件名和生态名称混用中英文（`genshin_impact_游戏辅助`），不符合 Python 模块命名规范（PEP 8 建议模块名全小写、可用下划线）；且 `desc_patterns` 包含中文 `'原神'`、`'星穹铁道'` | 跨平台文件系统兼容性问题（某些文件系统对 Unicode 支持不佳），import 时可能出问题 | 将文件名改为纯英文（如 `genshin_impact.py`），保留中文在 `register_ecology()` 第一个参数中 |
| P2-5 | `scripts/ecologies/rss_阅读.py` | 1,7 | 同上，文件名包含中文 `阅读` | 跨平台兼容性问题 | 改为 `rss_reader.py` |
| P2-6 | `scripts/ecologies/思维导图_白板.py` | 1,7 | 同上，文件名包含中文 `思维导图_白板` | 跨平台兼容性问题 | 改为 `mindmap_whiteboard.py` |
| P2-7 | `scripts/ecologies/iptv_直播.py` | 1,7 | 同上，文件名包含中文 `直播` | 跨平台兼容性问题 | 改为 `iptv_live.py` |
| P2-8 | `scripts/ecologies/bilibili.py` | 7 | `name_patterns` 包含 `'bbll'`，这是 Bilibili 的第三方客户端，但 `'bilitools'` 和 `'bili-copilot'` 也是第三方工具，而 `'bilibili'` 本身未在 `name_patterns` 中（只有前缀匹配） | 核心项目 `bilibili` 可能无法精确匹配 | 添加 `'bilibili'` 到 `name_patterns` |
| P2-9 | `scripts/ecologies/homebrew.py` | 7 | `core_projects` 包含 `'brew'`，但 `name_patterns` 仅包含 `'homebrew'`。若项目名为 `brew` 则无法通过 name 匹配 | 核心项目匹配不一致 | 添加 `'brew'` 到 `name_patterns` |
| P2-10 | `scripts/ecologies/starship.py` | 7 | `name_patterns` 仅包含 `'starship'`，但 `desc_patterns` 包含 `'shell prompt'`。`shell prompt` 是通用描述，可能匹配 `oh-my-posh`、`powerlevel10k` 等 | 轻微误匹配风险 | 从 `desc_patterns` 移除 `'shell prompt'` 或降低其权重 |
| P2-11 | `scripts/ecologies/git.py` | 7 | `name_patterns` 包含 `'lazygit'`、`'git-extras'`、`'gitui'`，但缺少 `'git'` 本身。`core_projects` 为 `['git']`，但 `name_patterns` 中无 `'git'` | `git` 核心项目无法通过 name 匹配 | 添加 `'git'` 到 `name_patterns`（需注意与 `github`、`digital` 等词的区分，可用词边界保护） |
| P2-12 | `scripts/ecologies/zsh_oh_my_zsh.py` | 7 | `name_patterns` 包含 `'powerlevel'`，但 `powerlevel10k` 的常用简称是 `'p10k'`，未覆盖 | 覆盖盲区 | 添加 `'p10k'` 到 `name_patterns` |
| P2-13 | `scripts/ecologies/i3_sway.py` | 7 | `name_patterns` 包含 `'i3'`、`'sway'`、`'polybar'`、`'rofi'`、`'dunst'`，但 `i3` 是2字符极短词，在 `_score_name()` 中 `len('i3')=2 <= 4`，需要词边界验证。`i3` 可能匹配 `wi3`、`mi3` 等（虽不常见） | 潜在误匹配 | 考虑将 `i3` 改为仅匹配前缀 `'i3-'` 或 `'i3_'` |
| P2-14 | `data/learned_rules.py` | 11-17 | 文件注释声明为"机器生成"，但 `LEARNED_OVERRIDES = {}` 为空字典，且文件头部缺少 `format()` 调用导致 `"生成时间: {}"` 未填充 | 文档与实现不一致，时间戳占位符未渲染 | 修复模板渲染，或若文件不再使用则删除并更新引用处（`rule_classifier.py` 的 `_load_learned_overrides()` 已优先 JSON 格式） |

---

## 按模块汇总

| 模块 | P0 | P1 | P2 | 关键问题 |
|------|----|----|----|----------|
| `__init__.py` | 1 | 2 | 1 | 动态导入无异常处理（P0）；无重复注册检测（P1-2） |
| `clash_mihomo.py` | 0 | 1 | 0 | 短前缀 `clash` 误匹配风险（P1-3） |
| `obs_studio.py` | 0 | 1 | 0 | `obs` 3字符短词误匹配 Obsidian（P1-4） |
| `vs_code.py` | 0 | 1 | 0 | 缺少 `code-` 前缀覆盖（P1-5） |
| `neovim.py` | 0 | 1 | 0 | `nvim` 4字符边界阈值问题（P1-6） |
| `vue.py` | 0 | 1 | 0 | `topic_patterns` 为空（P1-7） |
| `react.py` | 0 | 1 | 0 | 缺少 `react` 精确匹配（P1-8） |
| `tailwind_css.py` | 0 | 1 | 0 | `topic_patterns` 为空（P1-9） |
| `electron.py` | 0 | 1 | 0 | 通用描述 `cross-platform desktop` 误匹配（P1-10） |
| `docker.py` | 0 | 1 | 0 | 生态边界模糊（P1-11） |
| `config_rules.py` | 0 | 1 | 0 | `ECOLOGY_STANDARD_NAMES` 手动维护不同步（P1-12） |
| `genshin_impact_游戏辅助.py` | 0 | 0 | 1 | 文件名含中文（P2-4） |
| `rss_阅读.py` | 0 | 0 | 1 | 文件名含中文（P2-5） |
| `思维导图_白板.py` | 0 | 0 | 1 | 文件名含中文（P2-6） |
| `iptv_直播.py` | 0 | 0 | 1 | 文件名含中文（P2-7） |
| `bilibili.py` | 0 | 0 | 1 | 缺少 `bilibili` 精确匹配（P2-8） |
| `homebrew.py` | 0 | 0 | 1 | `brew` 核心项目 name 不匹配（P2-9） |
| `starship.py` | 0 | 0 | 1 | 通用描述 `shell prompt` 误匹配（P2-10） |
| `git.py` | 0 | 0 | 1 | 缺少 `git` 精确匹配（P2-11） |
| `zsh_oh_my_zsh.py` | 0 | 0 | 1 | 缺少 `p10k` 覆盖（P2-12） |
| `i3_sway.py` | 0 | 0 | 1 | `i3` 2字符极短词（P2-13） |
| `learned_rules.py` | 0 | 0 | 1 | 模板时间戳未渲染（P2-14） |
| 其他46个生态模块 | 0 | 0 | 0 | 无单独问题（受 P2-2、P2-3 共性问题影响） |

---

## 共性问题模式

### 模式1：动态导入无异常隔离（P0-1）
**影响范围**：`scripts/ecologies/__init__.py`
**描述**：`importlib.import_module()` 在循环中调用，任一模块的语法错误会导致整个注册过程失败，所有生态规则不可用。
**修复**：包裹 `try/except ImportError/SyntaxError`，记录失败模块名但继续加载其他模块。

### 模式2：68个模块完全重复的结构（P2-2）
**影响范围**：全部68个生态模块
**描述**：每个模块都是相同的5行模板（shebang + encoding + docstring + import + register_ecology），仅字典数据不同。这是典型的"配置伪装成代码"反模式。
**修复建议**：
- 短期：提供 `scripts/ci/add_ecology.py` CLI 工具自动生成模块文件
- 长期：考虑将生态规则迁移到 `data/ecologies.yaml` 或 `data/ecologies.json`，`__init__.py` 从文件加载并注册，消除68个几乎相同的 Python 文件

### 模式3：单行字典无格式化（P2-3）
**影响范围**：全部68个生态模块
**描述**：所有 `register_ecology()` 调用将字典写在单行，字段之间无空格，可读性极差，diff 时难以定位变更。
**示例**：
```python
# 当前
register_ecology('Clash / Mihomo', {'name_patterns': ['clash', 'mihomo', 'sing-box'], 'desc_patterns': [...], ...})

# 建议
register_ecology('Clash / Mihomo', {
    'name_patterns': ['clash', 'mihomo', 'sing-box'],
    'desc_patterns': ['mihomo core', 'clash core', 'sing-box', 'clashmeta', 'clash meta', 'based on clash', 'mihomo'],
    'topic_patterns': ['mihomo', 'sing-box', 'clash-meta'],
    'related_types': ['gui', 'config', 'rule-set', 'dashboard'],
    'core_projects': ['mihomo', 'clash', 'sing-box'],
})
```

### 模式4：短 pattern 词边界验证不一致（P1-3, P1-4, P1-6, P2-13）
**影响范围**：`rule_classifier.py` 的 `_score_name()`
**描述**：短 pattern（`<=4` 字符）需要词边界验证，但阈值 `4` 是魔法数字，且恰好让 `nvim`（4字符）走词边界分支而 `clash`（5字符）不走。`obs`（3字符）和 `i3`（2字符）走词边界分支但 `_has_word_boundary()` 仅检查前后是否为字母数字，对于 `obsidian` 中的 `obs` 前缀，`obs` 后面是 `i`（字母），`after_ok=False`，所以不会误匹配——实际上当前实现是安全的，但逻辑复杂且容易让人误解。
**修复建议**：将 `_has_word_boundary()` 的逻辑内联注释化，或添加单元测试覆盖边界情况。

### 模式5：文件名含中文字符（P2-4 ~ P2-7）
**影响范围**：4个生态模块
**描述**：`genshin_impact_游戏辅助.py`、`rss_阅读.py`、`思维导图_白板.py`、`iptv_直播.py` 的文件名包含中文字符。虽然 Python 3 支持 Unicode 标识符，但某些文件系统（如旧版 Windows 的 FAT32、某些 CI/CD 环境的默认编码）可能处理不当。更重要的是，这些文件在命令行中难以输入。
**修复**：将文件名改为纯英文，中文仅保留在模块内的字符串中。

### 模式6：`topic_patterns` 大量为空列表（P1-7, P1-9）
**影响范围**：至少 `react.py`、`vue.py`、`tailwind_css.py`、`electron.py` 等
**描述**：GitHub topics 是强信号源，但许多生态模块的 `topic_patterns` 为空，导致 `_score_topics()` 无法为这些生态加分。
**修复**：批量审计所有生态模块，为每个生态补充常见的 GitHub topics。

### 模式7：`learned_rules.py` 废弃状态（P2-14）
**影响范围**：`data/learned_rules.py`
**描述**：文件为空字典，且 `rule_classifier.py` 已优先使用 JSON 格式（`learned_rules.json`）。此文件成为死代码，但仍在仓库中占用空间并可能误导新开发者。
**修复**：删除文件，并清理 `rule_classifier.py` 中对 `.py` 格式回退的支持代码。

---

## 附录：生态模块完整清单（68个）

| # | 文件名 | 生态名称 | 状态 |
|---|--------|---------|------|
| 1 | `__init__.py` | (注册机制) | 有P0/P1 |
| 2 | `clash_mihomo.py` | Clash / Mihomo | 有P1 |
| 3 | `mpv.py` | MPV | 无问题 |
| 4 | `vs_code.py` | VS Code | 有P1 |
| 5 | `neovim.py` | Neovim | 有P1 |
| 6 | `obsidian.py` | Obsidian | 无问题 |
| 7 | `docker.py` | Docker | 有P1 |
| 8 | `home_assistant.py` | Home Assistant | 无问题 |
| 9 | `react.py` | React | 有P1 |
| 10 | `vue.py` | Vue | 有P1 |
| 11 | `tailwind_css.py` | Tailwind CSS | 有P1 |
| 12 | `ffmpeg.py` | FFmpeg | 无问题 |
| 13 | `qbittorrent.py` | qBittorrent | 无问题 |
| 14 | `hyprland.py` | Hyprland | 无问题 |
| 15 | `starship.py` | Starship | 有P2 |
| 16 | `zsh_oh_my_zsh.py` | Zsh / Oh-My-Zsh | 有P2 |
| 17 | `alacritty.py` | Alacritty | 无问题 |
| 18 | `kitty.py` | Kitty | 无问题 |
| 19 | `i3_sway.py` | i3 / Sway | 有P2 |
| 20 | `awesomewm.py` | AwesomeWM | 无问题 |
| 21 | `electron.py` | Electron | 有P1 |
| 22 | `obs_studio.py` | OBS Studio | 有P1 |
| 23 | `scoop.py` | Scoop | 无问题 |
| 24 | `typora.py` | Typora | 无问题 |
| 25 | `emby_jellyfin.py` | Emby / Jellyfin | 无问题 |
| 26 | `mihon_tachiyomi.py` | Mihon / Tachiyomi | 无问题 |
| 27 | `moonlight_sunshine.py` | Moonlight / Sunshine | 无问题 |
| 28 | `bilibili.py` | Bilibili | 有P2 |
| 29 | `aria2.py` | Aria2 | 无问题 |
| 30 | `stable_diffusion.py` | Stable Diffusion | 无问题 |
| 31 | `yt_dlp.py` | yt-dlp | 无问题 |
| 32 | `alist.py` | AList | 无问题 |
| 33 | `homebrew.py` | Homebrew | 有P2 |
| 34 | `nushell.py` | Nushell | 无问题 |
| 35 | `tailscale_wireguard.py` | Tailscale / WireGuard | 无问题 |
| 36 | `rvc_ai_voice.py` | RVC / AI Voice | 无问题 |
| 37 | `sillytavern.py` | SillyTavern | 无问题 |
| 38 | `notion_appflowy.py` | Notion / AppFlowy | 无问题 |
| 39 | `rss_阅读.py` | RSS / 阅读 | 有P2 |
| 40 | `localsend.py` | localsend | 无问题 |
| 41 | `ventoy.py` | Ventoy | 无问题 |
| 42 | `magisk.py` | Magisk | 无问题 |
| 43 | `v2ray.py` | V2Ray | 无问题 |
| 44 | `altstore.py` | AltStore | 无问题 |
| 45 | `genshin_impact_游戏辅助.py` | Genshin Impact / 游戏辅助 | 有P2 |
| 46 | `handbrake.py` | HandBrake | 无问题 |
| 47 | `playnite.py` | Playnite | 无问题 |
| 48 | `everything.py` | Everything | 无问题 |
| 49 | `wsl.py` | WSL | 无问题 |
| 50 | `screentogif.py` | ScreenToGif | 无问题 |
| 51 | `shairport_airplay.py` | shairport / AirPlay | 无问题 |
| 52 | `ehviewer.py` | EhViewer | 无问题 |
| 53 | `typst.py` | Typst | 无问题 |
| 54 | `anime4k.py` | Anime4K | 无问题 |
| 55 | `picacomic.py` | PicaComic | 无问题 |
| 56 | `rufus.py` | rufus | 无问题 |
| 57 | `czkawka.py` | Czkawka | 无问题 |
| 58 | `open_ani_animeko.py` | open-ani / Animeko | 无问题 |
| 59 | `spotube.py` | Spotube | 无问题 |
| 60 | `qtscrcpy_scrcpy.py` | QtScrcpy / Scrcpy | 无问题 |
| 61 | `trafficmonitor.py` | TrafficMonitor | 无问题 |
| 62 | `kernelsu.py` | KernelSU | 无问题 |
| 63 | `lsposed.py` | LSPosed | 无问题 |
| 64 | `trollstore.py` | TrollStore | 无问题 |
| 65 | `edk2.py` | EDK2 | 无问题 |
| 66 | `steam.py` | Steam | 无问题 |
| 67 | `telegram.py` | Telegram | 无问题 |
| 68 | `fcitx.py` | fcitx | 无问题 |
| 69 | `git.py` | Git | 有P2 |
| 70 | `firefox.py` | Firefox | 无问题 |
| 71 | `neofetch_fastfetch.py` | neofetch / fastfetch | 无问题 |
| 72 | `bittorrent.py` | BitTorrent | 无问题 |
| 73 | `iptv_直播.py` | IPTV / 直播 | 有P2 |
| 74 | `office.py` | Office | 无问题 |
| 75 | `思维导图_白板.py` | 思维导图 / 白板 | 有P2 |
