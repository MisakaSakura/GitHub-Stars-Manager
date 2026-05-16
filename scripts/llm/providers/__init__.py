#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM Provider 插件目录"""

from .base import LLMProvider
from .openai_compatible import OpenAICompatibleProvider

__all__ = ["LLMProvider", "OpenAICompatibleProvider"]
