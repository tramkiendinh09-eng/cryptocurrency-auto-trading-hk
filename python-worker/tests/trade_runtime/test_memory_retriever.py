from datetime import datetime, timezone

from trade_runtime.memory.long_term import InMemoryLongTermMemoryStore
from trade_runtime.memory.retriever import retrieve_memory


def test_long_term_store_filters_by_agent_and_symbol():
    store = InMemoryLongTermMemoryStore(
        [
            {"id": 1, "agent_code": "news_agent", "symbol": "BTCUSDT", "lesson_text": "news lesson", "quality_score": 0.8},
            {"id": 2, "agent_code": "onchain_agent", "symbol": "BTCUSDT", "lesson_text": "onchain lesson", "quality_score": 0.9},
            {"id": 3, "agent_code": "news_agent", "symbol": "ETHUSDT", "lesson_text": "eth lesson", "quality_score": 0.7},
        ]
    )

    result = store.search(agent_code="news_agent", symbol="BTCUSDT", tags=[], limit=5)

    assert [item["id"] for item in result] == [1]


def test_long_term_store_orders_by_quality_score():
    store = InMemoryLongTermMemoryStore(
        [
            {"id": 1, "agent_code": "news_agent", "symbol": "BTCUSDT", "lesson_text": "weak", "quality_score": 0.2},
            {"id": 2, "agent_code": "news_agent", "symbol": "BTCUSDT", "lesson_text": "strong", "quality_score": 0.9},
        ]
    )

    result = store.search(agent_code="news_agent", symbol="BTCUSDT", tags=[], limit=1)

    assert result[0]["id"] == 2


def test_retrieve_memory_adds_short_and_long_term_memory():
    store = InMemoryLongTermMemoryStore(
        [
            {
                "id": 10,
                "agent_code": "news_agent",
                "symbol": "BTCUSDT",
                "lesson_text": "news memory",
                "quality_score": 0.9,
                "event_tags": ["strong_news"],
            }
        ]
    )
    state = {
        "trace_id": "trace-1",
        "symbol": "BTCUSDT",
        "event_bundle": [
            {
                "event_type": "news",
                "headline": "fresh",
                "event_time": "2026-04-28T12:00:00+00:00",
                "tags": ["strong_news"],
            }
        ],
        "memory_store": store,
    }

    enriched = retrieve_memory(state, now=datetime(2026, 4, 28, 12, 1, tzinfo=timezone.utc))

    assert enriched["short_term_memory"]["news"]["sample_count"] == 1
    assert enriched["long_term_memory"]["selected_count"] == 1
    assert enriched["long_term_memory"]["items"][0]["id"] == 10
    assert enriched["memory_usage"]["used_memory_ids"] == [10]
