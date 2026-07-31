"""
仓位守卫模块

实现仓位保护功能，包括：
- 止损触发检查
- 止盈触发检查
- 最大持仓时间检查

当触发条件满足时，自动生成平仓订单。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数

    Args:
        value: 待转换值
        default: 默认值

    Returns:
        float: 转换后的浮点数
    """
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_ratio(position_guard: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key not in position_guard:
            continue
        value = position_guard.get(key)
        if value in (None, ""):
            continue
        return max(_to_float(value), 0.0)
    return 0.0


def _thresholds_payload(stop_loss_ratio: float, take_profit_ratio: float) -> dict[str, Any]:
    thresholds: dict[str, Any] = {"threshold_unit": "ratio"}
    if stop_loss_ratio > 0:
        thresholds["stop_loss_ratio"] = stop_loss_ratio
        thresholds["stop_loss_percent"] = round(stop_loss_ratio * 100, 8)
    if take_profit_ratio > 0:
        thresholds["take_profit_ratio"] = take_profit_ratio
        thresholds["take_profit_percent"] = round(take_profit_ratio * 100, 8)
    return thresholds

def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    raw = str(value).strip()
    if not raw:
        return None
    candidates = (
        raw.replace("Z", "+00:00"),
        raw.replace(" ", "T"),
        raw.replace(" ", "T").replace("Z", "+00:00"),
    )
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _market_price(market_payload: dict[str, Any] | None) -> float:
    if not isinstance(market_payload, dict):
        return 0.0
    return _to_float(market_payload.get("price"))


def _entry_price(account_context: dict[str, Any] | None) -> float:
    if not isinstance(account_context, dict):
        return 0.0
    quantity = _to_float(account_context.get("current_position_quantity"))
    if quantity <= 0:
        return 0.0
    notional = _to_float(account_context.get("current_position_notional"))
    if notional > 0:
        return notional / quantity
    return _to_float(account_context.get("entry_price"))


def _holding_minutes(account_context: dict[str, Any] | None, now: datetime) -> float | None:
    if not isinstance(account_context, dict):
        return None
    opened_at = _parse_datetime(account_context.get("current_position_opened_at"))
    if opened_at is None:
        return None
    normalized_now = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    return max((normalized_now - opened_at).total_seconds() / 60.0, 0.0)


def evaluate_position_guard(
    *,
    account_context: dict[str, Any] | None,
    position_guard: dict[str, Any] | None,
    market_payload: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    """评估仓位守卫条件

    检查是否触发止损、止盈或最大持仓时间。

    Args:
        account_context: 账户上下文
        position_guard: 仓位守卫配置
        market_payload: 市场数据
        now: 当前时间

    Returns:
        dict[str, Any]: 评估结果，包含triggered、reason等字段
    """
    result = {
        "triggered": False,
        "reason": None,
        "current_price": _market_price(market_payload),
        "entry_price": _entry_price(account_context),
        "holding_minutes": _holding_minutes(account_context, now),
    }
    if not isinstance(position_guard, dict):
        return result
    stop_loss_ratio = _resolve_ratio(position_guard, "stop_loss_ratio", "stopLossRatio", "stop_loss_pct", "stopLossPct")
    take_profit_ratio = _resolve_ratio(position_guard, "take_profit_ratio", "takeProfitRatio", "take_profit_pct", "takeProfitPct")
    result["thresholds"] = _thresholds_payload(stop_loss_ratio, take_profit_ratio)
    if not bool(position_guard.get("enabled", True)):
        return result
    if not isinstance(account_context, dict):
        return result
    side = str(account_context.get("current_position_side") or "").strip().lower()
    quantity = _to_float(account_context.get("current_position_quantity"))
    if side not in {"long", "short"} or quantity <= 0:
        return result

    current_price = result["current_price"]
    entry_price = result["entry_price"]
    max_holding_minutes = _to_float(position_guard.get("max_holding_minutes"))

    if entry_price > 0 and current_price > 0 and stop_loss_ratio > 0:
        if side == "long" and current_price <= entry_price * (1 - stop_loss_ratio):
            result["triggered"] = True
            result["reason"] = "stop_loss_pct"
            return result
        if side == "short" and current_price >= entry_price * (1 + stop_loss_ratio):
            result["triggered"] = True
            result["reason"] = "stop_loss_pct"
            return result

    if entry_price > 0 and current_price > 0 and take_profit_ratio > 0:
        if side == "long" and current_price >= entry_price * (1 + take_profit_ratio):
            result["triggered"] = True
            result["reason"] = "take_profit_pct"
            return result
        if side == "short" and current_price <= entry_price * (1 - take_profit_ratio):
            result["triggered"] = True
            result["reason"] = "take_profit_pct"
            return result

    holding_minutes = result["holding_minutes"]
    if holding_minutes is not None and max_holding_minutes > 0 and holding_minutes >= max_holding_minutes:
        result["triggered"] = True
        result["reason"] = "max_holding_minutes"
        return result

    return result


def build_guard_close_order(
    *,
    trace_id: str,
    symbol: str,
    account_context: dict[str, Any] | None,
    market_payload: dict[str, Any] | None,
    trigger_reason: str,
) -> dict[str, Any]:
    """构建守卫平仓订单

    根据当前仓位信息构建平仓订单。

    Args:
        trace_id: 追踪ID
        symbol: 交易品种
        account_context: 账户上下文
        market_payload: 市场数据
        trigger_reason: 触发原因

    Returns:
        dict[str, Any]: 订单信息
    """
    side = str((account_context or {}).get("current_position_side") or "").strip().lower()
    current_price = _market_price(market_payload)
    quantity = _to_float((account_context or {}).get("current_position_quantity"))
    entry_price = _entry_price(account_context)
    execution_price = current_price if current_price > 0 else entry_price
    quote_amount = quantity * execution_price if quantity > 0 and execution_price > 0 else 0.0
    td_mode = str((account_context or {}).get("td_mode") or "cross").strip().lower() or "cross"
    return {
        "symbol": symbol,
        "side": "SELL" if side == "long" else "BUY",
        "quote": round(quote_amount, 8),
        "trace_id": trace_id,
        "price": execution_price,
        "action": "CLOSE",
        "order_type": "market",
        "position_side": side,
        "reduce_only": True,
        "td_mode": td_mode,
        "quantity_base": round(quantity, 8),
        "reason": f"position_guard:{trigger_reason}",
    }
