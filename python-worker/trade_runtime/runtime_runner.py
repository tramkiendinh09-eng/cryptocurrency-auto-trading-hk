"""
运行时执行器模块

提供交易运行时的单次执行逻辑，负责协调配置获取、触发策略评估、
决策图执行等核心流程。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from trade_runtime.callback_client import RuntimeCallbackClient
from trade_runtime.config_client import RuntimeConfigClient
from trade_runtime.decision.graph import build_decision_graph
from trade_runtime.execution.router import ExecutionRouter
from trade_runtime.memory.trade_lifecycle import (
    TradeLifecycleManager,
    apply_trade_lifecycle_status,
    process_trade_lifecycle,
)
from trade_runtime.position_risk_watcher import PositionRiskWatcher
from trade_runtime.trigger_policy import classify_event_strength_from_policy, evaluate_trigger_policy


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _format_current_time(value: Any) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        parsed = datetime.now(timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _resolve_current_time(current_time: Any, fallback_time: Any) -> str:
    if current_time not in (None, ""):
        return str(current_time).strip()
    return _format_current_time(fallback_time)


def _safe_non_negative_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(int(float(value)), 0)
    except (TypeError, ValueError):
        return None


def _current_position_holding_minutes(opened_at: Any, current_time: Any) -> int | None:
    opened_at_dt = _parse_datetime(opened_at)
    current_time_dt = _parse_datetime(current_time)
    if opened_at_dt is None or current_time_dt is None:
        return None
    holding_seconds = (current_time_dt - opened_at_dt).total_seconds()
    if holding_seconds < 0:
        return 0
    return int(holding_seconds // 60)


def _normalize_mode(value: Any) -> str | None:
    """标准化运行模式

    Args:
        value: 运行模式值

    Returns:
        str | None: 标准化后的运行模式，空值返回None
    """
    normalized = str(value or "").strip().lower()
    return normalized or None


def _resolve_strategy_runtime_mode(strategy_context: dict[str, Any] | None) -> str | None:
    """解析策略运行模式

    从策略上下文中提取运行模式配置。

    Args:
        strategy_context: 策略上下文

    Returns:
        str | None: 运行模式
    """
    if not isinstance(strategy_context, dict):
        return None
    strategy_mode = _normalize_mode(strategy_context.get("runtime_mode"))
    if strategy_mode:
        return strategy_mode
    strategy_config = strategy_context.get("strategy_config") or {}
    if not isinstance(strategy_config, dict):
        return None
    return _normalize_mode(strategy_config.get("runtimeMode") or strategy_config.get("runtime_mode"))


def _resolve_strategy_risk_overrides(strategy_context: dict[str, Any] | None) -> dict[str, Any]:
    """解析策略风险覆盖配置

    Args:
        strategy_context: 策略上下文

    Returns:
        dict[str, Any]: 风险覆盖配置
    """
    if not isinstance(strategy_context, dict):
        return {}
    strategy_config = strategy_context.get("strategy_config") or {}
    if not isinstance(strategy_config, dict):
        return {}
    risk_config = strategy_config.get("riskConfig") or strategy_config.get("risk_config") or {}
    sources = [strategy_config]
    if isinstance(risk_config, dict):
        sources.insert(0, risk_config)
    overrides: dict[str, Any] = {}
    key_pairs = (
        ("maxPositionRatio", "max_position_ratio"),
        ("maxDailyLoss", "max_daily_loss"),
        ("maxConsecutiveFailures", "max_consecutive_failures"),
    )
    for source in sources:
        for camel_key, snake_key in key_pairs:
            if camel_key in source and source.get(camel_key) not in (None, ""):
                overrides[snake_key] = source.get(camel_key)
            elif snake_key in source and source.get(snake_key) not in (None, ""):
                overrides[snake_key] = source.get(snake_key)
    return overrides


def _resolve_strategy_list_payload(strategy_context: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    """解析策略列表类型数据

    Args:
        strategy_context: 策略上下文
        key: 数据键名

    Returns:
        list[dict[str, Any]]: 列表数据
    """
    if not isinstance(strategy_context, dict):
        return []
    payload = strategy_context.get(key) or []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _runtime_account_value(runtime_account_context: Any, *keys: str) -> Any:
    """从运行时账户上下文获取值

    支持字典和对象两种形式的上下文。

    Args:
        runtime_account_context: 运行时账户上下文
        keys: 候选字段名列表

    Returns:
        Any: 匹配到的值，未命中时返回None
    """
    if runtime_account_context is None:
        return None
    for key in keys:
        value = None
        if isinstance(runtime_account_context, dict):
            value = runtime_account_context.get(key)
        else:
            value = getattr(runtime_account_context, key, None)
        if value not in (None, ""):
            return value
    return None


def _normalize_runtime_account_context(runtime_account_context: Any) -> dict[str, Any]:
    """标准化运行时账户上下文

    将账户上下文转换为标准字典格式，包含账户权益、盈亏、仓位等信息。

    Args:
        runtime_account_context: 运行时账户上下文

    Returns:
        dict[str, Any]: 标准化后的账户上下文
    """
    current_position_side = str(
        _runtime_account_value(runtime_account_context, "current_position_side", "currentPositionSide") or "flat"
    ).strip().lower() or "flat"
    current_position_quantity = float(
        _runtime_account_value(runtime_account_context, "current_position_quantity", "currentPositionQuantity") or 0.0
    )
    if current_position_quantity <= 0:
        current_position_side = "flat"
    current_position_opened_at = _runtime_account_value(
        runtime_account_context,
        "current_position_opened_at",
        "currentPositionOpenedAt",
    )
    current_position_holding_minutes = _runtime_account_value(
        runtime_account_context,
        "current_position_holding_minutes",
        "currentPositionHoldingMinutes",
    )
    entry_trace_id = _runtime_account_value(
        runtime_account_context,
        "entry_trace_id",
        "entryTraceId",
    )
    if current_position_side == "flat":
        current_position_opened_at = None
        current_position_holding_minutes = None
        entry_trace_id = None
    return {
        "account_equity": float(_runtime_account_value(runtime_account_context, "account_equity", "accountEquity") or 10_000.0),
        "daily_pnl": float(_runtime_account_value(runtime_account_context, "daily_pnl", "dailyPnl") or 0.0),
        "realized_pnl": float(_runtime_account_value(runtime_account_context, "realized_pnl", "realizedPnl") or 0.0),
        "unrealized_pnl": float(_runtime_account_value(runtime_account_context, "unrealized_pnl", "unrealizedPnl") or 0.0),
        "current_position_side": current_position_side,
        "current_position_quantity": current_position_quantity,
        "current_position_notional": float(
            _runtime_account_value(runtime_account_context, "current_position_notional", "currentPositionNotional") or 0.0
        ),
        "entry_price": float(
            _runtime_account_value(runtime_account_context, "entry_price", "entryPrice") or 0.0
        ),
        "max_drawdown_pct": float(
            _runtime_account_value(runtime_account_context, "max_drawdown_pct", "maxDrawdownPct") or 0.0
        ),
        "peak_account_equity": float(
            _runtime_account_value(runtime_account_context, "peak_account_equity", "peakAccountEquity") or 0.0
        ),
        "current_position_opened_at": current_position_opened_at,
        "current_time": _runtime_account_value(
            runtime_account_context,
            "current_time",
            "currentTime",
        ),
        "current_position_holding_minutes": current_position_holding_minutes,
        "consecutive_failures": int(
            _runtime_account_value(runtime_account_context, "consecutive_failures", "consecutiveFailures") or 0
        ),
        "entry_trace_id": entry_trace_id,
    }


def _exchange_account_value(exchange_account: Any, *keys: str) -> Any:
    """从交易所账户获取值

    Args:
        exchange_account: 交易所账户
        keys: 候选字段名列表

    Returns:
        Any: 匹配到的值
    """
    if exchange_account is None:
        return None
    for key in keys:
        value = None
        if isinstance(exchange_account, dict):
            value = exchange_account.get(key)
        else:
            value = getattr(exchange_account, key, None)
        if value not in (None, ""):
            return value
    return None


def _normalize_exchange_account(exchange_account: Any) -> dict[str, Any] | None:
    """标准化交易所账户信息

    Args:
        exchange_account: 交易所账户

    Returns:
        dict[str, Any] | None: 标准化后的账户信息
    """
    if exchange_account is None:
        return None
    exchange_code = _exchange_account_value(exchange_account, "exchange_code", "exchangeCode")
    account_name = _exchange_account_value(exchange_account, "account_name", "accountName")
    health_status = _exchange_account_value(exchange_account, "health_status", "healthStatus")
    last_validated_at = _exchange_account_value(exchange_account, "last_validated_at", "lastValidatedAt")
    last_error_message = _exchange_account_value(exchange_account, "last_error_message", "lastErrorMessage")
    return {
        "exchange_code": str(exchange_code or "").strip().lower(),
        "account_name": str(account_name or "").strip(),
        "health_status": str(health_status or "").strip().lower(),
        "last_validated_at": str(last_validated_at or "").strip(),
        "last_error_message": str(last_error_message or "").strip(),
    }


class TradeRuntimeRunner:
    """交易运行时执行器

    负责执行单次交易决策流程，包括：
    - 获取运行时配置
    - 评估触发策略
    - 构建决策状态
    - 执行决策图

    Attributes:
        config_client: 配置客户端
        callback_client: 回调客户端
        graph: 决策图
        execution_router: 执行路由器
        memory_store: 记忆存储
        decision_model_client: 决策模型客户端
        trigger_state: 触发状态
    """

    def __init__(
        self,
        *,
        config_client: RuntimeConfigClient,
        callback_client: RuntimeCallbackClient,
        graph: Any = None,
        execution_router: ExecutionRouter | None = None,
        memory_store: Any = None,
        lifecycle_manager: TradeLifecycleManager | None = None,
    ):
        """初始化交易运行时执行器

        Args:
            config_client: 配置客户端
            callback_client: 回调客户端
            graph: 决策图，默认自动构建
            execution_router: 执行路由器
            memory_store: 记忆存储
            lifecycle_manager: 交易生命周期管理器
        """
        self.config_client = config_client
        self.callback_client = callback_client
        self.graph = graph or build_decision_graph()
        self.execution_router = execution_router
        self.memory_store = memory_store
        self.lifecycle_manager = lifecycle_manager
        self.decision_model_client = None
        self.trigger_state: dict[str, Any] = {}
        self.position_risk_watcher = PositionRiskWatcher()

    def run_once(
        self,
        *,
        trace_id: str | None = None,
        symbol: str,
        exchange: str,
        event_bundle: list[dict[str, Any]],
        feature_snapshot: dict[str, Any],
        signal_window_states: list[dict[str, Any]] | None = None,
        strategy_context: dict[str, Any] | None = None,
        runtime_account_context: Any | None = None,
        exchange_account: Any | None = None,
        mode_override: str | None = None,
        bypass_trigger_guards: bool = False,
        market_source_status: str | None = None,
        market_source_context: dict[str, Any] | None = None,
        market_context_history: list[dict[str, Any]] | None = None,
        evaluation_time: Any | None = None,
    ) -> dict[str, Any]:
        """执行一次交易决策流程

        流程步骤：
        1. 获取运行时配置
        2. 解析运行模式（paper/shadow/live）
        3. 标准化账户上下文
        4. 计算事件强度
        5. 评估触发策略
        6. 构建决策状态
        7. 执行决策图

        Args:
            trace_id: 追踪ID
            symbol: 交易品种
            exchange: 交易所代码
            event_bundle: 事件包列表
            feature_snapshot: 特征快照
            signal_window_states: 信号窗口状态列表
            strategy_context: 策略上下文
            runtime_account_context: 运行时账户上下文
            exchange_account: 交易所账户
            mode_override: 模式覆盖
            bypass_trigger_guards: 是否绕过触发守卫
            market_source_status: 市场数据源状态
            market_source_context: 市场数据源上下文
            market_context_history: 市场上下文历史
            evaluation_time: 评估时间

        Returns:
            dict[str, Any]: 决策执行结果
        """
        runtime_config = self.config_client.get_config()
        strategy_runtime_mode = _resolve_strategy_runtime_mode(strategy_context)
        requested_mode = _normalize_mode(mode_override) or strategy_runtime_mode or _normalize_mode(runtime_config.default_mode) or "paper"
        effective_mode = "shadow" if requested_mode == "live" and not runtime_config.live_enabled else requested_mode
        resolved_runtime_config = runtime_config.model_dump()
        normalized_runtime_account_context = _normalize_runtime_account_context(runtime_account_context)
        current_time = _resolve_current_time(normalized_runtime_account_context.get("current_time"), evaluation_time)
        normalized_runtime_account_context["current_time"] = current_time
        holding_minutes = normalized_runtime_account_context.get("current_position_holding_minutes")
        if holding_minutes in (None, ""):
            holding_minutes = _current_position_holding_minutes(
                normalized_runtime_account_context.get("current_position_opened_at"),
                current_time,
            )
        holding_minutes = _safe_non_negative_int(holding_minutes)
        if holding_minutes is not None:
            normalized_runtime_account_context["current_position_holding_minutes"] = holding_minutes
        normalized_exchange_account = _normalize_exchange_account(exchange_account)
        normalized_feature_snapshot = dict(feature_snapshot if isinstance(feature_snapshot, dict) else {})
        normalized_event_bundle = [item for item in event_bundle if isinstance(item, dict)] if isinstance(event_bundle, list) else []
        position_risk_result = self.position_risk_watcher.evaluate(
            account_context=normalized_runtime_account_context,
            feature_snapshot=normalized_feature_snapshot,
            event_bundle=normalized_event_bundle,
            runtime_config=resolved_runtime_config,
            strategy_context=strategy_context if isinstance(strategy_context, dict) else {},
            now=evaluation_time or datetime.now(timezone.utc),
        )
        if isinstance(position_risk_result, dict):
            position_risk_result["requested_mode"] = requested_mode
            position_risk_result["effective_mode"] = effective_mode
            position_risk_result["live_enabled"] = runtime_config.live_enabled
            position_risk_result["exchange"] = exchange
        # 始终注入仓位风险上下文（无论是否触发风险阈值）
        # 这样主管Agent始终能看到当前仓位的风险状态
        risk_context = position_risk_result.get("position_risk_context")
        if isinstance(risk_context, dict) and risk_context:
            normalized_feature_snapshot["position_risk_context"] = risk_context
        elif position_risk_result.get("has_position"):
            # 有仓位但无风险触发时，也提供基础仓位信息
            context = position_risk_result.get("position_risk_context") or {}
            normalized_feature_snapshot["position_risk_context"] = {
                "side": context.get("side"),
                "quantity": context.get("quantity"),
                "entry_price": context.get("entry_price"),
                "current_price": context.get("current_price"),
                "pnl_pct": context.get("pnl_pct"),
                "adverse_move_pct": context.get("adverse_move_pct", 0.0),
                "profit_giveback_pct": context.get("profit_giveback_pct", 0.0),
                "peak_unrealized_pnl_pct": context.get("peak_unrealized_pnl_pct"),
                "severity": "none",
                "status": "healthy",
            }

        # 风险事件处理：只在触发风险时添加风险事件到事件包
        if position_risk_result.get("triggered"):
            risk_event = position_risk_result.get("position_risk_event")
            if isinstance(risk_event, dict) and risk_event:
                risk_event["requested_mode"] = requested_mode
                risk_event["effective_mode"] = effective_mode
                risk_event["live_enabled"] = runtime_config.live_enabled
                risk_event["exchange"] = exchange
                normalized_event_bundle.append(risk_event)
            normalized_feature_snapshot["position_risk_severity"] = position_risk_result.get("severity")
        normalized_feature_snapshot["event_strength"] = classify_event_strength_from_policy(
            event_bundle=normalized_event_bundle,
            feature_snapshot=normalized_feature_snapshot,
            runtime_config=resolved_runtime_config,
            strategy_context=strategy_context,
            now=evaluation_time or datetime.now(timezone.utc),
        )
        dispatch_decision = evaluate_trigger_policy(
            event_bundle=normalized_event_bundle,
            feature_snapshot=normalized_feature_snapshot,
            signal_window_states=signal_window_states or [],
            runtime_account_context=normalized_runtime_account_context,
            runtime_config=resolved_runtime_config,
            strategy_context=strategy_context,
            trigger_state=self.trigger_state,
            now=evaluation_time or datetime.now(timezone.utc),
            bypass_budget=bypass_trigger_guards or bool(position_risk_result.get("bypass_trigger_guards")),
            bypass_cooldown=bypass_trigger_guards or bool(position_risk_result.get("bypass_trigger_guards")),
        )
        self.trigger_state = dispatch_decision.get("trigger_state") or self.trigger_state
        state = {
            "trace_id": trace_id or uuid4().hex,
            "symbol": symbol,
            "exchange": exchange,
            "event_bundle": normalized_event_bundle,
            "feature_snapshot": normalized_feature_snapshot,
            "market_context_history": market_context_history or [],
            "signal_window_states": signal_window_states or [],
            "mode": effective_mode,
            "requested_mode": requested_mode,
            "effective_mode": effective_mode,
            "mode_downgraded": requested_mode != effective_mode,
            "live_enabled": runtime_config.live_enabled,
            "runtime_config": resolved_runtime_config,
            "callback_client": self.callback_client,
            "execution_router": self.execution_router,
            "runtime_account_context": normalized_runtime_account_context,
            "position_risk_result": position_risk_result,
            "current_time": current_time,
            **normalized_runtime_account_context,
            **{key: value for key, value in dispatch_decision.items() if key != "trigger_state"},
        }
        if normalized_exchange_account is not None:
            state["exchange_account"] = normalized_exchange_account
        if market_source_status:
            state["market_source_status"] = market_source_status
        if market_source_context is not None:
            state["market_source_context"] = market_source_context
        if strategy_context is not None:
            state["strategy_context"] = strategy_context
            state["prompt_bindings"] = _resolve_strategy_list_payload(strategy_context, "prompt_bindings")
            state["agent_profiles"] = _resolve_strategy_list_payload(strategy_context, "agent_profiles")
            state["resolved_agent_configs"] = _resolve_strategy_list_payload(strategy_context, "resolved_agent_configs")
            deliberation_policy = strategy_context.get("deliberation_policy")
            if isinstance(deliberation_policy, dict):
                state["deliberation_policy"] = deliberation_policy
            supervisor_policy = strategy_context.get("supervisor_policy") or strategy_context.get("supervisorPolicy")
            if isinstance(supervisor_policy, dict):
                state["supervisor_policy"] = supervisor_policy
        if self.memory_store is not None:
            state["memory_store"] = self.memory_store
        if self.decision_model_client is not None:
            state["decision_model_client"] = self.decision_model_client
        if self.lifecycle_manager is not None:
            state["lifecycle_manager"] = self.lifecycle_manager
        result = self.graph.invoke(state)
        lifecycle_status = result.get("lifecycle_status")
        if not isinstance(lifecycle_status, dict) or not lifecycle_status:
            lifecycle_status = self._process_lifecycle(result, normalized_runtime_account_context)
        apply_trade_lifecycle_status(result, lifecycle_status)
        return result

    def _process_lifecycle(
        self,
        result: dict[str, Any],
        account_context: dict[str, Any],
    ) -> dict[str, Any]:
        """处理交易生命周期追踪

        根据决策结果更新交易生命周期记录：
        - OPEN_LONG/OPEN_SHORT: 记录开仓
        - ADD_LONG/ADD_SHORT: 加仓，更新lifecycle记录（不创建新记录）
        - REDUCE: 减仓，更新lifecycle记录
        - CLOSE: 平仓并生成记忆

        注意：CLOSE 操作时，trace_id 应与开仓时相同。
        如果账户上下文中有 entry_trace_id，优先使用它来关联开仓记录。

        Args:
            result: 决策执行结果
            account_context: 账户上下文
        """
        return process_trade_lifecycle(
            state=result,
            lifecycle_manager=self.lifecycle_manager,
            account_context=account_context,
        )
