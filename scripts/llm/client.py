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

    @staticmethod
    def _build_feedback_context() -> str:
        """从反馈系统读取高频修正模式，生成 LLM 上下文提示"""
        import os
        feedback_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "feedback.json")
        feedback_path = os.path.abspath(feedback_path)
        if not os.path.exists(feedback_path):
            return ""

        try:
            import json
            with open(feedback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries", {})
            if not entries:
                return ""

            # 统计高频否定模式（原始生态 != 目标生态）
            from collections import Counter
            neg_patterns = Counter()
            for entry in entries.values():
                orig = entry.get("original", {})
                corr = entry.get("corrected", {})
                old_eco = orig.get("ecology", "")
                new_eco = corr.get("ecology", "")
                if old_eco and new_eco and old_eco != new_eco:
                    neg_patterns[(old_eco, new_eco)] += 1

            if not neg_patterns:
                return ""

            lines = ["\n【重要：用户已确认的分类修正案例，遇到类似项目时请优先参考】"]
            for (old, new), count in neg_patterns.most_common(8):
                if count >= 2:
                    lines.append(f"- 曾被分到 '{old}' 但用户修正为 '{new}'（已确认 {count} 次）")
            return "\n".join(lines)
        except Exception:
            return ""

    def call(self, prompt: str, system_prompt: str | None = None, max_tokens: int | None = None) -> str | None:
        """通用文本调用，返回原始响应文本。支持指数退避重试（3次）。"""
        from config import LLM_CONFIG, LLM_SYSTEM_PROMPT
        import time
        sp = LLM_SYSTEM_PROMPT if system_prompt is None else system_prompt

        # 注入反馈上下文（用户已确认的修正案例）
        fb_ctx = self._build_feedback_context()
        if fb_ctx:
            sp = sp + fb_ctx

        # no_thinking 模式追加指令
        if self.profile and self.profile.system_prompt_mode == "no_thinking":
            sp = sp + "\n\n【强制】不要输出思考过程，直接输出最终结果。不要包含任何 markdown 代码块标记。"

        if self.provider.no_system_role:
            messages = [{"role": "user", "content": f"{sp}\n\n{prompt}"}]
        else:
            messages = [{"role": "system", "content": sp}, {"role": "user", "content": prompt}]

        mt = max_tokens or self.get_max_tokens("single")
        retries = 3
        last_error = None
        for attempt in range(retries):
            try:
                return self.provider.call(messages, mt, self.get_temperature())
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    log(f"LLM 调用失败（尝试 {attempt + 1}/{retries}）: {e}，{delay:.1f}s 后重试...", "WARN")
                    time.sleep(delay)
                else:
                    log(f"LLM 调用失败（尝试 {attempt + 1}/{retries}）: {e}，放弃重试", "ERROR")
        return None
