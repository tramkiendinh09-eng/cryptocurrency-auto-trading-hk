from trade_runtime.contracts.events import MarketTickEvent
from trade_runtime.streams import RuntimeStreamEvent
from trade_runtime.streams import StreamPublisher


def test_market_tick_serializes_to_stream_dict():
    event = MarketTickEvent(symbol="BTCUSDT", exchange="binance", price=65000.5, volume=12.4)

    payload = event.to_stream_entry()

    assert payload["event_type"] == "market_tick"
    assert payload["symbol"] == "BTCUSDT"
    assert payload["exchange"] == "binance"


def test_stream_publisher_accepts_normalized_dict_payload():
    captured = {}

    class StubRedis:
        def xadd(self, stream_name, payload):
            captured["stream_name"] = stream_name
            captured["payload"] = payload
            return "1-0"

    publisher = StreamPublisher(redis_client=StubRedis(), stream_name="trade.runtime.events")

    result = publisher.publish({"event_type": "news", "symbol": "BTCUSDT", "score": 0.8})

    assert result == "1-0"
    assert captured["stream_name"] == "trade.runtime.events"
    assert captured["payload"] == {
        "event_type": "news",
        "symbol": "BTCUSDT",
        "score": "0.8",
    }


def test_enhanced_market_events_default_to_market_source_type():
    for event_type in ("open_interest", "market_kline", "market_metric"):
        stream_event = RuntimeStreamEvent.from_event({"event_type": event_type, "symbol": "BTCUSDT", "exchange": "okx"})

        assert stream_event.source_type == "market"


def test_stream_publisher_wraps_runtime_event_contract_when_trace_and_source_metadata_provided():
    captured = {}

    class StubRedis:
        def xadd(self, stream_name, payload):
            captured["stream_name"] = stream_name
            captured["payload"] = payload
            return "2-0"

    publisher = StreamPublisher(redis_client=StubRedis(), stream_name="trade.runtime.events")

    result = publisher.publish(
        {
            "event_type": "news",
            "symbol": "BTCUSDT",
            "exchange": "external",
            "headline": "ETF inflow",
            "score": 0.8,
        },
        trace_id="trace-stream-1",
        source_metadata={
            "event_time": "2026-04-17T10:15:00Z",
            "source_type": "news",
            "source_name": "rss",
        },
    )

    assert result == "2-0"
    assert captured["stream_name"] == "trade.runtime.events"
    assert captured["payload"]["trace_id"] == "trace-stream-1"
    assert captured["payload"]["event_type"] == "news"
    assert captured["payload"]["symbol"] == "BTCUSDT"
    assert captured["payload"]["exchange"] == "external"
    assert captured["payload"]["event_time"] == "2026-04-17T10:15:00Z"
    assert captured["payload"]["source_type"] == "news"
    assert captured["payload"]["source_name"] == "rss"
    assert captured["payload"]["payload_json"] == (
        '{"event_type":"news","exchange":"external","headline":"ETF inflow","score":0.8,"symbol":"BTCUSDT"}'
    )
    assert captured["payload"]["idempotency_key"].startswith("trace-stream-1:news:BTCUSDT")


def test_stream_publisher_preserves_active_signal_metadata_inside_payload_json():
    captured = {}

    class StubRedis:
        def xadd(self, stream_name, payload):
            captured["stream_name"] = stream_name
            captured["payload"] = payload
            return "3-0"

    publisher = StreamPublisher(redis_client=StubRedis(), stream_name="trade.runtime.events")

    result = publisher.publish(
        {
            "event_type": "news",
            "symbol": "BTCUSDT",
            "exchange": "external",
            "headline": "ETF inflow",
            "active_signal_ref": "news:BTCUSDT:15m",
        },
        trace_id="trace-stream-active",
        source_metadata={"source_type": "news", "source_name": "rss"},
    )

    assert result == "3-0"
    assert captured["payload"]["payload_json"] == (
        '{"active_signal_ref":"news:BTCUSDT:15m","event_type":"news","exchange":"external","headline":"ETF inflow","symbol":"BTCUSDT"}'
    )
