import time

from trade_runtime.decision.nodes.multi_agent_node import multi_agent_node


def test_multi_agent_node_degrades_timed_out_specialists(monkeypatch):
    def slow_market(state):
        time.sleep(0.05)
        state["market_view"] = {"bias": "bullish", "confidence": 80, "reason": "slow", "ttl": 60, "risk_note": "ok"}
        return state

    def fast_news(state):
        state["news_view"] = {"bias": "bullish", "confidence": 72, "reason": "fast", "ttl": 60, "risk_note": "ok"}
        return state

    monkeypatch.setattr(
        "trade_runtime.decision.nodes.multi_agent_node.SPECIALIST_RUNNERS",
        (
            ("market_view", slow_market),
            ("news_view", fast_news),
        ),
    )

    state = multi_agent_node(
        {
            "strategy_context": {
                "strategy_config": {
                    "agentTimeoutSeconds": 0.01,
                    "agentMaxConcurrency": 2,
                    "agentCircuitBreakerThreshold": 1,
                }
            }
        }
    )

    assert state["news_view"]["reason"] == "fast"
    assert state["market_view"]["reason"] == "agent_timeout_fallback"
    assert state["multi_agent_runtime"]["timedOutAgents"] == ["market_view"]
    assert state["multi_agent_runtime"]["circuitOpen"] is True
    assert state["agent_circuit_breaker"]["circuit_open"] is True


def test_multi_agent_node_uses_agent_profile_timeout_override(monkeypatch):
    def slow_market(state):
        time.sleep(0.02)
        state["market_view"] = {"bias": "bullish", "confidence": 80, "reason": "slow", "ttl": 60, "risk_note": "ok"}
        return state

    monkeypatch.setattr(
        "trade_runtime.decision.nodes.multi_agent_node.SPECIALIST_RUNNERS",
        (("market_view", slow_market),),
    )

    state = multi_agent_node(
        {
            "strategy_context": {
                "strategy_config": {
                    "agentTimeoutSeconds": 0.01,
                    "agentMaxConcurrency": 1,
                    "agentCircuitBreakerThreshold": 1,
                }
            },
            "agent_profiles": [
                {
                    "agent_code": "market_agent",
                    "enabled": True,
                    "timeout_seconds": 1,
                }
            ],
        }
    )

    assert state["market_view"]["reason"] == "slow"
    assert state["multi_agent_runtime"]["timedOutAgents"] == []
    assert state["multi_agent_runtime"]["completedAgents"] == ["market_view"]


def test_multi_agent_node_defaults_timeout_to_45_seconds(monkeypatch):
    def fast_market(state):
        state["market_view"] = {"bias": "bullish", "confidence": 80, "reason": "fast", "ttl": 60, "risk_note": "ok"}
        return state

    monkeypatch.setattr(
        "trade_runtime.decision.nodes.multi_agent_node.SPECIALIST_RUNNERS",
        (("market_view", fast_market),),
    )

    state = multi_agent_node({})

    assert state["multi_agent_runtime"]["timeoutSeconds"] == 45.0
