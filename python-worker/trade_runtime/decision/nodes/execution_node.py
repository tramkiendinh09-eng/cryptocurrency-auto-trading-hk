"""
执行节点模块

实现交易订单的执行逻辑，包括：
1. 构建订单参数
2. 调用执行路由器下单
3. 处理paper模式的模拟成交
4. 更新仓位和账户状态
5. 发送回调通知
"""

from __future__ import annotations

import json

from trade_runtime.decision.state import DecisionState
from trade_runtime.decision.timestamps import stamp_state_timestamp
from trade_runtime.execution.router import ExecutionRouter


_BUSINESS_TO_ORDER_STATUS = {
    "filled": "FILLED",
    "pending": "PENDING",
    "partial": "PARTIALLY_FILLED",
    "canceled": "CANCELED",
    "expired": "EXPIRED",
    "failed": "REJECTED",
    "blocked": "BLOCKED",
    "skipped": "SKIPPED",
    "submitted": "SUBMITTED",
}


def _default_execution_router() -> ExecutionRouter:
    """创建默认执行路由器

    Returns:
        ExecutionRouter: 无客户端的默认路由器
    """
    return ExecutionRouter(binance_client=None, okx_client=None)


def _last_market_price(state: DecisionState) -> float:
    """从事件包中获取最新市场价格

    Args:
        state: 决策状态

    Returns:
        float: 最新市场价格
    """
    for event in reversed(state.get("event_bundle") or []):
        if event.get("event_type") != "market_tick":
            continue
        price = event.get("price")
        if price is not None:
            return float(price)
    return 0.0


def _feature_snapshot_price(state: DecisionState, *keys: str) -> float:
    feature_snapshot = state.get("feature_snapshot")
    if not isinstance(feature_snapshot, dict):
        return 0.0
    for key in keys:
        value = feature_snapshot.get(key)
        if value in (None, ""):
            continue
        try:
            price = float(value)
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
    return 0.0


def _runtime_execution_price(state: DecisionState) -> float:
    return (
        _feature_snapshot_price(state, "effective_price", "effectivePrice")
        or _feature_snapshot_price(state, "mark_price", "markPrice")
        or _last_market_price(state)
    )


def _execution_float(execution_result: dict, key: str, fallback: float = 0.0) -> float:
    value = execution_result.get(key)
    if value is None:
        return fallback
    return float(value)


def _current_entry_price(state: DecisionState) -> float:
    current_quantity = float(state.get("current_position_quantity", 0.0) or 0.0)
    current_notional = float(state.get("current_position_notional", 0.0) or 0.0)
    # 优先使用 entry_price 字段
    entry_price = float(state.get("entry_price", 0.0) or 0.0)
    if entry_price > 0:
        return entry_price
    # 如果有 notional 和 quantity，计算均价
    if current_quantity > 0 and current_notional > 0:
        return round(current_notional / current_quantity, 8)
    return 0.0


def _resulting_position_quantity(state: DecisionState, decision: dict, execution_result: dict, fill_quantity: float) -> float:
    action = str(decision.get("action", "")).upper()
    current_quantity = float(state.get("current_position_quantity", 0.0) or 0.0)
    status = str(execution_result.get("status") or "").strip().lower()
    if fill_quantity > 0:
        if action in {"CLOSE", "REDUCE"}:
            return round(max(current_quantity - fill_quantity, 0.0), 8)
        if action in {"OPEN_LONG", "OPEN_SHORT", "ADD_LONG", "ADD_SHORT"}:
            return round(current_quantity + fill_quantity, 8)
    if status == "filled" and action == "CLOSE":
        return 0.0
    return round(current_quantity, 8)


def _should_post_position_snapshot(execution_result: dict, fill_quantity: float) -> bool:
    status = str(execution_result.get("status") or "").strip().lower()
    if status in {"pending", "submitted", "failed", "blocked", "skipped", "canceled", "expired"}:
        return False
    return fill_quantity > 0


def _calculate_unrealized_pnl(
    side: str,
    position_quantity: float,
    entry_price: float,
    current_price: float,
) -> float:
    """计算paper模式的未实现盈亏"""
    if position_quantity <= 0 or entry_price <= 0 or current_price <= 0:
        return 0.0
    if side == "long":
        return round((current_price - entry_price) * position_quantity, 8)
    if side == "short":
        return round((entry_price - current_price) * position_quantity, 8)
    return 0.0


def _daily_pnl_basis_equity(state: DecisionState, current_account_equity: float) -> float:
    return round(current_account_equity - float(state.get("daily_pnl", 0.0) or 0.0), 8)


def _peak_account_equity(state: DecisionState, current_account_equity: float) -> float:
    peak_account_equity = float(state.get("peak_account_equity", 0.0) or 0.0)
    if peak_account_equity > 0:
        return peak_account_equity
    max_drawdown_pct = float(state.get("max_drawdown_pct", 0.0) or 0.0)
    if 0.0 < max_drawdown_pct < 100.0:
        denominator = 1.0 - (max_drawdown_pct / 100.0)
        if denominator > 0:
            return round(current_account_equity / denominator, 8)
    return round(current_account_equity, 8)


def _drawdown_pct(peak_account_equity: float, account_equity: float) -> float:
    if peak_account_equity <= 0:
        return 0.0
    return round(max((peak_account_equity - account_equity) / peak_account_equity, 0.0) * 100.0, 8)


def _recalculate_account_metrics(state: DecisionState, new_account_equity: float) -> dict:
    current_account_equity = float(state.get("account_equity", 10_000) or 10_000)
    daily_pnl_basis_equity = _daily_pnl_basis_equity(state, current_account_equity)
    prior_peak_account_equity = _peak_account_equity(state, current_account_equity)
    peak_account_equity = round(max(prior_peak_account_equity, new_account_equity), 8)
    current_drawdown_pct = _drawdown_pct(peak_account_equity, new_account_equity)
    max_drawdown_pct = round(
        max(float(state.get("max_drawdown_pct", 0.0) or 0.0), current_drawdown_pct),
        8,
    )
    return {
        "daily_pnl": round(new_account_equity - daily_pnl_basis_equity, 8),
        "max_drawdown_pct": max_drawdown_pct,
        "peak_account_equity": peak_account_equity,
    }


def _enrich_execution_result(state: DecisionState, execution_result: dict) -> dict:
    enriched = dict(execution_result)
    enriched.setdefault("account_equity", float(state.get("account_equity", 10_000)))
    enriched.setdefault("daily_pnl", float(state.get("daily_pnl", 0.0)))
    enriched.setdefault("max_drawdown_pct", float(state.get("max_drawdown_pct", 0.0)))
    enriched.setdefault("peak_account_equity", float(state.get("peak_account_equity", 0.0)))
    enriched.setdefault("unrealized_pnl", float(state.get("unrealized_pnl", 0.0)))
    enriched.setdefault("realized_pnl", float(state.get("realized_pnl", 0.0)))
    return enriched


def _calculate_realized_pnl_delta(side: str, entry_price: float, fill_price: float, closed_quantity: float) -> float:
    normalized_side = _normalize_position_side(side)
    if closed_quantity <= 0 or entry_price <= 0 or fill_price <= 0:
        return 0.0
    if normalized_side == "long":
        return round((fill_price - entry_price) * closed_quantity, 8)
    if normalized_side == "short":
        return round((entry_price - fill_price) * closed_quantity, 8)
    return 0.0


def _filled_position_effects(state: DecisionState, decision: dict, fill_price: float, fill_quantity: float) -> dict:
    action = str(decision.get("action", "")).strip().upper()
    current_side = _normalize_position_side(state.get("current_position_side"))
    current_quantity = float(state.get("current_position_quantity", 0.0) or 0.0)
    current_entry_price = _current_entry_price(state)
    current_realized_pnl = float(state.get("realized_pnl", 0.0) or 0.0)
    resulting_side = current_side
    position_quantity = max(current_quantity, 0.0)
    entry_price = current_entry_price if position_quantity > 0 else 0.0
    realized_pnl_delta = 0.0

    if fill_price > 0 and fill_quantity > 0:
        if action in {"OPEN_LONG", "ADD_LONG"}:
            resulting_side = "long"
            base_quantity = current_quantity if current_side == "long" and current_quantity > 0 else 0.0
            base_notional = current_entry_price * base_quantity
            position_quantity = round(base_quantity + fill_quantity, 8)
            entry_price = (
                round((base_notional + (fill_price * fill_quantity)) / position_quantity, 8)
                if position_quantity > 0
                else 0.0
            )
        elif action in {"OPEN_SHORT", "ADD_SHORT"}:
            resulting_side = "short"
            base_quantity = current_quantity if current_side == "short" and current_quantity > 0 else 0.0
            base_notional = current_entry_price * base_quantity
            position_quantity = round(base_quantity + fill_quantity, 8)
            entry_price = (
                round((base_notional + (fill_price * fill_quantity)) / position_quantity, 8)
                if position_quantity > 0
                else 0.0
            )
        elif action in {"REDUCE", "CLOSE"}:
            if current_side in {"long", "short"}:
                resulting_side = current_side
            closed_quantity = min(max(current_quantity, 0.0), fill_quantity)
            realized_pnl_delta = _calculate_realized_pnl_delta(
                resulting_side,
                current_entry_price,
                fill_price,
                closed_quantity,
            )
            position_quantity = 0.0 if action == "CLOSE" else round(max(current_quantity - closed_quantity, 0.0), 8)
            entry_price = 0.0 if position_quantity <= 0 else round(current_entry_price, 8)

    current_price = _runtime_execution_price(state) or fill_price
    unrealized_pnl = _calculate_unrealized_pnl(resulting_side, position_quantity, entry_price, current_price)
    realized_pnl = round(current_realized_pnl + realized_pnl_delta, 8)
    return {
        "position_quantity": position_quantity,
        "entry_price": entry_price,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "realized_pnl_delta": realized_pnl_delta,
        "current_position_side": "flat" if position_quantity <= 0 else resulting_side,
        "current_position_notional": round(position_quantity * entry_price, 8) if position_quantity > 0 else 0.0,
    }



def _normalize_position_side(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"long", "buy", "bullish"}:
        return "long"
    if normalized in {"short", "sell", "bearish"}:
        return "short"
    if normalized in {"flat", "hold", "skip", "none", "no_action", "neutral", ""}:
        return "flat"
    return normalized


def _has_position(side: object, quantity: object) -> bool:
    return _normalize_position_side(side) in {"long", "short"} and float(quantity or 0.0) > 0


def _sync_current_position_opened_at(
    state: DecisionState,
    *,
    had_position: bool,
    resulting_side: str,
    resulting_quantity: float,
) -> None:
    if not _has_position(resulting_side, resulting_quantity):
        state["current_position_opened_at"] = None
        return
    if had_position:
        return
    state["current_position_opened_at"] = state.get("executedAt")


def _position_snapshot_side(state: DecisionState, decision: dict) -> str:
    action = str(decision.get("action", "")).strip().upper()
    decision_side = _normalize_position_side(decision.get("side"))
    current_side = _normalize_position_side(state.get("current_position_side"))
    if action in {"OPEN_LONG", "ADD_LONG"}:
        return "long"
    if action in {"OPEN_SHORT", "ADD_SHORT"}:
        return "short"
    if action in {"REDUCE", "CLOSE"}:
        if current_side in {"long", "short"}:
            return current_side
        if decision_side in {"long", "short"}:
            return decision_side
    if decision_side in {"long", "short"}:
        return decision_side
    return "flat"

def _decision_side(state: DecisionState, decision: dict) -> str:
    action = str(decision.get("action", "")).upper()
    side = str(decision.get("side", "")).lower()
    current_position_side = str(state.get("current_position_side", "")).lower()
    if action == "HOLD":
        return "HOLD"
    if action in {"OPEN_LONG", "ADD_LONG"}:
        return "BUY"
    if action in {"OPEN_SHORT", "ADD_SHORT"}:
        return "SELL"
    if action in {"REDUCE", "CLOSE"}:
        effective_side = current_position_side or side
        if effective_side == "long":
            return "SELL"
        if effective_side == "short":
            return "BUY"
    return "BUY" if side == "long" else "SELL" if side == "short" else "HOLD"


def _order_quote_amount(state: DecisionState, decision: dict, account_equity: float) -> float:
    if state.get("requested_notional") is not None:
        return float(state.get("requested_notional"))
    action = str(decision.get("action", "")).upper()
    quantity_base = _order_quantity_base(state, decision)
    current_price = _runtime_execution_price(state)
    if action in {"REDUCE", "CLOSE"} and quantity_base > 0 and current_price > 0:
        return round(quantity_base * current_price, 8)
    if action in {"REDUCE", "CLOSE"}:
        # 优先使用 current_position_notional
        current_position_notional = float(state.get("current_position_notional", 0.0) or 0.0)
        if current_position_notional > 0:
            size_hint = float(decision.get("size_hint", 1.0 if action == "CLOSE" else 0.5))
            return current_position_notional if action == "CLOSE" else current_position_notional * size_hint
        # 如果 current_position_notional = 0，但有持仓数量，则重新计算
        current_position_quantity = float(state.get("current_position_quantity", 0.0) or 0.0)
        entry_price = float(state.get("entry_price", 0.0) or 0.0)
        if current_position_quantity > 0 and entry_price > 0:
            calculated_notional = current_position_quantity * entry_price
            size_hint = float(decision.get("size_hint", 1.0 if action == "CLOSE" else 0.5))
            return calculated_notional if action == "CLOSE" else calculated_notional * size_hint
        # 最后使用当前市场价格计算
        current_price = _runtime_execution_price(state)
        if current_position_quantity > 0 and current_price > 0:
            calculated_notional = current_position_quantity * current_price
            size_hint = float(decision.get("size_hint", 1.0 if action == "CLOSE" else 0.5))
            return calculated_notional if action == "CLOSE" else calculated_notional * size_hint
    size_hint = float(decision.get("size_hint", 0.0))
    return account_equity * size_hint


def _order_quantity_base(state: DecisionState, decision: dict) -> float:
    action = str(decision.get("action", "")).strip().upper()
    if action not in {"REDUCE", "CLOSE"}:
        return 0.0
    current_quantity = max(float(state.get("current_position_quantity", 0.0) or 0.0), 0.0)
    if current_quantity <= 0:
        return 0.0
    if action == "CLOSE":
        return round(current_quantity, 8)
    raw_size_hint = decision.get("size_hint", 0.5)
    size_hint = 0.5 if raw_size_hint in (None, "") else float(raw_size_hint)
    size_hint = min(max(size_hint, 0.0), 1.0)
    return round(current_quantity * size_hint, 8)


def _order_position_side(state: DecisionState, decision: dict) -> str:
    action = str(decision.get("action", "")).strip().upper()
    current_side = _normalize_position_side(state.get("current_position_side"))
    decision_side = _normalize_position_side(decision.get("side"))
    if action in {"OPEN_LONG", "ADD_LONG"}:
        return "long"
    if action in {"OPEN_SHORT", "ADD_SHORT"}:
        return "short"
    if action in {"REDUCE", "CLOSE"} and current_side in {"long", "short"}:
        return current_side
    return decision_side if decision_side in {"long", "short"} else ""


def _order_type(decision: dict) -> str:
    normalized = str(decision.get("order_type") or decision.get("orderType") or "market").strip().lower()
    return "limit" if normalized in {"limit", "post_only"} else "market"


def _optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _enrich_order_metadata(state: DecisionState, decision: dict, order: dict) -> dict:
    action = str(decision.get("action") or "").strip().upper()
    enriched = dict(order)
    enriched["action"] = action
    enriched["position_side"] = _order_position_side(state, decision)
    enriched["reduce_only"] = action in {"REDUCE", "CLOSE"}
    enriched["td_mode"] = str(decision.get("td_mode") or decision.get("tdMode") or "cross").strip().lower() or "cross"
    raw_order_type = str(decision.get("order_type") or decision.get("orderType") or "market").strip().lower()
    enriched["order_type"] = _order_type(decision)
    enriched["post_only"] = bool(decision.get("post_only") or decision.get("postOnly")) or raw_order_type == "post_only"
    leverage = _optional_float(decision.get("leverage") or decision.get("leverage_hint"))
    if leverage is not None:
        enriched["leverage"] = int(leverage) if leverage.is_integer() else leverage
    limit_price = _optional_float(decision.get("limit_price") or decision.get("limitPrice"))
    if enriched["order_type"] == "limit" and limit_price is not None:
        enriched["limit_price"] = limit_price
    quantity_base = _order_quantity_base(state, decision)
    if quantity_base > 0:
        enriched["quantity_base"] = quantity_base
    return enriched


def _order_audit_metadata(order: dict) -> dict:
    if not order:
        return {}
    price = float(order.get("price", 0) or 0)
    quote = float(order.get("quote", 0) or 0)
    quantity_base = float(order.get("quantity_base") or 0)
    if quantity_base <= 0 and price > 0 and quote > 0:
        quantity_base = round(quote / price, 8)
    order_type = str(order.get("order_type") or "").strip().lower()
    post_only = bool(order.get("post_only", False)) or order_type == "post_only"
    return {
        "action": order.get("action"),
        "orderType": order.get("order_type"),
        "positionSide": order.get("position_side"),
        "reduceOnly": bool(order.get("reduce_only", False)),
        "tdMode": order.get("td_mode"),
        "leverage": order.get("leverage"),
        "limitPrice": order.get("limit_price"),
        "quantityBase": quantity_base,
        "postOnly": post_only,
        "okxEnhancedExecution": order_type in {"limit", "post_only"}
        or bool(order.get("okx_enhanced_execution", False)),
    }


def _business_status_from_order_status(order_status: str) -> str:
    normalized = str(order_status or "").upper()
    if normalized == "FILLED":
        return "filled"
    if normalized in {"NEW", "PENDING"}:
        return "pending"
    if normalized == "PARTIALLY_FILLED":
        return "partial"
    if normalized == "CANCELED":
        return "canceled"
    if normalized == "EXPIRED":
        return "expired"
    if normalized in {"REJECTED"}:
        return "failed"
    return normalized.lower() if normalized else "pending"


def _strategy_user_id(state: DecisionState) -> int | None:
    strategy_context = state.get("strategy_context")
    if not isinstance(strategy_context, dict):
        return None
    raw_value = strategy_context.get("user_id")
    if raw_value in (None, ""):
        raw_value = strategy_context.get("userId")
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _normalize_execution_status_pair(execution_result: dict) -> dict:
    normalized = dict(execution_result)
    status = str(normalized.get("status") or "").strip().lower()
    order_status = str(normalized.get("order_status") or "").strip().upper()
    if not status and order_status:
        status = _business_status_from_order_status(order_status)
    if not status:
        status = "pending"
    if not order_status:
        order_status = _BUSINESS_TO_ORDER_STATUS.get(status, status.upper())
    normalized["status"] = status
    normalized["order_status"] = order_status
    return normalized


def _post_exchange_order_callback(state: DecisionState, side: str) -> None:
    callback_client = state.get("callback_client")
    if callback_client is None or not hasattr(callback_client, "post_exchange_order"):
        return
    execution_result = state.get("execution_result") or {}
    order = state.get("last_order") or {}
    fill_quantity = _execution_float(execution_result, "fill_quantity")
    fill_price = _execution_float(execution_result, "fill_price")
    execution_timestamp = state.get("executedAt")
    raw_payload = json.dumps(
        {"order": order, "execution_result": execution_result},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    callback_client.post_exchange_order(
        {
            "traceId": state.get("trace_id", ""),
            "exchangeCode": state.get("exchange", "binance"),
            "symbol": state.get("symbol", ""),
            "side": side,
            "mode": state.get("mode", "paper"),
            "orderRef": execution_result.get("order_id", ""),
            "clientOrderId": order.get("client_id") or order.get("trace_id") or state.get("trace_id", ""),
            "filledQuantity": fill_quantity if fill_quantity > 0 else None,
            "avgFillPrice": fill_price if fill_quantity > 0 else None,
            "fee": execution_result.get("fee"),
            "feeCcy": execution_result.get("fee_ccy"),
            "status": execution_result.get("status", "pending"),
            "executionStatus": execution_result.get("status", "pending"),
            "orderStatus": execution_result.get("order_status", "PENDING"),
            "updatedAt": execution_timestamp,
            "filledAt": execution_timestamp if fill_quantity > 0 else None,
            "rawPayload": raw_payload,
            **_order_audit_metadata(order),
        }
    )


def _post_paper_trade_order_callback(state: DecisionState, side: str, quote_amount: float) -> None:
    callback_client = state.get("callback_client")
    if callback_client is None or not hasattr(callback_client, "post_paper_trade_order"):
        return
    if str(state.get("mode", "")).strip().lower() != "paper":
        return
    execution_result = state.get("execution_result") or {}
    callback_client.post_paper_trade_order(
        {
            "traceId": state.get("trace_id", ""),
            "exchangeCode": state.get("exchange", "binance"),
            "symbol": state.get("symbol", ""),
            "side": side,
            "mode": state.get("mode", "paper"),
            "orderRef": execution_result.get("order_id", ""),
            "quoteAmount": quote_amount,
            "status": execution_result.get("status", "pending"),
            "executionStatus": execution_result.get("status", "pending"),
            "orderStatus": execution_result.get("order_status", "PENDING"),
            **_order_audit_metadata(state.get("last_order") or {}),
        }
    )


def execution_node(state: DecisionState) -> DecisionState:
    """执行节点

    根据主管决策执行交易订单。

    流程：
    1. 检查决策动作（SKIP/HOLD直接返回）
    2. 检查风控结果
    3. 构建订单参数
    4. 调用执行路由器下单
    5. 更新仓位状态（paper模式计算模拟盈亏）
    6. 发送回调通知

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含execution_result
    """
    stamp_state_timestamp(state, "executedAt")
    decision = state.get("supervisor_decision") or {}
    action = str(decision.get("action") or "").strip().upper()
    side = _decision_side(state, decision)
    risk_result = state.get("risk_result") or {"passed": True, "reason": "pass"}
    if action in {"SKIP", "HOLD"}:
        state["execution_result"] = _normalize_execution_status_pair(
            {"status": "skipped", "reason": "hold" if action == "HOLD" else "skip"}
        )
        _post_exchange_order_callback(state, side)
        return state
    if not risk_result.get("passed", False):
        state["execution_result"] = _normalize_execution_status_pair(
            {
                "status": "blocked",
                "reason": risk_result.get("reason", "risk_blocked"),
            }
        )
        _post_exchange_order_callback(state, side)
        return state

    account_equity = float(state.get("account_equity", 10_000))
    order = {
        "symbol": state.get("symbol", ""),
        "side": side,
        "quote": _order_quote_amount(state, decision, account_equity),
        "trace_id": state.get("trace_id", ""),
        "price": _runtime_execution_price(state),
    }
    order = _enrich_order_metadata(state, decision, order)
    state["last_order"] = order
    if float(order["quote"] or 0.0) <= 0:
        state["execution_result"] = _normalize_execution_status_pair(
            {
                "status": "skipped",
                "reason": "zero_quote_order",
            }
        )
        _post_exchange_order_callback(state, side)
        return state
    execution_router = state.get("execution_router") or _default_execution_router()
    state["execution_result"] = _normalize_execution_status_pair(
        _enrich_execution_result(
            state,
            execution_router.execute(
                mode=state.get("mode", "paper"),
                exchange=state.get("exchange", "binance"),
                order=order,
            ),
        ),
    )
    callback_client = state.get("callback_client")
    if callback_client is not None and hasattr(callback_client, "post_order_request"):
        callback_client.post_order_request(
            {
                "traceId": state.get("trace_id", ""),
                "exchangeCode": state.get("exchange", "binance"),
                "symbol": order["symbol"],
                "side": side,
                "mode": state.get("mode", "paper"),
                "quoteAmount": order["quote"],
                **_order_audit_metadata(order),
            }
        )
    _post_exchange_order_callback(state, side)
    _post_paper_trade_order_callback(state, side, order["quote"])
    fill_price = _execution_float(state["execution_result"], "fill_price", order["price"])
    fill_quantity = _execution_float(state["execution_result"], "fill_quantity")
    snapshot_side = _position_snapshot_side(state, decision)
    had_position = _has_position(state.get("current_position_side"), state.get("current_position_quantity"))
    resulting_position_side = snapshot_side
    if _should_post_position_snapshot(state["execution_result"], fill_quantity):
        position_effects = _filled_position_effects(state, decision, fill_price, fill_quantity)
        state["execution_result"]["position_quantity"] = position_effects["position_quantity"]
        state["execution_result"]["entry_price"] = position_effects["entry_price"]
        state["execution_result"]["unrealized_pnl"] = position_effects["unrealized_pnl"]
        state["execution_result"]["realized_pnl"] = position_effects["realized_pnl"]
        state["execution_result"]["realized_pnl_delta"] = position_effects["realized_pnl_delta"]
        # 更新 account_equity 以反映已实现盈亏
        current_account_equity = float(state.get("account_equity", 10_000))
        realized_pnl_delta = position_effects["realized_pnl_delta"]
        new_account_equity = round(current_account_equity + realized_pnl_delta, 8)
        account_metrics = _recalculate_account_metrics(state, new_account_equity)
        state["execution_result"]["account_equity"] = new_account_equity
        state["execution_result"]["daily_pnl"] = account_metrics["daily_pnl"]
        state["execution_result"]["max_drawdown_pct"] = account_metrics["max_drawdown_pct"]
        state["execution_result"]["peak_account_equity"] = account_metrics["peak_account_equity"]
        state["account_equity"] = new_account_equity
        state["daily_pnl"] = account_metrics["daily_pnl"]
        state["max_drawdown_pct"] = account_metrics["max_drawdown_pct"]
        state["peak_account_equity"] = account_metrics["peak_account_equity"]
        position_quantity = position_effects["position_quantity"]
        entry_price = position_effects["entry_price"]
        unrealized_pnl = position_effects["unrealized_pnl"]
        state["current_position_quantity"] = position_quantity
        state["current_position_notional"] = position_effects["current_position_notional"]
        state["current_position_side"] = position_effects["current_position_side"]
        state["realized_pnl"] = position_effects["realized_pnl"]
        state["unrealized_pnl"] = unrealized_pnl
        state["entry_price"] = entry_price
        resulting_position_side = position_effects["current_position_side"]
    else:
        position_quantity = _resulting_position_quantity(state, decision, state["execution_result"], fill_quantity)
        entry_price = 0.0 if position_quantity == 0 else _execution_float(state["execution_result"], "entry_price", fill_price)
        unrealized_pnl = _calculate_unrealized_pnl(
            snapshot_side,
            position_quantity,
            entry_price,
            _runtime_execution_price(state) or fill_price,
        )
        resulting_position_side = "flat" if position_quantity <= 0 else snapshot_side
    _sync_current_position_opened_at(
        state,
        had_position=had_position,
        resulting_side=resulting_position_side,
        resulting_quantity=position_quantity,
    )
    if callback_client is not None and hasattr(callback_client, "post_exchange_fill") and fill_price > 0 and fill_quantity > 0:
        order_ref = state["execution_result"].get("order_id", "")
        fill_payload = {
            "traceId": state.get("trace_id", ""),
            "exchangeCode": state.get("exchange", "binance"),
            "symbol": order.get("symbol", state.get("symbol", "")),
            "side": side,
            "positionSide": order.get("position_side") or snapshot_side,
            "orderRef": order_ref,
            "tradeId": state["execution_result"].get("trade_id") or f"{order_ref}-fill",
            "fillPrice": fill_price,
            "fillQuantity": fill_quantity,
            "fee": state["execution_result"].get("fee"),
            "feeCcy": state["execution_result"].get("fee_ccy"),
            "isMaker": state["execution_result"].get("is_maker"),
            "execType": state["execution_result"].get("exec_type"),
            "realizedPnl": state["execution_result"].get("realized_pnl_delta"),
            "filledAt": state.get("executedAt"),
            "rawPayload": json.dumps(
                {"order": order, "execution_result": state["execution_result"]},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }
        callback_client.post_exchange_fill(fill_payload)
    if (
        callback_client is not None
        and hasattr(callback_client, "post_position_snapshot")
        and _should_post_position_snapshot(state["execution_result"], fill_quantity)
    ):
        user_id = _strategy_user_id(state)
        # 对于OPEN操作，使用当前决策的trace_id
        # Keep traceId as the current decision trace for auditability.
        # Carry entryTraceId separately to link ADD/REDUCE/CLOSE snapshots to the original OPEN.
        position_trace_id = state.get("trace_id", "")
        entry_trace_id = state.get("entry_trace_id") or state.get("entryTraceId")
        if action in {"OPEN_LONG", "OPEN_SHORT"} or not entry_trace_id:
            entry_trace_id = position_trace_id
        callback_client.post_position_snapshot(
            {
                "traceId": position_trace_id,
                "entryTraceId": entry_trace_id,
                "exchangeCode": state.get("exchange", "binance"),
                "symbol": order["symbol"],
                "side": snapshot_side,
                "positionQuantity": position_quantity,
                "entryPrice": entry_price,
                "unrealizedPnl": unrealized_pnl,
                **({"userId": user_id} if user_id is not None else {}),
            }
        )
        # 更新state中的unrealized_pnl，供audit_node使用
        state["unrealized_pnl"] = unrealized_pnl
    return state
