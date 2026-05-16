#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 响应解析器：JSON 提取与字段规范化"""

import json
import re

from utils import log


class ResponseParser:
    """从 LLM 原始响应中提取结构化分类结果"""

    # ── 文本清洗 ──

    @staticmethod
    def clean_json(content: str) -> str:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    @staticmethod
    def extract_json_from_text(text: str) -> str | None:
        """从自然语言文本中提取 JSON 对象或数组（用于 reasoning 模型）"""
        text = text.strip()
        candidates = []

        for match in re.finditer(r'```json\s*([\s\S]*?)\s*```', text):
            candidate = match.group(1).strip()
            if candidate.startswith("[") or candidate.startswith("{"):
                candidates.append(candidate)

        for match in re.finditer(r'```\s*([\s\S]*?)\s*```', text):
            candidate = match.group(1).strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("[") or candidate.startswith("{"):
                if candidate not in candidates:
                    candidates.append(candidate)

        arr_start = text.find("[")
        arr_end = text.rfind("]")
        if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
            candidates.append(text[arr_start:arr_end + 1])

        obj_start = text.find("{")
        obj_end = text.rfind("}")
        if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
            candidates.append(text[obj_start:obj_end + 1])

        if not candidates:
            return None

        candidates.sort(key=lambda x: (len(x), x.startswith("[")), reverse=True)
        return candidates[0]

    # ── 单条解析 ──

    @classmethod
    def parse_single(cls, content: str) -> dict:
        content = cls.clean_json(content)
        # 先尝试标准 JSON 解析
        try:
            result = json.loads(content)
            if isinstance(result, dict):
                return cls._extract_fields(result)
        except json.JSONDecodeError:
            pass
        # 回退：从文本中提取 JSON
        extracted = cls.extract_json_from_text(content)
        if extracted:
            result = json.loads(extracted)
            if isinstance(result, dict):
                return cls._extract_fields(result)
        raise ValueError(f"无法解析单条响应: {content[:200]}")

    # ── 批量解析 ──

    @classmethod
    def parse_batch(cls, content: str, expected_count: int) -> dict[str, dict]:
        content = cls.clean_json(content)
        try:
            arr = json.loads(content)
        except json.JSONDecodeError:
            extracted = cls.extract_json_from_text(content)
            if not extracted:
                raise ValueError("无法从响应中提取 JSON 数组")
            arr = json.loads(extracted)

        if not isinstance(arr, list):
            raise ValueError(f"返回结果不是数组，而是 {type(arr).__name__}")
        # 允许 LLM 返回多于预期的结果，取前 expected_count 个
        if len(arr) < expected_count:
            raise ValueError(f"返回结果数量不匹配: 期望至少 {expected_count}, 实际 {len(arr)}")

        results = {}
        for i, result in enumerate(arr[:expected_count]):
            if not isinstance(result, dict):
                raise ValueError(f"Batch 中第 {i+1} 个元素不是对象，而是 {type(result).__name__}")
            results[i] = cls._extract_fields(result)
        return results

    # ── 字段提取与归一化 ──

    @staticmethod
    def _extract_fields(result: dict) -> dict:
        return {
            "platform": result.get("platform", "其他 / 未分类"),
            "type": result.get("type", "其他 / 未分类"),
            "ecology": result.get("ecology"),
            "ecology_role": result.get("ecology_role"),
            "confidence": result.get("confidence", 0.5),
            "reason": result.get("reason", ""),
            "ai_summary": result.get("ai_summary", ""),
            "ai_tags": result.get("ai_tags", []) if isinstance(result.get("ai_tags"), list) else [],
            "ai_platforms": result.get("ai_platforms", []) if isinstance(result.get("ai_platforms"), list) else [],
        }
