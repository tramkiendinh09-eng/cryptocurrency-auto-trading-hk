"""
分发模式模块

实现交易决策的分发逻辑，包括：
- 分发模式规范化（NO_DISPATCH/RULE_ONLY/LLM_ALLOWED）
- 专业Agent选择和启用状态解析
- 抑制原因代码构建
"""

from __future__ import annotations

from typing import Any


SPECIALIST_AGENT_CODES = (
    "market_agent",
    "news_agent",
    "onchain_agent",
    "social_agent",
)

_DISPATCH_MODES = {"NO_DISPATCH", "RULE_ONLY", "LLM_ALLOWED"}


def normalize_dispatch_mode(value: Any, default: str = "NO_DISPATCH") -> str:
    """规范化分发模式

    Args:
        value: 分发模式值
        default: 默认值

    Returns:
        str: 规范化后的分发模式
    """
    normalized = str(value or "").strip().upper()
    return normalized if normalized in _DISPATCH_MODES else default


def has_explicit_dispatch_mode(state: dict[str, Any] | None) -> bool:
    """检查是否有显式分发模式

    Args:
        state: 决策状态

    Returns:
        bool: 是否有显式分发模式
    """
    if not isinstance(state, dict):
        return False
    value = state.get("dispatch_mode")
    return value not in (None, "")


def derive_dispatch_mode(state: dict[str, Any] | None) -> str:
    """推导分发模式

    根据事件强度推导分发模式：
    - strong -> LLM_ALLOWED
    - normal -> RULE_ONLY
    - noise -> NO_DISPATCH

    Args:
        state: 决策状态

    Returns:
        str: 分发模式
    """
    if not isinstance(state, dict):
        return "NO_DISPATCH"
    if has_explicit_dispatch_mode(state):
        return normalize_dispatch_mode(state.get("dispatch_mode"))
    event_strength = str(state.get("event_strength") or "").strip().lower()
    if event_strength == "strong":
        return "LLM_ALLOWED"
    if event_strength == "normal":
        return "RULE_ONLY"
    return "NO_DISPATCH"


def llm_dispatch_allowed(state: dict[str, Any] | None) -> bool:
    """检查是否允许LLM分发

    Args:
        state: 决策状态

    Returns:
        bool: 是否允许LLM分发
    """
    if not isinstance(state, dict):
        return False
    if derive_dispatch_mode(state) != "LLM_ALLOWED":
        return False
    return not bool(state.get("cooldown_blocked")) and not bool(state.get("budget_blocked"))


def normalize_selected_agents(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        agent_code = str(item or "").strip().lower()
        if not agent_code or agent_code in normalized:
            continue
        normalized.append(agent_code)
    return normalized


def _is_enabled_flag(value: Any, default: bool = True) -> bool:
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


def resolve_enabled_specialists(agent_profiles: Any) -> list[str]:
    if not isinstance(agent_profiles, list):
        return list(SPECIALIST_AGENT_CODES)
    enabled: list[str] = []
    for profile in agent_profiles:
        if not isinstance(profile, dict):
            continue
        agent_code = str(profile.get("agent_code") or "").strip().lower()
        if agent_code not in SPECIALIST_AGENT_CODES:
            continue
        if not _is_enabled_flag(profile.get("enabled"), default=True):
            continue
        if agent_code not in enabled:
            enabled.append(agent_code)
    return enabled or list(SPECIALIST_AGENT_CODES)


def resolve_active_specialists(state: dict[str, Any] | None) -> list[str]:
    if not isinstance(state, dict):
        return list(SPECIALIST_AGENT_CODES)
    selected_agents = [
        agent_code
        for agent_code in normalize_selected_agents(state.get("selected_agents"))
        if agent_code in SPECIALIST_AGENT_CODES
    ]
    enabled_agents = set(resolve_enabled_specialists(state.get("agent_profiles")))
    base_agents = selected_agents or list(SPECIALIST_AGENT_CODES)
    return [agent_code for agent_code in base_agents if agent_code in enabled_agents]


def is_specialist_active(state: dict[str, Any] | None, agent_code: str) -> bool:
    normalized_agent_code = str(agent_code or "").strip().lower()
    if normalized_agent_code not in SPECIALIST_AGENT_CODES:
        return True
    return normalized_agent_code in resolve_active_specialists(state)


def is_specialist_selected(state: dict[str, Any] | None, agent_code: str) -> bool:
    selected_agents = normalize_selected_agents((state or {}).get("selected_agents"))
    if not selected_agents:
        return True
    return str(agent_code or "").strip().lower() in selected_agents


def build_suppression_reason_codes(state: dict[str, Any] | None) -> list[str]:
    if not isinstance(state, dict):
        return []
    normalized: list[str] = []
    for item in normalize_selected_agents(state.get("suppression_reason_codes")):
        normalized.append(item)
    if bool(state.get("cooldown_blocked")) and "cooldown_blocked" not in normalized:
        normalized.append("cooldown_blocked")
    if bool(state.get("budget_blocked")) and "budget_blocked" not in normalized:
        normalized.append("budget_blocked")
    rule_only_reason = str(state.get("rule_only_reason") or "").strip()
    if rule_only_reason and rule_only_reason not in normalized:
        normalized.append(rule_only_reason)
    return normalized
