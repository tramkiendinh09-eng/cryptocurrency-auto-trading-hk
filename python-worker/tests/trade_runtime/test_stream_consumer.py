import json

from trade_runtime.stream_consumer import StreamConsumer


def test_stream_consumer_acknowledges_and_persists_new_message_once():
    handled = []
    captured = {"acks": [], "group_create": []}

    class StubRedis:
        def __init__(self):
            self.messages = [
                (
                    "trade.runtime.events",
                    [
                        (
                            "1710000000000-0",
                            {
                                "trace_id": "trace-1",
                                "event_type": "news",
                                "symbol": "BTCUSDT",
                                "exchange": "external",
                                "event_time": "2026-04-17T10:15:00Z",
                                "source_type": "news",
                                "source_name": "rss",
                                "payload_json": json.dumps(
                                    {
                                        "event_type": "news",
                                        "symbol": "BTCUSDT",
                                        "exchange": "external",
                                        "headline": "ETF inflow",
                                    },
                                    ensure_ascii=True,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ),
                                "idempotency_key": "trace-1:news:BTCUSDT:dedupe",
                            },
                        )
                    ],
                )
            ]

        def xgroup_create(self, stream_name, group_name, id="$", mkstream=True):
            captured["group_create"].append((stream_name, group_name, id, mkstream))

        def xreadgroup(self, group_name, consumer_name, streams, count=1, block=0):
            captured["xreadgroup"] = {
                "group_name": group_name,
                "consumer_name": consumer_name,
                "streams": streams,
                "count": count,
                "block": block,
            }
            if self.messages:
                return [self.messages.pop(0)]
            return []

        def set(self, key, value, nx=True, ex=None):
            captured["dedupe"] = {"key": key, "value": value, "nx": nx, "ex": ex}
            return True

        def xack(self, stream_name, group_name, message_id):
            captured["acks"].append((stream_name, group_name, message_id))
            return 1

        def hdel(self, name, key):
            captured.setdefault("hdel", []).append((name, key))
            return 1

    consumer = StreamConsumer(
        redis_client=StubRedis(),
        stream_name="trade.runtime.events",
        group_name="trade-runtime.persist",
        consumer_name="worker-1",
        handler=lambda event: handled.append(event),
    )

    result = consumer.consume_once(count=1)

    assert result["processed"] == 1
    assert result["acked"] == 1
    assert result["duplicates"] == 0
    assert handled[0].trace_id == "trace-1"
    assert handled[0].payload["headline"] == "ETF inflow"
    assert captured["acks"] == [("trade.runtime.events", "trade-runtime.persist", "1710000000000-0")]


def test_stream_consumer_skips_duplicate_message_and_acknowledges():
    handled = []
    captured = {"acks": []}

    class StubRedis:
        def xgroup_create(self, stream_name, group_name, id="$", mkstream=True):
            return True

        def xreadgroup(self, group_name, consumer_name, streams, count=1, block=0):
            return [
                (
                    "trade.runtime.events",
                    [
                        (
                            "1710000000001-0",
                            {
                                "trace_id": "trace-1",
                                "event_type": "news",
                                "symbol": "BTCUSDT",
                                "exchange": "external",
                                "event_time": "2026-04-17T10:16:00Z",
                                "source_type": "news",
                                "source_name": "rss",
                                "payload_json": '{"event_type":"news","symbol":"BTCUSDT"}',
                                "idempotency_key": "trace-1:news:BTCUSDT:dedupe",
                            },
                        )
                    ],
                )
            ]

        def set(self, key, value, nx=True, ex=None):
            return False

        def xack(self, stream_name, group_name, message_id):
            captured["acks"].append((stream_name, group_name, message_id))
            return 1

        def hdel(self, name, key):
            return 1

    consumer = StreamConsumer(
        redis_client=StubRedis(),
        stream_name="trade.runtime.events",
        group_name="trade-runtime.persist",
        consumer_name="worker-1",
        handler=lambda event: handled.append(event),
    )

    result = consumer.consume_once(count=1)

    assert result["processed"] == 0
    assert result["acked"] == 1
    assert result["duplicates"] == 1
    assert handled == []
    assert captured["acks"] == [("trade.runtime.events", "trade-runtime.persist", "1710000000001-0")]


def test_stream_consumer_retries_then_dead_letters_poison_message():
    handled = []
    captured = {"acks": [], "xadd": [], "retry_calls": 0}

    class StubRedis:
        def xgroup_create(self, stream_name, group_name, id="$", mkstream=True):
            return True

        def xreadgroup(self, group_name, consumer_name, streams, count=1, block=0):
            return [
                (
                    "trade.runtime.events",
                    [
                        (
                            "1710000000002-0",
                            {
                                "trace_id": "trace-1",
                                "event_type": "social",
                                "symbol": "BTCUSDT",
                                "exchange": "external",
                                "event_time": "2026-04-17T10:17:00Z",
                                "source_type": "social",
                                "source_name": "x",
                                "payload_json": '{"event_type":"social","symbol":"BTCUSDT","score":0.9}',
                                "idempotency_key": "trace-1:social:BTCUSDT:dedupe",
                            },
                        )
                    ],
                )
            ]

        def set(self, key, value, nx=True, ex=None):
            return True

        def hincrby(self, name, key, amount):
            captured["retry_calls"] += 1
            return 3

        def xadd(self, stream_name, payload):
            captured["xadd"].append((stream_name, payload))
            return "900-1"

        def xack(self, stream_name, group_name, message_id):
            captured["acks"].append((stream_name, group_name, message_id))
            return 1

        def hdel(self, name, key):
            captured.setdefault("hdel", []).append((name, key))
            return 1

    consumer = StreamConsumer(
        redis_client=StubRedis(),
        stream_name="trade.runtime.events",
        group_name="trade-runtime.persist",
        consumer_name="worker-1",
        handler=lambda event: handled.append(event) or (_ for _ in ()).throw(RuntimeError("persist failed")),
        dead_letter_stream="trade.runtime.events.dlq",
        max_retries=3,
    )

    result = consumer.consume_once(count=1)

    assert result["processed"] == 0
    assert result["acked"] == 1
    assert result["dead_lettered"] == 1
    assert len(handled) == 1
    assert captured["xadd"][0][0] == "trade.runtime.events.dlq"
    assert captured["xadd"][0][1]["error_message"] == "persist failed"
    assert captured["acks"] == [("trade.runtime.events", "trade-runtime.persist", "1710000000002-0")]


def test_stream_consumer_rehydrates_active_signal_metadata_from_stream_entry():
    handled = []

    class StubRedis:
        def xgroup_create(self, stream_name, group_name, id="$", mkstream=True):
            return True

        def xreadgroup(self, group_name, consumer_name, streams, count=1, block=0):
            return [
                (
                    "trade.runtime.events",
                    [
                        (
                            "1710000000003-0",
                            {
                                "trace_id": "trace-2",
                                "event_type": "news",
                                "symbol": "BTCUSDT",
                                "exchange": "external",
                                "event_time": "2026-04-17T10:18:00Z",
                                "source_type": "news",
                                "source_name": "rss",
                                "payload_json": '{"active_signal_ref":"news:BTCUSDT:15m","event_type":"news","symbol":"BTCUSDT"}',
                                "idempotency_key": "trace-2:news:BTCUSDT:dedupe",
                            },
                        )
                    ],
                )
            ]

        def set(self, key, value, nx=True, ex=None):
            return True

        def xack(self, stream_name, group_name, message_id):
            return 1

        def hdel(self, name, key):
            return 1

    consumer = StreamConsumer(
        redis_client=StubRedis(),
        stream_name="trade.runtime.events",
        group_name="trade-runtime.persist",
        consumer_name="worker-1",
        handler=lambda event: handled.append(event),
    )

    result = consumer.consume_once(count=1)

    assert result["processed"] == 1
    assert handled[0].payload["active_signal_ref"] == "news:BTCUSDT:15m"
