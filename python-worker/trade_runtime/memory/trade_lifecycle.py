"""
交易生命周期管理模块

负责追踪每笔交易从开仓到平仓的完整过程，并自动生成记忆。

融入现有记忆链路：
1. 开仓时记录到 trade_lifecycle 表
2. 平仓时更新记录并调用现有的 create_memory_from_evaluated_decision
3. 记忆存储到现有的 agent_memory 表
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from trade_runtime.execution.status import (
    execution_moved_position,
    execution_status_of,
)
from trade_runtime.memory.price_pattern import analyze_price_pattern

logger = logging.getLogger(__name__)

#: 会改变仓位的动作。只有这些需要"确实成交了"作为前置条件；
#: SKIP/HOLD 本来就不写生命周期。
_POSITION_MUTATING_ACTIONS = frozenset(
    {"OPEN_LONG", "OPEN_SHORT", "ADD_LONG", "ADD_SHORT", "REDUCE", "CLOSE"}
)


class TradeLifecycleClient:
    """交易生命周期HTTP客户端

    用于与后端API交互，管理trade_lifecycle表
    """

    def __init__(self, *, base_url: str, bearer_token: str = "", timeout: int = 5):
        self.base_url = str(base_url or "").rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def create_lifecycle(self, lifecycle: dict[str, Any]) -> dict[str, Any]:
        """创建交易生命周期记录"""
        if not self.base_url:
            return {"id": 0, **lifecycle}
        import requests
        response = requests.post(
            f"{self.base_url}/dca/trade-lifecycle",
            json=self._to_camel_payload(lifecycle),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else payload
        return data if isinstance(data, dict) else {}

    def get_lifecycle(self, trace_id: str) -> dict[str, Any] | None:
        """获取交易生命周期记录"""
        if not self.base_url:
            return None
        import requests
        response = requests.get(
            f"{self.base_url}/dca/trade-lifecycle/{trace_id}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else payload
        return data if isinstance(data, dict) else None

    def update_lifecycle(self, trace_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """更新交易生命周期记录"""
        if not self.base_url:
            return {}
        import requests
        response = requests.patch(
            f"{self.base_url}/dca/trade-lifecycle/{trace_id}",
            json=self._to_camel_payload(updates),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else payload
        return data if isinstance(data, dict) else {}

    def list_closed_lifecycles(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取已平仓的交易生命周期列表（用于记忆生成）"""
        if not self.base_url:
            return []
        import requests
        response = requests.get(
            f"{self.base_url}/dca/trade-lifecycle/closed",
            params={"limit": limit},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else payload
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    # application.yml pins Jackson to `yyyy-MM-dd HH:mm:ss` in GMT+8. isoformat()
    # emits microseconds and a UTC offset, which Jackson rejects outright:
    # "Cannot deserialize value of type java.util.Date ... not a valid
    # representation". The write then fails with HTTP 200 and a 500 body, so
    # nothing surfaced.
    _BACKEND_TZ = timezone(timedelta(hours=8))

    @classmethod
    def _format_datetime(cls, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(cls._BACKEND_TZ).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _camel(key: str) -> str:
        """snake_case -> camelCase，已是驼峰的键原样返回。

        原实现是一张手写映射表，唯独漏了 trace_id，于是后端收到的载荷缺少
        traceId 并返回 {"code":500,"msg":"traceId is required"}——而 RuoYi 的
        业务错误走 HTTP 200，raise_for_status() 不会拦下，调用方拿到空 data
        仍报告 "recorded"。整条生命周期/复盘链路因此从未落过一行数据。
        改成通用转换，任何字段都不会再被遗漏。
        """
        if "_" not in key:
            return key
        head, *rest = key.split("_")
        return head + "".join(part[:1].upper() + part[1:] for part in rest if part)

    def _to_camel_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """转换为驼峰命名"""
        camel_map = {
            "exchange_code": "exchangeCode",
            "entry_price": "entryPrice",
            "entry_time": "entryTime",
            "entry_reason": "entryReason",
            "entry_conditions_json": "entryConditionsJson",
            "agent_views_json": "agentViewsJson",
            "supervisor_decision_json": "supervisorDecisionJson",
            "price_trajectory_json": "priceTrajectoryJson",
            "max_favorable_pct": "maxFavorablePct",
            "max_adverse_pct": "maxAdversePct",
            "holding_minutes": "holdingMinutes",
            "exit_price": "exitPrice",
            "exit_time": "exitTime",
            "exit_reason": "exitReason",
            "realized_pnl_pct": "realizedPnlPct",
            "memory_generated": "memoryGenerated",
            "lesson_text": "lessonText",
            "memory_status": "memoryStatus",
            "memory_reason": "memoryReason",
            "add_operations_json": "addOperationsJson",
            "reduce_operations_json": "reduceOperationsJson",
        }
        result = {}
        for key, value in payload.items():
            camel_key = camel_map.get(key) or self._camel(key)
            if isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, datetime):
                value = self._format_datetime(value)
            result[camel_key] = value
        return result


class TradeLifecycleManager:
    """交易生命周期管理器

    职责：
    1. 记录开仓决策和条件
    2. 追踪持仓过程中的价格波动
    3. 记录平仓结果
    4. 自动生成交易记忆（复用现有记忆链路）
    """

    def __init__(
        self,
        *,
        lifecycle_client: TradeLifecycleClient,
        memory_store: Any,
        model_client: Any,
        model_id: int | None = None,
        now_supplier: Callable[[], datetime] | None = None,
    ):
        self.lifecycle_client = lifecycle_client
        self.memory_store = memory_store
        self.model_client = model_client
        self.model_id = model_id
        self.now_supplier = now_supplier or (lambda: datetime.now(timezone.utc))

    def _persistence_enabled(self) -> bool:
        if self.lifecycle_client is None:
            return False
        base_url = getattr(self.lifecycle_client, "base_url", None)
        if base_url is None:
            return True
        return bool(str(base_url or "").strip())

    def record_entry(
        self,
        *,
        trace_id: str,
        symbol: str,
        exchange: str,
        side: str,
        entry_price: float,
        entry_time: datetime | None = None,
        supervisor_decision: dict[str, Any] | None = None,
        agent_views: dict[str, Any] | None = None,
        feature_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """记录开仓

        Args:
            trace_id: 决策追踪ID
            symbol: 交易品种
            exchange: 交易所
            side: 方向 (long/short)
            entry_price: 入场价格
            entry_time: 入场时间
            supervisor_decision: 主管决策
            agent_views: 各Agent观点
            feature_snapshot: 特征快照

        Returns:
            创建的生命周期记录
        """
        if not self._persistence_enabled():
            return {
                "status": "disabled",
                "operation": "entry",
                "trace_id": trace_id,
                "reason": "lifecycle_store_disabled",
            }
        if entry_time is None:
            entry_time = self.now_supplier()

        entry_conditions = self._extract_entry_conditions(feature_snapshot)

        lifecycle = {
            "trace_id": trace_id,
            "symbol": symbol,
            "exchange_code": exchange,
            "side": side,
            "entry_price": entry_price,
            "entry_time": entry_time,
            "entry_reason": (supervisor_decision or {}).get("summary_reason", ""),
            "entry_conditions_json": entry_conditions,
            "agent_views_json": agent_views or {},
            "supervisor_decision_json": supervisor_decision or {},
            "price_trajectory_json": [],
            "max_favorable_pct": 0.0,
            "max_adverse_pct": 0.0,
            "holding_minutes": 0,
        }

        created = self.lifecycle_client.create_lifecycle(lifecycle)
        return {
            "status": "recorded",
            "operation": "entry",
            "trace_id": trace_id,
            "lifecycle": created if isinstance(created, dict) else {},
        }

    def record_exit(
        self,
        *,
        trace_id: str,
        exit_price: float,
        exit_time: datetime | None = None,
        exit_reason: str = "",
        generate_memory: bool = True,
    ) -> dict[str, Any]:
        """记录平仓并自动生成记忆

        Args:
            trace_id: 追踪ID
            exit_price: 平仓价格
            exit_time: 平仓时间
            exit_reason: 平仓原因
            generate_memory: 是否自动生成记忆

        Returns:
            生成的记忆（如果有）
        """
        if not self._persistence_enabled():
            return {
                "status": "disabled",
                "operation": "exit",
                "trace_id": trace_id,
                "reason": "lifecycle_store_disabled",
                "memory_status": "disabled",
                "memory_reason": "memory_store_disabled",
            }
        lifecycle = self.lifecycle_client.get_lifecycle(trace_id)
        if not lifecycle:
            return {
                "status": "missing",
                "operation": "exit",
                "trace_id": trace_id,
                "reason": "lifecycle_not_found",
                "memory_status": "skipped",
                "memory_reason": "lifecycle_not_found",
            }

        if exit_time is None:
            exit_time = self.now_supplier()

        entry_price = float(lifecycle.get("entry_price") or lifecycle.get("entryPrice") or 0)
        side = lifecycle.get("side") or lifecycle.get("side", "long")
        entry_time_str = lifecycle.get("entry_time") or lifecycle.get("entryTime")

        # 计算最终盈亏
        if side == "long":
            realized_pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        else:
            realized_pnl_pct = ((entry_price - exit_price) / entry_price) * 100 if entry_price > 0 else 0

        # 计算持仓时长
        holding_minutes = 0
        if entry_time_str:
            try:
                if isinstance(entry_time_str, str):
                    entry_time_dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                else:
                    entry_time_dt = entry_time_str
                holding_minutes = int((exit_time - entry_time_dt).total_seconds() / 60)
            except Exception:
                holding_minutes = 0

        # 更新生命周期记录
        self.lifecycle_client.update_lifecycle(trace_id, {
            "exit_price": exit_price,
            "exit_time": exit_time,
            "exit_reason": exit_reason,
            "realized_pnl_pct": round(realized_pnl_pct, 6),
            "holding_minutes": max(0, holding_minutes),
        })

        memory_result = {"status": "not_requested", "reason": ""}
        if generate_memory:
            memory_result = self._generate_memory(
                lifecycle=lifecycle,
                exit_price=exit_price,
                exit_time=exit_time,
                exit_reason=exit_reason,
                realized_pnl_pct=realized_pnl_pct,
                holding_minutes=holding_minutes,
            )

            stored_memory = memory_result.get("memory") or memory_result.get("candidate") or {}
            self.lifecycle_client.update_lifecycle(
                trace_id,
                {
                    "memory_generated": memory_result.get("status") == "stored",
                    "lesson_text": str(stored_memory.get("lesson_text") or ""),
                    "memory_status": str(memory_result.get("status") or "not_requested"),
                    "memory_reason": str(memory_result.get("reason") or ""),
                },
            )

        return {
            "status": "recorded",
            "operation": "exit",
            "trace_id": trace_id,
            "memory_status": str(memory_result.get("status") or "not_requested"),
            "memory_reason": str(memory_result.get("reason") or ""),
            "memory": memory_result.get("memory") or memory_result.get("candidate") or {},
        }

    def record_add(
        self,
        *,
        trace_id: str,
        add_price: float,
        add_trace_id: str = "",
    ) -> dict[str, Any]:
        """记录加仓操作

        Args:
            trace_id: 开仓时的trace_id
            add_price: 加仓价格
            add_trace_id: 加仓决策的trace_id

        Returns:
            更新后的生命周期记录
        """
        if not self._persistence_enabled():
            return {
                "status": "disabled",
                "operation": "add",
                "trace_id": trace_id,
                "reason": "lifecycle_store_disabled",
            }
        lifecycle = self.lifecycle_client.get_lifecycle(trace_id)
        if not lifecycle:
            logger.warning("Cannot record add: lifecycle not found for trace_id=%s", trace_id)
            return {
                "status": "missing",
                "operation": "add",
                "trace_id": trace_id,
                "reason": "lifecycle_not_found",
            }

        # 获取现有的加仓记录
        add_operations = lifecycle.get("add_operations_json") or lifecycle.get("addOperationsJson") or []
        if isinstance(add_operations, str):
            try:
                add_operations = json.loads(add_operations)
            except Exception:
                add_operations = []
        if not isinstance(add_operations, list):
            add_operations = []

        # 添加新的加仓记录
        add_operations.append({
            "add_trace_id": add_trace_id,
            "add_price": add_price,
            "add_time": self.now_supplier().isoformat(),
        })

        # 更新lifecycle记录
        self.lifecycle_client.update_lifecycle(trace_id, {
            "add_operations_json": add_operations,
        })

        return {
            "status": "recorded",
            "operation": "add",
            "trace_id": trace_id,
            "lifecycle": lifecycle,
        }

    def record_reduce(
        self,
        *,
        trace_id: str,
        reduce_price: float,
        reduce_trace_id: str = "",
    ) -> dict[str, Any]:
        """记录减仓操作

        Args:
            trace_id: 开仓时的trace_id
            reduce_price: 减仓价格
            reduce_trace_id: 减仓决策的trace_id

        Returns:
            更新后的生命周期记录
        """
        if not self._persistence_enabled():
            return {
                "status": "disabled",
                "operation": "reduce",
                "trace_id": trace_id,
                "reason": "lifecycle_store_disabled",
            }
        lifecycle = self.lifecycle_client.get_lifecycle(trace_id)
        if not lifecycle:
            logger.warning("Cannot record reduce: lifecycle not found for trace_id=%s", trace_id)
            return {
                "status": "missing",
                "operation": "reduce",
                "trace_id": trace_id,
                "reason": "lifecycle_not_found",
            }

        # 获取现有的减仓记录
        reduce_operations = lifecycle.get("reduce_operations_json") or lifecycle.get("reduceOperationsJson") or []
        if isinstance(reduce_operations, str):
            try:
                reduce_operations = json.loads(reduce_operations)
            except Exception:
                reduce_operations = []
        if not isinstance(reduce_operations, list):
            reduce_operations = []

        # 添加新的减仓记录
        reduce_operations.append({
            "reduce_trace_id": reduce_trace_id,
            "reduce_price": reduce_price,
            "reduce_time": self.now_supplier().isoformat(),
        })

        # 更新lifecycle记录
        self.lifecycle_client.update_lifecycle(trace_id, {
            "reduce_operations_json": reduce_operations,
        })

        return {
            "status": "recorded",
            "operation": "reduce",
            "trace_id": trace_id,
            "lifecycle": lifecycle,
        }

    def _extract_entry_conditions(self, feature_snapshot: dict[str, Any] | None) -> dict[str, Any]:
        """提取开仓条件摘要"""
        if not feature_snapshot:
            return {}
        return {
            "event_strength": feature_snapshot.get("event_strength"),
            "price_change_pct": feature_snapshot.get("price_change_pct"),
            "funding_rate": feature_snapshot.get("funding_rate"),
            "wyckoff_shortterm": feature_snapshot.get("wyckoff_shortterm"),
            "kline_volume_price_signals": feature_snapshot.get("kline_volume_price_signals"),
        }

    def _generate_memory(
        self,
        lifecycle: dict[str, Any],
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
        realized_pnl_pct: float,
        holding_minutes: int,
    ) -> dict[str, Any]:
        """自动生成交易记忆

        复用现有的 create_memory_from_evaluated_decision 函数
        """
        from trade_runtime.memory.summarizer import create_memory_from_evaluated_decision

        trace_id = lifecycle.get("trace_id") or lifecycle.get("traceId", "")
        symbol = lifecycle.get("symbol") or lifecycle.get("symbol", "")
        side = lifecycle.get("side") or lifecycle.get("side", "long")
        entry_price = float(lifecycle.get("entry_price") or lifecycle.get("entryPrice") or 0)

        # 获取原始数据（兼容驼峰和下划线命名）
        entry_conditions = lifecycle.get("entry_conditions_json") or lifecycle.get("entryConditionsJson") or {}
        if isinstance(entry_conditions, str):
            try:
                entry_conditions = json.loads(entry_conditions)
            except Exception:
                entry_conditions = {}

        agent_views = lifecycle.get("agent_views_json") or lifecycle.get("agentViewsJson") or {}
        if isinstance(agent_views, str):
            try:
                agent_views = json.loads(agent_views)
            except Exception:
                agent_views = {}

        supervisor_decision = lifecycle.get("supervisor_decision_json") or lifecycle.get("supervisorDecisionJson") or {}
        if isinstance(supervisor_decision, str):
            try:
                supervisor_decision = json.loads(supervisor_decision)
            except Exception:
                supervisor_decision = {}

        price_trajectory = lifecycle.get("price_trajectory_json") or lifecycle.get("priceTrajectoryJson") or []
        if isinstance(price_trajectory, str):
            try:
                price_trajectory = json.loads(price_trajectory)
            except Exception:
                price_trajectory = []

        # 分析价格轨迹模式
        pattern = analyze_price_pattern(price_trajectory)

        # 构建决策载荷
        decision_payload = {
            "traceId": trace_id,
            "symbol": symbol,
            "action": "OPEN_LONG" if side == "long" else "OPEN_SHORT",
            "side": side,
            "summary_reason": lifecycle.get("entry_reason") or lifecycle.get("entryReason", ""),
            "featureSnapshot": {"snapshot": entry_conditions},
            "agentViews": agent_views,
            "supervisorDecision": supervisor_decision,
        }

        # 构建结果指标（使用真实的交易结果）
        outcome_metrics = {
            "realized_pnl_pct": round(realized_pnl_pct, 6),
            "max_favorable_pct": float(lifecycle.get("max_favorable_pct") or lifecycle.get("maxFavorablePct") or 0),
            "max_adverse_pct": float(lifecycle.get("max_adverse_pct") or lifecycle.get("maxAdversePct") or 0),
            "holding_minutes": holding_minutes,
            "exit_reason": exit_reason,
            "price_pattern": pattern,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "evaluated_at": self.now_supplier().isoformat(),
            "final_move_pct": round(realized_pnl_pct, 6),
            "mfe_pct": float(lifecycle.get("max_favorable_pct") or lifecycle.get("maxFavorablePct") or 0),
            "mae_pct": float(lifecycle.get("max_adverse_pct") or lifecycle.get("maxAdversePct") or 0),
        }

        # 复用现有的记忆生成函数
        try:
            result = create_memory_from_evaluated_decision(
                decision_payload=decision_payload,
                outcome_metrics=outcome_metrics,
                model_client=self.model_client,
                memory_store=self.memory_store,
                model_id=self.model_id,
            )
            if result.get("status") == "stored":
                return result
            logger.warning(
                "Memory generation did not store for trace_id=%s: status=%s reason=%s",
                trace_id,
                result.get("status"),
                result.get("reason"),
            )
            return result
        except Exception as e:
            logger.warning("Failed to generate memory for trace_id=%s: %s", trace_id, e)
            return {"status": "failed", "reason": str(e).strip() or e.__class__.__name__}


def process_trade_lifecycle(
    *,
    state: dict[str, Any],
    lifecycle_manager: TradeLifecycleManager | None,
    account_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process lifecycle persistence for a completed decision state."""
    if lifecycle_manager is None:
        return {"status": "disabled", "reason": "lifecycle_manager_unavailable"}

    supervisor_decision = state.get("supervisor_decision")
    if not isinstance(supervisor_decision, dict):
        return {"status": "skipped", "reason": "no_supervisor_decision"}

    execution_result = state.get("execution_result")
    if not isinstance(execution_result, dict):
        execution_result = {}

    normalized_account_context = (
        account_context
        if isinstance(account_context, dict)
        else (
            state.get("runtime_account_context")
            if isinstance(state.get("runtime_account_context"), dict)
            else {}
        )
    )

    action = str(supervisor_decision.get("action") or "").strip().upper()
    trace_id = state.get("trace_id")
    symbol = state.get("symbol")
    exchange = state.get("exchange")

    # 生命周期记的是仓位，不是意图。此前这里只看模型给了什么动作，从不
    # 检查这一单到底成没成交——而 router 即使返回 skipped 也会带上
    # entry_price，前置条件照样满足。结果是两笔被交易所以"低于该标的最小
    # 名义金额"拒掉的 ETH 单，各留下一条 exit_time 永远为空的持仓记录，
    # 记着两笔从未存在过的仓位，还会污染后续的交易记忆。
    if action in _POSITION_MUTATING_ACTIONS and not execution_moved_position(execution_result):
        status = execution_status_of(execution_result) or "unknown"
        logger.debug(
            "Skipping lifecycle %s: execution did not move the position (status=%s) trace_id=%s",
            action,
            status,
            trace_id,
        )
        return {
            "status": "skipped",
            "operation": "entry" if action in {"OPEN_LONG", "OPEN_SHORT"} else action.lower(),
            "reason": f"execution_not_filled:{status}",
            "trace_id": trace_id,
        }

    if action in {"OPEN_LONG", "OPEN_SHORT"}:
        side = "long" if "LONG" in action else "short"
        entry_price = float(
            execution_result.get("entry_price")
            or execution_result.get("fill_price")
            or supervisor_decision.get("entry_price")
            or normalized_account_context.get("entry_price")
            or 0
        )
        if entry_price <= 0:
            logger.debug("Skipping lifecycle entry: no valid entry_price for %s", action)
            return {"status": "skipped", "operation": "entry", "reason": "invalid_entry_price", "trace_id": trace_id}

        try:
            lifecycle_result = lifecycle_manager.record_entry(
                trace_id=trace_id,
                symbol=symbol,
                exchange=exchange,
                side=side,
                entry_price=entry_price,
                supervisor_decision=supervisor_decision,
                agent_views={
                    "market_view": state.get("market_view"),
                    "news_view": state.get("news_view"),
                    "onchain_view": state.get("onchain_view"),
                    "social_view": state.get("social_view"),
                },
                feature_snapshot=state.get("feature_snapshot"),
            )
            logger.info("Recorded lifecycle entry: trace_id=%s, symbol=%s, side=%s", trace_id, symbol, side)
            if isinstance(lifecycle_result, dict) and lifecycle_result.get("status"):
                return lifecycle_result
            return {"status": "recorded", "operation": "entry", "trace_id": trace_id}
        except Exception as exc:
            logger.warning("Failed to record lifecycle entry for trace_id=%s: %s", trace_id, exc)
            return {
                "status": "failed",
                "operation": "entry",
                "trace_id": trace_id,
                "reason": str(exc).strip() or exc.__class__.__name__,
            }

    if action in {"ADD_LONG", "ADD_SHORT"}:
        entry_trace_id = normalized_account_context.get("entry_trace_id") or normalized_account_context.get("entryTraceId")
        if not entry_trace_id:
            logger.debug("Skipping ADD operation lifecycle update: no entry_trace_id")
            return {"status": "skipped", "operation": "add", "reason": "missing_entry_trace_id", "trace_id": trace_id}
        add_price = float(
            execution_result.get("fill_price")
            or supervisor_decision.get("entry_price")
            or normalized_account_context.get("current_price")
            or 0
        )
        if add_price <= 0:
            logger.debug("Skipping ADD operation lifecycle update: no valid add_price")
            return {"status": "skipped", "operation": "add", "reason": "invalid_add_price", "trace_id": entry_trace_id}
        try:
            lifecycle_result = lifecycle_manager.record_add(
                trace_id=entry_trace_id,
                add_price=add_price,
                add_trace_id=trace_id,
            )
            logger.info("Recorded lifecycle add: entry_trace_id=%s, add_price=%s", entry_trace_id, add_price)
            if isinstance(lifecycle_result, dict) and lifecycle_result.get("status"):
                return lifecycle_result
            return {"status": "recorded", "operation": "add", "trace_id": entry_trace_id}
        except Exception as exc:
            logger.warning("Failed to record lifecycle add for entry_trace_id=%s: %s", entry_trace_id, exc)
            return {
                "status": "failed",
                "operation": "add",
                "trace_id": entry_trace_id,
                "reason": str(exc).strip() or exc.__class__.__name__,
            }

    if action == "REDUCE":
        entry_trace_id = normalized_account_context.get("entry_trace_id") or normalized_account_context.get("entryTraceId")
        if not entry_trace_id:
            logger.debug("Skipping REDUCE operation lifecycle update: no entry_trace_id")
            return {"status": "skipped", "operation": "reduce", "reason": "missing_entry_trace_id", "trace_id": trace_id}
        reduce_price = float(
            execution_result.get("fill_price")
            or supervisor_decision.get("exit_price")
            or normalized_account_context.get("current_price")
            or 0
        )
        if reduce_price <= 0:
            logger.debug("Skipping REDUCE operation lifecycle update: no valid reduce_price")
            return {"status": "skipped", "operation": "reduce", "reason": "invalid_reduce_price", "trace_id": entry_trace_id}
        try:
            lifecycle_result = lifecycle_manager.record_reduce(
                trace_id=entry_trace_id,
                reduce_price=reduce_price,
                reduce_trace_id=trace_id,
            )
            logger.info("Recorded lifecycle reduce: entry_trace_id=%s, reduce_price=%s", entry_trace_id, reduce_price)
            if isinstance(lifecycle_result, dict) and lifecycle_result.get("status"):
                return lifecycle_result
            return {"status": "recorded", "operation": "reduce", "trace_id": entry_trace_id}
        except Exception as exc:
            logger.warning("Failed to record lifecycle reduce for entry_trace_id=%s: %s", entry_trace_id, exc)
            return {
                "status": "failed",
                "operation": "reduce",
                "trace_id": entry_trace_id,
                "reason": str(exc).strip() or exc.__class__.__name__,
            }

    if action == "CLOSE":
        exit_price = float(
            execution_result.get("fill_price")
            or supervisor_decision.get("exit_price")
            or normalized_account_context.get("current_price")
            or 0
        )
        if exit_price <= 0:
            logger.debug("Skipping lifecycle exit: no valid exit_price")
            return {"status": "skipped", "operation": "exit", "reason": "invalid_exit_price", "trace_id": trace_id}

        exit_reason = str(supervisor_decision.get("summary_reason") or supervisor_decision.get("invalidation") or "").strip()
        entry_trace_id = normalized_account_context.get("entry_trace_id") or normalized_account_context.get("entryTraceId")
        effective_trace_id = entry_trace_id or trace_id

        try:
            lifecycle_result = lifecycle_manager.record_exit(
                trace_id=effective_trace_id,
                exit_price=exit_price,
                exit_reason=exit_reason,
                generate_memory=True,
            )
            logger.info("Recorded lifecycle exit: trace_id=%s, exit_price=%s", effective_trace_id, exit_price)
            if isinstance(lifecycle_result, dict) and lifecycle_result.get("status"):
                return lifecycle_result
            return {"status": "recorded", "operation": "exit", "trace_id": effective_trace_id}
        except Exception as exc:
            logger.warning("Failed to record lifecycle exit for trace_id=%s: %s", effective_trace_id, exc)
            return {
                "status": "failed",
                "operation": "exit",
                "trace_id": effective_trace_id,
                "reason": str(exc).strip() or exc.__class__.__name__,
                "memory_status": "failed",
                "memory_reason": str(exc).strip() or exc.__class__.__name__,
            }

    return {"status": "skipped", "reason": "unsupported_action", "trace_id": trace_id}


def trade_memory_status_from_lifecycle(lifecycle_status: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(lifecycle_status, dict):
        return None
    memory_status = str(lifecycle_status.get("memory_status") or "").strip()
    if not memory_status:
        return None
    memory_payload = lifecycle_status.get("memory")
    if not isinstance(memory_payload, dict):
        memory_payload = {}
    return {
        "status": memory_status,
        "reason": str(lifecycle_status.get("memory_reason") or "").strip(),
        "trace_id": lifecycle_status.get("trace_id"),
        "lesson_text": str(memory_payload.get("lesson_text") or memory_payload.get("lessonText") or "").strip(),
    }


def apply_trade_lifecycle_status(state: dict[str, Any], lifecycle_status: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(lifecycle_status, dict) or not lifecycle_status:
        return state
    state["lifecycle_status"] = lifecycle_status
    trade_memory_status = trade_memory_status_from_lifecycle(lifecycle_status)
    if trade_memory_status is not None:
        state["trade_memory_status"] = trade_memory_status
    return state
