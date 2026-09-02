from __future__ import annotations

import time
from typing import Any, Callable


class MarketWebSocketSupervisor:
    def __init__(
        self,
        *,
        source_name: str,
        client_factory: Callable[[], Any],
        rest_payload_supplier: Callable[[str], dict[str, Any]] | None = None,
        stale_after_seconds: float = 15.0,
        heartbeat_timeout_seconds: float = 30.0,
        connection_ttl_seconds: float | None = None,
        base_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 8.0,
        reconnect_attempts: int = 1,
        rest_primary: bool = False,
        time_fn: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.source_name = source_name
        self.client_factory = client_factory
        self.rest_payload_supplier = rest_payload_supplier
        # When the configured transport is REST, polling is the intended source
        # rather than a symptom of a broken socket. Without this the supervisor
        # reports "degraded" on every fetch, and risk/guard.py treats degraded as
        # an abnormal market source and blocks every order — so a network that
        # cannot carry the websocket silently disables trading altogether.
        self.rest_primary = bool(rest_primary)
        self.stale_after_seconds = stale_after_seconds
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.connection_ttl_seconds = connection_ttl_seconds
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.reconnect_attempts = max(0, int(reconnect_attempts))
        self.time_fn = time_fn
        self.sleep = sleep
        self.client: Any | None = None
        self.connected_symbol: str | None = None
        self.connected_at: float | None = None
        self.last_message_at: float | None = None
        self.reconnect_count = 0
        self.last_error: str = ""
        self.last_payload_by_symbol: dict[str, dict[str, Any]] = {}

    def _connect(self, symbol: str) -> None:
        if self.client is None:
            self.client = self.client_factory()
        if self.connected_symbol == symbol:
            return
        connect = getattr(self.client, "connect", None)
        if callable(connect):
            connect(symbol)
        self.connected_symbol = symbol
        self.connected_at = self.time_fn()

    def _close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        self.client = None
        self.connected_symbol = None
        self.connected_at = None

    def close(self) -> None:
        self._close()

    def _sync_client_heartbeat(self) -> None:
        get_last_heartbeat_at = getattr(self.client, "get_last_heartbeat_at", None)
        if not callable(get_last_heartbeat_at):
            return
        heartbeat_at = get_last_heartbeat_at()
        if heartbeat_at is None:
            return
        self.last_message_at = heartbeat_at

    def _annotate_payload(self, payload: dict[str, Any], source_status: str) -> dict[str, Any]:
        normalized = dict(payload)
        normalized["_market_source_status"] = source_status
        normalized["_market_source"] = self.source_name
        return normalized

    def _current_source_status(self) -> str:
        if self.last_message_at is None:
            return "cold"
        age = self.time_fn() - self.last_message_at
        if age >= self.heartbeat_timeout_seconds:
            return "abnormal"
        if age >= self.stale_after_seconds:
            return "stale"
        return "ready"

    def _should_rotate_connection(self) -> bool:
        if self.connection_ttl_seconds in (None, 0):
            return False
        if self.connected_at is None:
            return False
        return (self.time_fn() - self.connected_at) >= float(self.connection_ttl_seconds)

    def _backoff_seconds(self, failure_count: int) -> float:
        return min(
            self.max_backoff_seconds,
            self.base_backoff_seconds * (2 ** max(0, failure_count - 1)),
        )

    def _fallback_payload(self, symbol: str, source_status: str) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.rest_payload_supplier is not None:
            try:
                rest_payload = self.rest_payload_supplier(symbol)
                if isinstance(rest_payload, dict) and rest_payload:
                    payload = dict(rest_payload)
            except Exception as exc:
                self.last_error = str(exc)
        if not payload:
            payload = dict(self.last_payload_by_symbol.get(symbol) or {})
        return self._annotate_payload(payload, source_status)

    def _fetch_rest_primary(self, symbol: str) -> dict[str, Any]:
        """Poll REST as the configured transport.

        Reports "ready" only when the poll actually returned data; a failing REST
        source is still degraded, so the risk gate keeps its safety property.
        """
        if self.rest_payload_supplier is None:
            return self._annotate_payload({}, "degraded")
        try:
            payload = self.rest_payload_supplier(symbol)
        except Exception as exc:
            self.last_error = str(exc)
            return self._annotate_payload(
                dict(self.last_payload_by_symbol.get(symbol) or {}), "degraded"
            )
        if isinstance(payload, dict) and payload:
            self.last_message_at = self.time_fn()
            self.last_payload_by_symbol[symbol] = dict(payload)
            return self._annotate_payload(payload, "ready")
        return self._annotate_payload(
            dict(self.last_payload_by_symbol.get(symbol) or {}), "degraded"
        )

    def fetch(self, symbol: str) -> dict[str, Any]:
        if self.rest_primary:
            return self._fetch_rest_primary(symbol)
        attempts = 0
        next_failure_count = self.reconnect_count + 1
        final_status = "degraded"

        while True:
            try:
                if self._should_rotate_connection():
                    self._close()
                self._connect(symbol)
                payload = getattr(self.client, "recv")(symbol)
                self._sync_client_heartbeat()
                if isinstance(payload, dict) and payload:
                    self.last_message_at = self.time_fn()
                    self.reconnect_count = 0
                    self.last_payload_by_symbol[symbol] = dict(payload)
                    return self._annotate_payload(payload, "ready")
            except Exception as exc:
                self.last_error = str(exc)
                final_status = "degraded"
                self._close()
                if attempts < self.reconnect_attempts:
                    attempts += 1
                    self.sleep(self._backoff_seconds(next_failure_count))
                    continue
                self.reconnect_count = next_failure_count
                return self._fallback_payload(symbol, final_status)

            source_status = self._current_source_status()
            if source_status in {"stale", "abnormal"}:
                final_status = source_status
                self.last_error = f"source_status={source_status}"
                self._close()
                if attempts < self.reconnect_attempts:
                    attempts += 1
                    self.sleep(self._backoff_seconds(next_failure_count))
                    continue
                self.reconnect_count = next_failure_count
                return self._fallback_payload(symbol, final_status)

            self.reconnect_count = 0
            return self._fallback_payload(symbol, "ready")
