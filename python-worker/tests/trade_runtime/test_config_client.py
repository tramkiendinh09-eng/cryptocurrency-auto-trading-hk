from trade_runtime.config_client import RuntimeConfigClient


def test_build_runtime_headers_uses_bearer_token():
    client = RuntimeConfigClient(base_url="http://localhost:8080", bearer_token="abc")

    assert client.build_headers()["Authorization"] == "Bearer abc"


def test_get_config_parses_runtime_risk_thresholds(monkeypatch):
    captured = {}

    class StubResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 200,
                "data": {
                    "defaultMode": "SHADOW",
                    "liveEnabled": False,
                    "maxPositionRatio": 0.35,
                    "maxDailyLoss": -650.0,
                    "maxConsecutiveFailures": 5,
                    "routeMaxConcurrency": 3,
                    "routeSchedulerMode": "THREAD_POOL",
                },
            }

    def stub_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return StubResponse()

    monkeypatch.setattr("trade_runtime.config_client.requests.get", stub_get)

    client = RuntimeConfigClient(base_url="http://localhost:8080", bearer_token="abc", timeout=4)
    runtime_config = client.get_config()

    assert captured["url"] == "http://localhost:8080/dca/trade/runtime/config"
    assert runtime_config.default_mode == "shadow"
    assert runtime_config.max_position_ratio == 0.35
    assert runtime_config.max_daily_loss == -650.0
    assert runtime_config.max_consecutive_failures == 5
    assert runtime_config.route_max_concurrency == 3
    assert runtime_config.route_scheduler_mode == "THREAD_POOL"


def test_get_config_parses_runtime_whitelist_and_account_health_flag(monkeypatch):
    class StubResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 200,
                "data": {
                    "defaultMode": "PAPER",
                    "allowedSymbolsJson": "[\"BTCUSDT\", \" ethusdt \"]",
                    "allowedExchangesJson": "[\"binance\", \"OKX\"]",
                    "liveOrderRequiresHealthyAccount": False,
                },
            }

    def stub_get(url, headers, timeout):
        return StubResponse()

    monkeypatch.setattr("trade_runtime.config_client.requests.get", stub_get)

    client = RuntimeConfigClient(base_url="http://localhost:8080", bearer_token="abc", timeout=4)
    runtime_config = client.get_config()

    assert runtime_config.allowed_symbols == ["BTCUSDT", "ETHUSDT"]
    assert runtime_config.allowed_exchanges == ["BINANCE", "OKX"]
    assert runtime_config.live_order_requires_healthy_account is False


def test_get_bootstrap_parses_strategy_scope_and_exchange_account(monkeypatch):
    captured = {}

    class StubResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 200,
                "data": {
                    "runtimeConfig": {
                        "defaultMode": "SHADOW",
                        "liveEnabled": False,
                    },
                    "strategy": {
                        "id": 9,
                        "strategyKey": "event-btc",
                        "strategyName": "BTC Event Runtime",
                        "runtimeMode": "SHADOW",
                        "enabled": True,
                    },
                    "strategyVersion": {
                        "id": 11,
                        "strategyId": 9,
                        "versionNo": 3,
                        "configJson": "{\"riskBudget\":0.02}",
                    },
                    "symbolScope": {
                        "strategyId": 9,
                        "symbol": "BTCUSDT",
                        "exchangeCode": "binance",
                    },
                    "exchangeAccountBinding": {
                        "strategyId": 9,
                        "accountId": 21,
                        "exchangeCode": "binance",
                        "enabled": True,
                    },
                    "exchangeAccount": {
                        "id": 21,
                        "exchangeCode": "binance",
                        "accountName": "Primary Binance",
                        "apiKeyCiphertext": "ak-runtime",
                        "apiSecretCiphertext": "sk-runtime",
                        "testnet": True,
                        "healthStatus": "healthy",
                        "lastValidatedAt": "2026-04-17 09:30:00",
                    },
                    "aiModelConfig": {
                        "id": 31,
                        "modelCode": "gpt-4.1",
                        "modelName": "Runtime Default",
                        "provider": "openai",
                        "apiBaseUrl": "https://api.openai.internal",
                    },
                    "newsApiConfig": {
                        "id": 41,
                        "dataCategory": "NEWS",
                        "apiName": "NEWS_FEED",
                        "apiUrl": "https://feeds.internal/news",
                    },
                    "onchainApiConfig": {
                        "id": 42,
                        "dataCategory": "ONCHAIN",
                        "apiName": "ONCHAIN_FEED",
                        "apiUrl": "https://feeds.internal/onchain",
                    },
                    "socialApiConfig": {
                        "id": 43,
                        "dataCategory": "SOCIAL",
                        "apiName": "SOCIAL_FEED",
                        "apiUrl": "https://feeds.internal/social",
                    },
                    "marketApiConfig": {
                        "id": 44,
                        "versionNo": 4,
                        "dataCategory": "PRICE",
                        "transportType": "WEBSOCKET",
                        "vendorCode": "BINANCE",
                        "marketScope": "FUTURES",
                        "apiName": "BINANCE_FUTURES_TICKER_WS",
                        "wsBaseUrl": "wss://fstream.binance.com",
                        "wsPath": "/stream",
                        "wsStreamNameTemplate": "{symbol_lower}@ticker",
                        "wsCombinedEnabled": True,
                        "wsSymbolLowercase": True,
                        "wsPingIntervalSeconds": 20,
                        "wsPongTimeoutSeconds": 60,
                        "wsConnectionTtlHours": 24,
                        "wsMaxStreamsPerConnection": 1024,
                        "wsControlMessagesPerSecond": 5,
                        "updateTime": "2026-04-17 10:15:00",
                        "docReferenceUrl": "https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams",
                    },
                    "marketDataConfig": {
                        "id": 51,
                        "configName": "BTC Runtime Inputs",
                        "symbol": "BTCUSDT",
                        "enabled": "1",
                        "collectInterval": 15,
                        "dataSources": "[\"binance\",\"rss\",\"whale-alert\"]",
                        "collectOnchain": "1",
                    },
                    "runtimeAccountContext": {
                        "accountEquity": 12000.5,
                        "dailyPnl": 125.25,
                        "realizedPnl": 235.75,
                        "unrealizedPnl": -18.5,
                        "currentPositionSide": "long",
                        "currentPositionQuantity": 0.12,
                        "currentPositionNotional": 7800.0,
                        "entryPrice": 65000.0,
                        "maxDrawdownPct": 4.25,
                        "peakAccountEquity": 12544.2,
                        "currentPositionOpenedAt": "2026-04-21 09:15:00",
                        "currentTime": "2026-04-21 10:15:00",
                        "currentPositionHoldingMinutes": 60,
                        "consecutiveFailures": 2,
                    },
                    "positionGuard": {
                        "id": 301,
                        "guardName": "btc-default-guard",
                        "scopeType": "SYMBOL",
                        "strategyId": 9,
                        "symbol": "BTCUSDT",
                        "exchangeCode": "BINANCE",
                        "stopLossPct": 0.02,
                        "takeProfitPct": 0.05,
                        "maxHoldingMinutes": 180,
                        "enabled": True,
                    },
                    "promptBindings": [
                        {
                            "id": 101,
                            "bindingName": "Supervisor Prompt",
                            "bindingScope": "SUPERVISOR",
                            "templateCode": "trade.supervisor.v1",
                            "fallbackTemplateCode": "trade.supervisor.fallback",
                            "modelId": 31,
                            "outputSchemaCode": "supervisor_decision_v1",
                            "priority": 10,
                            "modeScopeJson": "[\"shadow\"]",
                            "eventStrengthScopeJson": "[\"strong\",\"normal\"]",
                            "enabled": True,
                        }
                    ],
                    "agentProfiles": [
                        {
                            "id": 201,
                            "agentCode": "supervisor_agent",
                            "agentName": "Supervisor",
                            "agentType": "LLM",
                            "enabled": True,
                            "llmEnabled": True,
                            "dialogueEnabled": False,
                            "maxDialogueRounds": 0,
                            "speakOrder": 1,
                            "timeoutSeconds": 45,
                            "maxRetries": 2,
                            "structuredSchemaCode": "supervisor_decision_v1",
                            "toolPolicyJson": "{}",
                            "runtimeOptionsJson": "{}",
                        }
                    ],
                    "resolvedAgentConfigs": [
                        {
                            "agentCode": "supervisor_agent",
                            "agentType": "LLM",
                            "enabled": True,
                            "llmEnabled": True,
                            "modelId": 31,
                            "modelCode": "gpt-4.1",
                            "modelProvider": "openai",
                            "templateCode": "trade.supervisor.v1",
                            "fallbackTemplateCode": "trade.supervisor.fallback",
                            "outputSchemaCode": "supervisor_decision_v1",
                            "resolutionSource": "PROFILE_DEFAULT",
                        }
                    ],
                    "deliberationPolicy": {
                        "enabled": True,
                        "maxRounds": 1,
                        "failOpen": True,
                    },
                },
            }

    def stub_get(url, headers, params, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["timeout"] = timeout
        return StubResponse()

    monkeypatch.setattr("trade_runtime.config_client.requests.get", stub_get)

    client = RuntimeConfigClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    bootstrap = client.get_bootstrap(symbol="BTCUSDT", exchange="binance")

    assert captured["url"] == "http://localhost:8080/dca/trade/runtime/bootstrap"
    assert captured["params"] == {"symbol": "BTCUSDT", "exchange": "binance"}
    assert bootstrap.runtime_config.default_mode == "shadow"
    assert bootstrap.strategy.strategy_key == "event-btc"
    assert bootstrap.symbol_scope.symbol == "BTCUSDT"
    assert bootstrap.exchange_account.account_name == "Primary Binance"
    assert bootstrap.exchange_account.testnet is True
    assert bootstrap.exchange_account.health_status == "healthy"
    assert bootstrap.exchange_account.last_validated_at == "2026-04-17 09:30:00"
    assert bootstrap.ai_model_config.model_code == "gpt-4.1"
    assert bootstrap.news_api_config.api_url == "https://feeds.internal/news"
    assert bootstrap.onchain_api_config.api_url == "https://feeds.internal/onchain"
    assert bootstrap.social_api_config.api_url == "https://feeds.internal/social"
    assert bootstrap.market_api_config.transport_type == "WEBSOCKET"
    assert bootstrap.market_api_config.vendor_code == "BINANCE"
    assert bootstrap.market_api_config.version_no == 4
    assert bootstrap.market_api_config.market_scope == "FUTURES"
    assert bootstrap.market_api_config.ws_base_url == "wss://fstream.binance.com"
    assert bootstrap.market_api_config.ws_path == "/stream"
    assert bootstrap.market_api_config.ws_stream_name_template == "{symbol_lower}@ticker"
    assert bootstrap.market_api_config.ws_combined_enabled is True
    assert bootstrap.market_api_config.ws_symbol_lowercase is True
    assert bootstrap.market_api_config.ws_connection_ttl_hours == 24
    assert bootstrap.market_api_config.update_time == "2026-04-17 10:15:00"
    assert bootstrap.market_data_config.symbol == "BTCUSDT"
    assert bootstrap.market_data_config.collect_onchain == "1"
    assert bootstrap.market_data_config.collect_interval == 15
    assert bootstrap.runtime_account_context.account_equity == 12000.5
    assert bootstrap.runtime_account_context.daily_pnl == 125.25
    assert bootstrap.runtime_account_context.realized_pnl == 235.75
    assert bootstrap.runtime_account_context.unrealized_pnl == -18.5
    assert bootstrap.runtime_account_context.current_position_side == "long"
    assert bootstrap.runtime_account_context.current_position_quantity == 0.12
    assert bootstrap.runtime_account_context.current_position_notional == 7800.0
    assert bootstrap.runtime_account_context.entry_price == 65000.0
    assert bootstrap.runtime_account_context.max_drawdown_pct == 4.25
    assert bootstrap.runtime_account_context.peak_account_equity == 12544.2
    assert bootstrap.runtime_account_context.current_time == "2026-04-21 10:15:00"
    assert bootstrap.runtime_account_context.current_position_holding_minutes == 60
    runtime_account_payload = bootstrap.runtime_account_context.model_dump(by_alias=True)
    assert runtime_account_payload["currentPositionOpenedAt"] == "2026-04-21 09:15:00"
    assert runtime_account_payload["currentTime"] == "2026-04-21 10:15:00"
    assert runtime_account_payload["currentPositionHoldingMinutes"] == 60
    assert bootstrap.runtime_account_context.consecutive_failures == 2
    bootstrap_payload = bootstrap.model_dump(by_alias=True)
    assert bootstrap_payload["positionGuard"] == {
        "id": 301,
        "guardName": "btc-default-guard",
        "scopeType": "SYMBOL",
        "strategyId": 9,
        "symbol": "BTCUSDT",
        "exchangeCode": "binance",
        "stopLossPct": 0.02,
        "takeProfitPct": 0.05,
        "maxHoldingMinutes": 180,
        "enabled": True,
    }
    assert bootstrap.prompt_bindings[0].binding_scope == "SUPERVISOR"
    assert bootstrap.prompt_bindings[0].template_code == "trade.supervisor.v1"
    assert bootstrap.prompt_bindings[0].model_id == 31
    assert bootstrap.agent_profiles[0].agent_code == "supervisor_agent"
    assert bootstrap.agent_profiles[0].structured_schema_code == "supervisor_decision_v1"
    assert bootstrap.resolved_agent_configs[0].agent_code == "supervisor_agent"
    assert bootstrap.resolved_agent_configs[0].model_code == "gpt-4.1"
    assert bootstrap.resolved_agent_configs[0].template_code == "trade.supervisor.v1"
    assert bootstrap.deliberation_policy == {
        "enabled": True,
        "maxRounds": 1,
        "failOpen": True,
    }


def test_list_bootstraps_parses_multiple_runtime_routes(monkeypatch):
    captured = {}

    class StubResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 200,
                "data": [
                    {
                        "runtimeConfig": {"defaultMode": "SHADOW", "liveEnabled": False},
                        "symbolScope": {"symbol": "BTCUSDT", "exchangeCode": "binance"},
                        "exchangeAccount": {"exchangeCode": "binance", "accountName": "binance-main"},
                    },
                    {
                        "runtimeConfig": {"defaultMode": "SHADOW", "liveEnabled": False},
                        "symbolScope": {"symbol": "ETHUSDT", "exchangeCode": "okx"},
                        "exchangeAccount": {"exchangeCode": "okx", "accountName": "okx-main"},
                    },
                ],
            }

    def stub_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return StubResponse()

    monkeypatch.setattr("trade_runtime.config_client.requests.get", stub_get)

    client = RuntimeConfigClient(base_url="http://localhost:8080", bearer_token="abc", timeout=4)
    bootstraps = client.list_bootstraps()

    assert captured["url"] == "http://localhost:8080/dca/trade/runtime/routes"
    assert len(bootstraps) == 2
    assert bootstraps[0].symbol_scope.symbol == "BTCUSDT"
    assert bootstraps[1].symbol_scope.exchange_code == "okx"
