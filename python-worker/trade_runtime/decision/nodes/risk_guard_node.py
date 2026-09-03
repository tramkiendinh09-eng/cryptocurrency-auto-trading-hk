"""
风控守卫节点模块 - 交易决策的最后一道防线

实现决策图中的风控检查节点，对交易决策进行风险控制验证。

风控守卫的职责:
1. 检查仓位限制: 确保不超过最大仓位比例
2. 检查日亏损限制: 防止单日亏损过大
3. 检查连续失败次数: 防止连续亏损
4. 检查数据源状态: 确保数据质量
5. 检查账户健康状态: 确保账户正常

风控检查流程:
```
主管决策(supervisor_decision)
           │
           ▼
    ┌─────────────────┐
    │ AI调用失败检查  │ ──► 失败且为开仓操作 ──► 阻止
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ SKIP/HOLD检查   │ ──► 直接通过
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 仓位限制检查    │ ──► 超过最大仓位 ──► 阻止
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 日亏损检查      │ ──► 超过最大日亏损 ──► 阻止
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 连续失败检查    │ ──► 超过最大连续失败 ──► 阻止
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 数据源状态检查  │ ──► 数据异常 ──► 阻止(可选)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 账户健康检查    │ ──► 账户异常 ──► 阻止(实盘模式)
    └────────┬────────┘
             │
             ▼
         通过检查
```

风控规则配置:
- max_position_ratio: 最大仓位比例(默认0.4，即40%)
- max_daily_loss: 最大日亏损(默认-500 USDT)
- max_consecutive_failures: 最大连续失败次数(默认3次)
- live_order_requires_healthy_account: 实盘订单是否需要健康账户

输出结果(risk_result):
- passed: 是否通过检查
- reason: 原因说明
- rule_code: 触发的规则代码
"""

from __future__ import annotations

from trade_runtime.decision.sizing import order_notional, resolve_leverage
from trade_runtime.decision.state import DecisionState
from trade_runtime.decision.timestamps import stamp_state_timestamp
from trade_runtime.risk.guard import RiskGuard
from trade_runtime.config import DEFAULT_MIN_POSITION_HOLD_MINUTES, _parse_json_object
from trade_runtime.prompting.render_context_builder import resolve_current_position_holding_minutes


def _default_min_position_hold_minutes() -> int:
    return DEFAULT_MIN_POSITION_HOLD_MINUTES


def _default_risk_guard() -> RiskGuard:
    """创建默认的风控守卫实例

    Returns:
        RiskGuard: 默认配置的风控守卫
    """
    return RiskGuard(
        max_position_ratio=0.4,
        max_daily_loss=-500.0,
        max_consecutive_failures=3,
    )


def _risk_guard_from_runtime_config(runtime_config: dict[str, object] | None) -> RiskGuard:
    """从运行时配置创建风控守卫实例

    Args:
        runtime_config: 运行时配置字典

    Returns:
        RiskGuard: 配置化的风控守卫实例
    """
    config = runtime_config or {}
    return RiskGuard(
        max_position_ratio=float(config.get("max_position_ratio", 0.4) or 0.4),
        max_daily_loss=float(config.get("max_daily_loss", -500.0) or -500.0),
        max_consecutive_failures=int(config.get("max_consecutive_failures", 3) or 3),
    )


def _halt_on_data_gap_enabled(runtime_config: dict[str, object] | None) -> bool:
    """检查是否启用了数据缺失时暂停功能

    Args:
        runtime_config: 运行时配置

    Returns:
        bool: 是否启用数据缺失暂停
    """
    policy = _parse_json_object((runtime_config or {}).get("runtime_flags_json") or (runtime_config or {}).get("runtimeFlagsJson"))
    value = policy.get("haltOnDataGap")
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _object_config(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    return _parse_json_object(value)


def _nested_object(payload: object, *keys: str) -> dict[str, object]:
    current = _object_config(payload)
    for key in keys:
        current = _object_config(current.get(key))
        if not current:
            return {}
    return current


def _non_negative_config_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _non_negative_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _positive_float(value: object) -> float:
    try:
        parsed = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0


def _normalize_position_side(value: object) -> str:
    side = str(value or "").strip().lower()
    if side in {"long", "buy"}:
        return "long"
    if side in {"short", "sell"}:
        return "short"
    return side


def _first_min_position_hold_minutes(*configs: object) -> int | None:
    for config_value in configs:
        config = _object_config(config_value)
        for key in ("min_position_hold_minutes", "minPositionHoldMinutes"):
            parsed = _non_negative_config_int(config.get(key))
            if parsed is not None:
                return parsed
    return None


def _resolve_min_position_hold_minutes(state: DecisionState) -> int | None:
    runtime_config = _object_config(state.get("runtime_config"))
    runtime_flags = _object_config(runtime_config.get("runtime_flags_json") or runtime_config.get("runtimeFlagsJson"))
    strategy_context = _object_config(state.get("strategy_context"))
    strategy_config = _nested_object(strategy_context, "strategy_config")
    min_minutes = _first_min_position_hold_minutes(
        runtime_config,
        _nested_object(runtime_config, "positionDiscipline"),
        _nested_object(runtime_config, "position_discipline"),
        _nested_object(runtime_flags, "positionDiscipline"),
        _nested_object(runtime_flags, "position_discipline"),
        strategy_config,
        _nested_object(strategy_config, "positionDiscipline"),
        _nested_object(strategy_config, "position_discipline"),
        _nested_object(strategy_context, "positionDiscipline"),
        _nested_object(strategy_context, "position_discipline"),
    )
    if min_minutes is None:
        return _default_min_position_hold_minutes()
    return min_minutes if min_minutes > 0 else None


def _position_discipline_result(state: DecisionState, action: str) -> dict[str, object] | None:
    if action not in {"REDUCE", "CLOSE"}:
        return None
    if action == "CLOSE":
        supervisor_exit_escalation = state.get("supervisor_exit_escalation")
        if isinstance(supervisor_exit_escalation, dict) and supervisor_exit_escalation:
            return None
    min_minutes = _resolve_min_position_hold_minutes(state)
    if min_minutes is None:
        return None
    side = _normalize_position_side(state.get("current_position_side"))
    if side not in {"long", "short"}:
        return None
    quantity = _positive_float(state.get("current_position_quantity"))
    notional = _positive_float(state.get("current_position_notional"))
    if quantity <= 0 and notional <= 0:
        return None
    holding_minutes = _non_negative_int(resolve_current_position_holding_minutes(state))
    if holding_minutes is None or holding_minutes >= min_minutes:
        return None
    return {
        "passed": False,
        "reason": "min_position_hold_minutes",
        "rule_code": "min_position_hold_minutes",
        "action": action,
        "current_position_side": side,
        "current_position_holding_minutes": holding_minutes,
        "min_position_hold_minutes": min_minutes,
    }


def _has_supervisor_ai_call_failed(state: DecisionState) -> bool:
    """检查主管Agent的AI调用是否失败

    Args:
        state: 决策状态

    Returns:
        bool: AI调用是否失败
    """
    if not state.get("ai_call_failed"):
        return False
    errors = state.get("agent_llm_errors")
    if not isinstance(errors, list):
        return True
    return any(
        isinstance(error, dict) and str(error.get("agent_code") or "").strip().lower() == "supervisor_agent"
        for error in errors
    )


def _post_risk_guard_hit(state: DecisionState) -> None:
    """发送风控触发回调

    当风控规则触发时，通过回调客户端通知外部系统。

    Args:
        state: 决策状态
    """
    callback_client = state.get("callback_client")
    risk_result = state.get("risk_result") or {}
    if callback_client is None or not hasattr(callback_client, "post_risk_guard_hit"):
        return
    if risk_result.get("passed", False):
        return
    callback_client.post_risk_guard_hit(
        {
            "traceId": state.get("trace_id", ""),
            "ruleCode": risk_result.get("rule_code", risk_result.get("reason", "risk_blocked")),
            "reason": risk_result.get("reason", "risk_blocked"),
        }
    )


def risk_guard_node(state: DecisionState) -> DecisionState:
    """风控守卫节点

    对主管决策进行风控检查，决定是否允许执行。

    检查顺序:
    1. AI调用失败检查(fail-closed模式)
    2. SKIP/HOLD动作直接通过
    3. 仓位限制检查
    4. 日亏损检查
    5. 连续失败检查
    6. 数据源状态检查(可选)
    7. 账户健康检查(实盘模式)

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含risk_result字段
    """
    stamp_state_timestamp(state, "riskCheckedAt")
    decision = state.get("supervisor_decision") or {}
    action = str(decision.get("action") or "").strip().upper()

    # AI调用失败且为开仓操作时，采用fail-closed策略阻止
    if _has_supervisor_ai_call_failed(state) and action in {"OPEN_LONG", "OPEN_SHORT", "ADD_LONG", "ADD_SHORT"}:
        state["risk_result"] = {
            "passed": False,
            "reason": "ai_call_failed_fail_closed",
            "rule_code": "ai_call_failed_fail_closed",
        }
        _post_risk_guard_hit(state)
        return state

    # SKIP和HOLD动作直接通过
    if action in {"SKIP", "HOLD"}:
        state["risk_result"] = {"passed": True, "reason": "skip"}
        return state

    position_discipline_result = _position_discipline_result(state, action)
    if position_discipline_result is not None:
        state["risk_result"] = position_discipline_result
        _post_risk_guard_hit(state)
        return state

    # 提取账户状态信息
    account_equity = float(state.get("account_equity", 10_000))
    size_hint = float(decision.get("size_hint", 0.0))
    # 必须与 execution_node 用同一个公式，否则会出现"风控放行了但下不出去"
    # 或者"模型按区间给的值被拒"这类很难查的问题。
    order_leverage = resolve_leverage(state.get("runtime_config"), decision)
    requested_notional = float(
        state.get("requested_notional", order_notional(account_equity, size_hint, order_leverage))
    )
    current_position_notional = float(state.get("current_position_notional", 0.0) or 0.0)
    daily_pnl = float(state.get("daily_pnl", 0.0))
    consecutive_failures = int(state.get("consecutive_failures", 0))

    # 获取或创建风控守卫实例
    risk_guard = state.get("risk_guard") or _risk_guard_from_runtime_config(state.get("runtime_config")) or _default_risk_guard()

    # 执行风控评估
    state["risk_result"] = risk_guard.evaluate(
        account_equity=account_equity,
        requested_notional=requested_notional,
        current_position_notional=current_position_notional,
        check_position_limit=action in {"OPEN_LONG", "OPEN_SHORT", "ADD_LONG", "ADD_SHORT"},
        # 传进去让上限按保证金口径判定：max_position_ratio 约束的是动用了
        # 多少权益，不是敞口，否则 3 倍杠杆下 0.3 的上限会把 size_hint
        # 压回 0.1，杠杆白加。
        leverage=order_leverage,
        daily_pnl=daily_pnl,
        consecutive_failures=consecutive_failures,
        mode=state.get("mode"),
        live_order_requires_healthy_account=bool((state.get("runtime_config") or {}).get("live_order_requires_healthy_account")),
        exchange_account=state.get("exchange_account"),
        market_source_status=state.get("market_source_status"),
        feature_snapshot=state.get("feature_snapshot"),
        halt_on_data_gap=_halt_on_data_gap_enabled(state.get("runtime_config")),
        event_bundle=state.get("event_bundle"),
    )
    _post_risk_guard_hit(state)
    return state
