#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 统一客户端：封装 API 调用、重试、模型参数管理"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any

from http_client import HTTPClient
from utils import log


class LLMProvider(ABC):
    """LLM 提供商抽象，每个厂商实现一个子类"""

    @abstractmethod
    def call(self, messages: list[dict], max_tokens: int, temperature: float) -> str | None:
        """调用 LLM API，返回原始文本响应"""
        pass

    @abstractmethod
    def name(self) -> str:
        pass


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI 兼容格式提供商（覆盖 openai / moonshot / deepseek / openrouter / xiaomimimo）"""

    def __init__(self, api_key: str, api_base: str, model: str, provider_name: str):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.provider_name = provider_name
        self.client = HTTPClient()
        self.no_system_role = False
        self.system_prompt_mode = "default"

    def name(self) -> str:
        return self.provider_name

    def call(self, messages: list[dict], max_tokens: int, temperature: float) -> str | None:
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.provider_name == "openrouter":
            headers["HTTP-Referer"] = "https://github.com"
            headers["X-Title"] = "GitHub Stars Classifier"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        max_retries = 3
        retry_codes = {429, 500, 502, 503, 504}
        for attempt in range(max_retries):
            try:
                code, body = self.client.post_json(url, payload, headers=headers, timeout=60)
                body_preview = body[:500] if body else "<空响应>"
                log(f"  ↳ API 响应: HTTP {code} | 体长 {len(body)} | 摘要: {body_preview}", "INFO")

                if code == 200:
                    return self._extract_content(body)
                elif code in retry_codes and attempt < max_retries - 1:
                    wait = 2 ** attempt
                    log(f"  ↳ HTTP {code}，{wait}s 后重试 ({attempt + 1}/{max_retries})", "WARN")
                    time.sleep(wait)
                    continue
                else:
                    log(f"  ↳ HTTP {code} 错误: {body[:200]}", "WARN")
                    return None
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    log(f"  ↳ 调用异常: {e}，{wait}s 后重试 ({attempt + 1}/{max_retries})", "WARN")
                    time.sleep(wait)
                    continue
                log(f"  ↳ 调用异常: {e}", "WARN")
                return None

    @staticmethod
    def _extract_content(body: str) -> str | None:
        """从 API 响应体中提取 content / reasoning_content"""
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None

        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            alt = data.get("content") or data.get("text") or data.get("response")
            if isinstance(alt, str):
                return alt
            return None

        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            alt = choices[0] if isinstance(choices[0], str) else None
            return alt

        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

        reasoning = message.get("reasoning_content") or message.get("reasoning")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning

        return None


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
