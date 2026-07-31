from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

import requests

from trade_runtime.memory.outcome import calculate_outcome_metrics
from trade_runtime.memory.price_pattern import analyze_price_pattern
from trade_runtime.memory.summarizer import create_memory_from_evaluated_decision

logger = logging.getLogger(__name__)


class HttpDecisionHistoryClient:
    def __init__(self, *, base_url: str, bearer_token: str = "", timeout: int = 5):
        self.base_url = str(base_url or "").rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def list_decision_runs(self) -> list[dict[str, Any]]:
        if not self.base_url:
            return []
        response = requests.get(
            f"{self.base_url}/dca/decision/runs",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else payload
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


class LongTermMemoryConsolidationJob:
    """长期记忆整合任务

    整合两个数据源：
    1. trade_lifecycle 表 - 已平仓的交易（优先处理，有完整交易结果）
    2. decision_run 表 - 历史决策记录（后备，只有决策时刻信息）
    """

    def __init__(
        self,
        *,
        decision_history_client: Any,
        lifecycle_client: Any = None,  # 新增：交易生命周期客户端
        model_client: Any,
        memory_store: Any,
        current_price_supplier: Callable[[str], float],
        now_supplier: Callable[[], datetime] | None = None,
        window_seconds: int = 7200,
        model_id: int | None = None,
        model_id_resolver: Callable[[dict[str, Any]], int | None] | None = None,
        max_runs_per_cycle: int = 5,
    ):
        self.decision_history_client = decision_history_client
        self.lifecycle_client = lifecycle_client
        self.model_client = model_client
        self.memory_store = memory_store
        self.current_price_supplier = current_price_supplier
        self.now_supplier = now_supplier or (lambda: datetime.now(timezone.utc))
        self.window_seconds = window_seconds
        self.model_id = model_id
        self.model_id_resolver = model_id_resolver
        self.max_runs_per_cycle = max_runs_per_cycle
        self.processed_trace_ids: set[str] = set()

    def run_once(self) -> dict[str, Any]:
        """运行一次记忆整合

        优先处理已平仓的交易生命周期记录（有完整交易结果）
        然后处理历史决策记录（后备）
        """
        stored_count = 0
        skipped_count = 0
        failed_count = 0
        processed: list[str] = []

        # 优先处理已平仓的交易生命周期记录
        if self.lifecycle_client is not None:
            for lifecycle in self._list_closed_lifecycles():
                trace_id = str(lifecycle.get("trace_id") or lifecycle.get("traceId") or "").strip()
                if not trace_id or trace_id in self.processed_trace_ids:
                    skipped_count += 1
                    continue
                if stored_count >= self.max_runs_per_cycle:
                    break

                try:
                    result = self._process_lifecycle_memory(lifecycle)
                except Exception:
                    failed_count += 1
                    processed.append(trace_id)
                    continue

                processed.append(trace_id)
                if result.get("status") != "failed":
                    self.processed_trace_ids.add(trace_id)

                if result.get("status") == "stored":
                    stored_count += 1
                elif result.get("status") == "failed":
                    failed_count += 1
                else:
                    skipped_count += 1

            # 如果处理了足够的交易生命周期，直接返回
            if stored_count >= self.max_runs_per_cycle:
                return {
                    "stored_count": stored_count,
                    "skipped_count": skipped_count,
                    "failed_count": failed_count,
                    "processed_trace_ids": processed,
                    "source": "lifecycle",
                }

        # 处理历史决策记录（后备）
        for decision in self.decision_history_client.list_decision_runs():
            trace_id = str(decision.get("traceId") or decision.get("trace_id") or "").strip()
            if not trace_id or trace_id in self.processed_trace_ids:
                skipped_count += 1
                continue
            if stored_count >= self.max_runs_per_cycle:
                break
            evaluation = self._build_evaluation(decision)
            if evaluation is None:
                skipped_count += 1
                continue
            try:
                result = create_memory_from_evaluated_decision(
                    decision_payload=decision,
                    outcome_metrics=evaluation,
                    model_client=self.model_client,
                    memory_store=self.memory_store,
                    model_id=self._resolve_model_id(decision),
                )
            except Exception:
                failed_count += 1
                self.processed_trace_ids.add(trace_id)
                processed.append(trace_id)
                continue
            self.processed_trace_ids.add(trace_id)
            processed.append(trace_id)
            if result.get("status") == "stored":
                stored_count += 1
            elif result.get("status") == "failed":
                failed_count += 1
            else:
                skipped_count += 1

        return {
            "stored_count": stored_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "processed_trace_ids": processed,
            "source": "mixed",
        }

    def _list_closed_lifecycles(self) -> list[dict[str, Any]]:
        """获取已平仓的交易生命周期列表"""
        if self.lifecycle_client is None:
            return []
        try:
            return self.lifecycle_client.list_closed_lifecycles(limit=self.max_runs_per_cycle * 2)
        except Exception:
            return []

    def _process_lifecycle_memory(self, lifecycle: dict[str, Any]) -> dict[str, Any]:
        """处理交易生命周期记录，生成记忆

        复用现有的 create_memory_from_evaluated_decision 函数
        """
        trace_id = str(lifecycle.get("trace_id") or lifecycle.get("traceId") or "").strip()
        symbol = str(lifecycle.get("symbol") or "").strip().upper()
        side = str(lifecycle.get("side") or "long").strip().lower()
        entry_price = float(lifecycle.get("entry_price") or lifecycle.get("entryPrice") or 0)
        exit_price = float(lifecycle.get("exit_price") or lifecycle.get("exitPrice") or 0)
        realized_pnl_pct = float(lifecycle.get("realized_pnl_pct") or lifecycle.get("realizedPnlPct") or 0)
        holding_minutes = int(lifecycle.get("holding_minutes") or lifecycle.get("holdingMinutes") or 0)
        exit_reason = str(lifecycle.get("exit_reason") or lifecycle.get("exitReason") or "").strip()

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
            "summary_reason": str(lifecycle.get("entry_reason") or lifecycle.get("entryReason") or "").strip(),
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
        result = create_memory_from_evaluated_decision(
            decision_payload=decision_payload,
            outcome_metrics=outcome_metrics,
            model_client=self.model_client,
            memory_store=self.memory_store,
            model_id=self._resolve_model_id(lifecycle),
        )
        if self.lifecycle_client is not None and trace_id:
            stored_memory = result.get("memory") or result.get("candidate") or {}
            self.lifecycle_client.update_lifecycle(
                trace_id,
                {
                    "memory_generated": result.get("status") == "stored",
                    "lesson_text": str(stored_memory.get("lesson_text") or ""),
                    "memory_status": str(result.get("status") or ""),
                    "memory_reason": str(result.get("reason") or ""),
                },
            )
        return result

    def _resolve_model_id(self, payload: dict[str, Any]) -> int | None:
        if callable(self.model_id_resolver):
            try:
                resolved = self.model_id_resolver(payload)
            except Exception:
                resolved = None
            if resolved is not None:
                return resolved
        return self.model_id

    def _build_evaluation(self, decision: dict[str, Any]) -> dict[str, Any] | None:
        created_at = _parse_datetime(decision.get("createdAt") or decision.get("created_at"))
        if created_at is None:
            return None
        now = self.now_supplier()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        if (now - created_at).total_seconds() < self.window_seconds:
            return None
        symbol = str(decision.get("symbol") or "").strip().upper()
        action = str(decision.get("action") or "").strip().upper()
        side = _resolve_side(decision, action)
        if not symbol or side not in {"long", "short"}:
            return None
        entry_price = _extract_entry_price(decision)
        if entry_price <= 0:
            return None
        current_price = float(self.current_price_supplier(symbol) or 0.0)
        if current_price <= 0:
            return None
        metrics = calculate_outcome_metrics(
            entry_price=entry_price,
            side=side,
            future_prices=[current_price],
            realized_pnl=0.0,
        )
        metrics.update(
            {
                "window_seconds": self.window_seconds,
                "entry_price": entry_price,
                "evaluation_price": current_price,
                "evaluated_at": now.isoformat(),
            }
        )
        return metrics


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _resolve_side(decision: dict[str, Any], action: str) -> str:
    side = str(decision.get("side") or "").strip().lower()
    if side in {"long", "short"}:
        return side
    if "LONG" in action:
        return "long"
    if "SHORT" in action:
        return "short"
    return ""


def _extract_entry_price(decision: dict[str, Any]) -> float:
    candidates = [
        decision.get("entryPrice"),
        decision.get("entry_price"),
        decision.get("price"),
    ]
    feature_snapshot = decision.get("featureSnapshot") or decision.get("feature_snapshot") or {}
    if isinstance(feature_snapshot, dict):
        snapshot = feature_snapshot.get("snapshot") or {}
        if not snapshot and feature_snapshot.get("snapshotJson"):
            try:
                snapshot = json.loads(feature_snapshot.get("snapshotJson") or "{}")
            except (TypeError, ValueError):
                snapshot = {}
        if isinstance(snapshot, dict):
            candidates.extend(_walk_price_candidates(snapshot))
    for value in candidates:
        try:
            price = float(value or 0.0)
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
    return 0.0


def _walk_price_candidates(value: Any) -> list[Any]:
    candidates: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in {"price", "latest_price", "latestprice", "last_price", "entry_price", "entryprice"}:
                candidates.append(child)
            candidates.extend(_walk_price_candidates(child))
    elif isinstance(value, list):
        for child in value:
            candidates.extend(_walk_price_candidates(child))
    return candidates
