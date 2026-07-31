"""
输出解析器模块

提供LLM响应内容的解析功能，用于从模型输出中提取结构化数据。
核心功能：
1. 解析JSON对象内容
2. 处理Markdown代码块
3. 提取AgentView结构
"""

from __future__ import annotations

import json
from typing import Any

from trade_runtime.decision.models import AgentView


def parse_json_object_content(content: str | None) -> dict[str, Any] | None:
    """解析JSON对象内容

    从文本中提取JSON对象，支持多种格式：
    - 直接JSON字符串
    - Markdown代码块包裹的JSON
    - 文本中嵌入的JSON对象

    Args:
        content: 待解析的文本内容

    Returns:
        dict[str, Any] | None: 解析成功返回字典，失败返回None
    """
    normalized_content = str(content or "").strip()
    if not normalized_content:
        return None
    candidates = [normalized_content]
    if normalized_content.startswith("```"):
        lines = normalized_content.splitlines()
        if len(lines) >= 3:
            candidates.append("\n".join(lines[1:-1]).strip())
    first_brace = normalized_content.find("{")
    last_brace = normalized_content.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(normalized_content[first_brace:last_brace + 1])
    seen: set[str] = set()
    for candidate in candidates:
        compact = str(candidate or "").strip()
        if not compact or compact in seen:
            continue
        seen.add(compact)
        try:
            payload = json.loads(compact)
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            return payload
    return None


def parse_agent_view_content(content: str | None) -> dict[str, Any] | None:
    """解析AgentView内容

    从文本中提取并验证AgentView结构。

    Args:
        content: 待解析的文本内容

    Returns:
        dict[str, Any] | None: 解析成功返回AgentView字典，失败返回None
    """
    payload = parse_json_object_content(content)
    if payload is None:
        return None
    try:
        return AgentView(
            bias=str(payload.get("bias") or "").strip(),
            confidence=int(payload.get("confidence")),
            reason=str(payload.get("reason") or "").strip(),
            ttl=int(payload.get("ttl")),
            risk_note=str(payload.get("risk_note") or payload.get("riskNote") or "").strip(),
        ).model_dump()
    except Exception:
        return None
