#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI 兼容格式 Provider（覆盖 openai / moonshot / deepseek / openrouter / xiaomimimo）"""

import json

from .base import LLMProvider
from http_client import HTTPClient
from utils import log


class OpenAICompatibleProvider(LLMProvider):
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
        """单次 API 调用，无重试逻辑（重试由 LLMClient.call 统一处理）。"""
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

        code, body = self.client.post_json(url, payload, headers=headers, timeout=60)
        body_preview = body[:500] if body else "<空响应>"
        log(f"  ↳ API 响应: HTTP {code} | 体长 {len(body)} | 摘要: {body_preview}", "INFO")

        if code == 200:
            return self._extract_content(body)
        log(f"  ↳ HTTP {code} 错误: {body[:200]}", "WARN")
        return None

    @staticmethod
    def _extract_content(body: str) -> str | None:
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
