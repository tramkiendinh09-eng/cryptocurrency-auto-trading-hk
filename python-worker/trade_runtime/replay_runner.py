from __future__ import annotations

import json
from typing import Any, Callable
from uuid import uuid4

from trade_runtime.runtime_inputs import build_feature_snapshot_from_events, normalize_event_bundle


def _normalized_event_bundle(source: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = source.get("eventBundle") or []
    return [item for item in bundle if isinstance(item, dict)]


def _feature_snapshot_from_events(event_bundle: list[dict[str, Any]]) -> dict[str, Any]:
    news_score = 0.0
    social_score = 0.0
    onchain_flow_bias = 0.0
    for event in event_bundle:
        event_type = str(event.get("event_type", "")).strip().lower()
        if event_type == "news":
            score = float(event.get("score", 0) or 0)
            if abs(score) >= abs(news_score):
                news_score = score
        elif event_type == "social":
            score = float(event.get("score", 0) or 0)
            if abs(score) >= abs(social_score):
                social_score = score
        elif event_type == "onchain":
            flow = str(event.get("flow", "")).strip().lower()
            if flow == "exchange_outflow":
                onchain_flow_bias = 1.0
            elif flow == "exchange_inflow":
                onchain_flow_bias = -1.0
    return {
        "price_change_pct": 0.0,
        "news_score": news_score,
        "social_score": social_score,
        "onchain_flow_bias": onchain_flow_bias,
    }


class TradeReplayRunner:
    def __init__(
        self,
        *,
        replay_client: Any,
        runtime_runner: Any,
        replay_trace_id_supplier: Callable[[], str] = lambda: uuid4().hex,
    ):
        self.replay_client = replay_client
        self.runtime_runner = runtime_runner
        self.replay_trace_id_supplier = replay_trace_id_supplier

    def run_trace(self, trace_id: str, session_id: int | None = None) -> dict[str, Any]:
        source = self.replay_client.get_trace_source(trace_id)
        source_events = self._source_events(trace_id, source)
        event_bundle = [item["payload"] for item in source_events]
        if not event_bundle:
            raise ValueError(f"Replay source for trace {trace_id} is missing an event bundle")

        requested_replay_trace_id = self.replay_trace_id_supplier()
        session = self._ensure_session(
            source_trace_id=trace_id,
            session_id=session_id,
            replay_trace_id=requested_replay_trace_id,
        )
        session_id = session.get("id")
        replay_trace_id = session.get("replay_trace_id") or requested_replay_trace_id
        if session_id:
            for event in source_events:
                self.replay_client.post_replay_event(
                    {
                        "sessionId": session_id,
                        "traceId": replay_trace_id,
                        "eventType": event["payload"].get("event_type", "unknown"),
                        "symbol": event.get("symbol") or source.get("symbol", ""),
                        "exchangeCode": event.get("exchange_code") or source.get("exchangeCode", "binance"),
                        "payloadJson": json.dumps(event["payload"], ensure_ascii=False, separators=(",", ":"), default=str),
                    }
                )
        try:
            result = self.runtime_runner.run_once(
                trace_id=replay_trace_id,
                symbol=source_events[0].get("symbol") or source.get("symbol", ""),
                exchange=source_events[0].get("exchange_code") or source.get("exchangeCode", "binance"),
                event_bundle=event_bundle,
                feature_snapshot=build_feature_snapshot_from_events(event_bundle),
                mode_override="shadow",
                bypass_trigger_guards=True,
            )
            if session_id and hasattr(self.replay_client, "update_replay_session"):
                self.replay_client.update_replay_session(
                    {
                        "id": session_id,
                        "status": "completed",
                        "replayTraceId": replay_trace_id,
                    }
                )
        except Exception:
            if session_id and hasattr(self.replay_client, "update_replay_session"):
                self.replay_client.update_replay_session(
                    {
                        "id": session_id,
                        "status": "failed",
                        "replayTraceId": replay_trace_id,
                    }
                )
            raise
        return {
            "session_id": session_id,
            "source_trace_id": trace_id,
            "replay_trace_id": replay_trace_id,
            "event_count": len(source_events),
            "events_in_order": source_events == sorted(source_events, key=lambda item: item["event_time"]),
            "execution_result": result.get("execution_result", {}),
            "result": result,
        }

    def _ensure_session(
        self,
        *,
        source_trace_id: str,
        session_id: int | None,
        replay_trace_id: str,
    ) -> dict[str, Any]:
        if hasattr(self.replay_client, "ensure_session"):
            return self.replay_client.ensure_session(
                source_trace_id=source_trace_id,
                session_id=session_id,
                replay_trace_id=replay_trace_id,
            )
        if session_id is not None:
            if hasattr(self.replay_client, "update_replay_session"):
                self.replay_client.update_replay_session(
                    {
                        "id": session_id,
                        "status": "running",
                        "replayTraceId": replay_trace_id,
                    }
                )
            return {
                "id": session_id,
                "replay_trace_id": replay_trace_id,
            }
        if hasattr(self.replay_client, "create_replay_session"):
            session = self.replay_client.create_replay_session(
                {
                    "sessionName": f"replay-{source_trace_id}",
                    "sourceTraceId": source_trace_id,
                    "mode": "shadow",
                    "status": "running",
                    "replayTraceId": replay_trace_id,
                }
            )
            return {
                "id": session.get("id"),
                "replay_trace_id": session.get("replayTraceId") or replay_trace_id,
            }
        return {
            "id": session_id,
            "replay_trace_id": replay_trace_id,
        }

    def _source_events(self, trace_id: str, source: dict[str, Any]) -> list[dict[str, Any]]:
        if hasattr(self.replay_client, "list_source_events"):
            events = self.replay_client.list_source_events(trace_id)
            if events:
                return sorted(events, key=lambda item: item.get("event_time"))
        event_bundle = normalize_event_bundle(_normalized_event_bundle(source))
        return [
            {
                "event_time": event.get("event_time") or event.get("eventTime") or index,
                "payload": event,
                "symbol": source.get("symbol") or event.get("symbol") or "",
                "exchange_code": source.get("exchangeCode") or event.get("exchange") or "binance",
            }
            for index, event in enumerate(event_bundle)
        ]
