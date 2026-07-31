from __future__ import annotations

from typing import Any, TypedDict

DEFAULT_SHORT_TERM_TTLS: dict[str, int] = {
    "market": 3600,
    "news": 3600,
    "onchain": 7200,
    "social": 1800,
    "supervisor_decision": 7200,
}


class MemoryItem(TypedDict, total=False):
    id: int | str
    agent_code: str
    symbol: str
    memory_type: str
    market_regime: str
    event_tags: list[str]
    direction: str
    action: str
    lesson_text: str
    quality_score: float
    confidence: float
    source_trace_id: str
    created_at: str


class MemoryBucket(TypedDict):
    window_seconds: int
    items: list[dict[str, Any]]
    sample_count: int


class ShortTermMemory(TypedDict):
    ttl_policy: dict[str, int]
    market: MemoryBucket
    news: MemoryBucket
    onchain: MemoryBucket
    social: MemoryBucket
    supervisor_decision: MemoryBucket


class LongTermMemory(TypedDict):
    status: str
    items: list[MemoryItem]
    selected_count: int
    max_items: int


def normalize_ttl_policy(overrides: dict[str, Any] | None = None) -> dict[str, int]:
    policy = dict(DEFAULT_SHORT_TERM_TTLS)
    if not isinstance(overrides, dict):
        return policy
    for key, value in overrides.items():
        if key not in policy:
            continue
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            continue
        if seconds > 0:
            policy[key] = seconds
    return policy
