from datetime import datetime, timezone

from trade_runtime.active_signal_store import InMemoryActiveSignalStore


def test_active_signal_store_keeps_valid_signal_and_expires_it_after_ttl():
    store = InMemoryActiveSignalStore()
    first_now = datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc)
    second_now = datetime(2026, 4, 17, 8, 4, tzinfo=timezone.utc)
    expired_now = datetime(2026, 4, 17, 8, 11, tzinfo=timezone.utc)

    store.upsert(
        {
            "symbol": "BTCUSDT",
            "window_key": "news:BTCUSDT:15m",
            "source_type": "news",
            "signal_type": "headline",
            "direction": "bullish",
            "strength_score": 0.92,
            "decay_score": 0.92,
            "opened_at": first_now.isoformat(),
            "expires_at": datetime(2026, 4, 17, 8, 10, tzinfo=timezone.utc).isoformat(),
            "last_event_at": first_now.isoformat(),
            "last_confirmed_at": first_now.isoformat(),
            "dedupe_key": "news:etf-approval",
            "combine_until_at": datetime(2026, 4, 17, 8, 10, tzinfo=timezone.utc).isoformat(),
            "active": True,
            "state": {"count": 1, "latest_headline": "ETF approval", "max_score": 0.92},
        },
        now=first_now,
    )

    active_snapshot = store.snapshot(symbol="BTCUSDT", now=second_now)
    expired_snapshot = store.snapshot(symbol="BTCUSDT", now=expired_now)

    assert len(active_snapshot) == 1
    assert active_snapshot[0]["source_type"] == "news"
    assert active_snapshot[0]["dedupe_key"] == "news:etf-approval"
    assert expired_snapshot == []
