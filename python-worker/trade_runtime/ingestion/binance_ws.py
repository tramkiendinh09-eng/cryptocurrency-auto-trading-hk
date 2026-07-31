"""
Binance WebSocket市场数据接入模块

实现Binance交易所的WebSocket连接和数据订阅，包括：
- 多流订阅管理
- 连接保活和重连
- 消息解析和分发
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import websocket

from trade_runtime.ingestion.ws_supervisor import MarketWebSocketSupervisor


def _parse_stream_templates(value: Any) -> tuple[str, ...]:
    """解析流名称模板

    Args:
        value: 模板值，支持字符串、列表、JSON格式

    Returns:
        tuple[str, ...]: 流名称模板元组
    """
    if isinstance(value, (list, tuple, set)):
        templates = [str(item).strip() for item in value if str(item).strip()]
        return tuple(templates) if templates else ("{symbol_lower}@ticker",)
    normalized = str(value or "").strip()
    if not normalized:
        return ("{symbol_lower}@ticker",)
    try:
        payload = json.loads(normalized)
    except (TypeError, ValueError):
        payload = None
    if isinstance(payload, list):
        templates = [str(item).strip() for item in payload if str(item).strip()]
        if templates:
            return tuple(templates)
    if "," in normalized:
        templates = [item.strip() for item in normalized.split(",") if item.strip()]
        if templates:
            return tuple(templates)
    return (normalized,)


@dataclass(frozen=True)
class BinanceWebSocketProfile:
    """Binance WebSocket配置

    包含连接参数、流订阅配置、保活参数等。

    Attributes:
        base_url: WebSocket基础URL
        path: WebSocket路径
        stream_name_template: 流名称模板
        combined_enabled: 是否启用组合流
        symbol_lowercase: 是否使用小写交易对
        ping_interval_seconds: ping间隔秒数
        pong_timeout_seconds: pong超时秒数
        connection_ttl_hours: 连接TTL小时数
        max_streams_per_connection: 每连接最大流数
        control_messages_per_second: 每秒控制消息数
    """
    base_url: str = "wss://fstream.binance.com"
    path: str = "/ws"
    stream_name_template: str = "{symbol_lower}@ticker"
    combined_enabled: bool = False
    symbol_lowercase: bool = True
    ping_interval_seconds: int = 20
    pong_timeout_seconds: int = 60
    connection_ttl_hours: int = 24
    max_streams_per_connection: int = 1024
    control_messages_per_second: int = 5
    reconnect_attempts: int = 1

    @classmethod
    def from_market_api_config(cls, market_api_config: Any | None) -> "BinanceWebSocketProfile":
        if market_api_config is None:
            return cls()
        return cls(
            base_url=str(getattr(market_api_config, "ws_base_url", None) or getattr(market_api_config, "wsBaseUrl", None) or cls.base_url).rstrip("/"),
            path=str(getattr(market_api_config, "ws_path", None) or getattr(market_api_config, "wsPath", None) or cls.path).strip(),
            stream_name_template=str(
                getattr(market_api_config, "ws_stream_name_template", None)
                or getattr(market_api_config, "wsStreamNameTemplate", None)
                or cls.stream_name_template
            ).strip(),
            combined_enabled=bool(
                getattr(market_api_config, "ws_combined_enabled", None)
                if getattr(market_api_config, "ws_combined_enabled", None) is not None
                else getattr(market_api_config, "wsCombinedEnabled", cls.combined_enabled)
            ),
            symbol_lowercase=bool(
                getattr(market_api_config, "ws_symbol_lowercase", None)
                if getattr(market_api_config, "ws_symbol_lowercase", None) is not None
                else getattr(market_api_config, "wsSymbolLowercase", cls.symbol_lowercase)
            ),
            ping_interval_seconds=int(
                getattr(market_api_config, "ws_ping_interval_seconds", None)
                or getattr(market_api_config, "wsPingIntervalSeconds", None)
                or cls.ping_interval_seconds
            ),
            pong_timeout_seconds=int(
                getattr(market_api_config, "ws_pong_timeout_seconds", None)
                or getattr(market_api_config, "wsPongTimeoutSeconds", None)
                or cls.pong_timeout_seconds
            ),
            connection_ttl_hours=int(
                getattr(market_api_config, "ws_connection_ttl_hours", None)
                or getattr(market_api_config, "wsConnectionTtlHours", None)
                or cls.connection_ttl_hours
            ),
            max_streams_per_connection=int(
                getattr(market_api_config, "ws_max_streams_per_connection", None)
                or getattr(market_api_config, "wsMaxStreamsPerConnection", None)
                or cls.max_streams_per_connection
            ),
            control_messages_per_second=int(
                getattr(market_api_config, "ws_control_messages_per_second", None)
                or getattr(market_api_config, "wsControlMessagesPerSecond", None)
                or cls.control_messages_per_second
            ),
            reconnect_attempts=int(
                getattr(market_api_config, "ws_reconnect_attempts", None)
                if getattr(market_api_config, "ws_reconnect_attempts", None) is not None
                else getattr(market_api_config, "wsReconnectAttempts", cls.reconnect_attempts)
            ),
        )

    @property
    def connection_ttl_seconds(self) -> float:
        return float(self.connection_ttl_hours) * 3600.0

    @property
    def resolved_path(self) -> str:
        return "/stream" if self.combined_enabled else "/ws"

    @property
    def stream_name_templates(self) -> tuple[str, ...]:
        return _parse_stream_templates(self.stream_name_template)

    @property
    def primary_stream_name_template(self) -> str:
        return self.stream_name_templates[0]

    def resolved_path_for_streams(self, stream_count: int) -> str:
        return "/stream" if self.combined_enabled or int(stream_count or 0) > 1 else "/ws"


class ControlMessageBudget:
    def __init__(self, *, max_messages_per_second: int, time_fn: Callable[[], float]):
        self.max_messages_per_second = max(1, int(max_messages_per_second or 1))
        self.time_fn = time_fn
        self._timestamps: deque[float] = deque()

    def record(self) -> None:
        now = self.time_fn()
        while self._timestamps and (now - self._timestamps[0]) >= 1.0:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_messages_per_second:
            raise RuntimeError("binance_ws_control_budget_exceeded")
        self._timestamps.append(now)


class BinanceMarketWebSocketClient:
    def __init__(
        self,
        profile: BinanceWebSocketProfile | None = None,
        timeout: float = 5.0,
        time_fn: Callable[[], float] = time.monotonic,
    ):
        self.profile = profile or BinanceWebSocketProfile()
        self.timeout = timeout
        self.time_fn = time_fn
        self.connection = None
        self.symbol = ""
        self.subscribed_symbols: list[str] = []
        self.pending_payloads_by_symbol: dict[str, dict[str, Any]] = {}
        self.pending_market_events_by_symbol: dict[str, list[dict[str, Any]]] = {}
        self.last_heartbeat_at: float | None = None
        self.last_frame_at: float | None = None
        self.control_message_budget = ControlMessageBudget(
            max_messages_per_second=self.profile.control_messages_per_second,
            time_fn=self.time_fn,
        )

    def _normalize_symbol(self, symbol: str) -> str:
        return str(symbol or "").strip().lower()

    def _stream_name(self, symbol: str, template: str | None = None) -> str:
        normalized_symbol = self._normalize_symbol(symbol)
        stream_name = str(template or self.profile.primary_stream_name_template)
        return (
            stream_name
            .replace("{symbol_lower}", normalized_symbol.lower())
            .replace("{symbol_upper}", normalized_symbol.upper())
            .replace("{symbol}", normalized_symbol)
        )

    def _stream_names(self, symbol: str) -> list[str]:
        return [self._stream_name(symbol, template) for template in self.profile.stream_name_templates]

    def _primary_stream_kind(self) -> str:
        return self._stream_kind(self.profile.primary_stream_name_template)

    def _stream_kind(self, stream_name: str) -> str:
        normalized = str(stream_name or "").strip().lower()
        if "@markprice" in normalized or normalized == "markpriceupdate":
            return "mark_price"
        if "@forceorder" in normalized or normalized == "forceorder":
            return "liquidation"
        if "@ticker" in normalized or normalized == "24hrticker":
            return "ticker"
        return normalized

    def _payload_symbol(self, payload: dict[str, Any]) -> str:
        order = payload.get("o")
        if isinstance(order, dict):
            nested_symbol = order.get("s") or order.get("symbol")
            if nested_symbol not in (None, ""):
                return str(nested_symbol).strip().upper()
        return str(payload.get("s") or payload.get("symbol") or "").strip().upper()

    def _payload_stream_kind(self, payload: dict[str, Any]) -> str:
        return self._stream_kind(payload.get("_market_stream_name") or payload.get("_market_stream_kind") or payload.get("e") or "")

    def _is_primary_payload(self, payload: dict[str, Any]) -> bool:
        payload_kind = self._payload_stream_kind(payload)
        primary_kind = self._primary_stream_kind()
        if payload_kind:
            return payload_kind == primary_kind
        return len(self.profile.stream_name_templates) == 1

    def _normalize_market_events(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        symbol = self._payload_symbol(payload)
        if not symbol:
            return []
        stream_kind = self._payload_stream_kind(payload)
        if stream_kind == "mark_price":
            events: list[dict[str, Any]] = []
            mark_price = payload.get("p") or payload.get("markPrice") or payload.get("price")
            if mark_price not in (None, ""):
                events.append(
                    {
                        "event_type": "mark_price",
                        "symbol": symbol,
                        "exchange": "binance",
                        "price": float(mark_price),
                    }
                )
            funding_rate = payload.get("r") or payload.get("fundingRate") or payload.get("funding_rate")
            if funding_rate not in (None, ""):
                events.append(
                    {
                        "event_type": "funding_rate",
                        "symbol": symbol,
                        "exchange": "binance",
                        "funding_rate": float(funding_rate),
                    }
                )
            return events
        if stream_kind == "liquidation":
            order = payload.get("o") if isinstance(payload.get("o"), dict) else payload
            price = order.get("ap") or order.get("p") or order.get("price")
            quantity = order.get("q") or order.get("z") or order.get("quantity")
            event = {
                "event_type": "liquidation",
                "symbol": symbol,
                "exchange": "binance",
            }
            side = str(order.get("S") or order.get("side") or "").strip().upper()
            if side:
                event["side"] = side
            if price not in (None, ""):
                event["price"] = float(price)
            if quantity not in (None, ""):
                event["quantity"] = float(quantity)
            if "price" in event and "quantity" in event:
                event["notionalUsd"] = float(event["price"]) * float(event["quantity"])
            return [event]
        return []

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

    def _next_frame(self) -> tuple[int, Any]:
        recv_frame = getattr(self.connection, "recv_frame", None)
        if callable(recv_frame):
            frame = recv_frame()
            return frame.opcode, frame
        recv_data_frame = getattr(self.connection, "recv_data_frame", None)
        if callable(recv_data_frame):
            return recv_data_frame(control_frame=True)
        raise AttributeError("binance_ws_recv_frame_missing")

    def _send_pong(self, payload: bytes | str = b"") -> None:
        self.control_message_budget.record()
        self.connection.pong(payload)

    def _primary_payload_timed_out(self, started_at: float) -> bool:
        timeout = float(self.timeout or 0.0)
        return timeout > 0 and (self.time_fn() - started_at) >= timeout

    def _raise_primary_payload_timeout(self) -> None:
        raise websocket.WebSocketTimeoutException("binance_ws_primary_payload_timeout")

    def build_url(self, symbols: str | Iterable[str]) -> str:
        normalized_symbols = [symbols] if isinstance(symbols, str) else list(symbols)
        stream_names: list[str] = []
        for symbol in normalized_symbols:
            if not str(symbol or "").strip():
                continue
            stream_names.extend(self._stream_names(symbol))
        combined_enabled = self.profile.combined_enabled or len(stream_names) > 1
        if combined_enabled:
            if len(stream_names) > int(self.profile.max_streams_per_connection):
                raise ValueError("binance_ws_max_streams_exceeded")
            return f"{self.profile.base_url}{self.profile.resolved_path_for_streams(len(stream_names))}?streams={'/'.join(stream_names)}"
        if not stream_names:
            raise ValueError("binance_ws_symbol_required")
        return f"{self.profile.base_url}{self.profile.resolved_path_for_streams(len(stream_names))}/{stream_names[0]}"

    def _desired_symbols(self, normalized_symbol: str) -> list[str]:
        if not self.profile.combined_enabled:
            return [normalized_symbol]
        symbols = list(self.subscribed_symbols)
        if normalized_symbol not in symbols:
            symbols.append(normalized_symbol)
        return symbols

    def connect(self, symbol: str) -> None:
        normalized_symbol = self._normalize_symbol(symbol)
        desired_symbols = self._desired_symbols(normalized_symbol)
        if self.connection is not None and self.subscribed_symbols == desired_symbols:
            self.symbol = normalized_symbol
            return
        self.close()
        self.symbol = normalized_symbol
        self.subscribed_symbols = desired_symbols
        self.connection = websocket.create_connection(
            self.build_url(desired_symbols if self.profile.combined_enabled else normalized_symbol),
            timeout=self.timeout,
        )

    def recv(self, symbol: str) -> dict[str, Any]:
        requested_symbol = str(symbol or "").strip().upper()
        cached_payload = self.pending_payloads_by_symbol.pop(requested_symbol, None)
        if isinstance(cached_payload, dict):
            return self._attach_market_events(requested_symbol, cached_payload)
        self.connect(symbol)
        started_at = self.time_fn()
        while True:
            opcode, frame = self._next_frame()
            now = self.time_fn()
            self.last_frame_at = now
            if opcode == websocket.ABNF.OPCODE_PING:
                self._send_pong(frame.data)
                self.last_heartbeat_at = now
                if self._primary_payload_timed_out(started_at):
                    self._raise_primary_payload_timeout()
                continue
            if opcode == websocket.ABNF.OPCODE_PONG:
                self.last_heartbeat_at = now
                if self._primary_payload_timed_out(started_at):
                    self._raise_primary_payload_timeout()
                continue
            if opcode == websocket.ABNF.OPCODE_CLOSE:
                raise RuntimeError("binance_ws_closed")
            payload_data = frame.data
            if isinstance(payload_data, bytes):
                payload_data = payload_data.decode("utf-8")
            payload = json.loads(payload_data)
            wrapper = payload if isinstance(payload, dict) else {}
            if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
                payload = dict(payload["data"])
                stream_name = str(wrapper.get("stream") or "").strip()
                if stream_name:
                    payload["_market_stream_name"] = stream_name
                    payload["_market_stream_kind"] = self._stream_kind(stream_name)
            if not isinstance(payload, dict):
                raise ValueError("binance_ws_payload_invalid")
            payload_symbol = self._payload_symbol(payload)
            if payload_symbol and not self._is_primary_payload(payload):
                self._append_market_events(payload_symbol, self._normalize_market_events(payload))
                if self._primary_payload_timed_out(started_at):
                    self._raise_primary_payload_timeout()
                continue
            if payload_symbol and payload_symbol != requested_symbol:
                self.pending_payloads_by_symbol[payload_symbol] = self._attach_market_events(payload_symbol, payload)
                if self._primary_payload_timed_out(started_at):
                    self._raise_primary_payload_timeout()
                continue
            return self._attach_market_events(requested_symbol, payload)

    def get_last_heartbeat_at(self) -> float | None:
        return self.last_heartbeat_at

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        self.symbol = ""
        self.subscribed_symbols = []
        self.pending_payloads_by_symbol = {}
        self.pending_market_events_by_symbol = {}


class BinanceWsMarketFeed:
    def __init__(
        self,
        *,
        rest_payload_supplier: Callable[[str], dict[str, Any]],
        market_api_config: Any | None = None,
        supervisor: MarketWebSocketSupervisor | None = None,
        client_factory: Callable[[], Any] | None = None,
    ):
        profile = BinanceWebSocketProfile.from_market_api_config(market_api_config)

        def build_client() -> Any:
            factory = client_factory or BinanceMarketWebSocketClient
            try:
                return factory(profile=profile)
            except TypeError:
                return factory()

        self.supervisor = supervisor or MarketWebSocketSupervisor(
            source_name="binance_ws",
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
