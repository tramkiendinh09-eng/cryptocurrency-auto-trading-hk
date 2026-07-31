from __future__ import annotations

import json
import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)


class RuntimeEventClient:
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

    def post_event(self, *, trace_id: str, event: dict[str, Any]) -> None:
        payload = {
            "traceId": trace_id,
            "eventType": event.get("event_type", ""),
            "symbol": event.get("symbol", ""),
            "exchange": event.get("exchange", ""),
            "payloadJson": json.dumps(event, ensure_ascii=True),
        }
        response = requests.post(
            f"{self.base_url}/dca/event/ingest",
            json=payload,
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        logger.info(
            "event ingest posted trace_id=%s event_type=%s symbol=%s exchange=%s status_code=%s",
            trace_id,
            payload["eventType"],
            payload["symbol"],
            payload["exchange"],
            getattr(response, "status_code", "unknown"),
        )

    def get_market_history(
        self,
        *,
        symbol: str,
        exchange: str,
        limit: int = 60,
        max_age_minutes: int = 300,
    ) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/dca/event/market-history",
            params={"symbol": symbol, "exchange": exchange, "limit": limit, "maxAgeMinutes": max_age_minutes},
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, list) else []
