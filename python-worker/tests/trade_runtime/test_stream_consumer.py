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


class _NoGroupError(Exception):
    """模拟 redis.exceptions.ResponseError 的 NOGROUP。"""


class _GroupVanishesRedis:
    """消费组在 __init__ 之后消失：第一次 xreadgroup 抛 NOGROUP，重建后才成功。

    线上真实故障：Redis 的 maxmemory-policy 是 allkeys-lru，会驱逐**任何** key，
    包括没有 TTL 的 trade.runtime.events 这条流；流被整个驱逐时消费组一起消失，
    之后 XADD 只重建流、不重建组。ensure_group() 只在 __init__ 跑一次，于是
    consume_once() 永远抛 NOGROUP，而这个消费者的 handler 正是把事件 POST 到
    后端——一挂就是 57 分钟 event_raw / market_metric_snapshot 完全没有写入，
    决策链路却照常跑，除了日志之外毫无征兆。
    """

    def __init__(self, message=None):
        self.group_creates = []
        self.reads = 0
        self.acks = []
        self._message = message

    def xgroup_create(self, stream_name, group_name, id="$", mkstream=True):
        self.group_creates.append((stream_name, group_name, id, mkstream))

    def xlen(self, stream_name):
        return 9483

    def xreadgroup(self, group_name, consumer_name, streams, count=1, block=0):
        self.reads += 1
        if self.reads == 1:
            raise _NoGroupError(
                "NOGROUP No such key 'trade.runtime.events' or consumer group "
                "'trade-runtime.persist' in XREADGROUP with GROUP option"
            )
        return [("trade.runtime.events", [self._message])] if self._message else []

    def set(self, *args, **kwargs):
        return True

    def delete(self, *args, **kwargs):
        return True

    def hincrby(self, *args, **kwargs):
        return 1

    def hdel(self, *args, **kwargs):
        return 1

    def xack(self, stream_name, group_name, message_id):
        self.acks.append(message_id)

    def xadd(self, *args, **kwargs):
        return "0-0"


def _consumer(redis_client, handler=lambda event: None):
    return StreamConsumer(
        redis_client=redis_client,
        stream_name="trade.runtime.events",
        group_name="trade-runtime.persist",
        consumer_name="worker-1",
        handler=handler,
    )


def test_missing_consumer_group_is_recreated_and_read_retried():
    redis_client = _GroupVanishesRedis()
    consumer = _consumer(redis_client)

    # 不该抛：NOGROUP 是可恢复的。
    consumer.consume_once(count=5)

    # __init__ 一次 + 恢复时一次
    assert len(redis_client.group_creates) == 2, redis_client.group_creates
    assert redis_client.reads == 2, "重建消费组之后必须重试本次读取"


def test_recovery_recreates_at_dollar_not_zero():
    """重建仍用 id="$"。

    去重键同样可能已被驱逐，从 0 重放会把同一批行情事件二次写进 event_raw，
    而下游聚合窗口会重复累加——宁可丢一段也不要污染。
    """
    redis_client = _GroupVanishesRedis()
    _consumer(redis_client).consume_once(count=1)

    assert [c[2] for c in redis_client.group_creates] == ["$", "$"]


def test_non_nogroup_errors_still_propagate():
    """只有 NOGROUP 才自愈，别的错误不能被吞掉。"""

    class _BrokenRedis(_GroupVanishesRedis):
        def xreadgroup(self, *args, **kwargs):
            raise _NoGroupError("WRONGTYPE Operation against a key holding the wrong kind of value")

    consumer = _consumer(_BrokenRedis())
    try:
        consumer.consume_once(count=1)
    except _NoGroupError:
        pass
    else:
        raise AssertionError("非 NOGROUP 的错误必须继续上抛")


def test_recovery_logs_skipped_backlog(caplog):
    """跳过的积压条数必须留在日志里，否则这段丢失无从察觉、也无从补。"""
    redis_client = _GroupVanishesRedis()
    with caplog.at_level("ERROR"):
        _consumer(redis_client).consume_once(count=1)
    assert "9483" in caplog.text, "必须记下跳过的积压条数"
