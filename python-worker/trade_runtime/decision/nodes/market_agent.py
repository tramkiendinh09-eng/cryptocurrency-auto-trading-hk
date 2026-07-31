"""
市场Agent节点模块

实现市场数据的分析和决策生成，负责处理市场相关事件并生成市场观点。
核心功能：
1. 检测显著市场事件（爆仓、资金费率、标记价格偏离等）
2. 解析Wyckoff短期信号
3. 根据价格变化生成规则决策
4. 可选调用LLM进行深度分析
"""

from trade_runtime.decision.models import AgentView
from trade_runtime.decision.agent_profile_resolver import resolve_agent_mode
from trade_runtime.decision.llm_agent_runner import run_llm_agent
from trade_runtime.decision.state import DecisionState
from trade_runtime.trigger_policy import resolve_trigger_policy


_SIGNIFICANT_MARKET_EVENT_TYPES = {
    "mark_price",
    "ticker",
    "orderbook_imbalance",
    "funding_rate",
}


def _safe_float(value: object, default: float = 0.0) -> float:
    """安全转换为浮点数

    Args:
        value: 输入值
        default: 默认值

    Returns:
        float: 转换后的浮点数
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _liquidation_threshold(resolved_policy: dict) -> float:
    """获取爆仓阈值

    Args:
        resolved_policy: 解析后的策略配置

    Returns:
        float: 爆仓名义金额阈值
    """
    market_trigger = resolved_policy.get("market_trigger") or {}
    return _safe_float(
        market_trigger.get("liquidationNotionalUsd") or market_trigger.get("liquidation_notional_usd"),
        250000.0,
    )


def _funding_rate_threshold(resolved_policy: dict) -> float:
    """获取资金费率阈值

    Args:
        resolved_policy: 解析后的策略配置

    Returns:
        float: 资金费率绝对值阈值
    """
    market_trigger = resolved_policy.get("market_trigger") or {}
    return abs(
        _safe_float(
            market_trigger.get("fundingRateAbs") or market_trigger.get("funding_rate_abs"),
            0.0,
        )
    )


def _mark_price_deviation_threshold(resolved_policy: dict) -> float:
    """获取标记价格偏离阈值

    Args:
        resolved_policy: 解析后的策略配置

    Returns:
        float: 标记价格偏离百分比阈值
    """
    market_trigger = resolved_policy.get("market_trigger") or {}
    return abs(
        _safe_float(
            market_trigger.get("markPriceDeviationPct") or market_trigger.get("mark_price_deviation_pct"),
            0.0,
        )
    )


def _price_acceleration_threshold(resolved_policy: dict) -> float:
    """获取价格加速度阈值

    Args:
        resolved_policy: 解析后的策略配置

    Returns:
        float: 价格加速度百分比阈值
    """
    market_trigger = resolved_policy.get("market_trigger") or {}
    return abs(
        _safe_float(
            market_trigger.get("priceAccelerationPct") or market_trigger.get("price_acceleration_pct"),
            0.0,
        )
    )


def _wyckoff_shortterm_signal(state: DecisionState) -> dict:
    """获取Wyckoff短期信号

    Args:
        state: 决策状态

    Returns:
        dict: Wyckoff信号字典
    """
    feature_snapshot = state.get("feature_snapshot") or {}
    if not isinstance(feature_snapshot, dict):
        return {}
    signal = feature_snapshot.get("wyckoff_shortterm")
    return signal if isinstance(signal, dict) else {}


def _has_ready_wyckoff_shortterm_signal(state: DecisionState) -> bool:
    """检查是否有就绪的Wyckoff短期信号

    Args:
        state: 决策状态

    Returns:
        bool: 是否有就绪的信号
    """
    signal = _wyckoff_shortterm_signal(state)
    if str(signal.get("trigger") or "").strip().lower() in {"", "none"}:
        return False
    if str(signal.get("entry_bias") or "").strip().lower() not in {"bullish", "bearish"}:
        return False
    return str(signal.get("trade_readiness") or "").strip().lower() == "ready"


def _wyckoff_confidence_pct(signal: dict) -> int:
    """计算Wyckoff信号置信度百分比

    Args:
        signal: Wyckoff信号字典

    Returns:
        int: 置信度百分比（50-95）
    """
    raw_confidence = _safe_float(signal.get("confidence"), 0.0)
    if raw_confidence <= 1.0:
        raw_confidence *= 100.0
    return max(50, min(95, int(round(raw_confidence))))


def _latest_market_tick_price(state: DecisionState) -> float:
    """获取最新市场价格

    Args:
        state: 决策状态

    Returns:
        float: 最新市场价格
    """
    for event in reversed(state.get("event_bundle", []) or []):
        if not isinstance(event, dict):
            continue
        if str(event.get("event_type") or "").strip().lower() != "market_tick":
            continue
        price = _safe_float(event.get("price"), 0.0)
        if price > 0:
            return price
    return 0.0


def _has_significant_market_event(state: DecisionState, *, resolved_policy: dict) -> bool:
    """检查是否有显著市场事件

    Args:
        state: 决策状态
        resolved_policy: 解析后的策略配置

    Returns:
        bool: 是否有显著市场事件
    """
    if _has_ready_wyckoff_shortterm_signal(state):
        return True
    liquidation_threshold = _liquidation_threshold(resolved_policy)
    funding_rate_threshold = _funding_rate_threshold(resolved_policy)
    mark_price_deviation_threshold = _mark_price_deviation_threshold(resolved_policy)
    price_acceleration_threshold = _price_acceleration_threshold(resolved_policy)
    feature_snapshot = state.get("feature_snapshot") or {}
    if isinstance(feature_snapshot, dict) and price_acceleration_threshold > 0.0:
        price_acceleration_pct = abs(_safe_float(feature_snapshot.get("market_price_acceleration_pct"), 0.0))
        if price_acceleration_pct >= price_acceleration_threshold:
            return True
    latest_market_tick_price = _latest_market_tick_price(state)
    for event in state.get("event_bundle", []) or []:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "").strip().lower()
        if event_type == "liquidation":
            notional = _safe_float(event.get("notionalUsd") or event.get("notional_usd"), 0.0)
            if notional >= liquidation_threshold:
                return True
            continue
        if event_type == "funding_rate":
            funding_rate = abs(_safe_float(event.get("funding_rate") or event.get("fundingRate"), 0.0))
            if funding_rate_threshold <= 0.0:
                return True
            if funding_rate >= funding_rate_threshold:
                return True
            continue
        if event_type == "mark_price":
            mark_price = _safe_float(event.get("price"), 0.0)
            if mark_price <= 0:
                continue
            if mark_price_deviation_threshold <= 0.0:
                return True
            if latest_market_tick_price <= 0:
                continue
            deviation_pct = abs(((mark_price - latest_market_tick_price) / latest_market_tick_price) * 100.0)
            if deviation_pct >= mark_price_deviation_threshold:
                return True
            continue
        if event_type in _SIGNIFICANT_MARKET_EVENT_TYPES:
            return True
        if event_type.startswith("market_") and event_type != "market_tick":
            return True
    return False


def _market_move_below_rule_only_threshold(state: DecisionState, *, resolved_policy: dict) -> bool:
    """检查市场波动是否低于规则阈值

    Args:
        state: 决策状态
        resolved_policy: 解析后的策略配置

    Returns:
        bool: 是否低于规则阈值
    """
    market_trigger = resolved_policy.get("market_trigger") or {}
    rule_only_threshold = _safe_float(
        market_trigger.get("ruleOnlyPriceChangePct") or market_trigger.get("rule_only_price_change_pct"),
        1.0,
    )
    feature_snapshot = state.get("feature_snapshot") or {}
    price_change_pct = max(
        abs(_safe_float(feature_snapshot.get("price_change_pct"), 0.0)),
        abs(_safe_float(feature_snapshot.get("market_window_price_change_pct"), 0.0)),
    )
    return price_change_pct < rule_only_threshold


def _should_skip_market_llm(state: DecisionState) -> bool:
    """判断是否跳过市场LLM调用

    Args:
        state: 决策状态

    Returns:
        bool: 是否跳过LLM
    """
    resolved_policy = resolve_trigger_policy(
        runtime_config=state.get("runtime_config"),
        strategy_context=state.get("strategy_context"),
    )
    if _has_significant_market_event(state, resolved_policy=resolved_policy):
        return False
    return _market_move_below_rule_only_threshold(state, resolved_policy=resolved_policy)


def _build_market_rule_view(state: DecisionState) -> dict:
    """构建市场规则观点

    Args:
        state: 决策状态

    Returns:
        dict: 市场观点字典
    """
    feature_snapshot = state.get("feature_snapshot", {})
    wyckoff_signal = _wyckoff_shortterm_signal(state)
    if _has_ready_wyckoff_shortterm_signal(state):
        entry_bias = str(wyckoff_signal.get("entry_bias") or "").strip().lower()
        trigger = str(wyckoff_signal.get("trigger") or "").strip() or "wyckoff_setup"
        return AgentView(
            bias="bullish" if entry_bias == "bullish" else "bearish",
            confidence=_wyckoff_confidence_pct(wyckoff_signal),
            reason=f"wyckoff:{trigger}",
            ttl=900,
            risk_note=str(wyckoff_signal.get("trade_readiness") or "wyckoff_setup"),
        ).model_dump()
    if str(wyckoff_signal.get("trigger") or "").strip().lower() not in {"", "none"}:
        trigger = str(wyckoff_signal.get("trigger") or "").strip() or "wyckoff_setup"
        readiness = str(wyckoff_signal.get("trade_readiness") or "watch").strip().lower() or "watch"
        return AgentView(
            bias="neutral",
            confidence=min(55, _wyckoff_confidence_pct(wyckoff_signal)),
            reason=f"wyckoff_watch:{trigger}:{wyckoff_signal.get('no_trade_reason') or readiness}",
            ttl=300,
            risk_note=str(wyckoff_signal.get("trap_risk") or readiness),
        ).model_dump()
    snapshot_pct = _safe_float(feature_snapshot.get("price_change_pct"), 0.0)
    window_pct = _safe_float(feature_snapshot.get("market_window_price_change_pct"), 0.0)
    pct = window_pct if abs(window_pct) > abs(snapshot_pct) else snapshot_pct
    neutral_deadband_pct = 0.1
    bias = "neutral"
    confidence = 50
    if pct >= neutral_deadband_pct:
        bias = "bullish"
        confidence = 80 if abs(pct) >= 5 else 60
    elif pct <= -neutral_deadband_pct:
        bias = "bearish"
        confidence = 80 if abs(pct) >= 5 else 60
    return AgentView(
        bias=bias,
        confidence=confidence,
        reason=f"price_change_pct={pct}",
        ttl=900,
        risk_note="high_volatility" if abs(pct) >= 5 else "normal",
    ).model_dump()


def market_agent(state: DecisionState) -> DecisionState:
    """市场Agent节点

    分析市场数据并生成市场观点。

    流程：
    1. 构建规则观点
    2. 判断是否需要LLM调用
    3. 可选调用LLM进行深度分析
    4. 更新状态中的market_view

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含market_view
    """
    rule_view = _build_market_rule_view(state)
    if resolve_agent_mode(state.get("agent_profiles"), "market_agent", state=state) != "RULE" and not _should_skip_market_llm(state):
        llm_view = run_llm_agent(
            state,
            agent_code="market_agent",
            binding_scope="MARKET_AGENT",
            rule_view=rule_view,
        )
        if llm_view is not None:
            state["market_view"] = llm_view
            return state
    state["market_view"] = rule_view
    return state
