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
    # xiaomimimo 全系模型都支持深度思考（reasoning），需配合大 max_tokens 使用
    # 价格: flash ¥2.1/1M < v2.5 ¥14/1M < pro ¥21/1M；上下文: 256K-1M
    "xiaomimimo": {
        "provider": "openai",
        "api_base": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2-flash",  # 推荐：性价比最高，分类任务够用
    },
    "xiaomimimo-v2.5": {
        "provider": "openai",
        "api_base": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.5",
    },
    "xiaomimimo-pro": {
        "provider": "openai",
        "api_base": "https://api.xiaomimimo.com/v1",
        "model": "mimo-v2.5-pro",
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
    "temperature": 0.0,  # 分类任务使用确定性输出，减少结果漂移
    "timeout": 30,  # batch 请求需要更长时间
    "batch_size": 5,  # 每批处理的项目数（防止长描述项目触发 token 超限）
    "max_consecutive_failures": 3,  # 连续 batch 失败 N 次后终止，避免无底洞式消耗
    "batch_readme_max_length": 150,  # batch prompt 中每个项目的 README 截断长度（越小 prompt 越短，API 响应越快）
    "enrich_readme_max_candidates": 50,  # enrich 阶段最多获取 README 的项目数
    "no_system_role": False,  # 兼容模式：部分国产 API 不支持 system role，设为 True 时合并到 user message
    "cache_results": True,  # 缓存 LLM 结果避免重复调用
}

def _build_system_prompt() -> str:
    """动态从 config_rules.py 生成系统提示词，确保分类列表与代码规则同步。"""
    # 延迟导入避免循环依赖
    from config_rules import PLATFORM_RULES, TYPE_RULES, ECOLOGY_ROLES, ECOLOGY_STANDARD_NAMES

    platforms = ", ".join(PLATFORM_RULES.keys())
    types = ", ".join(TYPE_RULES.keys())
    roles = ", ".join(ECOLOGY_ROLES.keys())
    # P1-27: 输出全部生态名称（YAML 重构后生态数量可控，避免截断导致生态漂移）
    ecologies = ", ".join(ECOLOGY_STANDARD_NAMES)

    return f"""你是 GitHub 项目分类专家。根据项目信息直接输出严格 JSON，不要任何其他内容（不要思考过程、不要解释、不要 markdown 代码块）。

单条输出格式:
{{"platform":"平台","type":"类型","ecology":"生态或null","ecology_role":"角色或null","confidence":0.85,"reason":"分类理由","ai_summary":"50字概括","ai_tags":["标签1"],"ai_platforms":["web","cli"]}}

batch 输出格式（JSON 数组，第 N 个元素对应第 N 个项目）:
[{{"platform":"...",...}}, {{...}}, ...]

platform: {platforms}
type: {types}
ecology: 必须使用标准名称（禁止自由发挥）。标准生态: {ecologies}; 非上述生态填 null 或 独立项目
ecology_role: {roles}
confidence: 0-1。ai_summary: 50字内。ai_tags: 3-5个关键词。ai_platforms: [linux,mac,windows,docker,web,cli,ios,android]
"""


LLM_SYSTEM_PROMPT = _build_system_prompt()
