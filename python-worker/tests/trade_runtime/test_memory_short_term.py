from datetime import datetime, timedelta, timezone

from trade_runtime.memory.schema import DEFAULT_SHORT_TERM_TTLS, normalize_ttl_policy
from trade_runtime.memory.short_term import build_short_term_memory


def test_default_short_term_ttls_match_product_policy():
    assert DEFAULT_SHORT_TERM_TTLS == {
        "market": 3600,
        "news": 3600,
        "onchain": 7200,
        "social": 1800,
        "supervisor_decision": 7200,
    }


def test_normalize_ttl_policy_rejects_non_positive_values():
    policy = normalize_ttl_policy({"market": -1, "news": 120})
    assert policy["market"] == 3600
    assert policy["news"] == 120
    assert policy["onchain"] == 7200


def test_build_short_term_memory_applies_source_ttls():
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    state = {
        "event_bundle": [
            {"event_type": "news", "headline": "fresh news", "event_time": (now - timedelta(minutes=20)).isoformat()},
            {"event_type": "news", "headline": "stale news", "event_time": (now - timedelta(minutes=90)).isoformat()},
            {"event_type": "onchain", "flow": "exchange_outflow", "event_time": (now - timedelta(minutes=90)).isoformat()},
            {"event_type": "social", "source": "x", "event_time": (now - timedelta(minutes=45)).isoformat()},
        ],
        "market_context_history": [
            {"price": 100.0, "observed_at": (now - timedelta(minutes=30)).isoformat()},
            {"price": 90.0, "observed_at": (now - timedelta(minutes=80)).isoformat()},
        ],
        "agent_messages": [],
    }

    memory = build_short_term_memory(state, now=now)

    assert memory["news"]["sample_count"] == 1
    assert memory["news"]["items"][0]["headline"] == "fresh news"
    assert memory["onchain"]["sample_count"] == 1
    assert memory["social"]["sample_count"] == 0
    assert memory["market"]["sample_count"] == 1


def test_build_short_term_memory_includes_recent_supervisor_decision():
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    state = {
        "agent_messages": [
            {
                "speaker_agent": "supervisor_agent",
                "message_type": "decision",
                "content_json": {"action": "hold", "summary_reason": "risk cap reached"},
                "created_at": (now - timedelta(minutes=30)).isoformat(),
            }
        ]
    }

    memory = build_short_term_memory(state, now=now)

    assert memory["supervisor_decision"]["sample_count"] == 1
    assert memory["supervisor_decision"]["items"][0]["content_json"]["action"] == "hold"
