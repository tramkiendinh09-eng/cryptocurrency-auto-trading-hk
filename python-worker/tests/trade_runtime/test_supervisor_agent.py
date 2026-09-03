import json

from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent


def test_supervisor_agent_opens_long_when_bullish_views_dominate():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 90, "reason": "ETF inflow"},
        "onchain_view": {"bias": "bearish", "confidence": 75, "reason": "exchange_inflow"},
        "social_view": {"bias": "bullish", "confidence": 70, "reason": "social_score=0.7"},
        "strategy_context": {
            "ai_model_config": {
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["side"] == "long"
    assert result["supervisor_decision"]["confidence"] == 80
    assert "price_breakout" in result["supervisor_decision"]["summary_reason"]
    assert "ETF inflow" in result["supervisor_decision"]["summary_reason"]
    assert result["supervisor_decision"]["model_code"] == "gpt-4.1"
    assert result["supervisor_decision"]["model_provider"] == "openai"
    assert result["agent_messages"][-1]["speaker_agent"] == "supervisor_agent"
    assert result["agent_messages"][-1]["message_type"] == "final_decision"
    assert result["agent_messages"][-1]["content"]["action"] == "OPEN_LONG"


def test_supervisor_agent_skips_when_views_are_balanced():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bullish", "confidence": 60, "reason": "price_rebound"},
        "news_view": {"bias": "bearish", "confidence": 60, "reason": "regulatory_risk"},
        "onchain_view": {"bias": "neutral", "confidence": 50, "reason": "mixed_flow"},
        "social_view": {"bias": "neutral", "confidence": 50, "reason": "flat_social"},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["side"] == "flat"
    assert result["supervisor_decision"]["size_hint"] == 0.0


def test_supervisor_agent_holds_long_when_bullish_views_dominate_existing_long_position():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bullish", "confidence": 85, "reason": "breakout"},
        "news_view": {"bias": "bullish", "confidence": 80, "reason": "etf_inflow"},
        "current_position_side": "long",
        "current_position_quantity": 0.25,
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "HOLD"
    assert result["supervisor_decision"]["side"] == "long"


def test_supervisor_agent_closes_short_when_bullish_views_dominate_existing_short_position():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bullish", "confidence": 85, "reason": "breakout"},
        "news_view": {"bias": "bullish", "confidence": 80, "reason": "etf_inflow"},
        "current_position_side": "short",
        "current_position_quantity": 0.25,
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "CLOSE"
    assert result["supervisor_decision"]["side"] == "short"


def test_supervisor_agent_reduces_position_when_views_are_balanced_but_position_exists():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bullish", "confidence": 60, "reason": "price_rebound"},
        "news_view": {"bias": "bearish", "confidence": 60, "reason": "regulatory_risk"},
        "current_position_side": "long",
        "current_position_quantity": 0.25,
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "REDUCE"
    assert result["supervisor_decision"]["side"] == "long"


def test_supervisor_agent_holds_short_when_bearish_views_dominate_existing_short_position():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bearish", "confidence": 84, "reason": "breakdown"},
        "news_view": {"bias": "bearish", "confidence": 79, "reason": "risk_off"},
        "current_position_side": "short",
        "current_position_quantity": 0.25,
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "HOLD"
    assert result["supervisor_decision"]["side"] == "short"


def test_supervisor_agent_skips_when_ai_model_config_is_disabled():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bullish", "confidence": 88, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 82, "reason": "ETF inflow"},
        "strategy_context": {
            "ai_model_config": {
                "model_code": "gpt-4.1",
                "provider": "openai",
                "is_enabled": 0,
            }
        },
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["side"] == "flat"
    assert result["supervisor_decision"]["size_hint"] == 0.0
    assert result["supervisor_decision"]["summary_reason"] == "ai_model_unavailable"


def test_supervisor_agent_uses_rule_aggregation_when_rule_only_policy_enables_supervisor():
    state = {
        "dispatch_mode": "RULE_ONLY",
        "market_view": {"bias": "bullish", "confidence": 88, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 76, "reason": "ETF inflow"},
        "supervisor_policy": {"enabledWhen": "RULE_ONLY"},
        "strategy_context": {
            "ai_model_config": {
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["side"] == "long"
    assert "price_breakout" in result["supervisor_decision"]["summary_reason"]
    assert result["agent_messages"][-1]["speaker_agent"] == "supervisor_agent"
    assert result["agent_messages"][-1]["message_type"] == "final_decision"


def test_supervisor_agent_uses_runtime_model_client_when_available():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": 31,
                "modelCode": "gpt-4.1",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"OPEN_LONG\",\"side\":\"long\",\"confidence\":91,"
                    "\"size_hint\":0.42,\"leverage_hint\":4,\"holding_window\":\"15m-1h\","
                    "\"invalidation\":\"below 65000\",\"summary_reason\":\"multi_agent_resonance\"}"
                ),
            }

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 90, "reason": "ETF inflow"},
        "onchain_view": {"bias": "neutral", "confidence": 55, "reason": "mixed_flow"},
        "social_view": {"bias": "bullish", "confidence": 70, "reason": "social_score=0.7"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }

    result = supervisor_agent(state)

    assert captured["model_id"] == 31
    assert "price_breakout" in captured["prompt"]
    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["side"] == "long"
    assert result["supervisor_decision"]["confidence"] == 91
    assert result["supervisor_decision"]["size_hint"] == 0.42
    assert result["supervisor_decision"]["leverage_hint"] == 4
    assert result["supervisor_decision"]["holding_window"] == "15m-1h"
    assert result["supervisor_decision"]["invalidation"] == "below 65000"
    assert result["supervisor_decision"]["summary_reason"] == "multi_agent_resonance"
    assert result["supervisor_decision"]["model_code"] == "gpt-4.1"
    assert result["supervisor_decision"]["model_provider"] == "openai"


def test_supervisor_agent_does_not_short_circuit_on_referee_review():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-supervisor",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"HOLD\",\"side\":\"long\",\"confidence\":82,"
                    "\"size_hint\":0.0,\"leverage_hint\":2,\"holding_window\":\"15m-1h\","
                    "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"supervisor_final\"}"
                ),
            }

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "current_position_side": "long",
        "current_position_quantity": 0.2,
        "market_view": {"bias": "bullish", "confidence": 70, "reason": "price_holds_range"},
        "onchain_view": {"bias": "bearish", "confidence": 75, "reason": "exchange_inflow"},
        "agent_messages": [
            {
                "round_no": 1,
                "speaker_agent": "deliberation_referee",
                "target_agent": "supervisor_agent",
                "message_type": "referee_review",
                "content": {"summary_reason": "referee_review_only"},
                "summary_text": "referee_review_only",
            }
        ],
        "deliberation_summary": "conflicting_specialist_views_detected",
        "deliberation_referee_review": {"summary_reason": "referee_review_only"},
        "deliberation_decision": {"action": "CLOSE", "summary_reason": "legacy_referee_final"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-supervisor",
                "provider": "openai",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }

    result = supervisor_agent(state)

    assert captured["model_id"] == 31
    assert "referee_review_only" in captured["prompt"]
    assert "conflicting_specialist_views_detected" in captured["prompt"]
    assert result["supervisor_decision"]["summary_reason"] == "supervisor_final"
    assert result["agent_messages"][-1]["speaker_agent"] == "supervisor_agent"
    assert result["agent_messages"][-1]["message_type"] == "final_decision"
    assert result["agent_messages"][-1]["content"]["summary_reason"] == "supervisor_final"


def test_supervisor_agent_fails_closed_when_model_output_is_invalid():
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1",
                "modelProvider": "openai",
                "content": "not-json",
            }

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 90, "reason": "ETF inflow"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }

    result = supervisor_agent(state)

    assert result["ai_call_failed"] is True
    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["side"] == "flat"
    assert result["supervisor_decision"]["summary_reason"] == "ai_model_call_failed_fail_closed"
    assert result["supervisor_decision"]["model_code"] == "gpt-4.1"
    assert result["supervisor_decision"]["model_provider"] == "openai"
    assert result["agent_llm_errors"][0]["agent_code"] == "supervisor_agent"
    assert result["agent_llm_errors"][0]["error"] == "invalid_supervisor_decision_content"


def test_supervisor_agent_can_fall_back_to_rule_decision_after_model_failure():
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            raise RuntimeError("model gateway timeout")

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "runtime_config": {"supervisor_ai_fail_open": True, "max_position_ratio": 0.25},
        "account_equity": 10000.0,
        "current_position_side": "flat",
        "current_position_quantity": 0.0,
        "current_position_notional": 0.0,
        "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 90, "reason": "ETF inflow"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }

    result = supervisor_agent(state)

    assert result["ai_call_failed"] is True
    assert result["agent_llm_errors"][0]["agent_code"] == "supervisor_agent"
    assert result["agent_llm_errors"][0]["error"] == "model gateway timeout"
    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["side"] == "long"
    assert result["supervisor_decision"]["size_hint"] == 0.25
    assert "price_breakout" in result["supervisor_decision"]["summary_reason"]


def test_supervisor_agent_accepts_fenced_json_and_clamps_open_position_to_runtime_limit():
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1",
                "modelProvider": "openai",
                "content": """```json
{"action":"OPEN_LONG","side":"long","confidence":91,"size_hint":0.35,"leverage_hint":4,"holding_window":"15m-1h","invalidation":"below 65000","summary_reason":"fenced_json_response"}
```""",
            }

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-fenced-json-clamp",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "strong",
        "account_equity": 10000.0,
        "current_position_side": "flat",
        "current_position_quantity": 0.0,
        "current_position_notional": 0.0,
        "runtime_config": {
            "max_position_ratio": 0.25,
        },
        "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 90, "reason": "ETF inflow"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["summary_reason"] == "fenced_json_response"
    assert result["supervisor_decision"]["size_hint"] == 0.25


def test_supervisor_agent_clamps_add_position_to_remaining_headroom():
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"ADD_LONG\",\"side\":\"long\",\"confidence\":87,"
                    "\"size_hint\":0.20,\"leverage_hint\":3,\"holding_window\":\"15m-4h\","
                    "\"invalidation\":\"below support\",\"summary_reason\":\"headroom_clamp\"}"
                ),
            }

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-add-headroom-clamp",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "strong",
        "account_equity": 10000.0,
        "current_position_side": "long",
        "current_position_quantity": 0.1,
        "current_position_notional": 1500.0,
        "runtime_config": {
            "max_position_ratio": 0.25,
        },
        "market_view": {"bias": "bullish", "confidence": 85, "reason": "breakout"},
        "news_view": {"bias": "bullish", "confidence": 80, "reason": "etf_inflow"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "ADD_LONG"
    assert result["supervisor_decision"]["size_hint"] == 0.10


def test_supervisor_agent_normalizes_add_to_hold_when_long_position_has_no_remaining_headroom():
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"ADD_LONG\",\"side\":\"long\",\"confidence\":87,"
                    "\"size_hint\":0.20,\"leverage_hint\":3,\"holding_window\":\"15m-4h\","
                    "\"invalidation\":\"below support\",\"summary_reason\":\"headroom_exhausted\"}"
                ),
            }

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-add-no-headroom",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "strong",
        "account_equity": 10000.0,
        "current_position_side": "long",
        "current_position_quantity": 0.1,
        "current_position_notional": 2500.0,
        "runtime_config": {
            "max_position_ratio": 0.25,
        },
        "market_view": {"bias": "bullish", "confidence": 85, "reason": "breakout"},
        "news_view": {"bias": "bullish", "confidence": 80, "reason": "etf_inflow"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "HOLD"
    assert result["supervisor_decision"]["side"] == "long"
    assert result["supervisor_decision"]["size_hint"] == 0.0


def test_supervisor_agent_records_specialist_handoff_messages_for_audit_transcript():
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-specialist-handoff",
        "market_view": {
            "bias": "bullish",
            "confidence": 80,
            "reason": "price_breakout",
            "template_code": "trade.market.v1",
            "model_code": "gpt-4.1-mini",
        },
        "news_view": {
            "bias": "bullish",
            "confidence": 90,
            "reason": "ETF inflow",
            "template_code": "trade.news.v1",
            "model_code": "gpt-4.1-mini",
        },
        "onchain_view": {"bias": "neutral", "confidence": 55, "reason": "mixed_flow"},
        "social_view": {"bias": "bullish", "confidence": 70, "reason": "social_score=0.7"},
        "agent_profiles": [
            {"agent_code": "news_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 1},
            {"agent_code": "market_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 2},
            {"agent_code": "social_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 3},
            {"agent_code": "onchain_agent", "enabled": True, "dialogue_enabled": True, "speak_order": 4},
        ],
    }

    result = supervisor_agent(state)

    handoff_messages = result["agent_messages"]
    assert [message["speaker_agent"] for message in handoff_messages[:4]] == [
        "news_agent",
        "market_agent",
        "social_agent",
        "onchain_agent",
    ]
    assert all(message["target_agent"] == "supervisor_agent" for message in handoff_messages[:4])
    assert all(message["message_type"] == "conclusion" for message in handoff_messages[:4])
    assert handoff_messages[0]["template_code"] == "trade.news.v1"
    assert handoff_messages[0]["model_code"] == "gpt-4.1-mini"
    assert handoff_messages[1]["template_code"] == "trade.market.v1"
    assert handoff_messages[1]["model_code"] == "gpt-4.1-mini"
    assert handoff_messages[-1]["speaker_agent"] == "supervisor_agent"
    assert handoff_messages[-1]["message_type"] == "final_decision"


def test_supervisor_agent_uses_prompt_binding_template_and_binding_model_id_when_available():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"OPEN_LONG\",\"side\":\"long\",\"confidence\":93,"
                    "\"size_hint\":0.55,\"leverage_hint\":3,\"holding_window\":\"15m-2h\","
                    "\"invalidation\":\"loss_of_breakout\",\"summary_reason\":\"template_driven_supervisor\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.v1":
                return {
                    "code": template_code,
                    "content": "Supervisor template {symbol} {market_view_json}",
                }
            return None

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-supervisor-template",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "strong",
        "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_breakout"},
        "news_view": {"bias": "bullish", "confidence": 90, "reason": "ETF inflow"},
        "onchain_view": {"bias": "neutral", "confidence": 55, "reason": "mixed_flow"},
        "social_view": {"bias": "bullish", "confidence": 70, "reason": "social_score=0.7"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "prompt_bindings": [
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.v1",
                "fallback_template_code": "trade.supervisor.fallback",
                "model_id": 77,
                "priority": 10,
                "enabled": True,
                "mode_scope_json": "[\"shadow\"]",
                "event_strength_scope_json": "[\"strong\"]",
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = supervisor_agent(state)

    assert captured["model_id"] == 77
    assert "Supervisor template BTCUSDT" in captured["prompt"]
    assert "price_breakout" in captured["prompt"]
    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["confidence"] == 93
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.v1"
    assert result["supervisor_prompt_metadata"]["prompt_template_fallback_used"] is False



def test_supervisor_agent_prompt_includes_recent_specialist_context_memory():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"HOLD\",\"side\":\"long\",\"confidence\":68,"
                    "\"size_hint\":\"current\",\"leverage_hint\":\"current\",\"holding_window\":\"30m\","
                    "\"invalidation\":\"breakdown\",\"summary_reason\":\"recent memory included\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.v1":
                return {
                    "code": template_code,
                    "content": "Recent news {recent_news_context_json} Recent onchain {recent_onchain_context_json}",
                }
            return None

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-supervisor-recent-context",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "event_strength": "strong",
        "market_view": {"bias": "neutral", "confidence": 60, "reason": "flat"},
        "news_view": {"bias": "bullish", "confidence": 75, "reason": "4 news events"},
        "onchain_view": {"bias": "bullish", "confidence": 75, "reason": "net_outflow"},
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.7},
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "Whales add longs", "score": 0.8},
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_outflow", "amountUsd": 213000000},
        ],
        "resolved_agent_configs": [
            {
                "agent_code": "supervisor_agent",
                "model_id": 77,
                "model_code": "gpt-4.1-mini",
                "model_provider": "openai",
                "template_code": "trade.supervisor.v1",
                "output_schema_code": "supervisor_decision_v1",
                "enabled": True,
                "llm_enabled": True,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = supervisor_agent(state)

    assert captured["model_id"] == 77
    assert "\"event_count\": 2" in captured["prompt"]
    assert "Whales add longs" in captured["prompt"]
    assert "\"net_flow_usd\": 213000000.0" in captured["prompt"]
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.v1"

def test_supervisor_agent_prefers_resolved_agent_config_over_legacy_binding():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "deepseek-reasoner",
                "modelProvider": "deepseek",
                "content": (
                    "{\"action\":\"OPEN_LONG\",\"side\":\"long\",\"confidence\":91,"
                    "\"size_hint\":0.45,\"leverage_hint\":2,\"holding_window\":\"15m-1h\","
                    "\"invalidation\":\"lost momentum\",\"summary_reason\":\"resolved_config_prompt\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.resolved":
                return {
                    "code": template_code,
                    "content": "Resolved supervisor template {symbol} {market_view_json}",
                }
            if template_code == "trade.supervisor.legacy":
                return {
                    "code": template_code,
                    "content": "Legacy supervisor template {symbol}",
                }
            return None

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-supervisor-resolved-config",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "shadow",
        "event_strength": "strong",
        "market_view": {"bias": "bullish", "confidence": 80, "reason": "price_breakout"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "resolved_agent_configs": [
            {
                "agent_code": "supervisor_agent",
                "model_id": 88,
                "model_code": "deepseek-reasoner",
                "model_provider": "deepseek",
                "template_code": "trade.supervisor.resolved",
                "fallback_template_code": "trade.supervisor.resolved.fallback",
                "output_schema_code": "supervisor_decision_v1",
                "resolution_source": "PROFILE_DEFAULT",
                "enabled": True,
                "llm_enabled": True,
            }
        ],
        "prompt_bindings": [
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.legacy",
                "model_id": 77,
                "priority": 10,
                "enabled": True,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = supervisor_agent(state)

    assert captured["model_id"] == 88
    assert "Resolved supervisor template BTCUSDT" in captured["prompt"]
    assert "Legacy supervisor template" not in captured["prompt"]
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.resolved"
    assert result["supervisor_prompt_metadata"]["model_id"] == 88
    assert result["supervisor_decision"]["model_code"] == "deepseek-reasoner"


def test_supervisor_agent_uses_fallback_template_when_primary_template_is_missing():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"SKIP\",\"side\":\"flat\",\"confidence\":51,"
                    "\"size_hint\":0.0,\"leverage_hint\":3,\"holding_window\":\"15m-4h\","
                    "\"invalidation\":\"\",\"summary_reason\":\"fallback_template_used\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.fallback":
                return {
                    "code": template_code,
                    "content": "Fallback template {symbol}",
                }
            return None

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-supervisor-fallback-template",
        "symbol": "ETHUSDT",
        "exchange": "okx",
        "mode": "shadow",
        "event_strength": "normal",
        "market_view": {"bias": "neutral", "confidence": 50, "reason": "flat_market"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "prompt_bindings": [
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.v1",
                "fallback_template_code": "trade.supervisor.fallback",
                "priority": 10,
                "enabled": True,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = supervisor_agent(state)

    assert "Fallback template ETHUSDT" in captured["prompt"]
    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.fallback"
    assert result["supervisor_prompt_metadata"]["prompt_template_fallback_used"] is True


def test_supervisor_agent_falls_back_to_inline_prompt_when_templates_are_unavailable():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"OPEN_SHORT\",\"side\":\"short\",\"confidence\":88,"
                    "\"size_hint\":0.4,\"leverage_hint\":3,\"holding_window\":\"15m-1h\","
                    "\"invalidation\":\"above resistance\",\"summary_reason\":\"inline_prompt_fallback\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            return None

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "trace_id": "trace-supervisor-inline-fallback",
        "symbol": "SOLUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "normal",
        "account_equity": 12500.0,
        "daily_pnl": -123.45,
        "current_position_side": "flat",
        "current_position_quantity": 0.0,
        "current_position_notional": 0.0,
        "runtime_config": {
            "max_position_ratio": 0.4,
        },
        "market_view": {"bias": "bearish", "confidence": 88, "reason": "failed_breakout"},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "prompt_bindings": [
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.v1",
                "fallback_template_code": "trade.supervisor.fallback",
                "priority": 10,
                "enabled": True,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = supervisor_agent(state)

    assert captured["model_id"] == 31
    assert "You are the trading supervisor." in captured["prompt"]
    assert "\"account_equity\": 12500.0" in captured["prompt"]
    assert "\"daily_pnl\": -123.45" in captured["prompt"]
    assert "\"current_position_notional\": 0.0" in captured["prompt"]
    assert "\"max_position_ratio\": 0.4" in captured["prompt"]
    assert result["supervisor_decision"]["action"] == "OPEN_SHORT"
    assert result["supervisor_prompt_metadata"]["prompt_source"] == "inline"
    assert result["supervisor_prompt_metadata"]["prompt_template_fallback_used"] is True

def _supervisor_state_with_model_content(content, **overrides):
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelId": model_id,
                "modelCode": "deepseek-reasoner",
                "modelProvider": "deepseek",
                "content": content,
            }

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "deepseek-reasoner",
                "provider": "deepseek",
            }
        },
        "decision_model_client": StubDecisionModelClient(),
    }
    state.update(overrides)
    return state


def test_supervisor_agent_normalizes_model_enter_buy_to_open_long_when_flat():
    state = _supervisor_state_with_model_content(
        "{\"action\":\"enter\",\"side\":\"buy\",\"confidence\":82,"
        "\"size_hint\":0.35,\"summary_reason\":\"model synonym\"}",
        current_position_side="flat",
        current_position_quantity=0.0,
    )

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["side"] == "long"


def test_supervisor_agent_holds_existing_long_on_ambiguous_increase_buy():
    state = _supervisor_state_with_model_content(
        "{\"action\":\"increase\",\"side\":\"buy\",\"confidence\":76,"
        "\"size_hint\":0.5,\"summary_reason\":\"model synonym\"}",
        current_position_side="long",
        current_position_quantity=0.2,
        current_position_notional=2000.0,
        account_equity=10000.0,
        runtime_config={"max_position_ratio": 0.5},
    )

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "HOLD"
    assert result["supervisor_decision"]["side"] == "long"
    assert result["supervisor_decision"]["size_hint"] == 0.0


def test_supervisor_agent_normalizes_model_adjust_sell_to_reduce_existing_long():
    state = _supervisor_state_with_model_content(
        "{\"action\":\"adjust\",\"side\":\"sell\",\"confidence\":78,"
        "\"size_hint\":0.4,\"summary_reason\":\"model synonym\"}",
        current_position_side="long",
        current_position_quantity=0.2,
        current_position_notional=2000.0,
    )

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "REDUCE"
    assert result["supervisor_decision"]["side"] == "long"


def test_supervisor_agent_normalizes_model_reduce_buy_to_reduce_current_long_side():
    state = _supervisor_state_with_model_content(
        "{\"action\":\"reduce\",\"side\":\"buy\",\"confidence\":80,"
        "\"size_hint\":0.5,\"summary_reason\":\"risk limit\"}",
        current_position_side="long",
        current_position_quantity=0.3,
        current_position_notional=3000.0,
    )

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "REDUCE"
    assert result["supervisor_decision"]["side"] == "long"


def test_supervisor_agent_escalates_reduce_to_close_when_invalidation_is_breached():
    state = _supervisor_state_with_model_content(
        "{\"action\":\"REDUCE\",\"side\":\"short\",\"confidence\":82,"
        "\"size_hint\":0.5,\"invalidation\":\"break above 2140 invalidates short\","
        "\"summary_reason\":\"trim losing short\"}",
        current_position_side="short",
        current_position_quantity=0.3,
        current_position_notional=6000.0,
        market_view={"bias": "bullish", "confidence": 84, "reason": "breakout continuation"},
        news_view={"bias": "bullish", "confidence": 73, "reason": "macro tailwind"},
        feature_snapshot={"position_risk_context": {"current_price": 2142.93}},
        position_risk_result={"triggered": True, "severity": "reduce", "reason": "structure_reversal"},
    )

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "CLOSE"
    assert result["supervisor_decision"]["side"] == "short"
    assert result["supervisor_decision"]["size_hint"] == 1.0
    assert result["supervisor_exit_escalation"]["reason"] == "invalidation_breached"



def test_supervisor_render_context_includes_memory_json():
    from trade_runtime.prompting.render_context_builder import build_supervisor_render_context

    state = {
        "trace_id": "trace-1",
        "symbol": "BTCUSDT",
        "short_term_memory": {"news": {"sample_count": 2, "items": []}},
        "long_term_memory": {
            "status": "ready",
            "items": [
                {
                    "id": 1,
                    "agent_code": "supervisor_agent",
                    "memory_type": "lesson",
                    "lesson_text": "Wait for price-volume confirmation before adding risk.",
                    "event_tags": ["risk_control", "breakout"],
                    "quality_score": 0.88,
                    "confidence": 0.82,
                    "evidence_json": {"text": "Breakout failed without expanding volume."},
                    "outcome_json": {"final_move_pct": -1.6, "verdict": "loss"},
                }
            ],
            "selected_count": 1,
        },
        "memory_usage": {"used_memory_ids": [1]},
    }

    context = build_supervisor_render_context(state)
    long_term_memory = json.loads(context["long_term_memory_json"])

    assert "short_term_memory_json" in context
    assert "long_term_memory_json" in context
    assert "memory_usage_json" in context
    assert long_term_memory["experience_items"][0]["memory_id"] == 1
    assert long_term_memory["experience_items"][0]["lesson"] == "Wait for price-volume confirmation before adding risk."
    assert "risk_control" in long_term_memory["experience_items"][0]["experience_text"]
    assert "final_move_pct=-1.6" in long_term_memory["experience_items"][0]["experience_text"]


def test_supervisor_render_context_includes_current_position_opened_at():
    from trade_runtime.prompting.render_context_builder import build_supervisor_render_context

    context = build_supervisor_render_context(
        {
            "trace_id": "trace-opened-at-1",
            "symbol": "BTCUSDT",
            "current_position_opened_at": "2026-05-05T16:30:12Z",
            "current_time": "2026-05-05T17:00:12Z",
            "current_position_holding_minutes": 30,
        }
    )

    assert context["current_position_opened_at"] == "2026-05-05T16:30:12Z"
    assert context["current_time"] == "2026-05-05T17:00:12Z"
    assert context["current_position_holding_minutes"] == 30


def test_normalize_recent_supervisor_decisions_keeps_two_identical_decisions():
    from trade_runtime.decision.nodes.supervisor_agent import _normalize_recent_supervisor_decisions

    history = [
        {
            "traceId": "trace-history-2",
            "contentJson": (
                "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":58,"
                "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                "\"invalidation\":\"range_break_above_2210\",\"summary_reason\":\"hold_range_short\"}"
            ),
        },
        {
            "traceId": "trace-history-1",
            "contentJson": (
                "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":58,"
                "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                "\"invalidation\":\"range_break_above_2210\",\"summary_reason\":\"hold_range_short\"}"
            ),
        },
    ]

    normalized = _normalize_recent_supervisor_decisions(history, limit=2)

    assert len(normalized) == 2
    assert normalized[0]["summary_reason"] == "hold_range_short"
    assert normalized[1]["summary_reason"] == "hold_range_short"


def test_supervisor_render_context_includes_previous_supervisor_decisions_json():
    from trade_runtime.prompting.render_context_builder import build_supervisor_render_context

    context = build_supervisor_render_context(
        {
            "trace_id": "trace-history-1",
            "symbol": "BTCUSDT",
            "recent_supervisor_decisions": [
                {
                    "action": "HOLD",
                    "side": "short",
                    "confidence": 58,
                    "size_hint": 0,
                    "leverage_hint": 1,
                    "holding_window": "15m-240m",
                    "invalidation": "range_break_above_2210",
                    "summary_reason": "hold_range_short",
                },
                {
                    "action": "SKIP",
                    "side": "flat",
                    "confidence": 44,
                    "size_hint": 0,
                    "leverage_hint": 1,
                    "holding_window": "15m-240m",
                    "invalidation": "no_trade_condition",
                    "summary_reason": "wait_for_breakout",
                },
            ],
        }
    )

    assert "previous_supervisor_decisions_json" in context
    assert "\"action\": \"HOLD\"" in context["previous_supervisor_decisions_json"]
    assert "\"summary_reason\": \"wait_for_breakout\"" in context["previous_supervisor_decisions_json"]


def test_supervisor_agent_renders_current_position_opened_at_in_template_prompt():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"HOLD\",\"side\":\"long\",\"confidence\":72,"
                    "\"size_hint\":0,\"leverage_hint\":2,\"holding_window\":\"15m-1h\","
                    "\"invalidation\":\"below support\",\"summary_reason\":\"opened_at_visible\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.v1":
                return {
                    "code": template_code,
                    "content": (
                        "Opened at {current_position_opened_at}; "
                        "Current time {current_time}; "
                        "Holding minutes {current_position_holding_minutes}"
                    ),
                }
            return None

    result = supervisor_agent(
        {
            "dispatch_mode": "LLM_ALLOWED",
            "trace_id": "trace-supervisor-opened-at",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "event_strength": "strong",
            "current_position_side": "long",
            "current_position_quantity": 0.25,
            "current_position_opened_at": "2026-05-05T16:30:12Z",
            "current_time": "2026-05-05T17:00:12Z",
            "current_position_holding_minutes": 30,
            "market_view": {"bias": "bullish", "confidence": 78, "reason": "breakout"},
            "strategy_context": {
                "ai_model_config": {
                    "id": 31,
                    "model_code": "gpt-4.1",
                    "provider": "openai",
                }
            },
            "prompt_bindings": [
                {
                    "binding_scope": "SUPERVISOR",
                    "template_code": "trade.supervisor.v1",
                    "model_id": 77,
                    "priority": 10,
                    "enabled": True,
                }
            ],
            "decision_model_client": StubDecisionModelClient(),
            "prompt_template_registry": StubPromptTemplateRegistry(),
        }
    )

    assert captured["model_id"] == 77
    assert "Opened at 2026-05-05T16:30:12Z; Current time 2026-05-05T17:00:12Z; Holding minutes 30" in captured["prompt"]
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.v1"


def test_supervisor_agent_uses_mode_scoped_history_from_callback_client():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":66,"
                    "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-4h\","
                    "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"history_visible\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.v1":
                return {
                    "code": template_code,
                    "content": "《上次决策记录》\n{previous_supervisor_decisions_json}",
                }
            return None

    class StubCallbackClient:
        def get_recent_supervisor_decisions(self, symbol, *, limit=2, exclude_trace_id="", mode=""):
            assert symbol == "BTCUSDT"
            assert limit == 2
            assert exclude_trace_id == "trace-supervisor-history"
            # mode参数不再匹配,改为空字符串以避免mode不匹配导致查询不到数据
            assert mode == ""
            return [
                {
                    "traceId": "trace-previous-2",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":58,"
                        "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                        "\"invalidation\":\"range_break_above_2210\",\"summary_reason\":\"hold_range_short\"}"
                    ),
                },
                {
                    "traceId": "trace-previous-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"SKIP\",\"side\":\"flat\",\"confidence\":41,"
                        "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                        "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"wait_for_breakout\"}"
                    ),
                },
            ]

    result = supervisor_agent(
        {
            "dispatch_mode": "LLM_ALLOWED",
            "trace_id": "trace-supervisor-history",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "event_strength": "strong",
            "current_position_side": "short",
            "current_position_quantity": 0.25,
            "strategy_context": {
                "ai_model_config": {
                    "id": 31,
                    "model_code": "gpt-4.1",
                    "provider": "openai",
                }
            },
            "prompt_bindings": [
                {
                    "binding_scope": "SUPERVISOR",
                    "template_code": "trade.supervisor.v1",
                    "model_id": 77,
                    "priority": 10,
                    "enabled": True,
                }
            ],
            "decision_model_client": StubDecisionModelClient(),
            "prompt_template_registry": StubPromptTemplateRegistry(),
            "callback_client": StubCallbackClient(),
        }
    )

    assert captured["model_id"] == 77
    assert "《上次决策记录》" in captured["prompt"]
    assert "\"action\": \"HOLD\"" in captured["prompt"]
    assert "\"summary_reason\": \"wait_for_breakout\"" in captured["prompt"]
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.v1"


def test_supervisor_agent_renders_previous_supervisor_decisions_in_template_prompt():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":66,"
                    "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-4h\","
                    "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"history_visible\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.v1":
                return {
                    "code": template_code,
                    "content": "《上次决策记录》\n{previous_supervisor_decisions_json}",
                }
            return None

    class StubCallbackClient:
        def get_recent_supervisor_decisions(self, symbol, *, limit=2, exclude_trace_id="", mode=""):
            assert symbol == "BTCUSDT"
            assert limit == 2
            assert exclude_trace_id == "trace-supervisor-history"
            # mode参数不再匹配,改为空字符串以避免mode不匹配导致查询不到数据
            assert mode == ""
            return [
                {
                    "traceId": "trace-previous-2",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":58,"
                        "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                        "\"invalidation\":\"range_break_above_2210\",\"summary_reason\":\"hold_range_short\"}"
                    ),
                },
                {
                    "traceId": "trace-previous-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"SKIP\",\"side\":\"flat\",\"confidence\":41,"
                        "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                        "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"wait_for_breakout\"}"
                    ),
                },
            ]

    result = supervisor_agent(
        {
            "dispatch_mode": "LLM_ALLOWED",
            "trace_id": "trace-supervisor-history",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "event_strength": "strong",
            "current_position_side": "short",
            "current_position_quantity": 0.25,
            "strategy_context": {
                "ai_model_config": {
                    "id": 31,
                    "model_code": "gpt-4.1",
                    "provider": "openai",
                }
            },
            "prompt_bindings": [
                {
                    "binding_scope": "SUPERVISOR",
                    "template_code": "trade.supervisor.v1",
                    "model_id": 77,
                    "priority": 10,
                    "enabled": True,
                }
            ],
            "decision_model_client": StubDecisionModelClient(),
            "prompt_template_registry": StubPromptTemplateRegistry(),
            "callback_client": StubCallbackClient(),
        }
    )

    assert captured["model_id"] == 77
    assert "《上次决策记录》" in captured["prompt"]
    assert "\"action\": \"HOLD\"" in captured["prompt"]
    assert "\"summary_reason\": \"wait_for_breakout\"" in captured["prompt"]
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.v1"


def test_supervisor_agent_accepts_decision_run_fallback_history_from_callback_client():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": (
                    "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":66,"
                    "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-4h\","
                    "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"history_visible\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.supervisor.v1":
                return {
                    "code": template_code,
                    "content": "《上次决策记录》\n{previous_supervisor_decisions_json}",
                }
            return None

    class StubCallbackClient:
        def get_recent_supervisor_decisions(self, symbol, *, limit=2, exclude_trace_id="", mode=""):
            assert symbol == "BTCUSDT"
            assert limit == 2
            assert exclude_trace_id == "trace-supervisor-history-fallback"
            assert mode == ""
            return [
                {
                    "traceId": "trace-run-only-2",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": "{\"action\":\"HOLD\",\"confidence\":65,\"summary_reason\":\"hold_range_short\"}",
                    "createdAt": "2026-05-18 18:00:00",
                },
                {
                    "traceId": "trace-run-only-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": "{\"action\":\"SKIP\",\"confidence\":41,\"summary_reason\":\"wait_for_breakout\"}",
                    "createdAt": "2026-05-18 17:00:00",
                },
            ]

    result = supervisor_agent(
        {
            "dispatch_mode": "LLM_ALLOWED",
            "trace_id": "trace-supervisor-history-fallback",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "mode": "paper",
            "event_strength": "strong",
            "current_time": "2026-05-18T10:05:00Z",
            "current_position_side": "short",
            "current_position_quantity": 0.25,
            "strategy_context": {
                "ai_model_config": {
                    "id": 31,
                    "model_code": "gpt-4.1",
                    "provider": "openai",
                }
            },
            "prompt_bindings": [
                {
                    "binding_scope": "SUPERVISOR",
                    "template_code": "trade.supervisor.v1",
                    "model_id": 77,
                    "priority": 10,
                    "enabled": True,
                }
            ],
            "decision_model_client": StubDecisionModelClient(),
            "prompt_template_registry": StubPromptTemplateRegistry(),
            "callback_client": StubCallbackClient(),
        }
    )

    assert captured["model_id"] == 77
    assert "《上次决策记录》" in captured["prompt"]
    assert "\"action\": \"HOLD\"" in captured["prompt"]
    assert "\"confidence\": 41" in captured["prompt"]
    assert "\"side\": \"short\"" in captured["prompt"]
    assert "\"size_hint\": 0.0" in captured["prompt"]
    assert "\"leverage_hint\": 1" in captured["prompt"]
    assert "\"holding_window\": \"15m-4h\"" in captured["prompt"]
    assert "\"invalidation\": \"no_trade_condition\"" in captured["prompt"]
    assert "\"summary_reason\": \"wait_for_breakout\"" in captured["prompt"]
    assert result["recent_supervisor_decisions"] == [
        {
            "action": "HOLD",
            "side": "short",
            "confidence": 65,
            "size_hint": 0.0,
            "leverage_hint": 1,
            "holding_window": "15m-4h",
            "invalidation": "no_trade_condition",
            "summary_reason": "hold_range_short",
        },
        {
            "action": "SKIP",
            "side": "flat",
            "confidence": 41,
            "size_hint": 0.0,
            "leverage_hint": 1,
            "holding_window": "15m-4h",
            "invalidation": "no_trade_condition",
            "summary_reason": "wait_for_breakout",
        },
    ]
    assert result["short_term_memory"]["supervisor_decision"]["sample_count"] == 2
    assert result["short_term_memory"]["supervisor_decision"]["items"][0]["summary_reason"] == "hold_range_short"
    assert result["memory_usage"]["short_term_counts"]["supervisor_decision"] == 2
    assert result["supervisor_prompt_metadata"]["resolved_template_code"] == "trade.supervisor.v1"


def test_inline_supervisor_prompt_hides_internal_model_routing():
    from trade_runtime.decision.nodes.supervisor_agent import _build_supervisor_prompt

    prompt = _build_supervisor_prompt(
        {
            "symbol": "BTCUSDT",
            "strategy_context": {
                "strategy_config": {"riskMode": "normal"},
                "ai_model_config": {"id": 31, "model_code": "gpt-4.1", "provider": "openai"},
                "prompt_bindings": [{"model_id": 31}],
                "resolved_agent_configs": [{"agent_code": "supervisor_agent", "model_id": 31}],
            },
        },
        {"id": 31, "model_code": "gpt-4.1", "provider": "openai"},
    )

    assert "riskMode" in prompt
    assert "ai_model_config" not in prompt
    assert "prompt_bindings" not in prompt
    assert "resolved_agent_configs" not in prompt
    assert "model_code" not in prompt


def test_inline_supervisor_prompt_requires_canonical_actions_only():
    from trade_runtime.decision.nodes.supervisor_agent import _build_supervisor_prompt

    prompt = _build_supervisor_prompt(
        {
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "current_position_side": "flat",
            "event_strength": "strong",
            "market_view": {"bias": "bullish", "confidence": 70, "reason": "breakout"},
            "news_view": {"bias": "neutral", "confidence": 50, "reason": "mixed"},
            "onchain_view": {"bias": "bullish", "confidence": 72, "reason": "outflow"},
            "social_view": {"bias": "neutral", "confidence": 50, "reason": "none"},
        },
        {"model_code": "gpt-5.5", "provider": "openai"},
    )

    assert "Allowed action values only" in prompt
    assert "OPEN_LONG" in prompt
    assert "OPEN_SHORT" in prompt
    assert "ADD_LONG" in prompt
    assert "ADD_SHORT" in prompt
    assert "REDUCE" in prompt
    assert "CLOSE" in prompt
    assert "HOLD" in prompt
    assert "SKIP" in prompt
    assert "Do not return open, open_position, buy, sell, long, short, wait, none, or no_action" in prompt


def test_inline_supervisor_prompt_warns_against_frequent_post_entry_operations():
    from trade_runtime.decision.nodes.supervisor_agent import _build_supervisor_prompt

    prompt = _build_supervisor_prompt(
        {
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "current_position_side": "short",
            "current_position_quantity": 0.4,
            "current_position_opened_at": "2026-05-05T16:30:12Z",
            "current_time": "2026-05-05T17:00:12Z",
            "current_position_holding_minutes": 30,
            "event_strength": "strong",
            "market_view": {"bias": "bearish", "confidence": 78, "reason": "breakdown"},
            "news_view": {"bias": "neutral", "confidence": 50, "reason": "mixed"},
            "onchain_view": {"bias": "bearish", "confidence": 74, "reason": "exchange inflow"},
            "social_view": {"bias": "neutral", "confidence": 50, "reason": "none"},
        },
        {"model_code": "gpt-5.5", "provider": "openai"},
    )

    assert "current_position_opened_at" in prompt
    assert "current_time" in prompt
    assert "current_position_holding_minutes" in prompt
    assert "avoid frequent ADD_LONG, ADD_SHORT, REDUCE, or CLOSE" in prompt


def test_inline_supervisor_prompt_includes_previous_supervisor_decisions_duplicate_case():
    from trade_runtime.decision.nodes.supervisor_agent import _build_supervisor_prompt

    prompt = _build_supervisor_prompt(
        {
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "recent_supervisor_decisions": [
                {
                    "action": "HOLD",
                    "side": "short",
                    "confidence": 58,
                    "size_hint": 0,
                    "leverage_hint": 1,
                    "holding_window": "15m-240m",
                    "invalidation": "range_break_above_2210",
                    "summary_reason": "hold_range_short",
                },
                {
                    "action": "SKIP",
                    "side": "flat",
                    "confidence": 41,
                    "size_hint": 0,
                    "leverage_hint": 1,
                    "holding_window": "15m-240m",
                    "invalidation": "no_trade_condition",
                    "summary_reason": "wait_for_breakout",
                },
            ],
        },
        {"model_code": "gpt-5.5", "provider": "openai"},
    )

    assert "《上次决策记录》" in prompt
    assert "\"action\": \"HOLD\"" in prompt
    assert "\"summary_reason\": \"wait_for_breakout\"" in prompt


def test_inline_supervisor_prompt_includes_previous_supervisor_decisions():
    from trade_runtime.decision.nodes.supervisor_agent import _build_supervisor_prompt

    prompt = _build_supervisor_prompt(
        {
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "recent_supervisor_decisions": [
                {
                    "action": "HOLD",
                    "side": "short",
                    "confidence": 58,
                    "size_hint": 0,
                    "leverage_hint": 1,
                    "holding_window": "15m-240m",
                    "invalidation": "range_break_above_2210",
                    "summary_reason": "hold_range_short",
                },
                {
                    "action": "SKIP",
                    "side": "flat",
                    "confidence": 41,
                    "size_hint": 0,
                    "leverage_hint": 1,
                    "holding_window": "15m-240m",
                    "invalidation": "no_trade_condition",
                    "summary_reason": "wait_for_breakout",
                },
            ],
        },
        {"model_code": "gpt-5.5", "provider": "openai"},
    )

    assert "《上次决策记录》" in prompt
    assert "\"action\": \"HOLD\"" in prompt
    assert "\"summary_reason\": \"wait_for_breakout\"" in prompt


def test_inline_supervisor_prompt_includes_readable_long_term_memory():
    from trade_runtime.decision.nodes.supervisor_agent import _build_supervisor_prompt

    prompt = _build_supervisor_prompt(
        {
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "long_term_memory": {
                "status": "ready",
                "items": [
                    {
                        "id": 1,
                        "agent_code": "supervisor_agent",
                        "memory_type": "lesson",
                        "lesson_text": "Wait for price-volume confirmation before adding risk.",
                        "event_tags": ["risk_control", "breakout"],
                        "quality_score": 0.88,
                        "confidence": 0.82,
                        "evidence_json": {"text": "Breakout failed without expanding volume."},
                        "outcome_json": {"final_move_pct": -1.6, "verdict": "loss"},
                    }
                ],
                "selected_count": 1,
            },
            "memory_usage": {"used_memory_ids": [1]},
        },
        {"model_code": "gpt-5.5", "provider": "openai"},
    )

    assert "Wait for price-volume confirmation before adding risk." in prompt
    assert "risk_control" in prompt
    assert "final_move_pct=-1.6" in prompt


def test_hydrate_recent_supervisor_decisions_keeps_callback_history_even_when_older_than_short_term_ttl():
    from trade_runtime.decision.nodes.supervisor_agent import _hydrate_recent_supervisor_decisions

    class StubCallbackClient:
        def get_recent_supervisor_decisions(self, symbol, *, limit=2, exclude_trace_id="", mode=""):
            return [
                {
                    "traceId": "trace-fresh-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "createdAt": "2026-05-18T10:30:00+00:00",
                    "contentJson": (
                        "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":58,"
                        "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                        "\"invalidation\":\"range_break_above_2210\",\"summary_reason\":\"fresh_history\"}"
                    ),
                },
                {
                    "traceId": "trace-stale-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "createdAt": "2026-05-18T07:30:00+00:00",
                    "contentJson": (
                        "{\"action\":\"SKIP\",\"side\":\"flat\",\"confidence\":41,"
                        "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                        "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"stale_history\"}"
                    ),
                },
            ]

    state = {
        "symbol": "BTCUSDT",
        "mode": "paper",
        "current_time": "2026-05-18T11:00:00+00:00",
        "short_term_memory": {
            "supervisor_decision": {
                "window_seconds": 7200,
                "items": [],
            }
        },
        "callback_client": StubCallbackClient(),
    }

    _hydrate_recent_supervisor_decisions(state, limit=2)

    assert state["recent_supervisor_decisions"] == [
        {
            "action": "HOLD",
            "side": "short",
            "confidence": 58,
            "size_hint": 0,
            "leverage_hint": 1,
            "holding_window": "15m-240m",
            "invalidation": "range_break_above_2210",
            "summary_reason": "fresh_history",
        },
        {
            "action": "SKIP",
            "side": "flat",
            "confidence": 41,
            "size_hint": 0,
            "leverage_hint": 1,
            "holding_window": "15m-240m",
            "invalidation": "no_trade_condition",
            "summary_reason": "stale_history",
        },
    ]


def test_hydrate_recent_supervisor_decisions_accepts_database_local_created_at_string():
    from trade_runtime.decision.nodes.supervisor_agent import _hydrate_recent_supervisor_decisions

    class StubCallbackClient:
        def get_recent_supervisor_decisions(self, symbol, *, limit=2, exclude_trace_id="", mode=""):
            return [
                {
                    "traceId": "trace-fresh-db-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "createdAt": "2026-05-18 18:00:00",
                    "contentJson": (
                        "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":58,"
                        "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                        "\"invalidation\":\"range_break_above_2210\",\"summary_reason\":\"db_local_time_history\"}"
                    ),
                }
            ]

    state = {
        "symbol": "BTCUSDT",
        "mode": "paper",
        "current_time": "2026-05-18T10:05:00+00:00",
        "short_term_memory": {
            "supervisor_decision": {
                "window_seconds": 7200,
                "items": [],
            }
        },
        "callback_client": StubCallbackClient(),
    }

    _hydrate_recent_supervisor_decisions(state, limit=2)

    assert state["recent_supervisor_decisions"] == [
        {
            "action": "HOLD",
            "side": "short",
            "confidence": 58,
            "size_hint": 0,
            "leverage_hint": 1,
            "holding_window": "15m-240m",
            "invalidation": "range_break_above_2210",
            "summary_reason": "db_local_time_history",
        }
    ]


def test_hydrate_recent_supervisor_decisions_filters_stale_short_term_memory_fallback():
    from trade_runtime.decision.nodes.supervisor_agent import _hydrate_recent_supervisor_decisions

    state = {
        "trace_id": "trace-current",
        "symbol": "BTCUSDT",
        "mode": "paper",
        "current_time": "2026-05-18T11:00:00+00:00",
        "short_term_memory": {
            "supervisor_decision": {
                "window_seconds": 7200,
                "items": [
                    {
                        "traceId": "trace-stale-1",
                        "createdAt": "2026-05-18T07:30:00+00:00",
                        "contentJson": (
                            "{\"action\":\"SKIP\",\"side\":\"flat\",\"confidence\":41,"
                            "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                            "\"invalidation\":\"no_trade_condition\",\"summary_reason\":\"stale_memory\"}"
                        ),
                    },
                    {
                        "traceId": "trace-fresh-1",
                        "createdAt": "2026-05-18T10:30:00+00:00",
                        "contentJson": (
                            "{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":58,"
                            "\"size_hint\":0,\"leverage_hint\":1,\"holding_window\":\"15m-240m\","
                            "\"invalidation\":\"range_break_above_2210\",\"summary_reason\":\"fresh_memory\"}"
                        ),
                    },
                ],
            }
        },
    }

    _hydrate_recent_supervisor_decisions(state, limit=2)

    assert state["recent_supervisor_decisions"] == [
        {
            "action": "HOLD",
            "side": "short",
            "confidence": 58,
            "size_hint": 0,
            "leverage_hint": 1,
            "holding_window": "15m-240m",
            "invalidation": "range_break_above_2210",
            "summary_reason": "fresh_memory",
        }
    ]


def test_hydrate_recent_supervisor_decisions_oversamples_callback_history_to_skip_empty_rule_only_records():
    from trade_runtime.decision.nodes.supervisor_agent import _hydrate_recent_supervisor_decisions

    captured = {}

    class StubCallbackClient:
        def get_recent_supervisor_decisions(self, symbol, *, limit=2, exclude_trace_id="", mode=""):
            captured["limit"] = limit
            rows = [
                {
                    "traceId": "trace-empty-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": "{\"action\":\"SKIP\",\"confidence\":0,\"summary_reason\":\"\"}",
                    "createdAt": "2026-05-18 18:00:00",
                },
                {
                    "traceId": "trace-empty-2",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": "{\"action\":\"HOLD\",\"confidence\":0,\"summary_reason\":\"\"}",
                    "createdAt": "2026-05-18 17:55:00",
                },
                {
                    "traceId": "trace-valid-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"CLOSE\",\"side\":\"short\",\"confidence\":74,"
                        "\"size_hint\":1,\"summary_reason\":\"invalidated_short\"}"
                    ),
                    "createdAt": "2026-05-18 17:50:00",
                },
                {
                    "traceId": "trace-valid-2",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"HOLD\",\"side\":\"long\",\"confidence\":61,"
                        "\"size_hint\":0,\"summary_reason\":\"trend_still_valid\"}"
                    ),
                    "createdAt": "2026-05-18 17:45:00",
                },
            ]
            return rows[:limit]

    state = {
        "trace_id": "trace-current",
        "symbol": "BTCUSDT",
        "mode": "paper",
        "current_time": "2026-05-18T11:00:00+00:00",
        "short_term_memory": {"supervisor_decision": {"window_seconds": 7200, "items": []}},
        "callback_client": StubCallbackClient(),
    }

    _hydrate_recent_supervisor_decisions(state, limit=2)

    assert captured["limit"] > 2
    assert [item["summary_reason"] for item in state["recent_supervisor_decisions"]] == [
        "invalidated_short",
        "trend_still_valid",
    ]


def test_hydrate_recent_supervisor_decisions_oversamples_when_initial_batch_is_partially_filtered():
    from trade_runtime.decision.nodes.supervisor_agent import _hydrate_recent_supervisor_decisions

    call_limits: list[int] = []

    class StubCallbackClient:
        def get_recent_supervisor_decisions(self, symbol, *, limit=2, exclude_trace_id="", mode=""):
            call_limits.append(limit)
            rows = [
                {
                    "traceId": "trace-empty-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": "{\"action\":\"SKIP\",\"confidence\":0,\"summary_reason\":\"\"}",
                    "createdAt": "2026-05-18 18:00:00",
                },
                {
                    "traceId": "trace-valid-1",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"CLOSE\",\"side\":\"short\",\"confidence\":74,"
                        "\"size_hint\":1,\"summary_reason\":\"invalidated_short\"}"
                    ),
                    "createdAt": "2026-05-18 17:50:00",
                },
                {
                    "traceId": "trace-valid-2",
                    "speakerAgent": "supervisor_agent",
                    "messageType": "final_decision",
                    "contentJson": (
                        "{\"action\":\"HOLD\",\"side\":\"long\",\"confidence\":61,"
                        "\"size_hint\":0,\"summary_reason\":\"trend_still_valid\"}"
                    ),
                    "createdAt": "2026-05-18 17:45:00",
                },
            ]
            return rows[:limit]

    state = {
        "trace_id": "trace-current",
        "symbol": "BTCUSDT",
        "mode": "paper",
        "current_time": "2026-05-18T11:00:00+00:00",
        "short_term_memory": {"supervisor_decision": {"window_seconds": 7200, "items": []}},
        "callback_client": StubCallbackClient(),
    }

    _hydrate_recent_supervisor_decisions(state, limit=2)

    assert len(call_limits) == 2
    assert call_limits[0] == 2
    assert call_limits[1] > 2
    assert [item["summary_reason"] for item in state["recent_supervisor_decisions"]] == [
        "invalidated_short",
        "trend_still_valid",
    ]


def test_supervisor_fail_closed_preserves_agent_llm_errors():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            raise TimeoutError("model timeout")

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "decision_model_client": StubDecisionModelClient(),
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "runtime_config": {},
        "market_view": {"bias": "bullish", "confidence": 70, "reason": "breakout"},
        "news_view": {},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["summary_reason"] == "ai_model_call_failed_fail_closed"
    assert result["agent_llm_errors"][0]["agent_code"] == "supervisor_agent"
    assert "model timeout" in result["agent_llm_errors"][0]["error"]


def test_supervisor_fail_closed_uses_resolved_agent_model_metadata():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            raise TimeoutError("model timeout")

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "decision_model_client": StubDecisionModelClient(),
        "strategy_context": {
            "ai_model_config": {"id": 6, "model_code": "deepseek-reasoner", "provider": "deepseek"},
            "resolved_agent_configs": [
                {
                    "agent_code": "supervisor_agent",
                    "model_id": 8,
                    "model_code": "gpt-5.5",
                    "model_provider": "openai",
                    "template_code": "trade.supervisor.v1",
                }
            ],
        },
        "runtime_config": {},
        "market_view": {"bias": "bullish", "confidence": 70, "reason": "breakout"},
        "news_view": {},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["summary_reason"] == "ai_model_call_failed_fail_closed"
    assert result["supervisor_decision"]["model_code"] == "gpt-5.5"
    assert result["supervisor_decision"]["model_provider"] == "openai"


def test_supervisor_model_decision_accepts_numeric_fields_with_units():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelCode": "gpt-5.5",
                "modelProvider": "openai",
                "content": (
                    '{"action":"OPEN_LONG","side":"long","confidence":68,'
                    '"size_hint":"0.02 BTC（约1500 USDT名义）",'
                    '"leverage_hint":"2x-3x","holding_window":"15m-60m",'
                    '"invalidation":"跌破失效","summary_reason":"confirmed breakout"}'
                ),
            }

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        # 关掉 size_hint 下界，这条测的是"带单位的字符串能不能解析成数值"，
        # 不是夹持——下界另有 TestPositionRatioFloor 守着。
        "runtime_config": {"minPositionRatio": 0},
        "decision_model_client": StubDecisionModelClient(),
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "bullish", "confidence": 70, "reason": "breakout"},
        "news_view": {},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["size_hint"] == 0.02
    assert result["supervisor_decision"]["leverage_hint"] == 2
    assert result.get("ai_call_failed") is not True


def test_supervisor_model_decision_normalizes_neutral_and_placeholder_strings():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelCode": "gpt-5.5",
                "modelProvider": "openai",
                "content": (
                    '{"action":"SKIP","side":"neutral","confidence":61,'
                    '"size_hint":0,"leverage_hint":1,"holding_window":"N/A",'
                    '"invalidation":"none","summary_reason":"waiting"}'
                ),
            }

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "decision_model_client": StubDecisionModelClient(),
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "neutral", "confidence": 50, "reason": "range"},
        "news_view": {},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["side"] == "flat"
    assert result["supervisor_decision"]["holding_window"] == "15m-4h"
    assert result["supervisor_decision"]["invalidation"] == "no_trade_condition"


def test_supervisor_model_decision_normalizes_backslash_na_placeholder_strings():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelCode": "gpt-5.5",
                "modelProvider": "openai",
                "content": (
                    '{"action":"SKIP","side":"neutral","confidence":61,'
                    '"size_hint":0,"leverage_hint":1,"holding_window":"N\\\\A",'
                    '"invalidation":"N\\\\A","summary_reason":"waiting"}'
                ),
            }

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "decision_model_client": StubDecisionModelClient(),
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "neutral", "confidence": 50, "reason": "range"},
        "news_view": {},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["side"] == "flat"
    assert result["supervisor_decision"]["holding_window"] == "15m-4h"
    assert result["supervisor_decision"]["invalidation"] == "no_trade_condition"


def test_supervisor_ai_fail_open_only_when_runtime_flag_enabled():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "dispatch_mode": "LLM_ALLOWED",
        "ai_call_failed": True,
        "runtime_config": {"runtime_flags": {"supervisorAiFailOpen": True}},
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "bullish", "confidence": 75, "reason": "market confirms"},
        "news_view": {"bias": "bullish", "confidence": 75, "reason": "news supports"},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["summary_reason"] != "ai_model_call_failed_fail_closed"


def test_supervisor_ai_fail_open_ignored_in_live_mode():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "live",
        "effective_mode": "live",
        "dispatch_mode": "LLM_ALLOWED",
        "ai_call_failed": True,
        "runtime_config": {"runtime_flags": {"supervisorAiFailOpen": True}},
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "bullish", "confidence": 75, "reason": "market confirms"},
        "news_view": {"bias": "bullish", "confidence": 75, "reason": "news supports"},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["summary_reason"] == "ai_model_call_failed_fail_closed"


def test_supervisor_ai_fail_open_top_level_false_overrides_runtime_flags():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "ai_call_failed": True,
        "runtime_config": {"supervisorAiFailOpen": False, "runtime_flags": {"supervisorAiFailOpen": True}},
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "bullish", "confidence": 75, "reason": "market confirms"},
        "news_view": {"bias": "bullish", "confidence": 75, "reason": "news supports"},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["summary_reason"] == "ai_model_call_failed_fail_closed"


def test_supervisor_ai_fail_open_reads_runtime_flags_json_string():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "ai_call_failed": True,
        "runtime_config": {"runtimeFlagsJson": '{"supervisorAiFailOpen":true}'},
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "bullish", "confidence": 75, "reason": "market confirms"},
        "news_view": {"bias": "bullish", "confidence": 75, "reason": "news supports"},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "OPEN_LONG"
    assert result["supervisor_decision"]["summary_reason"] != "ai_model_call_failed_fail_closed"


def test_supervisor_ai_fail_open_top_level_false_overrides_runtime_flags_json_string():
    from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent

    state = {
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "effective_mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "ai_call_failed": True,
        "runtime_config": {"supervisorAiFailOpen": False, "runtimeFlagsJson": '{"supervisorAiFailOpen":true}'},
        "strategy_context": {"ai_model_config": {"id": 8, "model_code": "gpt-5.5", "provider": "openai"}},
        "market_view": {"bias": "bullish", "confidence": 75, "reason": "market confirms"},
        "news_view": {"bias": "bullish", "confidence": 75, "reason": "news supports"},
        "onchain_view": {},
        "social_view": {},
    }

    result = supervisor_agent(state)

    assert result["supervisor_decision"]["action"] == "SKIP"
    assert result["supervisor_decision"]["summary_reason"] == "ai_model_call_failed_fail_closed"


def test_normalize_recent_supervisor_decisions_filters_empty_rule_only_records():
    """Test that RULE_ONLY decisions with empty summary_reason and confidence=0 are filtered out."""
    from trade_runtime.decision.nodes.supervisor_agent import _normalize_recent_supervisor_decisions

    items = [
        # Valid decision with summary_reason
        {
            "traceId": "trace-valid-1",
            "speakerAgent": "supervisor_agent",
            "messageType": "final_decision",
            "contentJson": '{"action":"SKIP","confidence":63,"summary_reason":"valid_reason"}',
            "createdAt": "2026-05-18 18:00:00",
        },
        # RULE_ONLY decision with empty summary_reason and confidence=0 (should be filtered)
        {
            "traceId": "trace-empty-1",
            "speakerAgent": "supervisor_agent",
            "messageType": "final_decision",
            "contentJson": '{"action":"SKIP","confidence":0,"summary_reason":""}',
            "createdAt": "2026-05-18 17:00:00",
        },
        # Another valid decision
        {
            "traceId": "trace-valid-2",
            "speakerAgent": "supervisor_agent",
            "messageType": "final_decision",
            "contentJson": '{"action":"HOLD","confidence":55,"summary_reason":"hold_reason"}',
            "createdAt": "2026-05-18 16:00:00",
        },
        # RULE_ONLY with confidence=0 but has summary_reason (should be kept)
        {
            "traceId": "trace-valid-3",
            "speakerAgent": "supervisor_agent",
            "messageType": "final_decision",
            "contentJson": '{"action":"SKIP","confidence":0,"summary_reason":"zero_confidence_but_has_reason"}',
            "createdAt": "2026-05-18 15:00:00",
        },
    ]

    result = _normalize_recent_supervisor_decisions(
        items,
        limit=5,
        enforce_freshness=False,
    )

    # Should have 3 records (empty one filtered out)
    assert len(result) == 3
    assert result[0]["summary_reason"] == "valid_reason"
    assert result[1]["summary_reason"] == "hold_reason"
    assert result[2]["summary_reason"] == "zero_confidence_but_has_reason"
