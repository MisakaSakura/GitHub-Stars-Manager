#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 模型配置中心 — 遍历主流厂商模型，自动匹配最优参数。

设计目标：
1. 每款模型绑定一组经过验证的参数（max_tokens、temperature、system_prompt 策略等）
2. LLMClassifier 根据当前 model 名自动拉取 profile，不再硬编码
3. 新增模型只需在这里注册，零侵入业务代码
"""

from dataclasses import dataclass, field
from typing import Optional

# P1-34: 评分权重常量
PRICE_WEIGHT = 10.0          # 价格系数（越低越好）
NON_REASONING_BONUS = 50     # 非 reasoning 模型加分
JSON_MODE_BONUS = 20         # 原生 JSON 模式加分
LARGE_CONTEXT_BONUS = 10     # 大上下文加分
MIN_CONTEXT_LIMIT = 32_000   # 最小上下文限制
LARGE_CONTEXT_THRESHOLD = 128_000  # 大上下文阈值


@dataclass
class ModelProfile:
    """单个模型的完整参数画像"""
    provider: str                # 所属服务商（openai/moonshot/deepseek/xiaomimimo...）
    model_id: str                # 模型标识（如 gpt-4o-mini）
    display_name: str            # 人类可读名称
    context_limit: int           # 上下文上限（tokens）
    max_output: int              # 模型自身的最大输出长度
    is_reasoning: bool           # 是否是 reasoning/thinking 模型（会消耗额外 tokens）
    supports_json_mode: bool     # 是否原生支持 response_format={type:"json_object"}
    no_system_role: bool         # 是否不支持 system role（需合并到 user）

    # 各场景 max_tokens（由项目经验 + 模型文档推导）
    batch_max_tokens: int        # batch 分类（多个项目同时分析）
    single_max_tokens: int       # 单条分类
    summarize_max_tokens: int    # 文本摘要 / 周报总结
    release_digest_max_tokens: int  # Release Notes 摘要
    ecology_review_max_tokens: int = 128  # 生态候选审查（默认 128，通常只需简短 JSON）

    temperature: float = 0.1     # 默认 temperature
    batch_size: int = 5          # 默认 batch_size（prompt 越长应越小）
    batch_readme_max_length: int = 150  # batch prompt 中 README 截断长度（P1-51: 移至 ModelProfile）

    # 定价参考（输出侧，单位：元 / 1M tokens，仅用于排序推荐）
    price_cny_per_1m_output: float = 0.0

    # 响应提取路径（P1-33: 配置化替代硬编码）
    # 格式: "choices.0.message.content" 表示 data["choices"][0]["message"]["content"]
    response_extract_paths: list[str] = field(default_factory=list)

    # system prompt 策略
    system_prompt_mode: str = "default"  # default / no_thinking / no_system_role

    # 推荐理由摘要
    recommendation: str = ""

    def get_max_tokens(self, scene: str) -> int:
        """根据场景返回匹配的 max_tokens（P1-31: 显式支持 ecology_review 场景）。"""
        mapping = {
            "batch": self.batch_max_tokens,
            "single": self.single_max_tokens,
            "summarize": self.summarize_max_tokens,
            "release_digest": self.release_digest_max_tokens,
            "ecology_review": self.ecology_review_max_tokens,
        }
        return mapping.get(scene, self.single_max_tokens)


# ═══════════════════════════════════════════════════════════════
# 模型注册表 — 遍历主流厂商，参数经过项目实战验证
# ═══════════════════════════════════════════════════════════════

MODEL_PROFILES: dict[str, ModelProfile] = {
    # ── OpenAI ──
    "gpt-4o-mini": ModelProfile(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="OpenAI GPT-4o mini",
        context_limit=128_000,
        max_output=16_384,
        is_reasoning=False,
        supports_json_mode=True,
        no_system_role=False,
        batch_max_tokens=2048,
        single_max_tokens=1024,
        summarize_max_tokens=512,
        release_digest_max_tokens=512,
        temperature=0.1,
        batch_size=8,
        batch_readme_max_length=150,
        price_cny_per_1m_output=4.40,  # 约 $0.60
        system_prompt_mode="default",
        recommendation="非 reasoning、速度快、价格低，分类任务首选。"
    ),
    "gpt-4o": ModelProfile(
        provider="openai",
        model_id="gpt-4o",
        display_name="OpenAI GPT-4o",
        context_limit=128_000,
        max_output=16_384,
        is_reasoning=False,
        supports_json_mode=True,
        no_system_role=False,
        batch_max_tokens=2048,
        single_max_tokens=1024,
        summarize_max_tokens=512,
        release_digest_max_tokens=512,
        temperature=0.1,
        batch_size=8,
        batch_readme_max_length=200,
        price_cny_per_1m_output=109.00,
        system_prompt_mode="default",
        recommendation="能力最强但贵，只有对分类精度极度敏感时才用。"
    ),

    # ── Moonshot ──
    "moonshot-v1-8k": ModelProfile(
        provider="moonshot",
        model_id="moonshot-v1-8k",
        display_name="Moonshot v1-8k",
        context_limit=8_000,
        max_output=8_000,
        is_reasoning=False,
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=2048,
        single_max_tokens=1024,
        summarize_max_tokens=512,
        release_digest_max_tokens=512,
        temperature=0.1,
        batch_size=5,
        batch_readme_max_length=100,
        price_cny_per_1m_output=12.00,
        system_prompt_mode="default",
        recommendation="上下文较短（8K），适合小批量分析。"
    ),
    "moonshot-v1-32k": ModelProfile(
        provider="moonshot",
        model_id="moonshot-v1-32k",
        display_name="Moonshot v1-32k",
        context_limit=32_000,
        max_output=32_000,
        is_reasoning=False,
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=4096,
        single_max_tokens=2048,
        summarize_max_tokens=1024,
        release_digest_max_tokens=1024,
        temperature=0.1,
        batch_size=5,
        batch_readme_max_length=150,
        price_cny_per_1m_output=24.00,
        system_prompt_mode="default",
        recommendation="32K 上下文，适合中等规模 batch。"
    ),
    "moonshot-v1-128k": ModelProfile(
        provider="moonshot",
        model_id="moonshot-v1-128k",
        display_name="Moonshot v1-128k",
        context_limit=128_000,
        max_output=128_000,
        is_reasoning=False,
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=4096,
        single_max_tokens=2048,
        summarize_max_tokens=1024,
        release_digest_max_tokens=1024,
        temperature=0.1,
        batch_size=5,
        batch_readme_max_length=200,
        price_cny_per_1m_output=60.00,
        system_prompt_mode="default",
        recommendation="128K 上下文，价格偏贵。"
    ),

    # ── DeepSeek ──
    "deepseek-chat": ModelProfile(
        provider="deepseek",
        model_id="deepseek-chat",
        display_name="DeepSeek-V3 (Chat)",
        context_limit=64_000,
        max_output=8_192,
        is_reasoning=True,           # 有 thinking 过程
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=4096,
        single_max_tokens=2048,
        summarize_max_tokens=1024,
        release_digest_max_tokens=1024,
        temperature=0.1,
        batch_size=5,
        batch_readme_max_length=150,
        price_cny_per_1m_output=2.00,
        system_prompt_mode="no_thinking",
        recommendation="reasoning 模型，价格便宜（¥2/1M），需给足 max_tokens。"
    ),
    "deepseek-reasoner": ModelProfile(
        provider="deepseek",
        model_id="deepseek-reasoner",
        display_name="DeepSeek-R1 (Reasoner)",
        context_limit=64_000,
        max_output=8_192,
        is_reasoning=True,
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=4096,
        single_max_tokens=2048,
        summarize_max_tokens=1024,
        release_digest_max_tokens=1024,
        temperature=0.1,
        batch_size=5,
        price_cny_per_1m_output=8.00,
        system_prompt_mode="no_thinking",
        recommendation="深度推理版，thinking 更长，适合需要强逻辑分析的场景。"
    ),

    # ── xiaomimimo ──
    # 文档: https://platform.xiaomimimo.com/docs/zh-CN/pricing
    # 全系支持深度思考，输出价格从 ¥2.1 ~ ¥21/1M
    "mimo-v2-flash": ModelProfile(
        provider="xiaomimimo",
        model_id="mimo-v2-flash",
        display_name="MiMo V2 Flash",
        context_limit=256_000,
        max_output=64_000,
        is_reasoning=True,
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=8192,
        single_max_tokens=4096,
        summarize_max_tokens=2048,
        release_digest_max_tokens=2048,
        temperature=0.1,
        batch_size=5,
        batch_readme_max_length=300,
        price_cny_per_1m_output=2.10,
        system_prompt_mode="no_thinking",
        recommendation="xiaomimimo 性价比之王（¥2.1/1M），分类任务完全够用，推荐作为默认。"
    ),
    "mimo-v2.5": ModelProfile(
        provider="xiaomimimo",
        model_id="mimo-v2.5",
        display_name="MiMo V2.5",
        context_limit=1_000_000,
        max_output=128_000,
        is_reasoning=True,
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=8192,
        single_max_tokens=4096,
        summarize_max_tokens=2048,
        release_digest_max_tokens=2048,
        temperature=0.1,
        batch_size=5,
        batch_readme_max_length=400,
        price_cny_per_1m_output=14.00,
        system_prompt_mode="no_thinking",
        recommendation="全模态理解，比 flash 强但贵 6.7 倍。"
    ),
    "mimo-v2.5-pro": ModelProfile(
        provider="xiaomimimo",
        model_id="mimo-v2.5-pro",
        display_name="MiMo V2.5 Pro",
        context_limit=1_000_000,
        max_output=128_000,
        is_reasoning=True,
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=8192,
        single_max_tokens=4096,
        summarize_max_tokens=2048,
        release_digest_max_tokens=2048,
        temperature=0.1,
        batch_size=5,
        price_cny_per_1m_output=21.00,
        system_prompt_mode="no_thinking",
        recommendation="最强能力，但价格是 flash 的 10 倍，分类任务没必要。"
    ),

    # ── OpenRouter（聚合路由，模型不固定，用保守参数） ──
    "openrouter/auto": ModelProfile(
        provider="openrouter",
        model_id="openrouter/auto",
        display_name="OpenRouter Auto",
        context_limit=128_000,
        max_output=16_384,
        is_reasoning=False,  # 不固定，保守起见按非 reasoning 处理
        supports_json_mode=False,
        no_system_role=False,
        batch_max_tokens=2048,
        single_max_tokens=1024,
        summarize_max_tokens=512,
        release_digest_max_tokens=512,
        temperature=0.1,
        batch_size=5,
        batch_readme_max_length=150,
        price_cny_per_1m_output=10.00,  # 不固定
        system_prompt_mode="default",
        recommendation="自动路由到最便宜的可用模型，参数保守适配。"
    ),
}


def get_profile(model_id: str) -> Optional[ModelProfile]:
    """根据模型 ID 获取参数画像，未知模型返回 None"""
    return MODEL_PROFILES.get(model_id)


def recommend_model(preferred_provider: Optional[str] = None) -> str:
    """
    根据项目需求推荐最适合的模型。

    排序逻辑（综合考虑）：
    1. 非 reasoning 优先（不需要额外处理 thinking）
    2. 价格低优先（分类任务不需要最强模型）
    3. 上下文够大（至少 32K，保证 batch prompt 放得下）
    4. 支持 JSON 输出稳定
    """
    candidates = list(MODEL_PROFILES.values())

    # 过滤掉明显不合适的
    candidates = [m for m in candidates if m.context_limit >= MIN_CONTEXT_LIMIT]

    # 评分：价格低 + 非 reasoning 加分
    def score(m: ModelProfile) -> float:
        s = 0.0
        s -= m.price_cny_per_1m_output * PRICE_WEIGHT
        if not m.is_reasoning:
            s += NON_REASONING_BONUS
        if m.supports_json_mode:
            s += JSON_MODE_BONUS
        if m.context_limit >= LARGE_CONTEXT_THRESHOLD:
            s += LARGE_CONTEXT_BONUS
        return s

    candidates.sort(key=score, reverse=True)
    return candidates[0].model_id if candidates else "gpt-4o-mini"


def get_compatible_profiles(provider: Optional[str] = None) -> list[ModelProfile]:
    """获取指定厂商的全部模型画像，或全部"""
    if provider:
        return [p for p in MODEL_PROFILES.values() if p.provider == provider]
    return list(MODEL_PROFILES.values())


# 预设 → 默认模型映射（用于 PROVIDER_PRESETS 的 model 字段自动补全）
PRESET_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "moonshot": "moonshot-v1-8k",
    "deepseek": "deepseek-chat",
    "openrouter": "openrouter/auto",
    "xiaomimimo": "mimo-v2-flash",
    "xiaomimimo-v2.5": "mimo-v2.5",
    "xiaomimimo-pro": "mimo-v2.5-pro",
}


def get_preset_default_model(preset_name: str) -> str:
    """获取预设的默认模型，未知则回退到推荐模型"""
    return PRESET_DEFAULT_MODELS.get(preset_name, recommend_model())
