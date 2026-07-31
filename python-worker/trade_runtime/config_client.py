from __future__ import annotations

import logging
from typing import Any

import requests

from trade_runtime.config import RuntimeBootstrap, RuntimeConfig


logger = logging.getLogger(__name__)


class RuntimeConfigClient:
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

    def get_config(self) -> RuntimeConfig:
        logger.info("runtime config fetch url=%s", f"{self.base_url}/dca/trade/runtime/config")
        response = requests.get(
            f"{self.base_url}/dca/trade/runtime/config",
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return RuntimeConfig.model_validate(payload.get("data") or {})

    def get_bootstrap(self, symbol: str | None = None, exchange: str | None = None) -> RuntimeBootstrap:
        params = {}
        if symbol:
            params["symbol"] = symbol
        if exchange:
            params["exchange"] = exchange
        logger.info("runtime bootstrap fetch url=%s symbol=%s exchange=%s", f"{self.base_url}/dca/trade/runtime/bootstrap", symbol or "-", exchange or "-")
        response = requests.get(
            f"{self.base_url}/dca/trade/runtime/bootstrap",
            headers=self.build_headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return RuntimeBootstrap.model_validate(payload.get("data") or {})

    def list_bootstraps(self) -> list[RuntimeBootstrap]:
        logger.info("runtime routes fetch url=%s", f"{self.base_url}/dca/trade/runtime/routes")
        response = requests.get(
            f"{self.base_url}/dca/trade/runtime/routes",
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        routes = payload.get("data") or []
        if not isinstance(routes, list):
            logger.warning("runtime routes payload ignored because data is not a list type=%s", type(routes).__name__)
            return []
        logger.info("runtime routes fetched count=%s", len(routes))
        return [RuntimeBootstrap.model_validate(item or {}) for item in routes]
