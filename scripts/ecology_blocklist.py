#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生态排除统一核心逻辑 —— 本地 CLI 和 GitHub Action 共用"""

import os
from typing import Optional

import yaml

from ecology_candidates import EcologyCandidatePool
from utils import log


# 补充的通用噪声词（无法从现有规则自动推导的泛称）
NOISE_WORDS: set[str] = {
    "应用", "客户端", "工具", "软件", "程序", "系统",
    "app", "client", "tool", "utility", "software", "program",
}


def _load_yaml(yaml_path: str) -> dict:
    """安全加载 ecology_blocklist.yaml，不存在时返回空结构。"""
    if not os.path.exists(yaml_path):
        return {"topics": [], "name_prefixes": [], "notes": {}}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {
            "topics": list(data.get("topics", [])),
            "name_prefixes": list(data.get("name_prefixes", [])),
            "notes": dict(data.get("notes", {})),
        }
    except (OSError, yaml.YAMLError):
        return {"topics": [], "name_prefixes": [], "notes": {}}


def _save_yaml(yaml_path: str, data: dict) -> None:
    """保存 YAML，保持原有格式（注释由 YAML loader 保留有限，但至少不损坏）。"""
    from utils import atomic_write

    def _write(f):
        # 保持与现有 ecology_blocklist.yaml 一致的格式
        f.write("# 生态发现 blocklist —— 手动排除不应被识别为生态的 topic/前缀\n")
        f.write("# 修改后随代码提交，GitHub Actions 自动生效\n#\n")
        f.write("# 说明：\n")
        f.write("# - topics: 排除的 topics，对应 topic_cluster 发现方式\n")
        f.write("# - name_prefixes: 排除的命名前缀，对应 name_prefix 发现方式\n")
        f.write("# - 备注仅用于文档，不影响逻辑\n#\n")
        f.write("# 大部分平台和类型关键词已由代码自动从 PLATFORM_RULES / TYPE_RULES 推导，\n")
        f.write("# 此处只补充自动推导未覆盖的边缘情况。\n\n")
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
    atomic_write(yaml_path, _write)


def _infer_indicator(state) -> tuple[str, str]:
    """从候选状态推断最应排除的 indicator 及其类型。

    优先检查 NOISE_WORDS（通用噪声词），其次选最短的关键词
    （更通用，误触发面更大）。

    Returns:
        (indicator, indicator_type) — indicator_type 为 "topic" 或 "name_prefix"
    """
    patterns = state.suggested_patterns or {}
    topic_patterns = patterns.get("topic_patterns", [])
    name_patterns = patterns.get("name_patterns", [])

    # 1. 优先检查 topic_patterns 是否命中 NOISE_WORDS
    for topic in topic_patterns:
        if topic.lower() in NOISE_WORDS:
            return topic, "topic"

    # 2. 优先检查 name_patterns 是否命中 NOISE_WORDS
    for prefix in name_patterns:
        if prefix.lower() in NOISE_WORDS:
            return prefix, "name_prefix"

    # 3. 选最短的 topic_patterns（更通用）
    if topic_patterns:
        indicator = min(topic_patterns, key=len)
        return indicator, "topic"

    # 4. 选最短的 name_patterns
    if name_patterns:
        indicator = min(name_patterns, key=len)
        return indicator, "name_prefix"

    # fallback：用候选名本身
    return state.name if hasattr(state, "name") else "", "topic"


def exclude_ecology(
    candidate_name: str,
    pool_path: str,
    yaml_path: str,
) -> Optional[dict]:
    """排除指定生态候选：从候选池读取信息、推断待排除项、更新 blocklist。

    返回排除结果字典（含 indicator / reason / example_projects 等），
    若候选不存在或已排除则返回 None。
    """
    pool = EcologyCandidatePool(pool_path)
    state = pool.candidates.get(candidate_name)
    if not state:
        return None

    indicator, indicator_type = _infer_indicator(state)
    if not indicator:
        indicator = candidate_name.lower()

    # 构建理由
    reasons: list[str] = []
    patterns = state.suggested_patterns or {}
    if patterns.get("topic_patterns"):
        reasons.append(f"topic_patterns: {patterns['topic_patterns']}")
    if patterns.get("name_patterns"):
        reasons.append(f"name_patterns: {patterns['name_patterns']}")

    reason = (
        f"'{candidate_name}' 被识别为生态候选，"
        f"但其核心特征（{indicator}）属于通用平台/类型关键词或前缀，"
        f"不应作为独立生态。"
    )
    if reasons:
        reason += f" 触发特征: {'; '.join(reasons)}"

    # 更新 blocklist
    updated = apply_exclusion(
        yaml_path,
        indicator=indicator,
        indicator_type=indicator_type,
        reason=reason,
    )
    if not updated:
        log(f"[{candidate_name}] indicator '{indicator}' 已在 blocklist 中", "WARN")
        return None

    # 标记候选为 rejected
    state.status = "rejected"
    state.rejected_reason = f"blocklist via exclude_ecology: {indicator}"
    pool.save()
    log(f"[{candidate_name}] 已排除 (indicator={indicator}, type={indicator_type})", "OK")

    return {
        "indicator": indicator,
        "indicator_type": indicator_type,
        "reason": reason,
        "candidate_name": candidate_name,
        "appear_count": state.appear_count,
        "example_projects": sorted(state.example_projects),
    }


def apply_exclusion(
    yaml_path: str,
    indicator: str,
    indicator_type: str,
    reason: str = "",
) -> bool:
    """更新 ecology_blocklist.yaml，添加新的排除项。

    Returns:
        True 表示成功添加；False 表示已存在，未修改。
    """
    data = _load_yaml(yaml_path)
    indicator_lower = indicator.lower()

    existing = {k.lower() for k in data.get("topics", [])}
    existing.update(k.lower() for k in data.get("name_prefixes", []))
    if indicator_lower in existing:
        return False

    if indicator_type == "name_prefix":
        data["name_prefixes"].append(indicator_lower)
    else:
        data["topics"].append(indicator_lower)

    if reason:
        data["notes"][indicator_lower] = reason

    _save_yaml(yaml_path, data)
    return True
