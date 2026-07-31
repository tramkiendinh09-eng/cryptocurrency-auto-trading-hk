from __future__ import annotations

import json
from typing import Any

_FORBIDDEN_PHRASES = ["一定", "稳赚", "必然", "all in", "满仓"]


def should_store_memory_candidate(candidate: dict[str, Any]) -> bool:
    if not bool(candidate.get("should_store", True)):
        return False
    lesson_text = str(candidate.get("lesson_text") or "").strip()
    if len(lesson_text) < 8:
        return False
    lowered = lesson_text.lower()
    if any(phrase in lowered for phrase in _FORBIDDEN_PHRASES):
        return False
    try:
        evidence_count = int(candidate.get("evidence_count") or 0)
        quality_score = float(candidate.get("quality_score") or 0.0)
        confidence = float(candidate.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return False
    # 放宽门槛：只要有证据且质量/置信度不为零即可存储
    # LLM可能返回较低的数值，不应因此拒绝有效记忆
    return evidence_count >= 1 and quality_score >= 0.3 and confidence >= 0.3


def build_memory_summary_prompt(*, decision_payload: dict[str, Any], outcome_metrics: dict[str, Any]) -> str:
    return (
        "You are a trading-memory summarizer for BTC/crypto agents.\n"
        "Create ONE conservative long-term memory only if the post-decision outcome validates a reusable lesson.\n"
        "Do not create rules that encourage over-leverage, all-in behavior, or bypassing risk controls.\n"
        "Return JSON only with fields: should_store, agent_code, memory_type, market_regime, event_tags, "
        "direction, action, lesson_text, evidence, evidence_count, quality_score, confidence.\n\n"
        f"Decision payload JSON:\n{json.dumps(decision_payload, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Post-decision outcome JSON:\n{json.dumps(outcome_metrics, ensure_ascii=False, sort_keys=True)}"
    )


def _parse_model_json(model_response: dict[str, Any]) -> dict[str, Any]:
    raw_content = model_response.get("content") or model_response.get("text") or model_response
    if isinstance(raw_content, dict):
        return dict(raw_content)
    text = str(raw_content or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _payload_value(payload: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return default


def _normalize_candidate(
    candidate: dict[str, Any],
    *,
    decision_payload: dict[str, Any],
    outcome_metrics: dict[str, Any],
) -> dict[str, Any]:
    trace_id = str(_payload_value(decision_payload, "traceId", "trace_id", default="")).strip()
    symbol = str(_payload_value(decision_payload, "symbol", default="")).strip().upper()
    agent_code = str(candidate.get("agent_code") or candidate.get("agentCode") or "supervisor_agent").strip()
    memory_type = str(candidate.get("memory_type") or candidate.get("memoryType") or "lesson").strip()
    event_tags = candidate.get("event_tags") or candidate.get("eventTags") or []
    if not isinstance(event_tags, list):
        event_tags = []
    evidence = candidate.get("evidence") or candidate.get("evidence_json") or {}
    return {
        "memory_key": f"{agent_code}:{symbol}:{trace_id}:{memory_type}",
        "agent_code": agent_code,
        "symbol": symbol,
        "memory_type": memory_type,
        "market_regime": str(candidate.get("market_regime") or candidate.get("marketRegime") or "").strip(),
        "event_tags": [str(tag).strip() for tag in event_tags if str(tag).strip()][:12],
        "direction": str(candidate.get("direction") or _payload_value(decision_payload, "side", default="")).strip(),
        "action": str(candidate.get("action") or _payload_value(decision_payload, "action", default="")).strip(),
        "lesson_text": str(candidate.get("lesson_text") or candidate.get("lessonText") or "").strip(),
        "evidence_json": evidence if isinstance(evidence, (dict, list)) else {"text": str(evidence)},
        "outcome_json": dict(outcome_metrics),
        "quality_score": float(candidate.get("quality_score") or candidate.get("qualityScore") or 0.0),
        "confidence": float(candidate.get("confidence") or 0.0),
        "source_trace_id": trace_id,
        "evidence_count": int(candidate.get("evidence_count") or candidate.get("evidenceCount") or 0),
        "should_store": bool(candidate.get("should_store", candidate.get("shouldStore", True))),
    }


def _memory_store_available(memory_store: Any) -> bool:
    if memory_store is None:
        return False
    if memory_store.__class__.__name__ == "NullLongTermMemoryStore":
        return False
    base_url = getattr(memory_store, "base_url", None)
    if base_url is not None:
        return bool(str(base_url or "").strip())
    return True


def create_memory_from_evaluated_decision(
    *,
    decision_payload: dict[str, Any],
    outcome_metrics: dict[str, Any],
    model_client: Any,
    memory_store: Any,
    model_id: int | None = None,
) -> dict[str, Any]:
    prompt = build_memory_summary_prompt(decision_payload=decision_payload, outcome_metrics=outcome_metrics)
    model_response = model_client.call_model(model_id=model_id, prompt=prompt)
    raw_candidate = _parse_model_json(model_response)
    if not raw_candidate:
        return {"status": "rejected", "reason": "invalid_model_json"}
    candidate = _normalize_candidate(
        raw_candidate,
        decision_payload=decision_payload,
        outcome_metrics=outcome_metrics,
    )
    if not should_store_memory_candidate(candidate):
        return {"status": "rejected", "reason": "candidate_failed_quality_gate", "candidate": candidate}
    stored_payload = dict(candidate)
    stored_payload.pop("evidence_count", None)
    stored_payload.pop("should_store", None)
    if not _memory_store_available(memory_store):
        return {"status": "failed", "reason": "memory_store_disabled", "candidate": candidate}
    created = memory_store.create_memory(stored_payload)
    if not isinstance(created, dict) or not created:
        return {"status": "failed", "reason": "memory_store_create_failed", "candidate": candidate}
    return {"status": "stored", "memory": created or stored_payload, "candidate": candidate}
