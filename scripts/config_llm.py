#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 配置：API 参数与系统提示词"""

# 提供商预设：一行 preset 同时搞定 provider + base + model
# 用法：--llm-preset <name> 或设置环境变量 LLM_PRESET
# 优先级：CLI 显式参数 > 自定义预设 > 内置预设 > config_llm.py > 内置默认值

# 内置预设（常用服务商）
PROVIDER_PRESETS = {
    "openai": {
        "provider": "openai",
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "moonshot": {
        "provider": "moonshot",
        "api_base": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "deepseek": {
        "provider": "deepseek",
        "api_base": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "openrouter": {
        "provider": "openrouter",
        "api_base": "https://openrouter.ai/api/v1",
        "model": "openrouter/auto",
    },
    "xiaomimimo": {
        "provider": "openai",   # 兼容 OpenAI 格式
        "api_base": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.5",
    },
}

# 自定义预设（用户扩展）
# 在这里添加你自己的服务商预设，键名就是 --llm-preset 的参数值
# 自定义预设会覆盖同名的内置预设
CUSTOM_PRESETS = {
    # 示例：
    # "mycompany": {
    #     "provider": "openai",
    #     "api_base": "https://llm.mycompany.com/v1",
    #     "model": "company-model-v1",
    # },
}

LLM_CONFIG = {
    # 注意：LLM 启用由 --llm-key 参数控制，不再使用此 enabled 字段
    "provider": "openai",  # 支持: openai, moonshot, deepseek, openrouter
    "api_key": None,
    "api_base": None,  # 自定义 base url，如 "https://api.moonshot.cn/v1" 或 "https://api.mimo.run/v1"
                         # 优先级：--llm-base CLI 参数 > 此处配置 > provider 内置默认值
    "model": "gpt-4o-mini",  # 或 "moonshot-v1-8k", "deepseek-chat"
    "max_tokens": 256,
    "temperature": 0.1,
    "timeout": 30,  # batch 请求需要更长时间
    "batch_size": 5,  # 每批处理的项目数（防止长描述项目触发 token 超限）
    "max_consecutive_failures": 3,  # 连续 batch 失败 N 次后终止，避免无底洞式消耗
    "batch_readme_max_length": 150,  # batch prompt 中每个项目的 README 截断长度（越小 prompt 越短，API 响应越快）
    "no_system_role": False,  # 兼容模式：部分国产 API 不支持 system role，设为 True 时合并到 user message
    "cache_results": True,  # 缓存 LLM 结果避免重复调用
}

LLM_SYSTEM_PROMPT = """你是一个 GitHub 项目分类专家。请根据项目名称、描述、Topics 和 README 摘要，为项目选择最合适的分类。

请严格按照以下 JSON 格式输出（不要有任何其他内容）：
{
  "platform": "最匹配的平台",
  "type": "最匹配的类型",
  "ecology": "最匹配的生态（如果没有则填 null）",
  "ecology_role": "生态内角色（如果没有则填 null）",
  "confidence": 0.85,
  "reason": "简要说明分类理由",
  "ai_summary": "用50字以内概括这个项目的核心用途",
  "ai_tags": ["标签1", "标签2", "标签3"],
  "ai_platforms": ["linux", "mac", "windows", "docker", "web", "cli", "ios", "android"]
}

可选的平台：Web 前端, Web 后端, 移动端, 桌面端, AI / 机器学习, DevOps / 运维, 数据库, 云原生, IoT / 嵌入式, 游戏 / 图形, CLI / 终端, 安全 / 渗透, 网络 / 代理, 音视频 / 流媒体, 其他 / 未分类
可选的类型：框架 / Framework, 工具 / Tool, 应用 / App, 编辑器 / IDE, 资源合集 / Awesome, 语言 / Compiler, 监控 / 可视化, 自动化 / 工作流, 笔记 / 知识管理, 算法 / 学习, 配置 / Dotfiles, 其他 / 未分类
可选的生态角色：核心 / Core, GUI 前端 / Client, 配置 / Config, 脚本 / Script, 主题 / Theme, 插件 / Plugin, 规则集 / Rules, Web UI / Dashboard, API 封装 / Wrapper, 教程 / Guide, 其他 / 未分类

ai_summary 要求：简洁明了，让不看 README 的人也能快速理解项目用途。
ai_tags 要求：3-5 个关键词标签，类似应用商店分类，如 ["database", "kv-store", "high-performance"]。
ai_platforms 要求：从 [linux, mac, windows, docker, web, cli, ios, android] 中选择该项目支持的平台。如果无法判断则返回 ["web", "cli"]。
"""
