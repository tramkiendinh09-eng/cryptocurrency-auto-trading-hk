from trade_runtime.config import RuntimeConfig
from trade_runtime.execution.router import ExecutionRouter
from trade_runtime.runtime_runner import TradeRuntimeRunner


def test_runtime_runner_keeps_noise_events_in_no_dispatch_mode():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="shadow", liveEnabled=False)

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
        trace_id="trace-trigger-noise",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 0.4, "event_strength": "noise"},
        signal_window_states=[],
    )

    assert result["dispatch_mode"] == "NO_DISPATCH"
    assert result["should_dispatch"] is False
    assert result["selected_agents"] == []
    assert result["trigger_reason"] == "noise_threshold_not_met"
    assert runner.trigger_state["budget_state"] == {}


def test_runtime_runner_routes_normal_events_to_rule_only_without_budget_consumption():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson="""
                {
                  "newsTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7},
                  "llmBudgetPolicy":{"perSymbolDailyLimit":2,"perSymbolWindowLimit":1,"windowSeconds":3600}
                }
                """,
            )

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
        trace_id="trace-trigger-rule-only",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF desk rumor", "score": 0.76}],
        feature_snapshot={"symbol": "BTCUSDT", "news_score": 0.76, "event_strength": "normal"},
        signal_window_states=[],
    )

    assert result["dispatch_mode"] == "RULE_ONLY"
    assert result["llm_allowed"] is False
    assert result["should_dispatch"] is True
    assert result["trigger_source"] == "news"
    assert result["selected_agents"] == ["market_agent", "news_agent"]
    assert runner.trigger_state["budget_state"] == {}


def test_runtime_runner_injects_position_risk_event_and_bypasses_trigger_guards():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson="""
                {
                  "positionRiskWatcher":{"enabled":true,"reviewAdverseMovePct":0.5,"cooldownSeconds":30},
                  "llmBudgetPolicy":{"perSymbolDailyLimit":0,"rollingWindowLimit":0,"rollingWindowMinutes":20}
                }
                """,
            )

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
        trace_id="trace-position-risk",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 100.0}],
        feature_snapshot={"symbol": "BTCUSDT", "effective_price": 99.0, "event_strength": "noise"},
        runtime_account_context={
            "current_position_side": "long",
            "current_position_quantity": 1.0,
            "entry_price": 100.0,
        },
        signal_window_states=[],
    )

    assert result["position_risk_result"]["triggered"] is True
    assert result["dispatch_mode"] == "LLM_ALLOWED"
    assert result["llm_allowed"] is True
    assert result["budget_blocked"] is False
    assert result["trigger_source"] == "position_risk"
    assert result["selected_agents"] == ["market_agent"]
    assert result["feature_snapshot"]["position_risk_context"]["adverse_move_pct"] == 1.0
    assert any(event.get("event_type") == "position_risk" for event in result["event_bundle"])


def test_runtime_runner_tags_live_position_risk_event_with_effective_mode():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="live",
                liveEnabled=True,
                runtimeFlagsJson="""
                {
                  "positionRiskWatcher":{"enabled":true,"reviewAdverseMovePct":0.5,"cooldownSeconds":30},
                  "llmBudgetPolicy":{"perSymbolDailyLimit":0,"rollingWindowLimit":0,"rollingWindowMinutes":20}
                }
                """,
            )

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
        trace_id="trace-live-position-risk",
        symbol="BTCUSDT",
        exchange="okx",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "exchange": "okx", "price": 100.0}],
        feature_snapshot={"symbol": "BTCUSDT", "exchange": "okx", "effective_price": 99.0, "event_strength": "noise"},
        runtime_account_context={
            "current_position_side": "long",
            "current_position_quantity": 1.0,
            "entry_price": 100.0,
        },
        signal_window_states=[],
    )

    risk_event = next(event for event in result["event_bundle"] if event.get("event_type") == "position_risk")
    assert result["mode"] == "live"
    assert result["exchange"] == "okx"
    assert result["position_risk_result"]["effective_mode"] == "live"
    assert result["position_risk_result"]["live_enabled"] is True
    assert result["position_risk_result"]["exchange"] == "okx"
    assert risk_event["effective_mode"] == "live"
    assert risk_event["live_enabled"] is True
    assert risk_event["exchange"] == "okx"
    assert result["dispatch_mode"] == "LLM_ALLOWED"
    assert result["budget_blocked"] is False


def test_runtime_runner_injects_mode_and_callback_client_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                maxPositionRatio=0.35,
                maxDailyLoss=-650.0,
                maxConsecutiveFailures=5,
            )

    class StubCallbackClient:
        pass

    class StubGraph:
        def __init__(self):
            self.invoked_state = None

        def invoke(self, state):
            self.invoked_state = state
            return {
                **state,
                "supervisor_decision": {"action": "OPEN_LONG", "confidence": 82},
            }

    graph = StubGraph()
    callback_client = StubCallbackClient()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=callback_client,
        graph=graph,
    )

    result = runner.run_once(
        trace_id="trace-9",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 6.2},
    )

    assert graph.invoked_state["trace_id"] == "trace-9"
    assert graph.invoked_state["mode"] == "shadow"
    assert graph.invoked_state["callback_client"] is callback_client
    assert graph.invoked_state["runtime_config"]["max_position_ratio"] == 0.35
    assert graph.invoked_state["runtime_config"]["max_daily_loss"] == -650.0
    assert graph.invoked_state["runtime_config"]["max_consecutive_failures"] == 5
    assert result["supervisor_decision"]["action"] == "OPEN_LONG"


def test_runtime_runner_records_lifecycle_entry_from_execution_result_price():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

    class StubGraph:
        def invoke(self, state):
            return {
                **state,
                "supervisor_decision": {
                    "action": "OPEN_LONG",
                    "side": "long",
                    "confidence": 82,
                    "summary_reason": "breakout_confirmed",
                },
                "execution_result": {
                    "status": "filled",
                    "order_status": "FILLED",
                    "entry_price": 101.5,
                    "fill_price": 101.5,
                    "fill_quantity": 1.0,
                },
            }

    class StubLifecycleManager:
        def __init__(self):
            self.entries = []

        def record_entry(self, **kwargs):
            self.entries.append(kwargs)
            return kwargs

        def record_exit(self, **kwargs):
            raise AssertionError("record_exit should not be called for OPEN_LONG")

    lifecycle_manager = StubLifecycleManager()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=StubGraph(),
        lifecycle_manager=lifecycle_manager,
    )

    runner.run_once(
        trace_id="trace-lifecycle-open",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 101.5}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 1.2},
        runtime_account_context={
            "current_position_side": "flat",
            "current_position_quantity": 0.0,
            "entry_price": 0.0,
        },
        signal_window_states=[],
    )

    assert lifecycle_manager.entries == [
        {
            "trace_id": "trace-lifecycle-open",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "side": "long",
            "entry_price": 101.5,
            "supervisor_decision": {
                "action": "OPEN_LONG",
                "side": "long",
                "confidence": 82,
                "summary_reason": "breakout_confirmed",
            },
            "agent_views": {
                "market_view": None,
                "news_view": None,
                "onchain_view": None,
                "social_view": None,
            },
            "feature_snapshot": {"symbol": "BTCUSDT", "price_change_pct": 1.2, "event_strength": "normal"},
        }
    ]


def test_runtime_runner_surfaces_lifecycle_and_trade_memory_status_for_close_flow():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

    class StubGraph:
        def invoke(self, state):
            return {
                **state,
                "supervisor_decision": {
                    "action": "CLOSE",
                    "side": "short",
                    "confidence": 78,
                    "summary_reason": "invalidated_short",
                },
                "execution_result": {
                    "status": "filled",
                    "order_status": "FILLED",
                    "fill_price": 2144.19,
                    "fill_quantity": 0.3,
                },
            }

    class StubLifecycleManager:
        def record_exit(self, **kwargs):
            assert kwargs["trace_id"] == "trace-open-1"
            return {
                "status": "recorded",
                "operation": "exit",
                "trace_id": "trace-open-1",
                "memory_status": "stored",
                "memory_reason": "",
                "memory": {
                    "lesson_text": "Only close the full short after support reclaim confirms invalidation."
                },
            }

    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=StubGraph(),
        lifecycle_manager=StubLifecycleManager(),
    )

    result = runner.run_once(
        trace_id="trace-close-1",
        symbol="ETHUSDT",
        exchange="okx",
        event_bundle=[{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2144.19}],
        feature_snapshot={"symbol": "ETHUSDT", "price_change_pct": 1.8},
        runtime_account_context={
            "current_position_side": "short",
            "current_position_quantity": 0.3,
            "entry_trace_id": "trace-open-1",
        },
        signal_window_states=[],
    )

    assert result["lifecycle_status"]["status"] == "recorded"
    assert result["lifecycle_status"]["operation"] == "exit"
    assert result["lifecycle_status"]["trace_id"] == "trace-open-1"
    assert result["trade_memory_status"]["status"] == "stored"
    assert result["trade_memory_status"]["reason"] == ""
    assert result["trade_memory_status"]["lesson_text"] == "Only close the full short after support reclaim confirms invalidation."


def test_runtime_runner_exposes_lifecycle_manager_to_graph_and_skips_duplicate_post_processing():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

    class StubGraph:
        def __init__(self):
            self.invoked_state = None

        def invoke(self, state):
            self.invoked_state = state
            return {
                **state,
                "supervisor_decision": {
                    "action": "CLOSE",
                    "side": "long",
                    "summary_reason": "take_profit_hit",
                },
                "execution_result": {
                    "status": "filled",
                    "order_status": "FILLED",
                    "fill_price": 103.2,
                    "fill_quantity": 0.25,
                },
                "lifecycle_status": {
                    "status": "recorded",
                    "operation": "exit",
                    "trace_id": "trace-open-1",
                    "memory_status": "stored",
                    "memory_reason": "",
                    "memory": {"lesson_text": "Let profit targets complete before trimming."},
                },
                "trade_memory_status": {
                    "status": "stored",
                    "reason": "",
                    "trace_id": "trace-open-1",
                    "lesson_text": "Let profit targets complete before trimming.",
                },
            }

    class StubLifecycleManager:
        def __init__(self):
            self.exit_calls = 0

        def record_exit(self, **kwargs):
            self.exit_calls += 1
            return {"status": "recorded", "operation": "exit", "trace_id": kwargs["trace_id"]}

    graph = StubGraph()
    lifecycle_manager = StubLifecycleManager()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
        lifecycle_manager=lifecycle_manager,
    )

    result = runner.run_once(
        trace_id="trace-close-2",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 103.2}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 1.1},
        runtime_account_context={
            "current_position_side": "long",
            "current_position_quantity": 0.25,
            "entry_trace_id": "trace-open-1",
        },
        signal_window_states=[],
    )

    assert graph.invoked_state["lifecycle_manager"] is lifecycle_manager
    assert lifecycle_manager.exit_calls == 0
    assert result["lifecycle_status"]["trace_id"] == "trace-open-1"
    assert result["trade_memory_status"]["status"] == "stored"


def test_runtime_runner_propagates_runtime_whitelist_defaults_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="shadow", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-runtime-whitelist",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 0.8},
    )

    assert graph.invoked_state["runtime_config"]["allowed_symbols"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert graph.invoked_state["runtime_config"]["allowed_exchanges"] == ["BINANCE", "OKX"]
    assert graph.invoked_state["runtime_config"]["live_order_requires_healthy_account"] is True


def test_runtime_runner_normalizes_mode_and_blocks_live_when_live_disabled():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode=" LIVE ", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-live-disabled",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
    )

    assert graph.invoked_state["mode"] == "shadow"
    assert graph.invoked_state["requested_mode"] == "live"
    assert graph.invoked_state["effective_mode"] == "shadow"
    assert graph.invoked_state["mode_downgraded"] is True
    assert graph.invoked_state["live_enabled"] is False


def test_runtime_runner_injects_execution_router_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="live", liveEnabled=True)

    class StubGraph:
        def __init__(self):
            self.invoked_state = None

        def invoke(self, state):
            self.invoked_state = state
            return state

    execution_router = ExecutionRouter(binance_client=object(), okx_client=None)
    graph = StubGraph()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
        execution_router=execution_router,
    )

    runner.run_once(
        trace_id="trace-live-router",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
    )

    assert graph.invoked_state["mode"] == "live"
    assert graph.invoked_state["execution_router"] is execution_router


def test_runtime_runner_injects_decision_model_client_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="shadow", liveEnabled=False)

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
    runner.decision_model_client = object()

    runner.run_once(
        trace_id="trace-model-client",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
    )

    assert graph.invoked_state["decision_model_client"] is runner.decision_model_client


def test_runtime_runner_injects_strategy_context_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-strategy-context",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
        strategy_context={
            "strategy_key": "event-btc",
            "strategy_version": 3,
            "strategy_config": {"riskBudget": 0.02},
        },
    )

    assert graph.invoked_state["strategy_context"]["strategy_key"] == "event-btc"
    assert graph.invoked_state["strategy_context"]["strategy_version"] == 3
    assert graph.invoked_state["strategy_context"]["strategy_config"]["riskBudget"] == 0.02


def test_runtime_runner_promotes_prompt_bindings_and_agent_profiles_into_state():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-prompt-state",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
        strategy_context={
            "strategy_key": "event-btc",
            "prompt_bindings": [{"binding_scope": "SUPERVISOR", "template_code": "trade.supervisor.v1"}],
            "agent_profiles": [{"agent_code": "supervisor_agent", "agent_type": "LLM"}],
        },
    )

    assert graph.invoked_state["prompt_bindings"][0]["binding_scope"] == "SUPERVISOR"
    assert graph.invoked_state["prompt_bindings"][0]["template_code"] == "trade.supervisor.v1"
    assert graph.invoked_state["agent_profiles"][0]["agent_code"] == "supervisor_agent"
    assert graph.invoked_state["agent_profiles"][0]["agent_type"] == "LLM"


def test_runtime_runner_promotes_deliberation_policy_into_state():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-deliberation-policy",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
        strategy_context={
            "strategy_key": "event-btc",
            "deliberation_policy": {"enabled": True, "maxRounds": 1, "failOpen": True},
        },
    )

    assert graph.invoked_state["deliberation_policy"] == {
        "enabled": True,
        "maxRounds": 1,
        "failOpen": True,
    }


def test_runtime_runner_injects_market_source_context_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-market-source-context",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
        market_source_context={
            "config_id": 91,
            "config_version": 4,
            "updated_at": "2026-04-17 10:15:00",
            "transport_type": "WEBSOCKET",
            "vendor_code": "BINANCE",
        },
    )

    assert graph.invoked_state["market_source_context"]["config_id"] == 91
    assert graph.invoked_state["market_source_context"]["config_version"] == 4
    assert graph.invoked_state["market_source_context"]["updated_at"] == "2026-04-17 10:15:00"


def test_runtime_runner_allows_forced_mode_override_for_replay():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="live", liveEnabled=True)

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

    runner.run_once(
        trace_id="trace-replay-1",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "news", "headline": "ETF inflow"}],
        feature_snapshot={"news_score": 0.91},
        mode_override="shadow",
    )

    assert graph.invoked_state["mode"] == "shadow"
    assert graph.invoked_state["requested_mode"] == "shadow"
    assert graph.invoked_state["effective_mode"] == "shadow"
    assert graph.invoked_state["mode_downgraded"] is False


def test_runtime_runner_prefers_strategy_runtime_mode_but_keeps_runtime_risk_limits():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="paper",
                liveEnabled=False,
                maxPositionRatio=0.4,
                maxDailyLoss=-500.0,
                maxConsecutiveFailures=3,
            )

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

    runner.run_once(
        trace_id="trace-strategy-overrides",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "news"}],
        feature_snapshot={"news_score": 0.95},
        strategy_context={
            "runtime_mode": "live",
            "strategy_config": {
                "riskConfig": {
                    "maxPositionRatio": 0.18,
                    "maxDailyLoss": -250.0,
                    "maxConsecutiveFailures": 6,
                }
            },
        },
    )

    assert graph.invoked_state["mode"] == "shadow"
    assert graph.invoked_state["runtime_config"]["max_position_ratio"] == 0.4
    assert graph.invoked_state["runtime_config"]["max_daily_loss"] == -500.0
    assert graph.invoked_state["runtime_config"]["max_consecutive_failures"] == 3


def test_runtime_runner_injects_runtime_account_context_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="shadow", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-runtime-account-context",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
        runtime_account_context={
            "account_equity": 12500.5,
            "daily_pnl": -45.6,
            "realized_pnl": 321.25,
            "unrealized_pnl": -18.75,
            "current_position_side": "long",
            "current_position_quantity": 0.15,
            "current_position_notional": 9750.0,
            "entry_price": 65000.0,
            "max_drawdown_pct": 4.25,
            "peak_account_equity": 13055.75,
            "consecutive_failures": 2,
        },
    )

    assert graph.invoked_state["account_equity"] == 12500.5
    assert graph.invoked_state["daily_pnl"] == -45.6
    assert graph.invoked_state["realized_pnl"] == 321.25
    assert graph.invoked_state["unrealized_pnl"] == -18.75
    assert graph.invoked_state["current_position_side"] == "long"
    assert graph.invoked_state["current_position_quantity"] == 0.15
    assert graph.invoked_state["current_position_notional"] == 9750.0
    assert graph.invoked_state["entry_price"] == 65000.0
    assert graph.invoked_state["max_drawdown_pct"] == 4.25
    assert graph.invoked_state["peak_account_equity"] == 13055.75
    assert graph.invoked_state["consecutive_failures"] == 2


def test_runtime_runner_injects_exchange_account_health_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="live", liveEnabled=True, liveOrderRequiresHealthyAccount=True)

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

    runner.run_once(
        trace_id="trace-exchange-account-health",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick"}],
        feature_snapshot={"price_change_pct": 1.2},
        exchange_account={
            "exchangeCode": "binance",
            "accountName": "binance-live",
            "healthStatus": "healthy",
            "lastValidatedAt": "2026-04-17 09:30:00",
        },
    )

    assert graph.invoked_state["exchange_account"]["health_status"] == "healthy"
    assert graph.invoked_state["exchange_account"]["last_validated_at"] == "2026-04-17 09:30:00"
    assert graph.invoked_state["runtime_config"]["live_order_requires_healthy_account"] is True


def test_runtime_runner_injects_trigger_policy_decision_into_graph():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson="""
                {
                  "newsTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7},
                  "llmBudgetPolicy":{"perSymbolDailyLimit":4,"perSymbolWindowLimit":2,"windowSeconds":3600}
                }
                """,
            )

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

    runner.run_once(
        trace_id="trace-trigger-policy",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF approval", "score": 0.95}],
        feature_snapshot={"symbol": "BTCUSDT", "news_score": 0.95, "event_strength": "strong"},
        signal_window_states=[],
    )

    assert graph.invoked_state["dispatch_mode"] == "LLM_ALLOWED"
    assert graph.invoked_state["llm_allowed"] is True
    assert graph.invoked_state["should_dispatch"] is True
    assert graph.invoked_state["trigger_source"] == "news"
    assert graph.invoked_state["selected_agents"] == ["market_agent", "news_agent"]
    assert graph.invoked_state["budget_blocked"] is False
    assert graph.invoked_state["cooldown_blocked"] is False


def test_runtime_runner_applies_cooldown_then_budget_downgrade_across_invocations():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson="""
                {
                  "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
                  "cooldownPolicy":{"globalSeconds":180},
                  "llmBudgetPolicy":{"perSymbolDailyLimit":1,"perSymbolWindowLimit":1,"windowSeconds":3600}
                }
                """,
            )

    class StubGraph:
        def __init__(self):
            self.invoked_states = []

        def invoke(self, state):
            self.invoked_states.append(state)
            return state

    graph = StubGraph()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
    )

    first = runner.run_once(
        trace_id="trace-trigger-budget-1",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 3.2, "event_strength": "strong"},
        evaluation_time="2026-04-17T08:00:00+00:00",
    )
    second = runner.run_once(
        trace_id="trace-trigger-budget-2",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65100.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 3.1, "event_strength": "strong"},
        evaluation_time="2026-04-17T08:01:00+00:00",
    )
    third = runner.run_once(
        trace_id="trace-trigger-budget-3",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65200.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 3.0, "event_strength": "strong"},
        evaluation_time="2026-04-17T08:05:00+00:00",
    )

    assert first["dispatch_mode"] == "LLM_ALLOWED"
    assert second["dispatch_mode"] == "RULE_ONLY"
    assert second["cooldown_blocked"] is True
    assert second["budget_blocked"] is False
    assert third["dispatch_mode"] == "RULE_ONLY"
    assert third["cooldown_blocked"] is False
    assert third["budget_blocked"] is True
    assert third["rule_only_reason"] == "budget_blocked"


def test_runtime_runner_upgrades_news_then_market_window_to_llm_dispatch():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson="""
                {
                  "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
                  "triggerMatrix":[
                    {"code":"strong_news_then_break","sources":["news","market"],"targetDispatchMode":"LLM_ALLOWED"}
                  ],
                  "llmBudgetPolicy":{"perSymbolDailyLimit":3,"perSymbolWindowLimit":2,"windowSeconds":3600}
                }
                """,
            )

    class StubGraph:
        def __init__(self):
            self.invoked_states = []

        def invoke(self, state):
            self.invoked_states.append(state)
            return state

    graph = StubGraph()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
    )

    first = runner.run_once(
        trace_id="trace-trigger-combo-1",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF approval watch", "score": 0.82}],
        feature_snapshot={"symbol": "BTCUSDT", "news_score": 0.82, "event_strength": "normal"},
        evaluation_time="2026-04-17T08:00:00+00:00",
    )
    second = runner.run_once(
        trace_id="trace-trigger-combo-2",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 66200.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 1.4, "event_strength": "normal"},
        signal_window_states=first["active_signals"],
        evaluation_time="2026-04-17T08:03:00+00:00",
    )

    assert first["dispatch_mode"] == "RULE_ONLY"
    assert second["dispatch_mode"] == "LLM_ALLOWED"
    assert second["trigger_source"] == "combination"
    assert second["combination_match"]["code"] == "strong_news_then_break"
    assert second["selected_agents"] == ["market_agent", "news_agent"]


def test_runtime_runner_upgrades_onchain_social_market_confirmation_with_strategy_routing():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson="""
                {
                  "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
                  "socialTrigger":{"scoreThreshold":0.85,"ruleOnlyScoreThreshold":0.65},
                  "onchainTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7,"flowUsdThreshold":1000000,"ruleOnlyFlowUsdThreshold":250000},
                  "triggerMatrix":[
                    {"code":"onchain_social_market_confirmation","sources":["onchain","social","market"],"targetDispatchMode":"LLM_ALLOWED"}
                  ],
                  "llmBudgetPolicy":{"perSymbolDailyLimit":3,"perSymbolWindowLimit":2,"windowSeconds":3600}
                }
                """,
            )

    class StubGraph:
        def __init__(self):
            self.invoked_states = []

        def invoke(self, state):
            self.invoked_states.append(state)
            return state

    graph = StubGraph()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
    )

    first = runner.run_once(
        trace_id="trace-trigger-onchain-1",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_outflow", "amountUsd": 450000}],
        feature_snapshot={"symbol": "BTCUSDT", "onchain_flow_bias": 0.78, "event_strength": "normal"},
        strategy_context={
            "strategy_config": {
                "specialistRouting": {
                    "onchain_social_market_confirmation": ["market_agent", "onchain_agent", "social_agent"]
                }
            }
        },
        evaluation_time="2026-04-17T08:00:00+00:00",
    )
    second = runner.run_once(
        trace_id="trace-trigger-onchain-2",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[
            {"event_type": "social", "symbol": "BTCUSDT", "score": 0.74},
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 66150.0},
        ],
        feature_snapshot={
            "symbol": "BTCUSDT",
            "social_score": 0.74,
            "price_change_pct": 1.5,
            "event_strength": "normal",
        },
        signal_window_states=first["active_signals"],
        strategy_context={
            "strategy_config": {
                "specialistRouting": {
                    "onchain_social_market_confirmation": ["market_agent", "onchain_agent", "social_agent"]
                }
            }
        },
        evaluation_time="2026-04-17T08:06:00+00:00",
    )

    assert first["dispatch_mode"] == "RULE_ONLY"
    assert second["dispatch_mode"] == "LLM_ALLOWED"
    assert second["trigger_source"] == "combination"
    assert second["combination_match"]["code"] == "onchain_social_market_confirmation"
    assert second["selected_agents"] == ["market_agent", "onchain_agent", "social_agent"]


def test_runtime_runner_bypass_trigger_guards_preserves_replay_dispatch_outside_live_cooldown_and_budget():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson="""
                {
                  "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
                  "cooldownPolicy":{"globalSeconds":180,"replayBypass":true},
                  "llmBudgetPolicy":{"perSymbolDailyLimit":1,"perSymbolWindowLimit":1,"windowSeconds":3600}
                }
                """,
            )

    class StubGraph:
        def __init__(self):
            self.invoked_states = []

        def invoke(self, state):
            self.invoked_states.append(state)
            return state

    graph = StubGraph()
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
    )

    first = runner.run_once(
        trace_id="trace-trigger-replay-1",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 3.2, "event_strength": "strong"},
        evaluation_time="2026-04-17T08:00:00+00:00",
    )
    live_trigger_state = {
        "cooldowns": dict(runner.trigger_state["cooldowns"]),
        "dedupe": dict(runner.trigger_state["dedupe"]),
        "budget_state": {
            "symbol_dispatches": dict(runner.trigger_state["budget_state"]["symbol_dispatches"]),
            "global_dispatches": list(runner.trigger_state["budget_state"]["global_dispatches"]),
        },
        # 每小时保底的计时点。回放不该推进它——推进了就等于一次回放吃掉
        # 线上一小时的保底额度。
        "last_llm_dispatch_at": runner.trigger_state.get("last_llm_dispatch_at", ""),
    }
    live_floor_at = runner.trigger_state.get("last_llm_dispatch_at", "")

    second = runner.run_once(
        trace_id="trace-trigger-replay-2",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65100.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 3.1, "event_strength": "strong"},
        evaluation_time="2026-04-17T08:01:00+00:00",
        mode_override="shadow",
        bypass_trigger_guards=True,
    )

    assert first["dispatch_mode"] == "LLM_ALLOWED"
    assert second["dispatch_mode"] == "LLM_ALLOWED"
    assert second["cooldown_blocked"] is False
    assert runner.trigger_state.get("last_llm_dispatch_at", "") == live_floor_at, (
        "回放推进了线上的保底计时器"
    )
    assert second["budget_blocked"] is False
    assert runner.trigger_state == live_trigger_state


def test_runtime_runner_overwrites_inconsistent_snapshot_event_strength():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson='{"marketTrigger":{"ruleOnlyPriceChangePct":1.0,"priceChangePct":2.5}}',
            )

    class StubGraph:
        def invoke(self, state):
            return state

    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=StubGraph(),
    )

    result = runner.run_once(
        trace_id="trace-strength-sync",
        symbol="BTCUSDT",
        exchange="binance",
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 1.2, "event_strength": "noise"},
        signal_window_states=[],
    )

    assert result["feature_snapshot"]["event_strength"] == "normal"


def test_runtime_runner_injects_memory_store_into_state():
    from trade_runtime.memory.long_term import InMemoryLongTermMemoryStore

    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

    class StubGraph:
        def __init__(self):
            self.invoked_state = None

        def invoke(self, state):
            self.invoked_state = state
            return state

    graph = StubGraph()
    memory_store = InMemoryLongTermMemoryStore([])
    runner = TradeRuntimeRunner(
        config_client=StubConfigClient(),
        callback_client=object(),
        graph=graph,
        memory_store=memory_store,
    )

    runner.run_once(
        trace_id="trace-memory-store",
        symbol="BTCUSDT",
        exchange="okx",
        event_bundle=[],
        feature_snapshot={},
        signal_window_states=[],
    )

    assert graph.invoked_state["memory_store"] is memory_store


def test_runtime_runner_injects_current_time_and_holding_minutes_into_state():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-current-time-holding-minutes",
        symbol="ETHUSDT",
        exchange="okx",
        event_bundle=[{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2400.0}],
        feature_snapshot={"symbol": "ETHUSDT", "price_change_pct": 0.4},
        signal_window_states=[],
        runtime_account_context={
            "current_position_side": "short",
            "current_position_quantity": 0.30826727,
            "current_position_opened_at": "2026-05-06 21:09:34",
        },
        evaluation_time="2026-05-07T09:09:34+00:00",
    )

    assert graph.invoked_state["current_position_opened_at"] == "2026-05-06 21:09:34"
    assert graph.invoked_state["current_time"] == "2026-05-07T09:09:34Z"
    assert graph.invoked_state["current_position_holding_minutes"] == 720
    assert graph.invoked_state["runtime_account_context"]["current_time"] == "2026-05-07T09:09:34Z"
    assert graph.invoked_state["runtime_account_context"]["current_position_holding_minutes"] == 720


def test_runtime_runner_prefers_runtime_account_time_context():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-runtime-account-time-context",
        symbol="ETHUSDT",
        exchange="okx",
        event_bundle=[{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2400.0}],
        feature_snapshot={"symbol": "ETHUSDT", "price_change_pct": 0.4},
        signal_window_states=[],
        runtime_account_context={
            "currentPositionSide": "short",
            "currentPositionQuantity": 0.30826727,
            "currentPositionOpenedAt": "2026-05-07 09:00:00",
            "currentTime": "2026-05-07 10:15:00",
            "currentPositionHoldingMinutes": "75.0",
        },
        evaluation_time="2026-05-07T01:15:00+00:00",
    )

    assert graph.invoked_state["current_position_opened_at"] == "2026-05-07 09:00:00"
    assert graph.invoked_state["current_time"] == "2026-05-07 10:15:00"
    assert graph.invoked_state["current_position_holding_minutes"] == 75
    assert graph.invoked_state["runtime_account_context"]["current_time"] == "2026-05-07 10:15:00"


def test_runtime_runner_treats_zero_quantity_position_as_flat():
    class StubConfigClient:
        def get_config(self):
            return RuntimeConfig(defaultMode="paper", liveEnabled=False)

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

    runner.run_once(
        trace_id="trace-zero-position-flat",
        symbol="ETHUSDT",
        exchange="okx",
        event_bundle=[{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2400.0}],
        feature_snapshot={"symbol": "ETHUSDT", "price_change_pct": 0.4},
        signal_window_states=[],
        runtime_account_context={
            "currentPositionSide": "short",
            "currentPositionQuantity": 0,
            "currentPositionNotional": 0,
            "currentPositionOpenedAt": "2026-05-07 09:00:00",
        },
        evaluation_time="2026-05-07T10:15:00+00:00",
    )

    assert graph.invoked_state["current_position_side"] == "flat"
    assert graph.invoked_state["current_position_quantity"] == 0
    assert graph.invoked_state["current_position_opened_at"] is None
    assert graph.invoked_state.get("current_position_holding_minutes") is None
    assert graph.invoked_state["runtime_account_context"]["current_position_side"] == "flat"
    assert graph.invoked_state["runtime_account_context"]["current_position_opened_at"] is None
