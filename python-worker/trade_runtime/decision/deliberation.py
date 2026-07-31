from __future__ import annotations

import json
from typing import Any

from trade_runtime.decision.agent_profile_resolver import resolve_agent_execution_config, resolve_agent_profile
from trade_runtime.decision.dispatch import is_specialist_active
from trade_runtime.decision.llm_agent_runner import record_llm_error
from trade_runtime.decision.models import SupervisorDecision
from trade_runtime.decision.nodes.supervisor_agent import (
    _clamp_size_hint,
    _normalize_holding_window,
    _normalize_invalidation,
    _normalize_model_decision_payload,
)
from trade_runtime.decision.output_parsers import parse_json_object_content
from trade_runtime.prompting.prompt_template_registry import resolve_prompt_template_registry
from trade_runtime.prompting.render_context_builder import build_supervisor_render_context
from trade_runtime.prompting.renderers import render_template


VIEW_BY_AGENT = {
    "market_agent": "market_view",
    "news_agent": "news_view",
    "onchain_agent": "onchain_view",
    "social_agent": "social_view",
}
REFEREE_AGENT_CODE = "deliberation_referee"
REFEREE_BINDING_SCOPE = "DELIBERATION_REFEREE"


def _message_metadata(view: dict[str, Any] | None) -> tuple[str, str]:
    if not isinstance(view, dict):
        return "", ""
    return (
        str(view.get("template_code") or "").strip(),
        str(view.get("model_code") or "").strip(),
    )


def _is_enabled_flag(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def _resolve_deliberation_policy(state: dict[str, Any]) -> dict[str, Any]:
    policy = state.get("deliberation_policy")
    if isinstance(policy, dict) and policy:
        return policy
    runtime_config = state.get("runtime_config")
    if not isinstance(runtime_config, dict):
        return {}
    return {
        "enabled": runtime_config.get("deliberation_enabled"),
        "maxRounds": runtime_config.get("deliberation_max_rounds"),
        "failOpen": runtime_config.get("deliberation_fail_open"),
    }


def _deliberation_fail_open(state: dict[str, Any]) -> bool:
    policy = _resolve_deliberation_policy(state)
    return _is_enabled_flag(policy.get("failOpen", policy.get("fail_open")), default=True)


def _sorted_dialogue_profiles(state: dict[str, Any]) -> list[dict[str, Any]]:
    agent_profiles = state.get("agent_profiles")
    if not isinstance(agent_profiles, list):
        return []
    profiles: list[dict[str, Any]] = []
    for profile in agent_profiles:
        if not isinstance(profile, dict):
            continue
        if not _is_enabled_flag(profile.get("enabled"), default=True):
            continue
        if not _is_enabled_flag(profile.get("dialogue_enabled"), default=False):
            continue
        if str(profile.get("agent_code") or "").strip().lower() not in VIEW_BY_AGENT:
            continue
        profiles.append(profile)
    profiles.sort(key=lambda item: int(item.get("speak_order") or 0))
    return profiles


def _collect_speakers(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    speakers: list[tuple[str, dict[str, Any]]] = []
    for profile in _sorted_dialogue_profiles(state):
        agent_code = str(profile.get("agent_code") or "").strip().lower()
        if not is_specialist_active(state, agent_code):
            continue
        view = state.get(VIEW_BY_AGENT.get(agent_code, ""))
        if isinstance(view, dict) and view:
            speakers.append((agent_code, view))
    return speakers


def _has_conflicting_biases(speakers: list[tuple[str, dict[str, Any]]]) -> bool:
    return _find_conflicting_speaker_pair(speakers) is not None


def _find_conflicting_speaker_pair(
    speakers: list[tuple[str, dict[str, Any]]]
) -> tuple[tuple[str, dict[str, Any]], tuple[str, dict[str, Any]]] | None:
    directional_biases = {"bullish", "bearish"}
    for target_index, target in enumerate(speakers):
        target_bias = str(target[1].get("bias") or "").strip().lower()
        if target_bias not in directional_biases:
            continue
        for challenger in speakers[target_index + 1 :]:
            challenger_bias = str(challenger[1].get("bias") or "").strip().lower()
            if {target_bias, challenger_bias} == directional_biases:
                return challenger, target
    return None


def should_run_deliberation(state: dict[str, Any]) -> bool:
    """判断是否应该运行审议流程

    修改：只要有足够的Agent观点（>=2个），就运行审议流程
    即使观点一致，也让裁判Agent进行复核确认，确保决策的合理性

    Args:
        state: 决策状态

    Returns:
        bool: 是否应该运行审议
    """
    policy = _resolve_deliberation_policy(state)
    if not _is_enabled_flag(policy.get("enabled"), default=False):
        return False
    try:
        max_rounds = int(policy.get("maxRounds") or policy.get("max_rounds") or 0)
    except (TypeError, ValueError):
        max_rounds = 0
    if max_rounds < 1:
        return False

    speakers = _collect_speakers(state)
    # 修改：只要有2个以上Agent发言，就运行审议
    # 即使观点一致，裁判Agent也可以确认决策的合理性
    return len(speakers) >= 2


def _json_compact(value: object, fallback: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError):
        return json.dumps(fallback, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _referee_profile_enabled(state: dict[str, Any]) -> bool:
    profile = resolve_agent_profile(state.get("agent_profiles"), REFEREE_AGENT_CODE)
    if not isinstance(profile, dict):
        return False
    if not _is_enabled_flag(profile.get("llm_enabled"), default=True):
        return False
    return _is_enabled_flag(profile.get("dialogue_enabled"), default=False)


def _build_referee_render_context(state: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
    context = build_supervisor_render_context(state)
    context["agent_messages_json"] = _json_compact(messages, [])
    context["deliberation_summary"] = str(state.get("deliberation_summary") or "").strip()
    context["deliberation_policy_json"] = _json_compact(_resolve_deliberation_policy(state), {})
    return context


def _fallback_referee_prompt(state: dict[str, Any], messages: list[dict[str, Any]]) -> str:
    payload = {
        "symbol": state.get("symbol"),
        "exchange": state.get("exchange"),
        "mode": state.get("mode"),
        "event_strength": state.get("event_strength"),
        "views": {
            "market_view": state.get("market_view") or {},
            "news_view": state.get("news_view") or {},
            "onchain_view": state.get("onchain_view") or {},
            "social_view": state.get("social_view") or {},
        },
        "agent_messages": messages,
        "deliberation_summary": state.get("deliberation_summary") or "",
    }
    return (
        "You are the deliberation referee. Review the specialist transcript and return JSON only with keys "
        "action, side, confidence, size_hint, leverage_hint, holding_window, invalidation, summary_reason. "
        "Allowed action values only: OPEN_LONG, OPEN_SHORT, ADD_LONG, ADD_SHORT, REDUCE, CLOSE, HOLD, SKIP.\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def _build_referee_prompt(state: dict[str, Any], messages: list[dict[str, Any]], agent_config: dict[str, Any]) -> str:
    prompt = ""
    template_code = str(agent_config.get("template_code") or "").strip()
    registry = resolve_prompt_template_registry(state)
    if template_code and registry is not None:
        prompt = render_template(registry.get_template(template_code), _build_referee_render_context(state, messages))
    if not prompt:
        prompt = _fallback_referee_prompt(state, messages)
    transcript_block = (
        "\n\nDeliberation transcript JSON:\n"
        f"{_json_compact(messages, [])}\n"
        "Deliberation summary:\n"
        f"{str(state.get('deliberation_summary') or '').strip()}"
    )
    if "Deliberation transcript JSON" not in prompt:
        prompt = f"{prompt}{transcript_block}"
    return prompt


def _parse_referee_decision(
    state: dict[str, Any],
    response: dict[str, Any],
    agent_config: dict[str, Any],
) -> dict[str, Any] | None:
    payload = parse_json_object_content(str(response.get("content") or ""))
    if payload is None:
        return None
    try:
        payload = _normalize_model_decision_payload(state, payload)
        normalized_action = str(payload.get("action") or "").strip().upper()
        decision = SupervisorDecision(
            action=normalized_action,
            side=str(payload.get("side") or "").strip(),
            confidence=int(payload.get("confidence", 0)),
            size_hint=float(payload.get("size_hint", 0.0)),
            leverage_hint=int(payload.get("leverage_hint", 3)),
            holding_window=_normalize_holding_window(payload.get("holding_window")),
            invalidation=_normalize_invalidation(payload.get("invalidation"), action=normalized_action),
            summary_reason=str(payload.get("summary_reason") or "").strip(),
            model_code=str(response.get("modelCode") or agent_config.get("model_code") or "").strip(),
            model_provider=str(response.get("modelProvider") or agent_config.get("model_provider") or "").strip(),
        )
    except Exception:
        return None
    return _clamp_size_hint(state, decision.model_dump())


def _fail_closed_referee_decision() -> dict[str, Any]:
    return SupervisorDecision(
        action="SKIP",
        side="flat",
        confidence=0,
        size_hint=0.0,
        leverage_hint=1,
        holding_window="15m-4h",
        invalidation="deliberation_referee_failed",
        summary_reason="deliberation_referee_failed_fail_closed",
    ).model_dump()


def _record_referee_failure(
    state: dict[str, Any],
    *,
    model_id: object = None,
    template_code: str = "",
    error: object,
    raw_response_snippet: object = None,
) -> None:
    state["deliberation_referee_error"] = str(error or "").strip()
    if _deliberation_fail_open(state):
        errors = state.setdefault("agent_llm_errors", [])
        if not isinstance(errors, list):
            errors = []
            state["agent_llm_errors"] = errors
        payload = {
            "agent_code": REFEREE_AGENT_CODE,
            "model_id": model_id,
            "template_code": str(template_code or "").strip(),
            "error": str(error or "").strip(),
        }
        if raw_response_snippet not in (None, ""):
            payload["raw_response_snippet"] = str(raw_response_snippet)[:500]
        errors.append(payload)
        return
    record_llm_error(
        state,
        agent_code=REFEREE_AGENT_CODE,
        model_id=model_id,
        template_code=template_code,
        error=error,
        raw_response_snippet=raw_response_snippet,
    )
    state["deliberation_referee_review"] = _fail_closed_referee_decision()


def _append_referee_message(
    state: dict[str, Any],
    messages: list[dict[str, Any]],
    decision: dict[str, Any],
    agent_config: dict[str, Any],
) -> None:
    max_round = max((int(message.get("round_no") or 0) for message in messages if isinstance(message, dict)), default=0)
    messages.append(
        {
            "round_no": max_round + 1,
            "speaker_agent": REFEREE_AGENT_CODE,
            "target_agent": "supervisor_agent",
            "message_type": "referee_review",
            "template_code": str(agent_config.get("template_code") or "").strip(),
            "model_code": str(decision.get("model_code") or agent_config.get("model_code") or "").strip(),
            "content": dict(decision),
            "summary_text": str(decision.get("summary_reason") or "").strip(),
        }
    )
    state["agent_messages"] = messages


def _run_referee(state: dict[str, Any], messages: list[dict[str, Any]]) -> None:
    if not _referee_profile_enabled(state):
        return
    agent_config = resolve_agent_execution_config(state, REFEREE_AGENT_CODE, binding_scope=REFEREE_BINDING_SCOPE)
    if not isinstance(agent_config, dict):
        return
    model_id = agent_config.get("model_id")
    template_code = str(agent_config.get("template_code") or "").strip()
    decision_model_client = state.get("decision_model_client")
    if decision_model_client is None or model_id is None:
        _record_referee_failure(
            state,
            model_id=model_id,
            template_code=template_code,
            error="deliberation_referee_model_unavailable",
        )
        return
    prompt = _build_referee_prompt(state, messages, agent_config)
    state["deliberation_referee_prompt_metadata"] = {
        "agent_code": REFEREE_AGENT_CODE,
        "model_id": model_id,
        "template_code": template_code,
    }
    try:
        response = decision_model_client.call_model(model_id=model_id, prompt=prompt)
    except Exception as exc:
        _record_referee_failure(
            state,
            model_id=model_id,
            template_code=template_code,
            error=exc,
        )
        return
    if not isinstance(response, dict):
        _record_referee_failure(
            state,
            model_id=model_id,
            template_code=template_code,
            error="invalid_referee_model_response",
        )
        return
    decision = _parse_referee_decision(state, response, agent_config)
    if decision is None:
        _record_referee_failure(
            state,
            model_id=model_id,
            template_code=template_code,
            error="invalid_referee_decision_content",
            raw_response_snippet=response.get("content"),
        )
        return
    state["deliberation_referee_review"] = decision
    _append_referee_message(state, messages, decision, agent_config)


def run_deliberation(state: dict[str, Any]) -> dict[str, Any]:
    speakers = _collect_speakers(state)
    if len(speakers) < 2:
        state["agent_messages"] = []
        state["deliberation_summary"] = ""
        return state

    messages: list[dict[str, Any]] = []
    for agent_code, view in speakers:
        template_code, model_code = _message_metadata(view)
        messages.append(
            {
                "round_no": 0,
                "speaker_agent": agent_code,
                "target_agent": "",
                "message_type": "proposal",
                "template_code": template_code,
                "model_code": model_code,
                "content": {
                    "bias": view.get("bias"),
                    "confidence": view.get("confidence"),
                    "risk_note": view.get("risk_note"),
                    "reason": view.get("reason"),
                },
                "summary_text": str(view.get("reason") or "").strip(),
            }
        )

    conflict_pair = _find_conflicting_speaker_pair(speakers)
    if conflict_pair is not None:
        (challenger_agent, challenger_view), (target_agent, target_view) = conflict_pair
        challenger_template_code, challenger_model_code = _message_metadata(challenger_view)
        messages.append(
            {
                "round_no": 1,
                "speaker_agent": challenger_agent,
                "target_agent": target_agent,
                "message_type": "challenge",
                "template_code": challenger_template_code,
                "model_code": challenger_model_code,
                "content": {
                    "challenger_bias": challenger_view.get("bias"),
                    "target_bias": target_view.get("bias"),
                    "challenger_reason": challenger_view.get("reason"),
                    "target_reason": target_view.get("reason"),
                },
                "summary_text": f"{challenger_agent} challenges {target_agent}",
            }
        )
        for agent_code, view in speakers:
            template_code, model_code = _message_metadata(view)
            messages.append(
                {
                    "round_no": 1,
                    "speaker_agent": agent_code,
                    "target_agent": challenger_agent if agent_code != challenger_agent else target_agent,
                    "message_type": "revision",
                    "template_code": template_code,
                    "model_code": model_code,
                    "content": {
                        "stance": "maintain",
                        "bias": view.get("bias"),
                        "confidence": view.get("confidence"),
                        "reason": view.get("reason"),
                    },
                    "summary_text": f"{agent_code} maintains {view.get('bias')}",
                }
            )
        summary_text = "conflicting_specialist_views_detected"
        messages.append(
            {
                "round_no": 1,
                "speaker_agent": "orchestrator",
                "target_agent": "",
                "message_type": "summary",
                "template_code": "",
                "model_code": "",
                "content": {
                    "participants": [agent_code for agent_code, _ in speakers],
                    "conflict": True,
                },
                "summary_text": summary_text,
            }
        )
        state["deliberation_summary"] = summary_text
    else:
        # 无冲突：构建一致性确认消息
        all_biases = [str(view.get("bias") or "").strip().lower() for _, view in speakers]
        consistent_bias = all_biases[0] if all_biases else "neutral"

        messages.append(
            {
                "round_no": 1,
                "speaker_agent": "orchestrator",
                "target_agent": "",
                "message_type": "consensus",
                "template_code": "",
                "model_code": "",
                "content": {
                    "participants": [agent_code for agent_code, _ in speakers],
                    "consensus_bias": consistent_bias,
                    "conflict": False,
                },
                "summary_text": f"all_specialists_agree_on_{consistent_bias}",
            }
        )
        state["deliberation_summary"] = f"consensus_{consistent_bias}"

    state["agent_messages"] = messages
    _run_referee(state, messages)
    return state
