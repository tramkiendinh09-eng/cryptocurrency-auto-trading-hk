from __future__ import annotations

from typing import Any

from trade_runtime.decision.dispatch import SPECIALIST_AGENT_CODES, is_specialist_selected, llm_dispatch_allowed
from trade_runtime.prompting.prompt_binding_resolver import resolve_prompt_binding


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


def resolve_agent_profile(agent_profiles: list[dict[str, Any]] | None, agent_code: str) -> dict[str, Any] | None:
    if not isinstance(agent_profiles, list):
        return None
    normalized_agent_code = str(agent_code or "").strip().lower()
    for profile in agent_profiles:
        if not isinstance(profile, dict):
            continue
        if str(profile.get("agent_code") or "").strip().lower() != normalized_agent_code:
            continue
        if not _is_enabled_flag(profile.get("enabled"), default=True):
            return None
        return profile
    return None


def resolve_agent_config(state: dict[str, Any] | None, agent_code: str) -> dict[str, Any] | None:
    if not isinstance(state, dict):
        return None
    normalized_agent_code = str(agent_code or "").strip().lower()
    resolved_agent_configs = state.get("resolved_agent_configs")
    if not isinstance(resolved_agent_configs, list):
        strategy_context = state.get("strategy_context")
        if isinstance(strategy_context, dict):
            resolved_agent_configs = strategy_context.get("resolved_agent_configs")
    if not isinstance(resolved_agent_configs, list):
        return None
    for config in resolved_agent_configs:
        if not isinstance(config, dict):
            continue
        if str(config.get("agent_code") or "").strip().lower() != normalized_agent_code:
            continue
        if not _is_enabled_flag(config.get("enabled"), default=True):
            return None
        return config
    return None



def _strategy_ai_model_config(state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    strategy_context = state.get("strategy_context") or {}
    if not isinstance(strategy_context, dict):
        return {}
    ai_model_config = strategy_context.get("ai_model_config") or {}
    return ai_model_config if isinstance(ai_model_config, dict) else {}


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_agent_execution_config(
    state: dict[str, Any] | None,
    agent_code: str,
    *,
    binding_scope: str,
) -> dict[str, Any] | None:
    if not isinstance(state, dict):
        return None
    resolved_config = resolve_agent_config(state, agent_code)
    if isinstance(resolved_config, dict):
        config = dict(resolved_config)
        config["model_id"] = _int_or_none(config.get("model_id"))
        config.setdefault("resolution_source", "AGENT_PROFILE")
        return config

    prompt_binding = resolve_prompt_binding(
        state.get("prompt_bindings"),
        binding_scope=binding_scope,
        mode=str(state.get("mode") or "").strip(),
        event_strength=str(state.get("event_strength") or "").strip(),
    )
    ai_model_config = _strategy_ai_model_config(state)
    if not isinstance(prompt_binding, dict) and not ai_model_config:
        return None

    config = dict(prompt_binding or {})
    model_id = _int_or_none(config.get("model_id")) or _int_or_none(ai_model_config.get("id"))
    config.update(
        {
            "agent_code": agent_code,
            "binding_scope": binding_scope,
            "model_id": model_id,
            "model_code": str(config.get("model_code") or ai_model_config.get("model_code") or "").strip(),
            "model_provider": str(config.get("model_provider") or ai_model_config.get("provider") or "").strip(),
            "resolution_source": "LEGACY_PROMPT_BINDING" if isinstance(prompt_binding, dict) else "LEGACY_AI_MODEL_CONFIG",
            "enabled": True,
        }
    )
    return config

def resolve_agent_mode(
    agent_profiles: list[dict[str, Any]] | None,
    agent_code: str,
    *,
    state: dict[str, Any] | None = None,
) -> str:
    normalized_agent_code = str(agent_code or "").strip().lower()
    if normalized_agent_code in SPECIALIST_AGENT_CODES:
        if not llm_dispatch_allowed(state):
            return "RULE"
        if not is_specialist_selected(state, normalized_agent_code):
            return "RULE"
    profile = resolve_agent_profile(agent_profiles, agent_code)
    if not isinstance(profile, dict):
        return "RULE"
    if not _is_enabled_flag(profile.get("llm_enabled"), default=True):
        return "RULE"
    normalized_type = str(profile.get("agent_type") or "RULE").strip().upper()
    if normalized_type in {"LLM", "HYBRID"}:
        return normalized_type
    return "RULE"
