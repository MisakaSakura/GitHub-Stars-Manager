#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分类规则配置：平台、类型、生态归属、生态角色"""

# 规则版本：平台/类型分类体系发生不兼容变更时递增
# 用于 feedback 系统判断旧修正是否仍适用
RULES_VERSION = "2026-05-17-platform-refactor"

# ==================== 平台分类规则 ====================
# 平台 = 操作系统 / 运行时环境，严格区别于应用形态
PLATFORM_RULES = {
    "Android": [
        "android", "apk", "aar", "android-app"
    ],
    "iOS": [
        "ios", "swift", "objective-c", "objc", "iphone", "ipad", "ipa"
    ],
    "Windows": [
        "windows", "win32", "win64", "uwp", "wsl", "winforms", "wpf", "windows-app"
    ],
    "Linux": [
        "linux", "ubuntu", "debian", "fedora", "arch", "gentoo", "redhat", "centos"
    ],
    "macOS": [
        "macos", "mac-os", "osx", "darwin", "apple"
    ],
    "Web": [
        "browser", "web", "html5", "pwa", "webapp"
    ],
    "跨平台": [
        "cross-platform", "multi-platform", "electron", "tauri", "qt", "flutter", "react-native", "xamarin"
    ],
}

# ==================== 类型分类规则 ====================
# 类型 = 应用形态 + 功能角色
TYPE_RULES = {
    "框架 / Framework": ["framework", "library", "sdk", "runtime", "engine"],
    "工具 / Tool": ["tool", "utility", "generator", "builder", "scaffold", "boilerplate", "helper"],
    "应用 / App": ["app", "application", "client", "service", "portal"],
    "Web 前端": [
        "frontend", "react", "vue", "angular", "svelte", "next.js", "nuxt",
        "webpack", "vite", "spa", "ssr", "dom", "browser-ui",
        "tailwind", "bootstrap", "preact", "solidjs", "astro", "remix", "gatsby"
    ],
    "Web 后端": [
        "backend", "api", "server", "rest", "graphql", "web-framework",
        "fastapi", "django", "express", "spring", "flask", "laravel", "nestjs", "gin", "fiber"
    ],
    "移动端 App": [
        "mobile", "ios-app", "android-app", "apk", "ipa",
        "play-store", "app-store", "cordova", "capacitor", "expo", "ionic"
    ],
    "桌面 GUI": [
        "desktop", "gui", "cross-platform-gui",
        "nw.js", "wxwidgets", "gtk", "native-app"
    ],
    "CLI / 终端": [
        "cli", "terminal", "shell", "command-line", "bash", "zsh",
        "powershell", "tmux", "fish", "nushell", "starship"
    ],
    "游戏": [
        "game", "unity", "unreal", "godot", "bevy", "love2d", "cocos",
        "rpg", "fps", "moba", "visual-novel", "launcher",
        "game-engine", "emulator", "retroarch", "rom", "save-editor", "trainer"
    ],
    "编辑器 / IDE": ["editor", "ide", "vscode", "vim", "neovim", "emacs", "jetbrains", "text-editor", "code-editor"],
    "资源合集 / Awesome": ["awesome", "list", "curated", "resources", "awesome-list", "cheatsheet", "roadmap"],
    "语言 / Compiler": ["language", "compiler", "interpreter", "transpiler", "bytecode"],
    "监控 / 可视化": ["monitoring", "dashboard", "visualization", "metrics", "observability", "chart", "plot", "grafana"],
    "自动化 / 工作流": ["automation", "workflow", "integration", "bot", "cron", "scheduler", "n8n", "ifttt"],
    "笔记 / 知识管理": ["notes", "knowledge", "wiki", "markdown", "second-brain", "documentation", "zettelkasten"],
    "算法 / 学习": ["algorithm", "leetcode", "interview", "tutorial", "course", "book", "study"],
    "配置 / Dotfiles": ["dotfiles", "config", "configuration", "settings", "preset", "rc-file"],
    "其他 / 未分类": [],
}

# ==================== 生态归属规则 ====================
# 生态规则已按生态拆分到 ecologies/ 目录下，每个生态一个独立文件。
# 新增生态：直接在 ecologies/ 下新建 .py 文件调用 register_ecology() 即可。
from ecologies import ECOLOGY_RULES  # noqa: E402

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
    "magisk": "Magisk", "magisk 生态": "Magisk",
    "v2ray": "V2Ray", "v2fly": "V2Ray", "v2ray 生态": "V2Ray",
    "genshin": "Genshin Impact / 游戏辅助", "genshin impact": "Genshin Impact / 游戏辅助",
    "genshin 生态": "Genshin Impact / 游戏辅助", "starrail": "Genshin Impact / 游戏辅助",
    "handbrake": "HandBrake", "handbrake 生态": "HandBrake",
    "altstore": "AltStore", "altstore 生态": "AltStore",
    "playnite": "Playnite", "playnite 生态": "Playnite",
    "everything": "Everything", "everything 生态": "Everything",
    "wsl": "WSL", "wsl 生态": "WSL",
    "shairport": "shairport / AirPlay", "airplay": "shairport / AirPlay",
    "shairport 生态": "shairport / AirPlay",
    "git": "Git", "git 生态": "Git",
    "firefox": "Firefox", "firefox 生态": "Firefox", "zen-browser": "Firefox",
    "neofetch": "neofetch / fastfetch", "fastfetch": "neofetch / fastfetch",
    "neofetch 生态": "neofetch / fastfetch", "fastfetch 生态": "neofetch / fastfetch",
    "iptv": "IPTV / 直播", "iptv 生态": "IPTV / 直播", "直播": "IPTV / 直播",
    "office": "Office", "office 生态": "Office",
    "mind-map": "思维导图 / 白板", "mindmap": "思维导图 / 白板", "whiteboard": "思维导图 / 白板",
    "思维导图": "思维导图 / 白板",
    "bittorrent": "BitTorrent", "bittorrent 生态": "BitTorrent",
    "trackerslist": "BitTorrent",
    "telegram": "Telegram", "telegram 生态": "Telegram",
    "steam": "Steam", "steam 生态": "Steam",
    "edk2": "EDK2", "edk2 生态": "EDK2",
    "fcitx": "fcitx", "fcitx 生态": "fcitx", "fcitx5": "fcitx",
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
    "bit-torrent": "BitTorrent", "bt": "BitTorrent",
    "airplay": "AirPlay",
    "hms": "HMS",

    # OBS / 新生态
    "obs": "OBS Studio", "obs studio": "OBS Studio", "obs-studio": "OBS Studio",
    "obs 生态": "OBS Studio", "obsstudio": "OBS Studio",
    "streamfx": "OBS Studio", "input-overlay": "OBS Studio",
    "scoop": "Scoop", "scoop 生态": "Scoop",
    "typora": "Typora", "typora 生态": "Typora",
    "moonlight": "Moonlight / Sunshine", "sunshine": "Moonlight / Sunshine",
    "moonlight 生态": "Moonlight / Sunshine", "sunshine 生态": "Moonlight / Sunshine",
    "apollo": "Moonlight / Sunshine",
    "mihon": "Mihon / Tachiyomi", "tachiyomi": "Mihon / Tachiyomi",
    "mihon 生态": "Mihon / Tachiyomi", "tachiyomi 生态": "Mihon / Tachiyomi",
    "emby": "Emby / Jellyfin", "jellyfin": "Emby / Jellyfin",
    "emby 生态": "Emby / Jellyfin", "jellyfin 生态": "Emby / Jellyfin",
    "emby/jellyfin": "Emby / Jellyfin",
    "bilibili 生态": "Bilibili",
    "stable diffusion": "Stable Diffusion", "stable diffusion 生态": "Stable Diffusion",
    "sd-webui": "Stable Diffusion", "comfyui": "Stable Diffusion",
    "comfyui 生态": "Stable Diffusion", "sd": "Stable Diffusion",
    "aria2": "Aria2", "aria2 生态": "Aria2", "ariang": "Aria2",
    "yt-dlp": "yt-dlp", "yt-dlp 生态": "yt-dlp", "youtube-dl": "yt-dlp",
    "alist": "AList", "alist 生态": "AList", "openlist": "AList",
    "tailscale": "Tailscale / WireGuard", "wireguard": "Tailscale / WireGuard",
    "tailscale 生态": "Tailscale / WireGuard", "wireguard 生态": "Tailscale / WireGuard",
    "nushell": "Nushell", "nushell 生态": "Nushell",
    "homebrew": "Homebrew", "homebrew 生态": "Homebrew", "brew": "Homebrew",
    "rvc": "RVC / AI Voice", "so-vits-svc": "RVC / AI Voice", "fish-speech": "RVC / AI Voice",
    "rvc 生态": "RVC / AI Voice", "ai voice": "RVC / AI Voice",
    "sillytavern": "SillyTavern", "sillytavern 生态": "SillyTavern",
    "notion": "Notion / AppFlowy", "appflowy": "Notion / AppFlowy", "affine": "Notion / AppFlowy",
    "notion 生态": "Notion / AppFlowy", "appflowy 生态": "Notion / AppFlowy",
    "rss": "RSS / 阅读", "rss 生态": "RSS / 阅读", "阅读": "RSS / 阅读",
    "rsshub": "RSS / 阅读", "folo": "RSS / 阅读",
    "localsend": "localsend", "localsend 生态": "localsend",
    "ventoy": "Ventoy", "ventoy 生态": "Ventoy",
    "screentogif": "ScreenToGif", "screentogif 生态": "ScreenToGif",
    "typst": "Typst", "typst 生态": "Typst",
    "ehviewer": "EhViewer", "ehviewer 生态": "EhViewer",
    "picacomic": "PicaComic", "picacomic 生态": "PicaComic",
    "anime4k": "Anime4K", "anime4k 生态": "Anime4K",
    "rufus": "rufus", "rufus 生态": "rufus",
    "spotube": "Spotube", "spotube 生态": "Spotube",
    "animeko": "open-ani / Animeko", "open-ani": "open-ani / Animeko",
    "animeko 生态": "open-ani / Animeko",
    "czkawka": "Czkawka", "czkawka 生态": "Czkawka",
    "trafficmonitor": "TrafficMonitor", "trafficmonitor 生态": "TrafficMonitor",
    "scrcpy": "QtScrcpy / Scrcpy", "qtscrcpy": "QtScrcpy / Scrcpy",
    "scrcpy 生态": "QtScrcpy / Scrcpy",
    "trollstore": "TrollStore", "trollstore 生态": "TrollStore",
    "kernelsu": "KernelSU", "kernelsu 生态": "KernelSU",
    "lsposed": "LSPosed", "lsposed 生态": "LSPosed", "xposed": "LSPosed",
}

# ==================== 全字段归一化映射 ====================
# LLM 返回的分类字段都是自由文本或半约束，容易产生空格/中英文/大小写变体。
# 后处理阶段用这些表统一映射到标准名称。

# 从规则字典自动生成标准名称集合
PLATFORM_STANDARD_NAMES = list(PLATFORM_RULES.keys()) + ["其他 / 未分类"]
TYPE_STANDARD_NAMES = list(TYPE_RULES.keys()) + ["其他 / 未分类"]
ECOLOGY_ROLE_STANDARD_NAMES = list(ECOLOGY_ROLES.keys()) + ["其他 / Other"]

PLATFORM_ALIASES = {
    "android": "Android", "安卓": "Android",
    "ios": "iOS",
    "windows": "Windows", "win32": "Windows", "win64": "Windows",
    "linux": "Linux",
    "macos": "macOS", "mac-os": "macOS", "osx": "macOS", "darwin": "macOS", "apple": "macOS",
    "web": "Web", "browser": "Web",
    "跨平台": "跨平台", "cross-platform": "跨平台", "multi-platform": "跨平台",
    "其他/未分类": "其他 / 未分类", "未分类": "其他 / 未分类", "other": "其他 / 未分类",
}

TYPE_ALIASES = {
    "应用/app": "应用 / App", "app": "应用 / App", "application": "应用 / App",
    "framework": "框架 / Framework", "library": "框架 / Framework",
    "tool": "工具 / Tool", "utility": "工具 / Tool",
    "web前端": "Web 前端", "web 前端": "Web 前端", "frontend": "Web 前端",
    "web后端": "Web 后端", "web 后端": "Web 后端", "backend": "Web 后端",
    "移动端app": "移动端 App", "移动端 app": "移动端 App", "mobile": "移动端 App",
    "桌面gui": "桌面 GUI", "桌面 gui": "桌面 GUI", "desktop": "桌面 GUI",
    "cli/终端": "CLI / 终端", "cli 终端": "CLI / 终端", "命令行": "CLI / 终端",
    "游戏": "游戏", "game": "游戏",
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
# 自动从 ECOLOGY_RULES 生成 + 补充不在规则中的独立生态
ECOLOGY_STANDARD_NAMES = list(ECOLOGY_RULES.keys()) + [
    "独立项目", "AI/ML", "Android", "Apple", "AirPlay", "HMS",
]
