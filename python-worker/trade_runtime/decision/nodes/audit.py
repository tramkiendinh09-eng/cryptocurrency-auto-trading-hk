import json

from trade_runtime.decision.agent_profile_resolver import resolve_agent_config
from trade_runtime.decision.dispatch import (
    build_suppression_reason_codes,
    derive_dispatch_mode,
    is_specialist_active,
    normalize_selected_agents,
    resolve_active_specialists,
)
from trade_runtime.decision.state import DecisionState


def _normalized_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalized_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalized_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalized_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _json_compact(value: object, default: object) -> str:
    payload = value if value is not None else default
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str)


def _normalized_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _normalized_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _build_signal_events_payload(state: DecisionState) -> list[dict]:
    trace_id = _normalized_str(state.get("trace_id"))
    symbol = _normalized_str(state.get("symbol"))
    event_bundle = state.get("event_bundle")
    if not isinstance(event_bundle, list):
        return []

    payload: list[dict] = []
    for event in event_bundle:
        if not isinstance(event, dict):
            continue
        item = {
            "traceId": trace_id,
            "symbol": symbol,
            "signalType": _normalized_str(event.get("event_type"), "unknown"),
            "featureJson": json.dumps(event, separators=(",", ":"), ensure_ascii=False, default=str),
        }
        score = _normalized_float(event.get("score"))
        if score is not None:
            item["score"] = score
        payload.append(item)
    return payload


def _build_signal_window_states_payload(state: DecisionState) -> list[dict]:
    trace_id = _normalized_str(state.get("trace_id"))
    signal_window_states = state.get("signal_window_states")
    if not isinstance(signal_window_states, list):
        return []

    payload: list[dict] = []
    for signal_window_state in signal_window_states:
        if not isinstance(signal_window_state, dict):
            continue
        state_value = signal_window_state.get("state")
        state_json = signal_window_state.get("state_json")
        if state_json is None and state_value is not None:
            state_json = json.dumps(state_value, separators=(",", ":"), ensure_ascii=False, default=str)
        payload.append(
            {
                "traceId": trace_id,
                "symbol": _normalized_str(signal_window_state.get("symbol") or state.get("symbol")),
                "windowKey": _normalized_str(signal_window_state.get("window_key") or signal_window_state.get("windowKey")),
                "sourceType": _normalized_str(signal_window_state.get("source_type") or signal_window_state.get("sourceType")),
                "signalType": _normalized_str(signal_window_state.get("signal_type") or signal_window_state.get("signalType")),
                "direction": _normalized_str(signal_window_state.get("direction")),
                "strengthScore": _normalized_float(
                    signal_window_state.get("strength_score") or signal_window_state.get("strengthScore")
                ),
                "decayScore": _normalized_float(
                    signal_window_state.get("decay_score") or signal_window_state.get("decayScore")
                ),
                "openedAt": _normalized_str(signal_window_state.get("opened_at") or signal_window_state.get("openedAt")),
                "expiresAt": _normalized_str(signal_window_state.get("expires_at") or signal_window_state.get("expiresAt")),
                "lastEventAt": _normalized_str(
                    signal_window_state.get("last_event_at") or signal_window_state.get("lastEventAt")
                ),
                "lastConfirmedAt": _normalized_str(
                    signal_window_state.get("last_confirmed_at") or signal_window_state.get("lastConfirmedAt")
                ),
                "dedupeKey": _normalized_str(signal_window_state.get("dedupe_key") or signal_window_state.get("dedupeKey")),
                "combineUntilAt": _normalized_str(
                    signal_window_state.get("combine_until_at") or signal_window_state.get("combineUntilAt")
                ),
                "active": _normalized_bool(signal_window_state.get("active", signal_window_state.get("is_active")), True),
                "stateJson": _normalized_str(state_json),
            }
        )
    return payload


def _agent_views(state: DecisionState) -> tuple[tuple[str, dict], ...]:
    active_specialists = set(resolve_active_specialists(state))
    specialist_views = (
        ("market_agent", "market", state.get("market_view")),
        ("news_agent", "news", state.get("news_view")),
        ("onchain_agent", "onchain", state.get("onchain_view")),
        ("social_agent", "social", state.get("social_view")),
    )
    return tuple(
        (agent_name, view)
        for agent_code, agent_name, view in specialist_views
        if agent_code in active_specialists
    )


def _feature_subset(feature_snapshot: dict, keys: tuple[str, ...]) -> dict:
    return {
        key: feature_snapshot[key]
        for key in keys
        if key in feature_snapshot
    }


def _build_agent_runs_payload(state: DecisionState) -> list[dict]:
    trace_id = _normalized_str(state.get("trace_id"))
    symbol = _normalized_str(state.get("symbol"))
    event_strength = _normalized_str(state.get("event_strength"))
    payload: list[dict] = []
    for agent_name, view in _agent_views(state):
        if not isinstance(view, dict) or not view:
            continue
        payload.append(
            {
                "traceId": trace_id,
                "symbol": symbol,
                "agentName": agent_name,
                "eventStrength": event_strength,
                "status": "completed",
            }
        )
    return payload


def _build_agent_observations_payload(state: DecisionState) -> list[dict]:
    trace_id = _normalized_str(state.get("trace_id"))
    feature_snapshot = state.get("feature_snapshot")
    if not isinstance(feature_snapshot, dict):
        feature_snapshot = {}
    event_bundle = state.get("event_bundle")
    if not isinstance(event_bundle, list):
        event_bundle = []

    payload: list[dict] = []
    for agent_name, view in _agent_views(state):
        if not isinstance(view, dict) or not view:
            continue
        if agent_name == "market":
            observation = {
                "feature_snapshot": feature_snapshot,
            }
            observation_type = "feature_context"
        elif agent_name == "news":
            observation = {
                "events": [event for event in event_bundle if isinstance(event, dict) and event.get("event_type") == "news"],
                "feature_snapshot": _feature_subset(feature_snapshot, ("news_score",)),
            }
            observation_type = "event_context"
        elif agent_name == "onchain":
            observation = {
                "events": [event for event in event_bundle if isinstance(event, dict) and event.get("event_type") == "onchain"],
                "feature_snapshot": _feature_subset(feature_snapshot, ("onchain_flow_bias",)),
            }
            observation_type = "event_context"
        else:
            observation = {
                "events": [event for event in event_bundle if isinstance(event, dict) and event.get("event_type") == "social"],
                "feature_snapshot": _feature_subset(feature_snapshot, ("social_score",)),
            }
            observation_type = "event_context"
        payload.append(
            {
                "traceId": trace_id,
                "agentName": agent_name,
                "observationType": observation_type,
                "observationJson": json.dumps(
                    observation,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    default=str,
                    sort_keys=True,
                ),
            }
        )
    return payload


def _build_agent_conclusions_payload(state: DecisionState) -> list[dict]:
    trace_id = _normalized_str(state.get("trace_id"))

    payload: list[dict] = []
    for agent_name, view in _agent_views(state):
        if not isinstance(view, dict) or not view:
            continue
        confidence = _normalized_int(view.get("confidence"), 0)
        payload.append(
            {
                "traceId": trace_id,
                "agentName": agent_name,
                "bias": _normalized_str(view.get("bias"), "neutral"),
                "confidence": confidence,
                "reason": _normalized_str(view.get("reason")),
            }
        )
    return payload


def _build_agent_messages_payload(state: DecisionState) -> list[dict]:
    trace_id = _normalized_str(state.get("trace_id"))
    agent_messages = state.get("agent_messages")
    if not isinstance(agent_messages, list):
        return []

    payload: list[dict] = []
    for agent_message in agent_messages:
        if not isinstance(agent_message, dict):
            continue
        speaker_agent = _normalized_str(agent_message.get("speaker_agent"))
        target_agent = _normalized_str(agent_message.get("target_agent"))
        if not is_specialist_active(state, speaker_agent) or not is_specialist_active(state, target_agent):
            continue
        content_json = agent_message.get("content_json")
        if content_json is None:
            content_payload = agent_message.get("content")
            if not isinstance(content_payload, dict):
                content_payload = {}
            content_payload = dict(content_payload)
            if speaker_agent and "speaker_agent" not in content_payload:
                content_payload["speaker_agent"] = speaker_agent
            if target_agent and "target_agent" not in content_payload:
                content_payload["target_agent"] = target_agent
            resolved_config = resolve_agent_config(state, speaker_agent)
            template_code = _normalized_str(agent_message.get("template_code")) or _normalized_str(
                (resolved_config or {}).get("template_code")
            )
            model_code = _normalized_str(agent_message.get("model_code")) or _normalized_str(
                (resolved_config or {}).get("model_code")
            )
            if template_code and "template_code" not in content_payload:
                content_payload["template_code"] = template_code
            if model_code and "model_code" not in content_payload:
                content_payload["model_code"] = model_code
            content_json = json.dumps(
                content_payload,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            )
        payload.append(
            _agent_message_payload_item(
                trace_id=trace_id,
                agent_message=agent_message,
                speaker_agent=speaker_agent,
                target_agent=target_agent,
                content_json=content_json,
                state=state,
            )
        )
    return payload


def _agent_message_payload_item(
    *,
    trace_id: str,
    agent_message: dict,
    speaker_agent: str,
    target_agent: str,
    content_json: object,
    state: DecisionState,
) -> dict:
    resolved_config = resolve_agent_config(state, speaker_agent)
    template_code = _normalized_str(agent_message.get("template_code")) or _normalized_str(
        (resolved_config or {}).get("template_code")
    )
    model_code = _normalized_str(agent_message.get("model_code")) or _normalized_str(
        (resolved_config or {}).get("model_code")
    )
    return (
            {
                "traceId": trace_id,
                "agentRunId": agent_message.get("agent_run_id"),
                "roundNo": _normalized_int(agent_message.get("round_no"), 0),
                "speakerAgent": speaker_agent,
                "targetAgent": target_agent,
                "messageType": _normalized_str(agent_message.get("message_type")),
                "templateCode": template_code,
                "modelCode": model_code,
                "contentJson": _normalized_str(content_json, "{}"),
                "summaryText": _normalized_str(agent_message.get("summary_text")),
            }
    )


def _build_decision_payload(state: DecisionState) -> dict:
    supervisor_decision = state.get("supervisor_decision")
    if not isinstance(supervisor_decision, dict):
        supervisor_decision = {}
    supervisor_prompt_metadata = state.get("supervisor_prompt_metadata")
    if not isinstance(supervisor_prompt_metadata, dict):
        supervisor_prompt_metadata = {}
    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        execution_result = {}
    dispatch_mode = derive_dispatch_mode(state)
    selected_agents = normalize_selected_agents(state.get("selected_agents"))
    combination_match = _normalized_dict(state.get("combination_match"))
    active_signal_refs = _normalized_list(state.get("active_signal_refs"))
    active_signals = _normalized_list(state.get("active_signals"))
    suppression_reason_codes = build_suppression_reason_codes(state)
    execution_status = _normalized_str(execution_result.get("status"))
    order_status = _normalized_str(execution_result.get("order_status"))
    action = _resolve_audit_action(supervisor_decision, execution_status)
    if not execution_status and action == "SKIP":
        execution_status = "skipped"
    if not order_status and execution_status == "skipped":
        order_status = "SKIPPED"
    return {
        "traceId": _normalized_str(state.get("trace_id")),
        "symbol": _normalized_str(state.get("symbol")),
        "exchangeCode": _normalized_str(state.get("exchange"), "binance"),
        "mode": _normalized_str(state.get("mode"), "paper"),
        "action": action,
        "side": _normalized_str(supervisor_decision.get("side"), "flat"),
        "confidence": _normalized_int(supervisor_decision.get("confidence"), 0),
        "modelCode": _normalized_str(supervisor_decision.get("model_code")),
        "modelProvider": _normalized_str(supervisor_decision.get("model_provider")),
        "promptSource": _normalized_str(supervisor_prompt_metadata.get("prompt_source")),
        "bindingTemplateCode": _normalized_str(supervisor_prompt_metadata.get("binding_template_code")),
        "fallbackTemplateCode": _normalized_str(supervisor_prompt_metadata.get("fallback_template_code")),
        "resolvedTemplateCode": _normalized_str(supervisor_prompt_metadata.get("resolved_template_code")),
        "promptTemplateFallbackUsed": bool(supervisor_prompt_metadata.get("prompt_template_fallback_used")),
        "summaryReason": _normalized_str(supervisor_decision.get("summary_reason")),
        "eventStrength": _normalized_str(state.get("event_strength")),
        "triggerReason": _normalized_str(state.get("trigger_reason")),
        "triggerSource": _normalized_str(state.get("trigger_source")),
        "dispatchMode": dispatch_mode,
        "selectedAgentsJson": _json_compact(selected_agents, []),
        "combinationMatchJson": _json_compact(combination_match, {}),
        "activeSignalRefsJson": _json_compact(active_signal_refs, []),
        "cooldownBlocked": bool(state.get("cooldown_blocked")),
        "budgetBlocked": bool(state.get("budget_blocked")),
        "selectedAgents": selected_agents,
        "combinationMatch": combination_match,
        "activeSignalRefs": active_signal_refs,
        "activeSignals": active_signals,
        "ruleOnlyReason": _normalized_str(state.get("rule_only_reason")),
        "suppressionReasonCodes": suppression_reason_codes,
        "triggerStrengthSource": _normalized_str(state.get("trigger_strength_source")),
        "featureSnapshot": state.get("feature_snapshot") if isinstance(state.get("feature_snapshot"), dict) else {},
        "executionStatus": execution_status,
        "orderStatus": order_status,
        "decisionActions": _build_decision_actions_payload(state, execution_status, order_status),
        "signalEvents": _build_signal_events_payload(state),
        "signalWindowStates": _build_signal_window_states_payload(state),
        "agentRuns": _build_agent_runs_payload(state),
        "agentObservations": _build_agent_observations_payload(state),
        "agentConclusions": _build_agent_conclusions_payload(state),
        "agentMessages": _build_agent_messages_payload(state),
        "marketSourceConfig": state.get("market_source_context") if isinstance(state.get("market_source_context"), dict) else {},
        "shortTermMemory": state.get("short_term_memory") if isinstance(state.get("short_term_memory"), dict) else {},
        "longTermMemory": state.get("long_term_memory") if isinstance(state.get("long_term_memory"), dict) else {},
        "memoryUsage": state.get("memory_usage") if isinstance(state.get("memory_usage"), dict) else {},
        "tradeMemoryStatus": state.get("trade_memory_status") if isinstance(state.get("trade_memory_status"), dict) else {},
        "lifecycleStatus": state.get("lifecycle_status") if isinstance(state.get("lifecycle_status"), dict) else {},
    }


def _build_decision_actions_payload(state: DecisionState, execution_status: str, order_status: str) -> list[dict]:
    supervisor_decision = state.get("supervisor_decision")
    if not isinstance(supervisor_decision, dict):
        supervisor_decision = {}
    action = _resolve_audit_action(supervisor_decision, execution_status)
    return [
        {
            "traceId": _normalized_str(state.get("trace_id")),
            "action": action,
            "side": _normalized_str(supervisor_decision.get("side"), "flat"),
            "orderRef": _normalized_str((state.get("execution_result") or {}).get("order_id")),
            "executionStatus": execution_status,
            "orderStatus": order_status,
        }
    ]


def _resolve_audit_action(supervisor_decision: dict, execution_status: str) -> str:
    action = _normalized_str((supervisor_decision or {}).get("action"))
    if action:
        return action
    if execution_status == "blocked":
        return "NO_ACTION"
    return "SKIP"


def _build_shadow_decision_log_payload(state: DecisionState) -> dict:
    decision_payload = _build_decision_payload(state)
    return {
        "traceId": decision_payload.get("traceId", ""),
        "exchangeCode": decision_payload.get("exchangeCode", "binance"),
        "symbol": decision_payload.get("symbol", ""),
        "mode": decision_payload.get("mode", "shadow"),
        "action": decision_payload.get("action", "SKIP"),
        "side": decision_payload.get("side", "flat"),
        "confidence": decision_payload.get("confidence", 0),
        "modelCode": decision_payload.get("modelCode", ""),
        "modelProvider": decision_payload.get("modelProvider", ""),
        "promptSource": decision_payload.get("promptSource", ""),
        "bindingTemplateCode": decision_payload.get("bindingTemplateCode", ""),
        "fallbackTemplateCode": decision_payload.get("fallbackTemplateCode", ""),
        "resolvedTemplateCode": decision_payload.get("resolvedTemplateCode", ""),
        "promptTemplateFallbackUsed": decision_payload.get("promptTemplateFallbackUsed", False),
        "summaryReason": decision_payload.get("summaryReason", ""),
        "executionStatus": decision_payload.get("executionStatus", "pending"),
        "orderStatus": decision_payload.get("orderStatus", "PENDING"),
    }


def _build_pnl_snapshot_payload(state: DecisionState) -> dict | None:
    execution_result = state.get("execution_result") or {}
    if "account_equity" not in execution_result:
        return None
    return {
        "traceId": state.get("trace_id", ""),
        "mode": state.get("mode", "paper"),
        "accountEquity": execution_result.get("account_equity", 0),
        "unrealizedPnl": execution_result.get("unrealized_pnl", 0),
        "realizedPnl": execution_result.get("realized_pnl", 0),
        "dailyPnl": execution_result.get("daily_pnl", 0),
        "maxDrawdownPct": execution_result.get("max_drawdown_pct", 0),
        "peakAccountEquity": execution_result.get(
            "peak_account_equity",
            state.get("peak_account_equity", execution_result.get("account_equity", 0)),
        ),
    }


def audit_node(state: DecisionState) -> DecisionState:
    dispatch_mode = derive_dispatch_mode(state)
    suppression_reason_codes = build_suppression_reason_codes(state)
    state["audit_payload"] = {
        "trace_id": state.get("trace_id", ""),
        "symbol": state.get("symbol", ""),
        "mode": state.get("mode", "paper"),
        "event_strength": state.get("event_strength", "noise"),
        "trigger_reason": state.get("trigger_reason", ""),
        "trigger_source": state.get("trigger_source", ""),
        "dispatch_mode": dispatch_mode,
        "selected_agents": normalize_selected_agents(state.get("selected_agents")),
        "active_signals": _normalized_list(state.get("active_signals")),
        "combination_match": _normalized_dict(state.get("combination_match")),
        "active_signal_refs": _normalized_list(state.get("active_signal_refs")),
        "cooldown_blocked": bool(state.get("cooldown_blocked")),
        "budget_blocked": bool(state.get("budget_blocked")),
        "rule_only_reason": state.get("rule_only_reason", ""),
        "suppression_reason_codes": suppression_reason_codes,
        "decision": state.get("supervisor_decision", {}),
    }
    callback_client = state.get("callback_client")
    if callback_client is not None:
        callback_client.post_decision_audit(_build_decision_payload(state))
        if state.get("mode") == "shadow" and hasattr(callback_client, "post_shadow_decision_log"):
            callback_client.post_shadow_decision_log(_build_shadow_decision_log_payload(state))
        pnl_snapshot_payload = _build_pnl_snapshot_payload(state)
        if pnl_snapshot_payload is not None and hasattr(callback_client, "post_pnl_snapshot"):
            state["pnl_snapshot_payload"] = pnl_snapshot_payload
            callback_client.post_pnl_snapshot(pnl_snapshot_payload)
    return state

