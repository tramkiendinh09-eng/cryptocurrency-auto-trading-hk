from __future__ import annotations

from typing import Any

import requests


class DecisionModelClient:
    def __init__(self, base_url: str, bearer_token: str, timeout: int = 10):
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

    def call_model(self, *, model_id: int | None, prompt: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/dca/trade/runtime/model-call",
            json={"modelId": model_id, "prompt": prompt},
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        data = payload.get("data") or {}
        return data if isinstance(data, dict) else {}
