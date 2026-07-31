import pytest

from trade_runtime.app import build_runtime_app
from trade_runtime.config import RuntimeConfig
from trade_runtime.replay_runner import TradeReplayRunner
from trade_runtime.runtime_inputs import RuntimeInputAssembler
from trade_runtime.runtime_runner import TradeRuntimeRunner


@pytest.mark.parametrize(
    ("default_mode", "live_enabled", "expected_mode", "expected_downgraded"),
    [
        ("paper", False, "paper", False),
        ("shadow", False, "shadow", False),
        ("live", False, "shadow", True),
    ],
)
def test_runtime_mode_conformance_covers_paper_shadow_and_live_downgrade(
    default_mode,
    live_enabled,
    expected_mode,
    expected_downgraded,
):
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode=default_mode, liveEnabled=live_enabled)

    class StubGraph:
        def __init__(self):
            self.invoked_state = None

        def invoke(self, state):
            self.invoked_state = state
            return state

    graph = StubGraph()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
    )

    result = runner.run_once(
        trace_id=f"trace-mode-{default_mode}",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "price": 65000.0}],
        feature_snapshot={"price_change_pct": 1.4},
    )

    assert result["mode"] == expected_mode
    assert result["effective_mode"] == expected_mode
    assert result["mode_downgraded"] is expected_downgraded


def test_binance_conformance_uses_futures_execution_and_futures_market_defaults_together(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = type("SymbolScope", (), {"symbol": "BTCUSDT", "exchange_code": "binance"})()
        exchange_account_binding = None
        exchange_account = type(
            "ExchangeAccount",
            (),
            {
                "exchange_code": "binance",
                "api_key_ciphertext": "ak-runtime",
                "api_secret_ciphertext": "sk-runtime",
                "testnet": True,
            },
        )()
        ai_model_config = None
        news_api_config = None
        onchain_api_config = None
        social_api_config = None
        market_api_config = type(
            "MarketApiConfig",
            (),
            {
                "id": 77,
                "transport_type": "WEBSOCKET",
                "vendor_code": "BINANCE",
                "api_name": "BINANCE_FUTURES_TICKER_WS",
                "ws_base_url": "wss://fstream.binance.com",
                "ws_path": "/stream",
                "ws_stream_name_template": "{symbol_lower}@ticker",
                "ws_combined_enabled": True,
                "ws_symbol_lowercase": True,
                "ws_ping_interval_seconds": 20,
                "ws_pong_timeout_seconds": 60,
                "ws_connection_ttl_hours": 24,
                "ws_max_streams_per_connection": 1024,
                "ws_control_messages_per_second": 5,
            },
        )()

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def get_bootstrap(self, symbol=None, exchange=None):
            return StubBootstrap()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRuntimeRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router

    class StubBinanceClient:
        def __init__(self, api_key, api_secret, testnet=False):
            captured["binance_client"] = {
                "api_key": api_key,
                "api_secret": api_secret,
                "testnet": testnet,
            }

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0", "_market_source_status": "ready"}

    class StubBinanceWsMarketFeed:
        def __init__(self, *, rest_payload_supplier, market_api_config=None, supervisor=None, client_factory=None):
            captured["market_api_config"] = market_api_config

        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0", "_market_source_status": "ready"}

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRuntimeRunner)
    monkeypatch.setattr("trade_runtime.app.BinanceRestExecutionClient", StubBinanceClient)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.BinanceWsMarketFeed", StubBinanceWsMarketFeed)

    app = build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
        }
    )

    assert captured["binance_client"]["testnet"] is True
    assert app.runner.execution_router.binance_client is not None
    assert captured["market_api_config"].ws_base_url == "wss://fstream.binance.com"
    assert captured["market_api_config"].ws_path == "/stream"


def test_event_bus_conformance_uses_streams_as_primary_and_http_as_compatibility_only():
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

    primary_assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "ETF inflow", "score": 0.7}],
        stream_publisher=StubPublisher(),
        stream_consumer=StubStreamConsumer(),
        event_client=StubEventClient(),
    )
    primary_assembler.build(symbol="BTCUSDT", trace_id="trace-stream-primary")

    fallback_assembler = RuntimeInputAssembler(
        exchange="binance",
        market_payload_supplier=lambda symbol: {"s": "BTCUSDT", "c": "100.0", "q": "2.0"},
        news_items_supplier=lambda symbol: [{"symbol": symbol, "headline": "ETF inflow", "score": 0.7}],
        event_client=StubEventClient(),
    )
    fallback_assembler.build(symbol="BTCUSDT", trace_id="trace-http-compat")

    assert [item["event"]["event_type"] for item in published] == ["market_tick", "news"]
    assert drained == [{"max_messages": 2, "block_ms": 0}]
    assert [item["trace_id"] for item in posted] == ["trace-http-compat", "trace-http-compat"]
    assert [item["event"]["event_type"] for item in posted] == ["market_tick", "news"]


def test_replay_conformance_preserves_source_trace_and_shadow_override():
    captured = {}

    class FakeReplayClient:
        def get_trace_source(self, trace_id):
            return {"traceId": trace_id, "symbol": "BTCUSDT", "exchangeCode": "binance", "eventBundle": []}

        def ensure_session(self, *, source_trace_id, session_id=None, replay_trace_id=None):
            return {"id": session_id or 9, "replay_trace_id": f"replay-{session_id or 9}-{source_trace_id}"}

        def list_source_events(self, trace_id):
            return [
                {"event_time": 2, "payload": {"event_type": "onchain", "flow": "exchange_outflow"}, "symbol": "BTCUSDT", "exchange_code": "binance"},
                {"event_time": 1, "payload": {"event_type": "news", "score": 0.8}, "symbol": "BTCUSDT", "exchange_code": "binance"},
            ]

        def post_replay_event(self, payload):
            return None

        def update_replay_session(self, payload):
            return None

    class FakeRuntimeRunner:
        def run_once(self, **kwargs):
            captured["runner_call"] = kwargs
            return {"execution_result": {"status": "pending", "order_status": "PENDING"}}

    runner = TradeReplayRunner(replay_client=FakeReplayClient(), runtime_runner=FakeRuntimeRunner())

    result = runner.run_trace("source-trace-9", session_id=9)

    assert result["source_trace_id"] == "source-trace-9"
    assert result["replay_trace_id"] == "replay-9-source-trace-9"
    assert captured["runner_call"]["mode_override"] == "shadow"
    assert [item["event_type"] for item in captured["runner_call"]["event_bundle"]] == ["news", "onchain"]
