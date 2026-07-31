from __future__ import annotations

from typing import Any, Callable

from trade_runtime.streams import RuntimeStreamEvent


class StreamConsumer:
    def __init__(
        self,
        *,
        redis_client,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        handler: Callable[[RuntimeStreamEvent], None],
        dead_letter_stream: str | None = None,
        max_retries: int = 3,
        dedupe_ttl_seconds: int = 86400,
    ):
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.handler = handler
        self.dead_letter_stream = dead_letter_stream or f"{stream_name}.dlq"
        self.max_retries = max(1, int(max_retries or 1))
        self.dedupe_ttl_seconds = max(60, int(dedupe_ttl_seconds or 60))
        self.retry_hash_name = f"{self.stream_name}:retries"
        self.dedupe_key_prefix = f"{self.stream_name}:processed"
        self.ensure_group()

    def ensure_group(self) -> None:
        try:
            self.redis_client.xgroup_create(self.stream_name, self.group_name, id="$", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def consume_available(self, *, max_messages: int, block_ms: int = 0) -> dict[str, int]:
        if max_messages <= 0:
            return {"read": 0, "processed": 0, "acked": 0, "duplicates": 0, "dead_lettered": 0, "retried": 0}
        return self.consume_once(count=max_messages, block_ms=block_ms)

    def consume_once(self, *, count: int = 1, block_ms: int = 0) -> dict[str, int]:
        result = {"read": 0, "processed": 0, "acked": 0, "duplicates": 0, "dead_lettered": 0, "retried": 0}
        messages = self.redis_client.xreadgroup(
            self.group_name,
            self.consumer_name,
            {self.stream_name: ">"},
            count=max(1, int(count or 1)),
            block=max(0, int(block_ms or 0)),
        ) or []
        for stream_name, stream_messages in messages:
            for message_id, entry in stream_messages:
                result["read"] += 1
                stream_event = RuntimeStreamEvent.from_stream_entry(message_id, entry)
                if not self._claim_idempotency(stream_event.idempotency_key):
                    self._ack(stream_name, message_id)
                    self._clear_retry(message_id)
                    result["acked"] += 1
                    result["duplicates"] += 1
                    continue
                try:
                    self.handler(stream_event)
                except Exception as exc:
                    attempt = self._record_failure(message_id)
                    if attempt >= self.max_retries:
                        self._dead_letter(stream_event, message_id, attempt, str(exc))
                        self._ack(stream_name, message_id)
                        self._clear_retry(message_id)
                        result["acked"] += 1
                        result["dead_lettered"] += 1
                    else:
                        self._release_idempotency(stream_event.idempotency_key)
                        result["retried"] += 1
                    continue
                self._ack(stream_name, message_id)
                self._clear_retry(message_id)
                result["acked"] += 1
                result["processed"] += 1
        return result

    def health(self) -> dict[str, Any]:
        payload = {"stream_name": self.stream_name, "group_name": self.group_name, "consumer_name": self.consumer_name}
        try:
            pending = self.redis_client.xpending(self.stream_name, self.group_name)
            payload["pending"] = pending
        except Exception:
            payload["pending"] = None
        try:
            groups = self.redis_client.xinfo_groups(self.stream_name) or []
            matched_group = next((item for item in groups if item.get("name") == self.group_name), None)
            payload["lag"] = matched_group.get("lag") if isinstance(matched_group, dict) else None
        except Exception:
            payload["lag"] = None
        return payload

    def _dedupe_key(self, idempotency_key: str) -> str:
        return f"{self.dedupe_key_prefix}:{idempotency_key}"

    def _claim_idempotency(self, idempotency_key: str) -> bool:
        return bool(
            self.redis_client.set(
                self._dedupe_key(idempotency_key),
                "1",
                nx=True,
                ex=self.dedupe_ttl_seconds,
            )
        )

    def _release_idempotency(self, idempotency_key: str) -> None:
        delete = getattr(self.redis_client, "delete", None)
        if callable(delete):
            delete(self._dedupe_key(idempotency_key))

    def _record_failure(self, message_id: str) -> int:
        return int(self.redis_client.hincrby(self.retry_hash_name, message_id, 1))

    def _clear_retry(self, message_id: str) -> None:
        hdel = getattr(self.redis_client, "hdel", None)
        if callable(hdel):
            hdel(self.retry_hash_name, message_id)

    def _dead_letter(self, event: RuntimeStreamEvent, message_id: str, retry_count: int, error_message: str) -> None:
        payload = RuntimeStreamEvent(
            trace_id=event.trace_id,
            event_type=event.event_type,
            symbol=event.symbol,
            exchange=event.exchange,
            event_time=event.event_time,
            source_type=event.source_type,
            source_name=event.source_name,
            payload=event.payload,
            idempotency_key=event.idempotency_key,
            published_at=event.published_at,
            stream_message_id=message_id,
            retry_count=retry_count,
            error_message=error_message,
        )
        self.redis_client.xadd(self.dead_letter_stream, payload.to_stream_entry())

    def _ack(self, stream_name: str, message_id: str) -> None:
        self.redis_client.xack(stream_name, self.group_name, message_id)
