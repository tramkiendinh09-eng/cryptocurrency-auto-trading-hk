"""
社交Agent节点模块

实现社交数据的分析和决策生成，负责处理社交事件并生成社交观点。
核心功能：
1. 检查社交API是否启用
2. 分析社交信号分数
3. 根据社交情绪生成规则决策
4. 可选调用LLM进行深度分析
"""

from trade_runtime.decision.models import AgentView
from trade_runtime.decision.agent_profile_resolver import resolve_agent_mode
from trade_runtime.decision.dispatch import is_specialist_active
from trade_runtime.decision.llm_agent_runner import run_llm_agent
from trade_runtime.decision.state import DecisionState


def _is_enabled_flag(value: object, default: bool = True) -> bool:
    """检查是否为启用标志

    Args:
        value: 标志值
        default: 默认值

    Returns:
        bool: 是否启用
    """
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


def _social_api_enabled(state: DecisionState) -> bool:
    """检查社交API是否启用

    Args:
        state: 决策状态

    Returns:
        bool: 社交API是否启用
    """
    strategy_context = state.get("strategy_context") or {}
    if not isinstance(strategy_context, dict):
        return True
    social_api_config = strategy_context.get("social_api_config") or {}
    if not isinstance(social_api_config, dict):
        return True
    return _is_enabled_flag(social_api_config.get("enabled"), default=True)


def _build_social_rule_view(state: DecisionState) -> dict:
    """构建社交规则观点

    Args:
        state: 决策状态

    Returns:
        dict: 社交观点字典
    """
    if not _social_api_enabled(state):
        return AgentView(
            bias="neutral",
            confidence=50,
            reason="social_api_disabled",
            ttl=900,
            risk_note="source_disabled",
        ).model_dump()
    social_events = [event for event in state.get("event_bundle", []) if event.get("event_type") == "social"]
    if social_events:
        latest = social_events[-1]
        score = float(latest.get("score", 0))
        if score > 0:
            bias = "bullish"
        elif score < 0:
            bias = "bearish"
        else:
            bias = "neutral"
        confidence = min(90, max(50, int(abs(score) * 100)))
        reason = f"social_score={score}"
    else:
        bias = "neutral"
        confidence = 50
        reason = "no_social_signal"
    return AgentView(
        bias=bias,
        confidence=confidence,
        reason=reason,
        ttl=900,
        risk_note="normal",
    ).model_dump()


def social_agent(state: DecisionState) -> DecisionState:
    """社交Agent节点

    分析社交数据并生成社交观点。

    流程：
    1. 检查是否为活跃专家
    2. 构建规则观点
    3. 判断是否需要LLM调用
    4. 可选调用LLM进行深度分析
    5. 更新状态中的social_view

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含social_view
    """
    if not is_specialist_active(state, "social_agent"):
        state["social_view"] = AgentView(
            bias="neutral",
            confidence=50,
            reason="no_social_signal",
            ttl=900,
            risk_note="inactive_specialist",
        ).model_dump()
        return state
    rule_view = _build_social_rule_view(state)
    if rule_view.get("reason") == "social_api_disabled":
        state["social_view"] = rule_view
        return state
    if resolve_agent_mode(state.get("agent_profiles"), "social_agent", state=state) != "RULE":
        llm_view = run_llm_agent(
            state,
            agent_code="social_agent",
            binding_scope="SOCIAL_AGENT",
            rule_view=rule_view,
        )
        if llm_view is not None:
            state["social_view"] = llm_view
            return state
    state["social_view"] = rule_view
    return state