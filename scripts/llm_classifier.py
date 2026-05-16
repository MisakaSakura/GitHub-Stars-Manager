#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于 LLM 的智能分类器（重构后薄层）

底层已分层为：
  - llm/client.py    : LLMClient + OpenAICompatibleProvider
  - llm/parser.py    : ResponseParser
  - llm/cache.py     : TTLCache
  - prompts/         : Prompt 模板

本层保持对外接口不变（契约锁定），仅作为 Facade 组合各组件。
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import log
from llm import LLMClient, ResponseParser, TTLCache
from prompts import PromptLoader


class LLMClassifier:
    """基于 LLM 的智能分类器 Facade。模型参数自动从 model_profiles 拉取。"""

    def __init__(self, api_key, provider="openai", api_base=None, model="gpt-4o-mini"):
        self.client = LLMClient(api_key, provider, api_base, model)
        self.cache = TTLCache(".llm_cache.json", ttl_seconds=0)  # 默认永不过期
        self.batch_size = self.client.batch_size

    def classify(self, item):
        """单条分类（带缓存）"""
        cache_key = self._make_cache_key(item)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        prompt = PromptLoader.render(
            "single_classify",
            name=item["name"],
            owner=item["owner"]["login"],
            description=item.get("description") or "无",
            topics=", ".join(item.get("topics", [])) or "无",
            language=item.get("language") or "未指定",
            readme_section=self._readme_section(item),
        )

        max_tokens = self.client.get_max_tokens("single")
        content = self.client.call(prompt, max_tokens=max_tokens)

        if content:
            try:
                result = ResponseParser.parse_single(content)
                self.cache.set(cache_key, result)
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
            cached = self.cache.get(cache_key)
            if cached is not None:
                results[key] = cached
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

        def process_one_batch(batch_idx, batch):
            batch_start = time.time()
            batch_results = self._classify_batch(batch, fallback=fallback)
            elapsed = time.time() - batch_start
            return batch_idx, batch_results, elapsed

        # 串行 vs 并发：batch_size 较大时串行已足够，小 batch_size 时并发有收益
        max_workers = 1 if self.batch_size >= 8 else 2

        if max_workers > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for i in range(0, total, self.batch_size):
                    batch = uncached_items[i:i + self.batch_size]
                    batch_num = i // self.batch_size + 1
                    fut = executor.submit(process_one_batch, batch_num, batch)
                    futures[fut] = batch_num
                    # 控制提交速率，避免触发 RPM 限制
                    time.sleep(0.3)

                for fut in as_completed(futures):
                    batch_num, batch_results, batch_elapsed = fut.result()
                    if batch_results:
                        results.update(batch_results)
                        success_count += len(batch_results)
                        consecutive_failures = 0
                        status = f"OK({len(batch_results)}个)"
                    else:
                        fail_count += len(batch)
                        consecutive_failures += 1
                        status = "FAIL"

                    processed_count = len(results) + fail_count
                    elapsed_total = time.time() - start_time
                    avg_per_batch = elapsed_total / batch_num if batch_num > 0 else 0
                    remaining_batches = total_batches - batch_num
                    eta = avg_per_batch * remaining_batches

                    log(f"[LLM] Batch {batch_num}/{total_batches} {status} | 已处理 {processed_count}/{total} | 本批 {batch_elapsed:.1f}s | 平均 {avg_per_batch:.1f}s/batch | 预计剩余 {eta/60:.1f}min", "STEP")

                    if consecutive_failures >= max_consecutive:
                        log(f"LLM 连续 {consecutive_failures} 个 batch 失败，已终止本轮后续分析", "ERROR")
                        # 取消剩余 futures
                        for f in futures:
                            f.cancel()
                        break
        else:
            for i in range(0, total, self.batch_size):
                batch = uncached_items[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                batch_num, batch_results, batch_elapsed = process_one_batch(batch_num, batch)

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

        prompt = PromptLoader.render(
            "batch_classify",
            count=len(items),
            projects_text="\n".join(lines),
        )

        max_tokens = self.client.get_max_tokens("batch")
        content = self.client.call(prompt, max_tokens=max_tokens)

        if not content:
            if fallback:
                log("LLM batch 调用失败，回退到单条处理", "WARN")
                return self._fallback_single(items)
            log(f"  ↳ batch 调用失败，跳过 {len(items)} 个项目（将计入下一轮重试）", "WARN")
            return {}

        try:
            parsed = ResponseParser.parse_batch(content, len(items))
            results = {}
            for idx, item in enumerate(items):
                key = f"{item['owner']['login']}/{item['name']}"
                result = parsed[idx]
                self.cache.set(self._make_cache_key(item), result)
                results[key] = result
            return results
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

    def summarize(self, text: str, system_prompt: str | None = None, max_tokens: int | None = None) -> str | None:
        """通用文本摘要，返回摘要字符串。max_tokens 自动从 profile 读取"""
        from config import LLM_SYSTEM_PROMPT
        sp = LLM_SYSTEM_PROMPT if system_prompt is None else system_prompt
        mt = max_tokens or self.client.get_max_tokens("summarize")
        result = self.client.call(text, system_prompt=sp, max_tokens=mt)
        return result.strip() if result else None

    # ---------- 内部工具 ----------

    @staticmethod
    def _make_cache_key(item):
        owner = item.get("owner", {})
        login = owner.get("login") if isinstance(owner, dict) else str(owner)
        name = item.get("name", "")
        return f"{login}/{name}"

    @staticmethod
    def _readme_section(item) -> str:
        readme = item.get("readme_excerpt", "")
        return f"\nREADME摘要: {readme[:800]}" if readme else ""
