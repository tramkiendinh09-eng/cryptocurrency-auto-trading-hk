import logging
from datetime import datetime, timezone

import pytest

from trade_runtime.config import RuntimeConfig
from trade_runtime.ingestion.news_feed import NewsFeedAdapter
from trade_runtime.ingestion.onchain_feed import OnchainFeedAdapter
from trade_runtime.ingestion.social_feed import SocialFeedAdapter
from trade_runtime.active_signal_store import InMemoryActiveSignalStore
from trade_runtime.runtime_inputs import (
    BinancePublicMarketFeed,
    HttpJsonFeedSupplier,
    OkxPublicMarketFeed,
    RuntimeInputAssembler,
)


class _BinanceRestStub:
    """Routes the public futures endpoints the REST feed depends on."""

    RESPONSES = {
        "/fapi/v1/ticker/24hr": {
            "symbol": "BTCUSDT",
            "lastPrice": "65000.1",
            "quoteVolume": "123.4",
            "volume": "99.9",
            "priceChangePercent": "1.5",
            "closeTime": "1700000000000",
        },
        "/fapi/v1/premiumIndex": {
            "symbol": "BTCUSDT",
            "markPrice": "65010.0",
            "indexPrice": "65000.0",
            "lastFundingRate": "0.00075",
            "nextFundingTime": "1700028800000",
            "time": "1700000000000",
        },
        "/fapi/v1/openInterest": {
            "symbol": "BTCUSDT",
            "openInterest": "1000.0",
            "time": "1700000000000",
        },
        "/futures/data/openInterestHist": [
            {"sumOpenInterestValue": "1000000.0"},
            {"sumOpenInterestValue": "900000.0"},
        ],
    }

    def __init__(self):
        self.calls = []

    def __call__(self, url, params=None, timeout=None):
        path = url.replace("https://fapi.binance.com", "")
        self.calls.append(path)
        body = self.RESPONSES[path]

        class _Response:
            def raise_for_status(self):
                return None

            def json(self):
                return body

        return _Response()


def test_binance_public_market_feed_fetches_ticker_and_derivative_events(monkeypatch):
    """The REST path must carry the signals the websocket path used to carry.

    mark_price, funding_rate and open interest previously existed only on the
    websocket feed, so fundingRateAbs / markPriceDeviationPct and every
    open-interest signal had no data whenever the runtime ran on REST.
    """
    stub = _BinanceRestStub()
    monkeypatch.setattr("trade_runtime.ingestion.binance_rest.requests.get", stub)

    payload = BinancePublicMarketFeed(timeout=4).fetch("BTCUSDT")

    assert payload["s"] == "BTCUSDT"
    assert payload["c"] == pytest.approx(65000.1)
    assert payload["q"] == pytest.approx(123.4)
    assert "/fapi/v1/ticker/24hr" in stub.calls

    events = {event["event_type"]: event for event in payload["_market_events"]}
    assert set(events) == {"mark_price", "funding_rate", "open_interest"}

    assert events["mark_price"]["price"] == pytest.approx(65010.0)
    assert events["mark_price"]["index_price"] == pytest.approx(65000.0)
    assert events["funding_rate"]["funding_rate"] == pytest.approx(0.00075)
    assert events["open_interest"]["open_interest"] == pytest.approx(1000.0)
    # notional is what the size-based thresholds are written against
    assert events["open_interest"]["open_interest_notional_usd"] == pytest.approx(65010000.0)
    assert events["open_interest"]["open_interest_change_pct"] == pytest.approx(-10.0)

    for event in payload["_market_events"]:
        assert event["exchange"] == "binance"
        assert event["symbol"] == "BTCUSDT"


def test_binance_public_market_feed_throttles_derivative_endpoints(monkeypatch):
    """Funding settles 8-hourly; re-fetching it every poll only spends weight."""
    stub = _BinanceRestStub()
    monkeypatch.setattr("trade_runtime.ingestion.binance_rest.requests.get", stub)

    clock = {"now": 1000.0}
    feed = BinancePublicMarketFeed(timeout=4, derivative_min_refresh_seconds=30.0)
    feed._feed.time_fn = lambda: clock["now"]

    feed.fetch("BTCUSDT")
    first_round = list(stub.calls)
    assert "/fapi/v1/premiumIndex" in first_round

    clock["now"] += 5.0
    payload = feed.fetch("BTCUSDT")
    # ticker is refetched every call, derivatives come from cache
    assert stub.calls.count("/fapi/v1/ticker/24hr") == 2
    assert stub.calls.count("/fapi/v1/premiumIndex") == 1
    assert len(payload["_market_events"]) == 3

    clock["now"] += 60.0
    feed.fetch("BTCUSDT")
    assert stub.calls.count("/fapi/v1/premiumIndex") == 2


def test_binance_rest_feed_keeps_price_when_derivatives_fail(monkeypatch):
    """A derivative endpoint failing must not cost us the price tick.

    The tick is what keeps the market source healthy; risk/guard.py blocks every
    order once the source is judged abnormal.
    """
    stub = _BinanceRestStub()

    def flaky(url, params=None, timeout=None):
        if "premiumIndex" in url or "openInterest" in url:
            raise RuntimeError("boom")
        return stub(url, params=params, timeout=timeout)

    monkeypatch.setattr("trade_runtime.ingestion.binance_rest.requests.get", flaky)

    payload = BinancePublicMarketFeed(timeout=4).fetch("BTCUSDT")

    assert payload["c"] == pytest.approx(65000.1)
    assert "_market_events" not in payload


def test_okx_public_market_feed_fetches_swap_ticker(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": "0",
                "data": [{"instId": "BTC-USDT-SWAP", "last": "65002.1", "vol24h": "88.8"}],
            }

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.runtime_inputs.requests.get", fake_get)

    payload = OkxPublicMarketFeed(timeout=6).fetch("BTCUSDT")

    assert captured["url"] == "https://www.okx.com/api/v5/market/ticker"
    assert captured["params"] == {"instId": "BTC-USDT-SWAP"}
    assert captured["timeout"] == 6
    assert payload["data"][0]["instId"] == "BTC-USDT-SWAP"


def test_http_json_feed_supplier_returns_items_from_data_payload(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.8}]}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.runtime_inputs.requests.get", fake_get)

    items = HttpJsonFeedSupplier(url="http://feed.local/news", timeout=9).fetch("BTCUSDT")

    assert captured["url"] == "http://feed.local/news"
    assert captured["params"] == {"symbol": "BTCUSDT"}
    assert captured["timeout"] == 9
    assert items[0]["headline"] == "ETF inflow"


def test_http_json_feed_supplier_returns_empty_when_url_missing():
    supplier = HttpJsonFeedSupplier(url=None)

    assert supplier.fetch("BTCUSDT") == []


def test_http_json_feed_supplier_returns_unavailable_status_when_request_fails(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise RuntimeError("upstream timeout")

    monkeypatch.setattr("trade_runtime.runtime_inputs.requests.get", fake_get)

    payload = HttpJsonFeedSupplier(url="http://feed.local/news", timeout=3).fetch("BTCUSDT")

    assert payload["items"] == []
    assert payload["source_status"] == "unavailable"
    assert payload["error_message"] == "upstream timeout"


def test_feed_adapters_validate_required_fields_and_preserve_source_metadata():
    assert NewsFeedAdapter().normalize(
        {
            "symbol": "BTCUSDT",
            "headline": "ETF inflow accelerates",
            "source": "rss",
            "publishedAt": "2026-04-17T10:15:00Z",
        }
    ) == {
        "event_type": "news",
        "symbol": "BTCUSDT",
        "exchange": "external",
        "headline": "ETF inflow accelerates",
        "source": "rss",
        "event_time": "2026-04-17T10:15:00Z",
    }
    assert OnchainFeedAdapter().normalize(
        {
            "symbol": "BTCUSDT",
            "wallet": "whale-1",
            "flow": "EXCHANGE_OUTFLOW",
            "asset": "BTC",
            "route": "Coinbase Prime -> Unknown wallet",
            "amountUsd": 71900000,
            "impact": "high",
            "summary": "Large withdrawal from exchange",
            "source": "whale-alert",
            "timestamp": "2026-04-17T10:10:00Z",
        }
    ) == {
        "event_type": "onchain",
        "symbol": "BTCUSDT",
        "exchange": "external",
        "wallet": "whale-1",
        "flow": "exchange_outflow",
        "asset": "BTC",
        "route": "Coinbase Prime -> Unknown wallet",
        "amountUsd": 71900000,
        "impact": "high",
        "summary": "Large withdrawal from exchange",
        "source": "whale-alert",
        "event_time": "2026-04-17T10:10:00Z",
    }
    assert SocialFeedAdapter().normalize(
        {
            "symbol": "BTCUSDT",
            "score": 0.82,
            "source": "x",
            "author": "macro_anon",
            "createdAt": "2026-04-17T10:05:00Z",
        }
    ) == {
        "event_type": "social",
        "symbol": "BTCUSDT",
        "exchange": "external",
        "score": 0.82,
        "source": "x",
        "author": "macro_anon",
        "event_time": "2026-04-17T10:05:00Z",
    }
    with pytest.raises(ValueError, match="news_symbol_required"):
        NewsFeedAdapter().normalize({"headline": "missing symbol"})
    with pytest.raises(ValueError, match="onchain_flow_required"):
        OnchainFeedAdapter().normalize({"symbol": "BTCUSDT", "wallet": "whale-1"})
    with pytest.raises(ValueError, match="social_score_required"):
        SocialFeedAdapter().normalize({"symbol": "BTCUSDT", "headline": "missing score"})


def test_runtime_input_assembler_builds_event_bundle_and_price_change_pct():
    market_payloads = iter(
        [
            {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
            {"s": "BTCUSDT", "c": "105.0", "q": "3.0"},
        ]
    )

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        news_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "ETF inflow", "score": 0.8}],
        onchain_items_supplier=lambda symbol: [{"symbol": symbol, "wallet": "whale-1", "flow": "exchange_inflow"}],
        social_items_supplier=lambda symbol: [{"symbol": symbol, "score": 0.8}],
    )

    first = assembler.build(symbol="BTCUSDT")
    second = assembler.build(symbol="BTCUSDT")

    assert first["feature_snapshot"]["price_change_pct"] == 0.0
    assert second["feature_snapshot"]["price_change_pct"] == 5.0
    assert second["feature_snapshot"]["news_score"] == 0.8
    assert second["feature_snapshot"]["social_score"] == 0.8
    assert second["feature_snapshot"]["onchain_flow_bias"] == -1.0
    assert second["feature_snapshot"]["event_strength"] == "strong"
    assert [item["event_type"] for item in second["event_bundle"]] == [
        "market_tick",
        "news",
        "onchain",
        "social",
    ]
    assert [item["window_key"] for item in second["signal_window_states"]] == [
        "market:BTCUSDT:15m",
        "news:BTCUSDT:15m",
        "onchain:BTCUSDT:15m",
        "social:BTCUSDT:15m",
    ]
    assert second["signal_window_states"][0]["state"]["count"] == 2
    assert second["signal_window_states"][0]["state"]["price_change_pct"] == 5.0
    assert second["signal_window_states"][1]["state"]["count"] == 1
    assert second["signal_window_states"][1]["state"]["max_score"] == 0.8


def test_runtime_input_assembler_posts_each_event_with_trace_id():
    posted = []

    class StubEventClient:
        def post_event(self, *, trace_id, event):
            posted.append({"trace_id": trace_id, "event": event})

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "ETF inflow"}],
        event_client=StubEventClient(),
    )

    assembler.build(symbol="BTCUSDT", trace_id="trace-22")

    assert [item["trace_id"] for item in posted] == ["trace-22", "trace-22"]
    assert [item["event"]["event_type"] for item in posted] == ["market_tick", "news"]


def test_runtime_input_assembler_keeps_building_when_event_post_fails(caplog):
    class StubEventClient:
        def post_event(self, *, trace_id, event):
            raise RuntimeError("backend ingest down")

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "ETF inflow"}],
        event_client=StubEventClient(),
    )

    with caplog.at_level(logging.WARNING, logger="trade_runtime.runtime_inputs"):
        result = assembler.build(symbol="BTCUSDT", trace_id="trace-22")

    assert result["event_bundle"][0]["event_type"] == "market_tick"
    assert "event emit failed" in caplog.text


def test_runtime_input_assembler_marks_market_unavailable_when_supplier_fails(caplog):
    def raise_market_error(symbol):
        raise RuntimeError("exchange restricted")

    assembler = RuntimeInputAssembler(
        exchange="okx",
        market_payload_supplier=raise_market_error,
    )

    with caplog.at_level(logging.WARNING, logger="trade_runtime.runtime_inputs"):
        result = assembler.build(symbol="BTCUSDT", trace_id="trace-23")

    assert result["market_source_status"] == "unavailable"
    assert any(event.get("event_type") == "market_source_abnormal" for event in result["event_bundle"])
    assert "market payload fetch failed" in caplog.text


def test_runtime_input_assembler_dedupes_repeated_news_for_event_posting():
    posted = []
    market_payloads = iter(
        [
            {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
            {"s": "BTCUSDT", "c": "101.0", "q": "2.5"},
        ]
    )
    news_payload = [
        {
            "symbol": "BTCUSDT",
            "headline": "ETF inflow remains strong",
            "source": "rss",
            "publishedAt": "2026-04-17T09:58:00Z",
            "score": 0.82,
        }
    ]

    class StubEventClient:
        def post_event(self, *, trace_id, event):
            posted.append({"trace_id": trace_id, "event": event})

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        news_items_supplier=lambda symbol: news_payload,
        event_client=StubEventClient(),
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 1, tzinfo=timezone.utc),
    )

    assembler.build(symbol="BTCUSDT", trace_id="trace-dup-1")
    assembler.build(symbol="BTCUSDT", trace_id="trace-dup-2")

    assert [item["event"]["event_type"] for item in posted] == ["market_tick", "news", "market_tick"]
    assert [item["trace_id"] for item in posted] == ["trace-dup-1", "trace-dup-1", "trace-dup-2"]


def test_runtime_input_assembler_publishes_normalized_events_to_stream():
    published = []

    class StubPublisher:
        def publish(self, event, *, trace_id="", source_metadata=None):
            published.append(
                {
                    "event": event,
                    "trace_id": trace_id,
                    "source_metadata": source_metadata,
                }
            )
            return f"stream-{len(published)}"

    drained = []

    class StubStreamConsumer:
        def consume_available(self, *, max_messages, block_ms=0):
            drained.append({"max_messages": max_messages, "block_ms": block_ms})
            return {"processed": max_messages}

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "ETF inflow", "score": 0.7}],
        social_items_supplier=lambda symbol: [{"symbol": symbol, "score": 0.8}],
        stream_publisher=StubPublisher(),
        stream_consumer=StubStreamConsumer(),
    )

    assembler.build(symbol="BTCUSDT", trace_id="trace-stream")

    assert [item["event"]["event_type"] for item in published] == ["market_tick", "news", "social"]
    assert [item["trace_id"] for item in published] == ["trace-stream", "trace-stream", "trace-stream"]
    assert drained == [{"max_messages": 3, "block_ms": 0}]


def test_runtime_input_assembler_dedupes_repeated_news_for_stream_publish():
    published = []
    market_payloads = iter(
        [
            {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
            {"s": "BTCUSDT", "c": "101.0", "q": "2.5"},
        ]
    )
    news_payload = [
        {
            "symbol": "BTCUSDT",
            "headline": "ETF inflow remains strong",
            "source": "rss",
            "publishedAt": "2026-04-17T09:58:00Z",
            "score": 0.82,
        }
    ]

    class StubPublisher:
        def publish(self, event, *, trace_id="", source_metadata=None):
            published.append({"trace_id": trace_id, "event": event, "source_metadata": source_metadata})
            return f"stream-{len(published)}"

    class StubStreamConsumer:
        def consume_available(self, *, max_messages, block_ms=0):
            return {"processed": max_messages}

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        news_items_supplier=lambda symbol: news_payload,
        stream_publisher=StubPublisher(),
        stream_consumer=StubStreamConsumer(),
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 1, tzinfo=timezone.utc),
    )

    assembler.build(symbol="BTCUSDT", trace_id="trace-stream-1")
    assembler.build(symbol="BTCUSDT", trace_id="trace-stream-2")

    assert [item["event"]["event_type"] for item in published] == ["market_tick", "news", "market_tick"]
    assert [item["trace_id"] for item in published] == ["trace-stream-1", "trace-stream-1", "trace-stream-2"]


def test_runtime_input_assembler_prefers_stream_backbone_over_direct_http_ingest():
    published = []
    posted = []
    drained = []

    class StubPublisher:
        def publish(self, event, *, trace_id="", source_metadata=None):
            published.append({"event": event, "trace_id": trace_id, "source_metadata": source_metadata})
            return f"stream-{len(published)}"

    class StubStreamConsumer:
        def consume_available(self, *, max_messages, block_ms=0):
            drained.append({"max_messages": max_messages, "block_ms": block_ms})
            return {"processed": max_messages}

    class StubEventClient:
        def post_event(self, *, trace_id, event):
            posted.append({"trace_id": trace_id, "event": event})

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "ETF inflow", "score": 0.7}],
        stream_publisher=StubPublisher(),
        stream_consumer=StubStreamConsumer(),
        event_client=StubEventClient(),
    )

    assembler.build(symbol="BTCUSDT", trace_id="trace-primary-stream")

    assert [item["event"]["event_type"] for item in published] == ["market_tick", "news"]
    assert drained == [{"max_messages": 2, "block_ms": 0}]
    assert posted == []


def test_runtime_input_assembler_emits_explicit_source_health_for_empty_stale_and_malformed_feeds():
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [],
        onchain_items_supplier=lambda symbol: [
            {
                "symbol": symbol,
                "wallet": "whale-1",
                "flow": "exchange_outflow",
                "source": "whale-alert",
                "timestamp": "2026-04-17T08:00:00Z",
            }
        ],
        social_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "missing score"}],
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 30, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="BTCUSDT", trace_id="trace-source-health")

    assert {
        (event["source_type"], event["source_status"])
        for event in result["event_bundle"]
        if event.get("event_type") == "source_health"
    } == {
        ("news", "ready_empty"),
        ("onchain", "stale_items_filtered"),
        ("social", "malformed"),
    }
    assert result["feature_snapshot"]["source_health"] == {
        "news": "ready_empty",
        "onchain": "stale_items_filtered",
        "social": "malformed",
    }
    assert result["feature_snapshot"]["degraded_sources"] == ["social"]


def test_runtime_input_assembler_keeps_prior_news_signal_for_later_market_confirmation():
    market_payloads = iter(
        [
            {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
            {"s": "BTCUSDT", "c": "103.0", "q": "2.5"},
        ]
    )
    news_payloads = iter(
        [
            [{"symbol": "BTCUSDT", "headline": "ETF approval", "score": 0.92}],
            [],
        ]
    )
    current_times = iter(
        [
            datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 17, 8, 5, tzinfo=timezone.utc),
        ]
    )

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        news_items_supplier=lambda symbol: next(news_payloads),
        active_signal_store=InMemoryActiveSignalStore(),
        current_time_supplier=lambda: next(current_times),
    )

    first = assembler.build(symbol="BTCUSDT")
    second = assembler.build(symbol="BTCUSDT")

    assert [item["source_type"] for item in first["signal_window_states"]] == ["market", "news"]
    assert [item["source_type"] for item in second["signal_window_states"]] == ["market", "news"]
    assert second["signal_window_states"][1]["state"]["latest_headline"] == "ETF approval"
    assert second["trigger_summary"]["active_sources"] == ["market", "news"]
    assert second["trigger_summary"]["active_signal_count"] == 2


def test_runtime_input_assembler_treats_ready_empty_aux_source_as_healthy():
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        onchain_items_supplier=lambda symbol: {"items": [], "source_status": "ready", "source_name": "onchain"},
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 30, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="BTCUSDT", trace_id="trace-ready-empty-onchain")

    assert [item["event_type"] for item in result["event_bundle"]] == ["market_tick", "source_health"]
    assert result["event_bundle"][1]["source_type"] == "onchain"
    assert result["event_bundle"][1]["source_status"] == "ready_empty"
    assert result["event_bundle"][1]["reason"] == "no_fresh_items"
    assert result["feature_snapshot"]["source_health"] == {"onchain": "ready_empty"}
    assert result["feature_snapshot"]["degraded_sources"] == []
    assert result["feature_snapshot"]["aux_source_status"] == "ready"


def test_runtime_input_assembler_filters_stale_onchain_items_without_data_gap():
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        onchain_items_supplier=lambda symbol: [
            {
                "symbol": symbol,
                "wallet": "OKX: Cold Wallet -> Unknown wallet",
                "flow": "exchange_outflow",
                "amountUsd": 41600000,
                "source": "onchainflows.io",
                "event_time": "2026-04-17T09:00:00Z",
            }
        ],
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 30, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="BTCUSDT", trace_id="trace-stale-filtered-onchain")

    assert [item["event_type"] for item in result["event_bundle"]] == ["market_tick", "source_health"]
    assert result["event_bundle"][1]["source_type"] == "onchain"
    assert result["event_bundle"][1]["source_status"] == "stale_items_filtered"
    assert result["event_bundle"][1]["reason"] == "event_time_stale"
    assert result["feature_snapshot"]["onchain_flow_bias"] == 0.0
    assert result["feature_snapshot"]["source_health"] == {"onchain": "stale_items_filtered"}
    assert result["feature_snapshot"]["degraded_sources"] == []
    assert result["feature_snapshot"]["aux_source_status"] == "ready"


def test_runtime_input_assembler_accepts_preloaded_market_context_history():
    seed_history = [
        {
            "observed_at": f"2026-04-17T09:{minute:02d}:00+00:00",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "price": 100 + minute,
            "volume": 10 + minute,
            "quote_volume": 1000 + minute,
        }
        for minute in range(10)
    ]
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "110.0", "q": "2000.0"},
        initial_market_context_history={"BTCUSDT": seed_history},
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="BTCUSDT", trace_id="trace-preloaded-market-history")

    assert len(result["market_context_history"]) == 11
    assert result["market_context_history"][0]["price"] == 100
    assert result["market_context_history"][-1]["price"] == 110.0


def test_runtime_input_assembler_uses_configurable_market_context_history_limit():
    seed_history = [
        {
            "observed_at": f"2026-04-17T09:{minute:02d}:00+00:00",
            "symbol": "ETHUSDT",
            "exchange": "binance",
            "price": 100 + minute,
        }
        for minute in range(5)
    ]
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "ETHUSDT", "c": "200.0", "q": "2000.0"},
        initial_market_context_history={"ETHUSDT": seed_history},
        market_context_history_limit=3,
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="ETHUSDT", trace_id="trace-configurable-market-history-limit")

    assert [item["price"] for item in result["market_context_history"]] == [103, 104, 200.0]


def test_runtime_input_assembler_trusts_news_supplier_freshness_and_does_not_recheck_event_time():
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [
            {
                "symbol": symbol,
                "headline": "Older headline A",
                "score": 0.91,
                "publishedAt": "2026-04-17T04:00:00Z",
                "source": "rss-A",
            },
            {
                "symbol": symbol,
                "headline": "Older headline B",
                "score": 0.67,
                "publishedAt": "2026-04-17T03:30:00Z",
                "source": "rss-B",
            },
        ],
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 30, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="BTCUSDT", trace_id="trace-trust-news-supplier")

    assert [item["event_type"] for item in result["event_bundle"]] == ["market_tick", "news", "news"]
    assert result["feature_snapshot"]["news_score"] == 0.91
    assert result["feature_snapshot"]["source_health"] == {}
    assert result["feature_snapshot"]["degraded_sources"] == []
    assert result["feature_snapshot"]["aux_source_status"] == "ready"
    assert [item["source_type"] for item in result["signal_window_states"]] == ["market", "news"]
    assert result["trigger_summary"]["active_sources"] == ["market", "news"]
    assert result["trigger_summary"]["active_signal_count"] == 2


def test_runtime_input_assembler_excludes_stale_news_source_payload_from_signals():
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: {
            "items": [],
            "source_status": "stale",
            "source_name": "news",
            "error_message": "event_time_stale",
        },
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 30, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="BTCUSDT", trace_id="trace-stale-news-source")

    assert [item["event_type"] for item in result["event_bundle"]] == ["market_tick", "source_health"]
    assert result["event_bundle"][1]["source_type"] == "news"
    assert result["event_bundle"][1]["source_status"] == "stale"
    assert result["feature_snapshot"]["news_score"] == 0.0
    assert result["feature_snapshot"]["source_health"] == {"news": "stale"}
    assert result["feature_snapshot"]["degraded_sources"] == ["news"]
    assert result["feature_snapshot"]["aux_source_status"] == "aux_source_degraded"
    assert [item["source_type"] for item in result["signal_window_states"]] == ["market"]
    assert result["trigger_summary"]["active_sources"] == ["market"]
    assert result["trigger_summary"]["active_signal_count"] == 1


def test_runtime_input_assembler_keeps_market_source_ready_when_only_aux_sources_are_degraded():
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: {
            "items": [],
            "source_status": "unavailable",
            "source_name": "news",
            "error_message": "upstream timeout",
        },
        social_items_supplier=lambda symbol: {
            "items": [],
            "source_status": "stale",
            "source_name": "social",
            "error_message": "event_time_stale",
        },
    )

    result = assembler.build(symbol="BTCUSDT", trace_id="trace-aux-source-degraded")

    assert result["market_source_status"] == "ready"
    assert result["feature_snapshot"]["source_health"] == {
        "news": "unavailable",
        "social": "stale",
    }
    assert result["feature_snapshot"]["degraded_sources"] == ["news", "social"]
    assert result["feature_snapshot"]["aux_source_status"] == "aux_source_degraded"


def test_runtime_input_assembler_dedupes_repeated_news_items_across_cycles():
    market_payloads = iter(
        [
            {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
            {"s": "BTCUSDT", "c": "100.0", "q": "2.5"},
        ]
    )
    news_payload = [
        {
            "symbol": "BTCUSDT",
            "headline": "ETF approval stays in focus",
            "score": 0.83,
            "publishedAt": "2026-04-17T09:58:00Z",
            "source": "rss",
        }
    ]
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        news_items_supplier=lambda symbol: news_payload,
        active_signal_store=InMemoryActiveSignalStore(),
        current_time_supplier=lambda: datetime(2026, 4, 17, 10, 1, tzinfo=timezone.utc),
    )

    first = assembler.build(symbol="BTCUSDT")
    second = assembler.build(symbol="BTCUSDT")

    assert first["feature_snapshot"]["news_score"] == 0.83
    assert second["feature_snapshot"]["news_score"] == 0.83
    assert first["signal_window_states"][1]["source_type"] == "news"
    assert first["signal_window_states"][1]["state"]["count"] == 1
    assert second["signal_window_states"][1]["source_type"] == "news"
    assert second["signal_window_states"][1]["state"]["count"] == 1
    assert second["signal_window_states"][1]["state"]["latest_headline"] == "ETF approval stays in focus"


def test_runtime_input_assembler_uses_runtime_policy_for_event_strength():
    payloads = iter(
        [
            {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
            {"s": "BTCUSDT", "c": "101.2", "q": "3.0"},
        ]
    )
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"ruleOnlyPriceChangePct":1.0,"priceChangePct":2.5}}',
    ).model_dump()

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(payloads),
    )

    assembler.build(symbol="BTCUSDT", runtime_config=runtime_config, strategy_context={})
    second = assembler.build(symbol="BTCUSDT", runtime_config=runtime_config, strategy_context={})

    assert second["feature_snapshot"]["price_change_pct"] == 1.2
    assert second["feature_snapshot"]["event_strength"] == "normal"


def test_runtime_input_assembler_includes_supplemental_market_events_and_uses_market_config_thresholds():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"liquidationNotionalUsd":250000,"ruleOnlyPriceChangePct":1.0,"priceChangePct":2.5}}',
    ).model_dump()
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {
            "s": "BTCUSDT",
            "c": "100.0",
            "q": "2.0",
            "_market_events": [
                {"event_type": "mark_price", "symbol": "BTCUSDT", "exchange": "binance", "price": 100.3},
                {"event_type": "funding_rate", "symbol": "BTCUSDT", "exchange": "binance", "funding_rate": 0.0008},
                {
                    "event_type": "liquidation",
                    "symbol": "BTCUSDT",
                    "exchange": "binance",
                    "side": "SELL",
                    "price": 99.8,
                    "quantity": 3000,
                    "notionalUsd": 299400.0,
                },
            ],
        },
        active_signal_store=InMemoryActiveSignalStore(),
        current_time_supplier=lambda: datetime(2026, 4, 23, 9, 0, tzinfo=timezone.utc),
    )

    result = assembler.build(symbol="BTCUSDT", runtime_config=runtime_config, strategy_context={})

    assert [item["event_type"] for item in result["event_bundle"]] == [
        "market_tick",
        "mark_price",
        "funding_rate",
        "liquidation",
    ]
    assert result["feature_snapshot"]["funding_rate"] == 0.0008
    assert result["feature_snapshot"]["event_strength"] == "strong"


def test_runtime_input_assembler_returns_bounded_market_context_history():
    market_payloads = iter(
        [
            {
                "s": "BTCUSDT",
                "c": "100.0",
                "q": "2000.0",
                "_market_events": [
                    {"event_type": "mark_price", "symbol": "BTCUSDT", "exchange": "binance", "price": 100.2},
                    {"event_type": "funding_rate", "symbol": "BTCUSDT", "exchange": "binance", "funding_rate": 0.0003},
                ],
            },
            {
                "s": "BTCUSDT",
                "c": "103.0",
                "q": "3400.0",
                "_market_events": [
                    {"event_type": "mark_price", "symbol": "BTCUSDT", "exchange": "binance", "price": 103.4},
                    {
                        "event_type": "liquidation",
                        "symbol": "BTCUSDT",
                        "exchange": "binance",
                        "side": "SELL",
                        "price": 102.7,
                        "quantity": 10,
                        "notionalUsd": 1027.0,
                    },
                ],
            },
        ]
    )
    current_times = iter(
        [
            datetime(2026, 4, 24, 7, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 24, 7, 5, tzinfo=timezone.utc),
        ]
    )
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        current_time_supplier=lambda: next(current_times),
    )

    first = assembler.build(symbol="BTCUSDT")
    second = assembler.build(symbol="BTCUSDT")

    assert [item["price"] for item in first["market_context_history"]] == [100.0]
    assert [item["price"] for item in second["market_context_history"]] == [100.0, 103.0]
    assert second["market_context_history"][0]["quote_volume"] == 2000.0
    assert second["market_context_history"][1]["mark_price"] == 103.4
    assert second["market_context_history"][1]["largest_liquidation_notional_usd"] == 1027.0


def test_runtime_input_assembler_prefers_latest_market_tick_for_history_price():
    current_time = datetime(2024, 4, 30, 9, 0, 30, tzinfo=timezone.utc)
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {
            "s": "ETHUSDT",
            "c": "100.0",
            "q": "5000.0",
            "_market_events": [
                {
                    "event_type": "market_tick",
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 103.0,
                    "volume": 53.0,
                    "quote_volume": 5300.0,
                    "event_time": "1714467630000",
                },
                {
                    "event_type": "mark_price",
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 102.8,
                    "event_time": "1714467630000",
                },
            ],
        },
        current_time_supplier=lambda: current_time,
    )

    result = assembler.build(symbol="ETHUSDT", trace_id="trace-latest-market-tick-history")

    history_entry = result["market_context_history"][-1]
    assert history_entry["price"] == 103.0
    assert history_entry["latest_trade_price"] == 103.0
    assert history_entry["effective_price"] == 103.0
    assert history_entry["effective_price_source"] == "trade"
    assert result["feature_snapshot"]["effective_price"] == 103.0
    assert result["feature_snapshot"]["effective_price_source"] == "trade"


def test_runtime_input_assembler_refreshes_okx_trade_tick_from_rest_when_ws_tick_is_stale():
    current_time = datetime(2024, 4, 30, 9, 5, 0, tzinfo=timezone.utc)

    class StubRestClient:
        def fetch_ticker(self, symbol):
            return {
                "event_type": "market_tick",
                "symbol": "ETHUSDT",
                "exchange": "okx",
                "price": 105.0,
                "volume": 60.0,
                "quote_volume": 6000.0,
                "event_time": "1714467890000",
            }

        def fetch_mark_price(self, symbol):
            return {
                "event_type": "mark_price",
                "symbol": "ETHUSDT",
                "exchange": "okx",
                "price": 104.0,
                "event_time": "1714467890000",
            }

        def fetch_funding_rate(self, symbol):
            return {"event_type": "funding_rate", "symbol": "ETHUSDT", "exchange": "okx", "funding_rate": 0.0}

        def fetch_open_interest(self, symbol):
            return {"event_type": "open_interest", "symbol": "ETHUSDT", "exchange": "okx", "open_interest": 1000.0}

        def fetch_candles(self, symbol, interval="1m", limit=120):
            return []

    assembler = RuntimeInputAssembler(
        exchange="okx",
        market_payload_supplier=lambda symbol: {
            "data": [
                {
                    "instId": "ETH-USDT-SWAP",
                    "last": "100.0",
                    "vol24h": "50.0",
                    "volCcyQuote24h": "5000.0",
                    "ts": "1714467600000",
                }
            ],
        },
        rest_market_client=StubRestClient(),
        current_time_supplier=lambda: current_time,
    )

    result = assembler.build(symbol="ETHUSDT", trace_id="trace-okx-rest-ticker-refresh")

    assert result["feature_snapshot"]["trade_tick_status"] == "ready"
    assert result["feature_snapshot"]["latest_trade_price"] == 105.0
    assert result["feature_snapshot"]["stale_trade_price"] == 0.0
    assert result["feature_snapshot"]["latest_price"] == 105.0
    assert result["feature_snapshot"]["effective_price"] == 105.0
    assert result["feature_snapshot"]["effective_price_source"] == "trade"
    assert result["feature_snapshot"]["market_tick_staleness_seconds"] == 10.0


def test_runtime_input_assembler_falls_back_to_mark_price_when_trade_tick_is_stale():
    current_time = datetime(2024, 4, 30, 9, 5, 0, tzinfo=timezone.utc)
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {
            "s": "ETHUSDT",
            "c": "100.0",
            "q": "5000.0",
            "_market_events": [
                {
                    "event_type": "market_tick",
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 100.0,
                    "volume": 50.0,
                    "quote_volume": 5000.0,
                    "event_time": "1714467600000",
                },
                {
                    "event_type": "mark_price",
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 104.0,
                    "event_time": "1714467900000",
                }
            ],
        },
        current_time_supplier=lambda: current_time,
    )

    result = assembler.build(symbol="ETHUSDT", trace_id="trace-stale-trade-effective-price")

    history_entry = result["market_context_history"][-1]
    assert history_entry["latest_trade_price"] == 100.0
    assert history_entry["price"] == 104.0
    assert history_entry["effective_price"] == 104.0
    assert history_entry["effective_price_source"] == "mark_price"
    assert history_entry["market_tick_staleness_seconds"] == 300.0
    assert result["feature_snapshot"]["latest_price"] == 104.0
    assert result["feature_snapshot"]["stale_trade_price"] == 100.0
    assert result["feature_snapshot"]["trade_tick_status"] == "stale"
    assert result["feature_snapshot"]["trade_tick_age_seconds"] == 300.0
    assert result["feature_snapshot"]["effective_price"] == 104.0
    assert result["feature_snapshot"]["effective_price_source"] == "mark_price"
    assert result["feature_snapshot"]["market_tick_staleness_seconds"] == 300.0


def test_runtime_input_assembler_keeps_market_source_ready_when_fresh_mark_price_covers_stale_trade_tick():
    current_time = datetime(2024, 4, 30, 9, 5, 0, tzinfo=timezone.utc)
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {
            "s": "ETHUSDT",
            "c": "100.0",
            "q": "5000.0",
            "_market_source_status": "ready",
            "_market_events": [
                {
                    "event_type": "market_tick",
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 100.0,
                    "volume": 50.0,
                    "quote_volume": 5000.0,
                    "event_time": "1714467600000",
                },
                {
                    "event_type": "mark_price",
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 104.0,
                    "event_time": "1714467870000",
                },
            ],
        },
        current_time_supplier=lambda: current_time,
    )

    result = assembler.build(symbol="ETHUSDT", trace_id="trace-stale-trade-ready-market-source")

    assert result["market_source_status"] == "ready"
    assert result["feature_snapshot"]["effective_price_source"] == "mark_price"
    assert not any(event.get("event_type") == "stale" for event in result["event_bundle"])


def test_runtime_input_assembler_marks_market_source_stale_when_trade_tick_is_stale():
    current_time = datetime(2024, 4, 30, 9, 5, 0, tzinfo=timezone.utc)
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {
            "s": "ETHUSDT",
            "c": "100.0",
            "q": "5000.0",
            "_market_source_status": "ready",
            "_market_events": [
                {
                    "event_type": "market_tick",
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 100.0,
                    "volume": 50.0,
                    "quote_volume": 5000.0,
                    "event_time": "1714467600000",
                }
            ],
        },
        current_time_supplier=lambda: current_time,
    )

    result = assembler.build(symbol="ETHUSDT", trace_id="trace-stale-market-status")

    assert result["market_source_status"] == "stale"
    assert any(event.get("event_type") == "stale" for event in result["event_bundle"])


def test_runtime_input_assembler_uses_effective_price_for_price_change_when_trade_tick_is_stale():
    market_payloads = iter(
        [
            {
                "s": "ETHUSDT",
                "c": "100.0",
                "q": "5000.0",
                "_market_events": [
                    {
                        "event_type": "market_tick",
                        "symbol": "ETHUSDT",
                        "exchange": "binance",
                        "price": 100.0,
                        "volume": 50.0,
                        "quote_volume": 5000.0,
                        "event_time": "1714467600000",
                    },
                    {
                        "event_type": "mark_price",
                        "symbol": "ETHUSDT",
                        "exchange": "binance",
                        "price": 104.0,
                        "event_time": "1714467900000",
                    },
                ],
            },
            {
                "s": "ETHUSDT",
                "c": "100.0",
                "q": "5000.0",
                "_market_events": [
                    {
                        "event_type": "market_tick",
                        "symbol": "ETHUSDT",
                        "exchange": "binance",
                        "price": 100.0,
                        "volume": 50.0,
                        "quote_volume": 5000.0,
                        "event_time": "1714467600000",
                    },
                    {
                        "event_type": "mark_price",
                        "symbol": "ETHUSDT",
                        "exchange": "binance",
                        "price": 106.0,
                        "event_time": "1714468200000",
                    },
                ],
            },
        ]
    )
    current_times = iter(
        [
            datetime(2024, 4, 30, 9, 5, 0, tzinfo=timezone.utc),
            datetime(2024, 4, 30, 9, 10, 0, tzinfo=timezone.utc),
        ]
    )
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        current_time_supplier=lambda: next(current_times),
    )

    assembler.build(symbol="ETHUSDT", trace_id="trace-stale-effective-price-first")
    second = assembler.build(symbol="ETHUSDT", trace_id="trace-stale-effective-price-second")

    assert second["feature_snapshot"]["latest_price"] == 106.0
    assert second["feature_snapshot"]["stale_trade_price"] == 100.0
    assert second["feature_snapshot"]["trade_tick_status"] == "stale"
    assert second["feature_snapshot"]["effective_price"] == 106.0
    assert second["feature_snapshot"]["effective_price_source"] == "mark_price"
    assert second["feature_snapshot"]["price_change_pct"] == pytest.approx(1.9231, abs=1e-4)


def test_runtime_input_assembler_adds_compact_wyckoff_15m_bars_from_rest_candles():
    current_time = datetime(2024, 4, 30, 9, 5, 0, tzinfo=timezone.utc)
    candles = [
        {
            "event_type": "market_kline",
            "interval": "15m",
            "open_time": 1714456800000 + index * 900000,
            "open": 100.0 + index,
            "high": 101.0 + index,
            "low": 99.0 + index,
            "close": 100.5 + index,
            "quote_volume": 1000.0 + index * 25,
        }
        for index in range(10)
    ]

    class StubRestClient:
        def fetch_candles(self, symbol, interval="1m", limit=120):
            return candles if interval == "15m" else []

    assembler = RuntimeInputAssembler(
        exchange="okx",
        market_payload_supplier=lambda symbol: {
            "data": [{"instId": "ETH-USDT-SWAP", "last": "108.0", "vol24h": "50", "ts": "1714467900000"}],
        },
        rest_market_client=StubRestClient(),
        current_time_supplier=lambda: current_time,
    )

    result = assembler.build(symbol="ETHUSDT", trace_id="trace-wyckoff-15m-bars")

    bars = result["feature_snapshot"]["wyckoff_15m_bars"]
    assert bars["provided_15m_bars"] == 8
    assert len(bars["bars"]) == 8
    assert bars["bars"][0]["open_time"] == candles[-8]["open_time"]
    assert bars["bars"][-1]["close"] == candles[-1]["close"]
    assert bars["bars"][-1]["volume_ratio"] > 0


def test_runtime_input_assembler_tracks_open_interest_change_from_supplemental_events():
    market_payloads = iter(
        [
            {
                "s": "BTCUSDT",
                "c": "100.0",
                "q": "2000.0",
                "_market_events": [
                    {"event_type": "open_interest", "symbol": "BTCUSDT", "exchange": "okx", "open_interest": 1000.0},
                ],
            },
            {
                "s": "BTCUSDT",
                "c": "101.0",
                "q": "2200.0",
                "_market_events": [
                    {"event_type": "open_interest", "symbol": "BTCUSDT", "exchange": "okx", "open_interest": 1100.0},
                ],
            },
        ]
    )
    current_times = iter(
        [
            datetime(2026, 4, 24, 7, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 24, 7, 5, tzinfo=timezone.utc),
        ]
    )
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        current_time_supplier=lambda: next(current_times),
    )

    assembler.build(symbol="BTCUSDT")
    second = assembler.build(symbol="BTCUSDT")

    assert second["market_context_history"][0]["open_interest"] == 1000.0
    assert second["market_context_history"][1]["open_interest"] == 1100.0
    assert second["feature_snapshot"]["oi_change_pct"] == 10.0


def test_runtime_input_assembler_adds_market_history_trigger_metrics_to_snapshot():
    market_payloads = iter(
        [
            {
                "s": "BTCUSDT",
                "c": "100.0",
                "q": "1000.0",
                "_market_events": [
                    {"event_type": "mark_price", "symbol": "BTCUSDT", "exchange": "binance", "price": 100.0},
                    {"event_type": "funding_rate", "symbol": "BTCUSDT", "exchange": "binance", "funding_rate": 0.0002},
                ],
            },
            {"s": "BTCUSDT", "c": "101.0", "q": "1200.0"},
            {
                "s": "BTCUSDT",
                "c": "104.0",
                "q": "1800.0",
                "_market_events": [
                    {"event_type": "mark_price", "symbol": "BTCUSDT", "exchange": "binance", "price": 105.04},
                    {"event_type": "funding_rate", "symbol": "BTCUSDT", "exchange": "binance", "funding_rate": 0.0011},
                ],
            },
        ]
    )
    current_times = iter(
        [
            datetime(2026, 4, 24, 7, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 24, 7, 2, tzinfo=timezone.utc),
            datetime(2026, 4, 24, 7, 5, tzinfo=timezone.utc),
        ]
    )
    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        current_time_supplier=lambda: next(current_times),
    )

    assembler.build(symbol="BTCUSDT")
    assembler.build(symbol="BTCUSDT")
    second = assembler.build(symbol="BTCUSDT")

    assert second["feature_snapshot"]["market_window_price_change_pct"] == 4.0
    assert second["feature_snapshot"]["market_price_acceleration_pct"] == 1.9703
    assert second["feature_snapshot"]["market_quote_volume_change_pct"] == 80.0
    assert second["feature_snapshot"]["mark_price_deviation_pct"] == 1.0
    assert second["feature_snapshot"]["funding_rate"] == 0.0011


def test_runtime_input_assembler_enhances_okx_market_data_with_rest_and_klines():
    published = []

    class StubPublisher:
        def publish(self, event, *, trace_id="", source_metadata=None):
            published.append({"event": event, "trace_id": trace_id, "source_metadata": source_metadata})
            return f"stream-{len(published)}"

    class StubRestClient:
        def fetch_mark_price(self, symbol):
            return {"event_type": "mark_price", "symbol": symbol, "exchange": "okx", "price": 101.0, "event_time": "1001"}

        def fetch_funding_rate(self, symbol):
            return {"event_type": "funding_rate", "symbol": symbol, "exchange": "okx", "funding_rate": 0.0009, "event_time": "1002"}

        def fetch_open_interest(self, symbol):
            return {"event_type": "open_interest", "symbol": symbol, "exchange": "okx", "open_interest": 1200.0, "event_time": "1003"}

        def fetch_candles(self, symbol, *, interval="1m", limit=120):
            return [
                {
                    "event_type": "market_kline",
                    "symbol": symbol,
                    "exchange": "okx",
                    "interval": interval,
                    "open": 100.0 + index,
                    "high": 101.0 + index,
                    "low": 99.0 + index,
                    "close": 100.0 + index,
                    "volume": 10.0 + index,
                    "quote_volume": 1000.0 + index * 10,
                    "event_time": str(1000 + index),
                }
                for index in range(80)
            ]

    assembler = RuntimeInputAssembler(
        exchange="okx",
        market_payload_supplier=lambda symbol: {
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "last": "100.0",
                    "vol24h": "50.0",
                    "volCcyQuote24h": "5000.0",
                    "ts": "1000",
                }
            ]
        },
        stream_publisher=StubPublisher(),
        rest_market_client=StubRestClient(),
        current_time_supplier=lambda: datetime(2026, 4, 24, 7, 0, tzinfo=timezone.utc),
    )

    result = assembler.build(
        symbol="BTCUSDT",
        trace_id="trace-enhanced",
        runtime_config={
            "runtimeFlagsJson": '{"marketDataEnhancement":{"enabled":true,"klineIntervals":["1m"],"klineLimit":80}}'
        },
    )

    event_types = [item["event_type"] for item in result["event_bundle"]]
    assert "market_metric" in event_types
    assert "market_kline" in event_types
    assert result["feature_snapshot"]["funding_rate"] == 0.0009
    assert result["feature_snapshot"]["open_interest"] == 1200.0
    assert result["feature_snapshot"]["mark_price"] == 101.0
    assert result["feature_snapshot"]["kline_price_change_pct"]["15m"] == 9.1463
    assert result["feature_snapshot"]["kline_quote_volume_ratio"]["15m"] == 1.0955
    assert result["feature_snapshot"]["kline_period_summaries"][0]["source"] == "kline_ohlcv"
    assert result["feature_snapshot"]["kline_period_summaries"][0]["quote_volume_sum"] > 0
    assert isinstance(result["feature_snapshot"]["kline_volume_price_signals"], list)
    assert result["market_context_history"][-1]["kline_context"]["price_change_pct"]["15m"] == 9.1463
    published_metric = next(item["event"] for item in published if item["event"]["event_type"] == "market_metric")
    assert published_metric["observed_at"] == "2026-04-24T07:00:00+00:00"


def test_runtime_input_assembler_prunes_market_window_to_last_fifteen_minutes():
    market_payloads = iter(
        [
            {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
            {"s": "BTCUSDT", "c": "105.0", "q": "2.2"},
            {"s": "BTCUSDT", "c": "110.0", "q": "2.4"},
        ]
    )
    current_times = iter(
        [
            datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 17, 8, 5, tzinfo=timezone.utc),
            datetime(2026, 4, 17, 8, 20, tzinfo=timezone.utc),
        ]
    )

    assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: next(market_payloads),
        active_signal_store=InMemoryActiveSignalStore(),
        current_time_supplier=lambda: next(current_times),
    )

    assembler.build(symbol="BTCUSDT")
    assembler.build(symbol="BTCUSDT")
    third = assembler.build(symbol="BTCUSDT")

    assert third["signal_window_states"] == [
        {
            "symbol": "BTCUSDT",
            "window_key": "market:BTCUSDT:15m",
            "source_type": "market",
            "signal_type": "price_break",
            "direction": "bullish",
            "strength_score": 4.7619,
            "decay_score": 4.7619,
            "opened_at": "2026-04-17T08:20:00+00:00",
            "expires_at": "2026-04-17T08:25:00+00:00",
            "last_event_at": "2026-04-17T08:20:00+00:00",
            "last_confirmed_at": "2026-04-17T08:20:00+00:00",
            "dedupe_key": "market:BTCUSDT:bullish",
            "combine_until_at": "2026-04-17T08:25:00+00:00",
            "active": True,
            "state": {"count": 2, "last_price": 110.0, "price_change_pct": 4.7619},
        }
    ]


def test_market_data_enhancement_config_accepts_model_and_dict_alike():
    """Operator config must win on every call path.

    runtime_runner passes RuntimeConfig.model_dump(); the bootstrap paths pass
    the RuntimeConfig object. The object form used to fall through to pure
    defaults, so klineIntervals / klineLimit were silently ignored on one of the
    two paths with nothing logged.
    """
    from trade_runtime.runtime_inputs import (
        _enhancement_exchanges,
        _market_data_enhancement_config,
    )

    flags = (
        '{"marketDataEnhancement":{"klineIntervals":["1m","15m"],'
        '"klineLimit":500,"exchanges":["okx","binance"]}}'
    )
    config = RuntimeConfig(runtimeFlagsJson=flags)

    from_dict = _market_data_enhancement_config(config.model_dump())
    from_model = _market_data_enhancement_config(config)

    for resolved in (from_dict, from_model):
        assert resolved["klineIntervals"] == ["1m", "15m"]
        assert resolved["klineLimit"] == 500
        assert _enhancement_exchanges(resolved) == {"okx", "binance"}


def test_market_data_enhancement_defaults_to_okx_only():
    """Binance enhancement is opt-in: it changes which events reach the gate."""
    from trade_runtime.runtime_inputs import (
        _enhancement_exchanges,
        _market_data_enhancement_config,
    )

    resolved = _market_data_enhancement_config({})
    assert _enhancement_exchanges(resolved) == {"okx"}
