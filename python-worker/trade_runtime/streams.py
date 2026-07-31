from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_payload(event: Any) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        payload = event.model_dump()
        if isinstance(payload, dict):
            return payload
    if hasattr(event, "to_stream_entry"):
        payload = event.to_stream_entry()
        if isinstance(payload, dict):
            return payload
    if isinstance(event, dict):
        return dict(event)
    raise TypeError(f"Unsupported stream event type: {type(event)!r}")


def _payload_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _default_source_type(event_type: str) -> str:
    normalized = str(event_type or "").strip().lower()
    if normalized in {
        "market_tick",
        "ticker",
        "mark_price",
        "liquidation",
        "funding_rate",
        "open_interest",
        "market_kline",
        "market_metric",
    }:
        return "market"
    if normalized in {"news", "onchain", "social"}:
        return normalized
    return "runtime"


def _default_source_name(payload: Mapping[str, Any], exchange: str) -> str:
    explicit_source = str(payload.get("source") or "").strip()
    if explicit_source:
        return explicit_source
    if exchange:
        return exchange
    return "runtime"


def _build_idempotency_key(
    trace_id: str,
    event_type: str,
    symbol: str,
    exchange: str,
    payload_json: str,
) -> str:
    digest = hashlib.sha1(payload_json.encode("utf-8")).hexdigest()[:12]
    return ":".join([trace_id or "no-trace", event_type or "unknown", symbol or "unknown", exchange or "unknown", digest])


@dataclass(frozen=True)
class RuntimeStreamEvent:
    trace_id: str
    event_type: str
    symbol: str
    exchange: str
    event_time: str
    source_type: str
    source_name: str
    payload: dict[str, Any]
    idempotency_key: str
    published_at: str
    stream_message_id: str = ""
    retry_count: int = 0
    error_message: str = ""

    @classmethod
    def from_event(
        cls,
        event: Any,
        *,
        trace_id: str = "",
        source_metadata: Mapping[str, Any] | None = None,
    ) -> "RuntimeStreamEvent":
        payload = _normalize_payload(event)
        metadata = dict(source_metadata or {})
        event_type = str(payload.get("event_type") or metadata.get("event_type") or "").strip()
        symbol = str(payload.get("symbol") or metadata.get("symbol") or "").strip()
        exchange = str(payload.get("exchange") or metadata.get("exchange") or "").strip()
        event_time = str(
            metadata.get("event_time")
            or payload.get("event_time")
            or payload.get("timestamp")
            or payload.get("ts")
            or _utc_now_iso()
        ).strip()
        source_type = str(
            metadata.get("source_type")
            or payload.get("source_type")
            or _default_source_type(event_type)
        ).strip()
        source_name = str(
            metadata.get("source_name")
            or payload.get("source_name")
            or _default_source_name(payload, exchange)
        ).strip()
        payload_json = _payload_json(payload)
        idempotency_key = str(
            metadata.get("idempotency_key")
            or payload.get("idempotency_key")
            or _build_idempotency_key(trace_id, event_type, symbol, exchange, payload_json)
        ).strip()
        return cls(
            trace_id=str(trace_id or payload.get("trace_id") or "").strip(),
            event_type=event_type,
            symbol=symbol,
            exchange=exchange,
            event_time=event_time,
            source_type=source_type,
            source_name=source_name,
            payload=payload,
            idempotency_key=idempotency_key,
            published_at=_utc_now_iso(),
        )

    @classmethod
    def from_stream_entry(cls, message_id: str, entry: Mapping[str, Any]) -> "RuntimeStreamEvent":
        payload_json = str(entry.get("payload_json") or "").strip()
        if payload_json:
            payload = json.loads(payload_json)
        else:
            payload = {
                key: value
                for key, value in entry.items()
                if key not in {"trace_id", "event_time", "source_type", "source_name", "idempotency_key", "published_at"}
            }
        event_type = str(entry.get("event_type") or payload.get("event_type") or "").strip()
        symbol = str(entry.get("symbol") or payload.get("symbol") or "").strip()
        exchange = str(entry.get("exchange") or payload.get("exchange") or "").strip()
        trace_id = str(entry.get("trace_id") or payload.get("trace_id") or "").strip()
        event_time = str(entry.get("event_time") or payload.get("event_time") or _utc_now_iso()).strip()
        source_type = str(entry.get("source_type") or payload.get("source_type") or _default_source_type(event_type)).strip()
        source_name = str(entry.get("source_name") or payload.get("source_name") or _default_source_name(payload, exchange)).strip()
        retry_count = int(entry.get("retry_count") or 0)
        error_message = str(entry.get("error_message") or "").strip()
        published_at = str(entry.get("published_at") or _utc_now_iso()).strip()
        idempotency_key = str(entry.get("idempotency_key") or "").strip() or _build_idempotency_key(
            trace_id,
            event_type,
            symbol,
            exchange,
            _payload_json(payload),
        )
        return cls(
            trace_id=trace_id,
            event_type=event_type,
            symbol=symbol,
            exchange=exchange,
            event_time=event_time,
            source_type=source_type,
            source_name=source_name,
            payload=payload,
            idempotency_key=idempotency_key,
            published_at=published_at,
            stream_message_id=str(message_id or "").strip(),
            retry_count=retry_count,
            error_message=error_message,
        )

    def to_stream_entry(self) -> dict[str, str]:
        payload = {
            "trace_id": self.trace_id,
            "event_type": self.event_type,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "event_time": self.event_time,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "payload_json": _payload_json(self.payload),
            "idempotency_key": self.idempotency_key,
            "published_at": self.published_at,
        }
        if self.stream_message_id:
            payload["stream_message_id"] = self.stream_message_id
        if self.retry_count:
            payload["retry_count"] = str(self.retry_count)
        if self.error_message:
            payload["error_message"] = self.error_message
        return payload


class StreamPublisher:
    def __init__(self, redis_client, stream_name: str):
        self.redis_client = redis_client
        self.stream_name = stream_name

    def _to_stream_entry(self, event) -> dict[str, str]:
        payload = _normalize_payload(event)
        return {key: str(value) for key, value in payload.items()}

    def publish(
        self,
        event,
        *,
        trace_id: str = "",
        source_metadata: Mapping[str, Any] | None = None,
    ) -> str:
        if trace_id or source_metadata:
            stream_event = RuntimeStreamEvent.from_event(
                event,
                trace_id=trace_id,
                source_metadata=source_metadata,
            )
            return self.redis_client.xadd(self.stream_name, stream_event.to_stream_entry())
        return self.redis_client.xadd(self.stream_name, self._to_stream_entry(event))
