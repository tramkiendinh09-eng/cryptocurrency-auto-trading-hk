"""
链上Agent节点模块

实现链上数据的分析和决策生成，负责处理链上事件并生成链上观点。
核心功能：
1. 检查链上数据收集是否启用
2. 分析交易所流入流出
3. 根据净流量生成规则决策
4. 可选调用LLM进行深度分析
"""

from trade_runtime.decision.models import AgentView
from trade_runtime.decision.agent_profile_resolver import resolve_agent_mode
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


def _onchain_collection_enabled(state: DecisionState) -> bool:
    """检查链上数据收集是否启用

    Args:
        state: 决策状态

    Returns:
        bool: 链上数据收集是否启用
    """
    strategy_context = state.get("strategy_context") or {}
    if not isinstance(strategy_context, dict):
        return True
    market_data_config = strategy_context.get("market_data_config") or {}
    if isinstance(market_data_config, dict) and not _is_enabled_flag(market_data_config.get("collect_onchain"), default=True):
        return False
    onchain_api_config = strategy_context.get("onchain_api_config") or {}
    if isinstance(onchain_api_config, dict) and not _is_enabled_flag(onchain_api_config.get("enabled"), default=True):
        return False
    return True


def _build_onchain_rule_view(state: DecisionState) -> dict:
    """构建链上规则观点

    Args:
        state: 决策状态

    Returns:
        dict: 链上观点字典
    """
    if not _onchain_collection_enabled(state):
        return AgentView(
            bias="neutral",
            confidence=50,
            reason="onchain_collection_disabled",
            ttl=900,
            risk_note="source_disabled",
        ).model_dump()
    onchain_events = [event for event in state.get("event_bundle", []) if event.get("event_type") == "onchain"]
    if onchain_events:
        inflow = sum(float(event.get("amountUsd", 0) or 0) for event in onchain_events if event.get("flow") == "exchange_inflow")
        outflow = sum(float(event.get("amountUsd", 0) or 0) for event in onchain_events if event.get("flow") == "exchange_outflow")
        net_flow = outflow - inflow
        if net_flow < 0:
            bias = "bearish"
            flow = "net_inflow"
        elif net_flow > 0:
            bias = "bullish"
            flow = "net_outflow"
        else:
            bias = "neutral"
            flow = "balanced"
        amount_usd = max(inflow, outflow)
        confidence = 75 if amount_usd >= 1_000_000 else 60
        if len(onchain_events) == 1:
            flow = str(onchain_events[0].get("flow") or flow)
        reason = f"{flow}; events={len(onchain_events)}; gross_usd={amount_usd:.0f}; net_usd={net_flow:.0f}"
    else:
        bias = "neutral"
        confidence = 50
        reason = "no_onchain_signal"
    return AgentView(
        bias=bias,
        confidence=confidence,
        reason=reason,
        ttl=900,
        risk_note="normal",
    ).model_dump()


def onchain_agent(state: DecisionState) -> DecisionState:
    """链上Agent节点

    分析链上数据并生成链上观点。

    流程：
    1. 构建规则观点
    2. 判断是否需要LLM调用
    3. 可选调用LLM进行深度分析
    4. 更新状态中的onchain_view

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含onchain_view
    """
    rule_view = _build_onchain_rule_view(state)
    if resolve_agent_mode(state.get("agent_profiles"), "onchain_agent", state=state) != "RULE":
        llm_view = run_llm_agent(
            state,
            agent_code="onchain_agent",
            binding_scope="ONCHAIN_AGENT",
            rule_view=rule_view,
        )
        if llm_view is not None:
            state["onchain_view"] = llm_view
            return state
    state["onchain_view"] = rule_view
    return state
