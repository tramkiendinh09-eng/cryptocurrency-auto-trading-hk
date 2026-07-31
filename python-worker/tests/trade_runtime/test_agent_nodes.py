from trade_runtime.decision.nodes.market_agent import market_agent
from trade_runtime.decision.nodes.news_agent import news_agent
from trade_runtime.decision.nodes.onchain_agent import onchain_agent
from trade_runtime.decision.nodes.social_agent import social_agent


def test_news_agent_marks_bullish_for_positive_news_score():
    state = {
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.9}
        ]
    }

    result = news_agent(state)

    assert result["news_view"]["bias"] == "bullish"
    assert result["news_view"]["confidence"] == 90
    assert "ETF inflow" in result["news_view"]["reason"]


def test_onchain_agent_marks_bearish_for_exchange_inflow():
    state = {
        "event_bundle": [
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_inflow", "amountUsd": 2500000}
        ]
    }

    result = onchain_agent(state)

    assert result["onchain_view"]["bias"] == "bearish"
    assert result["onchain_view"]["confidence"] == 75
    assert "exchange_inflow" in result["onchain_view"]["reason"]



def test_news_agent_rule_view_aggregates_recent_news_events():
    state = {
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.7},
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "Whales add longs", "score": 0.8},
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "Dormant BTC repricing", "score": 0.65},
        ]
    }

    result = news_agent(state)

    assert result["news_view"]["bias"] == "bullish"
    assert result["news_view"]["confidence"] == 80
    assert "3 news events" in result["news_view"]["reason"]
    assert "Whales add longs" in result["news_view"]["reason"]


def test_onchain_agent_rule_view_aggregates_recent_onchain_events():
    state = {
        "event_bundle": [
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_outflow", "amountUsd": 900000},
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_outflow", "amountUsd": 2500000},
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_inflow", "amountUsd": 300000},
        ]
    }

    result = onchain_agent(state)

    assert result["onchain_view"]["bias"] == "bullish"
    assert result["onchain_view"]["confidence"] == 75
    assert "net_outflow" in result["onchain_view"]["reason"]
    assert "3100000" in result["onchain_view"]["reason"]

def test_social_agent_marks_bullish_for_high_social_score():
    state = {
        "event_bundle": [
            {"event_type": "social", "symbol": "BTCUSDT", "score": 0.8}
        ]
    }

    result = social_agent(state)

    assert result["social_view"]["bias"] == "bullish"
    assert result["social_view"]["confidence"] == 80
    assert "0.8" in result["social_view"]["reason"]


def test_social_agent_does_not_call_llm_when_social_api_is_disabled(monkeypatch):
    def _unexpected_llm_call(*args, **kwargs):
        raise AssertionError("disabled social source must not call LLM")

    monkeypatch.setattr("trade_runtime.decision.nodes.social_agent.run_llm_agent", _unexpected_llm_call)
    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "event_bundle": [{"event_type": "social", "symbol": "BTCUSDT", "score": 0.91}],
        "strategy_context": {"social_api_config": {"enabled": "0"}},
        "agent_profiles": [
            {"agent_code": "social_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True}
        ],
    }

    result = social_agent(state)

    assert result["social_view"]["bias"] == "neutral"
    assert result["social_view"]["reason"] == "social_api_disabled"


def test_news_agent_returns_neutral_when_news_api_is_disabled():
    state = {
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.9}
        ],
        "strategy_context": {
            "news_api_config": {
                "enabled": "0",
            }
        },
    }

    result = news_agent(state)

    assert result["news_view"]["bias"] == "neutral"
    assert result["news_view"]["reason"] == "news_api_disabled"


def test_onchain_agent_returns_neutral_when_onchain_collection_is_disabled():
    state = {
        "event_bundle": [
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_outflow", "amountUsd": 2500000}
        ],
        "strategy_context": {
            "market_data_config": {
                "collect_onchain": "0",
            }
        },
    }

    result = onchain_agent(state)

    assert result["onchain_view"]["bias"] == "neutral"
    assert result["onchain_view"]["reason"] == "onchain_collection_disabled"


def test_market_agent_uses_llm_profile_and_prompt_binding_when_configured():
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
                    "{\"bias\":\"bearish\",\"confidence\":87,"
                    "\"reason\":\"llm_market_reversal\",\"ttl\":600,\"risk_note\":\"macro_divergence\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.market.v1":
                return {
                    "code": template_code,
                    "content": "Market template {symbol} {feature_snapshot_json}",
                }
            return None

    state = {
        "trace_id": "trace-market-llm",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "strong",
        "feature_snapshot": {"price_change_pct": 6.2},
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "structured_schema_code": "agent_view_v1",
            }
        ],
        "prompt_bindings": [
            {
                "binding_scope": "MARKET_AGENT",
                "template_code": "trade.market.v1",
                "model_id": 88,
                "enabled": True,
                "priority": 10,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = market_agent(state)

    assert captured["model_id"] == 88
    assert "Market template BTCUSDT" in captured["prompt"]
    assert "\"price_change_pct\": 6.2" in captured["prompt"]
    assert result["market_view"]["bias"] == "bearish"
    assert result["market_view"]["confidence"] == 87
    assert result["market_view"]["reason"] == "llm_market_reversal"
    assert result["market_view"]["template_code"] == "trade.market.v1"
    assert result["market_view"]["model_code"] == "gpt-4.1-mini"


def test_market_agent_prefers_resolved_agent_config_over_legacy_binding():
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
                    "{\"bias\":\"bullish\",\"confidence\":82,"
                    "\"reason\":\"resolved_market_prompt\",\"ttl\":600,\"risk_note\":\"ok\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.market.resolved":
                return {"code": template_code, "content": "Resolved market template {symbol}"}
            if template_code == "trade.market.legacy":
                return {"code": template_code, "content": "Legacy market template {symbol}"}
            return None

    state = {
        "trace_id": "trace-market-resolved",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "strong",
        "feature_snapshot": {"price_change_pct": 6.2},
        "selected_agents": ["market_agent"],
        "dispatch_mode": "LLM_ALLOWED",
        "strategy_context": {"ai_model_config": {"id": 31, "model_code": "gpt-4.1", "provider": "openai"}},
        "agent_profiles": [{"agent_code": "market_agent", "agent_type": "LLM", "llm_enabled": True}],
        "resolved_agent_configs": [
            {
                "agent_code": "market_agent",
                "model_id": 88,
                "model_code": "deepseek-reasoner",
                "model_provider": "deepseek",
                "template_code": "trade.market.resolved",
                "output_schema_code": "agent_view_v1",
                "enabled": True,
                "llm_enabled": True,
            }
        ],
        "prompt_bindings": [
            {"binding_scope": "MARKET_AGENT", "template_code": "trade.market.legacy", "model_id": 77, "enabled": True}
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = market_agent(state)

    assert captured["model_id"] == 88
    assert "Resolved market template BTCUSDT" in captured["prompt"]
    assert "Legacy market template" not in captured["prompt"]
    assert result["market_view"]["template_code"] == "trade.market.resolved"
    assert result["market_view"]["model_code"] == "deepseek-reasoner"


def test_market_agent_prompt_includes_rich_market_context_for_price_volume_events():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": (
                    "{\"bias\":\"bullish\",\"confidence\":84,"
                    "\"reason\":\"market_context_complete\",\"ttl\":600,\"risk_note\":\"watch_liquidation\"}"
                ),
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.market.v2":
                return {
                    "code": template_code,
                    "content": "Market context {market_context_json}",
                }
            return None

    state = {
        "trace_id": "trace-market-rich-context",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "dispatch_mode": "LLM_ALLOWED",
        "event_strength": "strong",
        "feature_snapshot": {"price_change_pct": 6.2},
        "event_bundle": [
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0, "volume": 123.4},
            {"event_type": "mark_price", "symbol": "BTCUSDT", "price": 64910.0},
            {"event_type": "funding_rate", "symbol": "BTCUSDT", "funding_rate": 0.0008},
            {"event_type": "liquidation", "symbol": "BTCUSDT", "notionalUsd": 500000.0, "side": "SELL", "price": 64880.0},
        ],
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
        "prompt_bindings": [
            {
                "binding_scope": "MARKET_AGENT",
                "template_code": "trade.market.v2",
                "model_id": 31,
                "enabled": True,
                "priority": 10,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = market_agent(state)

    assert "\"latest_price\": 65000.0" in captured["prompt"]
    assert "\"latest_volume\": 123.4" in captured["prompt"]
    assert "\"mark_price\": 64910.0" in captured["prompt"]
    assert "\"funding_rate\": 0.0008" in captured["prompt"]
    assert "\"largest_liquidation_notional_usd\": 500000.0" in captured["prompt"]
    assert result["market_view"]["reason"] == "market_context_complete"


def test_market_agent_prompt_includes_multi_period_volume_price_and_wyckoff_context():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": "{\"bias\":\"bullish\",\"confidence\":82,\"reason\":\"wyckoff_markup\"}",
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            return {"code": template_code, "content": "Market context {market_context_json}"}

    state = {
        "trace_id": "trace-market-wyckoff-context",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "dispatch_mode": "LLM_ALLOWED",
        "event_strength": "strong",
        "feature_snapshot": {"price_change_pct": 4.2},
        "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 104.0, "quoteVolume": 4200.0}],
        "market_context_history": [
            {"observed_at": "2026-04-24T07:00:00+00:00", "price": 100.0, "quote_volume": 1000.0},
            {"observed_at": "2026-04-24T07:05:00+00:00", "price": 101.0, "quote_volume": 1300.0},
            {"observed_at": "2026-04-24T07:10:00+00:00", "price": 102.0, "quote_volume": 1800.0},
            {"observed_at": "2026-04-24T07:15:00+00:00", "price": 104.0, "quote_volume": 4200.0},
        ],
        "strategy_context": {"ai_model_config": {"id": 31, "model_code": "gpt-4.1", "provider": "openai"}},
        "agent_profiles": [{"agent_code": "market_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True}],
        "prompt_bindings": [
            {"binding_scope": "MARKET_AGENT", "template_code": "trade.market.v2", "model_id": 31, "enabled": True}
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    market_agent(state)

    assert "\"period_summaries\"" in captured["prompt"]
    assert "\"window\": \"15m\"" in captured["prompt"]
    assert "\"volume_price_signals\"" in captured["prompt"]
    assert "\"wyckoff_context\"" in captured["prompt"]
    assert "\"phase\": \"markup\"" in captured["prompt"]




def test_news_agent_render_context_excludes_onchain_events():
    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "trace_id": "trace-news-domain-only",
        "symbol": "BTCUSDT",
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.7},
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_outflow", "amountUsd": 42300000},
            {"event_type": "social", "symbol": "BTCUSDT", "score": 0.9},
        ],
        "short_term_memory": {
            "news": {"sample_count": 1, "items": [{"headline": "ETF inflow"}]},
            "onchain": {"sample_count": 1, "items": [{"flow": "exchange_outflow"}]},
        },
    }

    context = build_agent_render_context(state, agent_code="news_agent", rule_view={})

    assert "ETF inflow" in context["event_bundle_json"]
    assert "exchange_outflow" not in context["event_bundle_json"]
    assert "exchange_outflow" not in context["recent_onchain_context_json"]
    assert "exchange_outflow" not in context["short_term_memory_json"]


def test_news_render_context_filters_stale_news_by_prompt_quality_ttl():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "trace_id": "trace-news-ttl",
        "symbol": "BTCUSDT",
        "current_time": "2026-05-08T08:00:00+00:00",
        "runtime_config": {"runtime_flags_json": "{\"promptQuality\":{\"recentNewsTtlSeconds\":3600}}"},
        "event_bundle": [
            {
                "event_type": "news",
                "symbol": "BTCUSDT",
                "headline": "old headline",
                "score": 0.92,
                "event_time": "2026-05-08T06:30:00+00:00",
            },
            {
                "event_type": "news",
                "symbol": "BTCUSDT",
                "headline": "fresh headline",
                "score": 0.7,
                "event_time": "2026-05-08T07:45:00+00:00",
            },
        ],
    }

    context = build_agent_render_context(state, agent_code="news_agent", rule_view={})
    recent_news = json.loads(context["recent_news_context_json"])

    assert recent_news["event_count"] == 1
    assert recent_news["stale_items_filtered"] == 1
    assert recent_news["latest_headline"] == "fresh headline"
    assert all(item["headline"] != "old headline" for item in recent_news["events"])
    event_bundle = json.loads(context["event_bundle_json"])
    assert [item["headline"] for item in event_bundle] == ["fresh headline"]


def test_onchain_render_context_filters_stale_and_duplicate_events():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "trace_id": "trace-onchain-ttl",
        "symbol": "BTCUSDT",
        "current_time": "2026-05-08T08:00:00+00:00",
        "runtime_config": {"runtime_flags_json": "{\"promptQuality\":{\"recentOnchainTtlSeconds\":7200}}"},
        "event_bundle": [
            {
                "event_type": "onchain",
                "symbol": "BTCUSDT",
                "flow": "exchange_outflow",
                "amountUsd": 5000000,
                "txHash": "old-tx",
                "event_time": "2026-05-08T05:00:00+00:00",
            },
            {
                "event_type": "onchain",
                "symbol": "BTCUSDT",
                "flow": "exchange_outflow",
                "amountUsd": 3000000,
                "txHash": "fresh-tx",
                "event_time": "2026-05-08T07:30:00+00:00",
            },
            {
                "event_type": "onchain",
                "symbol": "BTCUSDT",
                "flow": "exchange_outflow",
                "amountUsd": 3000000,
                "txHash": "fresh-tx",
                "event_time": "2026-05-08T07:31:00+00:00",
            },
        ],
    }

    context = build_agent_render_context(state, agent_code="onchain_agent", rule_view={})
    recent_onchain = json.loads(context["recent_onchain_context_json"])
    event_bundle = json.loads(context["event_bundle_json"])

    assert recent_onchain["event_count"] == 1
    assert recent_onchain["stale_items_filtered"] == 1
    assert recent_onchain["duplicate_items_filtered"] == 1
    assert recent_onchain["total_outflow_usd"] == 3000000
    assert [item["txHash"] for item in event_bundle] == ["fresh-tx"]


def test_agent_prompt_includes_specialist_recent_context_json():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": "{\"bias\":\"bullish\",\"confidence\":70,\"reason\":\"recent context\"}",
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            return {"code": template_code, "content": "Recent {recent_news_context_json} {recent_onchain_context_json}"}

    state = {
        "trace_id": "trace-specialist-context",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "event_strength": "strong",
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.7},
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "Whales add longs", "score": 0.8},
            {"event_type": "onchain", "symbol": "BTCUSDT", "flow": "exchange_outflow", "amountUsd": 2500000},
        ],
        "strategy_context": {"ai_model_config": {"id": 31, "model_code": "gpt-4.1", "provider": "openai"}},
        "agent_profiles": [{"agent_code": "news_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True}],
        "prompt_bindings": [{"binding_scope": "NEWS_AGENT", "template_code": "trade.news.v2", "model_id": 31, "enabled": True}],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    news_agent(state)

    assert "\"event_count\": 2" in captured["prompt"]
    assert "Whales add longs" in captured["prompt"]
    assert "exchange_outflow" not in captured["prompt"]


def test_market_agent_builds_history_from_event_bundle_when_runtime_history_missing():
    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["prompt"] = prompt
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": "{\"bias\":\"bullish\",\"confidence\":80,\"reason\":\"event bundle history\"}",
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            return {"code": template_code, "content": "Market context {market_context_json}"}

    state = {
        "trace_id": "trace-market-history-fallback",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "dispatch_mode": "LLM_ALLOWED",
        "event_strength": "strong",
        "feature_snapshot": {"price_change_pct": 3.2},
        "event_bundle": [
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 100.0, "quote_volume": 1000.0, "event_time": "2026-04-24T07:00:00Z"},
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 102.0, "quote_volume": 1600.0, "event_time": "2026-04-24T07:05:00Z"},
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 104.0, "quote_volume": 2400.0, "event_time": "2026-04-24T07:10:00Z"},
        ],
        "strategy_context": {"ai_model_config": {"id": 31, "model_code": "gpt-4.1", "provider": "openai"}},
        "agent_profiles": [{"agent_code": "market_agent", "agent_type": "LLM", "llm_enabled": True, "enabled": True}],
        "prompt_bindings": [{"binding_scope": "MARKET_AGENT", "template_code": "trade.market.v2", "model_id": 31, "enabled": True}],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    market_agent(state)

    assert "\"history_sample_count\": 3" in captured["prompt"]
    assert "not_enough_market_history" not in captured["prompt"]

def test_market_agent_skips_llm_below_rule_only_market_threshold_from_runtime_config(monkeypatch):
    def _unexpected_llm_call(*args, **kwargs):
        raise AssertionError("weak market move should not call LLM")

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _unexpected_llm_call)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 0.8},
        "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert result["market_view"]["reason"] == "price_change_pct=0.8"
    assert result["market_view"]["confidence"] == 60


def test_market_agent_rule_view_reflects_ready_wyckoff_shortterm_signal():
    state = {
        "dispatch_mode": "RULE_ONLY",
        "symbol": "ETHUSDT",
        "feature_snapshot": {
            "price_change_pct": 0.05,
            "wyckoff_shortterm": {
                "status": "ready",
                "phase": "markup",
                "entry_bias": "bullish",
                "trigger": "breakout_long",
                "trade_readiness": "ready",
                "confidence": 0.78,
            },
        },
        "event_bundle": [{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2250.0}],
    }

    result = market_agent(state)

    assert result["market_view"]["bias"] == "bullish"
    assert result["market_view"]["confidence"] == 78
    assert result["market_view"]["reason"] == "wyckoff:breakout_long"


def test_market_agent_rule_view_keeps_wyckoff_watch_neutral():
    from trade_runtime.decision.nodes.market_agent import market_agent

    state = {
        "dispatch_mode": "RULE_ONLY",
        "symbol": "ETHUSDT",
        "feature_snapshot": {
            "price_change_pct": 0.05,
            "market_window_price_change_pct": 0.05,
            "wyckoff_shortterm": {
                "status": "watch",
                "phase": "markup",
                "entry_bias": "bullish",
                "trigger": "breakout_long",
                "trade_readiness": "watch",
                "confidence": 0.72,
                "trap_risk": "medium",
                "no_trade_reason": "breakout_retest_required",
            },
        },
        "event_bundle": [{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2250.0}],
    }

    result = market_agent(state)

    assert result["market_view"]["bias"] == "neutral"
    assert result["market_view"]["reason"] == "wyckoff_watch:breakout_long:breakout_retest_required"
    assert result["market_view"]["risk_note"] == "medium"


def test_market_agent_treats_tiny_price_change_as_neutral_rule_view():
    from trade_runtime.decision.nodes.market_agent import market_agent

    state = {
        "dispatch_mode": "RULE_ONLY",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": -0.0041},
        "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
    }

    result = market_agent(state)

    assert result["market_view"]["bias"] == "neutral"
    assert result["market_view"]["confidence"] == 50
    assert result["market_view"]["reason"] == "price_change_pct=-0.0041"


def test_market_agent_uses_llm_when_market_move_reaches_rule_only_threshold(monkeypatch):
    captured = {"called": False}

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        captured["called"] = True
        return {
            "bias": "bullish",
            "confidence": 86,
            "reason": "threshold_reached_market_llm",
            "ttl": 900,
            "risk_note": "normal",
        }

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 1.2},
        "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert captured["called"] is True
    assert result["market_view"]["reason"] == "threshold_reached_market_llm"


def test_market_agent_uses_llm_when_ready_wyckoff_shortterm_setup_exists(monkeypatch):
    captured = {"called": False}

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        captured["called"] = True
        return {
            "bias": "bullish",
            "confidence": 89,
            "reason": "wyckoff_market_llm",
            "ttl": 900,
            "risk_note": "normal",
        }

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "ETHUSDT",
        "feature_snapshot": {
            "price_change_pct": 0.2,
            "market_window_price_change_pct": 0.2,
            "wyckoff_shortterm": {
                "status": "ready",
                "phase": "markup",
                "entry_bias": "bullish",
                "trigger": "breakout_long",
                "trade_readiness": "ready",
                "confidence": 0.78,
            },
        },
        "event_bundle": [{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2250.0}],
        "runtime_config": {"marketTrigger": {"ruleOnlyPriceChangePct": 1.0}},
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert captured["called"] is True
    assert result["market_view"]["reason"] == "wyckoff_market_llm"


def test_market_agent_uses_llm_when_window_move_reaches_rule_only_threshold(monkeypatch):
    captured = {"called": False}

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        captured["called"] = True
        return {
            "bias": "bearish",
            "confidence": 86,
            "reason": "window_threshold_reached_market_llm",
            "ttl": 900,
            "risk_note": "normal",
        }

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 0.0, "market_window_price_change_pct": -1.2},
        "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert captured["called"] is True
    assert result["market_view"]["reason"] == "window_threshold_reached_market_llm"


def test_market_agent_uses_llm_for_price_acceleration_above_configured_threshold(monkeypatch):
    captured = {"called": False}

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        captured["called"] = True
        return {
            "bias": "bullish",
            "confidence": 84,
            "reason": "acceleration_market_llm",
            "ttl": 900,
            "risk_note": "normal",
        }

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 0.2, "market_price_acceleration_pct": 1.3},
        "event_bundle": [{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
                "priceAccelerationPct": 1.2,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert captured["called"] is True
    assert result["market_view"]["reason"] == "acceleration_market_llm"


def test_market_agent_uses_llm_for_significant_market_event_even_below_threshold(monkeypatch):
    captured = {"called": False}

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        captured["called"] = True
        return {
            "bias": "bearish",
            "confidence": 88,
            "reason": "liquidation_market_llm",
            "ttl": 900,
            "risk_note": "normal",
        }

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 0.2},
        "event_bundle": [
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0},
            {"event_type": "liquidation", "symbol": "BTCUSDT", "notionalUsd": 500000.0},
        ],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
                "liquidationNotionalUsd": 250000,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert captured["called"] is True
    assert result["market_view"]["reason"] == "liquidation_market_llm"


def test_market_agent_skips_llm_for_small_liquidation_below_configured_threshold(monkeypatch):
    def _unexpected_llm_call(*args, **kwargs):
        raise AssertionError("small liquidation should not call LLM")

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _unexpected_llm_call)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 0.2},
        "event_bundle": [
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0},
            {"event_type": "liquidation", "symbol": "BTCUSDT", "notionalUsd": 100000.0},
        ],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
                "liquidationNotionalUsd": 250000,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert result["market_view"]["reason"] == "price_change_pct=0.2"


def test_market_agent_skips_llm_for_small_funding_rate_below_configured_threshold(monkeypatch):
    def _unexpected_llm_call(*args, **kwargs):
        raise AssertionError("small funding rate should not call LLM")

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _unexpected_llm_call)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 0.2},
        "event_bundle": [
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0},
            {"event_type": "funding_rate", "symbol": "BTCUSDT", "funding_rate": 0.0004},
        ],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
                "fundingRateAbs": 0.001,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert result["market_view"]["reason"] == "price_change_pct=0.2"


def test_market_agent_uses_llm_for_mark_price_deviation_above_configured_threshold(monkeypatch):
    captured = {"called": False}

    def _selected_market_llm(state, *, agent_code, binding_scope, rule_view=None):
        captured["called"] = True
        return {
            "bias": "bearish",
            "confidence": 84,
            "reason": "mark_price_gap_market_llm",
            "ttl": 900,
            "risk_note": "normal",
        }

    monkeypatch.setattr("trade_runtime.decision.nodes.market_agent.run_llm_agent", _selected_market_llm)

    state = {
        "dispatch_mode": "LLM_ALLOWED",
        "symbol": "BTCUSDT",
        "feature_snapshot": {"price_change_pct": 0.2},
        "event_bundle": [
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0},
            {"event_type": "mark_price", "symbol": "BTCUSDT", "price": 64220.0},
        ],
        "runtime_config": {
            "marketTrigger": {
                "ruleOnlyPriceChangePct": 1.0,
                "priceChangePct": 2.5,
                "markPriceDeviationPct": 1.0,
            }
        },
        "agent_profiles": [
            {
                "agent_code": "market_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
            }
        ],
    }

    result = market_agent(state)

    assert captured["called"] is True
    assert result["market_view"]["reason"] == "mark_price_gap_market_llm"


def test_news_agent_hybrid_falls_back_to_rule_view_when_llm_output_is_invalid():
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {
                "modelId": model_id,
                "modelCode": "gpt-4.1-mini",
                "modelProvider": "openai",
                "content": "not-json",
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.news.v1":
                return {
                    "code": template_code,
                    "content": "News template {symbol} {rule_view_json}",
                }
            return None

    state = {
        "trace_id": "trace-news-hybrid",
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "mode": "shadow",
        "event_strength": "strong",
        "dispatch_mode": "LLM_ALLOWED",
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.9}
        ],
        "strategy_context": {
            "ai_model_config": {
                "id": 31,
                "model_code": "gpt-4.1",
                "provider": "openai",
            }
        },
        "agent_profiles": [
            {
                "agent_code": "news_agent",
                "agent_type": "HYBRID",
                "llm_enabled": True,
                "structured_schema_code": "agent_view_v1",
            }
        ],
        "prompt_bindings": [
            {
                "binding_scope": "NEWS_AGENT",
                "template_code": "trade.news.v1",
                "model_id": 91,
                "enabled": True,
                "priority": 10,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = news_agent(state)

    assert result["news_view"]["bias"] == "bullish"
    assert result["news_view"]["confidence"] == 90
    assert "ETF inflow" in result["news_view"]["reason"]
    assert result["ai_call_failed"] is True
    assert result["news_view"]["llm_status"] == "failed_fallback_rule"
    assert result["agent_llm_errors"][0]["agent_code"] == "news_agent"
    assert result["agent_llm_errors"][0]["error"] == "invalid_agent_view_content"
    assert result["agent_llm_errors"][0]["raw_response_snippet"] == "not-json"


def test_llm_agent_records_raw_response_snippet_on_parse_failure():
    from trade_runtime.decision.llm_agent_runner import run_llm_agent

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            return {"content": "I think we should open_position long aggressively"}

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.news.v1":
                return {"content": "Return JSON only for {symbol}"}
            return None

    state = {
        "symbol": "BTCUSDT",
        "dispatch_mode": "LLM_ALLOWED",
        "selected_agents": ["news_agent"],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
        "resolved_agent_configs": [
            {
                "agent_code": "news_agent",
                "template_code": "trade.news.v1",
                "model_id": 31,
                "enabled": True,
                "llm_enabled": True,
            }
        ],
    }

    result = run_llm_agent(state, agent_code="news_agent", binding_scope="NEWS_AGENT")

    assert result is None
    assert state["ai_call_failed"] is True
    assert state["agent_llm_errors"][0]["error"] == "invalid_agent_view_content"
    assert "open_position long" in state["agent_llm_errors"][0]["raw_response_snippet"]


def test_news_agent_marks_llm_exception_and_falls_back_to_rule_view():
    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            raise RuntimeError("401 Unauthorized")

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            if template_code == "trade.news.v1":
                return {
                    "code": template_code,
                    "content": "News template {symbol} {rule_view_json}",
                }
            return None

    state = {
        "trace_id": "trace-news-llm-fail",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "event_strength": "strong",
        "event_bundle": [
            {"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF inflow", "score": 0.9}
        ],
        "agent_profiles": [
            {
                "agent_code": "news_agent",
                "agent_type": "LLM",
                "llm_enabled": True,
                "enabled": True,
                "structured_schema_code": "agent_view_v1",
            }
        ],
        "prompt_bindings": [
            {
                "binding_scope": "NEWS_AGENT",
                "template_code": "trade.news.v1",
                "model_id": 91,
                "enabled": True,
                "priority": 10,
            }
        ],
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
    }

    result = news_agent(state)

    assert result["news_view"]["bias"] == "bullish"
    assert result["news_view"]["llm_status"] == "failed_fallback_rule"
    assert result["ai_call_failed"] is True
    assert result["agent_llm_errors"] == [
        {
            "agent_code": "news_agent",
            "model_id": 91,
            "template_code": "trade.news.v1",
            "error": "401 Unauthorized",
        }
    ]

def test_run_llm_agent_uses_unified_agent_execution_config_without_legacy_model_fallback():
    from trade_runtime.decision.llm_agent_runner import run_llm_agent

    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "modelCode": "deepseek-reasoner",
                "modelProvider": "deepseek",
                "content": "{\"bias\":\"bullish\",\"confidence\":82,\"reason\":\"resolved config\",\"ttl\":900,\"risk_note\":\"normal\"}",
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            return {"code": template_code, "content": "Resolved template {symbol}"}

    state = {
        "symbol": "BTCUSDT",
        "mode": "paper",
        "event_strength": "strong",
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
        "strategy_context": {"ai_model_config": {"id": 6, "model_code": "legacy-model", "provider": "legacy"}},
        "resolved_agent_configs": [
            {
                "agent_code": "market_agent",
                "model_id": 88,
                "model_code": "deepseek-reasoner",
                "model_provider": "deepseek",
                "template_code": "trade.market.resolved",
                "output_schema_code": "agent_view_v1",
                "enabled": True,
            }
        ],
        "prompt_bindings": [
            {
                "binding_scope": "MARKET_AGENT",
                "model_id": 77,
                "template_code": "trade.market.legacy",
                "enabled": True,
            }
        ],
    }

    view = run_llm_agent(state, agent_code="market_agent", binding_scope="MARKET_AGENT")

    assert captured["model_id"] == 88
    assert "Resolved template BTCUSDT" in captured["prompt"]
    assert view["model_code"] == "deepseek-reasoner"


def test_run_llm_agent_uses_legacy_binding_only_through_unified_compat_config():
    from trade_runtime.decision.llm_agent_runner import run_llm_agent

    captured = {}

    class StubDecisionModelClient:
        def call_model(self, *, model_id, prompt):
            captured["model_id"] = model_id
            captured["prompt"] = prompt
            return {
                "content": "{\"bias\":\"neutral\",\"confidence\":61,\"reason\":\"compat config\",\"ttl\":900,\"risk_note\":\"normal\"}",
            }

    class StubPromptTemplateRegistry:
        def get_template(self, template_code):
            return {"code": template_code, "content": "Compat template {symbol}"}

    state = {
        "symbol": "ETHUSDT",
        "mode": "paper",
        "event_strength": "strong",
        "decision_model_client": StubDecisionModelClient(),
        "prompt_template_registry": StubPromptTemplateRegistry(),
        "strategy_context": {"ai_model_config": {"id": 6, "model_code": "deepseek-reasoner", "provider": "deepseek"}},
        "prompt_bindings": [
            {
                "binding_scope": "MARKET_AGENT",
                "template_code": "trade.market.legacy",
                "enabled": True,
            }
        ],
    }

    view = run_llm_agent(state, agent_code="market_agent", binding_scope="MARKET_AGENT")

    assert captured["model_id"] == 6
    assert "Compat template ETHUSDT" in captured["prompt"]
    assert view["model_code"] == "deepseek-reasoner"
    assert view["model_provider"] == "deepseek"



def test_agent_render_context_includes_memory_json():
    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "trace_id": "trace-1",
        "symbol": "BTCUSDT",
        "short_term_memory": {"news": {"sample_count": 2, "items": []}},
        "long_term_memory": {"status": "ready", "items": [{"id": 1, "lesson_text": "lesson"}]},
        "memory_usage": {"used_memory_ids": [1]},
    }

    context = build_agent_render_context(state, agent_code="news_agent", rule_view={})

    assert "short_term_memory_json" in context
    assert "long_term_memory_json" in context
    assert "memory_usage_json" in context
    assert "lesson" in context["long_term_memory_json"]


def test_market_render_context_includes_enhanced_market_sections():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "symbol": "BTCUSDT",
        "event_bundle": [
            {"event_type": "market_tick", "price": 77000, "quote_volume": 1000000},
            {
                "event_type": "market_metric",
                "latest_price": 77000,
                "mark_price": 77010,
                "funding_rate": 0.0001,
                "open_interest": 123456,
                "liquidation_notional_15m": 250000,
                "liquidation_notional_60m": 500000,
                "liquidation_notional_240m": 800000,
            },
        ],
        "feature_snapshot": {
            "kline_price_change_pct": {"15m": 1.2, "60m": 2.4},
            "kline_quote_volume_ratio": {"15m": 1.5},
            "atr_pct": {"15m": 0.8},
            "rsi_14": {"15m": 62.5},
            "ema_trend": {"15m": "up"},
            "wyckoff_15m_bars": {
                "required_15m_bars": 8,
                "provided_15m_bars": 8,
                "bars": [
                    {"open_time": index, "open": 100 + index, "high": 101 + index, "low": 99 + index, "close": 100.5 + index, "quote_volume": 1000 + index}
                    for index in range(8)
                ],
            },
        },
    }

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["kline_context"]["price_change_pct"]["15m"] == 1.2
    assert market_context["derivatives_context"]["open_interest"] == 123456
    assert market_context["liquidation_context"]["notional_60m"] == 500000
    assert market_context["wyckoff_15m_bars"]["provided_15m_bars"] == 8
    assert len(market_context["kline_series"]["15m"]) == 8


def test_market_render_context_prefers_kline_ohlcv_volume_price_summaries():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    kline_periods = [
        {
            "window": "15m",
            "source": "kline_ohlcv",
            "sample_count": 15,
            "start_price": 100.0,
            "end_price": 104.0,
            "price_change_pct": 4.0,
            "range_pct": 5.0,
            "quote_volume_sum": 45000.0,
            "previous_quote_volume_sum": 20000.0,
            "quote_volume_ratio": 2.25,
        }
    ]
    state = {
        "symbol": "BTCUSDT",
        "event_bundle": [{"event_type": "market_tick", "price": 104.0, "quote_volume": 1000000.0}],
        "market_context_history": [
            {"observed_at": "2026-04-24T07:00:00+00:00", "price": 100.0, "quote_volume": 1000000.0},
            {
                "observed_at": "2026-04-24T07:15:00+00:00",
                "price": 104.0,
                "quote_volume": 1000100.0,
                "kline_context": {
                    "period_summaries": kline_periods,
                    "volume_price_signals": ["15m:price_up_volume_expands"],
                },
            },
        ],
        "feature_snapshot": {},
    }

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["period_summaries"] == kline_periods
    assert market_context["volume_price_signals"] == ["15m:price_up_volume_expands"]
    assert market_context["wyckoff_context"]["phase"] == "markup"


def test_market_render_context_prefers_feature_snapshot_kline_ohlcv_summaries():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    kline_periods = [
        {
            "window": "15m",
            "source": "kline_ohlcv",
            "sample_count": 15,
            "start_price": 100.0,
            "end_price": 101.0,
            "price_change_pct": 1.0,
            "range_pct": 1.2,
            "quote_volume_sum": 45000.0,
            "previous_quote_volume_sum": 20000.0,
            "quote_volume_ratio": 2.25,
        }
    ]
    state = {
        "symbol": "BTCUSDT",
        "event_bundle": [{"event_type": "market_tick", "price": 101.0, "quote_volume": 1000000.0}],
        "market_context_history": [
            {"observed_at": "2026-04-24T07:00:00+00:00", "price": 100.0, "quote_volume": 1000.0},
            {"observed_at": "2026-04-24T07:15:00+00:00", "price": 101.0, "quote_volume": 1001.0},
        ],
        "feature_snapshot": {
            "kline_period_summaries": kline_periods,
            "kline_volume_price_signals": ["15m:price_up_volume_expands"],
        },
    }

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["period_summaries"] == kline_periods
    assert market_context["volume_price_signals"] == ["15m:price_up_volume_expands"]
    assert market_context["kline_context"]["period_summaries"] == kline_periods


def test_market_render_context_keeps_empty_feature_snapshot_kline_signals():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    kline_periods = [
        {
            "window": "15m",
            "source": "kline_ohlcv",
            "sample_count": 15,
            "price_change_pct": 0.1,
            "quote_volume_sum": 12000.0,
            "previous_quote_volume_sum": 11000.0,
            "quote_volume_ratio": 1.09,
        }
    ]
    state = {
        "symbol": "BTCUSDT",
        "event_bundle": [{"event_type": "market_tick", "price": 101.0, "quote_volume": 1000000.0}],
        "market_context_history": [
            {
                "observed_at": "2026-04-24T07:15:00+00:00",
                "price": 101.0,
                "quote_volume": 1001.0,
                "kline_context": {
                    "period_summaries": kline_periods,
                    "volume_price_signals": ["15m:stale_history_signal"],
                },
            },
        ],
        "feature_snapshot": {
            "kline_period_summaries": kline_periods,
            "kline_volume_price_signals": [],
        },
    }

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["period_summaries"] == kline_periods
    assert market_context["volume_price_signals"] == []


def test_market_render_context_does_not_fallback_to_ticker_signals_when_kline_signals_empty():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "symbol": "BTCUSDT",
        "event_bundle": [{"event_type": "market_tick", "price": 104.0, "quote_volume": 1000000.0}],
        "market_context_history": [
            {"observed_at": "2026-04-24T07:00:00+00:00", "price": 100.0, "quote_volume": 1000.0},
            {
                "observed_at": "2026-04-24T07:15:00+00:00",
                "price": 104.0,
                "quote_volume": 4200.0,
                "kline_context": {
                    "period_summaries": [
                        {
                            "window": "15m",
                            "source": "kline_ohlcv",
                            "sample_count": 15,
                            "start_price": 100.0,
                            "end_price": 100.2,
                            "price_change_pct": 0.2,
                            "range_pct": 0.3,
                            "quote_volume_sum": 15000.0,
                            "previous_quote_volume_sum": 15000.0,
                            "quote_volume_ratio": 1.0,
                        }
                    ],
                    "volume_price_signals": [],
                },
            },
        ],
    }

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["volume_price_signals"] == []


def test_market_render_context_does_not_fallback_to_ticker_wyckoff_when_kline_insufficient():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "symbol": "BTCUSDT",
        "event_bundle": [{"event_type": "market_tick", "price": 104.0, "quote_volume": 1000000.0}],
        "market_context_history": [
            {"observed_at": "2026-04-24T07:00:00+00:00", "price": 100.0, "quote_volume": 1000.0},
            {"observed_at": "2026-04-24T07:05:00+00:00", "price": 102.0, "quote_volume": 2000.0},
            {
                "observed_at": "2026-04-24T07:10:00+00:00",
                "price": 104.0,
                "quote_volume": 4000.0,
                "kline_context": {
                    "period_summaries": [
                        {
                            "window": "15m",
                            "source": "kline_ohlcv",
                            "sample_count": 10,
                            "expected_sample_count": 15,
                            "status": "insufficient",
                        }
                    ],
                    "volume_price_signals": [],
                },
            },
        ],
        "feature_snapshot": {},
    }

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["wyckoff_context"] == {
        "phase": "context_insufficient",
        "confidence": 0.0,
        "reason": "not_enough_kline_history",
    }
    assert market_context["period_summaries"][0]["source"] == "kline_ohlcv"


def test_market_render_context_includes_effective_price_and_wyckoff_shortterm():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context

    state = {
        "symbol": "ETHUSDT",
        "event_bundle": [{"event_type": "market_tick", "price": 100.0, "quote_volume": 1000000.0}],
        "market_context_history": [
            {
                "observed_at": "2026-04-24T07:15:00+00:00",
                "price": 104.0,
                "effective_price": 104.0,
                "effective_price_source": "mark_price",
                "market_tick_staleness_seconds": 300.0,
                "latest_trade_price": 100.0,
                "latest_kline_close": 103.2,
            }
        ],
        "feature_snapshot": {
            "effective_price": 104.0,
            "effective_price_source": "mark_price",
            "market_tick_staleness_seconds": 300.0,
            "latest_trade_price": 100.0,
            "latest_kline_close": 103.2,
            "wyckoff_shortterm": {
                "status": "ready",
                "phase": "markup",
                "entry_bias": "bullish",
                "trigger": "breakout_long",
                "trade_readiness": "ready",
                "confidence": 0.78,
            },
        },
    }

    context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    market_context = json.loads(context["market_context_json"])

    assert market_context["effective_price"] == 104.0
    assert market_context["latest_price"] == 104.0
    assert market_context["stale_trade_price"] == 100.0
    assert market_context["trade_tick_status"] == "stale"
    assert market_context["effective_price_source"] == "mark_price"
    assert market_context["market_tick_staleness_seconds"] == 300.0
    assert market_context["latest_trade_price"] == 100.0
    assert market_context["latest_kline_close"] == 103.2
    assert market_context["wyckoff_shortterm"]["trigger"] == "breakout_long"


def test_agent_render_context_hides_model_routing_from_strategy_context_json():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context, build_supervisor_render_context

    state = {
        "trace_id": "trace-model-scope",
        "symbol": "BTCUSDT",
        "strategy_context": {
            "strategy_config": {"riskMode": "normal"},
            "ai_model_config": {"id": 31, "model_code": "gpt-4.1", "provider": "openai"},
            "prompt_bindings": [{"model_id": 31, "template_code": "trade.news.v1"}],
            "agent_profiles": [{"agent_code": "news_agent", "model_id": 31}],
            "resolved_agent_configs": [{"agent_code": "news_agent", "model_id": 31}],
        },
    }

    agent_context = build_agent_render_context(state, agent_code="news_agent", rule_view={})
    supervisor_context = build_supervisor_render_context(state)

    for rendered in (agent_context["strategy_context_json"], supervisor_context["strategy_context_json"]):
        payload = json.loads(rendered)
        assert payload == {"strategy_config": {"riskMode": "normal"}}
        assert "ai_model_config" not in payload
        assert "prompt_bindings" not in payload
        assert "agent_profiles" not in payload
        assert "resolved_agent_configs" not in payload


def test_agent_render_context_hides_legacy_position_guard_pct_fields_from_strategy_context_json():
    import json

    from trade_runtime.prompting.render_context_builder import build_agent_render_context, build_supervisor_render_context

    state = {
        "trace_id": "trace-position-guard-units",
        "symbol": "ETHUSDT",
        "strategy_context": {
            "position_guard": {
                "enabled": True,
                "stop_loss_pct": 0.1,
                "take_profit_pct": 0.3,
                "stop_loss_ratio": 0.1,
                "take_profit_ratio": 0.3,
                "stop_loss_percent": 10.0,
                "take_profit_percent": 30.0,
                "threshold_unit": "ratio",
            }
        },
    }

    agent_context = build_agent_render_context(state, agent_code="market_agent", rule_view={})
    supervisor_context = build_supervisor_render_context(state)

    for rendered in (agent_context["strategy_context_json"], supervisor_context["strategy_context_json"]):
        position_guard = json.loads(rendered)["position_guard"]
        assert "stop_loss_pct" not in position_guard
        assert "take_profit_pct" not in position_guard
        assert position_guard["stop_loss_ratio"] == 0.1
        assert position_guard["take_profit_ratio"] == 0.3
        assert position_guard["stop_loss_percent"] == 10.0
        assert position_guard["take_profit_percent"] == 30.0
        assert position_guard["threshold_unit"] == "ratio"
