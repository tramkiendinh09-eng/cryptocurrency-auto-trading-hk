import logging
import threading

from trade_runtime.app import (
    RuntimeAppSettings,
    RuntimeContext,
    TradeRuntimeApp,
    _build_strategy_context,
    _build_memory_current_price_supplier,
    _build_runtime_input_supplier,
    _build_long_term_memory_store,
    _runtime_account_context_payload,
    build_execution_router,
    build_replay_runner,
    build_runtime_app,
    main,
)


def test_runtime_app_settings_reads_only_process_env_overrides():
    settings = RuntimeAppSettings.from_env(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:9000/",
            "TRADE_RUNTIME_BEARER_TOKEN": "secret-token",
            "TRADE_RUNTIME_SYMBOL": "ETHUSDT",
            "TRADE_RUNTIME_EXCHANGE": "okx",
            "TRADE_RUNTIME_DEFAULT_SYMBOL": "ETHUSDT",
            "TRADE_RUNTIME_POLL_INTERVAL_SECONDS": "9",
            "TRADE_RUNTIME_MODEL_CALL_TIMEOUT_SECONDS": "45",
            "TRADE_RUNTIME_RUN_MODE": "forever",
            "TRADE_RUNTIME_REPLAY_TRACE_ID": "trace-source-9",
        }
    )

    assert settings.base_url == "http://localhost:9000"
    assert settings.bearer_token == "secret-token"
    assert settings.default_symbol == "ETHUSDT"
    assert settings.symbol is None
    assert settings.exchange is None
    assert settings.news_url == ""
    assert settings.onchain_url == ""
    assert settings.social_url == ""
    assert settings.poll_interval_seconds == 9
    assert settings.model_call_timeout_seconds == 45
    assert settings.run_mode == "forever"
    assert settings.replay_trace_id == "trace-source-9"


def test_runtime_app_settings_defaults_model_call_timeout_to_45_seconds():
    settings = RuntimeAppSettings.from_env({})

    assert settings.model_call_timeout_seconds == 45




def test_runtime_app_settings_reads_mcp_memory_overrides():
    settings = RuntimeAppSettings.from_env(
        {
            "TRADE_RUNTIME_MEMORY_STORE": "hybrid",
            "TRADE_RUNTIME_MEMOS_MCP_URL": "http://38.12.21.62:8002/mcp",
            "TRADE_RUNTIME_MEMOS_USER_ID": "trade-runtime",
            "TRADE_RUNTIME_MEMOS_CHANNEL": "production",
        }
    )

    assert settings.memory_store == "hybrid"
    assert settings.memos_mcp_url == "http://38.12.21.62:8002/mcp"
    assert settings.memos_user_id == "trade-runtime"
    assert settings.memos_channel == "production"
    assert settings.memos_timeout_seconds == 20


def test_runtime_app_settings_reads_official_stdio_mcp_overrides():
    settings = RuntimeAppSettings.from_env(
        {
            "TRADE_RUNTIME_MEMORY_STORE": "hybrid",
            "TRADE_RUNTIME_MEMOS_MCP_TRANSPORT": "stdio",
            "TRADE_RUNTIME_MEMOS_MCP_COMMAND": "npx",
            "TRADE_RUNTIME_MEMOS_MCP_ARGS_JSON": '["-y", "@memtensor/memos-api-mcp@latest"]',
            "TRADE_RUNTIME_MEMOS_API_KEY": "official-key",
            "TRADE_RUNTIME_MEMOS_USER_ID": "trade-runtime",
            "TRADE_RUNTIME_MEMOS_CHANNEL": "MODELSCOPE",
        }
    )

    assert settings.memory_store == "hybrid"
    assert settings.memos_mcp_transport == "stdio"
    assert settings.memos_mcp_command == "npx"
    assert settings.memos_mcp_args_json == '["-y", "@memtensor/memos-api-mcp@latest"]'
    assert settings.memos_api_key == "official-key"
    assert settings.memos_channel == "MODELSCOPE"


def test_build_long_term_memory_store_uses_hybrid_local_primary_and_mcp_secondary(monkeypatch):
    captured = {}

    class StubHttpStore:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["http"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

    class StubMcpStore:
        def __init__(self, **kwargs):
            captured["mcp"] = kwargs

    class StubHybridStore:
        def __init__(self, *, primary, secondary):
            captured["hybrid"] = {"primary": primary, "secondary": secondary}

    monkeypatch.setattr("trade_runtime.app.HttpLongTermMemoryStore", StubHttpStore)
    monkeypatch.setattr("trade_runtime.app.McpLongTermMemoryStore", StubMcpStore)
    monkeypatch.setattr("trade_runtime.app.HybridLongTermMemoryStore", StubHybridStore)
    settings = RuntimeAppSettings.from_env(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_BEARER_TOKEN": "runtime-token",
            "TRADE_RUNTIME_MEMORY_STORE": "hybrid",
            "TRADE_RUNTIME_MEMOS_MCP_URL": "http://38.12.21.62:8002/mcp",
            "TRADE_RUNTIME_MEMOS_USER_ID": "trade-runtime",
            "TRADE_RUNTIME_MEMOS_CHANNEL": "production",
            "TRADE_RUNTIME_MEMOS_WRITE_ENABLED": "true",
            "TRADE_RUNTIME_MEMOS_SEARCH_ENABLED": "true",
        }
    )

    store = _build_long_term_memory_store(settings)

    assert store is captured["hybrid"] or store.__class__.__name__ == "StubHybridStore"
    assert captured["http"] == {"base_url": "http://localhost:8088", "bearer_token": "runtime-token", "timeout": 5}
    assert captured["mcp"]["mcp_url"] == "http://38.12.21.62:8002/mcp"
    assert captured["mcp"]["timeout"] == 20
    assert captured["mcp"]["user_id"] == "trade-runtime"
    assert captured["mcp"]["channel"] == "production"
    assert captured["mcp"]["transport"] == "http"
    assert captured["mcp"]["write_enabled"] is True
    assert captured["mcp"]["search_enabled"] is True


def test_build_long_term_memory_store_uses_official_stdio_mcp_when_no_url(monkeypatch):
    captured = {}

    class StubHttpStore:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["http"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

    class StubMcpStore:
        def __init__(self, **kwargs):
            captured["mcp"] = kwargs

    class StubHybridStore:
        def __init__(self, *, primary, secondary):
            captured["hybrid"] = {"primary": primary, "secondary": secondary}

    monkeypatch.setattr("trade_runtime.app.HttpLongTermMemoryStore", StubHttpStore)
    monkeypatch.setattr("trade_runtime.app.McpLongTermMemoryStore", StubMcpStore)
    monkeypatch.setattr("trade_runtime.app.HybridLongTermMemoryStore", StubHybridStore)
    settings = RuntimeAppSettings.from_env(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_BEARER_TOKEN": "runtime-token",
            "TRADE_RUNTIME_MEMORY_STORE": "hybrid",
            "TRADE_RUNTIME_MEMOS_MCP_TRANSPORT": "stdio",
            "TRADE_RUNTIME_MEMOS_MCP_COMMAND": "npx",
            "TRADE_RUNTIME_MEMOS_MCP_ARGS_JSON": '["-y", "@memtensor/memos-api-mcp@latest"]',
            "TRADE_RUNTIME_MEMOS_API_KEY": "official-key",
            "TRADE_RUNTIME_MEMOS_USER_ID": "trade-runtime",
            "TRADE_RUNTIME_MEMOS_CHANNEL": "MODELSCOPE",
        }
    )

    store = _build_long_term_memory_store(settings)

    assert store is captured["hybrid"] or store.__class__.__name__ == "StubHybridStore"
    assert captured["mcp"]["mcp_url"] == ""
    assert captured["mcp"]["transport"] == "stdio"
    assert captured["mcp"]["command"] == "npx"
    assert captured["mcp"]["args"] == ["-y", "@memtensor/memos-api-mcp@latest"]
    assert captured["mcp"]["env"]["MEMOS_API_KEY"] == "official-key"
    assert captured["mcp"]["env"]["MEMOS_CHANNEL"] == "MODELSCOPE"
    assert captured["mcp"]["timeout"] == 20

def test_runtime_account_context_payload_includes_current_time_fields():
    runtime_account_context = type(
        "RuntimeAccountContextStub",
        (),
        {
            "account_equity": 10000.0,
            "current_position_opened_at": "2026-05-07 09:00:00",
            "current_time": "2026-05-07T09:30:00Z",
            "current_position_holding_minutes": 30,
        },
    )()

    payload = _runtime_account_context_payload(runtime_account_context)

    assert payload["current_position_opened_at"] == "2026-05-07 09:00:00"
    assert payload["current_time"] == "2026-05-07T09:30:00Z"
    assert payload["current_position_holding_minutes"] == 30


def test_build_runtime_app_wires_process_clients_from_env_and_runtime_context_from_bootstrap(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = type("Scope", (), {"symbol": "SOLUSDT", "exchange_code": "binance"})()
        exchange_account_binding = None
        exchange_account = None
        news_api_config = type("NewsApiConfig", (), {"api_url": "http://feed.local/news"})()
        onchain_api_config = type("OnchainApiConfig", (), {"api_url": "http://feed.local/onchain"})()
        social_api_config = type("SocialApiConfig", (), {"api_url": "http://feed.local/social"})()
        market_data_config = type("MarketDataConfig", (), {"collect_onchain": "1"})()

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["config_client"] = {
                "base_url": base_url,
                "bearer_token": bearer_token,
                "timeout": timeout,
            }

        def get_bootstrap(self, symbol=None, exchange=None):
            captured["bootstrap_query"] = {"symbol": symbol, "exchange": exchange}
            return StubBootstrap()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["callback_client"] = {
                "base_url": base_url,
                "bearer_token": bearer_token,
                "timeout": timeout,
            }

        def post_worker_heartbeat(self, worker_id):
            captured["heartbeat_worker_id"] = worker_id

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["runner"] = {
                "config_client": config_client,
                "callback_client": callback_client,
                "graph": graph,
                "execution_router": execution_router,
            }

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            captured.setdefault("aux_suppliers", []).append({"url": url, "timeout": timeout})

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)

    app = build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_BEARER_TOKEN": "runtime-token",
            "TRADE_RUNTIME_POLL_INTERVAL_SECONDS": "12",
            "TRADE_RUNTIME_AUX_FEED_TIMEOUT_SECONDS": "20",
            "TRADE_RUNTIME_ONCHAIN_FEED_TIMEOUT_SECONDS": "30",
            "TRADE_RUNTIME_SOCIAL_FEED_TIMEOUT_SECONDS": "bad",
        }
    )

    assert app.symbol == "SOLUSDT"
    assert app.exchange == "binance"
    assert app.poll_interval_seconds == 12
    assert app.worker_id.startswith("trade-runtime-")
    assert captured["config_client"]["base_url"] == "http://localhost:8088"
    assert captured["callback_client"]["bearer_token"] == "runtime-token"
    assert captured["runner"]["graph"] is None
    assert captured["runner"]["execution_router"] is not None
    assert [item["url"] for item in captured["aux_suppliers"]] == [
        "http://feed.local/news",
        "http://feed.local/onchain",
        "http://feed.local/social",
    ]
    assert [item["timeout"] for item in captured["aux_suppliers"]] == [20, 30, 20]
    assert captured["bootstrap_query"] == {"symbol": None, "exchange": None}


def test_build_runtime_app_wires_long_term_memory_consolidation_job(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = type("Scope", (), {"symbol": "BTCUSDT", "exchange_code": "okx"})()
        exchange_account_binding = None
        exchange_account = None
        ai_model_config = type("AiModelConfig", (), {"id": 88})()
        news_api_config = None
        onchain_api_config = None
        social_api_config = None
        market_data_config = None

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

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            pass

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "123.4", "q": "1.0"}

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            self.exchange = exchange

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            captured["price_request"] = {"symbol": symbol, "trace_id": trace_id, "strategy_context": strategy_context}
            return {"event_bundle": [{"event_type": "market_tick", "symbol": symbol, "price": 123.4}]}

    class StubDecisionModelClient:
        def __init__(self, base_url, bearer_token, timeout=10):
            captured["model_client"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

    class StubMemoryStore:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["memory_store"] = {"base_url": base_url, "bearer_token": bearer_token}

    class StubDecisionHistoryClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["history_client"] = {"base_url": base_url, "bearer_token": bearer_token}

    class StubMemoryJob:
        def __init__(self, **kwargs):
            captured["memory_job"] = kwargs

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.DecisionModelClient", StubDecisionModelClient)
    monkeypatch.setattr("trade_runtime.app.HttpLongTermMemoryStore", StubMemoryStore)
    monkeypatch.setattr("trade_runtime.app.HttpDecisionHistoryClient", StubDecisionHistoryClient)
    monkeypatch.setattr("trade_runtime.app.LongTermMemoryConsolidationJob", StubMemoryJob)
    monkeypatch.setattr("trade_runtime.app.OkxPublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    app = build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_BEARER_TOKEN": "runtime-token",
            "TRADE_RUNTIME_MEMORY_WINDOW_SECONDS": "3600",
            "TRADE_RUNTIME_MODEL_CALL_TIMEOUT_SECONDS": "46",
        }
    )

    assert app.memory_consolidation_job is not None
    assert captured["model_client"] == {
        "base_url": "http://localhost:8088",
        "bearer_token": "runtime-token",
        "timeout": 46,
    }
    assert captured["memory_store"] == {"base_url": "http://localhost:8088", "bearer_token": "runtime-token"}
    assert captured["history_client"] == {"base_url": "http://localhost:8088", "bearer_token": "runtime-token"}
    assert captured["memory_job"]["model_id"] == 88
    assert captured["memory_job"]["model_id_resolver"]({"symbol": "BTCUSDT", "exchangeCode": "okx"}) == 88
    assert captured["memory_job"]["window_seconds"] == 3600
    assert captured["memory_job"]["current_price_supplier"]("BTCUSDT") == 123.4
    assert captured["price_request"]["symbol"] == "BTCUSDT"


def test_build_replay_runner_wires_memory_and_lifecycle_clients(monkeypatch):
    captured = {}

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["config_client"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

        def get_config(self):
            return type("Config", (), {"default_mode": "paper", "live_enabled": False, "model_dump": lambda self: {}})()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["callback_client"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

    class StubRuntimeRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.config_client = config_client
            self.callback_client = callback_client
            self.graph = graph
            self.execution_router = execution_router
            self.memory_store = None
            self.decision_model_client = None
            self.lifecycle_manager = None

    class StubDecisionModelClient:
        def __init__(self, base_url, bearer_token, timeout=10):
            captured["decision_model_client"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

    class StubMemoryStore:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["memory_store"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

    class StubLifecycleClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            captured["lifecycle_client"] = {"base_url": base_url, "bearer_token": bearer_token, "timeout": timeout}

    class StubLifecycleManager:
        def __init__(self, *, lifecycle_client, memory_store, model_client, model_id=None, now_supplier=None):
            captured["lifecycle_manager"] = {
                "lifecycle_client": lifecycle_client,
                "memory_store": memory_store,
                "model_client": model_client,
                "model_id": model_id,
            }
            self.lifecycle_client = lifecycle_client
            self.memory_store = memory_store
            self.model_client = model_client
            self.model_id = model_id

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeReplayClient", lambda base_url, bearer_token: object())
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRuntimeRunner)
    monkeypatch.setattr("trade_runtime.app.DecisionModelClient", StubDecisionModelClient)
    monkeypatch.setattr("trade_runtime.app.HttpLongTermMemoryStore", StubMemoryStore)
    monkeypatch.setattr("trade_runtime.app.TradeLifecycleClient", StubLifecycleClient)
    monkeypatch.setattr("trade_runtime.app.TradeLifecycleManager", StubLifecycleManager)

    replay_runner = build_replay_runner(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_BEARER_TOKEN": "runtime-token",
            "TRADE_RUNTIME_MODEL_CALL_TIMEOUT_SECONDS": "46",
        }
    )

    assert captured["decision_model_client"] == {
        "base_url": "http://localhost:8088",
        "bearer_token": "runtime-token",
        "timeout": 46,
    }
    assert captured["memory_store"] == {
        "base_url": "http://localhost:8088",
        "bearer_token": "runtime-token",
        "timeout": 5,
    }
    assert captured["lifecycle_client"] == {
        "base_url": "http://localhost:8088",
        "bearer_token": "runtime-token",
        "timeout": 5,
    }
    assert captured["lifecycle_manager"]["model_id"] is None
    assert replay_runner.runtime_runner.decision_model_client is not None
    assert replay_runner.runtime_runner.lifecycle_manager is not None
    assert replay_runner.runtime_runner.lifecycle_manager.memory_store is replay_runner.runtime_runner.memory_store


def test_memory_current_price_supplier_uses_matching_runtime_context_for_symbol():
    captured = []

    def runtime_input_supplier(**kwargs):
        captured.append(kwargs)
        return {"event_bundle": [{"event_type": "market_tick", "price": 456.7}]}

    supplier = _build_memory_current_price_supplier(
        runtime_input_supplier=runtime_input_supplier,
        runtime_context=[
            RuntimeContext(symbol="BTCUSDT", exchange="okx", feed_urls={"news_url": "btc-news"}),
            RuntimeContext(symbol="ETHUSDT", exchange="binance", feed_urls={"news_url": "eth-news"}),
        ],
    )

    assert supplier("ETHUSDT") == 456.7
    assert captured[0]["exchange"] == "binance"
    assert captured[0]["feed_urls"] == {"news_url": "eth-news"}


def test_build_runtime_app_prefers_bootstrap_feed_configs_over_env(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = None
        exchange_account_binding = None
        exchange_account = None
        ai_model_config = None
        news_api_config = type(
            "NewsApiConfig",
            (),
            {"api_url": "https://bootstrap.internal/news"},
        )()
        onchain_api_config = type(
            "OnchainApiConfig",
            (),
            {"api_url": "https://bootstrap.internal/onchain"},
        )()
        social_api_config = type(
            "SocialApiConfig",
            (),
            {"api_url": "https://bootstrap.internal/social"},
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

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["execution_router"] = execution_router

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            captured.setdefault("aux_suppliers", []).append({"url": url, "timeout": timeout})

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_SYMBOL": "BTCUSDT",
            "TRADE_RUNTIME_EXCHANGE": "binance",
            "TRADE_RUNTIME_NEWS_URL": "http://env.local/news",
            "TRADE_RUNTIME_ONCHAIN_URL": "http://env.local/onchain",
            "TRADE_RUNTIME_SOCIAL_URL": "http://env.local/social",
        }
    )

    assert [item["url"] for item in captured["aux_suppliers"]] == [
        "https://bootstrap.internal/news",
        "https://bootstrap.internal/onchain",
        "https://bootstrap.internal/social",
    ]
    assert [item["timeout"] for item in captured["aux_suppliers"]] == [15, 15, 15]


def test_build_runtime_app_does_not_fallback_to_env_feed_configs_when_bootstrap_missing(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = None
        exchange_account_binding = None
        exchange_account = None
        ai_model_config = None
        news_api_config = None
        onchain_api_config = None
        social_api_config = None
        market_data_config = None

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

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["execution_router"] = execution_router

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            captured.setdefault("aux_suppliers", []).append({"url": url, "timeout": timeout})

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_SYMBOL": "BTCUSDT",
            "TRADE_RUNTIME_EXCHANGE": "binance",
            "TRADE_RUNTIME_NEWS_URL": "http://env.local/news",
            "TRADE_RUNTIME_ONCHAIN_URL": "http://env.local/onchain",
            "TRADE_RUNTIME_SOCIAL_URL": "http://env.local/social",
        }
    )

    assert [item["url"] for item in captured.get("aux_suppliers", [])] == []


def test_build_strategy_context_carries_prompt_bindings_and_agent_profiles():
    bootstrap = type(
        "StubBootstrap",
        (),
        {
            "strategy": type("Strategy", (), {"id": 7, "strategy_key": "event-btc", "strategy_name": "BTC Event", "runtime_mode": "SHADOW"})(),
            "strategy_version": type("Version", (), {"strategy_id": 7, "version_no": 3, "config_json": "{\"riskBudget\":0.02}"})(),
            "ai_model_config": None,
            "news_api_config": None,
            "onchain_api_config": None,
            "social_api_config": None,
            "market_api_config": None,
            "market_data_config": None,
            "prompt_bindings": [
                type(
                    "Binding",
                    (),
                    {
                        "binding_scope": "SUPERVISOR",
                        "template_code": "trade.supervisor.v1",
                        "fallback_template_code": "trade.supervisor.fallback",
                        "model_id": 31,
                        "output_schema_code": "supervisor_decision_v1",
                        "mode_scope_json": "[\"shadow\"]",
                        "event_strength_scope_json": "[\"strong\",\"normal\"]",
                    },
                )()
            ],
            "agent_profiles": [
                type(
                    "Profile",
                    (),
                    {
                        "agent_code": "supervisor_agent",
                        "agent_type": "LLM",
                        "llm_enabled": True,
                        "structured_schema_code": "supervisor_decision_v1",
                    },
                )()
            ],
        },
    )()

    strategy_context = _build_strategy_context(bootstrap)

    assert strategy_context["prompt_bindings"][0]["template_code"] == "trade.supervisor.v1"
    assert strategy_context["prompt_bindings"][0]["binding_scope"] == "SUPERVISOR"
    assert strategy_context["agent_profiles"][0]["agent_code"] == "supervisor_agent"
    assert strategy_context["agent_profiles"][0]["structured_schema_code"] == "supervisor_decision_v1"


def test_build_strategy_context_carries_deliberation_policy():
    bootstrap = type(
        "StubBootstrap",
        (),
        {
            "strategy": type("Strategy", (), {"id": 7, "strategy_key": "event-btc", "strategy_name": "BTC Event", "runtime_mode": "SHADOW"})(),
            "strategy_version": type("Version", (), {"strategy_id": 7, "version_no": 3, "config_json": "{\"riskBudget\":0.02}"})(),
            "ai_model_config": None,
            "news_api_config": None,
            "onchain_api_config": None,
            "social_api_config": None,
            "market_api_config": None,
            "market_data_config": None,
            "prompt_bindings": [],
            "agent_profiles": [],
            "deliberation_policy": {
                "enabled": True,
                "maxRounds": 1,
                "failOpen": True,
            },
        },
    )()

    strategy_context = _build_strategy_context(bootstrap)

    assert strategy_context["deliberation_policy"] == {
        "enabled": True,
        "maxRounds": 1,
        "failOpen": True,
    }


def test_build_strategy_context_carries_supervisor_policy():
    bootstrap = type(
        "StubBootstrap",
        (),
        {
            "strategy": type("Strategy", (), {"id": 7, "strategy_key": "event-btc", "strategy_name": "BTC Event", "runtime_mode": "SHADOW"})(),
            "strategy_version": type("Version", (), {"strategy_id": 7, "version_no": 3, "config_json": "{\"supervisorPolicy\":{\"enabledWhen\":\"LLM_ALLOWED\"}}"})(),
            "ai_model_config": None,
            "news_api_config": None,
            "onchain_api_config": None,
            "social_api_config": None,
            "market_api_config": None,
            "market_data_config": None,
            "prompt_bindings": [],
            "agent_profiles": [],
            "deliberation_policy": {},
        },
    )()

    strategy_context = _build_strategy_context(bootstrap)

    assert strategy_context["supervisor_policy"] == {"enabledWhen": "LLM_ALLOWED"}


def test_build_strategy_context_carries_position_guard():
    bootstrap = type(
        "StubBootstrap",
        (),
        {
            "strategy": type("Strategy", (), {"id": 7, "strategy_key": "event-btc", "strategy_name": "BTC Event", "runtime_mode": "SHADOW"})(),
            "strategy_version": type("Version", (), {"strategy_id": 7, "version_no": 3, "config_json": "{\"riskBudget\":0.02}"})(),
            "ai_model_config": None,
            "news_api_config": None,
            "onchain_api_config": None,
            "social_api_config": None,
            "market_api_config": None,
            "market_data_config": None,
            "prompt_bindings": [],
            "agent_profiles": [],
            "deliberation_policy": {},
            "position_guard": type(
                "PositionGuard",
                (),
                {
                    "id": 31,
                    "guard_name": "btc-default-guard",
                    "scope_type": "SYMBOL",
                    "strategy_id": 7,
                    "symbol": "BTCUSDT",
                    "exchange_code": "BINANCE",
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.05,
                    "max_holding_minutes": 180,
                    "enabled": True,
                },
            )(),
        },
    )()

    strategy_context = _build_strategy_context(bootstrap)

    assert strategy_context["position_guard"] == {
        "id": 31,
        "guard_name": "btc-default-guard",
        "scope_type": "SYMBOL",
        "strategy_id": 7,
        "symbol": "BTCUSDT",
        "exchange_code": "BINANCE",
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.05,
        "stop_loss_ratio": 0.02,
        "stop_loss_percent": 2.0,
        "take_profit_ratio": 0.05,
        "take_profit_percent": 5.0,
        "threshold_unit": "ratio",
        "max_holding_minutes": 180,
        "enabled": True,
    }


def test_build_strategy_context_exposes_resolved_source_bindings():
    bootstrap = type(
        "StubBootstrap",
        (),
        {
            "strategy": type("Strategy", (), {"id": 7, "strategy_key": "event-btc", "strategy_name": "BTC Event", "runtime_mode": "SHADOW"})(),
            "strategy_version": type("Version", (), {"strategy_id": 7, "version_no": 3, "config_json": "{\"newsApiConfigId\":903}"})(),
            "ai_model_config": None,
            "market_api_config": None,
            "market_data_config": type("MarketDataConfig", (), {"collect_onchain": "1"})(),
            "news_api_config": type("NewsApi", (), {"id": 903, "data_category": "NEWS", "api_url": "https://feeds.internal/news", "enabled": "1"})(),
            "onchain_api_config": type("OnchainApi", (), {"id": 904, "data_category": "ONCHAIN", "api_url": "https://feeds.internal/onchain", "enabled": "1"})(),
            "social_api_config": type("SocialApi", (), {"id": 905, "data_category": "SOCIAL", "api_url": "https://feeds.internal/social", "enabled": "0"})(),
            "prompt_bindings": [],
            "agent_profiles": [],
            "deliberation_policy": {},
        },
    )()

    strategy_context = _build_strategy_context(bootstrap)

    assert strategy_context["source_bindings"] == {
        "news": {
            "config_id": 903,
            "category": "NEWS",
            "api_url": "https://feeds.internal/news",
            "enabled": True,
            "selection_mode": "strategy",
        },
        "onchain": {
            "config_id": 904,
            "category": "ONCHAIN",
            "api_url": "https://feeds.internal/onchain",
            "enabled": True,
            "selection_mode": "default",
        },
        "social": {
            "config_id": 905,
            "category": "SOCIAL",
            "api_url": "https://feeds.internal/social",
            "enabled": False,
            "selection_mode": "default",
        },
    }


def test_build_strategy_context_carries_runtime_user_id():
    bootstrap = type(
        "StubBootstrap",
        (),
        {
            "user_id": 42,
            "strategy": type("Strategy", (), {"id": 7, "strategy_key": "event-btc", "strategy_name": "BTC Event", "runtime_mode": "SHADOW"})(),
            "strategy_version": type("Version", (), {"strategy_id": 7, "version_no": 3, "config_json": "{\"riskBudget\":0.02}"})(),
            "ai_model_config": None,
            "news_api_config": None,
            "onchain_api_config": None,
            "social_api_config": None,
            "market_api_config": None,
            "market_data_config": None,
            "prompt_bindings": [],
            "agent_profiles": [],
            "deliberation_policy": {},
        },
    )()

    strategy_context = _build_strategy_context(bootstrap)

    assert strategy_context["user_id"] == 42


def test_build_runtime_app_passes_market_source_config_to_binance_ws_feed(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = type("SymbolScope", (), {"symbol": "BTCUSDT", "exchange_code": "binance"})()
        exchange_account_binding = None
        exchange_account = None
        ai_model_config = None
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
        news_api_config = None
        onchain_api_config = None
        social_api_config = None

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

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["execution_router"] = execution_router

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0", "_market_source_status": "ready"}

    class StubBinanceWsMarketFeed:
        def __init__(self, *, rest_payload_supplier, market_api_config=None, supervisor=None, client_factory=None):
            captured["market_api_config"] = market_api_config

        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0", "_market_source_status": "ready"}

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            self.exchange = exchange
            self.market_payload_supplier = market_payload_supplier

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            payload = self.market_payload_supplier(symbol)
            return {
                "event_bundle": [{"event_type": "market_tick", "symbol": payload["s"], "exchange": self.exchange}],
                "feature_snapshot": {"assembler_exchange": self.exchange},
                "market_source_status": payload["_market_source_status"],
            }

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.BinanceWsMarketFeed", StubBinanceWsMarketFeed)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
        }
    )

    assert captured["market_api_config"] is not None
    assert captured["market_api_config"].ws_base_url == "wss://fstream.binance.com"
    assert captured["market_api_config"].ws_path == "/stream"


def test_build_runtime_app_passes_market_source_config_to_okx_ws_feed(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = type("SymbolScope", (), {"symbol": "BTCUSDT", "exchange_code": "okx"})()
        exchange_account_binding = None
        exchange_account = None
        ai_model_config = None
        market_api_config = type(
            "MarketApiConfig",
            (),
            {
                "id": 105,
                "transport_type": "WEBSOCKET",
                "vendor_code": "OKX",
                "api_name": "OKX_SWAP_TICKER_WS",
                "ws_base_url": "wss://ws.okx.com:8443",
                "ws_path": "/ws/v5/public",
                "ws_stream_name_template": '{"args":[{"channel":"tickers","instId":"{instId}"}]}',
                "ws_combined_enabled": False,
                "ws_symbol_lowercase": False,
                "ws_ping_interval_seconds": 20,
                "ws_pong_timeout_seconds": 60,
                "ws_connection_ttl_hours": 24,
                "ws_max_streams_per_connection": 1024,
                "ws_control_messages_per_second": 5,
            },
        )()
        news_api_config = None
        onchain_api_config = None
        social_api_config = None

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

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["execution_router"] = execution_router

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"data": [{"instId": "BTC-USDT-SWAP", "last": "100.0", "vol24h": "1.0"}], "_market_source_status": "ready"}

    class StubOkxWsMarketFeed:
        def __init__(self, *, rest_payload_supplier, market_api_config=None, supervisor=None, client_factory=None):
            captured["market_api_config"] = market_api_config

        def fetch(self, symbol):
            return {"data": [{"instId": "BTC-USDT-SWAP", "last": "100.0", "vol24h": "1.0"}], "_market_source_status": "ready"}

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            self.exchange = exchange
            self.market_payload_supplier = market_payload_supplier

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            payload = self.market_payload_supplier(symbol)
            return {
                "event_bundle": [{"event_type": "market_tick", "symbol": symbol, "exchange": self.exchange}],
                "feature_snapshot": {"assembler_exchange": self.exchange},
                "market_source_status": payload["_market_source_status"],
            }

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.OkxPublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.OkxWsMarketFeed", StubOkxWsMarketFeed)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
        }
    )

    assert captured["market_api_config"] is not None
    assert captured["market_api_config"].ws_base_url == "wss://ws.okx.com:8443"
    assert captured["market_api_config"].ws_path == "/ws/v5/public"


def test_runtime_input_supplier_closes_stale_cached_assembler_and_feed_when_market_source_cache_key_changes(monkeypatch):
    created_feeds = []
    created_assemblers = []

    class StubSettings:
        news_url = ""
        onchain_url = ""
        social_url = ""

    class StubEventClient:
        pass

    class StubMarketFeed:
        def __init__(self, market_api_config=None):
            self.market_api_config = market_api_config
            self.closed = 0
            created_feeds.append(self)

        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0", "_market_source_status": "ready"}

        def close(self):
            self.closed += 1

    class StubRestMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            self.exchange = exchange
            self.market_payload_supplier = market_payload_supplier
            self.closed = 0
            created_assemblers.append(self)

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            payload = self.market_payload_supplier(symbol)
            return {
                "event_bundle": [{"event_type": "market_tick", "symbol": payload["s"], "exchange": self.exchange}],
                "feature_snapshot": {"assembler_exchange": self.exchange},
                "market_source_status": payload["_market_source_status"],
            }

        def close(self):
            self.closed += 1

    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubRestMarketFeed())
    monkeypatch.setattr(
        "trade_runtime.app.BinanceWsMarketFeed",
        lambda *, rest_payload_supplier, market_api_config=None, supervisor=None, client_factory=None: StubMarketFeed(
            market_api_config=market_api_config
        ),
    )
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    supplier = _build_runtime_input_supplier(
        settings=StubSettings(),
        event_client=StubEventClient(),
        stream_publisher=None,
        initial_exchange="binance",
        initial_feed_urls=None,
        initial_market_api_config=type("MarketApiConfig", (), {"id": 1, "ws_path": "/ws"})(),
    )

    supplier(trace_id="trace-1", symbol="BTCUSDT", exchange="binance", market_api_config=type("MarketApiConfig", (), {"id": 1, "ws_path": "/ws"})())
    supplier(trace_id="trace-2", symbol="BTCUSDT", exchange="binance", market_api_config=type("MarketApiConfig", (), {"id": 2, "ws_path": "/stream"})())

    assert len(created_assemblers) == 2
    assert len(created_feeds) == 2
    assert created_assemblers[0].closed == 1
    assert created_feeds[0].closed == 1
    assert created_assemblers[1].closed == 0
    assert created_feeds[1].closed == 0



def test_runtime_input_supplier_prefers_persisted_market_history_when_db_has_more_samples(monkeypatch):
    class StubSettings:
        news_url = ""
        onchain_url = ""
        social_url = ""

    class StubEventClient:
        def get_market_history(self, *, symbol, exchange, limit, max_age_minutes):
            assert symbol == "BTCUSDT"
            assert exchange == "binance"
            assert limit == 60
            assert max_age_minutes == 300
            return [
                {"observed_at": "2026-04-29T04:00:00+00:00", "price": 100.0, "quote_volume": 1000.0},
                {"observed_at": "2026-04-29T04:01:00+00:00", "price": 101.0, "quote_volume": 1200.0},
                {"observed_at": "2026-04-29T04:02:00+00:00", "price": 102.0, "quote_volume": 1400.0},
            ]

    class StubRestMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "103.0", "q": "1500.0"}

    class StubMarketFeed:
        def __init__(self, *, rest_payload_supplier, market_api_config=None, supervisor=None, client_factory=None):
            pass

        def fetch(self, symbol):
            return {"s": symbol, "p": "103.0", "q": "1500.0", "_market_source_status": "ready"}

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            pass

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {
                "event_bundle": [],
                "feature_snapshot": {"symbol": symbol, "event_strength": "normal"},
                "market_context_history": [
                    {"observed_at": "2026-04-29T04:03:00+00:00", "price": 103.0, "quote_volume": 1500.0}
                ],
            }

    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubRestMarketFeed())
    monkeypatch.setattr("trade_runtime.app.BinanceWsMarketFeed", StubMarketFeed)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    supplier = _build_runtime_input_supplier(
        settings=StubSettings(),
        event_client=StubEventClient(),
        stream_publisher=None,
        initial_exchange="binance",
        initial_feed_urls=None,
        initial_market_api_config=None,
    )

    result = supplier(trace_id="trace-db-history", symbol="BTCUSDT", exchange="binance")

    assert [item["price"] for item in result["market_context_history"]] == [100.0, 101.0, 102.0]


def test_runtime_input_supplier_passes_runtime_config_and_strategy_context(monkeypatch):
    captured = {}

    class StubSettings:
        news_url = ""
        onchain_url = ""
        social_url = ""

    class StubEventClient:
        pass

    class StubRestMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubMarketFeed:
        def __init__(self, *, rest_payload_supplier, market_api_config=None, supervisor=None, client_factory=None):
            pass

        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0", "_market_source_status": "ready"}

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            pass

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            captured["runtime_config"] = runtime_config
            captured["strategy_context"] = strategy_context
            return {
                "event_bundle": [],
                "feature_snapshot": {"symbol": symbol, "event_strength": "noise"},
            }

    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubRestMarketFeed())
    monkeypatch.setattr("trade_runtime.app.BinanceWsMarketFeed", StubMarketFeed)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    supplier = _build_runtime_input_supplier(
        settings=StubSettings(),
        event_client=StubEventClient(),
        stream_publisher=None,
        initial_exchange="binance",
        initial_feed_urls=None,
        initial_market_api_config=None,
    )

    runtime_config = {"market_trigger": {"ruleOnlyPriceChangePct": 1.0}}
    strategy_context = {"strategy_key": "btc-route"}

    supplier(
        trace_id="trace-policy",
        symbol="BTCUSDT",
        exchange="binance",
        runtime_config=runtime_config,
        strategy_context=strategy_context,
    )

    assert captured["runtime_config"] == runtime_config
    assert captured["strategy_context"] == strategy_context


def test_runtime_input_supplier_does_not_enable_disabled_aux_sources(monkeypatch):
    captured = {}

    class StubSettings:
        news_url = ""
        onchain_url = ""
        social_url = ""

    class StubEventClient:
        pass

    class StubRestMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubMarketFeed:
        def __init__(self, *, rest_payload_supplier, market_api_config=None, supervisor=None, client_factory=None):
            pass

        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0", "_market_source_status": "ready"}

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            captured["news_items_supplier"] = kwargs.get("news_items_supplier")
            captured["onchain_items_supplier"] = kwargs.get("onchain_items_supplier")
            captured["social_items_supplier"] = kwargs.get("social_items_supplier")

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {
                "event_bundle": [],
                "feature_snapshot": {"symbol": symbol, "event_strength": "noise"},
            }

    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubRestMarketFeed())
    monkeypatch.setattr("trade_runtime.app.BinanceWsMarketFeed", StubMarketFeed)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    supplier = _build_runtime_input_supplier(
        settings=StubSettings(),
        event_client=StubEventClient(),
        stream_publisher=None,
        initial_exchange="binance",
        initial_feed_urls={
            "news_url": "http://feed.local/news",
            "onchain_url": "",
            "social_url": "",
        },
        initial_market_api_config=None,
    )

    supplier(
        trace_id="trace-disabled-aux",
        symbol="BTCUSDT",
        exchange="binance",
        feed_urls={
            "news_url": "http://feed.local/news",
            "onchain_url": "",
            "social_url": "",
        },
    )

    assert callable(captured["news_items_supplier"])
    assert captured["onchain_items_supplier"] is None
    assert captured["social_items_supplier"] is None


def test_build_runtime_app_disables_onchain_feed_when_market_data_config_turns_it_off(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = None
        exchange_account_binding = None
        exchange_account = None
        ai_model_config = None
        news_api_config = type("NewsApiConfig", (), {"api_url": "https://bootstrap.internal/news"})()
        onchain_api_config = type("OnchainApiConfig", (), {"api_url": "https://bootstrap.internal/onchain"})()
        social_api_config = type("SocialApiConfig", (), {"api_url": "https://bootstrap.internal/social"})()
        market_data_config = type(
            "MarketDataConfig",
            (),
            {
                "symbol": "BTCUSDT",
                "enabled": "1",
                "collect_interval": 15,
                "collect_onchain": "0",
                "data_sources": "[\"binance\",\"rss\"]",
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

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["execution_router"] = execution_router

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            captured.setdefault("aux_suppliers", []).append({"url": url, "timeout": timeout})

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
        }
    )

    assert [item["url"] for item in captured.get("aux_suppliers", [])] == [
        "https://bootstrap.internal/news",
        "https://bootstrap.internal/social",
    ]


def test_build_runtime_app_does_not_reenable_disabled_source_feeds_from_env(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = None
        exchange_account_binding = None
        exchange_account = None
        ai_model_config = None
        news_api_config = type("NewsApiConfig", (), {"api_url": "https://bootstrap.internal/news", "enabled": "0"})()
        onchain_api_config = type("OnchainApiConfig", (), {"api_url": "https://bootstrap.internal/onchain", "enabled": "1"})()
        social_api_config = type("SocialApiConfig", (), {"api_url": "https://bootstrap.internal/social", "enabled": "0"})()
        market_data_config = type(
            "MarketDataConfig",
            (),
            {
                "symbol": "BTCUSDT",
                "enabled": "1",
                "collect_interval": 15,
                "collect_onchain": "1",
                "data_sources": "[\"rss\",\"whale-alert\",\"social\"]",
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

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["execution_router"] = execution_router

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            captured.setdefault("aux_suppliers", []).append({"url": url, "timeout": timeout})

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_SYMBOL": "BTCUSDT",
            "TRADE_RUNTIME_EXCHANGE": "binance",
            "TRADE_RUNTIME_NEWS_URL": "http://env.local/news",
            "TRADE_RUNTIME_ONCHAIN_URL": "http://env.local/onchain",
            "TRADE_RUNTIME_SOCIAL_URL": "http://env.local/social",
        }
    )

    assert [item["url"] for item in captured.get("aux_suppliers", [])] == [
        "https://bootstrap.internal/onchain",
    ]


def test_build_runtime_app_wires_stream_publisher_when_redis_env_present(monkeypatch):
    captured = {}

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def get_bootstrap(self, symbol=None, exchange=None):
            return type(
                "Bootstrap",
                (),
                {
                    "runtime_config": None,
                    "strategy": None,
                    "strategy_version": None,
                    "symbol_scope": None,
                    "exchange_account_binding": None,
                    "exchange_account": None,
                },
            )()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            pass

    class StubRuntimeInputAssembler:
        def __init__(self, **kwargs):
            captured["assembler_kwargs"] = kwargs

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {"event_bundle": [], "feature_snapshot": {}}

    class StubRedisClient:
        def __init__(self, **kwargs):
            captured["redis_kwargs"] = kwargs

    class StubStreamPublisher:
        def __init__(self, redis_client, stream_name):
            captured["stream_publisher"] = {
                "redis_client": redis_client,
                "stream_name": stream_name,
            }

    class StubStreamConsumer:
        def __init__(
            self,
            *,
            redis_client,
            stream_name,
            group_name,
            consumer_name,
            handler,
            dead_letter_stream=None,
            max_retries=3,
            dedupe_ttl_seconds=86400,
        ):
            captured["stream_consumer"] = {
                "redis_client": redis_client,
                "stream_name": stream_name,
                "group_name": group_name,
                "consumer_name": consumer_name,
                "handler": handler,
                "dead_letter_stream": dead_letter_stream,
                "max_retries": max_retries,
                "dedupe_ttl_seconds": dedupe_ttl_seconds,
            }

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            pass

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)
    monkeypatch.setattr("trade_runtime.app.redis.Redis", lambda **kwargs: StubRedisClient(**kwargs))
    monkeypatch.setattr("trade_runtime.app.StreamPublisher", StubStreamPublisher)
    monkeypatch.setattr("trade_runtime.app.StreamConsumer", StubStreamConsumer)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_STREAM_NAME": "trade.runtime.events",
            "TRADE_RUNTIME_STREAM_GROUP": "trade-runtime.persist",
            "TRADE_RUNTIME_REDIS_HOST": "redis.local",
            "TRADE_RUNTIME_REDIS_PORT": "6381",
            "TRADE_RUNTIME_REDIS_DB": "2",
            "TRADE_RUNTIME_REDIS_PASSWORD": "secret-redis",
        }
    )

    assert captured["redis_kwargs"] == {
        "host": "redis.local",
        "port": 6381,
        "db": 2,
        "password": "secret-redis",
        "decode_responses": True,
    }
    assert captured["stream_publisher"]["stream_name"] == "trade.runtime.events"
    assert captured["assembler_kwargs"]["stream_publisher"] is not None
    assert captured["assembler_kwargs"]["stream_consumer"] is not None
    assert captured["assembler_kwargs"]["event_client"] is None
    assert captured["stream_consumer"]["stream_name"] == "trade.runtime.events"
    assert captured["stream_consumer"]["group_name"] == "trade-runtime.persist"


def test_build_execution_router_requires_runtime_account_for_binance_credentials(monkeypatch):
    captured = {}

    class StubBinanceClient:
        def __init__(self, api_key, api_secret, testnet=False):
            captured["binance_client"] = {
                "api_key": api_key,
                "api_secret": api_secret,
                "testnet": testnet,
            }

    monkeypatch.setattr("trade_runtime.app.BinanceRestExecutionClient", StubBinanceClient)

    router = build_execution_router(
        {
            "TRADE_RUNTIME_BINANCE_API_KEY": "key-1",
            "TRADE_RUNTIME_BINANCE_API_SECRET": "secret-1",
            "TRADE_RUNTIME_BINANCE_TESTNET": "true",
        }
    )

    assert "binance_client" not in captured
    assert router is not None


def test_build_execution_router_requires_runtime_account_for_okx_credentials(monkeypatch):
    captured = {}

    class StubOkxClient:
        def __init__(self, api_key, api_secret, passphrase, base_url="https://www.okx.com", demo_trading=False):
            captured["okx_client"] = {
                "api_key": api_key,
                "api_secret": api_secret,
                "passphrase": passphrase,
                "base_url": base_url,
                "demo_trading": demo_trading,
            }

    monkeypatch.setattr("trade_runtime.app.OkxRestExecutionClient", StubOkxClient)

    router = build_execution_router(
        {
            "TRADE_RUNTIME_OKX_API_KEY": "okx-key-1",
            "TRADE_RUNTIME_OKX_API_SECRET": "okx-secret-1",
            "TRADE_RUNTIME_OKX_PASSPHRASE": "okx-pass-1",
            "TRADE_RUNTIME_OKX_BASE_URL": "https://okx.local",
            "TRADE_RUNTIME_OKX_DEMO_TRADING": "true",
        }
    )

    assert "okx_client" not in captured
    assert router is not None


def test_build_runtime_app_prefers_control_plane_scope_and_account(monkeypatch):
    captured = {}

    class StubBootstrap:
        def __init__(self):
            self.runtime_config = None
            self.strategy = None
            self.strategy_version = None
            self.symbol_scope = type(
                "SymbolScope",
                (),
                {"symbol": "ETHUSDT", "exchange_code": "okx"},
            )()
            self.exchange_account_binding = None
            self.exchange_account = type(
                "ExchangeAccount",
                (),
                {
                    "exchange_code": "okx",
                    "api_key_ciphertext": "okx-ak",
                    "api_secret_ciphertext": "okx-sk",
                    "passphrase_ciphertext": "okx-pass",
                    "api_base_url": "https://okx.control-plane",
                    "demo_trading": True,
                    "testnet": False,
                },
            )()

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def get_bootstrap(self, symbol=None, exchange=None):
            captured["bootstrap_query"] = {"symbol": symbol, "exchange": exchange}
            return StubBootstrap()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            captured["execution_router"] = execution_router

    class StubOkxClient:
        def __init__(self, api_key, api_secret, passphrase, base_url="https://www.okx.com", demo_trading=False):
            captured["okx_client"] = {
                "api_key": api_key,
                "api_secret": api_secret,
                "passphrase": passphrase,
                "base_url": base_url,
                "demo_trading": demo_trading,
            }

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"data": [{"instId": symbol, "last": "100.0", "vol24h": "1.0"}]}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            pass

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.OkxRestExecutionClient", StubOkxClient)
    monkeypatch.setattr("trade_runtime.app.OkxPublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)

    app = build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_BEARER_TOKEN": "runtime-token",
        }
    )

    assert captured["bootstrap_query"] == {"symbol": None, "exchange": None}
    assert app.symbol == "ETHUSDT"
    assert app.exchange == "okx"
    assert captured["okx_client"] == {
        "api_key": "okx-ak",
        "api_secret": "okx-sk",
        "passphrase": "okx-pass",
        "base_url": "https://okx.control-plane",
        "demo_trading": True,
    }
    assert captured["execution_router"] is not None


def test_build_runtime_app_ignores_env_symbol_exchange_and_uses_multi_route_control_plane(monkeypatch):
    captured = {}

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def list_bootstraps(self):
            captured["used_list_bootstraps"] = True
            return [
                type(
                    "Bootstrap",
                    (),
                    {
                        "runtime_config": None,
                        "strategy": None,
                        "strategy_version": None,
                        "symbol_scope": type("Scope", (), {"symbol": "BTCUSDT", "exchange_code": "binance"})(),
                        "exchange_account_binding": None,
                        "exchange_account": None,
                    },
                )(),
                type(
                    "Bootstrap",
                    (),
                    {
                        "runtime_config": None,
                        "strategy": None,
                        "strategy_version": None,
                        "symbol_scope": type("Scope", (), {"symbol": "ETHUSDT", "exchange_code": "okx"})(),
                        "exchange_account_binding": None,
                        "exchange_account": None,
                    },
                )(),
            ]

        def get_bootstrap(self, symbol=None, exchange=None):
            raise AssertionError("get_bootstrap should not be used when symbol/exchange come from env only")

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            pass

    class StubMarketFeed:
        def __init__(self, exchange="binance"):
            self.exchange = exchange

        def fetch(self, symbol):
            return {"exchange": self.exchange, "symbol": symbol}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            pass

        def fetch(self, symbol):
            return []

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed("binance"))
    monkeypatch.setattr("trade_runtime.app.OkxPublicMarketFeed", lambda: StubMarketFeed("okx"))
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)

    app = build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_SYMBOL": "SHOULD_NOT_BE_USED",
            "TRADE_RUNTIME_EXCHANGE": "binance",
        }
    )

    assert captured["used_list_bootstraps"] is True
    assert app.symbol == "BTCUSDT"
    assert app.exchange == "binance"


def test_runtime_app_run_once_delegates_to_runner_with_supplied_payloads():
    captured = {}

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            captured["trace_id"] = trace_id
            captured["symbol"] = symbol
            captured["exchange"] = exchange
            captured["event_bundle"] = event_bundle
            captured["feature_snapshot"] = feature_snapshot
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle_supplier=lambda: [{"event_type": "market_tick"}],
        feature_snapshot_supplier=lambda: {"price_change_pct": 2.3},
    )

    result = app.run_once()

    assert captured["trace_id"]
    assert captured["symbol"] == "BTCUSDT"
    assert captured["exchange"] == "binance"
    assert captured["event_bundle"][0]["event_type"] == "market_tick"
    assert captured["feature_snapshot"]["price_change_pct"] == 2.3
    assert result["status"] == "ok"


def test_runtime_app_run_once_prefers_runtime_input_supplier():
    captured = {}

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            captured["trace_id"] = trace_id
            captured["event_bundle"] = event_bundle
            captured["feature_snapshot"] = feature_snapshot
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_input_supplier=lambda **kwargs: {
            "trace_id": kwargs["trace_id"],
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {"price_change_pct": 4.5},
        },
        event_bundle_supplier=lambda: [{"event_type": "stale"}],
        feature_snapshot_supplier=lambda: {"price_change_pct": -1},
    )

    result = app.run_once()

    assert captured["trace_id"]
    assert captured["event_bundle"] == [{"event_type": "market_tick"}]
    assert captured["feature_snapshot"]["price_change_pct"] == 4.5
    assert result["status"] == "ok"


def test_runtime_app_run_once_passes_market_context_history_from_runtime_input_supplier():
    captured = {}

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, market_context_history):
            captured["market_context_history"] = market_context_history
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "price": 100.0}],
            "feature_snapshot": {"price_change_pct": 0.0},
            "market_context_history": [{"observed_at": "2026-04-24T07:00:00+00:00", "price": 100.0}],
        },
    )

    result = app.run_once()

    assert captured["market_context_history"] == [{"observed_at": "2026-04-24T07:00:00+00:00", "price": 100.0}]
    assert result["status"] == "ok"


def test_runtime_app_run_once_sends_worker_heartbeat_before_execution():
    captured = {"heartbeats": []}

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            captured["runner_trace_id"] = trace_id
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        worker_id="runtime-worker-1",
        heartbeat_publisher=captured["heartbeats"].append,
    )

    result = app.run_once()

    assert captured["heartbeats"] == ["runtime-worker-1"]
    assert captured["runner_trace_id"]
    assert result["status"] == "ok"


def test_runtime_app_run_once_refreshes_runtime_context_before_inputs_and_execution():
    captured = {}

    class StubRunner:
        def __init__(self):
            self.execution_router = "initial-router"

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            captured["runner"] = {
                "trace_id": trace_id,
                "symbol": symbol,
                "exchange": exchange,
                "event_bundle": event_bundle,
                "feature_snapshot": feature_snapshot,
                "execution_router": self.execution_router,
            }
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="ETHUSDT",
            exchange="okx",
            execution_router="refreshed-router",
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [
                {
                    "event_type": "market_tick",
                    "symbol": kwargs["symbol"],
                    "exchange": kwargs["exchange"],
                }
            ],
            "feature_snapshot": {"source_exchange": kwargs["exchange"]},
        },
    )

    result = app.run_once()

    assert app.symbol == "ETHUSDT"
    assert app.exchange == "okx"
    assert captured["runner"]["symbol"] == "ETHUSDT"
    assert captured["runner"]["exchange"] == "okx"
    assert captured["runner"]["execution_router"] == "refreshed-router"
    assert captured["runner"]["event_bundle"][0]["exchange"] == "okx"
    assert captured["runner"]["feature_snapshot"]["source_exchange"] == "okx"
    assert result["status"] == "ok"


def test_runtime_app_run_once_runs_memory_consolidation_after_iteration():
    captured = {"memory_calls": 0}

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            return {"status": "ok", "trace_id": trace_id, "symbol": symbol, "exchange": exchange}

    class StubMemoryJob:
        def run_once(self):
            captured["memory_calls"] += 1
            return {"stored_count": 1}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        memory_consolidation_job=StubMemoryJob(),
    )

    result = app.run_once()

    assert result["status"] == "ok"
    assert captured["memory_calls"] == 1


def test_runtime_app_run_once_runs_memory_consolidation_after_multi_context_iteration():
    captured = {"memory_calls": 0, "runner_calls": []}

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            captured["runner_calls"].append({"trace_id": trace_id, "symbol": symbol, "exchange": exchange})
            return {"status": "ok", "trace_id": trace_id, "symbol": symbol, "exchange": exchange}

    class StubMemoryJob:
        def run_once(self):
            captured["memory_calls"] += 1
            return {"stored_count": 2}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: [
            RuntimeContext(symbol="BTCUSDT", exchange="binance", strategy_context={}),
            RuntimeContext(symbol="ETHUSDT", exchange="okx", strategy_context={}),
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"], "price": 100.0}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
        memory_consolidation_job=StubMemoryJob(),
    )

    result = app.run_once()

    assert result["status"] == "ok"
    assert len(result["results"]) == 2
    assert len(captured["runner_calls"]) == 2
    assert captured["memory_calls"] == 1


def test_runtime_app_run_forever_repeats_with_sleep_between_iterations():
    calls = []
    sleeps = []

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            calls.append(
                {
                    "trace_id": trace_id,
                    "symbol": symbol,
                    "exchange": exchange,
                    "event_bundle": event_bundle,
                    "feature_snapshot": feature_snapshot,
                }
            )
            return {"status": "ok", "count": len(calls)}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        poll_interval_seconds=7,
        sleep=sleeps.append,
    )

    result = app.run_forever(iterations=2)

    assert len(calls) == 2
    assert calls[0]["trace_id"]
    assert calls[1]["trace_id"]
    assert sleeps == [7]
    assert result["count"] == 2


def test_runtime_app_run_forever_splits_sleep_when_active_position_watcher_interval_is_shorter():
    calls = []
    sleeps = []

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, **kwargs):
            calls.append(trace_id)
            return {"status": "ok", "count": len(calls)}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        poll_interval_seconds=30,
        sleep=sleeps.append,
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="binance",
            strategy_context={},
            runtime_config=type(
                "RuntimeConfigPayload",
                (),
                {"runtime_flags_json": "{\"positionRiskWatcher\":{\"enabled\":true,\"intervalSeconds\":10}}"},
            )(),
            runtime_account_context={
                "current_position_side": "long",
                "current_position_quantity": 1.0,
                "entry_price": 100.0,
            },
        ),
    )

    result = app.run_forever(iterations=2)

    assert len(calls) == 2
    assert sleeps == [10]
    assert result["count"] == 2


def test_runtime_app_run_forever_splits_sleep_for_active_position_in_multi_route_contexts():
    calls = []
    sleeps = []

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, **kwargs):
            calls.append({"trace_id": trace_id, "symbol": symbol, "exchange": exchange})
            return {"status": "ok", "symbol": symbol, "exchange": exchange}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        poll_interval_seconds=30,
        sleep=sleeps.append,
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="BTCUSDT",
                exchange="okx",
                strategy_context={},
                runtime_config=type(
                    "RuntimeConfigPayload",
                    (),
                    {"runtime_flags_json": "{\"positionRiskWatcher\":{\"enabled\":true,\"intervalSeconds\":8}}"},
                )(),
                runtime_account_context={
                    "current_position_side": "long",
                    "current_position_quantity": 1.0,
                    "entry_price": 100.0,
                },
            ),
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                strategy_context={},
                runtime_account_context={"current_position_side": "flat", "current_position_quantity": 0.0},
            ),
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"], "price": 100.0}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    result = app.run_forever(iterations=2)

    assert len(calls) == 4
    assert sleeps == [8]
    assert result["status"] == "ok"
    assert len(result["results"]) == 2


def test_runtime_app_run_forever_continues_after_iteration_exception(caplog):
    calls = []
    sleeps = []

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            calls.append(trace_id)
            if len(calls) == 1:
                raise RuntimeError("backend temporarily unavailable")
            return {"status": "ok", "count": len(calls)}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        poll_interval_seconds=7,
        sleep=sleeps.append,
    )

    with caplog.at_level(logging.WARNING, logger="trade_runtime.app"):
        result = app.run_forever(iterations=2)

    assert len(calls) == 2
    assert sleeps == [7]
    assert result == {"status": "ok", "count": 2}
    assert "runtime iteration failed" in caplog.text


def test_runtime_app_run_forever_runs_memory_consolidation_after_iteration():
    calls = []

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            calls.append(trace_id)
            return {"status": "ok", "count": len(calls)}

    class StubMemoryJob:
        def __init__(self):
            self.calls = 0

        def run_once(self):
            self.calls += 1
            return {"stored_count": 1}

    memory_job = StubMemoryJob()
    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        memory_consolidation_job=memory_job,
    )

    result = app.run_forever(iterations=2)

    assert result == {"status": "ok", "count": 2}
    assert memory_job.calls == 2


def test_runtime_app_run_forever_continues_after_memory_consolidation_exception(caplog):
    calls = []

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            calls.append(trace_id)
            return {"status": "ok", "count": len(calls)}

    class FailingMemoryJob:
        def run_once(self):
            raise RuntimeError("memory backend temporarily unavailable")

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        memory_consolidation_job=FailingMemoryJob(),
    )

    with caplog.at_level(logging.WARNING, logger="trade_runtime.app"):
        result = app.run_forever(iterations=2)

    assert len(calls) == 2
    assert result == {"status": "ok", "count": 2}
    assert "memory consolidation failed" in caplog.text


def test_runtime_main_forever_retries_after_startup_service_exception(monkeypatch, caplog):
    captured = {"build_calls": 0, "sleeps": []}

    class StubApp:
        def run_forever(self):
            return {"mode": "forever", "started_after": captured["build_calls"]}

    def stub_build_runtime_app(env=None):
        captured["build_calls"] += 1
        if captured["build_calls"] == 1:
            raise ConnectionError("backend refused connection")
        return StubApp()

    monkeypatch.setattr("trade_runtime.app.build_runtime_app", stub_build_runtime_app)
    monkeypatch.setattr("trade_runtime.app.time.sleep", captured["sleeps"].append)

    with caplog.at_level(logging.WARNING, logger="trade_runtime.app"):
        result = main({"TRADE_RUNTIME_RUN_MODE": "forever", "TRADE_RUNTIME_POLL_INTERVAL_SECONDS": "3"})

    assert captured["build_calls"] == 2
    assert captured["sleeps"] == [3]
    assert result == {"mode": "forever", "started_after": 2}
    assert "runtime startup failed" in caplog.text


def test_build_runtime_app_refreshes_bootstrap_scope_and_execution_router_between_iterations(monkeypatch):
    captured = {"runner_calls": [], "binance_clients": [], "okx_clients": []}

    class StubBootstrap:
        def __init__(self, symbol, exchange, account):
            self.runtime_config = None
            self.strategy = None
            self.strategy_version = None
            self.symbol_scope = type(
                "SymbolScope",
                (),
                {"symbol": symbol, "exchange_code": exchange},
            )()
            self.exchange_account_binding = None
            self.exchange_account = account

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            self._bootstraps = iter(
                [
                    StubBootstrap(
                        "BTCUSDT",
                        "binance",
                        type(
                            "ExchangeAccount",
                            (),
                            {
                                "exchange_code": "binance",
                                "api_key_ciphertext": "binance-ak",
                                "api_secret_ciphertext": "binance-sk",
                                "testnet": True,
                            },
                        )(),
                    ),
                    StubBootstrap(
                        "ETHUSDT",
                        "okx",
                        type(
                            "ExchangeAccount",
                            (),
                            {
                                "exchange_code": "okx",
                                "api_key_ciphertext": "okx-ak",
                                "api_secret_ciphertext": "okx-sk",
                                "passphrase_ciphertext": "okx-pass",
                                "api_base_url": "https://okx.local",
                                "demo_trading": True,
                                "testnet": False,
                            },
                        )(),
                    ),
                ]
            )

        def get_bootstrap(self, symbol=None, exchange=None):
            return next(self._bootstraps)

        def get_config(self):
            return type("RuntimeConfig", (), {"effective_mode": lambda self: "paper", "live_enabled": False})()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, exchange_account=None):
            captured["runner_calls"].append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "event_bundle": event_bundle,
                    "feature_snapshot": feature_snapshot,
                    "execution_router": self.execution_router,
                    "exchange_account": exchange_account,
                }
            )
            return {"status": "ok", "symbol": symbol, "exchange": exchange}

    class StubBinanceClient:
        def __init__(self, api_key, api_secret, testnet=False):
            captured["binance_clients"].append(
                {"api_key": api_key, "api_secret": api_secret, "testnet": testnet}
            )

    class StubOkxClient:
        def __init__(self, api_key, api_secret, passphrase, base_url="https://www.okx.com", demo_trading=False):
            captured["okx_clients"].append(
                {
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "passphrase": passphrase,
                    "base_url": base_url,
                    "demo_trading": demo_trading,
                }
            )

    class StubMarketFeed:
        def __init__(self, exchange):
            self.exchange = exchange

        def fetch(self, symbol):
            return {"exchange": self.exchange, "symbol": symbol}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            pass

        def fetch(self, symbol):
            return []

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            self.exchange = exchange
            self.market_payload_supplier = market_payload_supplier

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {
                "event_bundle": [{"event_type": "market_tick", "symbol": symbol, "exchange": self.exchange}],
                "feature_snapshot": {"assembler_exchange": self.exchange},
            }

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinanceRestExecutionClient", StubBinanceClient)
    monkeypatch.setattr("trade_runtime.app.OkxRestExecutionClient", StubOkxClient)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed("binance"))
    monkeypatch.setattr("trade_runtime.app.OkxPublicMarketFeed", lambda: StubMarketFeed("okx"))
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    app = build_runtime_app({"TRADE_RUNTIME_BASE_URL": "http://localhost:8088"})

    first = app.run_once()
    second = app.run_once()

    assert first["symbol"] == "BTCUSDT"
    assert first["exchange"] == "binance"
    assert second["symbol"] == "ETHUSDT"
    assert second["exchange"] == "okx"
    assert captured["runner_calls"][0]["execution_router"] != captured["runner_calls"][1]["execution_router"]
    assert captured["runner_calls"][0]["feature_snapshot"]["assembler_exchange"] == "binance"
    assert captured["runner_calls"][1]["feature_snapshot"]["assembler_exchange"] == "okx"
    assert captured["binance_clients"] == [
        {"api_key": "binance-ak", "api_secret": "binance-sk", "testnet": True}
    ]
    assert captured["okx_clients"] == [
        {
            "api_key": "okx-ak",
            "api_secret": "okx-sk",
            "passphrase": "okx-pass",
            "base_url": "https://okx.local",
            "demo_trading": True,
        }
    ]


def test_build_runtime_app_passes_parsed_strategy_context_to_runner(monkeypatch):
    captured = {}

    class StubBootstrap:
        def __init__(self):
            self.runtime_config = None
            self.strategy = type(
                "Strategy",
                (),
                {
                    "id": 7,
                    "strategy_key": "event-btc",
                    "strategy_name": "BTC Event",
                    "runtime_mode": "shadow",
                },
            )()
            self.strategy_version = type(
                "StrategyVersion",
                (),
                {
                    "strategy_id": 7,
                    "version_no": 3,
                    "config_json": "{\"riskBudget\":0.02,\"maxPositionRatio\":0.4}",
                },
            )()
            self.symbol_scope = type(
                "SymbolScope",
                (),
                {"symbol": "BTCUSDT", "exchange_code": "binance"},
            )()
            self.exchange_account_binding = None
            self.exchange_account = None
            self.ai_model_config = type(
                "AiModelConfig",
                (),
                {
                    "id": 31,
                    "model_code": "gpt-4.1",
                    "model_name": "Runtime Default",
                    "provider": "openai",
                    "api_base_url": "https://api.openai.internal",
                },
            )()
            self.news_api_config = None
            self.onchain_api_config = type(
                "OnchainApiConfig",
                (),
                {
                    "data_category": "ONCHAIN",
                    "api_url": "https://feeds.internal/onchain",
                    "enabled": "1",
                },
            )()
            self.social_api_config = type(
                "SocialApiConfig",
                (),
                {
                    "data_category": "SOCIAL",
                    "api_url": "https://feeds.internal/social",
                    "enabled": "0",
                },
            )()
            self.news_api_config = type(
                "NewsApiConfig",
                (),
                {
                    "data_category": "NEWS",
                    "api_url": "https://feeds.internal/news",
                    "enabled": "1",
                },
            )()
            self.market_data_config = type(
                "MarketDataConfig",
                (),
                {
                    "config_name": "BTC Runtime Inputs",
                    "symbol": "BTCUSDT",
                    "enabled": "1",
                    "collect_interval": 15,
                    "collect_onchain": "1",
                    "data_sources": "[\"binance\",\"rss\",\"whale-alert\"]",
                },
            )()

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def get_bootstrap(self, symbol=None, exchange=None):
            return StubBootstrap()

        def get_config(self):
            return type("RuntimeConfig", (), {"effective_mode": lambda self: "shadow", "live_enabled": False})()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            captured["strategy_context"] = strategy_context
            return {"status": "ok"}

    class StubMarketFeed:
        def __init__(self, exchange):
            self.exchange = exchange

        def fetch(self, symbol):
            return {"exchange": self.exchange, "symbol": symbol}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            pass

        def fetch(self, symbol):
            return []

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            self.exchange = exchange

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {
                "event_bundle": [{"event_type": "market_tick", "symbol": symbol, "exchange": self.exchange}],
                "feature_snapshot": {"assembler_exchange": self.exchange},
            }

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed("binance"))
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    app = build_runtime_app({"TRADE_RUNTIME_BASE_URL": "http://localhost:8088"})
    app.run_once()

    assert captured["strategy_context"]["strategy_key"] == "event-btc"
    assert captured["strategy_context"]["strategy_version"] == 3
    assert captured["strategy_context"]["strategy_config"] == {
        "riskBudget": 0.02,
        "maxPositionRatio": 0.4,
    }
    assert captured["strategy_context"]["ai_model_config"] == {
        "id": 31,
        "model_code": "gpt-4.1",
        "model_name": "Runtime Default",
        "provider": "openai",
        "api_base_url": "https://api.openai.internal",
    }
    assert captured["strategy_context"]["market_data_config"] == {
        "config_name": "BTC Runtime Inputs",
        "symbol": "BTCUSDT",
        "enabled": "1",
        "collect_interval": 15,
        "collect_onchain": "1",
        "data_sources": "[\"binance\",\"rss\",\"whale-alert\"]",
    }
    assert captured["strategy_context"]["news_api_config"] == {
        "data_category": "NEWS",
        "api_url": "https://feeds.internal/news",
        "enabled": "1",
    }
    assert captured["strategy_context"]["onchain_api_config"] == {
        "data_category": "ONCHAIN",
        "api_url": "https://feeds.internal/onchain",
        "enabled": "1",
    }
    assert captured["strategy_context"]["social_api_config"] == {
        "data_category": "SOCIAL",
        "api_url": "https://feeds.internal/social",
        "enabled": "0",
    }


def test_build_runtime_app_passes_initial_market_history_to_assembler(monkeypatch):
    captured = {}

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def get_bootstrap(self, symbol=None, exchange=None):
            return type(
                "Bootstrap",
                (),
                {
                    "runtime_config": None,
                    "strategy": None,
                    "strategy_version": None,
                    "symbol_scope": type("Scope", (), {"symbol": "BTCUSDT", "exchange_code": "binance"})(),
                    "exchange_account_binding": None,
                    "exchange_account": None,
                },
            )()

        def get_config(self):
            return type("RuntimeConfig", (), {"effective_mode": lambda self: "paper", "live_enabled": False})()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            pass

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "c": "100.0", "q": "2.0"}

    class StubRuntimeInputAssembler:
        def __init__(self, **kwargs):
            captured["assembler_kwargs"] = kwargs

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {"event_bundle": [], "feature_snapshot": {}}

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_INITIAL_MARKET_HISTORY_JSON": "{\"BTCUSDT\":[{\"price\":100,\"observed_at\":\"2026-04-17T09:00:00+00:00\"}]}",
            "TRADE_RUNTIME_MARKET_CONTEXT_HISTORY_LIMIT": "12",
        }
    )

    assert captured["assembler_kwargs"]["initial_market_context_history"] == {
        "BTCUSDT": [{"price": 100, "observed_at": "2026-04-17T09:00:00+00:00"}]
    }
    assert captured["assembler_kwargs"]["market_context_history_limit"] == 12


def test_build_runtime_app_passes_configured_market_history_limit_to_assembler(monkeypatch):
    captured = {}

    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = type("Scope", (), {"symbol": "ETHUSDT", "exchange_code": "binance"})()
        exchange_account_binding = None
        exchange_account = None
        news_api_config = None
        onchain_api_config = None
        social_api_config = None
        market_api_config = None
        market_data_config = type("MarketDataConfig", (), {"collect_onchain": "0", "collect_social": "0", "collect_news": "0"})()

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def get_bootstrap(self, symbol=None, exchange=None):
            return StubBootstrap()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            pass

    class StubRunner:
        def __init__(self, **kwargs):
            pass

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubRuntimeInputAssembler:
        def __init__(self, **kwargs):
            captured["assembler_kwargs"] = kwargs

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {"event_bundle": [], "feature_snapshot": {}}

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_MARKET_CONTEXT_HISTORY_LIMIT": "48",
        }
    )

    assert captured["assembler_kwargs"]["market_context_history_limit"] == 48


def test_build_runtime_app_uses_market_data_config_symbol_when_scope_missing(monkeypatch):
    class StubBootstrap:
        runtime_config = None
        strategy = None
        strategy_version = None
        symbol_scope = None
        exchange_account_binding = None
        exchange_account = None
        news_api_config = None
        onchain_api_config = None
        social_api_config = None
        market_api_config = None
        market_data_config = type("MarketDataConfig", (), {"symbol": "ETHUSDT", "collect_onchain": "0"})()

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def get_bootstrap(self, symbol=None, exchange=None):
            return StubBootstrap()

        def list_bootstraps(self):
            return []

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            pass

    class StubRunner:
        def __init__(self, **kwargs):
            pass

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubRuntimeInputAssembler:
        def __init__(self, **kwargs):
            pass

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {"event_bundle": [], "feature_snapshot": {"symbol": symbol}}

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    app = build_runtime_app({"TRADE_RUNTIME_BASE_URL": "http://localhost:8088"})

    assert app.symbol == "ETHUSDT"


def test_runtime_app_run_once_executes_all_runtime_contexts_when_supplier_returns_multiple_routes():
    captured = []

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            captured.append(
                {
                    "trace_id": trace_id,
                    "symbol": symbol,
                    "exchange": exchange,
                    "execution_router": self.execution_router,
                    "strategy_context": strategy_context,
                    "feature_snapshot": feature_snapshot,
                }
            )
            return {"symbol": symbol, "exchange": exchange}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="BTCUSDT",
                exchange="binance",
                execution_router="binance-router",
                strategy_context={"strategy_key": "btc-route"},
            ),
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route"},
            ),
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    result = app.run_once()

    assert len(captured) == 2
    assert captured[0]["symbol"] == "BTCUSDT"
    assert captured[0]["execution_router"] == "binance-router"
    assert captured[1]["symbol"] == "ETHUSDT"
    assert captured[1]["execution_router"] == "okx-router"
    assert result["results"] == [
        {"symbol": "BTCUSDT", "exchange": "binance"},
        {"symbol": "ETHUSDT", "exchange": "okx"},
    ]


def test_runtime_app_run_once_executes_multi_context_routes_concurrently_when_thread_pool_enabled():
    lock = threading.Lock()
    release = threading.Event()
    observed = {"active": 0, "max_active": 0}

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            with lock:
                observed["active"] += 1
                observed["max_active"] = max(observed["max_active"], observed["active"])
                if observed["active"] >= 2:
                    release.set()
            release.wait(timeout=0.3)
            with lock:
                observed["active"] -= 1
            return {"symbol": symbol, "exchange": exchange, "trace_id": trace_id}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="BTCUSDT",
                exchange="binance",
                execution_router="binance-router",
                strategy_context={"strategy_key": "btc-route"},
                runtime_config={"route_scheduler_mode": "THREAD_POOL", "route_max_concurrency": 2},
            ),
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route"},
                runtime_config={"route_scheduler_mode": "THREAD_POOL", "route_max_concurrency": 2},
            ),
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    result = app.run_once()

    assert observed["max_active"] == 2
    assert [item["symbol"] for item in result["results"]] == ["BTCUSDT", "ETHUSDT"]


def test_runtime_app_run_once_isolates_multi_context_failures_and_trace_ids_under_concurrency():
    captured_inputs = []
    trace_counter = {"value": 0}
    trace_lock = threading.Lock()

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            if symbol == "ETHUSDT":
                raise ValueError("route failed")
            return {
                "status": "ok",
                "symbol": symbol,
                "exchange": exchange,
                "trace_id": trace_id,
                "feature_snapshot": feature_snapshot,
            }

    def runtime_input_supplier(**kwargs):
        captured_inputs.append(
            {
                "symbol": kwargs["symbol"],
                "exchange": kwargs["exchange"],
                "trace_id": kwargs["trace_id"],
            }
        )
        return {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"route_symbol": kwargs["symbol"], "route_exchange": kwargs["exchange"]},
        }

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        trace_id_supplier=lambda: _next_trace_id(trace_counter, trace_lock),
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="BTCUSDT",
                exchange="binance",
                execution_router="binance-router",
                strategy_context={"strategy_key": "btc-route"},
                runtime_config={"route_scheduler_mode": "THREAD_POOL", "route_max_concurrency": 2},
            ),
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route"},
                runtime_config={"route_scheduler_mode": "THREAD_POOL", "route_max_concurrency": 2},
            ),
        ],
        runtime_input_supplier=runtime_input_supplier,
    )

    result = app.run_once()

    assert len({item["trace_id"] for item in captured_inputs}) == 2
    assert sorted(captured_inputs, key=lambda item: item["trace_id"]) == [
        {"symbol": "BTCUSDT", "exchange": "binance", "trace_id": "trace-1"},
        {"symbol": "ETHUSDT", "exchange": "okx", "trace_id": "trace-2"},
    ]
    assert result["results"][0]["trace_id"] == "trace-1"
    assert result["results"][0]["feature_snapshot"]["route_symbol"] == "BTCUSDT"
    assert result["results"][1] == {
        "status": "error",
        "symbol": "ETHUSDT",
        "exchange": "okx",
        "trace_id": "trace-2",
        "error": "route failed",
    }


def test_runtime_app_multi_route_persists_trigger_state_across_runs(monkeypatch):
    observed_trigger_states = []
    trace_counter = {"value": 0}
    trace_lock = threading.Lock()

    class StubRouteRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router
            self.trigger_state = {}

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            observed_trigger_states.append(
                {
                    "trace_id": trace_id,
                    "cooldowns": dict(self.trigger_state.get("cooldowns") or {}),
                    "dedupe": dict(self.trigger_state.get("dedupe") or {}),
                    "budget_state": dict(self.trigger_state.get("budget_state") or {}),
                }
            )
            next_trigger_state = {
                "cooldowns": {f"{symbol}:market:bearish": trace_id},
                "dedupe": {},
                "budget_state": {},
            }
            self.trigger_state = next_trigger_state
            return {
                "status": "ok",
                "symbol": symbol,
                "exchange": exchange,
                "trace_id": trace_id,
                "trigger_state": next_trigger_state,
            }

    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRouteRunner)

    class StubParentRunner:
        def __init__(self):
            self.config_client = object()
            self.callback_client = object()
            self.graph = object()
            self.execution_router = None
            self.memory_store = None
            self.decision_model_client = None
            self.trigger_state = {}

    app = TradeRuntimeApp(
        runner=StubParentRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        trace_id_supplier=lambda: _next_trace_id(trace_counter, trace_lock),
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route"},
                runtime_config={"route_scheduler_mode": "SERIAL"},
            )
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"symbol": kwargs["symbol"]},
        },
    )

    first = app.run_once()
    second = app.run_once()

    assert first["results"][0]["trace_id"] == "trace-1"
    assert second["results"][0]["trace_id"] == "trace-2"
    assert observed_trigger_states[0]["cooldowns"] == {}
    assert observed_trigger_states[1]["cooldowns"] == {"ETHUSDT:market:bearish": "trace-1"}
    assert app.runner.trigger_state["cooldowns"] == {"ETHUSDT:market:bearish": "trace-2"}


def test_runtime_app_multi_route_merges_concurrent_trigger_state_updates(monkeypatch):
    lock = threading.Lock()
    release = threading.Event()
    observed = {"active": 0}
    trace_counter = {"value": 0}
    trace_lock = threading.Lock()

    class StubRouteRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router
            self.trigger_state = {}

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            with lock:
                observed["active"] += 1
                if observed["active"] >= 2:
                    release.set()
            release.wait(timeout=0.5)
            next_trigger_state = {
                "cooldowns": {
                    **dict(self.trigger_state.get("cooldowns") or {}),
                    f"{symbol}:market:bearish": trace_id,
                },
                "dedupe": {},
                "budget_state": {
                    "symbol_dispatches": {symbol: [trace_id]},
                    "global_dispatches": [trace_id],
                },
            }
            self.trigger_state = next_trigger_state
            return {"status": "ok", "symbol": symbol, "exchange": exchange, "trace_id": trace_id}

    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRouteRunner)

    class StubParentRunner:
        def __init__(self):
            self.config_client = object()
            self.callback_client = object()
            self.graph = object()
            self.execution_router = None
            self.memory_store = None
            self.decision_model_client = None
            self.trigger_state = {}

    app = TradeRuntimeApp(
        runner=StubParentRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        trace_id_supplier=lambda: _next_trace_id(trace_counter, trace_lock),
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="BTCUSDT",
                exchange="binance",
                execution_router="binance-router",
                strategy_context={"strategy_key": "btc-route"},
                runtime_config={"route_scheduler_mode": "THREAD_POOL", "route_max_concurrency": 2},
            ),
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route"},
                runtime_config={"route_scheduler_mode": "THREAD_POOL", "route_max_concurrency": 2},
            ),
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"symbol": kwargs["symbol"]},
        },
    )

    app.run_once()

    assert app.runner.trigger_state["cooldowns"] == {
        "BTCUSDT:market:bearish": "trace-1",
        "ETHUSDT:market:bearish": "trace-2",
    }
    assert app.runner.trigger_state["budget_state"]["symbol_dispatches"] == {
        "BTCUSDT": ["trace-1"],
        "ETHUSDT": ["trace-2"],
    }
    assert sorted(app.runner.trigger_state["budget_state"]["global_dispatches"]) == ["trace-1", "trace-2"]


def test_runtime_app_multi_route_commits_trigger_state_when_route_fails(monkeypatch):
    trace_counter = {"value": 0}
    trace_lock = threading.Lock()

    class StubRouteRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router
            self.trigger_state = {}

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            self.trigger_state = {
                "cooldowns": {f"{symbol}:market:bearish": trace_id},
                "dedupe": {},
                "budget_state": {},
            }
            raise ValueError("route failed after trigger state update")

    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRouteRunner)

    class StubParentRunner:
        def __init__(self):
            self.config_client = object()
            self.callback_client = object()
            self.graph = object()
            self.execution_router = None
            self.memory_store = None
            self.decision_model_client = None
            self.trigger_state = {}

    app = TradeRuntimeApp(
        runner=StubParentRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        trace_id_supplier=lambda: _next_trace_id(trace_counter, trace_lock),
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route"},
                runtime_config={"route_scheduler_mode": "SERIAL"},
            )
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"symbol": kwargs["symbol"]},
        },
    )

    result = app.run_once()

    assert result["results"][0]["status"] == "error"
    assert app.runner.trigger_state["cooldowns"] == {"ETHUSDT:market:bearish": "trace-1"}


def test_runtime_app_multi_route_persists_position_risk_watcher_cooldowns(monkeypatch):
    observed_cooldowns = []
    trace_counter = {"value": 0}
    trace_lock = threading.Lock()

    class StubWatcher:
        def __init__(self):
            self._cooldowns = {}

    class StubRouteRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router
            self.trigger_state = {}
            self.position_risk_watcher = StubWatcher()

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            observed_cooldowns.append(dict(self.position_risk_watcher._cooldowns))
            self.position_risk_watcher._cooldowns[f"{symbol}:short:2353"] = {
                "triggered_at": trace_id,
                "severity_rank": 3,
            }
            return {"status": "ok", "symbol": symbol, "exchange": exchange, "trace_id": trace_id}

    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRouteRunner)

    class StubParentRunner:
        def __init__(self):
            self.config_client = object()
            self.callback_client = object()
            self.graph = object()
            self.execution_router = None
            self.memory_store = None
            self.decision_model_client = None
            self.trigger_state = {}
            self.position_risk_watcher = StubWatcher()

    app = TradeRuntimeApp(
        runner=StubParentRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        trace_id_supplier=lambda: _next_trace_id(trace_counter, trace_lock),
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route"},
                runtime_config={"route_scheduler_mode": "SERIAL"},
            )
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"symbol": kwargs["symbol"]},
        },
    )

    app.run_once()
    app.run_once()

    assert observed_cooldowns[0] == {}
    assert observed_cooldowns[1] == {
        "ETHUSDT:short:2353": {"triggered_at": "trace-1", "severity_rank": 3}
    }
    assert app.runner.position_risk_watcher._cooldowns == {
        "ETHUSDT:short:2353": {"triggered_at": "trace-2", "severity_rank": 3}
    }


def test_runtime_app_multi_route_binds_lifecycle_manager_per_route(monkeypatch):
    observed_model_ids = []
    trace_counter = {"value": 0}
    trace_lock = threading.Lock()

    class StubRouteRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router
            self.trigger_state = {}

        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot, strategy_context=None):
            observed_model_ids.append(getattr(getattr(self, "lifecycle_manager", None), "model_id", None))
            return {"status": "ok", "symbol": symbol, "exchange": exchange, "trace_id": trace_id}

    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRouteRunner)

    class StubLifecycleManager:
        def __init__(self, model_id):
            self.model_id = model_id

    class StubParentRunner:
        def __init__(self):
            self.config_client = object()
            self.callback_client = object()
            self.graph = object()
            self.execution_router = None
            self.memory_store = None
            self.decision_model_client = None
            self.trigger_state = {}
            self.lifecycle_manager = StubLifecycleManager(99)

    app = TradeRuntimeApp(
        runner=StubParentRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        trace_id_supplier=lambda: _next_trace_id(trace_counter, trace_lock),
        runtime_context_supplier=lambda: [
            RuntimeContext(
                symbol="BTCUSDT",
                exchange="binance",
                execution_router="binance-router",
                strategy_context={"strategy_key": "btc-route", "ai_model_config": {"id": 11}},
                runtime_config={"route_scheduler_mode": "SERIAL"},
            ),
            RuntimeContext(
                symbol="ETHUSDT",
                exchange="okx",
                execution_router="okx-router",
                strategy_context={"strategy_key": "eth-route", "ai_model_config": {"id": 22}},
                runtime_config={"route_scheduler_mode": "SERIAL"},
            ),
        ],
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"symbol": kwargs["symbol"]},
        },
    )

    app.run_once()

    assert observed_model_ids == [11, 22]
    assert app.runner.lifecycle_manager.model_id == 99


def _next_trace_id(counter, lock):
    with lock:
        counter["value"] += 1
        return f"trace-{counter['value']}"


def test_build_runtime_app_uses_multi_route_control_plane_when_symbol_and_exchange_not_pinned(monkeypatch):
    captured = {"runner_calls": []}

    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def list_bootstraps(self):
            return [
                type(
                    "Bootstrap",
                    (),
                    {
                        "runtime_config": None,
                        "strategy": type("Strategy", (), {"strategy_key": "btc-route", "strategy_name": "BTC"})(),
                        "strategy_version": type("Version", (), {"strategy_id": 1, "version_no": 2, "config_json": "{\"riskBudget\":0.02}"})(),
                        "symbol_scope": type("Scope", (), {"symbol": "BTCUSDT", "exchange_code": "binance"})(),
                        "exchange_account_binding": None,
                        "exchange_account": type("Account", (), {"exchange_code": "binance", "api_key_ciphertext": "ak", "api_secret_ciphertext": "sk", "testnet": True})(),
                    },
                )(),
                type(
                    "Bootstrap",
                    (),
                    {
                        "runtime_config": None,
                        "strategy": type("Strategy", (), {"strategy_key": "eth-route", "strategy_name": "ETH"})(),
                        "strategy_version": type("Version", (), {"strategy_id": 2, "version_no": 5, "config_json": "{\"riskBudget\":0.03}"})(),
                        "symbol_scope": type("Scope", (), {"symbol": "ETHUSDT", "exchange_code": "okx"})(),
                        "exchange_account_binding": None,
                        "exchange_account": type(
                            "Account",
                            (),
                            {
                                "exchange_code": "okx",
                                "api_key_ciphertext": "okx-ak",
                                "api_secret_ciphertext": "okx-sk",
                                "passphrase_ciphertext": "okx-pass",
                                "api_base_url": "https://okx.local",
                                "demo_trading": True,
                                "testnet": False,
                            },
                        )(),
                    },
                )(),
            ]

        def get_bootstrap(self, symbol=None, exchange=None):
            raise AssertionError("get_bootstrap should not be used when routes are not pinned")

        def get_config(self):
            return type("RuntimeConfig", (), {"effective_mode": lambda self: "shadow", "live_enabled": False})()

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            return None

    class StubRunner:
        def __init__(self, *, config_client, callback_client, graph=None, execution_router=None):
            self.execution_router = execution_router

        def run_once(
            self,
            *,
            trace_id,
            symbol,
            exchange,
            event_bundle,
            feature_snapshot,
            strategy_context=None,
            exchange_account=None,
        ):
            captured["runner_calls"].append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "execution_router": self.execution_router,
                    "strategy_context": strategy_context,
                    "feature_snapshot": feature_snapshot,
                    "exchange_account": exchange_account,
                }
            )
            return {"symbol": symbol, "exchange": exchange}

    class StubBinanceClient:
        def __init__(self, api_key, api_secret, testnet=False):
            pass

    class StubOkxClient:
        def __init__(self, api_key, api_secret, passphrase, base_url="https://www.okx.com", demo_trading=False):
            pass

    class StubMarketFeed:
        def __init__(self, exchange):
            self.exchange = exchange

        def fetch(self, symbol):
            return {"exchange": self.exchange, "symbol": symbol}

    class StubAuxSupplier:
        def __init__(self, url, timeout=5):
            pass

        def fetch(self, symbol):
            return []

    class StubRuntimeInputAssembler:
        def __init__(self, *, exchange, market_payload_supplier, **kwargs):
            self.exchange = exchange

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {
                "event_bundle": [{"event_type": "market_tick", "symbol": symbol, "exchange": self.exchange}],
                "feature_snapshot": {"assembler_exchange": self.exchange},
            }

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinanceRestExecutionClient", StubBinanceClient)
    monkeypatch.setattr("trade_runtime.app.OkxRestExecutionClient", StubOkxClient)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed("binance"))
    monkeypatch.setattr("trade_runtime.app.OkxPublicMarketFeed", lambda: StubMarketFeed("okx"))
    monkeypatch.setattr("trade_runtime.app.HttpJsonFeedSupplier", StubAuxSupplier)
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    app = build_runtime_app({"TRADE_RUNTIME_BASE_URL": "http://localhost:8088"})
    result = app.run_once()

    assert result["results"] == [
        {"symbol": "BTCUSDT", "exchange": "binance"},
        {"symbol": "ETHUSDT", "exchange": "okx"},
    ]
    assert [item["symbol"] for item in captured["runner_calls"]] == ["BTCUSDT", "ETHUSDT"]
    assert captured["runner_calls"][0]["strategy_context"]["strategy_key"] == "btc-route"
    assert captured["runner_calls"][1]["strategy_context"]["strategy_key"] == "eth-route"


def test_build_runtime_app_uses_default_symbol_for_unscoped_route(monkeypatch):
    class StubConfigClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def list_bootstraps(self):
            return [
                type(
                    "Bootstrap",
                    (),
                    {
                        "runtime_config": None,
                        "strategy": None,
                        "strategy_version": None,
                        "symbol_scope": None,
                        "exchange_account_binding": None,
                        "exchange_account": None,
                        "market_data_config": None,
                        "news_api_config": None,
                        "onchain_api_config": None,
                        "social_api_config": None,
                        "market_api_config": None,
                    },
                )()
            ]

        def get_bootstrap(self, symbol=None, exchange=None):
            raise AssertionError("get_bootstrap should not be used when routes are available")

    class StubCallbackClient:
        def __init__(self, base_url, bearer_token, timeout=5):
            pass

        def post_worker_heartbeat(self, worker_id):
            pass

    class StubRunner:
        def __init__(self, **kwargs):
            pass

    class StubMarketFeed:
        def fetch(self, symbol):
            return {"s": symbol, "p": "100.0", "q": "1.0"}

    class StubRuntimeInputAssembler:
        def __init__(self, **kwargs):
            pass

        def build(self, *, symbol, trace_id="", runtime_config=None, strategy_context=None):
            return {"event_bundle": [], "feature_snapshot": {"symbol": symbol}}

    monkeypatch.setattr("trade_runtime.app.RuntimeConfigClient", StubConfigClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeCallbackClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.RuntimeEventClient", StubCallbackClient)
    monkeypatch.setattr("trade_runtime.app.TradeRuntimeRunner", StubRunner)
    monkeypatch.setattr("trade_runtime.app.BinancePublicMarketFeed", lambda: StubMarketFeed())
    monkeypatch.setattr("trade_runtime.app.RuntimeInputAssembler", StubRuntimeInputAssembler)

    app = build_runtime_app(
        {
            "TRADE_RUNTIME_BASE_URL": "http://localhost:8088",
            "TRADE_RUNTIME_DEFAULT_SYMBOL": "ETHUSDT",
        }
    )

    assert app.symbol == "ETHUSDT"


def test_runtime_main_uses_requested_run_mode(monkeypatch):
    captured = {"mode": None}

    class StubApp:
        def run_once(self):
            captured["mode"] = "once"
            return {"mode": "once"}

        def run_forever(self, iterations=None):
            captured["mode"] = "forever"
            captured["iterations"] = iterations
            return {"mode": "forever"}

    monkeypatch.setattr("trade_runtime.app.build_runtime_app", lambda env=None: StubApp())

    result = main({"TRADE_RUNTIME_RUN_MODE": "forever"})

    assert captured["mode"] == "forever"
    assert captured["iterations"] is None
    assert result["mode"] == "forever"


def test_runtime_app_passes_runtime_account_context_to_runner():
    captured = {}

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(
            self,
            *,
            trace_id,
            symbol,
            exchange,
            event_bundle,
            feature_snapshot,
            strategy_context=None,
            runtime_account_context=None,
            market_source_status=None,
        ):
            captured["strategy_context"] = strategy_context
            captured["runtime_account_context"] = runtime_account_context
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="binance",
            execution_router="binance-router",
            strategy_context={"strategy_key": "btc-route"},
            runtime_account_context={
                "account_equity": 12345.0,
                "daily_pnl": 50.0,
                "current_position_side": "long",
                "current_position_quantity": 0.25,
                "current_position_notional": 16000.0,
                "consecutive_failures": 1,
            },
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    app.run_once()

    assert captured["strategy_context"]["strategy_key"] == "btc-route"
    assert captured["runtime_account_context"]["account_equity"] == 12345.0
    assert captured["runtime_account_context"]["current_position_side"] == "long"
    assert captured["runtime_account_context"]["consecutive_failures"] == 1


def test_runtime_app_passes_market_source_context_to_runner():
    captured = {}

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(
            self,
            *,
            trace_id,
            symbol,
            exchange,
            event_bundle,
            feature_snapshot,
            strategy_context=None,
            market_source_context=None,
            market_source_status=None,
        ):
            captured["strategy_context"] = strategy_context
            captured["market_source_context"] = market_source_context
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="binance",
            execution_router="binance-router",
            strategy_context={"strategy_key": "btc-route"},
            market_api_config=type(
                "MarketApiConfig",
                (),
                {
                    "id": 91,
                    "version_no": 4,
                    "update_time": "2026-04-17 10:15:00",
                    "transport_type": "WEBSOCKET",
                    "vendor_code": "BINANCE",
                },
            )(),
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    app.run_once()

    assert captured["strategy_context"]["strategy_key"] == "btc-route"
    assert captured["market_source_context"]["config_id"] == 91
    assert captured["market_source_context"]["config_version"] == 4
    assert captured["market_source_context"]["updated_at"] == "2026-04-17 10:15:00"


def test_runtime_app_triggers_position_guard_close_after_skip():
    captured = {"guard_orders": [], "position_payloads": [], "paper_trade_orders": [], "pnl_snapshots": []}

    class StubCallbackClient:
        def post_order_request(self, payload):
            captured["order_request"] = payload

        def post_exchange_order(self, payload):
            captured["exchange_order"] = payload

        def post_exchange_fill(self, payload):
            captured["exchange_fill"] = payload

        def post_position_snapshot(self, payload):
            captured["position_payloads"].append(payload)

        def post_paper_trade_order(self, payload):
            captured["paper_trade_orders"].append(payload)

        def post_pnl_snapshot(self, payload):
            captured["pnl_snapshots"].append(payload)

    class StubRunner:
        def __init__(self):
            self.execution_router = None
            self.callback_client = StubCallbackClient()

        def run_once(
            self,
            *,
            trace_id,
            symbol,
            exchange,
            event_bundle,
            feature_snapshot,
            strategy_context=None,
            runtime_account_context=None,
            market_source_status=None,
        ):
            return {
                "trace_id": trace_id,
                "symbol": symbol,
                "exchange": exchange,
                "supervisor_decision": {"action": "SKIP", "side": "flat", "size_hint": 0.0},
                "execution_result": {"status": "skipped", "order_status": "SKIPPED"},
            }

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["guard_orders"].append({"mode": mode, "exchange": exchange, "order": order})
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"guard-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 97.0,
                "fill_quantity": 1.0,
                "position_quantity": 0.0,
                "entry_price": 100.0,
            }

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="binance",
            execution_router=StubExecutionRouter(),
            strategy_context={
                "strategy_key": "btc-route",
                "position_guard": {
                    "enabled": True,
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.05,
                    "max_holding_minutes": 180,
                },
            },
            runtime_account_context={
                "account_equity": 10000.0,
                "daily_pnl": 0.0,
                "realized_pnl": 0.0,
                "current_position_side": "long",
                "current_position_quantity": 1.0,
                "current_position_notional": 100.0,
                "entry_price": 100.0,
                "entry_trace_id": "trace-open-1",
                "max_drawdown_pct": 0.0,
                "peak_account_equity": 10000.0,
                "current_position_opened_at": "2026-04-21 09:00:00",
                "consecutive_failures": 0,
            },
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"], "price": 97.0}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    result = app.run_once()

    assert result["position_guard_result"]["triggered"] is True
    assert result["position_guard_result"]["reason"] == "stop_loss_pct"
    assert captured["guard_orders"][-1]["order"]["side"] == "SELL"
    assert captured["guard_orders"][-1]["order"]["quote"] == 97.0
    assert captured["guard_orders"][-1]["order"]["action"] == "CLOSE"
    assert captured["guard_orders"][-1]["order"]["reduce_only"] is True
    assert captured["order_request"]["action"] == "CLOSE"
    assert captured["exchange_order"]["action"] == "CLOSE"
    assert captured["exchange_order"]["positionSide"] == "long"
    assert captured["exchange_order"]["reduceOnly"] is True
    assert captured["paper_trade_orders"][-1]["action"] == "CLOSE"
    assert captured["paper_trade_orders"][-1]["positionSide"] == "long"
    assert captured["paper_trade_orders"][-1]["reduceOnly"] is True
    assert captured["pnl_snapshots"][-1]["accountEquity"] == 9997.0
    assert captured["pnl_snapshots"][-1]["dailyPnl"] == -3.0
    assert captured["pnl_snapshots"][-1]["realizedPnl"] == -3.0
    assert captured["pnl_snapshots"][-1]["unrealizedPnl"] == 0.0
    assert captured["pnl_snapshots"][-1]["maxDrawdownPct"] == 0.03
    assert captured["pnl_snapshots"][-1]["peakAccountEquity"] == 10000.0
    assert captured["position_payloads"][-1]["positionQuantity"] == 0.0
    assert captured["position_payloads"][-1]["traceId"] == result["trace_id"]
    assert captured["position_payloads"][-1]["entryTraceId"] == "trace-open-1"


def test_runtime_app_does_not_zero_position_snapshot_when_guard_close_is_pending():
    captured = {"guard_orders": [], "position_payloads": []}

    class StubCallbackClient:
        def post_order_request(self, payload):
            captured["order_request"] = payload

        def post_exchange_order(self, payload):
            captured["exchange_order"] = payload

        def post_exchange_fill(self, payload):
            captured["exchange_fill"] = payload

        def post_position_snapshot(self, payload):
            captured["position_payloads"].append(payload)

    class StubRunner:
        def __init__(self):
            self.execution_router = None
            self.callback_client = StubCallbackClient()

        def run_once(
            self,
            *,
            trace_id,
            symbol,
            exchange,
            event_bundle,
            feature_snapshot,
            strategy_context=None,
            runtime_account_context=None,
            market_source_status=None,
        ):
            return {
                "trace_id": trace_id,
                "symbol": symbol,
                "exchange": exchange,
                "supervisor_decision": {"action": "SKIP", "side": "flat", "size_hint": 0.0},
                "execution_result": {"status": "skipped", "order_status": "SKIPPED"},
            }

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["guard_orders"].append({"mode": mode, "exchange": exchange, "order": order})
            return {
                "status": "pending",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"guard-{order['symbol']}",
                "order_status": "PENDING",
                "fill_price": 97.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 100.0,
            }

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="binance",
            execution_router=StubExecutionRouter(),
            strategy_context={
                "strategy_key": "btc-route",
                "position_guard": {
                    "enabled": True,
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.05,
                    "max_holding_minutes": 180,
                },
            },
            runtime_account_context={
                "account_equity": 12345.0,
                "daily_pnl": 50.0,
                "current_position_side": "long",
                "current_position_quantity": 1.0,
                "current_position_notional": 100.0,
                "current_position_opened_at": "2026-04-21 09:00:00",
                "consecutive_failures": 0,
            },
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"], "price": 97.0}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    result = app.run_once()

    assert result["position_guard_result"]["triggered"] is True
    assert result["position_guard_result"]["execution_result"]["status"] == "pending"
    assert captured["guard_orders"][-1]["order"]["side"] == "SELL"
    assert captured["position_payloads"] == []


def test_runtime_app_executes_position_risk_hard_close_without_position_guard_config():
    captured = {"guard_orders": []}

    class StubRunner:
        def __init__(self):
            self.execution_router = None
            self.callback_client = None

        def run_once(self, **kwargs):
            return {
                "trace_id": kwargs["trace_id"],
                "symbol": kwargs["symbol"],
                "exchange": kwargs["exchange"],
                "supervisor_decision": {"action": "HOLD", "side": "long", "size_hint": 0.0},
                "execution_result": {"status": "skipped", "order_status": "SKIPPED"},
                "position_risk_result": {
                    "triggered": True,
                    "action": "CLOSE",
                    "reason": "adverse_move_close",
                    "position_risk_context": {"current_price": 96.0},
                },
            }

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["guard_orders"].append({"mode": mode, "exchange": exchange, "order": order})
            return {"status": "filled", "order_status": "FILLED", "fill_price": 96.0, "fill_quantity": 1.0}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="binance",
            execution_router=StubExecutionRouter(),
            strategy_context={"strategy_key": "btc-route"},
            runtime_account_context={
                "current_position_side": "long",
                "current_position_quantity": 1.0,
                "current_position_notional": 100.0,
                "entry_price": 100.0,
            },
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [
                {"event_type": "market_tick", "symbol": kwargs["symbol"], "price": 100.0},
                {"event_type": "market_metric", "symbol": kwargs["symbol"], "effective_price": 96.0},
            ],
            "feature_snapshot": {"exchange": kwargs["exchange"], "effective_price": 96.0},
        },
    )

    result = app.run_once()

    assert result["position_risk_result"]["execution_result"]["status"] == "filled"
    assert captured["guard_orders"][-1]["order"]["side"] == "SELL"
    assert captured["guard_orders"][-1]["order"]["price"] == 96.0
    assert captured["guard_orders"][-1]["order"]["reason"] == "position_guard:position_risk:adverse_move_close"


def test_runtime_app_live_position_risk_hard_close_uses_live_route_without_paper_trade_orders():
    captured = {"guard_orders": [], "position_payloads": [], "paper_trade_orders": [], "pnl_snapshots": []}

    class StubCallbackClient:
        def post_order_request(self, payload):
            captured["order_request"] = payload

        def post_exchange_order(self, payload):
            captured["exchange_order"] = payload

        def post_exchange_fill(self, payload):
            captured["exchange_fill"] = payload

        def post_position_snapshot(self, payload):
            captured["position_payloads"].append(payload)

        def post_paper_trade_order(self, payload):
            captured["paper_trade_orders"].append(payload)

        def post_pnl_snapshot(self, payload):
            captured["pnl_snapshots"].append(payload)

    class StubRunner:
        def __init__(self):
            self.execution_router = None
            self.callback_client = StubCallbackClient()

        def run_once(self, **kwargs):
            return {
                "trace_id": kwargs["trace_id"],
                "symbol": kwargs["symbol"],
                "exchange": kwargs["exchange"],
                "mode": "live",
                "effective_mode": "live",
                "supervisor_decision": {"action": "HOLD", "side": "long", "size_hint": 0.0},
                "execution_result": {"status": "skipped", "order_status": "SKIPPED"},
                "position_risk_result": {
                    "triggered": True,
                    "action": "CLOSE",
                    "reason": "adverse_move_close",
                    "effective_mode": "live",
                    "live_enabled": True,
                    "position_risk_context": {"current_price": 96.0},
                },
            }

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["guard_orders"].append({"mode": mode, "exchange": exchange, "order": order})
            return {
                "status": "filled",
                "is_live": True,
                "exchange": exchange,
                "order_id": f"risk-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 96.0,
                "fill_quantity": 1.0,
                "position_quantity": 0.0,
                "entry_price": 100.0,
            }

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="okx",
            execution_router=StubExecutionRouter(),
            strategy_context={"strategy_key": "btc-route"},
            runtime_account_context={
                "account_equity": 10000.0,
                "daily_pnl": 0.0,
                "realized_pnl": 0.0,
                "current_position_side": "long",
                "current_position_quantity": 1.0,
                "current_position_notional": 100.0,
                "entry_price": 100.0,
                "max_drawdown_pct": 0.0,
                "peak_account_equity": 10000.0,
                "consecutive_failures": 0,
            },
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [
                {"event_type": "market_tick", "symbol": kwargs["symbol"], "price": 100.0},
                {"event_type": "market_metric", "symbol": kwargs["symbol"], "effective_price": 96.0},
            ],
            "feature_snapshot": {"exchange": kwargs["exchange"], "effective_price": 96.0},
        },
    )

    result = app.run_once()

    assert result["position_risk_result"]["execution_result"]["status"] == "filled"
    assert captured["guard_orders"][-1]["mode"] == "live"
    assert captured["guard_orders"][-1]["order"]["reason"] == "position_guard:position_risk:adverse_move_close"
    assert captured["exchange_order"]["action"] == "CLOSE"
    assert captured["exchange_fill"]["fillPrice"] == 96.0
    assert captured["paper_trade_orders"] == []
    assert captured["pnl_snapshots"][-1]["accountEquity"] == 9996.0
    assert captured["pnl_snapshots"][-1]["dailyPnl"] == -4.0
    assert captured["pnl_snapshots"][-1]["realizedPnl"] == -4.0
    assert result["position_risk_result"]["execution_result"]["account_equity"] == 9996.0
    assert captured["position_payloads"][-1]["positionQuantity"] == 0.0


def test_runtime_app_live_position_guard_close_uses_live_route_without_paper_trade_orders():
    captured = {"guard_orders": [], "position_payloads": [], "paper_trade_orders": [], "pnl_snapshots": []}

    class StubCallbackClient:
        def post_order_request(self, payload):
            captured["order_request"] = payload

        def post_exchange_order(self, payload):
            captured["exchange_order"] = payload

        def post_exchange_fill(self, payload):
            captured["exchange_fill"] = payload

        def post_position_snapshot(self, payload):
            captured["position_payloads"].append(payload)

        def post_paper_trade_order(self, payload):
            captured["paper_trade_orders"].append(payload)

        def post_pnl_snapshot(self, payload):
            captured["pnl_snapshots"].append(payload)

    class StubRunner:
        def __init__(self):
            self.execution_router = None
            self.callback_client = StubCallbackClient()

        def run_once(
            self,
            *,
            trace_id,
            symbol,
            exchange,
            event_bundle,
            feature_snapshot,
            strategy_context=None,
            runtime_account_context=None,
            market_source_status=None,
        ):
            return {
                "trace_id": trace_id,
                "symbol": symbol,
                "exchange": exchange,
                "mode": "live",
                "supervisor_decision": {"action": "SKIP", "side": "flat", "size_hint": 0.0},
                "execution_result": {"status": "skipped", "order_status": "SKIPPED"},
            }

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["guard_orders"].append({"mode": mode, "exchange": exchange, "order": order})
            return {
                "status": "filled",
                "is_live": True,
                "exchange": exchange,
                "order_id": f"guard-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 97.0,
                "fill_quantity": 1.0,
                "position_quantity": 0.0,
                "entry_price": 100.0,
            }

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        runtime_context_supplier=lambda: RuntimeContext(
            symbol="BTCUSDT",
            exchange="okx",
            execution_router=StubExecutionRouter(),
            strategy_context={
                "strategy_key": "btc-route",
                "position_guard": {
                    "enabled": True,
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.05,
                    "max_holding_minutes": 180,
                },
            },
            runtime_account_context={
                "account_equity": 10000.0,
                "daily_pnl": 0.0,
                "realized_pnl": 0.0,
                "current_position_side": "long",
                "current_position_quantity": 1.0,
                "current_position_notional": 100.0,
                "entry_price": 100.0,
                "max_drawdown_pct": 0.0,
                "peak_account_equity": 10000.0,
                "current_position_opened_at": "2026-04-21 09:00:00",
                "consecutive_failures": 0,
            },
        ),
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"], "price": 97.0}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
        },
    )

    result = app.run_once()

    assert result["position_guard_result"]["triggered"] is True
    assert captured["guard_orders"][-1]["mode"] == "live"
    assert captured["exchange_order"]["action"] == "CLOSE"
    assert captured["exchange_fill"]["fillPrice"] == 97.0
    assert captured["paper_trade_orders"] == []
    assert captured["pnl_snapshots"][-1]["accountEquity"] == 9997.0
    assert captured["pnl_snapshots"][-1]["dailyPnl"] == -3.0
    assert captured["pnl_snapshots"][-1]["realizedPnl"] == -3.0
    assert result["position_guard_result"]["execution_result"]["account_equity"] == 9997.0
    assert result["position_guard_result"]["execution_result"]["daily_pnl"] == -3.0
    assert result["position_guard_result"]["execution_result"]["realized_pnl"] == -3.0
    assert captured["position_payloads"][-1]["positionQuantity"] == 0.0


def test_runtime_app_passes_signal_window_states_to_runner():
    captured = {}

    class StubRunner:
        def __init__(self):
            self.execution_router = None

        def run_once(
            self,
            *,
            trace_id,
            symbol,
            exchange,
            event_bundle,
            feature_snapshot,
            signal_window_states=None,
            market_source_status=None,
        ):
            captured["signal_window_states"] = signal_window_states
            captured["market_source_status"] = market_source_status
            return {"status": "ok"}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="binance",
        runtime_input_supplier=lambda **kwargs: {
            "event_bundle": [{"event_type": "market_tick", "symbol": kwargs["symbol"]}],
            "feature_snapshot": {"exchange": kwargs["exchange"]},
            "signal_window_states": [
                {
                    "window_key": "news:BTCUSDT:15m",
                    "source_type": "news",
                    "signal_type": "headline",
                    "direction": "bullish",
                    "strength_score": 0.92,
                    "state": {"count": 1, "latest_headline": "ETF approval", "max_score": 0.92},
                }
            ],
            "market_source_status": "ready",
        },
    )

    app.run_once()

    assert captured["signal_window_states"][0]["source_type"] == "news"
    assert captured["signal_window_states"][0]["state"]["latest_headline"] == "ETF approval"
    assert captured["market_source_status"] == "ready"


def test_runtime_main_runs_trace_replay_when_requested(monkeypatch):
    captured = {}

    class StubReplayRunner:
        def run_trace(self, trace_id):
            captured["trace_id"] = trace_id
            return {"mode": "replay", "trace_id": trace_id}

    monkeypatch.setattr("trade_runtime.app.build_replay_runner", lambda env=None: StubReplayRunner())

    result = main(
        {
            "TRADE_RUNTIME_RUN_MODE": "replay",
            "TRADE_RUNTIME_REPLAY_TRACE_ID": "trace-source-1",
        }
    )

    assert captured["trace_id"] == "trace-source-1"
    assert result["mode"] == "replay"


def test_runtime_app_run_forever_consumes_runtime_replay_task():
    captured = {"heartbeats": [], "sleep": []}

    class StubRunner:
        def run_once(self, *, trace_id, symbol, exchange, event_bundle, feature_snapshot):
            return {"status": "ok"}

    class StubReplayRunner:
        def run_trace(self, trace_id, session_id=None):
            captured["replay_call"] = {"trace_id": trace_id, "session_id": session_id}
            return {"success": True, "session_id": session_id, "source_trace_id": trace_id}

    class StubTaskClient:
        def __init__(self):
            self.tasks = [
                {
                    "taskId": "task-replay-1",
                    "taskType": "TRADE_RUNTIME_REPLAY",
                    "taskData": {"sourceTraceId": "trace-source-1", "sessionId": 18},
                }
            ]

        def pull_task(self, worker_id):
            captured["pull_worker_id"] = worker_id
            if self.tasks:
                return self.tasks.pop(0)
            return None

        def save_task_result(self, task_id, result):
            captured["saved_result"] = {"task_id": task_id, "result": result}

        def update_task_status(self, task_id, status, result=""):
            captured.setdefault("status_updates", []).append(
                {"task_id": task_id, "status": status, "result": result}
            )

    app = TradeRuntimeApp(
        runner=StubRunner(),
        worker_id="runtime-worker-1",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle_supplier=lambda: [{"event_type": "market_tick"}],
        feature_snapshot_supplier=lambda: {"price_change_pct": 0.5},
        heartbeat_publisher=captured["heartbeats"].append,
        task_client=StubTaskClient(),
        replay_runner=StubReplayRunner(),
        sleep=captured["sleep"].append,
    )

    result = app.run_forever(iterations=1)

    assert captured["pull_worker_id"] == "runtime-worker-1"
    assert captured["replay_call"] == {"trace_id": "trace-source-1", "session_id": 18}
    assert captured["saved_result"]["task_id"] == "task-replay-1"
    assert captured["status_updates"][-1]["status"] == "completed"
    assert result["status"] == "ok"
