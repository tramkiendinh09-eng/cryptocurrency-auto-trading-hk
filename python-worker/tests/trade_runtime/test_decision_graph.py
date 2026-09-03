from trade_runtime.config import RuntimeConfig
from trade_runtime.decision.deliberation import should_run_deliberation
from trade_runtime.decision.graph import build_decision_graph
from trade_runtime.decision.nodes.classify import classify_event_strength
from trade_runtime.decision.nodes.execution_node import execution_node
from trade_runtime.decision.nodes.lifecycle_node import lifecycle_node
from trade_runtime.decision.nodes.risk_guard_node import risk_guard_node
from trade_runtime.execution.router import ExecutionRouter


def test_strong_event_skips_noise_path_and_reaches_supervisor():
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "paper",
        }
    )
    assert result["supervisor_decision"]["action"] in {"OPEN_LONG", "OPEN_SHORT", "HOLD", "SKIP"}
    assert "market_view" in result
    assert "news_view" in result
    assert "onchain_view" in result
    assert "social_view" in result


def test_graph_preserves_market_context_history_for_prompt_context():
    graph = build_decision_graph()
    market_context_history = [
        {"observed_at": "2026-04-29 16:58:40", "price": 77010.0, "quote_volume": 67602.5674},
        {"observed_at": "2026-04-29 16:59:41", "price": 77009.9, "quote_volume": 67602.5686},
        {"observed_at": "2026-04-29 17:00:42", "price": 77009.9, "quote_volume": 67602.5686},
    ]

    result = graph.invoke(
        {
            "trace_id": "t-market-history",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 77009.9}],
            "feature_snapshot": {"price_change_pct": 0.0},
            "market_context_history": market_context_history,
            "mode": "paper",
        }
    )

    assert result["market_context_history"] == market_context_history


def test_normal_news_signal_stays_rule_only_without_large_price_move():
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-2",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [
                {"event_type": "market_tick"},
                {"event_type": "news", "headline": "ETF inflow", "score": 0.8},
            ],
            "feature_snapshot": {"price_change_pct": 0.4, "news_score": 0.8},
            "mode": "paper",
        }
    )

    assert result["event_strength"] == "normal"
    assert "market_view" in result
    assert "news_view" in result
    assert "onchain_view" in result
    assert "social_view" in result
    assert "ETF inflow" in result["news_view"]["reason"]
    assert "supervisor_decision" not in result
    assert "risk_result" not in result
    assert "execution_result" not in result


def test_llm_allowed_signal_routes_through_deliberation_when_policy_enabled():
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-deliberation-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [
                {"event_type": "market_tick"},
                {"event_type": "news", "headline": "ETF inflow", "score": 0.8},
            ],
            "feature_snapshot": {"price_change_pct": -1.4, "news_score": 0.8},
            "mode": "paper",
            "dispatch_mode": "LLM_ALLOWED",
            "selected_agents": ["market_agent", "news_agent"],
            "agent_profiles": [
                {"agent_code": "market_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 1},
                {"agent_code": "news_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 2},
            ],
            "deliberation_policy": {"enabled": True, "maxRounds": 1, "failOpen": True},
        }
    )

    assert result["event_strength"] == "normal"
    assert result["market_view"]["bias"] == "bearish"
    assert result["news_view"]["bias"] == "bullish"
    message_types = [message["message_type"] for message in result["agent_messages"]]
    assert message_types[:6] == [
        "proposal",
        "proposal",
        "challenge",
        "revision",
        "revision",
        "summary",
    ]
    assert message_types[6:] == ["final_decision"]
    assert "conclusion" not in message_types



def test_should_run_deliberation_requires_conflicting_directional_biases():
    """测试审议触发条件

    修改后的逻辑：只要有>=2个Agent发言，就触发审议
    即使观点一致，裁判Agent也可以确认决策合理性
    """
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "selected_agents": ["market_agent", "news_agent"],
        "agent_profiles": [
            {"agent_code": "market_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 1},
            {"agent_code": "news_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 2},
        ],
        "deliberation_policy": {"enabled": True, "maxRounds": 1, "failOpen": True},
        "market_view": {"bias": "neutral", "confidence": 55, "reason": "wyckoff_watch"},
        "news_view": {"bias": "bullish", "confidence": 80, "reason": "ETF inflow"},
    }

    # 修改后：有2个Agent发言，即使观点不冲突也触发审议
    assert should_run_deliberation(state) is True


def test_deliberation_referee_profile_calls_model_and_supplies_review_before_supervisor_final():
    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            assert template_code == "trade.referee.v1"
            return {
                "code": template_code,
                "content": "Referee transcript={agent_messages_json} market={market_view_json} news={news_view_json}",
            }

    class StubDecisionModelClient:
        def __init__(self):
            self.calls = []

        def call_model(self, *, model_id, prompt):
            self.calls.append({"model_id": model_id, "prompt": prompt})
            if model_id == 77:
                content = (
                    "{\"action\":\"HOLD\",\"side\":\"flat\",\"confidence\":91,"
                    "\"size_hint\":0.0,\"leverage_hint\":1,\"holding_window\":\"15m-1h\","
                    "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"referee_override\"}"
                )
                model_code = "gpt-referee"
            else:
                content = (
                    "{\"action\":\"HOLD\",\"side\":\"long\",\"confidence\":88,"
                    "\"size_hint\":0.0,\"leverage_hint\":2,\"holding_window\":\"15m-1h\","
                    "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"supervisor_final\"}"
                )
                model_code = "gpt-supervisor"
            return {
                "modelId": model_id,
                "modelCode": model_code,
                "modelProvider": "openai",
                "content": content,
            }

    decision_model_client = StubDecisionModelClient()
    graph = build_decision_graph()

    result = graph.invoke(
        {
            "trace_id": "t-deliberation-referee",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "event_bundle": [
                {"event_type": "market_tick"},
                {"event_type": "news", "headline": "ETF inflow", "score": 0.8},
            ],
            "feature_snapshot": {"price_change_pct": -1.4, "news_score": 0.8},
            "mode": "paper",
            "dispatch_mode": "LLM_ALLOWED",
            "selected_agents": ["market_agent", "news_agent"],
            "agent_profiles": [
                {"agent_code": "market_agent", "agent_type": "RULE", "enabled": True, "dialogue_enabled": True, "speak_order": 1},
                {"agent_code": "news_agent", "agent_type": "RULE", "enabled": True, "dialogue_enabled": True, "speak_order": 2},
                {"agent_code": "deliberation_referee", "agent_type": "LLM", "enabled": True, "llm_enabled": True, "dialogue_enabled": True, "speak_order": 5},
            ],
            "resolved_agent_configs": [
                {
                    "agent_code": "deliberation_referee",
                    "agent_type": "LLM",
                    "enabled": True,
                    "llm_enabled": True,
                    "model_id": 77,
                    "model_code": "gpt-referee",
                    "model_provider": "openai",
                    "template_code": "trade.referee.v1",
                    "output_schema_code": "deliberation_referee_v1",
                }
            ],
            "strategy_context": {
                "ai_model_config": {
                    "id": 31,
                    "model_code": "gpt-supervisor",
                    "provider": "openai",
                }
            },
            "deliberation_policy": {"enabled": True, "maxRounds": 1, "failOpen": True},
            "decision_model_client": decision_model_client,
            "prompt_template_registry": StubPromptTemplateRegistry(),
        }
    )

    assert len(decision_model_client.calls) == 2
    assert decision_model_client.calls[0]["model_id"] == 77
    assert decision_model_client.calls[1]["model_id"] == 31
    assert "proposal" in decision_model_client.calls[0]["prompt"]
    assert "challenge" in decision_model_client.calls[0]["prompt"]
    assert "referee_override" in decision_model_client.calls[1]["prompt"]
    assert "conflicting_specialist_views_detected" in decision_model_client.calls[1]["prompt"]
    assert result["deliberation_referee_review"]["summary_reason"] == "referee_override"
    assert result["supervisor_decision"]["summary_reason"] == "supervisor_final"
    assert result["agent_messages"][-2]["speaker_agent"] == "deliberation_referee"
    assert result["agent_messages"][-2]["message_type"] == "referee_review"
    assert result["agent_messages"][-1]["speaker_agent"] == "supervisor_agent"
    assert result["agent_messages"][-1]["message_type"] == "final_decision"


def test_deliberation_uses_only_selected_specialists_for_conflicts():
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-deliberation-active-only",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "event_bundle": [
                {"event_type": "market_tick"},
                {"event_type": "onchain", "flow": "exchange_inflow", "amountUsd": 2500000},
            ],
            "feature_snapshot": {"price_change_pct": 1.8, "onchain_flow_bias": 0.92},
            "mode": "paper",
            "dispatch_mode": "LLM_ALLOWED",
            "selected_agents": ["market_agent", "onchain_agent"],
            "agent_profiles": [
                {"agent_code": "market_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 1},
                {"agent_code": "news_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 2},
                {"agent_code": "onchain_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 3},
                {"agent_code": "social_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 4},
            ],
            "deliberation_policy": {"enabled": True, "maxRounds": 1, "failOpen": True},
        }
    )

    message_types = [message["message_type"] for message in result["agent_messages"]]
    assert message_types[:6] == [
        "proposal",
        "proposal",
        "challenge",
        "revision",
        "revision",
        "summary",
    ]
    assert message_types[6:] == ["final_decision"]
    assert "conclusion" not in message_types
    debate_speakers = {
        message["speaker_agent"]
        for message in result["agent_messages"]
        if message["message_type"] in {"proposal", "challenge", "revision", "summary"}
    }
    assert debate_speakers == {"market_agent", "onchain_agent", "orchestrator"}
    assert all(message["speaker_agent"] != "news_agent" for message in result["agent_messages"])
    assert all(message["speaker_agent"] != "social_agent" for message in result["agent_messages"])

def test_strong_news_signal_runs_multi_agent_for_full_context():
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-2b",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "news", "headline": "ETF approval", "score": 0.95}],
            "feature_snapshot": {"price_change_pct": 0.3, "news_score": 0.95},
            "mode": "paper",
        }
    )

    assert result["event_strength"] == "strong"
    assert "market_view" in result
    assert "news_view" in result
    assert "ETF approval" in result["news_view"]["reason"]
    assert "onchain_view" in result
    assert "social_view" in result


def test_strong_onchain_signal_runs_multi_agent_for_full_context():
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-2c",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "onchain", "flow": "exchange_outflow", "amountUsd": 2500000}],
            "feature_snapshot": {"price_change_pct": 0.2, "onchain_flow_bias": 0.92},
            "mode": "paper",
        }
    )

    assert result["event_strength"] == "strong"
    assert "market_view" in result
    assert "news_view" in result
    assert "onchain_view" in result
    assert "exchange_outflow" in result["onchain_view"]["reason"]
    assert "social_view" in result


def test_selected_strong_signal_routes_selected_specialists_before_supervisor():
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-selected-strong-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "event_bundle": [
                {"event_type": "market_tick"},
                {"event_type": "news", "headline": "ETF approval", "score": 0.95},
                {"event_type": "onchain", "flow": "exchange_outflow", "amountUsd": 2500000},
            ],
            "feature_snapshot": {"price_change_pct": 1.2, "news_score": 0.95, "onchain_flow_bias": 0.92},
            "mode": "paper",
            "dispatch_mode": "LLM_ALLOWED",
            "selected_agents": ["market_agent", "news_agent", "onchain_agent"],
        }
    )

    assert result["multi_agent_runtime"]["selectedAgents"] == ["market_agent", "news_agent", "onchain_agent"]
    assert "market_view" in result
    assert "news_view" in result
    assert "onchain_view" in result
    assert "supervisor_decision" in result


def test_graph_blocks_execution_when_risk_guard_fails():
    class StubRiskGuard:
        def evaluate(self, **kwargs):
            return {"passed": False, "reason": "daily_loss_limit"}

    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-3",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "paper",
            "risk_guard": StubRiskGuard(),
        }
    )

    assert result["risk_result"]["passed"] is False
    assert result["execution_result"]["status"] == "blocked"
    assert result["execution_result"]["reason"] == "daily_loss_limit"


def test_risk_guard_node_emits_risk_guard_hit_when_market_source_is_abnormal():
    class StubCallbackClient:
        def __init__(self):
            self.risk_guard_hit_payloads = []

        def post_risk_guard_hit(self, payload):
            self.risk_guard_hit_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = risk_guard_node(
        {
            "trace_id": "t-risk-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "stale"}],
            "feature_snapshot": {},
            "mode": "paper",
            "supervisor_decision": {"action": "OPEN_LONG", "size_hint": 0.2},
            "account_equity": 10000.0,
            "callback_client": callback_client,
        }
    )

    assert state["risk_result"]["passed"] is False
    assert state["risk_result"]["rule_code"] == "market_source_abnormal"
    assert callback_client.risk_guard_hit_payloads[0]["traceId"] == "t-risk-1"
    assert callback_client.risk_guard_hit_payloads[0]["ruleCode"] == "market_source_abnormal"


def test_risk_guard_node_uses_runtime_config_thresholds_from_control_plane():
    state = risk_guard_node(
        {
            "trace_id": "t-risk-config-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            "supervisor_decision": {"action": "OPEN_LONG", "size_hint": 0.2},
            "account_equity": 10000.0,
            "daily_pnl": -550.0,
            "runtime_config": {
                "max_position_ratio": 0.6,
                "max_daily_loss": -500.0,
                "max_consecutive_failures": 6,
            },
        }
    )

    assert state["risk_result"]["passed"] is False
    assert state["risk_result"]["rule_code"] == "daily_loss_limit"


def test_risk_guard_node_blocks_when_projected_position_exceeds_runtime_limit():
    state = risk_guard_node(
        {
            "trace_id": "t-risk-position-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            # max_position_ratio 现在约束的是保证金占比而不是敞口占比，
            # 所以要触发这条上限，输入得按新口径重算：
            #   请求敞口 = 10000 × 0.25 × 3（默认杠杆）= 7500，保证金 2500
            #   叠加已有 2000 敞口（保证金 667）后共 3167 = 权益的 31.7%
            #   超过 0.25，应当被拦。
            # 旧口径下 size_hint 0.1 就够了，那是因为当时直接拿敞口去比。
            "supervisor_decision": {"action": "ADD_LONG", "size_hint": 0.25, "side": "long"},
            "account_equity": 10000.0,
            "current_position_notional": 2000.0,
            "runtime_config": {
                "max_position_ratio": 0.25,
            },
        }
    )

    assert state["risk_result"]["passed"] is False
    assert state["risk_result"]["rule_code"] == "position_limit"


def test_risk_guard_node_blocks_fast_reduce_before_minimum_holding_minutes():
    class StubCallbackClient:
        def __init__(self):
            self.risk_guard_hit_payloads = []

        def post_risk_guard_hit(self, payload):
            self.risk_guard_hit_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = risk_guard_node(
        {
            "trace_id": "t-risk-hold-discipline-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            "current_time": "2026-05-12T01:49:00+08:00",
            "current_position_side": "long",
            "current_position_quantity": 0.2,
            "current_position_opened_at": "2026-05-12T01:44:00+08:00",
            "supervisor_decision": {"action": "REDUCE", "side": "long", "size_hint": 0.5},
            "account_equity": 10000.0,
            "runtime_config": {
                "runtime_flags_json": '{"positionDiscipline":{"minPositionHoldMinutes":15}}',
            },
            "callback_client": callback_client,
        }
    )

    assert state["risk_result"]["passed"] is False
    assert state["risk_result"]["rule_code"] == "min_position_hold_minutes"
    assert state["risk_result"]["action"] == "REDUCE"
    assert state["risk_result"]["current_position_side"] == "long"
    assert state["risk_result"]["current_position_holding_minutes"] == 5
    assert state["risk_result"]["min_position_hold_minutes"] == 15
    assert callback_client.risk_guard_hit_payloads[0]["ruleCode"] == "min_position_hold_minutes"


def test_risk_guard_node_applies_default_minimum_holding_minutes_for_fast_close():
    state = risk_guard_node(
        {
            "trace_id": "t-risk-hold-default-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            "current_position_side": "long",
            "current_position_quantity": 0.2,
            "current_position_holding_minutes": 5,
            "supervisor_decision": {"action": "CLOSE", "side": "long", "size_hint": 1.0},
            "account_equity": 10000.0,
            "runtime_config": {},
        }
    )

    assert state["risk_result"]["passed"] is False
    assert state["risk_result"]["rule_code"] == "min_position_hold_minutes"
    assert state["risk_result"]["current_position_holding_minutes"] == 5
    assert state["risk_result"]["min_position_hold_minutes"] == 15


def test_risk_guard_node_allows_fast_close_when_minimum_holding_minutes_is_disabled():
    state = risk_guard_node(
        {
            "trace_id": "t-risk-hold-disabled-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            "current_position_side": "long",
            "current_position_quantity": 0.2,
            "current_position_holding_minutes": 5,
            "supervisor_decision": {"action": "CLOSE", "side": "long", "size_hint": 1.0},
            "account_equity": 10000.0,
            "runtime_config": {
                "runtime_flags_json": '{"positionDiscipline":{"minPositionHoldMinutes":0}}',
            },
        }
    )

    assert state["risk_result"]["passed"] is True
    assert state["risk_result"]["rule_code"] == "pass"


def test_risk_guard_node_allows_emergency_close_when_supervisor_exit_escalation_is_present():
    state = risk_guard_node(
        {
            "trace_id": "t-risk-hold-emergency-close-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            "current_position_side": "short",
            "current_position_quantity": 0.2,
            "current_position_holding_minutes": 5,
            "supervisor_decision": {"action": "CLOSE", "side": "short", "size_hint": 1.0},
            "supervisor_exit_escalation": {"reason": "invalidation_breached"},
            "position_risk_result": {"triggered": True, "severity": "reduce", "reason": "structure_reversal"},
            "account_equity": 10000.0,
            "runtime_config": {
                "runtime_flags_json": '{"positionDiscipline":{"minPositionHoldMinutes":15}}',
            },
        }
    )

    assert state["risk_result"]["passed"] is True
    assert state["risk_result"]["rule_code"] == "pass"


def test_risk_guard_node_blocks_open_or_add_when_supervisor_ai_call_failed():
    class StubCallbackClient:
        def __init__(self):
            self.risk_guard_hit_payloads = []

        def post_risk_guard_hit(self, payload):
            self.risk_guard_hit_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = risk_guard_node(
        {
            "trace_id": "t-risk-ai-failed-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            "ai_call_failed": True,
            "agent_llm_errors": [{"agent_code": "supervisor_agent", "error": "timeout"}],
            "supervisor_decision": {"action": "OPEN_LONG", "size_hint": 0.1, "side": "long"},
            "account_equity": 10000.0,
            "runtime_config": {"max_position_ratio": 0.5},
            "callback_client": callback_client,
        }
    )

    assert state["risk_result"]["passed"] is False
    assert state["risk_result"]["rule_code"] == "ai_call_failed_fail_closed"
    assert callback_client.risk_guard_hit_payloads[0]["traceId"] == "t-risk-ai-failed-1"
    assert callback_client.risk_guard_hit_payloads[0]["ruleCode"] == "ai_call_failed_fail_closed"


def test_risk_guard_node_allows_open_when_only_specialist_ai_call_failed():
    state = risk_guard_node(
        {
            "trace_id": "t-risk-specialist-ai-failed-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "paper",
            "ai_call_failed": True,
            "agent_llm_errors": [{"agent_code": "market_agent", "error": "timeout"}],
            "supervisor_decision": {"action": "OPEN_SHORT", "size_hint": 0.1, "side": "short"},
            "account_equity": 10000.0,
            "runtime_config": {"max_position_ratio": 0.5},
        }
    )

    assert state["risk_result"]["passed"] is True
    assert state["risk_result"]["rule_code"] == "pass"


def test_supervisor_llm_exception_fails_closed_instead_of_rule_open():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            raise RuntimeError("401 Unauthorized")

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.v1":
                return {"code": template_code, "content": "Supervisor template {symbol}"}
            return None

    state = supervisor_agent(
        {
            "trace_id": "t-supervisor-ai-failed-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "event_strength": "strong",
            "dispatch_mode": "LLM_ALLOWED",
            "market_view": {"bias": "bullish", "confidence": 80, "reason": "breakout"},
            "news_view": {"bias": "bullish", "confidence": 75, "reason": "news"},
            "current_position_side": "flat",
            "strategy_context": {"ai_model_config": {"id": 6, "model_code": "gpt-test", "provider": "openai"}},
            "agent_profiles": [{"agent_code": "supervisor_agent", "agent_type": "LLM", "llm_enabled": True}],
            "prompt_bindings": [
                {
                    "binding_scope": "SUPERVISOR",
                    "template_code": "trade.supervisor.v1",
                    "model_id": 91,
                    "enabled": True,
                    "priority": 10,
                }
            ],
            "decision_model_client": StubDecisionModelClient(),
            "prompt_template_registry": StubPromptTemplateRegistry(),
        }
    )

    assert state["ai_call_failed"] is True
    assert state["supervisor_decision"]["action"] == "SKIP"
    assert state["supervisor_decision"]["summary_reason"] == "ai_model_call_failed_fail_closed"
    assert state["agent_llm_errors"][0]["agent_code"] == "supervisor_agent"


def test_risk_guard_node_blocks_live_execution_when_account_is_not_healthy():
    state = risk_guard_node(
        {
            "trace_id": "t-risk-account-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick"}],
            "feature_snapshot": {},
            "mode": "live",
            "supervisor_decision": {"action": "OPEN_LONG", "size_hint": 0.2},
            "account_equity": 10000.0,
            "runtime_config": {
                "live_order_requires_healthy_account": True,
            },
            "exchange_account": {
                "exchange_code": "binance",
                "account_name": "binance-live",
                "health_status": "degraded",
                "last_validated_at": "2026-04-17 09:30:00",
            },
        }
    )

    assert state["risk_result"]["passed"] is False
    assert state["risk_result"]["rule_code"] == "account_unhealthy"


def test_graph_routes_stale_market_source_through_risk_guard():
    class StubCallbackClient:
        def __init__(self):
            self.risk_guard_hit_payloads = []
            self.exchange_order_payloads = []

        def post_decision_audit(self, payload):
            return None

        def post_risk_guard_hit(self, payload):
            self.risk_guard_hit_payloads.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

    callback_client = StubCallbackClient()
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-risk-graph-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "stale"}],
            "feature_snapshot": {"price_change_pct": 0.0},
            "mode": "paper",
            "callback_client": callback_client,
        }
    )

    assert result["risk_result"]["passed"] is False
    assert result["risk_result"]["rule_code"] == "market_source_abnormal"
    assert callback_client.risk_guard_hit_payloads[0]["traceId"] == "t-risk-graph-1"
    assert callback_client.exchange_order_payloads[0]["status"] == "blocked"


def test_decision_graph_routes_execution_through_trade_lifecycle_before_audit():
    graph = build_decision_graph()

    assert "trade_lifecycle" in graph.nodes
    assert ("execute_order", "trade_lifecycle") in graph.builder.edges
    assert ("trade_lifecycle", "audit") in graph.builder.edges
    assert ("execute_order", "audit") not in graph.builder.edges


def test_trade_lifecycle_node_populates_trade_memory_status_for_close_flow():
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
                    "lesson_text": "Close the short only after the breakdown is invalidated on reclaim.",
                },
            }

    state = lifecycle_node(
        {
            "trace_id": "trace-close-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "supervisor_decision": {
                "action": "CLOSE",
                "side": "short",
                "summary_reason": "invalidated_short",
            },
            "execution_result": {
                "status": "filled",
                "order_status": "FILLED",
                "fill_price": 2144.19,
                "fill_quantity": 0.3,
            },
            "runtime_account_context": {
                "current_position_side": "short",
                "current_position_quantity": 0.3,
                "entry_trace_id": "trace-open-1",
            },
            "lifecycle_manager": StubLifecycleManager(),
        }
    )

    assert state["lifecycle_status"]["status"] == "recorded"
    assert state["lifecycle_status"]["trace_id"] == "trace-open-1"
    assert state["trade_memory_status"]["status"] == "stored"
    assert state["trade_memory_status"]["trace_id"] == "trace-open-1"
    assert (
        state["trade_memory_status"]["lesson_text"]
        == "Close the short only after the breakdown is invalidated on reclaim."
    )


def test_execution_node_emits_blocked_exchange_order_callback_with_status_pair():
    class StubCallbackClient:
        def __init__(self):
            self.exchange_order_payloads = []

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "t-3b",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "supervisor_decision": {"action": "OPEN_LONG", "side": "long"},
            "risk_result": {"passed": False, "reason": "daily_loss_limit"},
            "callback_client": callback_client,
        }
    )

    assert state["execution_result"]["status"] == "blocked"
    assert state["execution_result"]["order_status"] == "BLOCKED"
    assert callback_client.exchange_order_payloads[0]["status"] == "blocked"
    assert callback_client.exchange_order_payloads[0]["executionStatus"] == "blocked"
    assert callback_client.exchange_order_payloads[0]["orderStatus"] == "BLOCKED"


def test_execution_node_emits_skipped_exchange_order_callback_with_status_pair():
    class StubCallbackClient:
        def __init__(self):
            self.exchange_order_payloads = []

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "t-3c",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "supervisor_decision": {"action": "SKIP", "side": "flat"},
            "risk_result": {"passed": True, "reason": "pass"},
            "callback_client": callback_client,
        }
    )

    assert state["execution_result"]["status"] == "skipped"
    assert state["execution_result"]["order_status"] == "SKIPPED"
    assert callback_client.exchange_order_payloads[0]["status"] == "skipped"
    assert callback_client.exchange_order_payloads[0]["executionStatus"] == "skipped"
    assert callback_client.exchange_order_payloads[0]["orderStatus"] == "SKIPPED"


def test_execution_node_skips_hold_without_placing_order():
    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            raise AssertionError("HOLD should not reach execution router")

    state = execution_node(
        {
            "trace_id": "t-hold-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "supervisor_decision": {"action": "HOLD", "side": "long"},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
        }
    )

    assert state["execution_result"]["status"] == "skipped"
    assert state["execution_result"]["order_status"] == "SKIPPED"
    assert state["execution_result"]["reason"] == "hold"


def test_execution_node_emits_paper_trade_order_callback_in_paper_mode():
    class StubCallbackClient:
        def __init__(self):
            self.paper_trade_order_payloads = []

        def post_paper_trade_order(self, payload):
            self.paper_trade_order_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "paper-BTCUSDT",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "t-paper-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "supervisor_decision": {"action": "OPEN_LONG", "side": "long", "size_hint": 0.35},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert state["execution_result"]["status"] == "filled"
    assert callback_client.paper_trade_order_payloads[0]["traceId"] == "t-paper-1"
    # 敞口 = 权益 × size_hint × 杠杆。模型没给 leverage_hint，用默认 5 倍，
    # 所以是不带杠杆时 3500 的五倍——杠杆真正参与仓位计算。
    assert callback_client.paper_trade_order_payloads[0]["quoteAmount"] == 17500.0
    assert callback_client.paper_trade_order_payloads[0]["orderRef"] == "paper-BTCUSDT"
    assert callback_client.paper_trade_order_payloads[0]["executionStatus"] == "filled"
    assert callback_client.paper_trade_order_payloads[0]["orderStatus"] == "FILLED"


def test_execution_node_prefers_effective_price_for_paper_execution_and_fill_callbacks():
    class StubCallbackClient:
        def __init__(self):
            self.exchange_fill_payloads = []
            self.position_snapshot_payloads = []

        def post_exchange_fill(self, payload):
            self.exchange_fill_payloads.append(payload)

        def post_position_snapshot(self, payload):
            self.position_snapshot_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "t-paper-effective-price-1",
            "symbol": "XAUUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 2371.19}],
            "feature_snapshot": {
                "effective_price": 2362.05,
                "mark_price": 2362.05,
            },
            "supervisor_decision": {"action": "OPEN_SHORT", "side": "short", "size_hint": 0.1},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": ExecutionRouter(binance_client=None, okx_client=None),
            "callback_client": callback_client,
        }
    )

    assert state["last_order"]["price"] == 2362.05
    assert state["execution_result"]["fill_price"] == 2362.05
    assert callback_client.exchange_fill_payloads[0]["fillPrice"] == 2362.05
    assert callback_client.position_snapshot_payloads[0]["entryPrice"] == 2362.05


def test_execution_node_includes_strategy_user_id_in_position_snapshot_callback():
    class StubCallbackClient:
        def __init__(self):
            self.position_snapshot_payloads = []

        def post_position_snapshot(self, payload):
            self.position_snapshot_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "paper-BTCUSDT",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()

    execution_node(
        {
            "trace_id": "t-position-user-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "supervisor_decision": {"action": "OPEN_LONG", "side": "long", "size_hint": 0.35},
            "risk_result": {"passed": True, "reason": "pass"},
            "strategy_context": {"user_id": 42},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert callback_client.position_snapshot_payloads[0]["userId"] == 42


def test_execution_node_sets_current_position_opened_at_when_opening_new_position():
    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "paper-BTCUSDT-opened-at",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    state = execution_node(
        {
            "trace_id": "t-position-opened-at-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 64000.0}],
            "supervisor_decision": {"action": "OPEN_LONG", "side": "long", "size_hint": 0.35},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "timestamp_supplier": lambda: "2026-05-06T13:41:01.000Z",
        }
    )

    assert state["current_position_opened_at"] == "2026-05-06T13:41:01.000Z"


def test_execution_node_keeps_current_position_opened_at_when_live_close_order_is_pending():
    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "pending",
                "order_status": "PENDING",
                "order_id": "live-close-pending-opened-at",
                "fill_price": 0.0,
                "fill_quantity": 0.0,
            }

    state = execution_node(
        {
            "trace_id": "t-live-close-pending-opened-at-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "live",
            "event_bundle": [{"event_type": "market_tick", "price": 64000.0}],
            "current_position_side": "long",
            "current_position_quantity": 0.5,
            "current_position_notional": 32000.0,
            "current_position_opened_at": "2026-05-06T13:41:01.000Z",
            "supervisor_decision": {"action": "CLOSE", "side": "long", "size_hint": 1.0},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "timestamp_supplier": lambda: "2026-05-06T14:00:00.000Z",
        }
    )

    assert state["execution_result"]["status"] == "pending"
    assert state["current_position_opened_at"] == "2026-05-06T13:41:01.000Z"


def test_execution_node_accumulates_add_long_quantity_and_weighted_entry_price():
    class StubCallbackClient:
        def __init__(self):
            self.position_snapshot_payloads = []

        def post_position_snapshot(self, payload):
            self.position_snapshot_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "paper-BTCUSDT-add",
                "fill_price": 120.0,
                "fill_quantity": 1.0,
                "position_quantity": 1.0,
                "entry_price": 120.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "t-add-long-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 120.0}],
            "current_position_side": "long",
            "current_position_quantity": 2.0,
            "current_position_notional": 200.0,
            "supervisor_decision": {"action": "ADD_LONG", "side": "long", "size_hint": 0.1},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert state["execution_result"]["position_quantity"] == 3.0
    assert state["execution_result"]["entry_price"] == 106.66666667
    assert callback_client.position_snapshot_payloads[0]["positionQuantity"] == 3.0
    assert callback_client.position_snapshot_payloads[0]["entryPrice"] == 106.66666667


def test_execution_node_closes_existing_long_with_sell_order():
    captured = {}

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["order"] = order
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "close-1",
                "fill_price": 65000.0,
                "fill_quantity": 0.1,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
            }

    state = execution_node(
        {
            "trace_id": "t-close-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "current_position_side": "long",
            "current_position_notional": 5000.0,
            "supervisor_decision": {"action": "CLOSE", "side": "long", "size_hint": 1.0},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
        }
    )

    assert captured["order"]["side"] == "SELL"
    assert captured["order"]["quote"] == 5000.0
    assert captured["order"]["action"] == "CLOSE"
    assert captured["order"]["position_side"] == "long"
    assert captured["order"]["reduce_only"] is True
    assert captured["order"]["order_type"] == "market"
    assert state["execution_result"]["status"] == "filled"


def test_execution_node_computes_realized_pnl_for_short_reduce_and_keeps_entry_price():
    class StubCallbackClient:
        def __init__(self):
            self.position_snapshot_payloads = []

        def post_position_snapshot(self, payload):
            self.position_snapshot_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "reduce-short-1",
                "fill_price": 90.0,
                "fill_quantity": 0.5,
                "position_quantity": 0.5,
                "entry_price": 90.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "t-reduce-short-realized-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 90.0}],
            "current_position_side": "short",
            "current_position_quantity": 2.0,
            "current_position_notional": 200.0,
            "realized_pnl": 12.0,
            "supervisor_decision": {"action": "REDUCE", "side": "short", "size_hint": 0.25},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert state["execution_result"]["position_quantity"] == 1.5
    assert state["execution_result"]["entry_price"] == 100.0
    assert state["execution_result"]["realized_pnl"] == 17.0
    assert callback_client.position_snapshot_payloads[0]["positionQuantity"] == 1.5
    assert callback_client.position_snapshot_payloads[0]["entryPrice"] == 100.0


def test_execution_node_reduces_existing_short_with_buy_order():
    captured = {}

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["order"] = order
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "reduce-1",
                "fill_price": 65000.0,
                "fill_quantity": 0.05,
                "position_quantity": 0.05,
                "entry_price": 65000.0,
            }

    state = execution_node(
        {
            "trace_id": "t-reduce-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "current_position_side": "short",
            "current_position_notional": 4000.0,
            "supervisor_decision": {"action": "REDUCE", "side": "short", "size_hint": 0.5},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
        }
    )

    assert captured["order"]["side"] == "BUY"
    assert captured["order"]["quote"] == 2000.0
    assert captured["order"]["action"] == "REDUCE"
    assert captured["order"]["position_side"] == "short"
    assert captured["order"]["reduce_only"] is True
    assert state["execution_result"]["status"] == "filled"


def test_execution_node_passes_limit_order_metadata_without_changing_callbacks():
    captured = {}

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            captured["order"] = order
            return {
                "status": "pending",
                "order_status": "PENDING",
                "order_id": "limit-1",
                "fill_price": 65000.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
            }

    state = execution_node(
        {
            "trace_id": "t-limit-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "live",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "supervisor_decision": {
                "action": "OPEN_LONG",
                "side": "long",
                "size_hint": 0.1,
                "leverage_hint": 7,
                "order_type": "limit",
                "limit_price": 64950.0,
            },
            # 没有 maxLeverage 时天花板退回默认 5 倍，7 会被夹到 5——
            # 那测的就是夹持而不是元数据流转了。
            "runtime_config": {"maxLeverage": 10},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
        }
    )

    assert captured["order"]["side"] == "BUY"
    assert captured["order"]["action"] == "OPEN_LONG"
    assert captured["order"]["position_side"] == "long"
    assert captured["order"]["reduce_only"] is False
    assert captured["order"]["order_type"] == "limit"
    assert captured["order"]["limit_price"] == 64950.0
    assert captured["order"]["leverage"] == 7
    assert captured["order"]["td_mode"] == "cross"
    assert state["execution_result"]["status"] == "pending"


def test_execution_node_posts_order_audit_metadata_callbacks():
    class StubCallbackClient:
        def __init__(self):
            self.order_requests = []
            self.exchange_orders = []

        def post_order_request(self, payload):
            self.order_requests.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_orders.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "pending",
                "order_status": "PENDING",
                "order_id": "okx-limit-1",
                "fill_price": 65000.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
            }

    callback_client = StubCallbackClient()
    execution_node(
        {
            "trace_id": "t-audit-meta-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "live",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "supervisor_decision": {
                "action": "CLOSE",
                "side": "long",
                "size_hint": 1.0,
                "leverage_hint": 6,
                "order_type": "limit",
                "limit_price": 65000.1,
            },
            "runtime_config": {"maxLeverage": 10},
            "current_position_side": "long",
            "current_position_notional": 3250.0,
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    for payload in (callback_client.order_requests[0], callback_client.exchange_orders[0]):
        assert payload["action"] == "CLOSE"
        assert payload["orderType"] == "limit"
        assert payload["positionSide"] == "long"
        assert payload["reduceOnly"] is True
        assert payload["tdMode"] == "cross"
        assert payload["leverage"] == 6
        assert payload["limitPrice"] == 65000.1
        assert payload["quantityBase"] == 0.05
        assert payload["okxEnhancedExecution"] is True


def test_execution_node_skips_zero_quote_add_without_fake_fill_callbacks():
    class StubCallbackClient:
        def __init__(self):
            self.order_payloads = []
            self.paper_trade_order_payloads = []
            self.exchange_order_payloads = []
            self.exchange_fill_payloads = []
            self.position_payloads = []

        def post_order_request(self, payload):
            self.order_payloads.append(payload)

        def post_paper_trade_order(self, payload):
            self.paper_trade_order_payloads.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

        def post_exchange_fill(self, payload):
            self.exchange_fill_payloads.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            raise AssertionError("zero quote should be skipped before routing")

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "t-zero-quote-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "current_position_side": "long",
            "current_position_notional": 2500.0,
            "supervisor_decision": {"action": "ADD_LONG", "side": "long", "size_hint": 0.0},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert state["execution_result"]["status"] == "skipped"
    assert state["execution_result"]["order_status"] == "SKIPPED"
    assert state["execution_result"]["reason"] == "zero_quote_order"
    assert callback_client.order_payloads == []
    assert callback_client.paper_trade_order_payloads == []
    assert callback_client.exchange_order_payloads[0]["status"] == "skipped"
    assert callback_client.exchange_fill_payloads == []
    assert callback_client.position_payloads == []


def test_graph_executes_paper_order_after_risk_passes():
    class StubRiskGuard:
        def evaluate(self, **kwargs):
            return {"passed": True, "reason": "pass"}

    class StubCallbackClient:
        def __init__(self):
            self.order_payloads = []
            self.position_payloads = []
            self.exchange_order_payloads = []
            self.exchange_fill_payloads = []
            self.pnl_payloads = []

        def post_order_request(self, payload):
            self.order_payloads.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

        def post_exchange_fill(self, payload):
            self.exchange_fill_payloads.append(payload)

        def post_decision_audit(self, payload):
            return None

        def post_pnl_snapshot(self, payload):
            self.pnl_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"{mode}-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-4",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "paper",
            "risk_guard": StubRiskGuard(),
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert result["risk_result"]["passed"] is True
    assert result["execution_result"]["status"] == "filled"
    assert result["execution_result"]["order_id"] == "paper-BTCUSDT"
    assert callback_client.order_payloads[0]["traceId"] == "t-4"
    # 同上：默认 5 倍杠杆下敞口是保证金的五倍。
    assert callback_client.order_payloads[0]["quoteAmount"] == 17500.0
    assert callback_client.exchange_order_payloads[0]["orderRef"] == "paper-BTCUSDT"
    assert callback_client.exchange_order_payloads[0]["status"] == "filled"
    assert callback_client.exchange_order_payloads[0]["executionStatus"] == "filled"
    assert callback_client.exchange_order_payloads[0]["orderStatus"] == "FILLED"
    assert callback_client.exchange_fill_payloads[0]["orderRef"] == "paper-BTCUSDT"
    assert callback_client.exchange_fill_payloads[0]["fillPrice"] == 64000.0
    assert callback_client.exchange_fill_payloads[0]["fillQuantity"] == 0.0546875
    assert callback_client.position_payloads[0]["symbol"] == "BTCUSDT"
    assert callback_client.position_payloads[0]["side"] == "long"
    assert callback_client.position_payloads[0]["entryPrice"] == 64000.0
    assert callback_client.position_payloads[0]["positionQuantity"] == 0.0546875
    assert callback_client.pnl_payloads[0]["traceId"] == "t-4"
    assert callback_client.pnl_payloads[0]["accountEquity"] == 10000.0
    assert callback_client.pnl_payloads[0]["dailyPnl"] == 0.0


def test_graph_keeps_failed_execution_without_fill_or_position_callbacks():
    class StubRiskGuard:
        def evaluate(self, **kwargs):
            return {"passed": True, "reason": "pass"}

    class StubCallbackClient:
        def __init__(self):
            self.order_payloads = []
            self.position_payloads = []
            self.exchange_order_payloads = []
            self.exchange_fill_payloads = []
            self.pnl_payloads = []

        def post_order_request(self, payload):
            self.order_payloads.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

        def post_exchange_fill(self, payload):
            self.exchange_fill_payloads.append(payload)

        def post_decision_audit(self, payload):
            return None

        def post_pnl_snapshot(self, payload):
            self.pnl_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "failed",
                "is_live": True,
                "exchange": exchange,
                "order_id": "",
                "order_status": "REJECTED",
                "fill_price": 65000.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
                "error": "network timeout",
            }

    callback_client = StubCallbackClient()
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-5",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "live",
            "risk_guard": StubRiskGuard(),
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert result["execution_result"]["status"] == "failed"
    assert callback_client.exchange_order_payloads[0]["status"] == "failed"
    assert callback_client.exchange_order_payloads[0]["executionStatus"] == "failed"
    assert result["execution_result"]["order_status"] == "REJECTED"
    assert callback_client.order_payloads[0]["traceId"] == "t-5"
    assert callback_client.exchange_order_payloads[0]["orderStatus"] == "REJECTED"
    assert callback_client.exchange_fill_payloads == []
    assert callback_client.position_payloads == []
    assert callback_client.pnl_payloads[0]["traceId"] == "t-5"


def test_graph_keeps_canceled_execution_without_fill_or_position_callbacks():
    class StubRiskGuard:
        def evaluate(self, **kwargs):
            return {"passed": True, "reason": "pass"}

    class StubCallbackClient:
        def __init__(self):
            self.order_payloads = []
            self.position_payloads = []
            self.exchange_order_payloads = []
            self.exchange_fill_payloads = []
            self.pnl_payloads = []

        def post_order_request(self, payload):
            self.order_payloads.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

        def post_exchange_fill(self, payload):
            self.exchange_fill_payloads.append(payload)

        def post_decision_audit(self, payload):
            return None

        def post_pnl_snapshot(self, payload):
            self.pnl_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "canceled",
                "is_live": True,
                "exchange": exchange,
                "order_id": "cancel-BTCUSDT",
                "order_status": "CANCELED",
                "fill_price": 65000.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
            }

    callback_client = StubCallbackClient()
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-5b",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "live",
            "risk_guard": StubRiskGuard(),
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert result["execution_result"]["status"] == "canceled"
    assert callback_client.exchange_order_payloads[0]["status"] == "canceled"
    assert callback_client.exchange_order_payloads[0]["executionStatus"] == "canceled"
    assert result["execution_result"]["order_status"] == "CANCELED"
    assert callback_client.exchange_order_payloads[0]["orderStatus"] == "CANCELED"
    assert callback_client.exchange_fill_payloads == []
    assert callback_client.position_payloads == []
    assert callback_client.pnl_payloads[0]["traceId"] == "t-5b"


def test_graph_keeps_pending_execution_without_fill_or_position_callbacks():
    class StubRiskGuard:
        def evaluate(self, **kwargs):
            return {"passed": True, "reason": "pass"}

    class StubCallbackClient:
        def __init__(self):
            self.order_payloads = []
            self.position_payloads = []
            self.exchange_order_payloads = []
            self.exchange_fill_payloads = []
            self.pnl_payloads = []

        def post_order_request(self, payload):
            self.order_payloads.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

        def post_exchange_fill(self, payload):
            self.exchange_fill_payloads.append(payload)

        def post_decision_audit(self, payload):
            return None

        def post_pnl_snapshot(self, payload):
            self.pnl_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "pending",
                "is_live": True,
                "exchange": exchange,
                "order_id": "pending-BTCUSDT",
                "order_status": "PENDING",
                "fill_price": 65000.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
            }

    callback_client = StubCallbackClient()
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-5c",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "live",
            "risk_guard": StubRiskGuard(),
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert result["execution_result"]["status"] == "pending"
    assert callback_client.exchange_order_payloads[0]["status"] == "pending"
    assert callback_client.exchange_order_payloads[0]["executionStatus"] == "pending"
    assert result["execution_result"]["order_status"] == "PENDING"
    assert callback_client.exchange_order_payloads[0]["orderStatus"] == "PENDING"
    assert callback_client.exchange_fill_payloads == []
    assert callback_client.position_payloads == []
    assert callback_client.pnl_payloads[0]["traceId"] == "t-5c"


def test_graph_keeps_success_callbacks_after_router_retry_recovers(monkeypatch):
    class StubRiskGuard:
        def evaluate(self, **kwargs):
            return {"passed": True, "reason": "pass"}

    class StubCallbackClient:
        def __init__(self):
            self.order_payloads = []
            self.position_payloads = []
            self.exchange_order_payloads = []
            self.exchange_fill_payloads = []
            self.pnl_payloads = []

        def post_order_request(self, payload):
            self.order_payloads.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            self.exchange_order_payloads.append(payload)

        def post_exchange_fill(self, payload):
            self.exchange_fill_payloads.append(payload)

        def post_decision_audit(self, payload):
            return None

        def post_pnl_snapshot(self, payload):
            self.pnl_payloads.append(payload)

    captured = {"calls": 0}

    class StubAdapter:
        def __init__(self, client):
            self.client = client

        def place_market_order(self, order):
            captured["calls"] += 1
            if captured["calls"] == 1:
                return {
                    "status": "failed",
                    "is_live": True,
                    "exchange": "binance",
                    "order_id": "",
                    "order_status": "REJECTED",
                    "fill_price": 65000.0,
                    "fill_quantity": 0.0,
                    "position_quantity": 0.0,
                    "entry_price": 65000.0,
                    "error": "network timeout",
                }
            return {
                "status": "filled",
                "is_live": True,
                "exchange": "binance",
                "order_id": "live-BTCUSDT",
                "order_status": "FILLED",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    monkeypatch.setattr("trade_runtime.execution.router.BinanceFuturesExecutionAdapter", StubAdapter)

    callback_client = StubCallbackClient()
    execution_router = ExecutionRouter(binance_client=object(), okx_client=None)
    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-6",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "live",
            "risk_guard": StubRiskGuard(),
            "execution_router": execution_router,
            "callback_client": callback_client,
        }
    )

    assert captured["calls"] == 2
    assert result["execution_result"]["status"] == "filled"
    assert result["execution_result"]["order_id"] == "live-BTCUSDT"
    assert callback_client.exchange_order_payloads[0]["status"] == "filled"
    assert callback_client.exchange_order_payloads[0]["executionStatus"] == "filled"
    assert callback_client.exchange_fill_payloads[0]["orderRef"] == "live-BTCUSDT"
    assert callback_client.position_payloads[0]["positionQuantity"] == 0.0546875
    assert callback_client.pnl_payloads[0]["traceId"] == "t-6"


def test_graph_stamps_stage_timestamps_in_order():
    timestamp_values = iter(
        [
            "2026-04-16T12:00:00.000Z",
            "2026-04-16T12:00:01.000Z",
            "2026-04-16T12:00:02.000Z",
            "2026-04-16T12:00:03.000Z",
            "2026-04-16T12:00:04.000Z",
        ]
    )
    graph = build_decision_graph()

    result = graph.invoke(
        {
            "trace_id": "t-ts-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "paper",
            "timestamp_supplier": lambda: next(timestamp_values),
        }
    )

    assert result["ingestedAt"] == "2026-04-16T12:00:00.000Z"
    assert result["classifiedAt"] == "2026-04-16T12:00:01.000Z"
    assert result["supervisedAt"] == "2026-04-16T12:00:02.000Z"
    assert result["riskCheckedAt"] == "2026-04-16T12:00:03.000Z"
    assert result["executedAt"] == "2026-04-16T12:00:04.000Z"


def test_graph_routes_no_dispatch_directly_to_audit_and_persists_trigger_metadata():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

    callback_client = StubCallbackClient()
    graph = build_decision_graph()

    result = graph.invoke(
        {
            "trace_id": "t-dispatch-none-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 0.1},
            "mode": "shadow",
            "dispatch_mode": "NO_DISPATCH",
            "selected_agents": [],
            "trigger_reason": "below_threshold_noise",
            "trigger_source": "market",
            "active_signals": [{"window_key": "market:BTCUSDT:15m"}],
            "active_signal_refs": ["market:BTCUSDT:15m"],
            "combination_match": {"code": "market_noise_only", "target_dispatch_mode": "NO_DISPATCH"},
            "suppression_reason_codes": ["below_threshold"],
            "rule_only_reason": "below_threshold",
            "callback_client": callback_client,
        }
    )

    assert "market_view" not in result
    assert "supervisor_decision" not in result
    assert "risk_result" not in result
    assert "execution_result" not in result
    assert result["audit_payload"]["dispatch_mode"] == "NO_DISPATCH"
    assert result["audit_payload"]["trigger_reason"] == "below_threshold_noise"
    assert result["audit_payload"]["active_signal_refs"] == ["market:BTCUSDT:15m"]
    assert callback_client.decision_payloads[0]["dispatchMode"] == "NO_DISPATCH"
    assert callback_client.decision_payloads[0]["triggerReason"] == "below_threshold_noise"
    assert callback_client.decision_payloads[0]["triggerSource"] == "market"
    assert callback_client.decision_payloads[0]["selectedAgentsJson"] == "[]"
    assert callback_client.decision_payloads[0]["combinationMatchJson"] == (
        '{"code":"market_noise_only","target_dispatch_mode":"NO_DISPATCH"}'
    )
    assert callback_client.decision_payloads[0]["activeSignalRefsJson"] == '["market:BTCUSDT:15m"]'
    assert callback_client.decision_payloads[0]["executionStatus"] == "skipped"
    assert callback_client.decision_payloads[0]["orderStatus"] == "SKIPPED"


def test_graph_routes_rule_only_through_rule_views_without_llm_or_supervisor(monkeypatch):
    def _unexpected_llm_call(*args, **kwargs):
        raise AssertionError("LLM specialist should not run in RULE_ONLY mode")

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _unexpected_llm_call)
    monkeypatch.setattr("trade_runtime.decision.nodes.news_agent.run_llm_agent", _unexpected_llm_call)
    monkeypatch.setattr("trade_runtime.decision.nodes.onchain_agent.run_llm_agent", _unexpected_llm_call)
    monkeypatch.setattr("trade_runtime.decision.nodes.social_agent.run_llm_agent", _unexpected_llm_call)

    class StubDecisionModelClient:
        def __init__(self):
            self.calls = 0

        def call_model(self, *, model_id, prompt):
            self.calls += 1
            return {"content": "{}"}

    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

    decision_model_client = StubDecisionModelClient()
    callback_client = StubCallbackClient()
    graph = build_decision_graph()

    result = graph.invoke(
        {
            "trace_id": "t-rule-only-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [
                {"event_type": "market_tick", "price": 65000.0},
                {"event_type": "news", "headline": "ETF flow steady", "score": 0.62},
            ],
            "feature_snapshot": {"price_change_pct": 1.2, "news_score": 0.62},
            "mode": "shadow",
            "dispatch_mode": "RULE_ONLY",
            "selected_agents": ["market_agent", "news_agent"],
            "trigger_reason": "normal_news_monitoring",
            "trigger_source": "news",
            "rule_only_reason": "normal_signal",
            "strategy_context": {
                "ai_model_config": {"id": 101, "model_code": "gpt-4.1", "provider": "openai"},
            },
            "agent_profiles": [
                {"agent_code": "market_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "news_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "onchain_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "social_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
            ],
            "decision_model_client": decision_model_client,
            "callback_client": callback_client,
        }
    )

    assert result["market_view"]["reason"] == "price_change_pct=1.2"
    assert "ETF flow steady" in result["news_view"]["reason"]
    assert result["onchain_view"]["reason"] == "no_onchain_signal"
    assert result["social_view"]["reason"] == "no_social_signal"
    assert "supervisor_decision" not in result
    assert "risk_result" not in result
    assert "execution_result" not in result
    assert "supervisedAt" not in result
    assert decision_model_client.calls == 0
    assert callback_client.decision_payloads[0]["dispatchMode"] == "RULE_ONLY"
    assert callback_client.decision_payloads[0]["triggerReason"] == "normal_news_monitoring"
    assert callback_client.decision_payloads[0]["selectedAgentsJson"] == '["market_agent","news_agent"]'
    assert callback_client.decision_payloads[0]["executionStatus"] == "skipped"


def test_graph_llm_allowed_runs_only_selected_specialists_and_falls_back_for_others(monkeypatch):
    llm_calls = []

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        llm_calls.append(agent_code)
        return {
            "bias": "bullish",
            "confidence": 91,
            "reason": "market_llm_selected",
            "ttl": 900,
            "risk_note": "normal",
        }

    def _selected_news_llm(state, *, agent_code, binding_scope, rule_view=None):
        llm_calls.append(agent_code)
        return {
            "bias": "bullish",
            "confidence": 89,
            "reason": "news_llm_selected",
            "ttl": 900,
            "risk_note": "normal",
        }

    def _unexpected_llm_call(*args, **kwargs):
        raise AssertionError("Unselected specialist should not run LLM")

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)
    monkeypatch.setattr("trade_runtime.decision.nodes.news_agent.run_llm_agent", _selected_news_llm)
    monkeypatch.setattr("trade_runtime.decision.nodes.onchain_agent.run_llm_agent", _unexpected_llm_call)
    monkeypatch.setattr("trade_runtime.decision.nodes.social_agent.run_llm_agent", _unexpected_llm_call)

    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-llm-selective-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [
                {"event_type": "market_tick", "price": 65000.0},
                {"event_type": "news", "headline": "ETF approval", "score": 0.95},
            ],
            "feature_snapshot": {"price_change_pct": 3.8, "news_score": 0.95},
            "mode": "paper",
            "dispatch_mode": "LLM_ALLOWED",
            "selected_agents": ["market_agent", "news_agent"],
            "trigger_reason": "strong_news_then_break",
            "trigger_source": "news",
            "agent_profiles": [
                {"agent_code": "market_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "news_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "onchain_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "social_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
            ],
        }
    )

    assert llm_calls == ["market_agent", "news_agent"]
    assert result["market_view"]["reason"] == "market_llm_selected"
    assert result["news_view"]["reason"] == "news_llm_selected"
    assert result["onchain_view"]["reason"] == "no_onchain_signal"
    assert result["social_view"]["reason"] == "no_social_signal"
    assert result["supervisor_decision"]["action"] in {"OPEN_LONG", "OPEN_SHORT", "HOLD", "SKIP"}


def test_graph_allows_llm_flow_when_aux_source_health_is_ready_empty(monkeypatch):
    llm_calls = []

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        llm_calls.append(agent_code)
        return {
            "bias": "bullish",
            "confidence": 91,
            "reason": "market_llm_selected",
            "ttl": 900,
            "risk_note": "normal",
        }

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)

    graph = build_decision_graph()
    result = graph.invoke(
        {
            "trace_id": "t-llm-ready-empty-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [
                {"event_type": "market_tick", "price": 65000.0},
                {"event_type": "source_health", "source_type": "news", "source_status": "ready_empty"},
            ],
            "feature_snapshot": {
                "price_change_pct": 3.8,
                "source_health": {"news": "ready_empty"},
                "degraded_sources": [],
                "aux_source_status": "ready",
            },
            "runtime_config": {"runtime_flags_json": '{"haltOnDataGap": true}'},
            "mode": "paper",
            "dispatch_mode": "LLM_ALLOWED",
            "selected_agents": ["market_agent"],
            "trigger_reason": "market_threshold_met",
            "trigger_source": "market",
            "agent_profiles": [
                {"agent_code": "market_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
            ],
        }
    )

    assert llm_calls == ["market_agent"]
    assert result["market_view"]["reason"] == "market_llm_selected"
    assert result["supervisor_decision"]["action"] in {"OPEN_LONG", "OPEN_SHORT", "HOLD", "SKIP"}


def test_graph_budget_blocked_rule_only_path_remains_auditable():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

    callback_client = StubCallbackClient()
    graph = build_decision_graph()

    result = graph.invoke(
        {
            "trace_id": "t-budget-blocked-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "news", "headline": "ETF rumor", "score": 0.91}],
            "feature_snapshot": {"news_score": 0.91},
            "mode": "shadow",
            "dispatch_mode": "RULE_ONLY",
            "selected_agents": ["news_agent", "market_agent"],
            "trigger_reason": "strong_news_then_break",
            "trigger_source": "news",
            "budget_blocked": True,
            "rule_only_reason": "budget_blocked",
            "suppression_reason_codes": ["budget_blocked"],
            "callback_client": callback_client,
        }
    )

    assert result["audit_payload"]["dispatch_mode"] == "RULE_ONLY"
    assert result["audit_payload"]["budget_blocked"] is True
    assert result["audit_payload"]["suppression_reason_codes"] == ["budget_blocked"]
    assert "supervisor_decision" not in result
    assert callback_client.decision_payloads[0]["dispatchMode"] == "RULE_ONLY"
    assert callback_client.decision_payloads[0]["budgetBlocked"] is True
    assert callback_client.decision_payloads[0]["executionStatus"] == "skipped"


def test_graph_audit_payload_excludes_disabled_specialists_from_runs_and_messages():
    class StubCallbackClient:
        def __init__(self):
            self.decision_payloads = []

        def post_decision_audit(self, payload):
            self.decision_payloads.append(payload)

    callback_client = StubCallbackClient()
    graph = build_decision_graph()

    result = graph.invoke(
        {
            "trace_id": "t-disabled-social-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [
                {"event_type": "market_tick", "price": 65000.0},
                {"event_type": "social", "score": 0.9},
            ],
            "feature_snapshot": {"price_change_pct": 1.3, "social_score": 0.9},
            "mode": "shadow",
            "dispatch_mode": "RULE_ONLY",
            "selected_agents": ["market_agent"],
            "trigger_reason": "social_market_confirmation",
            "trigger_source": "combination",
            "rule_only_reason": "social_agent_disabled",
            "strategy_context": {
                "ai_model_config": {"id": 101, "model_code": "gpt-4.1", "provider": "openai"},
            },
            "agent_profiles": [
                {"agent_code": "market_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "news_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "onchain_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True},
                {"agent_code": "social_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": False},
            ],
            "callback_client": callback_client,
        }
    )

    assert result["social_view"]["reason"] == "no_social_signal"
    payload = callback_client.decision_payloads[0]
    assert [item["agentName"] for item in payload["agentRuns"]] == ["market"]
    assert [item["agentName"] for item in payload["agentObservations"]] == ["market"]
    assert [item["agentName"] for item in payload["agentConclusions"]] == ["market"]
    assert payload["agentMessages"] == []


def test_classify_event_strength_node_uses_runtime_policy_instead_of_hardcoded_threshold():
    state = classify_event_strength(
        {
            "feature_snapshot": {"symbol": "BTCUSDT", "price_change_pct": 1.2},
            "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
            "runtime_config": RuntimeConfig(
                defaultMode="shadow",
                liveEnabled=False,
                runtimeFlagsJson='{"marketTrigger":{"ruleOnlyPriceChangePct":1.0,"priceChangePct":2.5}}',
            ).model_dump(),
            "strategy_context": {},
        }
    )

    assert state["event_strength"] == "normal"

def test_execution_node_posts_canonical_position_side_for_noncanonical_decision_side():
    class StubCallbackClient:
        def __init__(self):
            self.position_snapshot_payloads = []

        def post_position_snapshot(self, payload):
            self.position_snapshot_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "paper-BTCUSDT",
                "fill_price": 64000.0,
                "fill_quantity": 0.01,
                "position_quantity": 0.02,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()

    execution_node(
        {
            "trace_id": "t-position-canonical-side-1",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 64000.0}],
            "current_position_side": "long",
            "current_position_quantity": 0.03,
            "current_position_notional": 3000.0,
            "supervisor_decision": {"action": "REDUCE", "side": "buy", "size_hint": 0.5},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert callback_client.position_snapshot_payloads[0]["side"] == "long"

