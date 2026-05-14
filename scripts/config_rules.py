#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分类规则配置：平台、类型、生态归属、生态角色"""

# ==================== 平台分类规则 ====================
PLATFORM_RULES = {
    "Web 前端": [
        "frontend", "react", "vue", "angular", "svelte", "next.js", "nuxt",
        "webpack", "vite", "spa", "ssr", "dom", "browser", "html", "css",
        "tailwind", "bootstrap", "preact", "solidjs", "astro", "remix", "gatsby"
    ],
    "Web 后端": [
        "backend", "api", "server", "rest", "graphql", "web-framework",
        "fastapi", "django", "express", "spring", "flask", "laravel", "nestjs", "gin", "fiber"
    ],
    "移动端": [
        "mobile", "ios", "android", "flutter", "react-native", "swift",
        "kotlin", "cordova", "capacitor", "expo", "ionic"
    ],
    "桌面端": [
        "desktop", "electron", "tauri", "qt", "gui", "cross-platform-gui",
        "nw.js", "wxwidgets", "gtk", "winforms", "wpf"
    ],
    "AI / 机器学习": [
        "machine-learning", "deep-learning", "ai", "llm", "neural-network",
        "stable-diffusion", "tensorflow", "pytorch", "langchain", "transformers",
        "openai", "hugging-face", "ollama", "comfyui", "invokeai", "sd-webui",
        "gpt", "claude", "gemini", "mistral", "llama"
    ],
    "DevOps / 运维": [
        "devops", "containers", "docker", "kubernetes", "cicd", "deployment",
        "infrastructure", "terraform", "ansible", "monitoring", "jenkins",
        "github-actions", "argo", "helm", "pulumi", "vagrant", "packer"
    ],
    "数据库": [
        "database", "sql", "nosql", "redis", "postgres", "mongodb", "cache",
        "key-value", "orm", "sqlite", "elasticsearch", "clickhouse",
        "timescaledb", "cassandra", "couchdb", "neo4j"
    ],
    "云原生": [
        "cloud", "serverless", "aws", "gcp", "azure", "microservices",
        "lambda", "faas", "knative", "istio", "linkerd", "envoy"
    ],
    "IoT / 嵌入式": [
        "iot", "embedded", "arduino", "raspberry-pi", "smart-home",
        "home-automation", "esp32", "firmware", "rtos", "zephyr", "platformio"
    ],
    "游戏 / 图形": [
        "game", "graphics", "webgl", "3d", "unity", "unreal", "opengl",
        "vulkan", "blender", "godot", "raytracing", "bevy", "love2d", "cocos"
    ],
    "CLI / 终端": [
        "cli", "terminal", "shell", "command-line", "bash", "zsh",
        "powershell", "tmux", "fish", "nushell", "starship"
    ],
    "安全 / 渗透": [
        "security", "pentest", "ctf", "vulnerability", "cryptography",
        "reverse-engineering", "malware", "osint", "forensics", "burp"
    ],
    "网络 / 代理": [
        "proxy", "vpn", "network", "tunnel", "wireguard", "shadowsocks",
        "v2ray", "trojan", "xray", "naiveproxy", "brook"
    ],
    "音视频 / 流媒体": [
        "video", "audio", "streaming", "media", "ffmpeg", "obs", "vlc",
        "webrtc", "rtmp", "hls", "dash", "pulseaudio", "pipewire"
    ],
}

# ==================== 类型分类规则 ====================
TYPE_RULES = {
    "框架 / Framework": ["framework", "library", "sdk", "runtime", "engine"],
    "工具 / Tool": ["tool", "cli", "utility", "generator", "builder", "scaffold", "boilerplate", "helper"],
    "应用 / App": ["app", "application", "client", "server", "platform", "service", "portal"],
    "编辑器 / IDE": ["editor", "ide", "vscode", "vim", "neovim", "emacs", "jetbrains"],
    "资源合集 / Awesome": ["awesome", "list", "curated", "resources", "awesome-list", "cheatsheet", "roadmap"],
    "语言 / Compiler": ["language", "compiler", "interpreter", "transpiler", "bytecode"],
    "监控 / 可视化": ["monitoring", "dashboard", "visualization", "metrics", "observability", "chart", "plot", "grafana"],
    "自动化 / 工作流": ["automation", "workflow", "integration", "bot", "cron", "scheduler", "n8n", "ifttt"],
    "笔记 / 知识管理": ["notes", "knowledge", "wiki", "markdown", "second-brain", "documentation", "zettelkasten"],
    "算法 / 学习": ["algorithm", "leetcode", "interview", "tutorial", "course", "book", "study"],
    "配置 / Dotfiles": ["dotfiles", "config", "configuration", "settings", "preset", "rc-file"],
}

# ==================== 生态归属规则 ====================
ECOLOGY_RULES = {
    "Clash / Mihomo": {
        "name_patterns": ["clash", "mihomo", "sing-box"],
        "desc_patterns": ["mihomo core", "clash core", "sing-box", "proxy", "代理"],
        "topic_patterns": ["proxy", "vpn", "mihomo", "sing-box"],
        "related_types": ["gui", "config", "rule-set", "dashboard"],
        "core_projects": ["mihomo", "clash", "sing-box"],
    },
    "MPV": {
        "name_patterns": ["mpv"],
        "desc_patterns": ["mpv", "media player", "lua script", "mpv plugin"],
        "topic_patterns": ["mpv", "media-player"],
        "related_types": ["script", "config", "gui", "skin", "theme", "thumbnail"],
        "core_projects": ["mpv"],
    },
    "VS Code": {
        "name_patterns": ["vscode", "vs-code"],
        "desc_patterns": ["vscode extension", "visual studio code", "vs code"],
        "topic_patterns": ["vscode", "vscode-extension"],
        "related_types": ["extension", "theme", "icon-theme", "snippet"],
        "core_projects": ["vscode"],
    },
    "Neovim": {
        "name_patterns": ["nvim", "neovim"],
        "desc_patterns": ["neovim", "nvim plugin", "vim plugin"],
        "topic_patterns": ["neovim", "vim"],
        "related_types": ["plugin", "colorscheme", "config", "lsp"],
        "core_projects": ["neovim"],
    },
    "Obsidian": {
        "name_patterns": ["obsidian"],
        "desc_patterns": ["obsidian plugin", "obsidian theme"],
        "topic_patterns": ["obsidian"],
        "related_types": ["plugin", "theme", "snippet"],
        "core_projects": ["obsidian"],
    },
    "Home Assistant": {
        "name_patterns": ["home-assistant", "hass", "homeassistant"],
        "desc_patterns": ["home assistant", "homeassistant", "smart home"],
        "topic_patterns": ["home-assistant", "smart-home"],
        "related_types": ["integration", "addon", "theme", "card"],
        "core_projects": ["home-assistant"],
    },
    "Docker": {
        "name_patterns": ["docker", "container"],
        "desc_patterns": ["docker", "container", "dockerfile", "docker-compose"],
        "topic_patterns": ["docker", "containers"],
        "related_types": ["image", "compose", "registry"],
        "core_projects": ["docker", "moby"],
    },
    "React": {
        "name_patterns": ["react-"],
        "desc_patterns": ["react component", "react hook", "for react"],
        "topic_patterns": ["react"],
        "related_types": ["component", "hook", "boilerplate"],
        "core_projects": ["react"],
    },
    "Vue": {
        "name_patterns": ["vue-", "nuxt"],
        "desc_patterns": ["vue", "nuxt", "vuejs"],
        "topic_patterns": ["vue", "vuejs", "nuxt"],
        "related_types": ["component", "plugin", "boilerplate"],
        "core_projects": ["vue", "nuxt"],
    },
    "Tailwind CSS": {
        "name_patterns": ["tailwind"],
        "desc_patterns": ["tailwind", "tailwindcss"],
        "topic_patterns": ["tailwindcss"],
        "related_types": ["plugin", "component", "ui-kit"],
        "core_projects": ["tailwindcss"],
    },
    "FFmpeg": {
        "name_patterns": ["ffmpeg"],
        "desc_patterns": ["ffmpeg", "video processing", "codec"],
        "topic_patterns": ["ffmpeg"],
        "related_types": ["wrapper", "gui", "binding"],
        "core_projects": ["ffmpeg"],
    },
    "qBittorrent": {
        "name_patterns": ["qbittorrent", "qbit"],
        "desc_patterns": ["qbittorrent", "bt client", "torrent"],
        "topic_patterns": ["qbittorrent", "torrent"],
        "related_types": ["theme", "plugin", "web-ui"],
        "core_projects": ["qbittorrent"],
    },
    "Hyprland": {
        "name_patterns": ["hypr", "waybar", "wofi", "swww"],
        "desc_patterns": ["hyprland", "wayland compositor", "hypr"],
        "topic_patterns": ["hyprland", "wayland"],
        "related_types": ["dotfiles", "config", "theme", "plugin"],
        "core_projects": ["hyprland"],
    },
    "Zsh / Oh-My-Zsh": {
        "name_patterns": ["zsh", "oh-my-zsh", "powerlevel"],
        "desc_patterns": ["zsh", "oh-my-zsh", "zsh plugin", "shell theme"],
        "topic_patterns": ["zsh", "oh-my-zsh"],
        "related_types": ["plugin", "theme", "config"],
        "core_projects": ["oh-my-zsh"],
    },
    "Starship": {
        "name_patterns": ["starship"],
        "desc_patterns": ["starship", "shell prompt"],
        "topic_patterns": ["starship"],
        "related_types": ["preset", "config", "theme"],
        "core_projects": ["starship"],
    },
    "Alacritty": {
        "name_patterns": ["alacritty"],
        "desc_patterns": ["alacritty", "terminal emulator"],
        "topic_patterns": ["alacritty"],
        "related_types": ["theme", "config"],
        "core_projects": ["alacritty"],
    },
    "Kitty": {
        "name_patterns": ["kitty"],
        "desc_patterns": ["kitty terminal", "kitty config"],
        "topic_patterns": ["kitty"],
        "related_types": ["theme", "config", "script"],
        "core_projects": ["kitty"],
    },
    "i3 / Sway": {
        "name_patterns": ["i3", "sway", "polybar", "rofi", "dunst"],
        "desc_patterns": ["i3wm", "swaywm", "tiling window manager"],
        "topic_patterns": ["i3", "sway", "window-manager"],
        "related_types": ["config", "theme", "script", "bar"],
        "core_projects": ["i3", "sway"],
    },
    "AwesomeWM": {
        "name_patterns": ["awesomewm", "awesome-wm"],
        "desc_patterns": ["awesome window manager", "awesomewm"],
        "topic_patterns": ["awesome-wm"],
        "related_types": ["config", "theme", "widget"],
        "core_projects": ["awesome"],
    },
}

# 已确认准确的生态，AI 批量分析时不会覆盖这些生态下的项目分类
# 用法示例: ["Clash / Mihomo 生态", "Neovim 生态", "VS Code 生态"]
LOCKED_ECOLOGIES = []

ECOLOGY_ROLES = {
    "核心 / Core": ["core", "kernel", "engine", "official"],
    "GUI 前端 / Client": ["gui", "client", "app", "desktop", "frontend", "verge", "nyanpasu", "party"],
    "配置 / Config": ["config", "configuration", "dotfiles", "settings", "preset"],
    "脚本 / Script": ["script", "lua", "python-script", "automation"],
    "主题 / Theme": ["theme", "skin", "color-scheme", "appearance", "icon-theme"],
    "插件 / Plugin": ["plugin", "extension", "addon", "integration"],
    "规则集 / Rules": ["rule", "rule-set", "filter", "list", "blocklist"],
    "Web UI / Dashboard": ["web-ui", "dashboard", "panel", "web"],
    "API 封装 / Wrapper": ["wrapper", "binding", "sdk", "api"],
    "教程 / Guide": ["guide", "tutorial", "awesome", "collection", "list"],
}

# ==================== 生态名称归一化 ====================
# LLM 返回的 ecology 是自由文本，容易产生 "Clash"/"Clash Meta"/"Clash / Mihomo 生态" 等变体。
# 后处理阶段用此表统一映射到标准名称。
ECOLOGY_ALIASES = {
    # Bilibili
    "b站": "Bilibili", "bilibili": "Bilibili", "哔哩哔哩": "Bilibili",
    # Clash / Mihomo（所有变体统一为简洁名称）
    "clash": "Clash / Mihomo", "clash meta": "Clash / Mihomo", "clashmeta": "Clash / Mihomo",
    "mihomo": "Clash / Mihomo", "mihomo 生态": "Clash / Mihomo",
    "clash / mihomo": "Clash / Mihomo", "clash / mihomo 生态": "Clash / Mihomo",
    "clash生态": "Clash / Mihomo", "clash 生态": "Clash / Mihomo",
    "sing-box": "Clash / Mihomo", "sing-box 生态": "Clash / Mihomo",
    # Docker
    "docker 生态": "Docker", "docker生态": "Docker", "container": "Docker",
    # AI/ML
    "ai": "AI/ML", "ai agents": "AI/ML", "ai/ml": "AI/ML", "人工智能": "AI/ML",
    # 独立项目
    "standalone": "独立项目", "none": "独立项目", "null": "独立项目",
    "独立项目 / standalone": "独立项目", "独立": "独立项目",
    # 其他常见变体（去"生态"后缀统一）
    "android 生态": "Android", "apple 生态": "Apple", "苹果": "Apple",
    "ffmpeg": "FFmpeg", "ffmpeg 生态": "FFmpeg", "ffmpeg生态": "FFmpeg",
    "electron": "Electron", "electron 生态": "Electron",
    "flutter": "Flutter", "flutter 生态": "Flutter",
    "mpv": "MPV", "mpv 播放器生态": "MPV", "mpv播放器生态": "MPV",
    "qbittorrent": "qBittorrent", "qbittorrent 生态": "qBittorrent", "qbit": "qBittorrent",
    "hyprland": "Hyprland", "hyprland 生态": "Hyprland", "hypr": "Hyprland",
    "obsidian": "Obsidian", "obsidian 生态": "Obsidian",
    "neovim": "Neovim", "neovim 生态": "Neovim", "nvim": "Neovim",
    "vscode": "VS Code", "vscode 生态": "VS Code", "vs code": "VS Code",
    "home assistant": "Home Assistant", "home assistant 生态": "Home Assistant",
    "homeassistant": "Home Assistant", "hass": "Home Assistant",
    "zsh": "Zsh / Oh-My-Zsh", "zsh 生态": "Zsh / Oh-My-Zsh",
    "oh-my-zsh": "Zsh / Oh-My-Zsh", "oh-my-zsh 生态": "Zsh / Oh-My-Zsh",
    "starship": "Starship", "starship 生态": "Starship",
    "alacritty": "Alacritty", "alacritty 生态": "Alacritty",
    "kitty": "Kitty", "kitty 生态": "Kitty",
    "i3": "i3 / Sway", "i3 生态": "i3 / Sway", "sway": "i3 / Sway", "sway 生态": "i3 / Sway",
    "awesomewm": "AwesomeWM", "awesome 生态": "AwesomeWM", "awesomewm 生态": "AwesomeWM",
    "awesome wm": "AwesomeWM",
    "react": "React", "react 生态": "React",
    "vue": "Vue", "vue 生态": "Vue", "nuxt": "Vue", "nuxt 生态": "Vue",
    "tailwind": "Tailwind CSS", "tailwind 生态": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS", "tailwindcss 生态": "Tailwind CSS",
    # 新发现生态
    "firefox": "Firefox", "firefox 生态": "Firefox",
    "git": "Git", "git 生态": "Git",
    "magisk": "Magisk", "magisk 生态": "Magisk",
    "bit-torrent": "BitTorrent", "bittorrent": "BitTorrent", "bt": "BitTorrent",
    "emby": "Emby/Jellyfin", "jellyfin": "Emby/Jellyfin", "emby/jellyfin": "Emby/Jellyfin",
    "airplay": "AirPlay",
    "hms": "HMS",
    "edk2": "EDK2",
}

# ==================== 全字段归一化映射 ====================
# LLM 返回的分类字段都是自由文本或半约束，容易产生空格/中英文/大小写变体。
# 后处理阶段用这些表统一映射到标准名称。

# 从规则字典自动生成标准名称集合
PLATFORM_STANDARD_NAMES = list(PLATFORM_RULES.keys()) + ["其他 / 未分类"]
TYPE_STANDARD_NAMES = list(TYPE_RULES.keys()) + ["其他 / 未分类"]
ECOLOGY_ROLE_STANDARD_NAMES = list(ECOLOGY_ROLES.keys()) + ["其他 / Other"]

PLATFORM_ALIASES = {
    # 只处理空格/大小写/格式变体，不强制扩展为完整名称（保留简洁写法）
    "web前端": "Web 前端", "web 前端": "Web 前端", "webfrontend": "Web 前端", "web前端/后端": "Web 前端",
    "web后端": "Web 后端", "web 后端": "Web 后端", "webbackend": "Web 后端",
    "ai/机器学习": "AI / 机器学习", "人工智能": "AI / 机器学习",
    "devops/运维": "DevOps / 运维", "运维": "DevOps / 运维",
    "iot/嵌入式": "IoT / 嵌入式", "嵌入式": "IoT / 嵌入式",
    "游戏/图形": "游戏 / 图形", "graphics": "游戏 / 图形",
    "cli/终端": "CLI / 终端", "终端": "CLI / 终端", "命令行": "CLI / 终端",
    "安全/渗透": "安全 / 渗透", "渗透": "安全 / 渗透", "security": "安全 / 渗透",
    "网络/代理": "网络 / 代理", "代理": "网络 / 代理", "proxy": "网络 / 代理",
    "音视频/流媒体": "音视频 / 流媒体", "流媒体": "音视频 / 流媒体", "media": "音视频 / 流媒体",
    "其他/未分类": "其他 / 未分类", "未分类": "其他 / 未分类", "other": "其他 / 未分类",
    "linux": "Linux", "手机端": "移动端", "pc端": "桌面端", "pc": "桌面端",
}

TYPE_ALIASES = {
    # 只处理空格/格式变体，保留 LLM 和测试使用的简洁写法
    "应用/app": "应用 / App", "app": "应用 / App", "application": "应用 / App",
    "framework": "框架 / Framework", "library": "框架 / Framework",
    "tool": "工具 / Tool", "utility": "工具 / Tool",
    "ide": "编辑器 / IDE", "editor": "编辑器 / IDE",
    "awesome": "资源合集 / Awesome", "list": "资源合集 / Awesome", "合集": "资源合集 / Awesome",
    "compiler": "语言 / Compiler", "interpreter": "语言 / Compiler",
    "monitoring": "监控 / 可视化", "dashboard": "监控 / 可视化", "可视化": "监控 / 可视化",
    "workflow": "自动化 / 工作流", "automation": "自动化 / 工作流", "工作流": "自动化 / 工作流",
    "notes": "笔记 / 知识管理", "wiki": "笔记 / 知识管理", "知识管理": "笔记 / 知识管理",
    "algorithm": "算法 / 学习", "tutorial": "算法 / 学习", "学习": "算法 / 学习",
    "dotfiles": "配置 / Dotfiles", "config": "配置 / Dotfiles",
    "其他/未分类": "其他 / 未分类", "未分类": "其他 / 未分类", "other": "其他 / 未分类",
}

ECOLOGY_ROLE_ALIASES = {
    "核心": "核心 / Core", "core": "核心 / Core", "kernel": "核心 / Core", "engine": "核心 / Core",
    "gui前端": "GUI 前端 / Client", "gui 前端": "GUI 前端 / Client", "gui前端/client": "GUI 前端 / Client",
    "client": "GUI 前端 / Client", "frontend": "GUI 前端 / Client", "app": "GUI 前端 / Client",
    "配置": "配置 / Config", "config": "配置 / Config", "configuration": "配置 / Config", "dotfiles": "配置 / Config",
    "脚本": "脚本 / Script", "script": "脚本 / Script", "lua": "脚本 / Script", "automation": "脚本 / Script",
    "主题": "主题 / Theme", "theme": "主题 / Theme", "skin": "主题 / Theme", "colorscheme": "主题 / Theme",
    "插件": "插件 / Plugin", "plugin": "插件 / Plugin", "extension": "插件 / Plugin", "addon": "插件 / Plugin",
    "规则集": "规则集 / Rules", "rules": "规则集 / Rules", "rule": "规则集 / Rules", "filter": "规则集 / Rules",
    "webui": "Web UI / Dashboard", "web ui": "Web UI / Dashboard", "web-ui": "Web UI / Dashboard",
    "dashboard": "Web UI / Dashboard", "panel": "Web UI / Dashboard",
    "api封装": "API 封装 / Wrapper", "api 封装": "API 封装 / Wrapper", "apiwrapper": "API 封装 / Wrapper",
    "wrapper": "API 封装 / Wrapper", "binding": "API 封装 / Wrapper", "sdk": "API 封装 / Wrapper",
    "教程": "教程 / Guide", "guide": "教程 / Guide", "tutorial": "教程 / Guide", "awesome": "教程 / Guide",
    "其他": "其他 / Other", "other": "其他 / Other", "null": "其他 / Other", "none": "其他 / Other", "-": "其他 / Other",
}

# 标准生态名称集合（用于系统提示限制和验证）
ECOLOGY_STANDARD_NAMES = list(ECOLOGY_RULES.keys()) + [
    "独立项目", "AI/ML", "Android", "Apple", "Bilibili", "BitTorrent",
    "AirPlay", "HMS", "EDK2", "Emby/Jellyfin", "Firefox", "Git", "Magisk",
]
