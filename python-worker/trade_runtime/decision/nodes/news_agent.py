"""
新闻Agent节点模块

实现新闻数据的分析和决策生成，负责处理新闻事件并生成新闻观点。
核心功能：
1. 检查新闻API是否启用
2. 分析新闻事件情感分数
3. 根据新闻强度生成规则决策
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


def _news_api_enabled(state: DecisionState) -> bool:
    """检查新闻API是否启用

    Args:
        state: 决策状态

    Returns:
        bool: 新闻API是否启用
    """
    strategy_context = state.get("strategy_context") or {}
    if not isinstance(strategy_context, dict):
        return True
    news_api_config = strategy_context.get("news_api_config") or {}
    if not isinstance(news_api_config, dict):
        return True
    return _is_enabled_flag(news_api_config.get("enabled"), default=True)


def _build_news_rule_view(state: DecisionState) -> dict:
    """构建新闻规则观点

    Args:
        state: 决策状态

    Returns:
        dict: 新闻观点字典
    """
    if not _news_api_enabled(state):
        return AgentView(
            bias="neutral",
            confidence=50,
            reason="news_api_disabled",
            ttl=900,
            risk_note="source_disabled",
        ).model_dump()
    news_events = [event for event in state.get("event_bundle", []) if event.get("event_type") == "news"]
    if news_events:
        strongest = max(news_events, key=lambda event: abs(float(event.get("score", 0) or 0)))
        score = float(strongest.get("score", 0) or 0)
        if score > 0:
            bias = "bullish"
        elif score < 0:
            bias = "bearish"
        else:
            bias = "neutral"
        confidence = min(95, max(50, int(abs(score) * 100)))
        reason = f"{len(news_events)} news events; strongest={strongest.get('headline', 'news_signal')}"
    else:
        bias = "neutral"
        confidence = 50
        reason = "no_news_signal"
    return AgentView(
        bias=bias,
        confidence=confidence,
        reason=reason,
        ttl=900,
        risk_note="normal",
    ).model_dump()


def _mark_llm_fallback_status(state: DecisionState, agent_code: str, view: dict) -> dict:
    """标记LLM回退状态

    Args:
        state: 决策状态
        agent_code: Agent编码
        view: 观点字典

    Returns:
        dict: 标记后的观点字典
    """
    errors = state.get("agent_llm_errors") or []
    if not isinstance(errors, list):
        return view
    has_agent_error = any(
        isinstance(item, dict) and str(item.get("agent_code") or "").strip() == agent_code
        for item in errors
    )
    if not has_agent_error:
        return view
    normalized = dict(view)
    normalized["llm_status"] = "failed_fallback_rule"
    return normalized


def news_agent(state: DecisionState) -> DecisionState:
    """新闻Agent节点

    分析新闻数据并生成新闻观点。

    流程：
    1. 构建规则观点
    2. 判断是否需要LLM调用
    3. 可选调用LLM进行深度分析
    4. 更新状态中的news_view

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含news_view
    """
    rule_view = _build_news_rule_view(state)
    if resolve_agent_mode(state.get("agent_profiles"), "news_agent", state=state) != "RULE":
        llm_view = run_llm_agent(
            state,
            agent_code="news_agent",
            binding_scope="NEWS_AGENT",
            rule_view=rule_view,
        )
        if llm_view is not None:
            state["news_view"] = llm_view
            return state
    state["news_view"] = _mark_llm_fallback_status(state, "news_agent", rule_view)
    return state
