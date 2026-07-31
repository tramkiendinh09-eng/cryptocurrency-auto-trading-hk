from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any

from trade_runtime.decision.dispatch import normalize_selected_agents
from trade_runtime.decision.models import AgentView
from trade_runtime.decision.state import DecisionState


_FIELD_TO_AGENT_CODE = {
    "market_view": "market_agent",
    "news_view": "news_agent",
    "onchain_view": "onchain_agent",
    "social_view": "social_agent",
}


def _fallback_view(reason: str) -> dict[str, Any]:
    return AgentView(
        bias="neutral",
        confidence=0,
        reason=reason,
        ttl=30,
        risk_note="degraded",
    ).model_dump()


def _normalize_positive_int(value: Any, default: int) -> int:
    try:
        normalized = int(value)
        return normalized if normalized > 0 else default
    except (TypeError, ValueError):
        return default


def _normalize_positive_float(value: Any, default: float) -> float:
    try:
        normalized = float(value)
        return normalized if normalized > 0 else default
    except (TypeError, ValueError):
        return default


def _resolve_parallel_config(state: DecisionState, runner_count: int) -> dict[str, Any]:
    runtime_config = state.get("runtime_config") or {}
    strategy_context = state.get("strategy_context") or {}
    strategy_config = strategy_context.get("strategy_config") or {} if isinstance(strategy_context, dict) else {}
    return {
        "max_concurrency": min(
            runner_count,
            _normalize_positive_int(
                strategy_config.get("agentMaxConcurrency")
                or strategy_config.get("agent_max_concurrency")
                or runtime_config.get("agent_max_concurrency"),
                runner_count,
            ),
        ),
        "timeout_seconds": _normalize_positive_float(
            strategy_config.get("agentTimeoutSeconds")
            or strategy_config.get("agent_timeout_seconds")
            or runtime_config.get("agent_timeout_seconds"),
            45.0,
        ),
        "circuit_breaker_threshold": _normalize_positive_int(
            strategy_config.get("agentCircuitBreakerThreshold")
            or strategy_config.get("agent_circuit_breaker_threshold")
            or runtime_config.get("agent_circuit_breaker_threshold"),
            2,
        ),
    }


def _run_specialist(field_name: str, runner, state: DecisionState) -> tuple[str, dict[str, Any], dict[str, Any]]:
    scoped_state = dict(state)
    result_state = runner(scoped_state)
    metadata: dict[str, Any] = {}
    if result_state.get("ai_call_failed"):
        metadata["ai_call_failed"] = True
    errors = result_state.get("agent_llm_errors")
    if isinstance(errors, list) and errors:
        metadata["agent_llm_errors"] = errors
    return field_name, result_state.get(field_name, {}), metadata


def _resolve_agent_timeout_seconds(state: DecisionState, field_name: str, default_timeout_seconds: float) -> float:
    agent_code = _FIELD_TO_AGENT_CODE.get(field_name)
    agent_profiles = state.get("agent_profiles")
    if not agent_code or not isinstance(agent_profiles, list):
        return default_timeout_seconds
    for profile in agent_profiles:
        if not isinstance(profile, dict):
            continue
        if str(profile.get("agent_code") or "").strip().lower() != agent_code:
            continue
        return _normalize_positive_float(profile.get("timeout_seconds"), default_timeout_seconds)
    return default_timeout_seconds


def run_parallel_specialists(
    state: DecisionState,
    specialist_runners: tuple[tuple[str, Any], ...],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    breaker_state = dict(state.get("agent_circuit_breaker") or {})
    config = _resolve_parallel_config(state, len(specialist_runners))
    selected_agents = normalize_selected_agents(state.get("selected_agents"))
    timeout_seconds = config["timeout_seconds"]
    circuit_breaker_threshold = config["circuit_breaker_threshold"]
    if breaker_state.get("circuit_open"):
        views = {field_name: _fallback_view("agent_circuit_open_fallback") for field_name, _ in specialist_runners}
        runtime = {
            "maxConcurrency": config["max_concurrency"],
            "timeoutSeconds": timeout_seconds,
            "completedAgents": [],
            "timedOutAgents": [],
            "failedAgents": [],
            "degradedAgents": list(views.keys()),
            "circuitOpen": True,
            "fallbackReason": "agent_circuit_open_fallback",
            "selectedAgents": selected_agents,
            "ruleOnlyAgents": [],
        }
        return views, runtime, breaker_state

    executor = ThreadPoolExecutor(max_workers=config["max_concurrency"])
    futures = {
        field_name: executor.submit(_run_specialist, field_name, runner, state)
        for field_name, runner in specialist_runners
    }
    views: dict[str, dict[str, Any]] = {}
    completed_agents: list[str] = []
    timed_out_agents: list[str] = []
    failed_agents: list[str] = []
    agent_llm_errors: list[dict[str, Any]] = []
    ai_call_failed = bool(state.get("ai_call_failed"))
    try:
        for field_name, future in futures.items():
            timeout_for_agent = _resolve_agent_timeout_seconds(state, field_name, timeout_seconds)
            try:
                _, view, metadata = future.result(timeout=timeout_for_agent)
            except TimeoutError:
                timed_out_agents.append(field_name)
                views[field_name] = _fallback_view("agent_timeout_fallback")
                future.cancel()
            except Exception:
                failed_agents.append(field_name)
                views[field_name] = _fallback_view("agent_error_fallback")
            else:
                completed_agents.append(field_name)
                views[field_name] = view or _fallback_view("agent_empty_fallback")
                if isinstance(metadata, dict):
                    ai_call_failed = ai_call_failed or bool(metadata.get("ai_call_failed"))
                    errors = metadata.get("agent_llm_errors")
                    if isinstance(errors, list):
                        agent_llm_errors.extend(item for item in errors if isinstance(item, dict))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    failure_count = len(timed_out_agents) + len(failed_agents)
    consecutive_failures = 0 if failure_count == 0 else int(breaker_state.get("consecutive_failures", 0) or 0) + failure_count
    circuit_open = failure_count > 0 and consecutive_failures >= circuit_breaker_threshold
    runtime = {
        "maxConcurrency": config["max_concurrency"],
        "timeoutSeconds": timeout_seconds,
        "completedAgents": completed_agents,
        "timedOutAgents": timed_out_agents,
        "failedAgents": failed_agents,
        "degradedAgents": timed_out_agents + failed_agents,
        "circuitOpen": circuit_open,
        "fallbackReason": "agent_timeout_fallback" if timed_out_agents else "agent_error_fallback" if failed_agents else "",
        "selectedAgents": selected_agents,
        "ruleOnlyAgents": [
            field_name
            for field_name, _ in specialist_runners
            if field_name.replace("_view", "_agent") not in selected_agents
        ] if selected_agents else [],
    }
    next_breaker_state = {
        "circuit_open": circuit_open,
        "consecutive_failures": consecutive_failures,
    }
    if ai_call_failed:
        runtime["aiCallFailed"] = True
        state["ai_call_failed"] = True
    if agent_llm_errors:
        existing_errors = state.setdefault("agent_llm_errors", [])
        if not isinstance(existing_errors, list):
            existing_errors = []
            state["agent_llm_errors"] = existing_errors
        existing_errors.extend(agent_llm_errors)
    return views, runtime, next_breaker_state
