from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

import websocket

from trade_runtime.ingestion.ws_supervisor import MarketWebSocketSupervisor


def _attr(source: Any, snake_name: str, camel_name: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        if source.get(snake_name) is not None:
            return source.get(snake_name)
        if source.get(camel_name) is not None:
            return source.get(camel_name)
        return default
    value = getattr(source, snake_name, None)
    if value is not None:
        return value
    value = getattr(source, camel_name, None)
    if value is not None:
        return value
    return default


def _format_inst_id(symbol: str) -> str:
    normalized = str(symbol or "").replace("/", "").replace("-", "").upper()
    if normalized.endswith("USDT") and len(normalized) > 4:
        return f"{normalized[:-4]}-USDT-SWAP"
    if normalized.endswith("USDC") and len(normalized) > 4:
        return f"{normalized[:-4]}-USDC-SWAP"
    return str(symbol or "").strip().upper()


def _normalize_symbol(inst_id: str) -> str:
    parts = [part for part in str(inst_id or "").strip().upper().split("-") if part and part != "SWAP"]
    return "".join(parts)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_template_args(value: Any) -> tuple[dict[str, Any], ...]:
    if isinstance(value, dict):
        args = value.get("args")
        if isinstance(args, list):
            parsed = [dict(item) for item in args if isinstance(item, dict)]
            if parsed:
                return tuple(parsed)
        if value.get("channel"):
            return (dict(value),)
    if isinstance(value, (list, tuple)):
        parsed = [dict(item) for item in value if isinstance(item, dict)]
        if parsed:
            return tuple(parsed)
    normalized = str(value or "").strip()
    if not normalized:
        return ({"channel": "tickers", "instId": "{instId}"},)
    try:
        payload = json.loads(normalized)
    except (TypeError, ValueError):
        payload = None
    if payload is not None:
        return _parse_template_args(payload)
    args: list[dict[str, Any]] = []
    for item in normalized.split(","):
        token = item.strip()
        if not token:
            continue
        if ":" in token:
            channel, inst_id_template = token.split(":", 1)
            rendered = {"channel": channel.strip()}
            if inst_id_template.strip():
                rendered["instId"] = inst_id_template.strip()
            args.append(rendered)
        else:
            args.append({"channel": token, "instId": "{instId}"})
    return tuple(args or [{"channel": "tickers", "instId": "{instId}"}])


@dataclass(frozen=True)
class OkxWebSocketProfile:
    base_url: str = "wss://ws.okx.com:8443"
    path: str = "/ws/v5/public"
    stream_name_template: str = "tickers:{instId}"
    ping_interval_seconds: int = 20
    pong_timeout_seconds: int = 60
    connection_ttl_hours: int = 24
    control_messages_per_second: int = 5
    reconnect_attempts: int = 1

    @classmethod
    def from_market_api_config(cls, market_api_config: Any | None) -> "OkxWebSocketProfile":
        if market_api_config is None:
            return cls()
        return cls(
            base_url=str(_attr(market_api_config, "ws_base_url", "wsBaseUrl", cls.base_url) or cls.base_url).rstrip("/"),
            path=str(_attr(market_api_config, "ws_path", "wsPath", cls.path) or cls.path).strip() or cls.path,
            stream_name_template=str(
                _attr(
                    market_api_config,
                    "ws_stream_name_template",
                    "wsStreamNameTemplate",
                    cls.stream_name_template,
                )
                or cls.stream_name_template
            ).strip(),
            ping_interval_seconds=int(_attr(market_api_config, "ws_ping_interval_seconds", "wsPingIntervalSeconds", cls.ping_interval_seconds) or cls.ping_interval_seconds),
            pong_timeout_seconds=int(_attr(market_api_config, "ws_pong_timeout_seconds", "wsPongTimeoutSeconds", cls.pong_timeout_seconds) or cls.pong_timeout_seconds),
            connection_ttl_hours=int(_attr(market_api_config, "ws_connection_ttl_hours", "wsConnectionTtlHours", cls.connection_ttl_hours) or cls.connection_ttl_hours),
            control_messages_per_second=int(_attr(market_api_config, "ws_control_messages_per_second", "wsControlMessagesPerSecond", cls.control_messages_per_second) or cls.control_messages_per_second),
            reconnect_attempts=int(_attr(market_api_config, "ws_reconnect_attempts", "wsReconnectAttempts", cls.reconnect_attempts)),
        )

    @property
    def url(self) -> str:
        normalized_path = self.path if self.path.startswith("/") else f"/{self.path}"
        return f"{self.base_url}{normalized_path}"

    @property
    def connection_ttl_seconds(self) -> float:
        return float(self.connection_ttl_hours) * 3600.0

    @property
    def template_args(self) -> tuple[dict[str, Any], ...]:
        return _parse_template_args(self.stream_name_template)

    def render_subscribe_args(self, symbol: str) -> list[dict[str, Any]]:
        inst_id = _format_inst_id(symbol)
        symbol_upper = str(symbol or "").replace("/", "").upper()
        replacements = {
            "{instId}": inst_id,
            "{inst_id}": inst_id,
            "{symbol}": symbol_upper,
            "{symbol_upper}": symbol_upper,
            "{symbol_lower}": symbol_upper.lower(),
        }
        rendered_args: list[dict[str, Any]] = []
        for item in self.template_args:
            rendered: dict[str, Any] = {}
            for key, value in item.items():
                if isinstance(value, str):
                    rendered_value = value
                    for placeholder, replacement in replacements.items():
                        rendered_value = rendered_value.replace(placeholder, replacement)
                    rendered[key] = rendered_value
                else:
                    rendered[key] = value
            if rendered.get("channel"):
                rendered_args.append(rendered)
        return rendered_args or [{"channel": "tickers", "instId": inst_id}]


class OkxMarketWebSocketClient:
    def __init__(
        self,
        profile: OkxWebSocketProfile | None = None,
        url: str | None = None,
        timeout: float = 5.0,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        if profile is not None:
            self.profile = profile
            self.url = self.profile.url
        elif url:
            self.profile = OkxWebSocketProfile(base_url=str(url).rstrip("/"), path="")
            self.url = str(url)
        else:
            self.profile = OkxWebSocketProfile()
            self.url = self.profile.url
        self.timeout = timeout
        self.time_fn = time_fn
        self.connection = None
        self.symbol = ""
        self.pending_market_events_by_symbol: dict[str, list[dict[str, Any]]] = {}

    def _format_inst_id(self, symbol: str) -> str:
        return _format_inst_id(symbol)

    def connect(self, symbol: str) -> None:
        if self.connection is not None and self.symbol == symbol:
            return
        self.close()
        self.symbol = symbol
        self.connection = websocket.create_connection(self.url, timeout=self.timeout)
        self.connection.send(
            json.dumps(
                {
                    "op": "subscribe",
                    "args": self.profile.render_subscribe_args(symbol),
                }
            )
        )

    def _payload_channel(self, payload: dict[str, Any]) -> str:
        arg = payload.get("arg")
        if isinstance(arg, dict):
            return str(arg.get("channel") or "").strip().lower()
        return ""

    def _payload_data_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def _payload_symbol(self, payload: dict[str, Any]) -> str:
        arg = payload.get("arg")
        if isinstance(arg, dict) and arg.get("instId"):
            return _normalize_symbol(str(arg.get("instId")))
        for item in self._payload_data_items(payload):
            if item.get("instId"):
                return _normalize_symbol(str(item.get("instId")))
            details = item.get("details")
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict) and detail.get("instId"):
                        return _normalize_symbol(str(detail.get("instId")))
        return ""

    def _normalize_market_events(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        channel = self._payload_channel(payload)
        symbol = self._payload_symbol(payload)
        if not symbol:
            return []
        events: list[dict[str, Any]] = []
        for item in self._payload_data_items(payload):
            event_time = str(item.get("ts") or item.get("event_time") or "").strip()
            if channel == "mark-price":
                price = _safe_float(item.get("markPx") or item.get("mark_price") or item.get("price"))
                if price > 0:
                    event = {"event_type": "mark_price", "symbol": symbol, "exchange": "okx", "price": price}
                    if event_time:
                        event["event_time"] = event_time
                    events.append(event)
            elif channel == "funding-rate":
                funding_rate = _safe_float(item.get("fundingRate") or item.get("funding_rate"))
                event = {"event_type": "funding_rate", "symbol": symbol, "exchange": "okx", "funding_rate": funding_rate}
                if event_time:
                    event["event_time"] = event_time
                events.append(event)
            elif channel == "open-interest":
                open_interest = _safe_float(item.get("oi") or item.get("openInterest") or item.get("open_interest"))
                if open_interest > 0:
                    event = {"event_type": "open_interest", "symbol": symbol, "exchange": "okx", "open_interest": open_interest}
                    if event_time:
                        event["event_time"] = event_time
                    events.append(event)
            elif channel == "liquidation-orders":
                details = item.get("details") if isinstance(item.get("details"), list) else [item]
                for detail in details:
                    if not isinstance(detail, dict):
                        continue
                    price = _safe_float(detail.get("bkPx") or detail.get("price") or detail.get("px"))
                    quantity = _safe_float(detail.get("sz") or detail.get("quantity") or detail.get("qty"))
                    event = {"event_type": "liquidation", "symbol": symbol, "exchange": "okx"}
                    side = str(detail.get("side") or "").strip().lower()
                    if side:
                        event["side"] = side
                    if price > 0:
                        event["price"] = price
                    if quantity > 0:
                        event["quantity"] = quantity
                    if price > 0 and quantity > 0:
                        event["notionalUsd"] = price * quantity
                    detail_time = str(detail.get("ts") or event_time or "").strip()
                    if detail_time:
                        event["event_time"] = detail_time
                    events.append(event)
            elif channel in {"trades", "books5"}:
                event = {"event_type": channel.replace("-", "_"), "symbol": symbol, "exchange": "okx"}
                if event_time:
                    event["event_time"] = event_time
                events.append(event)
        return events

    def _append_market_events(self, symbol: str, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        pending = self.pending_market_events_by_symbol.setdefault(symbol, [])
        pending.extend(dict(item) for item in events if isinstance(item, dict))

    def _attach_market_events(self, symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
        pending = self.pending_market_events_by_symbol.pop(symbol, [])
        if not pending:
            return payload
        normalized = dict(payload)
        existing = normalized.get("_market_events")
        if isinstance(existing, list) and existing:
            normalized["_market_events"] = [*existing, *pending]
        else:
            normalized["_market_events"] = pending
        return normalized

    def _primary_payload_timed_out(self, started_at: float) -> bool:
        timeout = float(self.timeout or 0.0)
        return timeout > 0 and (self.time_fn() - started_at) >= timeout

    def _raise_primary_payload_timeout(self) -> None:
        raise websocket.WebSocketTimeoutException("okx_ws_primary_payload_timeout")

    def recv(self, symbol: str) -> dict[str, Any]:
        self.connect(symbol)
        requested_symbol = _normalize_symbol(_format_inst_id(symbol))
        started_at = self.time_fn()
        while True:
            payload = json.loads(self.connection.recv())
            if not isinstance(payload, dict) or not payload.get("data"):
                if self._primary_payload_timed_out(started_at):
                    self._raise_primary_payload_timeout()
                continue
            channel = self._payload_channel(payload)
            payload_symbol = self._payload_symbol(payload) or requested_symbol
            if channel != "tickers":
                self._append_market_events(payload_symbol, self._normalize_market_events(payload))
                if self._primary_payload_timed_out(started_at):
                    self._raise_primary_payload_timeout()
                continue
            if payload_symbol != requested_symbol:
                if self._primary_payload_timed_out(started_at):
                    self._raise_primary_payload_timeout()
                continue
            return self._attach_market_events(requested_symbol, payload)

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        self.pending_market_events_by_symbol = {}


class OkxWsMarketFeed:
    def __init__(
        self,
        *,
        rest_payload_supplier: Callable[[str], dict[str, Any]],
        market_api_config: Any | None = None,
        supervisor: MarketWebSocketSupervisor | None = None,
        client_factory: Callable[[], Any] | None = None,
    ):
        profile = OkxWebSocketProfile.from_market_api_config(market_api_config)

        def build_client() -> Any:
            factory = client_factory or OkxMarketWebSocketClient
            try:
                return factory(profile=profile)
            except TypeError:
                return factory()

        self.supervisor = supervisor or MarketWebSocketSupervisor(
            source_name="okx_ws",
            client_factory=build_client,
            rest_payload_supplier=rest_payload_supplier,
            stale_after_seconds=float(profile.ping_interval_seconds),
            heartbeat_timeout_seconds=float(profile.pong_timeout_seconds),
            connection_ttl_seconds=profile.connection_ttl_seconds,
            reconnect_attempts=profile.reconnect_attempts,
        )

    def fetch(self, symbol: str) -> dict[str, Any]:
        return self.supervisor.fetch(symbol)

    def close(self) -> None:
        self.supervisor.close()
