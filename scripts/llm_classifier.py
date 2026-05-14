#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于 LLM 的智能分类器"""

import json
import os
import re
import time

from http_client import HTTPClient
from utils import log


class LLMClassifier:
    """基于 LLM 的智能分类器，支持真正的批量分类以减少 API 调用。
    模型参数（max_tokens、batch_size、system_prompt 策略等）自动从 model_profiles 拉取。
    """

    def __init__(self, api_key, provider="openai", api_base=None, model="gpt-4o-mini"):
        self.api_key = api_key
        self.provider = provider.lower()
        self.model = model
        self.cache = {}
        self.cache_file = ".llm_cache.json"
        self._load_cache()
        self.client = HTTPClient()

        # 加载模型参数画像（自动匹配最优配置）
        from model_profiles import get_profile
        self.profile = get_profile(model)
        if self.profile:
            log(f"[ModelProfile] {model} → batch={self.profile.batch_size}, reasoning={self.profile.is_reasoning}, "
                f"batch_max_tokens={self.profile.batch_max_tokens}, single_max_tokens={self.profile.single_max_tokens}", "INFO")
        else:
            log(f"[ModelProfile] {model} 未注册，使用保守默认值", "WARN")

        # batch_size 优先从 profile 读取，回退到 config
        from config import LLM_CONFIG
        self.batch_size = (self.profile.batch_size if self.profile else None) or LLM_CONFIG.get("batch_size", 5)

        # 优先级：CLI 传入 > config_llm.py 配置 > provider 默认值
        config_base = LLM_CONFIG.get("api_base")
        fallback_base = api_base or config_base

        if self.provider == "openai":
            self.api_base = fallback_base or "https://api.openai.com/v1"
        elif self.provider == "moonshot":
            self.api_base = fallback_base or "https://api.moonshot.cn/v1"
        elif self.provider == "deepseek":
            self.api_base = fallback_base or "https://api.deepseek.com/v1"
        elif self.provider == "openrouter":
            self.api_base = fallback_base or "https://openrouter.ai/api/v1"
        else:
            self.api_base = fallback_base or "https://api.openai.com/v1"

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _make_cache_key(self, item):
        """缓存键使用稳定的 full_name，避免描述变化导致重复调用"""
        owner = item.get("owner", {})
        login = owner.get("login") if isinstance(owner, dict) else str(owner)
        name = item.get("name", "")
        return f"{login}/{name}"

    def classify(self, item):
        """单条分类（带缓存）"""
        cache_key = self._make_cache_key(item)
        if cache_key in self.cache:
            return self.cache[cache_key]

        prompt = self._build_prompt(item)
        max_tokens = self.profile.get_max_tokens("single") if self.profile else 1024
        content = self._call_api(prompt, max_tokens=max_tokens)

        if content:
            try:
                result = self._parse_single_response(content)
                self.cache[cache_key] = result
                self._save_cache()
                return result
            except Exception as e:
                log(f"LLM 单条解析失败: {e}", "WARN")

        return None

    def classify_batch(self, items, fallback=False, round_label=""):
        """批量分类，按 batch_size 分组，真正减少 API 调用次数

        Args:
            fallback: batch 失败时是否回退到单条处理（多轮重试策略中应设为 False）
            round_label: 轮次标签，用于进度显示（如 "第 2/3 轮重试"）
        """
        if not items:
            return {}

        results = {}
        uncached_items = []
        for item in items:
            cache_key = self._make_cache_key(item)
            key = f"{item['owner']['login']}/{item['name']}"
            if cache_key in self.cache:
                results[key] = self.cache[cache_key]
            else:
                uncached_items.append(item)

        if not uncached_items:
            return results

        total = len(uncached_items)
        total_batches = (total + self.batch_size - 1) // self.batch_size
        from config import LLM_CONFIG
        max_consecutive = LLM_CONFIG.get("max_consecutive_failures", 3)

        label = f" [{round_label}]" if round_label else ""
        log(f"LLM{label} 开始: {total} 个项目, batch_size={self.batch_size}, 预计 {total_batches} 次 API 调用", "STEP")
        start_time = time.time()
        success_count = 0
        fail_count = 0
        consecutive_failures = 0

        for i in range(0, total, self.batch_size):
            batch = uncached_items[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            batch_start = time.time()

            batch_results = self._classify_batch(batch, fallback=fallback)
            batch_elapsed = time.time() - batch_start

            if batch_results:
                results.update(batch_results)
                success_count += len(batch_results)
                consecutive_failures = 0
                status = f"OK({len(batch_results)}个)"
            else:
                fail_count += len(batch)
                consecutive_failures += 1
                status = "FAIL"

            processed = min(i + self.batch_size, total)
            elapsed_total = time.time() - start_time
            avg_per_batch = elapsed_total / batch_num if batch_num > 0 else 0
            remaining_batches = total_batches - batch_num
            eta = avg_per_batch * remaining_batches

            log(f"[LLM] Batch {batch_num}/{total_batches} {status} | 已处理 {processed}/{total} | 本批 {batch_elapsed:.1f}s | 平均 {avg_per_batch:.1f}s/batch | 预计剩余 {eta/60:.1f}min", "STEP")

            if consecutive_failures >= max_consecutive:
                log(f"LLM 连续 {consecutive_failures} 个 batch 失败，已终止本轮后续分析", "ERROR")
                break

            if i + self.batch_size < total:
                time.sleep(0.5)

        elapsed_total = time.time() - start_time
        log(f"LLM{label} 结束: 成功 {success_count}/{total} 个, 本轮失败 {fail_count}/{total} 个, 耗时 {elapsed_total:.1f}s", "OK")
        return results

    def _classify_batch(self, items, fallback=False):
        """对一批项目执行单次 LLM 调用"""
        prompt = self._build_batch_prompt(items)
        # 自动从 profile 获取 batch 场景的 max_tokens
        max_tokens = self.profile.get_max_tokens("batch") if self.profile else 2048
        content = self._call_api(prompt, max_tokens=max_tokens)

        if not content:
            if fallback:
                log("LLM batch 调用失败，回退到单条处理", "WARN")
                return self._fallback_single(items)
            log(f"  ↳ batch 调用失败，跳过 {len(items)} 个项目（将计入下一轮重试）", "WARN")
            return {}

        try:
            parsed = self._parse_batch_response(content, items)
            for key in parsed:
                # key 格式为 "owner/name"
                self.cache[key] = parsed[key]
            self._save_cache()
            return parsed
        except Exception as e:
            if fallback:
                log(f"LLM batch 解析失败，回退到单条处理: {e}", "WARN")
                return self._fallback_single(items)
            log(f"  ↳ batch 解析失败，跳过 {len(items)} 个项目: {e}", "WARN")
            return {}

    def _fallback_single(self, items):
        """batch 失败时回退到逐个单条处理"""
        log(f"  ↳ 回退到单条处理: {len(items)} 个项目...", "WARN")
        results = {}
        for idx, item in enumerate(items, 1):
            key = f"{item['owner']['login']}/{item['name']}"
            result = self.classify(item)
            if result:
                results[key] = result
                log(f"    [{idx}/{len(items)}] {key} OK", "OK")
            else:
                log(f"    [{idx}/{len(items)}] {key} FAIL", "WARN")
        return results

    def _build_prompt(self, item):
        topics = ", ".join(item.get("topics", []))
        readme = item.get("readme_excerpt", "")
        readme_section = f"\nREADME摘要: {readme[:800]}" if readme else ""
        return f"""项目名称: {item['name']}
作者: {item['owner']['login']}
描述: {item.get('description') or '无'}
Topics: {topics or '无'}
语言: {item.get('language') or '未指定'}{readme_section}

请分类。"""

    def _build_batch_prompt(self, items):
        from config import LLM_CONFIG
        readme_max = LLM_CONFIG.get("batch_readme_max_length", 150)
        lines = []
        for idx, item in enumerate(items, 1):
            topics = ", ".join(item.get("topics", []))
            readme = item.get("readme_excerpt", "")
            readme_part = f" | README: {readme[:readme_max]}" if readme else ""
            lines.append(
                f"{idx}. {item['owner']['login']}/{item['name']}: "
                f"{item.get('description') or '无'} "
                f"(Topics: {topics or '无'}, 语言: {item.get('language') or '未指定'}){readme_part}"
            )

        projects_text = "\n".join(lines)
        return f"""请为以下 {len(items)} 个项目分类，返回 JSON 数组，数组中第 N 个元素对应上面第 N 个项目：

{projects_text}

请严格按以下格式输出 JSON 数组，不要包含任何其他内容（如 markdown 代码块标记）：
[
  {{"platform": "最匹配的平台", "type": "最匹配的类型", "ecology": "最匹配的生态（没有则填 null）", "ecology_role": "生态内角色（没有则填 null）", "confidence": 0.85, "reason": "简要说明分类理由", "ai_summary": "50字概括", "ai_tags": ["标签1"], "ai_platforms": ["linux", "web"]}},
  ...
]"""

    def summarize(self, text: str, system_prompt: str | None = None, max_tokens: int = None) -> str | None:
        """通用文本摘要，返回摘要字符串。max_tokens 自动从 profile 读取"""
        from config import LLM_CONFIG, LLM_SYSTEM_PROMPT
        if max_tokens is None:
            max_tokens = self.profile.get_max_tokens("summarize") if self.profile else 512
        # 显式区分 "未传入"(None) 和 "传入空字符串"
        sp = LLM_SYSTEM_PROMPT if system_prompt is None else system_prompt
        result = self._call_api(text, max_tokens=max_tokens, system_prompt=sp)
        return result.strip() if result else None

    def _call_api(self, prompt, max_tokens=None, system_prompt=None):
        from config import LLM_CONFIG, LLM_SYSTEM_PROMPT

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com"
            headers["X-Title"] = "GitHub Stars Classifier"

        # 显式区分 "未传入"(None) 和 "传入空字符串"
        sp = LLM_SYSTEM_PROMPT if system_prompt is None else system_prompt

        # P1 fix: system_prompt_mode 实际生效——no_thinking 模式追加强制指令
        if self.profile and self.profile.system_prompt_mode == "no_thinking":
            sp = sp + "\n\n【强制】不要输出思考过程，直接输出最终结果。不要包含任何 markdown 代码块标记。"

        # system prompt 策略：优先从 profile 读取，回退到 config
        no_system_role = False
        if self.profile:
            no_system_role = self.profile.no_system_role
        else:
            no_system_role = LLM_CONFIG.get("no_system_role", False)

        if no_system_role:
            messages = [{"role": "user", "content": f"{sp}\n\n{prompt}"}]
        else:
            messages = [
                {"role": "system", "content": sp},
                {"role": "user", "content": prompt}
            ]

        # P1 fix: temperature 优先从 profile 读取，回退到 config
        temperature = self.profile.temperature if self.profile else LLM_CONFIG.get("temperature", 0.1)
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or LLM_CONFIG.get("max_tokens", 256),
            "temperature": temperature,
        }

        max_retries = 3
        retry_codes = {429, 500, 502, 503, 504}
        for attempt in range(max_retries):
            try:
                code, body = self.client.post_json(url, payload, headers=headers, timeout=LLM_CONFIG.get("timeout", 30))
                # 调试：无论成功失败，先打印状态码和响应摘要
                body_preview = body[:500] if body else "<空响应>"
                log(f"  ↳ API 响应: HTTP {code} | 体长 {len(body)} | 摘要: {body_preview}", "INFO")

                if code == 200:
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        log(f"  ↳ 响应不是有效 JSON", "WARN")
                        return None
                    if not isinstance(data, dict):
                        log(f"  ↳ 响应格式错误: 期望 dict，实际为 {type(data).__name__}", "WARN")
                        return None
                    choices = data.get("choices")
                    if not isinstance(choices, list) or len(choices) == 0:
                        # 兼容：某些 API 直接在顶层返回 content
                        alt_content = data.get("content") or data.get("text") or data.get("response")
                        if isinstance(alt_content, str):
                            log(f"  ↳ 使用兼容路径获取 content", "OK")
                            return alt_content
                        log(f"  ↳ 响应格式错误: choices 为空或缺失，且无兼容字段", "WARN")
                        return None
                    message = choices[0].get("message") if isinstance(choices[0], dict) else None
                    if not isinstance(message, dict):
                        # 兼容：某些 API choices[0] 直接是字符串 content
                        alt_content = choices[0] if isinstance(choices[0], str) else None
                        if alt_content:
                            log(f"  ↳ 使用兼容路径 choices[0] 字符串", "OK")
                            return alt_content
                        log(f"  ↳ 响应格式错误: message 缺失或格式不对", "WARN")
                        return None
                    content = message.get("content")
                    reasoning = message.get("reasoning_content") or message.get("reasoning")

                    # 优先使用标准 content
                    if isinstance(content, str) and content.strip():
                        return content

                    # 兼容 reasoning 模型：content 为空时尝试从 reasoning_content 提取
                    if isinstance(reasoning, str) and reasoning.strip():
                        log(f"  ↳ content 为空，尝试从 reasoning_content ({len(reasoning)} 字) 提取", "WARN")
                        extracted = self._extract_json_from_text(reasoning)
                        if extracted:
                            log(f"  ↳ 从 reasoning_content 成功提取 JSON", "OK")
                            return extracted
                        # 对于 summarize 等场景，直接返回 reasoning 原文
                        log(f"  ↳ 返回 reasoning_content 原文", "WARN")
                        return reasoning

                    log(f"  ↳ 响应 content 为空且无 reasoning_content", "WARN")
                    return None
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
    def _clean_json_content(content):
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    @staticmethod
    def _extract_json_from_text(text: str) -> str | None:
        """从自然语言文本中提取 JSON 对象或数组（用于 reasoning 模型）
        P2 fix: 支持多代码块/多候选，优先选最长且以 [ 或 { 开头的"""
        text = text.strip()
        candidates = []

        # 1. 找所有 ```json ... ``` 代码块
        for match in re.finditer(r'```json\s*([\s\S]*?)\s*```', text):
            candidate = match.group(1).strip()
            if candidate.startswith("[") or candidate.startswith("{"):
                candidates.append(candidate)

        # 2. 找所有 ``` ... ``` 代码块（排除 json 标签已匹配的）
        for match in re.finditer(r'```\s*([\s\S]*?)\s*```', text):
            candidate = match.group(1).strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("[") or candidate.startswith("{"):
                # 去重：避免和 ```json 块重复
                if candidate not in candidates:
                    candidates.append(candidate)

        # 3. 找最外层 JSON 数组 [ ... ]
        arr_start = text.find("[")
        arr_end = text.rfind("]")
        if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
            candidates.append(text[arr_start:arr_end + 1])

        # 4. 找最外层 JSON 对象 { ... }
        obj_start = text.find("{")
        obj_end = text.rfind("}")
        if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
            candidates.append(text[obj_start:obj_end + 1])

        if not candidates:
            return None

        # P2 fix: 优先选最长的候选（完整 JSON 通常更长），数组优先于对象（batch 场景）
        candidates.sort(key=lambda x: (len(x), x.startswith("[")), reverse=True)
        return candidates[0]

    def _parse_single_response(self, content):
        content = self._clean_json_content(content)
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError(f"返回结果不是对象，而是 {type(result).__name__}")
        return self._extract_fields(result)

    def _parse_batch_response(self, content, items):
        content = self._clean_json_content(content)
        arr = json.loads(content)
        if not isinstance(arr, list):
            raise ValueError(f"返回结果不是数组，而是 {type(arr).__name__}")
        if len(arr) != len(items):
            raise ValueError(f"返回结果数量不匹配: 期望 {len(items)}, 实际 {len(arr)}")

        results = {}
        for item, result in zip(items, arr):
            if not isinstance(result, dict):
                raise ValueError(f"Batch 中某元素不是对象，而是 {type(result).__name__}")
            key = f"{item['owner']['login']}/{item['name']}"
            results[key] = self._extract_fields(result)
        return results

    @staticmethod
    def _extract_fields(result):
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
