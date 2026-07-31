from trade_runtime.decision.nodes.audit import audit_node
from trade_runtime.decision.nodes.build_feature_snapshot import build_feature_snapshot_node
from trade_runtime.decision.nodes.execution_node import execution_node


def test_audit_node_emits_decision_and_pnl_callbacks_when_client_present():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []
            self.pnl_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

        def post_pnl_snapshot(self, payload):
            self.pnl_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = audit_node(
        {
            "trace_id": "trace-2",
            "symbol": "ETHUSDT",
            "mode": "paper",
            "event_strength": "strong",
            "feature_snapshot": {
                "price_change_pct": 6.4,
                "news_score": 0.82,
                "event_strength": "strong",
            },
            "signal_window_states": [
                {
                    "window_key": "news:ETHUSDT:15m",
                    "state": {"count": 2, "max_score": 0.82},
                }
            ],
            "supervisor_decision": {
                "action": "OPEN_LONG",
                "confidence": 88,
                "model_code": "gpt-4.1",
                "model_provider": "openai",
            },
            "supervisor_prompt_metadata": {
                "prompt_source": "template",
                "binding_template_code": "trade.supervisor.v1",
                "fallback_template_code": "trade.supervisor.fallback",
                "resolved_template_code": "trade.supervisor.v1",
                "prompt_template_fallback_used": False,
            },
            "event_bundle": [
                {"event_type": "news", "headline": "ETF inflow", "score": 0.82},
                {"event_type": "social", "score": 0.77},
            ],
            "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_change_pct=6.4"},
            "news_view": {"bias": "bullish", "confidence": 82, "reason": "ETF inflow"},
            "onchain_view": {"bias": "neutral", "confidence": 60, "reason": "no_onchain_signal"},
            "agent_messages": [
                {
                    "round_no": 0,
                    "speaker_agent": "market_agent",
                    "target_agent": "news_agent",
                    "message_type": "proposal",
                    "summary_text": "market stays bearish on price weakness",
                    "content": {"stance": "maintain"},
                }
            ],
            "execution_result": {
                "status": "filled",
                "order_status": "FILLED",
                "account_equity": 12000.0,
                "daily_pnl": 140.5,
                "max_drawdown_pct": 3.2,
                "peak_account_equity": 12140.5,
                "unrealized_pnl": 22.4,
                "realized_pnl": 118.1,
            },
            "callback_client": callback_client,
        }
    )

    assert state["audit_payload"]["trace_id"] == "trace-2"
    assert callback_client.decision_payloads[0]["traceId"] == "trace-2"
    assert callback_client.decision_payloads[0]["signalEvents"][0]["traceId"] == "trace-2"
    assert callback_client.decision_payloads[0]["signalEvents"][0]["symbol"] == "ETHUSDT"
    assert callback_client.decision_payloads[0]["signalEvents"][0]["signalType"] == "news"
    assert callback_client.decision_payloads[0]["signalEvents"][0]["score"] == 0.82
    assert callback_client.decision_payloads[0]["signalEvents"][0]["featureJson"] == (
        '{"event_type":"news","headline":"ETF inflow","score":0.82}'
    )
    assert callback_client.decision_payloads[0]["agentConclusions"][0]["traceId"] == "trace-2"
    assert callback_client.decision_payloads[0]["agentConclusions"][0]["agentName"] == "market"
    assert callback_client.decision_payloads[0]["agentConclusions"][0]["bias"] == "bullish"
    assert callback_client.decision_payloads[0]["agentConclusions"][0]["confidence"] == 80
    assert callback_client.decision_payloads[0]["agentConclusions"][0]["reason"] == "price_change_pct=6.4"
    assert callback_client.decision_payloads[0]["modelCode"] == "gpt-4.1"
    assert callback_client.decision_payloads[0]["modelProvider"] == "openai"
    assert callback_client.decision_payloads[0]["promptSource"] == "template"
    assert callback_client.decision_payloads[0]["bindingTemplateCode"] == "trade.supervisor.v1"
    assert callback_client.decision_payloads[0]["fallbackTemplateCode"] == "trade.supervisor.fallback"
    assert callback_client.decision_payloads[0]["resolvedTemplateCode"] == "trade.supervisor.v1"
    assert callback_client.decision_payloads[0]["promptTemplateFallbackUsed"] is False
    assert callback_client.decision_payloads[0]["executionStatus"] == "filled"
    assert callback_client.decision_payloads[0]["orderStatus"] == "FILLED"
    assert callback_client.decision_payloads[0]["eventStrength"] == "strong"
    assert callback_client.decision_payloads[0]["featureSnapshot"]["price_change_pct"] == 6.4
    assert callback_client.decision_payloads[0]["signalWindowStates"][0]["windowKey"] == "news:ETHUSDT:15m"
    assert callback_client.decision_payloads[0]["signalWindowStates"][0]["stateJson"] == '{"count":2,"max_score":0.82}'
    assert callback_client.decision_payloads[0]["agentRuns"][0]["agentName"] == "market"
    assert callback_client.decision_payloads[0]["agentRuns"][0]["status"] == "completed"
    assert callback_client.decision_payloads[0]["agentRuns"][0]["eventStrength"] == "strong"
    assert callback_client.decision_payloads[0]["agentObservations"][0]["agentName"] == "market"
    assert callback_client.decision_payloads[0]["agentObservations"][0]["observationType"] == "feature_context"
    assert callback_client.decision_payloads[0]["agentObservations"][0]["observationJson"] == (
        '{"feature_snapshot":{"event_strength":"strong","news_score":0.82,"price_change_pct":6.4}}'
    )
    assert callback_client.decision_payloads[0]["agentMessages"][0]["speakerAgent"] == "market_agent"
    assert callback_client.decision_payloads[0]["agentMessages"][0]["messageType"] == "proposal"
    assert callback_client.decision_payloads[0]["agentMessages"][0]["contentJson"] == (
        '{"speaker_agent":"market_agent","stance":"maintain","target_agent":"news_agent"}'
    )
    assert callback_client.decision_payloads[0]["decisionActions"][0]["traceId"] == "trace-2"
    assert callback_client.decision_payloads[0]["decisionActions"][0]["action"] == "OPEN_LONG"
    assert callback_client.decision_payloads[0]["decisionActions"][0]["executionStatus"] == "filled"
    assert callback_client.decision_payloads[0]["decisionActions"][0]["orderStatus"] == "FILLED"
    assert callback_client.pnl_payloads[0]["mode"] == "paper"
    assert callback_client.pnl_payloads[0]["maxDrawdownPct"] == 3.2
    assert callback_client.pnl_payloads[0]["peakAccountEquity"] == 12140.5


def test_audit_node_fills_agent_message_model_and_template_from_resolved_config():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

    callback_client = StubCallbackClient()
    audit_node(
        {
            "trace_id": "trace-agent-message-resolved-metadata",
            "symbol": "BTCUSDT",
            "mode": "paper",
            "event_strength": "strong",
            "feature_snapshot": {},
            "supervisor_decision": {"action": "SKIP", "confidence": 0},
            "agent_messages": [
                {
                    "round_no": 0,
                    "speaker_agent": "market_agent",
                    "target_agent": "supervisor_agent",
                    "message_type": "conclusion",
                    "content": {"bias": "bullish"},
                }
            ],
            "resolved_agent_configs": [
                {
                    "agent_code": "market_agent",
                    "template_code": "trade.market.v1",
                    "model_code": "deepseek-reasoner",
                }
            ],
            "callback_client": callback_client,
        }
    )

    message = callback_client.decision_payloads[0]["agentMessages"][0]
    assert message["templateCode"] == "trade.market.v1"
    assert message["modelCode"] == "deepseek-reasoner"
    assert message["contentJson"] == (
        '{"bias":"bullish","model_code":"deepseek-reasoner","speaker_agent":"market_agent",'
        '"target_agent":"supervisor_agent","template_code":"trade.market.v1"}'
    )


def test_audit_node_keeps_deliberation_transcript_and_referee_review():
    from trade_runtime.decision.nodes.audit import _build_decision_payload

    payload = _build_decision_payload(
        {
            "trace_id": "trace-deliberation-audit",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "dispatch_mode": "LLM_ALLOWED",
            "selected_agents": ["market_agent", "onchain_agent"],
            "agent_profiles": [
                {"agent_code": "market_agent", "enabled": True},
                {"agent_code": "news_agent", "enabled": True},
                {"agent_code": "onchain_agent", "enabled": True},
            ],
            "supervisor_decision": {"action": "HOLD", "confidence": 70, "summary_reason": "supervisor_final"},
            "agent_messages": [
                {
                    "round_no": 0,
                    "speaker_agent": "market_agent",
                    "target_agent": "",
                    "message_type": "proposal",
                    "content": {"bias": "bullish"},
                },
                {
                    "round_no": 0,
                    "speaker_agent": "onchain_agent",
                    "target_agent": "",
                    "message_type": "proposal",
                    "content": {"bias": "bearish"},
                },
                {
                    "round_no": 1,
                    "speaker_agent": "onchain_agent",
                    "target_agent": "market_agent",
                    "message_type": "challenge",
                    "content": {"challenger_bias": "bearish", "target_bias": "bullish"},
                },
                {
                    "round_no": 1,
                    "speaker_agent": "market_agent",
                    "target_agent": "onchain_agent",
                    "message_type": "revision",
                    "content": {"stance": "maintain", "bias": "bullish"},
                },
                {
                    "round_no": 1,
                    "speaker_agent": "orchestrator",
                    "target_agent": "",
                    "message_type": "summary",
                    "content": {"conflict": True},
                    "summary_text": "conflicting_specialist_views_detected",
                },
                {
                    "round_no": 2,
                    "speaker_agent": "deliberation_referee",
                    "target_agent": "supervisor_agent",
                    "message_type": "referee_review",
                    "template_code": "trade.deliberation_referee.v1",
                    "model_code": "gpt-referee",
                    "content": {"action": "HOLD", "summary_reason": "referee_advice"},
                },
                {
                    "round_no": 0,
                    "speaker_agent": "news_agent",
                    "target_agent": "supervisor_agent",
                    "message_type": "conclusion",
                    "content": {"bias": "bearish"},
                },
            ],
        }
    )

    messages = payload["agentMessages"]
    assert [message["messageType"] for message in messages] == [
        "proposal",
        "proposal",
        "challenge",
        "revision",
        "summary",
        "referee_review",
    ]
    assert messages[-1]["speakerAgent"] == "deliberation_referee"
    assert messages[-1]["targetAgent"] == "supervisor_agent"
    assert messages[-1]["templateCode"] == "trade.deliberation_referee.v1"
    assert "referee_advice" in messages[-1]["contentJson"]


def test_audit_node_normalizes_null_decision_fields_for_java_audit_api():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

        def post_pnl_snapshot(self, payload):
            return None

    callback_client = StubCallbackClient()
    audit_node(
        {
            "trace_id": "trace-3",
            "symbol": "BTCUSDT",
            "mode": None,
            "supervisor_decision": {"action": None, "confidence": None, "summary_reason": None},
            "callback_client": callback_client,
        }
    )

    payload = callback_client.decision_payloads[0]
    assert payload["mode"] == "paper"
    assert payload["action"] == "SKIP"
    assert payload["confidence"] == 0
    assert payload["summaryReason"] == ""


def test_audit_node_keeps_action_empty_when_execution_is_blocked_without_supervisor_action():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

        def post_pnl_snapshot(self, payload):
            return None

    callback_client = StubCallbackClient()
    audit_node(
        {
            "trace_id": "trace-blocked-no-action",
            "symbol": "BTCUSDT",
            "supervisor_decision": {},
            "execution_result": {"status": "blocked", "order_status": "BLOCKED"},
            "callback_client": callback_client,
        }
    )

    payload = callback_client.decision_payloads[0]
    assert payload["action"] == "NO_ACTION"
    assert payload["executionStatus"] == "blocked"
    assert payload["orderStatus"] == "BLOCKED"
    assert payload["decisionActions"][0]["action"] == "NO_ACTION"
    assert payload["decisionActions"][0]["executionStatus"] == "blocked"
    assert payload["decisionActions"][0]["orderStatus"] == "BLOCKED"


def test_audit_node_emits_shadow_decision_log_when_runtime_mode_is_shadow():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []
            self.shadow_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

        def post_pnl_snapshot(self, payload):
            return None

        def post_shadow_decision_log(self, payload):
            self.shadow_payloads.append(payload)

    callback_client = StubCallbackClient()
    audit_node(
        {
            "trace_id": "trace-shadow-2",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "mode": "shadow",
            "supervisor_decision": {
                "action": "OPEN_LONG",
                "side": "long",
                "confidence": 79,
                "summary_reason": "shadow confirmation",
                "model_code": "gpt-4.1-mini",
                "model_provider": "openai",
            },
            "supervisor_prompt_metadata": {
                "prompt_source": "inline",
                "binding_template_code": "trade.supervisor.v1",
                "fallback_template_code": "trade.supervisor.fallback",
                "resolved_template_code": "",
                "prompt_template_fallback_used": True,
            },
            "execution_result": {"status": "pending", "order_status": "PENDING"},
            "callback_client": callback_client,
        }
    )

    assert callback_client.decision_payloads[0]["traceId"] == "trace-shadow-2"
    assert callback_client.shadow_payloads[0]["traceId"] == "trace-shadow-2"
    assert callback_client.shadow_payloads[0]["exchangeCode"] == "okx"
    assert callback_client.shadow_payloads[0]["action"] == "OPEN_LONG"
    assert callback_client.shadow_payloads[0]["modelCode"] == "gpt-4.1-mini"
    assert callback_client.shadow_payloads[0]["modelProvider"] == "openai"
    assert callback_client.shadow_payloads[0]["promptSource"] == "inline"
    assert callback_client.shadow_payloads[0]["bindingTemplateCode"] == "trade.supervisor.v1"
    assert callback_client.shadow_payloads[0]["fallbackTemplateCode"] == "trade.supervisor.fallback"
    assert callback_client.shadow_payloads[0]["resolvedTemplateCode"] == ""
    assert callback_client.shadow_payloads[0]["promptTemplateFallbackUsed"] is True
    assert callback_client.shadow_payloads[0]["orderStatus"] == "PENDING"


def test_audit_node_serializes_generated_signal_window_states_from_feature_engine():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

        def post_pnl_snapshot(self, payload):
            return None

    callback_client = StubCallbackClient()
    state = build_feature_snapshot_node(
        {
            "trace_id": "trace-window-1",
            "symbol": "BTCUSDT",
            "event_bundle": [
                {"event_type": "market_tick", "symbol": "BTCUSDT", "exchange": "binance", "price": 65000.0},
                {"event_type": "news", "symbol": "BTCUSDT", "exchange": "external", "headline": "ETF inflow", "score": 0.82},
                {"event_type": "social", "symbol": "BTCUSDT", "exchange": "external", "score": 0.77},
            ],
        }
    )

    audit_node(
        {
            **state,
            "mode": "paper",
            "event_strength": "strong",
            "supervisor_decision": {
                "action": "OPEN_LONG",
                "side": "long",
                "confidence": 88,
            },
            "execution_result": {
                "status": "filled",
                "order_status": "FILLED",
                "account_equity": 12000.0,
                "daily_pnl": 140.5,
                "max_drawdown_pct": 3.2,
                "unrealized_pnl": 22.4,
                "realized_pnl": 118.1,
            },
            "callback_client": callback_client,
        }
    )

    signal_window_states = callback_client.decision_payloads[0]["signalWindowStates"]
    assert [item["windowKey"] for item in signal_window_states] == [
        "market:BTCUSDT:15m",
        "news:BTCUSDT:15m",
        "social:BTCUSDT:15m",
    ]
    assert signal_window_states[1]["stateJson"] == '{"count":1,"latest_headline":"ETF inflow","max_score":0.82}'
    assert signal_window_states[1]["sourceType"] == "news"
    assert signal_window_states[1]["signalType"] == "headline"
    assert signal_window_states[1]["direction"] == "bullish"
    assert signal_window_states[1]["strengthScore"] == 0.82
    assert signal_window_states[1]["active"] is True
    assert signal_window_states[1]["expiresAt"]
    assert signal_window_states[1]["sourceType"] == "news"
    assert signal_window_states[1]["signalType"] == "headline"
    assert signal_window_states[1]["direction"] == "bullish"
    assert signal_window_states[1]["strengthScore"] == 0.82
    assert signal_window_states[1]["active"] is True
    assert signal_window_states[1]["expiresAt"]


def test_decision_audit_payload_includes_memory_fields():
    from trade_runtime.decision.nodes.audit import _build_decision_payload

    payload = _build_decision_payload(
        {
            "trace_id": "trace-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "supervisor_decision": {"action": "hold", "confidence": 60, "summary_reason": "test"},
            "short_term_memory": {"news": {"sample_count": 1, "items": []}},
            "long_term_memory": {"status": "ready", "items": [{"id": 1, "lesson_text": "lesson"}]},
            "memory_usage": {"used_memory_ids": [1]},
            "trade_memory_status": {
                "status": "stored",
                "reason": "",
                "trace_id": "trace-1",
                "lesson_text": "Wait for breakdown retest before treating the move as trend continuation.",
            },
            "lifecycle_status": {
                "status": "recorded",
                "operation": "exit",
                "trace_id": "trace-1",
                "memory_status": "stored",
                "memory_reason": "",
                "memory": {
                    "lesson_text": "Wait for breakdown retest before treating the move as trend continuation."
                },
            },
        }
    )

    assert payload["shortTermMemory"]["news"]["sample_count"] == 1
    assert payload["longTermMemory"]["items"][0]["id"] == 1
    assert payload["memoryUsage"]["used_memory_ids"] == [1]
    assert payload["tradeMemoryStatus"]["status"] == "stored"
    assert payload["tradeMemoryStatus"]["lesson_text"] == "Wait for breakdown retest before treating the move as trend continuation."
    assert payload["lifecycleStatus"]["memory"]["lesson_text"] == "Wait for breakdown retest before treating the move as trend continuation."


def test_audit_node_emits_recalculated_daily_pnl_and_drawdown_after_paper_reduce():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []
            self.pnl_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

        def post_pnl_snapshot(self, payload):
            self.pnl_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "reduce-loss-1",
                "fill_price": 90.0,
                "fill_quantity": 1.0,
                "position_quantity": 1.0,
                "entry_price": 100.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-pnl-recalc-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "account_equity": 9800.0,
            "daily_pnl": -200.0,
            "max_drawdown_pct": 2.0,
            "realized_pnl": 15.0,
            "event_bundle": [{"event_type": "market_tick", "price": 90.0}],
            "current_position_side": "long",
            "current_position_quantity": 2.0,
            "current_position_notional": 200.0,
            "supervisor_decision": {"action": "REDUCE", "side": "long", "size_hint": 0.5},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
        }
    )

    audit_node(
        {
            **state,
            "callback_client": callback_client,
        }
    )

    assert callback_client.pnl_payloads[0]["accountEquity"] == 9790.0
    assert callback_client.pnl_payloads[0]["dailyPnl"] == -210.0
    assert callback_client.pnl_payloads[0]["maxDrawdownPct"] == 2.1
