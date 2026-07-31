from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trade_runtime.memory.long_term import NullLongTermMemoryStore
from trade_runtime.memory.short_term import build_short_term_memory

_AGENT_CODES = ["market_agent", "news_agent", "onchain_agent", "social_agent", "supervisor_agent"]


def _event_tags(state: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for event in state.get("event_bundle") or []:
        if not isinstance(event, dict):
            continue
        for key in ("tags", "event_tags"):
            raw_tags = event.get(key)
            if isinstance(raw_tags, list):
                tags.extend(str(tag).strip() for tag in raw_tags if str(tag).strip())
        event_type = str(event.get("event_type") or "").strip()
        if event_type:
            tags.append(event_type)
    seen: set[str] = set()
    unique: list[str] = []
    for tag in tags:
        normalized = tag.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(tag)
    return unique[:20]


def _short_term_counts(short_term_memory: dict[str, Any]) -> dict[str, int]:
    return {
        key: int((short_term_memory.get(key) or {}).get("sample_count") or 0)
        for key in ("market", "news", "onchain", "social", "supervisor_decision")
    }


def _memory_store_enabled(memory_store: Any) -> bool:
    if memory_store is None:
        return False
    if memory_store.__class__.__name__ == "NullLongTermMemoryStore":
        return False
    base_url = getattr(memory_store, "base_url", None)
    if base_url is not None:
        return bool(str(base_url or "").strip())
    return True


def retrieve_memory(
    state: dict[str, Any],
    *,
    now: datetime | None = None,
    max_long_term_items: int = 5,
) -> dict[str, Any]:
    enriched = dict(state)
    current_time = now or datetime.now(timezone.utc)
    short_term_memory = build_short_term_memory(enriched, now=current_time)
    memory_store = enriched.get("memory_store") or NullLongTermMemoryStore()
    symbol = str(enriched.get("symbol") or "").strip().upper()
    tags = _event_tags(enriched)
    retrieval_status = "ready"
    retrieval_reason = ""

    selected: list[dict[str, Any]] = []
    if _memory_store_enabled(memory_store):
        try:
            for agent_code in _AGENT_CODES:
                selected.extend(
                    memory_store.search(
                        agent_code=agent_code,
                        symbol=symbol,
                        tags=tags,
                        limit=2,
                    )
                )
        except Exception as exc:
            selected = []
            retrieval_status = "error"
            retrieval_reason = str(exc).strip() or exc.__class__.__name__
    else:
        retrieval_status = "disabled"
        retrieval_reason = "memory_store_disabled"

    deduped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in selected:
        memory_id = str(item.get("id") or item.get("memory_id") or item.get("memory_key") or "")
        if memory_id and memory_id in seen_ids:
            continue
        if memory_id:
            seen_ids.add(memory_id)
        deduped.append(dict(item))
        if len(deduped) >= max_long_term_items:
            break

    memory_ids = [item.get("id") for item in deduped if item.get("id") is not None]
    trace_id = str(enriched.get("trace_id") or "")
    if memory_ids and retrieval_status == "ready":
        try:
            memory_store.record_usage(trace_id=trace_id, symbol=symbol, memory_ids=memory_ids)
        except Exception as exc:
            retrieval_status = "error"
            retrieval_reason = str(exc).strip() or exc.__class__.__name__

    enriched["short_term_memory"] = short_term_memory
    enriched["long_term_memory"] = {
        "status": retrieval_status,
        "reason": retrieval_reason,
        "items": deduped,
        "selected_count": len(deduped),
        "max_items": max_long_term_items,
    }
    enriched["memory_usage"] = {
        "trace_id": trace_id,
        "symbol": symbol,
        "used_memory_ids": memory_ids,
        "short_term_counts": _short_term_counts(short_term_memory),
        "long_term_count": len(deduped),
        "created_at": current_time.isoformat(),
    }
    enriched["memory_retrieval_status"] = retrieval_status
    return enriched
