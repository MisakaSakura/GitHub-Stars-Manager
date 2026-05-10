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
    "Clash / Mihomo 生态": {
        "name_patterns": ["clash", "mihomo", "sing-box"],
        "desc_patterns": ["mihomo core", "clash core", "sing-box", "proxy", "代理"],
        "topic_patterns": ["proxy", "vpn", "mihomo", "sing-box"],
        "related_types": ["gui", "config", "rule-set", "dashboard"],
        "core_projects": ["mihomo", "clash", "sing-box"],
    },
    "MPV 播放器生态": {
        "name_patterns": ["mpv"],
        "desc_patterns": ["mpv", "media player", "lua script", "mpv plugin"],
        "topic_patterns": ["mpv", "media-player"],
        "related_types": ["script", "config", "gui", "skin", "theme", "thumbnail"],
        "core_projects": ["mpv"],
    },
    "VS Code 生态": {
        "name_patterns": ["vscode", "vs-code"],
        "desc_patterns": ["vscode extension", "visual studio code", "vs code"],
        "topic_patterns": ["vscode", "vscode-extension"],
        "related_types": ["extension", "theme", "icon-theme", "snippet"],
        "core_projects": ["vscode"],
    },
    "Neovim 生态": {
        "name_patterns": ["nvim", "neovim"],
        "desc_patterns": ["neovim", "nvim plugin", "vim plugin"],
        "topic_patterns": ["neovim", "vim"],
        "related_types": ["plugin", "colorscheme", "config", "lsp"],
        "core_projects": ["neovim"],
    },
    "Obsidian 生态": {
        "name_patterns": ["obsidian"],
        "desc_patterns": ["obsidian plugin", "obsidian theme"],
        "topic_patterns": ["obsidian"],
        "related_types": ["plugin", "theme", "snippet"],
        "core_projects": ["obsidian"],
    },
    "Home Assistant 生态": {
        "name_patterns": ["home-assistant", "hass", "homeassistant"],
        "desc_patterns": ["home assistant", "homeassistant", "smart home"],
        "topic_patterns": ["home-assistant", "smart-home"],
        "related_types": ["integration", "addon", "theme", "card"],
        "core_projects": ["home-assistant"],
    },
    "Docker 生态": {
        "name_patterns": ["docker", "container"],
        "desc_patterns": ["docker", "container", "dockerfile", "docker-compose"],
        "topic_patterns": ["docker", "containers"],
        "related_types": ["image", "compose", "registry"],
        "core_projects": ["docker", "moby"],
    },
    "React 生态": {
        "name_patterns": ["react-"],
        "desc_patterns": ["react component", "react hook", "for react"],
        "topic_patterns": ["react"],
        "related_types": ["component", "hook", "boilerplate"],
        "core_projects": ["react"],
    },
    "Vue 生态": {
        "name_patterns": ["vue-", "nuxt"],
        "desc_patterns": ["vue", "nuxt", "vuejs"],
        "topic_patterns": ["vue", "vuejs", "nuxt"],
        "related_types": ["component", "plugin", "boilerplate"],
        "core_projects": ["vue", "nuxt"],
    },
    "Tailwind CSS 生态": {
        "name_patterns": ["tailwind"],
        "desc_patterns": ["tailwind", "tailwindcss"],
        "topic_patterns": ["tailwindcss"],
        "related_types": ["plugin", "component", "ui-kit"],
        "core_projects": ["tailwindcss"],
    },
    "FFmpeg 生态": {
        "name_patterns": ["ffmpeg"],
        "desc_patterns": ["ffmpeg", "video processing", "codec"],
        "topic_patterns": ["ffmpeg"],
        "related_types": ["wrapper", "gui", "binding"],
        "core_projects": ["ffmpeg"],
    },
    "qBittorrent 生态": {
        "name_patterns": ["qbittorrent", "qbit"],
        "desc_patterns": ["qbittorrent", "bt client", "torrent"],
        "topic_patterns": ["qbittorrent", "torrent"],
        "related_types": ["theme", "plugin", "web-ui"],
        "core_projects": ["qbittorrent"],
    },
    "Hyprland 生态": {
        "name_patterns": ["hypr", "waybar", "wofi", "swww"],
        "desc_patterns": ["hyprland", "wayland compositor", "hypr"],
        "topic_patterns": ["hyprland", "wayland"],
        "related_types": ["dotfiles", "config", "theme", "plugin"],
        "core_projects": ["hyprland"],
    },
    "Zsh / Oh-My-Zsh 生态": {
        "name_patterns": ["zsh", "oh-my-zsh", "powerlevel"],
        "desc_patterns": ["zsh", "oh-my-zsh", "zsh plugin", "shell theme"],
        "topic_patterns": ["zsh", "oh-my-zsh"],
        "related_types": ["plugin", "theme", "config"],
        "core_projects": ["oh-my-zsh"],
    },
    "Starship 生态": {
        "name_patterns": ["starship"],
        "desc_patterns": ["starship", "shell prompt"],
        "topic_patterns": ["starship"],
        "related_types": ["preset", "config", "theme"],
        "core_projects": ["starship"],
    },
    "Alacritty 生态": {
        "name_patterns": ["alacritty"],
        "desc_patterns": ["alacritty", "terminal emulator"],
        "topic_patterns": ["alacritty"],
        "related_types": ["theme", "config"],
        "core_projects": ["alacritty"],
    },
    "Kitty 生态": {
        "name_patterns": ["kitty"],
        "desc_patterns": ["kitty terminal", "kitty config"],
        "topic_patterns": ["kitty"],
        "related_types": ["theme", "config", "script"],
        "core_projects": ["kitty"],
    },
    "i3 / Sway 生态": {
        "name_patterns": ["i3", "sway", "polybar", "rofi", "dunst"],
        "desc_patterns": ["i3wm", "swaywm", "tiling window manager"],
        "topic_patterns": ["i3", "sway", "window-manager"],
        "related_types": ["config", "theme", "script", "bar"],
        "core_projects": ["i3", "sway"],
    },
    "AwesomeWM 生态": {
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
