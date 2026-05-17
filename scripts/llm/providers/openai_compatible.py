#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI 兼容格式 Provider（覆盖 openai / moonshot / deepseek / openrouter / xiaomimimo）"""

import json

from .base import LLMProvider
from http_client import HTTPClient
from utils import log


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI 兼容格式 Provider。

    设计约定（GC-11）:
    - 本层只负责单次 API 调用，不处理重试
    - HTTP 错误（非 200）时抛出 RuntimeError，由 LLMClient 统一重试
    - 200 但解析失败时返回 None（表示响应格式问题，通常不应重试）
    """

    # P1-33: 默认响应提取路径（OpenAI 标准格式 + 常见兼容格式）
    DEFAULT_EXTRACT_PATHS = [
        "choices.0.message.content",
        "choices.0.message.reasoning_content",
        "choices.0.message.reasoning",
        "content",
        "text",
        "response",
    ]

    def __init__(self, api_key: str, api_base: str, model: str, provider_name: str):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.provider_name = provider_name
        self.client = HTTPClient()
        self.no_system_role = False
        self.system_prompt_mode = "default"
        self._extract_paths: list[str] = []  # 延迟加载

    def _get_extract_paths(self) -> list[str]:
        """获取响应提取路径：优先从 ModelProfile 读取，否则使用默认路径（P1-33）。"""
        if self._extract_paths:
            return self._extract_paths
        from model_profiles import get_profile
        profile = get_profile(self.model)
        if profile and profile.response_extract_paths:
            self._extract_paths = profile.response_extract_paths
        else:
            self._extract_paths = list(self.DEFAULT_EXTRACT_PATHS)
        return self._extract_paths

    def name(self) -> str:
        return self.provider_name

    def call(self, messages: list[dict], max_tokens: int, temperature: float) -> str | None:
        """单次 API 调用。HTTP 错误时抛出 RuntimeError，由上层重试。"""
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
        # GC-11: HTTP 错误抛异常，由 LLMClient 统一重试
        raise RuntimeError(f"LLM API HTTP {code}: {body[:200]}")

    def _extract_content(self, body: str) -> str | None:
        """从 JSON 响应中提取内容，使用配置化的提取路径（P1-33）。"""
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None

        # 尝试所有配置化的提取路径
        for path in self._get_extract_paths():
            result = self._get_by_path(data, path)
            if isinstance(result, str) and result.strip():
                return result

        return None

    @staticmethod
    def _get_by_path(data: dict, path: str):
        """按点分隔路径从嵌套字典中提取值。

        示例:
            _get_by_path(data, "choices.0.message.content")
            => data["choices"][0]["message"]["content"]
        """
        current = data
        for part in path.split("."):
            if current is None:
                return None
            # 支持数组索引（如 "0" -> choices[0]）
            if part.isdigit():
                idx = int(part)
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
        return current
