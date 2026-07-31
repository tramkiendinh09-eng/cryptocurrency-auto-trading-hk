from __future__ import annotations

from typing import Any

import requests


class RuntimeTaskQueueClient:
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

    def pull_task(self, worker_id: str) -> dict[str, Any] | None:
        response = requests.post(
            f"{self.base_url}/dca/taskqueue/pull",
            params={"workerId": worker_id},
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload.get("data")

    def save_task_result(self, task_id: str, result: dict[str, Any]) -> None:
        response = requests.post(
            f"{self.base_url}/dca/taskqueue/result",
            params={"taskId": task_id},
            json=result,
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

    def update_task_status(self, task_id: str, status: str, result: str = "") -> None:
        response = requests.put(
            f"{self.base_url}/dca/taskqueue/status",
            params={"taskId": task_id, "status": status, "result": result},
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
