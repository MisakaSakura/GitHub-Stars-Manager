#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 统一客户端：封装 API 调用、重试、模型参数管理"""

from .providers import OpenAICompatibleProvider
from utils import log


class LLMClient:
    """LLM 调用统一入口：组合 Provider + Profile + 缓存"""

    def __init__(self, api_key: str, provider_name: str, api_base: str | None, model: str):
        self.api_key = api_key
        self.provider_name = provider_name.lower()
        self.model = model
        self.profile = self._load_profile(model)

        base = api_base or self._default_base()
        self.provider = OpenAICompatibleProvider(api_key, base, model, self.provider_name)
        self.provider.no_system_role = (
            self.profile.no_system_role if self.profile else False
        )
        self.provider.system_prompt_mode = (
            self.profile.system_prompt_mode if self.profile else "default"
        )

        if self.profile:
            log(f"[LLMClient] {model} → batch={self.profile.batch_size}, "
                f"reasoning={self.profile.is_reasoning}", "INFO")

    def _load_profile(self, model: str):
        from model_profiles import get_profile
        return get_profile(model)

    def _default_base(self) -> str:
        defaults = {
            "openai": "https://api.openai.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "xiaomimimo": "https://api.xiaomimimo.com/v1",
        }
        return defaults.get(self.provider_name, "https://api.openai.com/v1")

    @property
    def batch_size(self) -> int:
        from config import LLM_CONFIG
        bs = (self.profile.batch_size if self.profile else None) or LLM_CONFIG.get("batch_size", 5)
        return max(1, bs)

    def get_max_tokens(self, scene: str) -> int:
        if self.profile:
            return self.profile.get_max_tokens(scene)
        defaults = {"batch": 2048, "single": 1024, "summarize": 512, "release_digest": 512}
        return defaults.get(scene, 1024)

    def get_temperature(self) -> float:
        from config import LLM_CONFIG
        t = self.profile.temperature if self.profile else LLM_CONFIG.get("temperature", 0.1)
        try:
            return float(t) if t is not None else 0.1
        except (ValueError, TypeError):
            return 0.1

    def call(self, prompt: str, system_prompt: str | None = None, max_tokens: int | None = None) -> str | None:
        """通用文本调用，返回原始响应文本"""
        from config import LLM_CONFIG, LLM_SYSTEM_PROMPT
        sp = LLM_SYSTEM_PROMPT if system_prompt is None else system_prompt

        # no_thinking 模式追加指令
        if self.profile and self.profile.system_prompt_mode == "no_thinking":
            sp = sp + "\n\n【强制】不要输出思考过程，直接输出最终结果。不要包含任何 markdown 代码块标记。"

        if self.provider.no_system_role:
            messages = [{"role": "user", "content": f"{sp}\n\n{prompt}"}]
        else:
            messages = [{"role": "system", "content": sp}, {"role": "user", "content": prompt}]

        mt = max_tokens or self.get_max_tokens("single")
        return self.provider.call(messages, mt, self.get_temperature())
