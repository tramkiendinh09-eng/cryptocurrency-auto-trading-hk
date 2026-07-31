from __future__ import annotations

from typing import Any

import requests


class PromptTemplateRegistry:
    def __init__(self, *, base_url: str, bearer_token: str, timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout
        self._cache: dict[str, dict[str, Any] | None] = {}

    def build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def get_template(self, template_code: str | None) -> dict[str, Any] | None:
        normalized_code = str(template_code or "").strip()
        if not normalized_code:
            return None
        if normalized_code in self._cache:
            return self._cache[normalized_code]
        try:
            response = requests.get(
                f"{self.base_url}/dca/template/code/{normalized_code}",
                headers=self.build_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            data = payload.get("data") or {}
            template = data if isinstance(data, dict) else None
        except Exception:
            template = None
        self._cache[normalized_code] = template
        return template


def resolve_prompt_template_registry(state: dict[str, Any]) -> Any | None:
    registry = state.get("prompt_template_registry")
    if registry is not None and hasattr(registry, "get_template"):
        return registry
    decision_model_client = state.get("decision_model_client")
    base_url = str(getattr(decision_model_client, "base_url", "") or "").strip()
    if not base_url:
        return None
    registry = PromptTemplateRegistry(
        base_url=base_url,
        bearer_token=str(getattr(decision_model_client, "bearer_token", "") or "").strip(),
        timeout=int(getattr(decision_model_client, "timeout", 10) or 10),
    )
    state["prompt_template_registry"] = registry
    return registry
