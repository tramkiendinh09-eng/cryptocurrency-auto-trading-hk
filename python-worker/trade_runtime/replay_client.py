from __future__ import annotations

from typing import Any

import requests


class TradeReplayClient:
    def __init__(self, base_url: str, bearer_token: str, timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout

    def build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def get_trace_source(self, trace_id: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/dca/trade/replay/source",
            params={"traceId": trace_id},
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload.get("data") or {}

    def create_replay_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/dca/trade/replay/session",
            json=payload,
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return body.get("data") or {}

    def ensure_session(self, *, source_trace_id: str, session_id: int | None = None, replay_trace_id: str | None = None) -> dict[str, Any]:
        stable_replay_trace_id = replay_trace_id or (
            f"replay-{session_id}-{source_trace_id}" if session_id is not None else f"replay-{source_trace_id}"
        )
        if session_id is None:
            session = self.create_replay_session(
                {
                    "sessionName": f"replay-{source_trace_id}",
                    "sourceTraceId": source_trace_id,
                    "mode": "shadow",
                    "status": "running",
                    "replayTraceId": stable_replay_trace_id,
                }
            )
            session.setdefault("replayTraceId", stable_replay_trace_id)
            return {
                "id": session.get("id"),
                "replay_trace_id": session.get("replayTraceId"),
            }
        self.update_replay_session(
            {
                "id": session_id,
                "status": "running",
                "replayTraceId": stable_replay_trace_id,
            }
        )
        return {
            "id": session_id,
            "replay_trace_id": stable_replay_trace_id,
        }

    def list_source_events(self, trace_id: str) -> list[dict[str, Any]]:
        source = self.get_trace_source(trace_id)
        event_bundle = source.get("eventBundle") or []
        events: list[dict[str, Any]] = []
        for index, payload in enumerate(event_bundle):
            if not isinstance(payload, dict):
                continue
            events.append(
                {
                    "event_time": payload.get("event_time") or payload.get("eventTime") or index,
                    "payload": payload,
                    "symbol": source.get("symbol") or payload.get("symbol") or "",
                    "exchange_code": source.get("exchangeCode") or payload.get("exchange") or "binance",
                }
            )
        return events

    def update_replay_session(self, payload: dict[str, Any]) -> None:
        response = requests.put(
            f"{self.base_url}/dca/trade/replay/session",
            json=payload,
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

    def post_replay_event(self, payload: dict[str, Any]) -> None:
        response = requests.post(
            f"{self.base_url}/dca/trade/replay/event",
            json=payload,
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
