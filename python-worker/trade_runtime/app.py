"""
交易运行时应用模块

提供交易运行时的核心应用逻辑，包括配置管理、执行路由构建、运行时上下文管理等。

核心流程:
1. 数据摄入: 从多个数据源(市场行情、新闻、链上、社交)收集实时数据
2. 触发评估: 根据触发策略判断是否应该触发交易决策
3. 决策执行: 通过决策图(Decision Graph)执行多Agent协作决策
4. 风控检查: 对决策结果进行风险控制检查
5. 订单执行: 将决策转化为实际订单并执行

运行模式:
- paper: 模拟交易模式，不实际下单
- shadow: 影子模式，记录决策但不执行
- live: 实盘模式，实际下单执行
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import redis

from trade_runtime.callback_client import RuntimeCallbackClient
from trade_runtime.config import RuntimeExchangeAccount
from trade_runtime.config_client import RuntimeConfigClient
from trade_runtime.decision.model_client import DecisionModelClient
from trade_runtime.event_client import RuntimeEventClient
from trade_runtime.execution.clients import BinanceRestExecutionClient
from trade_runtime.execution.clients import OkxRestExecutionClient
from trade_runtime.execution.order_sync import OkxOrderSyncService
from trade_runtime.account_equity import AccountEquitySync
from trade_runtime.execution.router import ExecutionRouter
from trade_runtime.ingestion.binance_ws import BinanceWsMarketFeed
from trade_runtime.ingestion.okx_ws import OkxWsMarketFeed
from trade_runtime.memory.consolidation import HttpDecisionHistoryClient, LongTermMemoryConsolidationJob
from trade_runtime.memory.long_term import HybridLongTermMemoryStore, HttpLongTermMemoryStore, McpLongTermMemoryStore
from trade_runtime.memory.trade_lifecycle import TradeLifecycleClient, TradeLifecycleManager
from trade_runtime.replay_client import TradeReplayClient
from trade_runtime.replay_runner import TradeReplayRunner
from trade_runtime.route_scheduler import RouteScheduler, RouteSchedulerConfig, RouteTask
from trade_runtime.route_session import RouteSession
from trade_runtime.position_guard import build_guard_close_order, evaluate_position_guard
from trade_runtime.position_risk_watcher import resolve_position_risk_watcher_config
from trade_runtime.source_config_client import SourceConfigClient
from trade_runtime.task_queue_client import RuntimeTaskQueueClient
from trade_runtime.runtime_inputs import (
    BinancePublicMarketFeed,
    HttpJsonFeedSupplier,
    OkxPublicMarketFeed,
    RuntimeInputAssembler,
)
from trade_runtime.runtime_runner import TradeRuntimeRunner
from trade_runtime.stream_consumer import StreamConsumer
from trade_runtime.streams import StreamPublisher


logger = logging.getLogger(__name__)
DEFAULT_AUX_FEED_TIMEOUT_SECONDS = 15


def _default_event_bundle() -> list[dict[str, Any]]:
    """
    返回默认的事件包列表
    
    Returns:
        list[dict[str, Any]]: 空事件包列表
    """
    return []


def _default_feature_snapshot() -> dict[str, Any]:
    """
    返回默认的特征快照字典
    
    Returns:
        dict[str, Any]: 空特征快照字典
    """
    return {}


def _parse_bool(value: str | None) -> bool:
    """
    将字符串值解析为布尔值

    Args:
        value: 待解析的字符串值

    Returns:
        bool: 解析后的布尔值
    """
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_enabled_flag(value: Any, *, default: bool = True) -> bool:
    """
    检查值是否为启用标志

    Args:
        value: 待检查的值
        default: 默认值

    Returns:
        bool: 是否为启用状态
    """
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _runtime_config_value(runtime_config: Any, *keys: str) -> Any:
    """
    浠庤繍琛屾椂閰嶇疆涓鍙栧瓧娈靛€?

    Args:
        runtime_config: 杩愯鏃堕厤缃璞?
        keys: 鍊欓€夊瓧娈靛悕

    Returns:
        Any: 鍖归厤鍒扮殑鍊硷紝鏈懡涓椂杩斿洖None
    """
    if runtime_config is None:
        return None
    for key in keys:
        value = runtime_config.get(key) if isinstance(runtime_config, dict) else getattr(runtime_config, key, None)
        if value not in (None, ""):
            return value
    return None


def _normalize_route_scheduler_mode(value: Any) -> str:
    """
    鏍囧噯鍖栬矾鐢辫皟搴︽ā寮?

    Args:
        value: 璋冨害妯″紡鍊?

    Returns:
        str: 鏍囧噯鍖栧悗鐨勮皟搴︽ā寮?
    """
    normalized = str(value or "SERIAL").strip().upper()
    return normalized if normalized in {"SERIAL", "THREAD_POOL"} else "SERIAL"


def _normalize_route_max_concurrency(value: Any) -> int:
    """
    鏍囧噯鍖栬矾鐢辨渶澶у苟鍙戞暟

    Args:
        value: 骞跺彂鍊?

    Returns:
        int: 鏈夋晥鐨勫苟鍙戞暟
    """
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


def _latest_market_price(event_bundle: list[dict[str, Any]] | None) -> float:
    for event in reversed(event_bundle or []):
        if event.get("event_type") != "market_tick":
            continue
        try:
            price = float(event.get("price"))
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
    return 0.0


def _position_risk_close_price(result: dict[str, Any] | None, event_bundle: list[dict[str, Any]] | None) -> float:
    position_risk_result = (result or {}).get("position_risk_result")
    if isinstance(position_risk_result, dict):
        context = position_risk_result.get("position_risk_context")
        if isinstance(context, dict):
            try:
                current_price = float(context.get("current_price") or 0.0)
            except (TypeError, ValueError):
                current_price = 0.0
            if current_price > 0:
                return current_price
    for event in reversed(event_bundle or []):
        if str(event.get("event_type") or "").strip().lower() != "market_metric":
            continue
        try:
            price = float(event.get("effective_price") or event.get("latest_price") or 0.0)
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
    return _latest_market_price(event_bundle)


def _normalize_execution_result(execution_result: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(execution_result or {})
    status = str(normalized.get("status") or "").strip().lower()
    order_status = str(normalized.get("order_status") or "").strip().upper()
    if not status and order_status == "FILLED":
        status = "filled"
    elif not status and order_status == "SKIPPED":
        status = "skipped"
    elif not status and order_status == "BLOCKED":
        status = "blocked"
    elif not status and order_status:
        status = order_status.lower()
    if not status:
        status = "pending"
    if not order_status:
        order_status = status.upper()
    normalized["status"] = status
    normalized["order_status"] = order_status
    return normalized


def _should_run_position_guard(result: dict[str, Any] | None) -> bool:
    payload = result or {}
    action = str(((payload.get("supervisor_decision") or {}).get("action") or "")).strip().upper()
    if action in {"", "SKIP", "HOLD"}:
        return True
    execution_status = str(((payload.get("execution_result") or {}).get("status") or "")).strip().lower()
    return execution_status in {"skipped", "blocked"}


def _guard_callback_client(runner: Any) -> Any | None:
    return getattr(runner, "callback_client", None)


def _runtime_account_context_payload(runtime_account_context: Any) -> dict[str, Any]:
    if isinstance(runtime_account_context, dict):
        return dict(runtime_account_context)
    if runtime_account_context is None:
        return {}
    payload = {
        "account_equity": getattr(runtime_account_context, "account_equity", None),
        "daily_pnl": getattr(runtime_account_context, "daily_pnl", None),
        "realized_pnl": getattr(runtime_account_context, "realized_pnl", None),
        "unrealized_pnl": getattr(runtime_account_context, "unrealized_pnl", None),
        "current_position_side": getattr(runtime_account_context, "current_position_side", None),
        "current_position_quantity": getattr(runtime_account_context, "current_position_quantity", None),
        "current_position_notional": getattr(runtime_account_context, "current_position_notional", None),
        "entry_price": getattr(runtime_account_context, "entry_price", None),
        "max_drawdown_pct": getattr(runtime_account_context, "max_drawdown_pct", None),
        "peak_account_equity": getattr(runtime_account_context, "peak_account_equity", None),
        "current_position_opened_at": getattr(runtime_account_context, "current_position_opened_at", None),
        "current_time": getattr(runtime_account_context, "current_time", None),
        "current_position_holding_minutes": getattr(runtime_account_context, "current_position_holding_minutes", None),
        "consecutive_failures": getattr(runtime_account_context, "consecutive_failures", None),
        "entry_trace_id": getattr(runtime_account_context, "entry_trace_id", None),
    }
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }


def _has_active_position(runtime_account_context: Any) -> bool:
    payload = _runtime_account_context_payload(runtime_account_context)
    side = str(payload.get("current_position_side") or "").strip().lower()
    try:
        quantity = float(payload.get("current_position_quantity") or 0.0)
    except (TypeError, ValueError):
        quantity = 0.0
    return side in {"long", "short"} and quantity > 0


def _guard_position_side(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"buy", "long", "bullish"}:
        return "long"
    if normalized in {"sell", "short", "bearish"}:
        return "short"
    if normalized in {"flat", "hold", "skip", "none", "neutral", ""}:
        return "flat"
    return normalized


def _guard_entry_price(account_context: dict[str, Any] | None) -> float:
    if not isinstance(account_context, dict):
        return 0.0
    entry_price = float(account_context.get("entry_price") or 0.0)
    if entry_price > 0:
        return entry_price
    quantity = float(account_context.get("current_position_quantity") or 0.0)
    notional = float(account_context.get("current_position_notional") or 0.0)
    if quantity > 0 and notional > 0:
        return round(notional / quantity, 8)
    return 0.0


def _guard_realized_pnl_delta(position_side: str, entry_price: float, fill_price: float, closed_quantity: float) -> float:
    if closed_quantity <= 0 or entry_price <= 0 or fill_price <= 0:
        return 0.0
    if position_side == "long":
        return round((fill_price - entry_price) * closed_quantity, 8)
    if position_side == "short":
        return round((entry_price - fill_price) * closed_quantity, 8)
    return 0.0


def _guard_unrealized_pnl(position_side: str, position_quantity: float, entry_price: float, current_price: float) -> float:
    if position_quantity <= 0 or entry_price <= 0 or current_price <= 0:
        return 0.0
    if position_side == "long":
        return round((current_price - entry_price) * position_quantity, 8)
    if position_side == "short":
        return round((entry_price - current_price) * position_quantity, 8)
    return 0.0


def _guard_drawdown_pct(peak_account_equity: float, account_equity: float) -> float:
    if peak_account_equity <= 0:
        return 0.0
    return round(max((peak_account_equity - account_equity) / peak_account_equity, 0.0) * 100.0, 8)


def _guard_order_audit_metadata(order: dict[str, Any]) -> dict[str, Any]:
    if not order:
        return {}
    price = float(order.get("price") or 0.0)
    quote = float(order.get("quote") or 0.0)
    quantity_base = float(order.get("quantity_base") or 0.0)
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


def _enrich_position_guard_execution_result(
    *,
    mode: str,
    order: dict[str, Any],
    execution_result: dict[str, Any],
    account_context: dict[str, Any] | None,
) -> dict[str, Any]:
    enriched = dict(execution_result or {})
    normalized_mode = str(mode or "").strip().lower()
    execution_status = str(enriched.get("status") or "").strip().lower()
    fill_price = float(enriched.get("fill_price") or 0.0)
    fill_quantity = float(enriched.get("fill_quantity") or 0.0)
    if execution_status in {"pending", "submitted", "failed", "blocked", "skipped", "canceled", "expired"} or fill_quantity <= 0:
        return enriched
    account_payload = dict(account_context or {})
    position_side = _guard_position_side(account_payload.get("current_position_side"))
    current_quantity = float(account_payload.get("current_position_quantity") or 0.0)
    entry_price = _guard_entry_price(account_payload)
    resulting_quantity = round(max(current_quantity - fill_quantity, 0.0), 8)
    current_price = fill_price or float(order.get("price") or 0.0)
    resulting_entry_price = 0.0 if resulting_quantity <= 0 else entry_price
    unrealized_pnl = _guard_unrealized_pnl(position_side, resulting_quantity, resulting_entry_price, current_price)
    enriched["position_quantity"] = resulting_quantity
    enriched["entry_price"] = resulting_entry_price
    enriched["unrealized_pnl"] = unrealized_pnl
    enriched["current_position_side"] = "flat" if resulting_quantity <= 0 else position_side
    closed_quantity = min(max(current_quantity, 0.0), fill_quantity)
    realized_pnl_delta = _guard_realized_pnl_delta(position_side, entry_price, fill_price, closed_quantity)
    realized_pnl = round(float(account_payload.get("realized_pnl") or 0.0) + realized_pnl_delta, 8)
    current_account_equity = float(account_payload.get("account_equity") or 10_000.0)
    current_daily_pnl = float(account_payload.get("daily_pnl") or 0.0)
    daily_pnl_basis_equity = round(current_account_equity - current_daily_pnl, 8)
    account_equity = round(current_account_equity + realized_pnl_delta, 8)
    peak_account_equity = float(account_payload.get("peak_account_equity") or 0.0)
    if peak_account_equity <= 0:
        peak_account_equity = round(current_account_equity, 8)
    peak_account_equity = round(max(peak_account_equity, account_equity), 8)
    max_drawdown_pct = round(
        max(
            float(account_payload.get("max_drawdown_pct") or 0.0),
            _guard_drawdown_pct(peak_account_equity, account_equity),
        ),
        8,
    )
    enriched["realized_pnl"] = realized_pnl
    enriched["realized_pnl_delta"] = realized_pnl_delta
    enriched["account_equity"] = account_equity
    enriched["daily_pnl"] = round(account_equity - daily_pnl_basis_equity, 8)
    enriched["max_drawdown_pct"] = max_drawdown_pct
    enriched["peak_account_equity"] = peak_account_equity
    return enriched


def _post_position_guard_callbacks(
    *,
    callback_client: Any | None,
    trace_id: str,
    exchange: str,
    mode: str,
    order: dict[str, Any],
    execution_result: dict[str, Any],
    account_context: dict[str, Any] | None,
    user_id: int | None = None,
) -> None:
    if callback_client is None:
        return
    normalized_mode = str(mode or "").strip().lower()
    audit_metadata = _guard_order_audit_metadata(order)
    if hasattr(callback_client, "post_order_request"):
        callback_client.post_order_request(
            {
                "traceId": trace_id,
                "exchangeCode": exchange,
                "symbol": order.get("symbol", ""),
                "side": order.get("side", ""),
                "mode": mode,
                "quoteAmount": order.get("quote", 0.0),
                **audit_metadata,
            }
        )
    if hasattr(callback_client, "post_exchange_order"):
        fill_quantity = float(execution_result.get("fill_quantity") or 0.0)
        fill_price = float(execution_result.get("fill_price") or 0.0)
        execution_timestamp = execution_result.get("filledAt") or execution_result.get("executedAt")
        callback_client.post_exchange_order(
            {
                "traceId": trace_id,
                "exchangeCode": exchange,
                "symbol": order.get("symbol", ""),
                "side": order.get("side", ""),
                "mode": mode,
                "orderRef": execution_result.get("order_id", ""),
                "clientOrderId": order.get("client_id") or trace_id,
                "filledQuantity": fill_quantity if fill_quantity > 0 else None,
                "avgFillPrice": fill_price if fill_quantity > 0 else None,
                "fee": execution_result.get("fee"),
                "feeCcy": execution_result.get("fee_ccy"),
                "status": execution_result.get("status", "pending"),
                "executionStatus": execution_result.get("status", "pending"),
                "orderStatus": execution_result.get("order_status", "PENDING"),
                "updatedAt": execution_timestamp,
                "filledAt": execution_timestamp if fill_quantity > 0 else None,
                "rawPayload": json.dumps(
                    {"order": order, "execution_result": execution_result},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                **audit_metadata,
            }
        )
    if (
        normalized_mode == "paper"
        and hasattr(callback_client, "post_paper_trade_order")
    ):
        callback_client.post_paper_trade_order(
            {
                "traceId": trace_id,
                "exchangeCode": exchange,
                "symbol": order.get("symbol", ""),
                "side": order.get("side", ""),
                "mode": mode,
                "orderRef": execution_result.get("order_id", ""),
                "quoteAmount": order.get("quote", 0.0),
                "status": execution_result.get("status", "pending"),
                "executionStatus": execution_result.get("status", "pending"),
                "orderStatus": execution_result.get("order_status", "PENDING"),
                **audit_metadata,
            }
        )
    fill_price = float(execution_result.get("fill_price") or 0.0)
    fill_quantity = float(execution_result.get("fill_quantity") or 0.0)
    execution_status = str(execution_result.get("status") or "").strip().lower()
    if fill_price > 0 and fill_quantity > 0 and hasattr(callback_client, "post_exchange_fill"):
        order_ref = execution_result.get("order_id", "")
        callback_client.post_exchange_fill(
            {
                "traceId": trace_id,
                "exchangeCode": exchange,
                "symbol": order.get("symbol", ""),
                "side": order.get("side", ""),
                "positionSide": order.get("position_side") or _guard_position_side((account_context or {}).get("current_position_side")),
                "orderRef": order_ref,
                "tradeId": execution_result.get("trade_id") or f"{order_ref}-fill",
                "fillPrice": fill_price,
                "fillQuantity": fill_quantity,
                "fee": execution_result.get("fee"),
                "feeCcy": execution_result.get("fee_ccy"),
                "isMaker": execution_result.get("is_maker"),
                "execType": execution_result.get("exec_type"),
                "realizedPnl": execution_result.get("realized_pnl_delta") or execution_result.get("realized_pnl"),
                "filledAt": execution_result.get("filledAt") or execution_result.get("executedAt"),
                "rawPayload": json.dumps(
                    {"order": order, "execution_result": execution_result},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            }
        )
    if (
        fill_quantity > 0
        and execution_status not in {"pending", "submitted", "failed", "blocked", "skipped", "canceled", "expired"}
        and hasattr(callback_client, "post_pnl_snapshot")
    ):
        callback_client.post_pnl_snapshot(
            {
                "traceId": trace_id,
                "mode": mode,
                "accountEquity": execution_result.get("account_equity", float((account_context or {}).get("account_equity") or 0.0)),
                "unrealizedPnl": execution_result.get("unrealized_pnl", 0.0),
                "realizedPnl": execution_result.get("realized_pnl", float((account_context or {}).get("realized_pnl") or 0.0)),
                "dailyPnl": execution_result.get("daily_pnl", float((account_context or {}).get("daily_pnl") or 0.0)),
                "maxDrawdownPct": execution_result.get(
                    "max_drawdown_pct",
                    float((account_context or {}).get("max_drawdown_pct") or 0.0),
                ),
                "peakAccountEquity": execution_result.get(
                    "peak_account_equity",
                    float((account_context or {}).get("peak_account_equity") or 0.0),
                ),
            }
        )
    if (
        fill_quantity > 0
        and execution_status not in {"pending", "submitted", "failed", "blocked", "skipped", "canceled", "expired"}
        and hasattr(callback_client, "post_position_snapshot")
    ):
        resulting_position_quantity = float(execution_result.get("position_quantity") or 0.0)
        entry_price = float(execution_result.get("entry_price") or 0.0)
        position_entry_trace_id = str(
            (account_context or {}).get("entry_trace_id")
            or (account_context or {}).get("entryTraceId")
            or trace_id
        )
        callback_client.post_position_snapshot(
            {
                "traceId": trace_id,
                "entryTraceId": position_entry_trace_id,
                "exchangeCode": exchange,
                "symbol": order.get("symbol", ""),
                "side": _guard_position_side((account_context or {}).get("current_position_side")),
                "positionQuantity": resulting_position_quantity,
                "entryPrice": entry_price,
                "unrealizedPnl": execution_result.get("unrealized_pnl", 0.0),
                **({"userId": user_id} if user_id is not None else {}),
            }
        )


def _position_guard_value(position_guard: Any, *keys: str) -> Any:
    for key in keys:
        if isinstance(position_guard, dict) and key not in position_guard:
            continue
        value = position_guard.get(key) if isinstance(position_guard, dict) else getattr(position_guard, key, None)
        if value not in (None, ""):
            return value
    return None


def _position_guard_ratio(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _position_guard_percent(ratio: float | None) -> float | None:
    if ratio is None:
        return None
    return round(ratio * 100, 8)


def _build_position_guard_context(position_guard: Any) -> dict[str, Any] | None:
    if position_guard is None:
        return None
    stop_loss_ratio = _position_guard_ratio(
        _position_guard_value(position_guard, "stop_loss_ratio", "stopLossRatio", "stop_loss_pct", "stopLossPct")
    )
    take_profit_ratio = _position_guard_ratio(
        _position_guard_value(position_guard, "take_profit_ratio", "takeProfitRatio", "take_profit_pct", "takeProfitPct")
    )
    payload = {
        "id": _position_guard_value(position_guard, "id"),
        "guard_name": _position_guard_value(position_guard, "guard_name", "guardName"),
        "scope_type": _position_guard_value(position_guard, "scope_type", "scopeType"),
        "strategy_id": _position_guard_value(position_guard, "strategy_id", "strategyId"),
        "symbol": _position_guard_value(position_guard, "symbol"),
        "exchange_code": _position_guard_value(position_guard, "exchange_code", "exchangeCode"),
        "stop_loss_pct": stop_loss_ratio,
        "take_profit_pct": take_profit_ratio,
        "stop_loss_ratio": stop_loss_ratio,
        "stop_loss_percent": _position_guard_percent(stop_loss_ratio),
        "take_profit_ratio": take_profit_ratio,
        "take_profit_percent": _position_guard_percent(take_profit_ratio),
        "threshold_unit": "ratio" if stop_loss_ratio is not None or take_profit_ratio is not None else None,
        "max_holding_minutes": _position_guard_value(position_guard, "max_holding_minutes", "maxHoldingMinutes"),
        "enabled": _position_guard_value(position_guard, "enabled"),
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def build_stream_publisher(env: Mapping[str, str] | None = None) -> StreamPublisher | None:
    """
    构建流发布器

    Args:
        env: 环境变量映射

    Returns:
        StreamPublisher | None: 流发布器实例或None
    """
    source = env or os.environ
    stream_name = (source.get("TRADE_RUNTIME_STREAM_NAME") or "").strip()
    if not stream_name:
        return None
    redis_client = redis.Redis(
        host=(source.get("TRADE_RUNTIME_REDIS_HOST") or source.get("REDIS_HOST") or "localhost").strip(),
        port=int(source.get("TRADE_RUNTIME_REDIS_PORT") or source.get("REDIS_PORT") or "6379"),
        db=int(source.get("TRADE_RUNTIME_REDIS_DB") or source.get("REDIS_DB") or "0"),
        password=(source.get("TRADE_RUNTIME_REDIS_PASSWORD") or source.get("REDIS_PASSWORD") or None),
        decode_responses=True,
    )
    return StreamPublisher(redis_client=redis_client, stream_name=stream_name)


def build_stream_consumer(
    event_client: RuntimeEventClient,
    env: Mapping[str, str] | None = None,
) -> StreamConsumer | None:
    source = env or os.environ
    stream_name = (source.get("TRADE_RUNTIME_STREAM_NAME") or "").strip()
    if not stream_name:
        return None
    redis_client = redis.Redis(
        host=(source.get("TRADE_RUNTIME_REDIS_HOST") or source.get("REDIS_HOST") or "localhost").strip(),
        port=int(source.get("TRADE_RUNTIME_REDIS_PORT") or source.get("REDIS_PORT") or "6379"),
        db=int(source.get("TRADE_RUNTIME_REDIS_DB") or source.get("REDIS_DB") or "0"),
        password=(source.get("TRADE_RUNTIME_REDIS_PASSWORD") or source.get("REDIS_PASSWORD") or None),
        decode_responses=True,
    )
    group_name = (source.get("TRADE_RUNTIME_STREAM_GROUP") or "trade-runtime.persist").strip()
    consumer_name = (
        source.get("TRADE_RUNTIME_STREAM_CONSUMER")
        or source.get("TRADE_RUNTIME_WORKER_ID")
        or source.get("WORKER_ID")
        or f"trade-runtime-{os.getpid()}"
    ).strip()
    dead_letter_stream = (source.get("TRADE_RUNTIME_STREAM_DLQ") or f"{stream_name}.dlq").strip()
    max_retries = int(source.get("TRADE_RUNTIME_STREAM_MAX_RETRIES") or "3")
    dedupe_ttl_seconds = int(source.get("TRADE_RUNTIME_STREAM_DEDUPE_TTL_SECONDS") or "86400")
    return StreamConsumer(
        redis_client=redis_client,
        stream_name=stream_name,
        group_name=group_name,
        consumer_name=consumer_name,
        handler=lambda event: event_client.post_event(trace_id=event.trace_id, event=event.payload),
        dead_letter_stream=dead_letter_stream,
        max_retries=max_retries,
        dedupe_ttl_seconds=dedupe_ttl_seconds,
    )


def build_execution_router(
    env: Mapping[str, str] | None = None,
    runtime_account: RuntimeExchangeAccount | None = None,
) -> ExecutionRouter:
    """
    构建执行路由器

    Args:
        env: 环境变量映射
        runtime_account: 运行时账户配置

    Returns:
        ExecutionRouter: 执行路由器实例
    """
    account_exchange = str(getattr(runtime_account, "exchange_code", "") or "").strip().lower()
    binance_api_key = (
        str(getattr(runtime_account, "api_key_ciphertext", "") or "").strip()
        if account_exchange == "binance"
        else ""
    )
    binance_api_secret = (
        str(getattr(runtime_account, "api_secret_ciphertext", "") or "").strip()
        if account_exchange == "binance"
        else ""
    )
    binance_testnet = (
        bool(getattr(runtime_account, "testnet", False))
        if account_exchange == "binance"
        else False
    )
    okx_api_key = (
        str(getattr(runtime_account, "api_key_ciphertext", "") or "").strip()
        if account_exchange == "okx"
        else ""
    )
    okx_api_secret = (
        str(getattr(runtime_account, "api_secret_ciphertext", "") or "").strip()
        if account_exchange == "okx"
        else ""
    )
    okx_passphrase = (
        str(getattr(runtime_account, "passphrase_ciphertext", "") or "").strip()
        if account_exchange == "okx"
        else ""
    )
    okx_base_url = (
        str(getattr(runtime_account, "api_base_url", "") or "").strip()
        if account_exchange == "okx" and str(getattr(runtime_account, "api_base_url", "") or "").strip()
        else "https://www.okx.com"
    )
    okx_demo_trading = (
        bool(getattr(runtime_account, "demo_trading", False))
        if account_exchange == "okx"
        else False
    )
    binance_client = None
    okx_client = None
    if binance_api_key and binance_api_secret:
        binance_client = BinanceRestExecutionClient(
            api_key=binance_api_key,
            api_secret=binance_api_secret,
            testnet=binance_testnet,
        )
    if okx_api_key and okx_api_secret and okx_passphrase:
        okx_client = OkxRestExecutionClient(
            api_key=okx_api_key,
            api_secret=okx_api_secret,
            passphrase=okx_passphrase,
            base_url=okx_base_url,
            demo_trading=okx_demo_trading,
        )
    return ExecutionRouter(binance_client=binance_client, okx_client=okx_client)


@dataclass(frozen=True)
class RuntimeAppSettings:
    """
    运行时应用配置类

    存储交易运行时的所有配置参数

    Attributes:
        base_url: 基础URL地址
        bearer_token: 认证令牌
        worker_id: 工作节点ID
        symbol: 交易品种
        exchange: 交易所代码
        news_url: 新闻数据源URL
        onchain_url: 链上数据源URL
        social_url: 社交数据源URL
        poll_interval_seconds: 轮询间隔秒数
        run_mode: 运行模式
        replay_trace_id: 回放追踪ID
    """
    base_url: str
    bearer_token: str
    worker_id: str
    default_symbol: str
    symbol: str | None
    exchange: str | None
    news_url: str
    onchain_url: str
    social_url: str
    poll_interval_seconds: int
    model_call_timeout_seconds: int
    memory_store: str
    memos_mcp_url: str
    memos_mcp_transport: str
    memos_mcp_command: str
    memos_mcp_args_json: str
    memos_api_key: str
    memos_user_id: str
    memos_channel: str
    memos_timeout_seconds: int
    memos_bearer_token: str
    memos_write_enabled: bool
    memos_search_enabled: bool
    run_mode: str
    replay_trace_id: str | None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "RuntimeAppSettings":
        """
        从环境变量创建设置实例

        Args:
            env: 环境变量映射

        Returns:
            RuntimeAppSettings: 运行时应用配置实例
        """
        source = env or os.environ
        return cls(
            base_url=(source.get("TRADE_RUNTIME_BASE_URL") or "http://127.0.0.1:8080").rstrip("/"),
            bearer_token=source.get("TRADE_RUNTIME_BEARER_TOKEN", ""),
            worker_id=(source.get("TRADE_RUNTIME_WORKER_ID") or source.get("WORKER_ID") or f"trade-runtime-{os.getpid()}").strip(),
            default_symbol=(str(source.get("TRADE_RUNTIME_DEFAULT_SYMBOL") or "").strip().upper() or "BTCUSDT"),
            symbol=None,
            exchange=None,
            news_url="",
            onchain_url="",
            social_url="",
            poll_interval_seconds=int(source.get("TRADE_RUNTIME_POLL_INTERVAL_SECONDS", "60")),
            model_call_timeout_seconds=max(
                1,
                int(source.get("TRADE_RUNTIME_MODEL_CALL_TIMEOUT_SECONDS", "45")),
            ),
            memory_store=(source.get("TRADE_RUNTIME_MEMORY_STORE") or "local").strip().lower(),
            memos_mcp_url=(source.get("TRADE_RUNTIME_MEMOS_MCP_URL") or "").strip(),
            memos_mcp_transport=(source.get("TRADE_RUNTIME_MEMOS_MCP_TRANSPORT") or "").strip().lower(),
            memos_mcp_command=(source.get("TRADE_RUNTIME_MEMOS_MCP_COMMAND") or "").strip(),
            memos_mcp_args_json=(source.get("TRADE_RUNTIME_MEMOS_MCP_ARGS_JSON") or "").strip(),
            memos_api_key=(source.get("TRADE_RUNTIME_MEMOS_API_KEY") or source.get("MEMOS_API_KEY") or "").strip(),
            memos_user_id=(source.get("TRADE_RUNTIME_MEMOS_USER_ID") or "trade-runtime").strip() or "trade-runtime",
            memos_channel=(source.get("TRADE_RUNTIME_MEMOS_CHANNEL") or "production").strip() or "production",
            memos_timeout_seconds=max(1, int(source.get("TRADE_RUNTIME_MEMOS_TIMEOUT_SECONDS", "20"))),
            memos_bearer_token=(source.get("TRADE_RUNTIME_MEMOS_BEARER_TOKEN") or "").strip(),
            memos_write_enabled=_parse_bool(source.get("TRADE_RUNTIME_MEMOS_WRITE_ENABLED", "true")),
            memos_search_enabled=_parse_bool(source.get("TRADE_RUNTIME_MEMOS_SEARCH_ENABLED", "true")),
            run_mode=(source.get("TRADE_RUNTIME_RUN_MODE") or "once").lower(),
            replay_trace_id=(source.get("TRADE_RUNTIME_REPLAY_TRACE_ID") or "").strip() or None,
        )


def _parse_mcp_args_json(value: str) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _build_long_term_memory_store(settings: RuntimeAppSettings) -> Any:
    local_store = HttpLongTermMemoryStore(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    mode = str(settings.memory_store or "local").strip().lower()
    transport = settings.memos_mcp_transport or ("stdio" if settings.memos_mcp_command else "http")
    command = settings.memos_mcp_command
    args = _parse_mcp_args_json(settings.memos_mcp_args_json)
    if transport == "stdio" and not command:
        command = "npx"
        args = ["-y", "@memtensor/memos-api-mcp@latest"]
    if transport == "stdio" and not args and command in {"npx", "npx.cmd"}:
        args = ["-y", "@memtensor/memos-api-mcp@latest"]
    has_mcp_backend = bool(settings.memos_mcp_url) or transport == "stdio"
    if mode in {"memos", "mcp", "hybrid"} and has_mcp_backend:
        mcp_env = {
            "MEMOS_USER_ID": settings.memos_user_id,
            "MEMOS_CHANNEL": settings.memos_channel,
        }
        if settings.memos_api_key:
            mcp_env["MEMOS_API_KEY"] = settings.memos_api_key
        mcp_store = McpLongTermMemoryStore(
            mcp_url=settings.memos_mcp_url,
            user_id=settings.memos_user_id,
            channel=settings.memos_channel,
            bearer_token=settings.memos_bearer_token,
            timeout=settings.memos_timeout_seconds,
            write_enabled=settings.memos_write_enabled,
            search_enabled=settings.memos_search_enabled,
            transport=transport,
            command=command,
            args=args,
            env=mcp_env,
        )
        if mode == "hybrid":
            return HybridLongTermMemoryStore(primary=local_store, secondary=mcp_store)
        return mcp_store
    return local_store


@dataclass(frozen=True)
class RuntimeContext:
    """
    运行时上下文类

    存储交易运行时的上下文信息

    Attributes:
        symbol: 交易品种
        exchange: 交易所代码
        execution_router: 执行路由器
        strategy_context: 策略上下文
        runtime_account_context: 运行时账户上下文
        exchange_account: 交易所账户
        feed_urls: 数据源URL映射
        market_api_config: 市场API配置
        market_source_context: 市场数据源上下文
    """
    symbol: str
    exchange: str
    execution_router: ExecutionRouter | None = None
    strategy_context: dict[str, Any] | None = None
    runtime_account_context: Any | None = None
    exchange_account: Any | None = None
    feed_urls: dict[str, str] | None = None
    market_api_config: Any | None = None
    market_source_context: dict[str, Any] | None = None
    runtime_config: Any | None = None


class TradeRuntimeApp:
    """
    交易运行时应用类
    
    负责管理交易运行时的执行流程，包括单次运行、循环运行和任务处理
    """
    def __init__(
        self,
        *,
        runner: TradeRuntimeRunner,
        worker_id: str = "",
        symbol: str,
        exchange: str,
        poll_interval_seconds: int = 60,
        runtime_input_supplier: Callable[..., dict[str, Any]] | None = None,
        event_bundle_supplier: Callable[[], list[dict[str, Any]]] = _default_event_bundle,
        feature_snapshot_supplier: Callable[[], dict[str, Any]] = _default_feature_snapshot,
        heartbeat_publisher: Callable[[str], None] | None = None,
        runtime_context_supplier: Callable[[], RuntimeContext | None] | None = None,
        trace_id_supplier: Callable[[], str] = lambda: uuid4().hex,
        task_client: Any | None = None,
        replay_runner: TradeReplayRunner | None = None,
        memory_consolidation_job: Any | None = None,
        sleep: Callable[[int], None] = time.sleep,
    ):
        """
        初始化交易运行时应用
        
        Args:
            runner: 交易运行时运行器
            worker_id: 工作节点ID
            symbol: 交易品种
            exchange: 交易所代码
            poll_interval_seconds: 轮询间隔秒数
            runtime_input_supplier: 运行时输入供应函数
            event_bundle_supplier: 事件包供应函数
            feature_snapshot_supplier: 特征快照供应函数
            heartbeat_publisher: 心跳发布函数
            runtime_context_supplier: 运行时上下文供应函数
            trace_id_supplier: 追踪ID供应函数
            task_client: 任务客户端
            replay_runner: 回放运行器
            sleep: 睡眠函数
        """
        self.runner = runner
        self.worker_id = worker_id
        self.symbol = symbol
        self.exchange = exchange
        self.poll_interval_seconds = poll_interval_seconds
        self.runtime_input_supplier = runtime_input_supplier
        self.event_bundle_supplier = event_bundle_supplier
        self.feature_snapshot_supplier = feature_snapshot_supplier
        self.heartbeat_publisher = heartbeat_publisher
        self.runtime_context_supplier = runtime_context_supplier
        self.strategy_context: dict[str, Any] | None = None
        self.runtime_account_context: Any | None = None
        self.exchange_account: Any | None = None
        self.market_source_context: dict[str, Any] | None = None
        self.current_runtime_context: RuntimeContext | None = None
        self.current_runtime_contexts: list[RuntimeContext] = []
        self.trace_id_supplier = trace_id_supplier
        self.task_client = task_client
        self.replay_runner = replay_runner
        self.memory_consolidation_job = memory_consolidation_job
        # Keeps accountEquity honest; see trade_runtime.account_equity for why the
        # control plane would otherwise size positions off a 10000 USDT constant.
        self.account_equity_sync = AccountEquitySync()
        self.sleep = sleep
        self._trigger_state_lock = threading.Lock()

    def _sync_account_equity(self, run_once_kwargs: dict[str, Any], trace_id: str) -> None:
        """Refresh equity from the venue before the graph sizes anything.

        Without this the control plane keeps its 10000 USDT placeholder until a
        fill produces the first pnl snapshot, and every position limit is a
        fraction of a number nobody chose.
        """
        syncer = getattr(self, "account_equity_sync", None)
        if syncer is None:
            return
        runtime_config = run_once_kwargs.get("runtime_config") or {}
        mode = ""
        if isinstance(runtime_config, dict):
            mode = str(runtime_config.get("default_mode") or runtime_config.get("defaultMode") or "")
        try:
            syncer.sync(
                execution_router=getattr(self.runner, "execution_router", None),
                callback_client=getattr(self.runner, "callback_client", None),
                mode=mode,
                exchange=str(run_once_kwargs.get("exchange") or ""),
                trace_id=trace_id,
            )
        except Exception as exc:
            logger.warning("account equity sync raised error=%s", exc.__class__.__name__)

    def run_once(self) -> dict[str, Any]:
        """
        运行一次交易流程

        Returns:
            dict[str, Any]: 运行结果
        """
        if self.heartbeat_publisher is not None and self.worker_id:
            self.heartbeat_publisher(self.worker_id)
        if self.runtime_context_supplier is not None:
            runtime_contexts = self.runtime_context_supplier()
            if isinstance(runtime_contexts, list):
                self.current_runtime_contexts = [item for item in runtime_contexts if isinstance(item, RuntimeContext)]
                return self._finalize_iteration(self._run_multi_context(runtime_contexts))
            if runtime_contexts is not None:
                self.current_runtime_contexts = []
                self._apply_runtime_context(runtime_contexts)
        trace_id = self.trace_id_supplier()
        run_once_kwargs = self._build_route_run_once_kwargs(self.current_runtime_context, trace_id)
        logger.info(
            "runtime iteration start trace_id=%s worker_id=%s symbol=%s exchange=%s",
            trace_id,
            self.worker_id or "-",
            run_once_kwargs.get("symbol"),
            run_once_kwargs.get("exchange"),
        )
        self._sync_account_equity(run_once_kwargs, trace_id)
        result = self.runner.run_once(**run_once_kwargs)
        enriched_result = self._apply_position_guard(self.runner, self.current_runtime_context, run_once_kwargs, result)
        sync_result = self._sync_okx_order_history(
            runner=self.runner,
            runtime_context=self.current_runtime_context,
            run_once_kwargs=run_once_kwargs,
            result=enriched_result,
        )
        if sync_result is not None and isinstance(enriched_result, dict):
            enriched_result = dict(enriched_result)
            enriched_result["okx_order_sync_result"] = sync_result
        logger.info(
            "runtime iteration complete trace_id=%s status=%s dispatch_mode=%s action=%s",
            trace_id,
            enriched_result.get("status", "ok") if isinstance(enriched_result, dict) else "ok",
            enriched_result.get("dispatch_mode", "-") if isinstance(enriched_result, dict) else "-",
            ((enriched_result.get("supervisor_decision") or {}).get("action") if isinstance(enriched_result, dict) else None) or "-",
        )
        return self._finalize_iteration(enriched_result)

    def _finalize_iteration(self, result: dict[str, Any]) -> dict[str, Any]:
        self._process_memory_consolidation()
        return result

    def _apply_runtime_context(self, runtime_context: RuntimeContext) -> None:
        """
        应用运行时上下文
        
        Args:
            runtime_context: 运行时上下文
        """
        self.current_runtime_context = runtime_context
        self.current_runtime_contexts = []
        self.symbol = runtime_context.symbol
        self.exchange = runtime_context.exchange
        self.runner.execution_router = runtime_context.execution_router
        self.strategy_context = runtime_context.strategy_context
        self.runtime_account_context = runtime_context.runtime_account_context
        self.exchange_account = runtime_context.exchange_account
        self.market_source_context = runtime_context.market_source_context or _build_market_source_context(runtime_context.market_api_config)
        logger.info(
            "runtime route applied symbol=%s exchange=%s market_config_id=%s",
            self.symbol,
            self.exchange,
            (self.market_source_context or {}).get("config_id") if isinstance(self.market_source_context, dict) else None,
        )

    def _sync_okx_order_history(
        self,
        *,
        runner: Any,
        runtime_context: RuntimeContext | None,
        run_once_kwargs: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not isinstance(result, dict):
            return None
        mode = str(result.get("mode") or run_once_kwargs.get("mode") or "").strip().lower()
        exchange = str(
            run_once_kwargs.get("exchange")
            or result.get("exchange")
            or getattr(runtime_context, "exchange", "")
            or self.exchange
            or ""
        ).strip().lower()
        if exchange != "okx" or mode != "live":
            return None
        execution_router = getattr(runner, "execution_router", None) or getattr(runtime_context, "execution_router", None)
        okx_client = getattr(execution_router, "okx_client", None)
        callback_client = _guard_callback_client(runner)
        if okx_client is None or callback_client is None:
            return None
        if not hasattr(okx_client, "get_order_history") or not hasattr(okx_client, "get_fills_history"):
            return None
        symbol = str(run_once_kwargs.get("symbol") or getattr(runtime_context, "symbol", "") or self.symbol or "")
        try:
            return OkxOrderSyncService(okx_client=okx_client, callback_client=callback_client).sync_once(
                symbol=symbol,
                mode=mode,
            )
        except Exception as exc:
            logger.exception(
                "okx order sync failed worker_id=%s symbol=%s exchange=%s error=%s",
                self.worker_id or "-",
                symbol,
                exchange,
                exc,
            )
            return {"orders": 0, "fills": 0, "skipped": True, "error": str(exc)}

    def _apply_position_guard(
        self,
        runner: Any,
        runtime_context: RuntimeContext | None,
        run_once_kwargs: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        strategy_context = run_once_kwargs.get("strategy_context")
        position_guard = strategy_context.get("position_guard") if isinstance(strategy_context, dict) else None
        position_risk_result = result.get("position_risk_result") if isinstance(result, dict) else None
        position_risk_hard_close = (
            isinstance(position_risk_result, dict)
            and bool(position_risk_result.get("triggered"))
            and str(position_risk_result.get("action") or "").strip().upper() == "CLOSE"
        )
        if not isinstance(position_guard, dict) and not position_risk_hard_close:
            return result
        account_context = run_once_kwargs.get("runtime_account_context")
        account_payload = _runtime_account_context_payload(account_context)
        event_bundle = run_once_kwargs.get("event_bundle") or []
        if isinstance(position_guard, dict):
            guard_result = evaluate_position_guard(
                account_context=account_payload,
                position_guard=position_guard,
                market_payload={"price": _latest_market_price(event_bundle)},
                now=datetime.now(timezone.utc),
            )
        else:
            guard_result = {"triggered": False, "reason": None}
        if position_risk_hard_close and not guard_result.get("triggered"):
            guard_result = dict(guard_result)
            guard_result["triggered"] = True
            guard_result["reason"] = f"position_risk:{position_risk_result.get('reason') or 'hard_close'}"
            guard_result["current_price"] = _position_risk_close_price(result, event_bundle)
        enriched_result = dict(result)
        enriched_result["position_guard_result"] = guard_result
        if not guard_result.get("triggered") or not _should_run_position_guard(result):
            return enriched_result
        execution_router = getattr(runner, "execution_router", None) or getattr(runtime_context, "execution_router", None)
        if execution_router is None:
            return enriched_result
        trace_id = str(run_once_kwargs.get("trace_id") or result.get("trace_id") or "")
        order = build_guard_close_order(
            trace_id=trace_id,
            symbol=str(run_once_kwargs.get("symbol") or ""),
            account_context=account_payload,
            market_payload={"price": _position_risk_close_price(result, event_bundle) if position_risk_hard_close else _latest_market_price(event_bundle)},
            trigger_reason=str(guard_result.get("reason") or "position_guard"),
        )
        execution_result = _normalize_execution_result(
            execution_router.execute(
                mode=str(result.get("mode") or run_once_kwargs.get("mode") or "paper"),
                exchange=str(run_once_kwargs.get("exchange") or result.get("exchange") or "binance"),
                order=order,
            )
        )
        execution_result = _enrich_position_guard_execution_result(
            mode=str(result.get("mode") or run_once_kwargs.get("mode") or "paper"),
            order=order,
            execution_result=execution_result,
            account_context=account_payload,
        )
        _post_position_guard_callbacks(
            callback_client=_guard_callback_client(runner),
            trace_id=trace_id,
            exchange=str(run_once_kwargs.get("exchange") or result.get("exchange") or "binance"),
            mode=str(result.get("mode") or run_once_kwargs.get("mode") or "paper"),
            order=order,
            execution_result=execution_result,
            account_context=account_payload,
            user_id=(
                int(strategy_context.get("user_id"))
                if isinstance(strategy_context, dict) and strategy_context.get("user_id") not in (None, "")
                else None
            ),
        )
        guard_result["execution_result"] = execution_result
        enriched_result["position_guard_result"] = guard_result
        if position_risk_hard_close and isinstance(position_risk_result, dict):
            enriched_position_risk_result = dict(position_risk_result)
            enriched_position_risk_result["execution_result"] = execution_result
            enriched_result["position_risk_result"] = enriched_position_risk_result
        return enriched_result

    def _run_multi_context(self, runtime_contexts: list[RuntimeContext]) -> dict[str, Any]:
        """
        运行多上下文交易流程
        
        Args:
            runtime_contexts: 运行时上下文列表
            
        Returns:
            dict[str, Any]: 运行结果
        """
        scheduler = RouteScheduler(self._resolve_route_scheduler_config(runtime_contexts))
        logger.info("runtime multi-route iteration start route_count=%s", len(runtime_contexts))
        sessions = []
        for index, runtime_context in enumerate(runtime_contexts):
            trace_id = self.trace_id_supplier()
            sessions.append(
                RouteSession(
                    index=index,
                    runtime_context=runtime_context,
                    trace_id=trace_id,
                )
            )
        results = scheduler.run(
            [
                RouteTask(
                    index=session.index,
                    symbol=session.symbol,
                    exchange=session.exchange,
                    trace_id=session.trace_id,
                    execute=lambda current_session=session: self._execute_route_session(current_session),
                )
                for session in sessions
            ]
        )
        return {"status": "ok", "results": results}

    def _resolve_route_scheduler_config(self, runtime_contexts: list[RuntimeContext]) -> RouteSchedulerConfig:
        """
        瑙ｆ瀽澶氳矾鐢辫皟搴﹂厤缃?

        Args:
            runtime_contexts: 杩愯鏃朵笂涓嬫枃鍒楄〃

        Returns:
            RouteSchedulerConfig: 璋冨害閰嶇疆
        """
        runtime_config = next(
            (getattr(item, "runtime_config", None) for item in runtime_contexts if getattr(item, "runtime_config", None) is not None),
            None,
        )
        return RouteSchedulerConfig(
            mode=_normalize_route_scheduler_mode(
                _runtime_config_value(runtime_config, "route_scheduler_mode", "routeSchedulerMode")
            ),
            max_concurrency=_normalize_route_max_concurrency(
                _runtime_config_value(runtime_config, "route_max_concurrency", "routeMaxConcurrency")
            ),
        )

    def _build_route_run_once_kwargs(
        self,
        runtime_context: RuntimeContext | None,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        鏋勫缓鍗曡矾鐢辫繍琛屽弬鏁?

        Args:
            runtime_context: 褰撳墠璺敱涓婁笅鏂?
            trace_id: 璺敱trace_id

        Returns:
            dict[str, Any]: run_once鍙傛暟
        """
        resolved_context = runtime_context or self.current_runtime_context
        symbol = runtime_context.symbol if runtime_context is not None else self.symbol
        exchange = runtime_context.exchange if runtime_context is not None else self.exchange
        strategy_context = runtime_context.strategy_context if runtime_context is not None else self.strategy_context
        runtime_account_context = (
            runtime_context.runtime_account_context if runtime_context is not None else self.runtime_account_context
        )
        exchange_account = runtime_context.exchange_account if runtime_context is not None else self.exchange_account
        if runtime_context is not None:
            market_source_context = runtime_context.market_source_context or _build_market_source_context(runtime_context.market_api_config)
        else:
            market_source_context = self.market_source_context
        if self.runtime_input_supplier is not None:
            runtime_inputs = self.runtime_input_supplier(
                trace_id=trace_id,
                symbol=symbol,
                exchange=exchange,
                feed_urls=getattr(resolved_context, "feed_urls", None),
                market_api_config=getattr(resolved_context, "market_api_config", None),
                runtime_config=getattr(resolved_context, "runtime_config", None),
                strategy_context=strategy_context,
            )
            event_bundle = runtime_inputs.get("event_bundle") or []
            feature_snapshot = runtime_inputs.get("feature_snapshot") or {}
        else:
            runtime_inputs = {}
            event_bundle = self.event_bundle_supplier()
            feature_snapshot = self.feature_snapshot_supplier()
        run_once_kwargs = {
            "trace_id": trace_id,
            "symbol": symbol,
            "exchange": exchange,
            "event_bundle": event_bundle,
            "feature_snapshot": feature_snapshot,
        }
        if self.runtime_input_supplier is not None and runtime_inputs.get("market_context_history") is not None:
            run_once_kwargs["market_context_history"] = runtime_inputs.get("market_context_history")
        if self.runtime_input_supplier is not None and runtime_inputs.get("signal_window_states") is not None:
            run_once_kwargs["signal_window_states"] = runtime_inputs.get("signal_window_states")
        if self.runtime_input_supplier is not None and runtime_inputs.get("market_source_status"):
            run_once_kwargs["market_source_status"] = runtime_inputs.get("market_source_status")
        if strategy_context is not None:
            run_once_kwargs["strategy_context"] = strategy_context
        if runtime_account_context is not None:
            run_once_kwargs["runtime_account_context"] = runtime_account_context
        if exchange_account is not None:
            run_once_kwargs["exchange_account"] = exchange_account
        if market_source_context is not None:
            run_once_kwargs["market_source_context"] = market_source_context
        return run_once_kwargs

    def _sleep_interval_seconds(self) -> int:
        interval = int(self.poll_interval_seconds)
        candidate_contexts = self.current_runtime_contexts or ([self.current_runtime_context] if self.current_runtime_context is not None else [])
        watcher_intervals: list[int] = []
        for runtime_context in candidate_contexts:
            if runtime_context is None or not _has_active_position(runtime_context.runtime_account_context):
                continue
            config = resolve_position_risk_watcher_config(runtime_context.runtime_config, runtime_context.strategy_context)
            if not config.get("enabled"):
                continue
            watcher_intervals.append(int(config.get("intervalSeconds") or interval))
        if watcher_intervals:
            return max(1, min(interval, *watcher_intervals))
        if not _has_active_position(self.runtime_account_context):
            return interval
        runtime_config = getattr(self.current_runtime_context, "runtime_config", None)
        config = resolve_position_risk_watcher_config(runtime_config, self.strategy_context)
        if not config.get("enabled"):
            return interval
        watcher_interval = int(config.get("intervalSeconds") or interval)
        return max(1, min(interval, watcher_interval))

    def _build_route_runner(self, runtime_context: RuntimeContext):
        """
        涓鸿矾鐢辨瀯寤洪殧绂荤殑杩愯鍣?

        Args:
            runtime_context: 褰撳墠璺敱涓婁笅鏂?

        Returns:
            Any: 鍙敤浜庡崟璺敱鐨勮繍琛屽櫒
        """
        if hasattr(self.runner, "config_client") and hasattr(self.runner, "callback_client"):
            route_runner = TradeRuntimeRunner(
                config_client=self.runner.config_client,
                callback_client=self.runner.callback_client,
                graph=getattr(self.runner, "graph", None),
                execution_router=runtime_context.execution_router,
            )
            route_runner.decision_model_client = getattr(self.runner, "decision_model_client", None)
            route_runner.memory_store = getattr(self.runner, "memory_store", None)
        else:
            try:
                route_runner = copy.copy(self.runner)
            except Exception:
                route_runner = self.runner
            if hasattr(route_runner, "execution_router"):
                route_runner.execution_router = runtime_context.execution_router
        route_runner.lifecycle_manager = _bind_lifecycle_manager_model(
            getattr(self.runner, "lifecycle_manager", None),
            runtime_context.strategy_context,
        )
        self._seed_route_state(route_runner)
        return route_runner

    def _seed_route_state(self, route_runner: Any) -> None:
        self._seed_route_trigger_state(route_runner)
        self._seed_route_position_risk_watcher(route_runner)

    def _commit_route_state(self, route_runner: Any) -> None:
        self._commit_route_trigger_state(route_runner)
        self._commit_route_position_risk_watcher(route_runner)

    def _seed_route_trigger_state(self, route_runner: Any) -> None:
        if not hasattr(route_runner, "trigger_state"):
            return
        with self._trigger_state_lock:
            parent_trigger_state = getattr(self.runner, "trigger_state", {})
            seed_trigger_state = copy.deepcopy(parent_trigger_state if isinstance(parent_trigger_state, dict) else {})
            route_runner.trigger_state = copy.deepcopy(seed_trigger_state)
            setattr(route_runner, "_seed_trigger_state", seed_trigger_state)

    def _commit_route_trigger_state(self, route_runner: Any) -> None:
        if not hasattr(self.runner, "trigger_state") or not hasattr(route_runner, "trigger_state"):
            return
        route_trigger_state = getattr(route_runner, "trigger_state", None)
        if not isinstance(route_trigger_state, dict):
            return
        seed_trigger_state = getattr(route_runner, "_seed_trigger_state", {})
        if not isinstance(seed_trigger_state, dict):
            seed_trigger_state = {}
        with self._trigger_state_lock:
            parent_trigger_state = getattr(self.runner, "trigger_state", {})
            if not isinstance(parent_trigger_state, dict) or parent_trigger_state == seed_trigger_state:
                self.runner.trigger_state = copy.deepcopy(route_trigger_state)
                return
            self.runner.trigger_state = self._merge_trigger_state_updates(
                parent_trigger_state,
                seed_trigger_state,
                route_trigger_state,
            )

    def _merge_trigger_state_updates(
        self,
        parent_trigger_state: dict[str, Any],
        seed_trigger_state: dict[str, Any],
        route_trigger_state: dict[str, Any],
    ) -> dict[str, Any]:
        merged = copy.deepcopy(parent_trigger_state)
        for key in ("cooldowns", "dedupe"):
            merged_bucket = dict(merged.get(key) or {})
            seed_bucket = seed_trigger_state.get(key) if isinstance(seed_trigger_state.get(key), dict) else {}
            route_bucket = route_trigger_state.get(key) if isinstance(route_trigger_state.get(key), dict) else {}
            for item_key, item_value in route_bucket.items():
                if seed_bucket.get(item_key) != item_value:
                    merged_bucket[item_key] = copy.deepcopy(item_value)
            merged[key] = merged_bucket
        merged["budget_state"] = self._merge_budget_state_updates(
            merged.get("budget_state") if isinstance(merged.get("budget_state"), dict) else {},
            seed_trigger_state.get("budget_state") if isinstance(seed_trigger_state.get("budget_state"), dict) else {},
            route_trigger_state.get("budget_state") if isinstance(route_trigger_state.get("budget_state"), dict) else {},
        )
        return merged

    def _merge_budget_state_updates(
        self,
        parent_budget_state: dict[str, Any],
        seed_budget_state: dict[str, Any],
        route_budget_state: dict[str, Any],
    ) -> dict[str, Any]:
        merged = copy.deepcopy(parent_budget_state)
        merged_symbol_dispatches = dict(merged.get("symbol_dispatches") or {})
        seed_symbol_dispatches = seed_budget_state.get("symbol_dispatches") if isinstance(seed_budget_state.get("symbol_dispatches"), dict) else {}
        route_symbol_dispatches = route_budget_state.get("symbol_dispatches") if isinstance(route_budget_state.get("symbol_dispatches"), dict) else {}
        for symbol, route_entries in route_symbol_dispatches.items():
            seed_entries = seed_symbol_dispatches.get(symbol) if isinstance(seed_symbol_dispatches, dict) else []
            route_list = list(route_entries) if isinstance(route_entries, list) else []
            seed_list = list(seed_entries) if isinstance(seed_entries, list) else []
            new_entries = route_list[len(seed_list):] if route_list[:len(seed_list)] == seed_list else route_list
            if not new_entries:
                continue
            merged_symbol_dispatches[str(symbol)] = list(merged_symbol_dispatches.get(str(symbol)) or []) + copy.deepcopy(new_entries)
        merged["symbol_dispatches"] = merged_symbol_dispatches
        seed_global = seed_budget_state.get("global_dispatches") if isinstance(seed_budget_state.get("global_dispatches"), list) else []
        route_global = route_budget_state.get("global_dispatches") if isinstance(route_budget_state.get("global_dispatches"), list) else []
        new_global = route_global[len(seed_global):] if route_global[:len(seed_global)] == seed_global else route_global
        if new_global:
            merged["global_dispatches"] = list(merged.get("global_dispatches") or []) + copy.deepcopy(new_global)
        return merged

    def _seed_route_position_risk_watcher(self, route_runner: Any) -> None:
        parent_watcher = getattr(self.runner, "position_risk_watcher", None)
        route_watcher = getattr(route_runner, "position_risk_watcher", None)
        if parent_watcher is None or route_watcher is None or not hasattr(parent_watcher, "_cooldowns") or not hasattr(route_watcher, "_cooldowns"):
            return
        with self._trigger_state_lock:
            seed_cooldowns = copy.deepcopy(getattr(parent_watcher, "_cooldowns", {}) or {})
            route_watcher._cooldowns = copy.deepcopy(seed_cooldowns)
            setattr(route_runner, "_seed_position_risk_cooldowns", seed_cooldowns)

    def _commit_route_position_risk_watcher(self, route_runner: Any) -> None:
        parent_watcher = getattr(self.runner, "position_risk_watcher", None)
        route_watcher = getattr(route_runner, "position_risk_watcher", None)
        if parent_watcher is None or route_watcher is None or not hasattr(parent_watcher, "_cooldowns") or not hasattr(route_watcher, "_cooldowns"):
            return
        route_cooldowns = getattr(route_watcher, "_cooldowns", None)
        if not isinstance(route_cooldowns, dict):
            return
        seed_cooldowns = getattr(route_runner, "_seed_position_risk_cooldowns", {})
        if not isinstance(seed_cooldowns, dict):
            seed_cooldowns = {}
        with self._trigger_state_lock:
            parent_cooldowns = getattr(parent_watcher, "_cooldowns", {})
            if not isinstance(parent_cooldowns, dict) or parent_cooldowns == seed_cooldowns:
                parent_watcher._cooldowns = copy.deepcopy(route_cooldowns)
                return
            merged_cooldowns = copy.deepcopy(parent_cooldowns)
            for key, value in route_cooldowns.items():
                if seed_cooldowns.get(key) != value:
                    merged_cooldowns[key] = copy.deepcopy(value)
            parent_watcher._cooldowns = merged_cooldowns

    def _execute_route_session(self, session: RouteSession) -> dict[str, Any]:
        """
        鎵ц鍗曚釜璺敱浼氳瘽

        Args:
            session: 璺敱浼氳瘽

        Returns:
            dict[str, Any]: 璺敱鎵ц缁撴灉
        """
        logger.info(
            "runtime route session start trace_id=%s symbol=%s exchange=%s",
            session.trace_id,
            session.symbol,
            session.exchange,
        )
        runner = self._build_route_runner(session.runtime_context)
        run_once_kwargs = self._build_route_run_once_kwargs(session.runtime_context, session.trace_id)
        try:
            result = runner.run_once(**run_once_kwargs)
            enriched_result = self._apply_position_guard(runner, session.runtime_context, run_once_kwargs, result)
            sync_result = self._sync_okx_order_history(
                runner=runner,
                runtime_context=session.runtime_context,
                run_once_kwargs=run_once_kwargs,
                result=enriched_result,
            )
            if sync_result is not None and isinstance(enriched_result, dict):
                enriched_result = dict(enriched_result)
                enriched_result["okx_order_sync_result"] = sync_result
        except Exception:
            self._commit_route_state(runner)
            raise
        self._commit_route_state(runner)
        logger.info(
            "runtime route session complete trace_id=%s symbol=%s exchange=%s status=%s dispatch_mode=%s action=%s",
            session.trace_id,
            session.symbol,
            session.exchange,
            enriched_result.get("status", "ok") if isinstance(enriched_result, dict) else "ok",
            enriched_result.get("dispatch_mode", "-") if isinstance(enriched_result, dict) else "-",
            ((enriched_result.get("supervisor_decision") or {}).get("action") if isinstance(enriched_result, dict) else None) or "-",
        )
        return enriched_result

    def run_forever(self, iterations: int | None = None) -> dict[str, Any]:
        """
        持续运行交易流程
        
        Args:
            iterations: 运行次数，None表示无限运行
            
        Returns:
            dict[str, Any]: 最后一次运行的结果
        """
        completed = 0
        last_result: dict[str, Any] = {}
        logger.info(
            "runtime loop starting worker_id=%s symbol=%s exchange=%s poll_interval_seconds=%s iterations=%s",
            self.worker_id or "-",
            self.symbol,
            self.exchange,
            self.poll_interval_seconds,
            iterations if iterations is not None else "forever",
        )
        while iterations is None or completed < iterations:
            try:
                last_result = self.run_once()
                self._process_runtime_tasks()
            except Exception as exc:
                logger.exception(
                    "runtime iteration failed worker_id=%s symbol=%s exchange=%s error=%s",
                    self.worker_id or "-",
                    self.symbol,
                    self.exchange,
                    exc,
                )
                last_result = {
                    "status": "error",
                    "symbol": self.symbol,
                    "exchange": self.exchange,
                    "error": str(exc),
                }
            completed += 1
            if iterations is None or completed < iterations:
                self.sleep(self._sleep_interval_seconds())
        return last_result

    def _process_runtime_tasks(self) -> None:
        """
        处理运行时任务
        """
        if self.task_client is None or self.replay_runner is None or not self.worker_id:
            return
        task = self.task_client.pull_task(self.worker_id)
        if not isinstance(task, dict) or not task:
            return
        task_id = str(task.get("taskId") or "").strip()
        task_type = str(task.get("taskType") or task.get("task_type") or "").strip()
        task_data = task.get("taskData") or task.get("task_data") or {}
        if task_type != "TRADE_RUNTIME_REPLAY" or not task_id:
            return
        logger.info("runtime task received worker_id=%s task_id=%s task_type=%s", self.worker_id, task_id, task_type)
        source_trace_id = str(task_data.get("sourceTraceId") or task_data.get("source_trace_id") or "").strip()
        session_id = task_data.get("sessionId") or task_data.get("session_id")
        try:
            result = self.replay_runner.run_trace(source_trace_id, session_id=session_id)
            self.task_client.save_task_result(task_id, result)
            self.task_client.update_task_status(task_id, "completed", json.dumps(result, ensure_ascii=False))
        except Exception as exc:
            logger.exception("runtime task failed task_id=%s task_type=%s error=%s", task_id, task_type, exc)
            payload = {"success": False, "error": str(exc), "source_trace_id": source_trace_id, "session_id": session_id}
            self.task_client.save_task_result(task_id, payload)
            self.task_client.update_task_status(task_id, "failed", json.dumps(payload, ensure_ascii=False))

    def _process_memory_consolidation(self) -> None:
        if self.memory_consolidation_job is None:
            return
        try:
            result = self.memory_consolidation_job.run_once()
            logger.info("memory consolidation complete result=%s", result)
        except Exception as exc:
            logger.warning("memory consolidation failed error=%s", exc, exc_info=True)


def _resolve_runtime_context(
    settings: RuntimeAppSettings,
    config_client: RuntimeConfigClient,
    env: Mapping[str, str] | None = None,
) -> RuntimeContext:
    """
    解析运行时上下文
    
    Args:
        settings: 运行时应用配置
        config_client: 配置客户端
        env: 环境变量映射
        
    Returns:
        RuntimeContext: 运行时上下文
    """
    bootstrap = config_client.get_bootstrap(
        symbol=settings.symbol,
        exchange=settings.exchange,
    )
    resolved_symbol = _resolve_bootstrap_symbol(bootstrap, settings)
    resolved_exchange = (
        str(getattr(getattr(bootstrap, "symbol_scope", None), "exchange_code", "") or "").strip().lower()
        or str(settings.exchange or "").strip().lower()
        or "binance"
    )
    market_api_config = SourceConfigClient(bootstrap).resolve_market_api_config(
        symbol=resolved_symbol,
        exchange=resolved_exchange,
    )
    return RuntimeContext(
        symbol=resolved_symbol,
        exchange=resolved_exchange,
        execution_router=build_execution_router(env, runtime_account=getattr(bootstrap, "exchange_account", None)),
        strategy_context=_build_strategy_context(bootstrap),
        runtime_account_context=getattr(bootstrap, "runtime_account_context", None),
        exchange_account=getattr(bootstrap, "exchange_account", None),
        feed_urls=_build_feed_urls(settings, bootstrap),
        market_api_config=market_api_config,
        market_source_context=_build_market_source_context(market_api_config),
        runtime_config=getattr(bootstrap, "runtime_config", None),
    )


def _parse_strategy_config(config_json: str | None) -> dict[str, Any]:
    """
    解析策略配置
    
    Args:
        config_json: 配置JSON字符串
        
    Returns:
        dict[str, Any]: 解析后的配置字典
    """
    if not config_json or not str(config_json).strip():
        return {}
    try:
        payload = json.loads(config_json)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_initial_market_context_history(history_json: str | None) -> dict[str, list[dict[str, Any]]]:
    """Parse optional initial market context history from env JSON."""
    if not history_json or not str(history_json).strip():
        return {}
    try:
        payload = json.loads(history_json)
    except (TypeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}

    history: dict[str, list[dict[str, Any]]] = {}
    for raw_symbol, raw_items in payload.items():
        symbol = str(raw_symbol or "").strip().upper()
        if not symbol or not isinstance(raw_items, list):
            continue
        items = [dict(item) for item in raw_items if isinstance(item, dict)]
        if items:
            history[symbol] = items
    return history


def _parse_market_context_history_limit(raw_limit: str | None) -> int:
    try:
        return max(1, int(str(raw_limit or "60").strip() or "60"))
    except (TypeError, ValueError):
        return 60


def _parse_market_context_history_max_age_minutes(raw_value: str | None) -> int:
    try:
        return max(1, int(str(raw_value or "300").strip() or "300"))
    except (TypeError, ValueError):
        return 300


def _resolve_bootstrap_symbol(bootstrap: Any, settings: RuntimeAppSettings | None = None) -> str:
    default_symbol = str(getattr(settings, "default_symbol", None) or "BTCUSDT").strip().upper()
    return (
        str(getattr(getattr(bootstrap, "symbol_scope", None), "symbol", None) or "").strip().upper()
        or str(getattr(getattr(bootstrap, "market_data_config", None), "symbol", None) or "").strip().upper()
        or str(getattr(settings, "symbol", None) or "").strip().upper()
        or default_symbol
    )


def _build_strategy_context(bootstrap: Any) -> dict[str, Any] | None:
    """
    构建策略上下文
    
    Args:
        bootstrap: 引导配置
        
    Returns:
        dict[str, Any] | None: 策略上下文
    """
    strategy = getattr(bootstrap, "strategy", None)
    strategy_version = getattr(bootstrap, "strategy_version", None)
    ai_model_config = getattr(bootstrap, "ai_model_config", None)
    news_api_config = getattr(bootstrap, "news_api_config", None)
    onchain_api_config = getattr(bootstrap, "onchain_api_config", None)
    social_api_config = getattr(bootstrap, "social_api_config", None)
    market_api_config = getattr(bootstrap, "market_api_config", None)
    market_data_config = getattr(bootstrap, "market_data_config", None)
    prompt_bindings = getattr(bootstrap, "prompt_bindings", None) or []
    agent_profiles = getattr(bootstrap, "agent_profiles", None) or []
    resolved_agent_configs = getattr(bootstrap, "resolved_agent_configs", None) or []
    deliberation_policy = getattr(bootstrap, "deliberation_policy", None) or {}
    position_guard = getattr(bootstrap, "position_guard", None)
    strategy_config = _parse_strategy_config(getattr(strategy_version, "config_json", None))
    supervisor_policy = strategy_config.get("supervisorPolicy") or strategy_config.get("supervisor_policy") or {}

    def source_binding_payload(source_key: str, api_config: Any) -> dict[str, Any] | None:
        if api_config is None:
            return None
        strategy_keys = {
            "news": ("newsApiConfigId", "news_api_config_id"),
            "onchain": ("onchainApiConfigId", "onchain_api_config_id"),
            "social": ("socialApiConfigId", "social_api_config_id"),
        }
        explicit_keys = strategy_keys.get(source_key, ())
        selection_mode = "strategy" if any(strategy_config.get(key) not in (None, "") for key in explicit_keys) else "default"
        return {
            "config_id": getattr(api_config, "id", None),
            "category": getattr(api_config, "data_category", None),
            "api_url": getattr(api_config, "api_url", None),
            "enabled": _is_enabled_flag(getattr(api_config, "enabled", None), default=True),
            "selection_mode": selection_mode,
        }

    source_bindings = {
        source_key: payload
        for source_key, payload in (
            ("news", source_binding_payload("news", news_api_config)),
            ("onchain", source_binding_payload("onchain", onchain_api_config)),
            ("social", source_binding_payload("social", social_api_config)),
        )
        if payload is not None
    }
    payload = {
        "user_id": getattr(bootstrap, "user_id", None),
        "strategy_id": getattr(strategy, "id", None) or getattr(strategy_version, "strategy_id", None),
        "strategy_key": getattr(strategy, "strategy_key", None),
        "strategy_name": getattr(strategy, "strategy_name", None),
        "runtime_mode": getattr(strategy, "runtime_mode", None),
        "strategy_version": getattr(strategy_version, "version_no", None),
        "strategy_config": strategy_config,
        "ai_model_config": _build_ai_model_context(ai_model_config),
        "news_api_config": _build_market_api_context(news_api_config),
        "onchain_api_config": _build_market_api_context(onchain_api_config),
        "social_api_config": _build_market_api_context(social_api_config),
        "market_api_config": _build_market_api_context(market_api_config),
        "market_data_config": _build_market_data_context(market_data_config),
        "prompt_bindings": [
            item
            for item in (_build_prompt_binding_context(binding) for binding in prompt_bindings)
            if item is not None
        ],
        "agent_profiles": [
            item
            for item in (_build_agent_profile_context(profile) for profile in agent_profiles)
            if item is not None
        ],
        "resolved_agent_configs": [
            item
            for item in (_build_resolved_agent_config_context(config) for config in resolved_agent_configs)
            if item is not None
        ],
        "source_bindings": source_bindings,
        "position_guard": _build_position_guard_context(position_guard),
        "deliberation_policy": deliberation_policy if isinstance(deliberation_policy, dict) else {},
        "supervisor_policy": supervisor_policy if isinstance(supervisor_policy, dict) else {},
    }
    if any(value not in (None, "", {}, []) for value in payload.values()):
        return payload
    return None


def _build_runtime_context_supplier(
    *,
    initial_context: RuntimeContext | list[RuntimeContext],
    resolver: Callable[[], RuntimeContext | list[RuntimeContext]],
) -> Callable[[], RuntimeContext | list[RuntimeContext]]:
    pending_initial_context = [initial_context]

    def supply() -> RuntimeContext | list[RuntimeContext]:
        if pending_initial_context:
            return pending_initial_context.pop(0)
        return resolver()

    return supply


def _parse_aux_feed_timeout(value: Any, default: int = DEFAULT_AUX_FEED_TIMEOUT_SECONDS) -> int:
    text = str(value or "").strip()
    if not text:
        return default
    try:
        return max(1, int(text))
    except (TypeError, ValueError):
        logger.warning("invalid auxiliary feed timeout=%r, fallback=%s", value, default)
        return default


def _resolve_aux_feed_timeout(env: Mapping[str, str] | None, source_type: str) -> int:
    source = env if env is not None else os.environ
    global_timeout = _parse_aux_feed_timeout(source.get("TRADE_RUNTIME_AUX_FEED_TIMEOUT_SECONDS"))
    prefix = str(source_type or "").strip().upper()
    specific_key = f"TRADE_RUNTIME_{prefix}_FEED_TIMEOUT_SECONDS"
    specific_value = source.get(specific_key)
    if specific_value not in (None, ""):
        return _parse_aux_feed_timeout(specific_value, default=global_timeout)
    return global_timeout


def _build_runtime_input_supplier(
    *,
    settings: RuntimeAppSettings,
    event_client: RuntimeEventClient,
    stream_publisher: StreamPublisher | None,
    stream_consumer: StreamConsumer | None = None,
    initial_exchange: str,
    initial_symbol: str | None = None,
    default_symbol: str = "BTCUSDT",
    initial_feed_urls: Mapping[str, str] | None = None,
    initial_market_api_config: Any | None = None,
    initial_market_context_history: Mapping[str, list[dict[str, Any]]] | None = None,
    market_context_history_limit: int = 60,
    market_context_history_max_age_minutes: int = 300,
    env: Mapping[str, str] | None = None,
) -> Callable[..., dict[str, Any]]:
    assemblers: dict[str, RuntimeInputAssembler] = {}
    cached_resources: dict[str, tuple[Any, ...]] = {}
    route_cache_keys: dict[str, str] = {}
    cache_lock = threading.Lock()

    def close_resource(resource: Any) -> None:
        close = getattr(resource, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                return

    def close_cached_resources(cache_key: str) -> None:
        resources = (assemblers.pop(cache_key, None), *cached_resources.pop(cache_key, ()))
        seen_ids: set[int] = set()
        for resource in resources:
            if resource is None:
                continue
            resource_id = id(resource)
            if resource_id in seen_ids:
                continue
            seen_ids.add(resource_id)
            close_resource(resource)

    def resolve_assembler(
        exchange: str,
        feed_urls: Mapping[str, str] | None = None,
        market_api_config: Any | None = None,
    ) -> RuntimeInputAssembler:
        normalized_exchange = str(exchange or "").strip().lower() or "binance"

        def resolve_feed_url(key: str) -> str:
            if feed_urls is not None and key in feed_urls:
                return str(feed_urls.get(key) or "").strip()
            return ""

        resolved_news_url = resolve_feed_url("news_url")
        resolved_onchain_url = resolve_feed_url("onchain_url")
        resolved_social_url = resolve_feed_url("social_url")
        market_source_key = _build_market_api_cache_key(market_api_config)
        news_timeout = _resolve_aux_feed_timeout(env, "news")
        onchain_timeout = _resolve_aux_feed_timeout(env, "onchain")
        social_timeout = _resolve_aux_feed_timeout(env, "social")
        timeout_key = ":".join([str(news_timeout), str(onchain_timeout), str(social_timeout)])
        route_key = "|".join([normalized_exchange, resolved_news_url, resolved_onchain_url, resolved_social_url])
        cache_key = "|".join([normalized_exchange, resolved_news_url, resolved_onchain_url, resolved_social_url, market_source_key, timeout_key])
        with cache_lock:
            previous_cache_key = route_cache_keys.get(route_key)
            if previous_cache_key and previous_cache_key != cache_key:
                close_cached_resources(previous_cache_key)
            assembler = assemblers.get(cache_key)
            if assembler is None:
                rest_market_feed = OkxPublicMarketFeed() if normalized_exchange == "okx" else BinancePublicMarketFeed()
                news_supplier = HttpJsonFeedSupplier(url=resolved_news_url or None, timeout=news_timeout) if resolved_news_url else None
                onchain_supplier = HttpJsonFeedSupplier(url=resolved_onchain_url or None, timeout=onchain_timeout) if resolved_onchain_url else None
                social_supplier = HttpJsonFeedSupplier(url=resolved_social_url or None, timeout=social_timeout) if resolved_social_url else None
                market_feed = (
                    OkxWsMarketFeed(
                        rest_payload_supplier=rest_market_feed.fetch,
                        market_api_config=market_api_config,
                    )
                    if normalized_exchange == "okx"
                    else BinanceWsMarketFeed(
                        rest_payload_supplier=rest_market_feed.fetch,
                        market_api_config=market_api_config,
                    )
                )
                assembler = RuntimeInputAssembler(
                    exchange=normalized_exchange,
                    market_payload_supplier=market_feed.fetch,
                    news_items_supplier=news_supplier.fetch if news_supplier is not None else None,
                    onchain_items_supplier=onchain_supplier.fetch if onchain_supplier is not None else None,
                    social_items_supplier=social_supplier.fetch if social_supplier is not None else None,
                    stream_publisher=stream_publisher,
                    stream_consumer=stream_consumer,
                    event_client=None if stream_consumer is not None else event_client,
                    initial_market_context_history=initial_market_context_history,
                    market_context_history_limit=market_context_history_limit,
                )
                assemblers[cache_key] = assembler
                cached_resources[cache_key] = (
                    market_feed,
                    rest_market_feed,
                    news_supplier,
                    onchain_supplier,
                    social_supplier,
                )
            route_cache_keys[route_key] = cache_key
            return assembler

    def supply(**kwargs) -> dict[str, Any]:
        symbol = (
            str(kwargs.get("symbol") or "").strip().upper()
            or str(initial_symbol or "").strip().upper()
            or str(default_symbol or "").strip().upper()
        )
        exchange = str(kwargs.get("exchange") or "").strip().lower() or "binance"
        runtime_inputs = resolve_assembler(exchange, kwargs.get("feed_urls"), kwargs.get("market_api_config")).build(
            symbol=symbol,
            trace_id=kwargs.get("trace_id", ""),
            runtime_config=kwargs.get("runtime_config"),
            strategy_context=kwargs.get("strategy_context"),
        )
        market_context_history = _select_market_context_history(
            runtime_inputs=runtime_inputs,
            event_client=event_client,
            symbol=symbol,
            exchange=exchange,
            limit=market_context_history_limit,
            max_age_minutes=market_context_history_max_age_minutes,
        )
        if market_context_history or "market_context_history" in runtime_inputs:
            runtime_inputs["market_context_history"] = market_context_history
        else:
            runtime_inputs.pop("market_context_history", None)
        return runtime_inputs

    resolve_assembler(initial_exchange, initial_feed_urls, initial_market_api_config)
    return supply



def _select_market_context_history(
    *,
    runtime_inputs: dict[str, Any],
    event_client: Any,
    symbol: str,
    exchange: str,
    limit: int,
    max_age_minutes: int,
) -> list[dict[str, Any]]:
    in_memory_history = runtime_inputs.get("market_context_history")
    if not isinstance(in_memory_history, list):
        in_memory_history = []
    get_market_history = getattr(event_client, "get_market_history", None)
    if not callable(get_market_history):
        return in_memory_history
    try:
        persisted_history = get_market_history(symbol=symbol, exchange=exchange, limit=limit, max_age_minutes=max_age_minutes)
    except Exception:
        return in_memory_history
    if not isinstance(persisted_history, list):
        return in_memory_history
    normalized_persisted_history = [dict(item) for item in persisted_history if isinstance(item, dict)]
    if len(normalized_persisted_history) >= len(in_memory_history):
        return normalized_persisted_history[-limit:]
    return in_memory_history

def _resolve_memory_model_id(strategy_context: dict[str, Any] | None) -> int | None:
    if not isinstance(strategy_context, dict):
        return None
    ai_model_config = strategy_context.get("ai_model_config")
    if not isinstance(ai_model_config, dict):
        return None
    try:
        model_id = int(ai_model_config.get("id") or 0)
    except (TypeError, ValueError):
        return None
    return model_id if model_id > 0 else None


def _bind_lifecycle_manager_model(
    lifecycle_manager: TradeLifecycleManager | None,
    strategy_context: dict[str, Any] | None,
) -> TradeLifecycleManager | None:
    if lifecycle_manager is None:
        return None
    try:
        bound_manager = copy.copy(lifecycle_manager)
    except Exception:
        bound_manager = lifecycle_manager
    bound_manager.model_id = _resolve_memory_model_id(strategy_context)
    return bound_manager


def _build_memory_model_id_resolver(
    runtime_context: RuntimeContext | list[RuntimeContext],
) -> Callable[[dict[str, Any]], int | None]:
    runtime_contexts = runtime_context if isinstance(runtime_context, list) else [runtime_context]
    by_symbol_exchange: dict[tuple[str, str], int] = {}
    by_symbol: dict[str, set[int]] = {}
    for item in runtime_contexts:
        if not isinstance(item, RuntimeContext):
            continue
        model_id = _resolve_memory_model_id(item.strategy_context)
        if model_id is None:
            continue
        symbol = str(item.symbol or "").strip().upper()
        exchange = str(item.exchange or "").strip().lower()
        if symbol and exchange:
            by_symbol_exchange[(symbol, exchange)] = model_id
        if symbol:
            by_symbol.setdefault(symbol, set()).add(model_id)

    def resolve(payload: dict[str, Any]) -> int | None:
        if not isinstance(payload, dict):
            return None
        symbol = str(payload.get("symbol") or "").strip().upper()
        exchange = str(
            payload.get("exchange")
            or payload.get("exchange_code")
            or payload.get("exchangeCode")
            or ""
        ).strip().lower()
        if symbol and exchange:
            matched = by_symbol_exchange.get((symbol, exchange))
            if matched is not None:
                return matched
        if symbol:
            symbol_matches = by_symbol.get(symbol) or set()
            if len(symbol_matches) == 1:
                return next(iter(symbol_matches))
        return None

    return resolve


def _build_memory_current_price_supplier(
    *,
    runtime_input_supplier: Callable[..., dict[str, Any]],
    runtime_context: RuntimeContext | list[RuntimeContext],
) -> Callable[[str], float]:
    runtime_contexts = runtime_context if isinstance(runtime_context, list) else [runtime_context]
    default_context = runtime_contexts[0]

    def resolve_context(symbol: str) -> RuntimeContext:
        normalized_symbol = str(symbol or "").strip().upper()
        for item in runtime_contexts:
            if str(item.symbol or "").strip().upper() == normalized_symbol:
                return item
        return default_context

    def supply(symbol: str) -> float:
        resolved_context = resolve_context(symbol)
        runtime_inputs = runtime_input_supplier(
            trace_id=f"memory-price-{uuid4().hex}",
            symbol=symbol,
            exchange=resolved_context.exchange,
            feed_urls=resolved_context.feed_urls,
            market_api_config=resolved_context.market_api_config,
            runtime_config=resolved_context.runtime_config,
            strategy_context=resolved_context.strategy_context,
        )
        return _latest_market_price(runtime_inputs.get("event_bundle") or [])

    return supply


def _resolve_runtime_contexts(
    settings: RuntimeAppSettings,
    config_client: RuntimeConfigClient,
    env: Mapping[str, str] | None = None,
) -> RuntimeContext | list[RuntimeContext]:
    if settings.symbol or settings.exchange:
        return _resolve_runtime_context(settings, config_client, env)
    list_bootstraps = getattr(config_client, "list_bootstraps", None)
    if callable(list_bootstraps):
        bootstraps = list_bootstraps()
        if bootstraps:
            return [_bootstrap_to_runtime_context(item, env, settings=settings) for item in bootstraps]
    return _resolve_runtime_context(settings, config_client, env)


def _bootstrap_to_runtime_context(
    bootstrap: Any,
    env: Mapping[str, str] | None = None,
    *,
    settings: RuntimeAppSettings | None = None,
) -> RuntimeContext:
    resolved_symbol = _resolve_bootstrap_symbol(bootstrap, settings)
    resolved_exchange = (
        str(getattr(getattr(bootstrap, "symbol_scope", None), "exchange_code", "") or "").strip().lower()
        or "binance"
    )
    market_api_config = SourceConfigClient(bootstrap).resolve_market_api_config(
        symbol=resolved_symbol,
        exchange=resolved_exchange,
    )
    return RuntimeContext(
        symbol=resolved_symbol,
        exchange=resolved_exchange,
        execution_router=build_execution_router(env, runtime_account=getattr(bootstrap, "exchange_account", None)),
        strategy_context=_build_strategy_context(bootstrap),
        runtime_account_context=getattr(bootstrap, "runtime_account_context", None),
        exchange_account=getattr(bootstrap, "exchange_account", None),
        feed_urls=_build_feed_urls(None, bootstrap),
        market_api_config=market_api_config,
        market_source_context=_build_market_source_context(market_api_config),
        runtime_config=getattr(bootstrap, "runtime_config", None),
    )


def build_runtime_app(env: Mapping[str, str] | None = None) -> TradeRuntimeApp:
    settings = RuntimeAppSettings.from_env(env)
    logger.info(
        "runtime app building base_url=%s worker_id=%s run_mode=%s poll_interval_seconds=%s",
        settings.base_url,
        settings.worker_id,
        settings.run_mode,
        settings.poll_interval_seconds,
    )
    config_client = RuntimeConfigClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    callback_client = RuntimeCallbackClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    replay_client = TradeReplayClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    task_client = RuntimeTaskQueueClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    event_client = RuntimeEventClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    initial_runtime_contexts = _resolve_runtime_contexts(settings, config_client, env)
    route_count = len(initial_runtime_contexts) if isinstance(initial_runtime_contexts, list) else 1
    logger.info("runtime routes resolved count=%s", route_count)
    first_runtime_context = initial_runtime_contexts[0] if isinstance(initial_runtime_contexts, list) and initial_runtime_contexts else (
        initial_runtime_contexts if not isinstance(initial_runtime_contexts, list) else RuntimeContext(symbol=settings.default_symbol, exchange="binance")
    )
    memory_model_id_resolver = _build_memory_model_id_resolver(initial_runtime_contexts)
    runner = TradeRuntimeRunner(
        config_client=config_client,
        callback_client=callback_client,
        execution_router=first_runtime_context.execution_router,
    )
    runner.decision_model_client = DecisionModelClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
        timeout=settings.model_call_timeout_seconds,
    )
    runner.memory_store = _build_long_term_memory_store(settings)
    lifecycle_client = TradeLifecycleClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    lifecycle_manager = TradeLifecycleManager(
        lifecycle_client=lifecycle_client,
        memory_store=runner.memory_store,
        model_client=runner.decision_model_client,
        model_id=_resolve_memory_model_id(first_runtime_context.strategy_context),
    )
    runner.lifecycle_manager = lifecycle_manager
    stream_publisher = build_stream_publisher(env)
    stream_consumer = build_stream_consumer(event_client, env)
    env_source = env or os.environ
    initial_market_context_history = _parse_initial_market_context_history(
        env_source.get("TRADE_RUNTIME_INITIAL_MARKET_HISTORY_JSON")
    )
    market_context_history_limit = _parse_market_context_history_limit(
        env_source.get("TRADE_RUNTIME_MARKET_CONTEXT_HISTORY_LIMIT")
    )
    market_context_history_max_age_minutes = _parse_market_context_history_max_age_minutes(
        env_source.get("TRADE_RUNTIME_MARKET_CONTEXT_HISTORY_MAX_AGE_MINUTES")
    )
    runtime_input_supplier = _build_runtime_input_supplier(
        settings=settings,
        event_client=event_client,
        stream_publisher=stream_publisher,
        stream_consumer=stream_consumer,
        initial_exchange=first_runtime_context.exchange,
        initial_symbol=first_runtime_context.symbol,
        default_symbol=settings.default_symbol,
        initial_feed_urls=first_runtime_context.feed_urls,
        initial_market_api_config=first_runtime_context.market_api_config,
        initial_market_context_history=initial_market_context_history,
        market_context_history_limit=market_context_history_limit,
        market_context_history_max_age_minutes=market_context_history_max_age_minutes,
        env=env_source,
    )
    memory_consolidation_job = LongTermMemoryConsolidationJob(
        decision_history_client=HttpDecisionHistoryClient(
            base_url=settings.base_url,
            bearer_token=settings.bearer_token,
        ),
        lifecycle_client=lifecycle_client,
        model_client=runner.decision_model_client,
        memory_store=runner.memory_store,
        current_price_supplier=_build_memory_current_price_supplier(
            runtime_input_supplier=runtime_input_supplier,
            runtime_context=initial_runtime_contexts,
        ),
        window_seconds=int(env_source.get("TRADE_RUNTIME_MEMORY_WINDOW_SECONDS") or "7200"),
        model_id=_resolve_memory_model_id(first_runtime_context.strategy_context),
        model_id_resolver=memory_model_id_resolver,
    )
    return TradeRuntimeApp(
        runner=runner,
        worker_id=settings.worker_id,
        symbol=first_runtime_context.symbol,
        exchange=first_runtime_context.exchange,
        poll_interval_seconds=settings.poll_interval_seconds,
        heartbeat_publisher=callback_client.post_worker_heartbeat,
        runtime_context_supplier=_build_runtime_context_supplier(
            initial_context=initial_runtime_contexts,
            resolver=lambda: _resolve_runtime_contexts(settings, config_client, env),
        ),
        runtime_input_supplier=runtime_input_supplier,
        task_client=task_client,
        replay_runner=TradeReplayRunner(
            replay_client=replay_client,
            runtime_runner=runner,
        ),
        memory_consolidation_job=memory_consolidation_job,
    )


def _build_ai_model_context(ai_model_config: Any) -> dict[str, Any] | None:
    if ai_model_config is None:
        return None
    # 支持驼峰和下划线两种命名方式
    model_code = getattr(ai_model_config, "model_code", None) or getattr(ai_model_config, "modelCode", None)
    model_key = getattr(ai_model_config, "model_key", None) or getattr(ai_model_config, "modelKey", None)
    model_name = getattr(ai_model_config, "model_name", None) or getattr(ai_model_config, "modelName", None)
    api_endpoint = getattr(ai_model_config, "api_endpoint", None) or getattr(ai_model_config, "apiEndpoint", None)
    api_base_url = getattr(ai_model_config, "api_base_url", None) or getattr(ai_model_config, "apiBaseUrl", None)
    api_version = getattr(ai_model_config, "api_version", None) or getattr(ai_model_config, "apiVersion", None)
    model_version = getattr(ai_model_config, "model_version", None) or getattr(ai_model_config, "modelVersion", None)
    timeout_seconds = getattr(ai_model_config, "timeout_seconds", None) or getattr(ai_model_config, "timeoutSeconds", None)
    retry_times = getattr(ai_model_config, "retry_times", None) or getattr(ai_model_config, "retryTimes", None)
    max_tokens = getattr(ai_model_config, "max_tokens", None) or getattr(ai_model_config, "maxTokens", None)
    is_enabled = getattr(ai_model_config, "is_enabled", None) or getattr(ai_model_config, "isEnabled", None)
    is_default = getattr(ai_model_config, "is_default", None) or getattr(ai_model_config, "isDefault", None)
    daily_limit = getattr(ai_model_config, "daily_limit", None) or getattr(ai_model_config, "dailyLimit", None)
    monthly_token_limit = getattr(ai_model_config, "monthly_token_limit", None) or getattr(ai_model_config, "monthlyTokenLimit", None)

    payload = {
        "id": getattr(ai_model_config, "id", None),
        "model_key": model_key,
        "model_code": model_code,
        "model_name": model_name,
        "provider": getattr(ai_model_config, "provider", None),
        "api_endpoint": api_endpoint,
        "api_base_url": api_base_url,
        "api_version": api_version,
        "model_version": model_version,
        "timeout_seconds": timeout_seconds,
        "retry_times": retry_times,
        "priority": getattr(ai_model_config, "priority", None),
        "temperature": getattr(ai_model_config, "temperature", None),
        "top_p": getattr(ai_model_config, "top_p", None) or getattr(ai_model_config, "topP", None),
        "max_tokens": max_tokens,
        "is_enabled": is_enabled,
        "is_default": is_default,
        "daily_limit": daily_limit,
        "monthly_token_limit": monthly_token_limit,
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def _build_prompt_binding_context(prompt_binding: Any) -> dict[str, Any] | None:
    if prompt_binding is None:
        return None
    # 支持驼峰和下划线两种命名方式
    binding_name = getattr(prompt_binding, "binding_name", None) or getattr(prompt_binding, "bindingName", None)
    binding_scope = getattr(prompt_binding, "binding_scope", None) or getattr(prompt_binding, "bindingScope", None)
    template_code = getattr(prompt_binding, "template_code", None) or getattr(prompt_binding, "templateCode", None)
    fallback_template_code = getattr(prompt_binding, "fallback_template_code", None) or getattr(prompt_binding, "fallbackTemplateCode", None)
    model_id = getattr(prompt_binding, "model_id", None) or getattr(prompt_binding, "modelId", None)
    output_schema_code = getattr(prompt_binding, "output_schema_code", None) or getattr(prompt_binding, "outputSchemaCode", None)
    mode_scope_json = getattr(prompt_binding, "mode_scope_json", None) or getattr(prompt_binding, "modeScopeJson", None)
    event_strength_scope_json = getattr(prompt_binding, "event_strength_scope_json", None) or getattr(prompt_binding, "eventStrengthScopeJson", None)

    payload = {
        "id": getattr(prompt_binding, "id", None),
        "binding_name": binding_name,
        "binding_scope": binding_scope,
        "template_code": template_code,
        "fallback_template_code": fallback_template_code,
        "model_id": model_id,
        "output_schema_code": output_schema_code,
        "priority": getattr(prompt_binding, "priority", None),
        "mode_scope_json": mode_scope_json,
        "event_strength_scope_json": event_strength_scope_json,
        "enabled": getattr(prompt_binding, "enabled", None),
        "remark": getattr(prompt_binding, "remark", None),
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def _build_agent_profile_context(agent_profile: Any) -> dict[str, Any] | None:
    if agent_profile is None:
        return None
    # 支持驼峰和下划线两种命名方式
    agent_code = getattr(agent_profile, "agent_code", None) or getattr(agent_profile, "agentCode", None)
    agent_name = getattr(agent_profile, "agent_name", None) or getattr(agent_profile, "agentName", None)
    agent_type = getattr(agent_profile, "agent_type", None) or getattr(agent_profile, "agentType", None)
    llm_enabled = getattr(agent_profile, "llm_enabled", None) or getattr(agent_profile, "llmEnabled", None)
    dialogue_enabled = getattr(agent_profile, "dialogue_enabled", None) or getattr(agent_profile, "dialogueEnabled", None)
    max_dialogue_rounds = getattr(agent_profile, "max_dialogue_rounds", None) or getattr(agent_profile, "maxDialogueRounds", None)
    speak_order = getattr(agent_profile, "speak_order", None) or getattr(agent_profile, "speakOrder", None)
    timeout_seconds = getattr(agent_profile, "timeout_seconds", None) or getattr(agent_profile, "timeoutSeconds", None)
    max_retries = getattr(agent_profile, "max_retries", None) or getattr(agent_profile, "maxRetries", None)
    temperature_override = getattr(agent_profile, "temperature_override", None) or getattr(agent_profile, "temperatureOverride", None)
    top_p_override = getattr(agent_profile, "top_p_override", None) or getattr(agent_profile, "topPOverride", None)
    max_tokens_override = getattr(agent_profile, "max_tokens_override", None) or getattr(agent_profile, "maxTokensOverride", None)
    structured_schema_code = getattr(agent_profile, "structured_schema_code", None) or getattr(agent_profile, "structuredSchemaCode", None)
    tool_policy_json = getattr(agent_profile, "tool_policy_json", None) or getattr(agent_profile, "toolPolicyJson", None)
    runtime_options_json = getattr(agent_profile, "runtime_options_json", None) or getattr(agent_profile, "runtimeOptionsJson", None)
    default_model_id = getattr(agent_profile, "default_model_id", None) or getattr(agent_profile, "defaultModelId", None)
    default_template_code = getattr(agent_profile, "default_template_code", None) or getattr(agent_profile, "defaultTemplateCode", None)
    default_fallback_template_code = getattr(agent_profile, "default_fallback_template_code", None) or getattr(agent_profile, "defaultFallbackTemplateCode", None)
    default_output_schema_code = getattr(agent_profile, "default_output_schema_code", None) or getattr(agent_profile, "defaultOutputSchemaCode", None)

    payload = {
        "id": getattr(agent_profile, "id", None),
        "agent_code": agent_code,
        "agent_name": agent_name,
        "agent_type": agent_type,
        "enabled": getattr(agent_profile, "enabled", None),
        "llm_enabled": llm_enabled,
        "dialogue_enabled": dialogue_enabled,
        "max_dialogue_rounds": max_dialogue_rounds,
        "speak_order": speak_order,
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "temperature_override": temperature_override,
        "top_p_override": top_p_override,
        "max_tokens_override": max_tokens_override,
        "structured_schema_code": structured_schema_code,
        "tool_policy_json": tool_policy_json,
        "runtime_options_json": runtime_options_json,
        "default_model_id": default_model_id,
        "default_template_code": default_template_code,
        "default_fallback_template_code": default_fallback_template_code,
        "default_output_schema_code": default_output_schema_code,
        "remark": getattr(agent_profile, "remark", None),
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def _build_resolved_agent_config_context(config: Any) -> dict[str, Any] | None:
    if config is None:
        return None
    # 支持驼峰和下划线两种命名方式
    agent_code = getattr(config, "agent_code", None) or getattr(config, "agentCode", None)
    agent_type = getattr(config, "agent_type", None) or getattr(config, "agentType", None)
    llm_enabled = getattr(config, "llm_enabled", None) or getattr(config, "llmEnabled", None)
    model_id = getattr(config, "model_id", None) or getattr(config, "modelId", None)
    model_code = getattr(config, "model_code", None) or getattr(config, "modelCode", None)
    model_provider = getattr(config, "model_provider", None) or getattr(config, "modelProvider", None)
    template_code = getattr(config, "template_code", None) or getattr(config, "templateCode", None)
    fallback_template_code = getattr(config, "fallback_template_code", None) or getattr(config, "fallbackTemplateCode", None)
    output_schema_code = getattr(config, "output_schema_code", None) or getattr(config, "outputSchemaCode", None)
    source_profile_id = getattr(config, "source_profile_id", None) or getattr(config, "sourceProfileId", None)
    source_binding_id = getattr(config, "source_binding_id", None) or getattr(config, "sourceBindingId", None)
    resolution_source = getattr(config, "resolution_source", None) or getattr(config, "resolutionSource", None)

    payload = {
        "agent_code": agent_code,
        "agent_type": agent_type,
        "enabled": getattr(config, "enabled", None),
        "llm_enabled": llm_enabled,
        "model_id": model_id,
        "model_code": model_code,
        "model_provider": model_provider,
        "template_code": template_code,
        "fallback_template_code": fallback_template_code,
        "output_schema_code": output_schema_code,
        "source_profile_id": source_profile_id,
        "source_binding_id": source_binding_id,
        "resolution_source": resolution_source,
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def _build_feed_urls(settings: RuntimeAppSettings | None, bootstrap: Any) -> dict[str, str] | None:
    market_data_config = getattr(bootstrap, "market_data_config", None)
    collect_onchain_enabled = _is_enabled_flag(getattr(market_data_config, "collect_onchain", None), default=True)
    news_api_config = getattr(bootstrap, "news_api_config", None)
    onchain_api_config = getattr(bootstrap, "onchain_api_config", None)
    social_api_config = getattr(bootstrap, "social_api_config", None)

    def resolve_source_url(api_config: Any) -> str:
        if api_config is None:
            return ""
        if not _is_enabled_flag(getattr(api_config, "enabled", None), default=True):
            return ""
        return str(getattr(api_config, "api_url", "") or "").strip()

    payload = {
        "news_url": resolve_source_url(news_api_config),
        "onchain_url": (
            resolve_source_url(onchain_api_config)
            if collect_onchain_enabled
            else ""
        ),
        "social_url": resolve_source_url(social_api_config),
    }
    if any(payload.values()):
        return payload
    return None


def _build_market_data_context(market_data_config: Any) -> dict[str, Any] | None:
    if market_data_config is None:
        return None
    payload = {
        "config_name": getattr(market_data_config, "config_name", None),
        "symbol": getattr(market_data_config, "symbol", None),
        "enabled": getattr(market_data_config, "enabled", None),
        "collect_interval": getattr(market_data_config, "collect_interval", None),
        "data_sources": getattr(market_data_config, "data_sources", None),
        "collect_kline": getattr(market_data_config, "collect_kline", None),
        "kline_periods": getattr(market_data_config, "kline_periods", None),
        "collect_fear_greed": getattr(market_data_config, "collect_fear_greed", None),
        "collect_onchain": getattr(market_data_config, "collect_onchain", None),
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def _build_market_api_context(market_api_config: Any) -> dict[str, Any] | None:
    if market_api_config is None:
        return None
    payload = {
        "id": getattr(market_api_config, "id", None),
        "version_no": getattr(market_api_config, "version_no", None),
        "data_category": getattr(market_api_config, "data_category", None),
        "data_sub_type": getattr(market_api_config, "data_sub_type", None),
        "transport_type": getattr(market_api_config, "transport_type", None),
        "vendor_code": getattr(market_api_config, "vendor_code", None),
        "market_scope": getattr(market_api_config, "market_scope", None),
        "api_name": getattr(market_api_config, "api_name", None),
        "api_url": getattr(market_api_config, "api_url", None),
        "ws_base_url": getattr(market_api_config, "ws_base_url", None),
        "ws_path": getattr(market_api_config, "ws_path", None),
        "ws_stream_name_template": getattr(market_api_config, "ws_stream_name_template", None),
        "ws_combined_enabled": getattr(market_api_config, "ws_combined_enabled", None),
        "ws_symbol_lowercase": getattr(market_api_config, "ws_symbol_lowercase", None),
        "ws_ping_interval_seconds": getattr(market_api_config, "ws_ping_interval_seconds", None),
        "ws_pong_timeout_seconds": getattr(market_api_config, "ws_pong_timeout_seconds", None),
        "ws_connection_ttl_hours": getattr(market_api_config, "ws_connection_ttl_hours", None),
        "ws_max_streams_per_connection": getattr(market_api_config, "ws_max_streams_per_connection", None),
        "ws_control_messages_per_second": getattr(market_api_config, "ws_control_messages_per_second", None),
        "doc_reference_url": getattr(market_api_config, "doc_reference_url", None),
        "enabled": getattr(market_api_config, "enabled", None),
        "priority": getattr(market_api_config, "priority", None),
        "update_time": getattr(market_api_config, "update_time", None),
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def _build_market_source_context(market_api_config: Any) -> dict[str, Any] | None:
    if market_api_config is None:
        return None
    payload = {
        "config_id": getattr(market_api_config, "id", None),
        "config_version": getattr(market_api_config, "version_no", None),
        "updated_at": getattr(market_api_config, "update_time", None),
        "transport_type": getattr(market_api_config, "transport_type", None),
        "vendor_code": getattr(market_api_config, "vendor_code", None),
        "market_scope": getattr(market_api_config, "market_scope", None),
    }
    normalized_payload = {
        key: value
        for key, value in payload.items()
        if value not in (None, "")
    }
    if normalized_payload:
        return normalized_payload
    return None


def _build_market_api_cache_key(market_api_config: Any) -> str:
    if market_api_config is None:
        return ""
    context = _build_market_api_context(market_api_config)
    if context is None:
        return ""
    return json.dumps(context, sort_keys=True, ensure_ascii=True)


def build_replay_runner(env: Mapping[str, str] | None = None) -> TradeReplayRunner:
    settings = RuntimeAppSettings.from_env(env)
    config_client = RuntimeConfigClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    callback_client = RuntimeCallbackClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    replay_client = TradeReplayClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    runtime_runner = TradeRuntimeRunner(
        config_client=config_client,
        callback_client=callback_client,
    )
    runtime_runner.decision_model_client = DecisionModelClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
        timeout=settings.model_call_timeout_seconds,
    )
    runtime_runner.memory_store = _build_long_term_memory_store(settings)
    lifecycle_client = TradeLifecycleClient(
        base_url=settings.base_url,
        bearer_token=settings.bearer_token,
    )
    runtime_runner.lifecycle_manager = TradeLifecycleManager(
        lifecycle_client=lifecycle_client,
        memory_store=runtime_runner.memory_store,
        model_client=runtime_runner.decision_model_client,
        model_id=None,
    )
    return TradeReplayRunner(
        replay_client=replay_client,
        runtime_runner=runtime_runner,
    )


def main(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    settings = RuntimeAppSettings.from_env(env)
    if settings.run_mode == "replay":
        if not settings.replay_trace_id:
            raise ValueError("TRADE_RUNTIME_REPLAY_TRACE_ID is required when TRADE_RUNTIME_RUN_MODE=replay")
        return build_replay_runner(env).run_trace(settings.replay_trace_id)
    if settings.run_mode == "forever":
        while True:
            try:
                app = build_runtime_app(env)
                return app.run_forever()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                logger.exception(
                    "runtime startup failed base_url=%s worker_id=%s retry_seconds=%s error=%s",
                    settings.base_url,
                    settings.worker_id,
                    settings.poll_interval_seconds,
                    exc,
                )
                time.sleep(settings.poll_interval_seconds)
    app = build_runtime_app(env)
    return app.run_once()


if __name__ == "__main__":
    main()
