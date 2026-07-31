from __future__ import annotations

import json

from trade_runtime.config import RuntimeBootstrap, RuntimeMarketApiConfig


class SourceConfigClient:
    def __init__(self, bootstrap: RuntimeBootstrap | None):
        self.bootstrap = bootstrap

    def _is_enabled(self, config: RuntimeMarketApiConfig | None) -> bool:
        if config is None:
            return False
        enabled = str(getattr(config, "enabled", "") or "").strip().lower()
        return enabled not in {"0", "false", "off", "no"}

    def _matches_exchange_scope(self, exchange: str | None) -> bool:
        if self.bootstrap is None or not exchange:
            return True
        scope = getattr(self.bootstrap, "symbol_scope", None)
        scope_exchange = str(getattr(scope, "exchange_code", "") or "").strip().lower()
        if not scope_exchange:
            return True
        return scope_exchange == str(exchange).strip().lower()

    def _matches_symbol_scope(self, config: RuntimeMarketApiConfig | None, symbol: str | None) -> bool:
        if config is None or not symbol:
            return True
        apply_symbols = str(getattr(config, "apply_symbols", "") or "").strip()
        if not apply_symbols:
            return True
        try:
            payload = json.loads(apply_symbols)
        except (TypeError, ValueError):
            payload = apply_symbols.split(",")
        allowed_symbols = {
            str(item or "").strip().upper()
            for item in payload
            if str(item or "").strip()
        }
        if not allowed_symbols:
            return True
        return str(symbol).strip().upper() in allowed_symbols

    def resolve_market_api_config(
        self,
        *,
        symbol: str | None = None,
        exchange: str | None = None,
    ) -> RuntimeMarketApiConfig | None:
        if self.bootstrap is None:
            return None
        config = getattr(self.bootstrap, "market_api_config", None)
        if not self._is_enabled(config):
            return None
        if not self._matches_exchange_scope(exchange):
            return None
        if not self._matches_symbol_scope(config, symbol):
            return None
        return config
