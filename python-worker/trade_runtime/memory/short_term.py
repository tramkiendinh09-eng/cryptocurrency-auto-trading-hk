"""
短期记忆模块

构建和管理交易决策的短期记忆，包括：
- 市场事件记忆
- 新闻事件记忆
- 链上事件记忆
- 社交事件记忆
- 主管决策记忆

支持TTL过期和容量限制。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trade_runtime.memory.schema import ShortTermMemory, normalize_ttl_policy

_SOURCE_TO_BUCKET = {
    "market_tick": "market",
    "mark_price": "market",
    "funding_rate": "market",
    "liquidation": "market",
    "news": "news",
    "onchain": "onchain",
    "social": "social",
}


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.isdigit():
        timestamp = int(text)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _age_seconds(item: dict[str, Any], now: datetime) -> float | None:
    observed_at = _parse_datetime(
        item.get("event_time")
        or item.get("observed_at")
        or item.get("created_at")
        or item.get("timestamp")
        or item.get("ts")
    )
    if observed_at is None:
        return None
    return (now - observed_at).total_seconds()


def _within_ttl(item: dict[str, Any], *, now: datetime, ttl_seconds: int) -> bool:
    age = _age_seconds(item, now)
    return age is not None and 0 <= age <= ttl_seconds


def _bucket(window_seconds: int, items: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    bounded = items[-limit:]
    return {
        "window_seconds": window_seconds,
        "items": bounded,
        "sample_count": len(bounded),
    }


def build_short_term_memory(
    state: dict[str, Any],
    *,
    now: datetime | None = None,
    ttl_overrides: dict[str, Any] | None = None,
    per_bucket_limit: int = 20,
) -> ShortTermMemory:
    """构建短期记忆

    从决策状态中提取各类事件，按类型分组并过滤过期数据。

    Args:
        state: 决策状态
        now: 当前时间，默认为UTC当前时间
        ttl_overrides: TTL覆盖配置
        per_bucket_limit: 每个桶的最大条目数

    Returns:
        ShortTermMemory: 短期记忆结构
    """
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    ttl_policy = normalize_ttl_policy(ttl_overrides)
    grouped: dict[str, list[dict[str, Any]]] = {
        "market": [],
        "news": [],
        "onchain": [],
        "social": [],
        "supervisor_decision": [],
    }

    for event in state.get("event_bundle") or []:
        if not isinstance(event, dict):
            continue
        bucket_name = _SOURCE_TO_BUCKET.get(str(event.get("event_type") or "").strip().lower())
        if bucket_name and _within_ttl(event, now=current_time, ttl_seconds=ttl_policy[bucket_name]):
            grouped[bucket_name].append(dict(event))

    for entry in state.get("market_context_history") or []:
        if isinstance(entry, dict) and _within_ttl(entry, now=current_time, ttl_seconds=ttl_policy["market"]):
            grouped["market"].append(dict(entry))

    for message in state.get("agent_messages") or []:
        if not isinstance(message, dict):
            continue
        speaker = str(message.get("speaker_agent") or message.get("speakerAgent") or "").strip()
        if speaker == "supervisor_agent" and _within_ttl(message, now=current_time, ttl_seconds=ttl_policy["supervisor_decision"]):
            grouped["supervisor_decision"].append(dict(message))

    return {
        "ttl_policy": ttl_policy,
        "market": _bucket(ttl_policy["market"], grouped["market"], per_bucket_limit),
        "news": _bucket(ttl_policy["news"], grouped["news"], per_bucket_limit),
        "onchain": _bucket(ttl_policy["onchain"], grouped["onchain"], per_bucket_limit),
        "social": _bucket(ttl_policy["social"], grouped["social"], per_bucket_limit),
        "supervisor_decision": _bucket(ttl_policy["supervisor_decision"], grouped["supervisor_decision"], per_bucket_limit),
    }
