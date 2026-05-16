#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM Provider 抽象基类"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """LLM 提供商抽象，每个厂商实现一个子类"""

    @abstractmethod
    def call(self, messages: list[dict], max_tokens: int, temperature: float) -> str | None:
        """调用 LLM API，返回原始文本响应"""
        pass

    @abstractmethod
    def name(self) -> str:
        pass
