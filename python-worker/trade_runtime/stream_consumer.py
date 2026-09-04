from __future__ import annotations

import logging
from typing import Any, Callable

from trade_runtime.streams import RuntimeStreamEvent

logger = logging.getLogger(__name__)


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

    def _recover_missing_group(self) -> bool:
        """消费组事后消失时重建它，返回是否值得重试本次读取。

        ensure_group() 原本只在 __init__ 调用一次。消费组一旦事后消失，
        consume_once() 就会永远抛 NOGROUP，对象自己不会恢复——只有重启进程
        才可能修好。2026-09-04 实际发生过：Redis 的 maxmemory-policy 是
        allkeys-lru，会驱逐**任何** key，包括没有 TTL 的这条流；流被整个驱逐时
        消费组一起消失，之后 XADD 只重建流、不重建组。因为本消费者的 handler
        就是把事件 POST 到后端，这一挂就是 57 分钟 event_raw 与
        market_metric_snapshot 完全没有写入，而决策链路照常跑、日志之外毫无
        征兆。根因已另行修掉（redis.conf 改成 volatile-lru），这里是第二道防线。

        重建仍用 id="$"，与 ensure_group 一致：只收新消息。不改成 id=0 是因为
        去重键同样可能已被驱逐，重放会把同一批行情事件二次写进 event_raw，
        而下游的聚合窗口会把它们重复累加——宁可丢一段也不要污染。所以这里把
        当前积压条数打进日志，需要补数据时可人工从 id=0 重建。
        """
        try:
            backlog = self.redis_client.xlen(self.stream_name)
        except Exception:
            backlog = -1
        try:
            self.ensure_group()
        except Exception:
            logger.exception(
                "stream consumer group recreate failed stream=%s group=%s",
                self.stream_name,
                self.group_name,
            )
            return False
        logger.error(
            "stream consumer group was missing and has been recreated at $; "
            "stream=%s group=%s skipped_backlog=%s "
            "(要补这段数据需人工 XGROUP CREATE ... 0 重建)",
            self.stream_name,
            self.group_name,
            backlog,
        )
        return True

    def _read_group(self, *, count: int, block_ms: int) -> list:
        return self.redis_client.xreadgroup(
            self.group_name,
            self.consumer_name,
            {self.stream_name: ">"},
            count=max(1, int(count or 1)),
            block=max(0, int(block_ms or 0)),
        ) or []

    def consume_available(self, *, max_messages: int, block_ms: int = 0) -> dict[str, int]:
        if max_messages <= 0:
            return {"read": 0, "processed": 0, "acked": 0, "duplicates": 0, "dead_lettered": 0, "retried": 0}
        return self.consume_once(count=max_messages, block_ms=block_ms)

    def consume_once(self, *, count: int = 1, block_ms: int = 0) -> dict[str, int]:
        result = {"read": 0, "processed": 0, "acked": 0, "duplicates": 0, "dead_lettered": 0, "retried": 0}
        try:
            messages = self._read_group(count=count, block_ms=block_ms)
        except Exception as exc:
            # NOGROUP 只在消费组不存在时出现，是可恢复的；其它错误照常上抛。
            if "NOGROUP" not in str(exc) or not self._recover_missing_group():
                raise
            messages = self._read_group(count=count, block_ms=block_ms)
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
