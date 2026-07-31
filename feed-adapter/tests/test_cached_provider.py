from datetime import datetime, timedelta, timezone

import pytest

from feed_adapter.cached_provider import MinRefreshCachedProvider
from feed_adapter.models import UpstreamUnavailableError


class _Clock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current = self.current + timedelta(seconds=seconds)


def test_min_refresh_cached_provider_reuses_cached_items_within_refresh_window():
    clock = _Clock(datetime(2026, 4, 23, 3, 34, 15, tzinfo=timezone.utc))
    calls: list[str] = []

    def fetch(symbol: str):
        calls.append(symbol)
        return [{"symbol": symbol, "headline": f"headline-{len(calls)}"}]

    provider = MinRefreshCachedProvider(
        provider_name="news",
        provider=type("Provider", (), {"fetch": staticmethod(fetch)})(),
        min_refresh_seconds=180,
        current_time_supplier=clock.now,
    )

    first = provider.fetch("BTCUSDT")
    clock.advance(60)
    second = provider.fetch("BTCUSDT")

    assert first == [{"symbol": "BTCUSDT", "headline": "headline-1"}]
    assert second == first
    assert calls == ["BTCUSDT"]


def test_min_refresh_cached_provider_refreshes_after_refresh_window_expires():
    clock = _Clock(datetime(2026, 4, 23, 3, 34, 15, tzinfo=timezone.utc))
    calls: list[str] = []

    def fetch(symbol: str):
        calls.append(symbol)
        return [{"symbol": symbol, "headline": f"headline-{len(calls)}"}]

    provider = MinRefreshCachedProvider(
        provider_name="onchain",
        provider=type("Provider", (), {"fetch": staticmethod(fetch)})(),
        min_refresh_seconds=300,
        current_time_supplier=clock.now,
    )

    first = provider.fetch("BTCUSDT")
    clock.advance(301)
    second = provider.fetch("BTCUSDT")

    assert first == [{"symbol": "BTCUSDT", "headline": "headline-1"}]
    assert second == [{"symbol": "BTCUSDT", "headline": "headline-2"}]
    assert calls == ["BTCUSDT", "BTCUSDT"]


def test_min_refresh_cached_provider_keeps_separate_cache_per_symbol():
    clock = _Clock(datetime(2026, 4, 23, 3, 34, 15, tzinfo=timezone.utc))
    calls: list[str] = []

    def fetch(symbol: str):
        calls.append(symbol)
        return [{"symbol": symbol}]

    provider = MinRefreshCachedProvider(
        provider_name="social",
        provider=type("Provider", (), {"fetch": staticmethod(fetch)})(),
        min_refresh_seconds=300,
        current_time_supplier=clock.now,
    )

    provider.fetch("BTCUSDT")
    provider.fetch("ETHUSDT")
    provider.fetch("BTCUSDT")

    assert calls == ["BTCUSDT", "ETHUSDT"]


def test_min_refresh_cached_provider_does_not_mask_refresh_failures_after_window_expires():
    clock = _Clock(datetime(2026, 4, 23, 3, 34, 15, tzinfo=timezone.utc))
    calls = 0

    class Provider:
        def fetch(self, symbol: str):
            nonlocal calls
            calls += 1
            if calls == 1:
                return [{"symbol": symbol, "headline": "headline-1"}]
            raise UpstreamUnavailableError("news_upstream_unavailable")

    provider = MinRefreshCachedProvider(
        provider_name="news",
        provider=Provider(),
        min_refresh_seconds=180,
        current_time_supplier=clock.now,
    )

    provider.fetch("BTCUSDT")
    clock.advance(181)

    with pytest.raises(UpstreamUnavailableError, match="news_upstream_unavailable"):
        provider.fetch("BTCUSDT")

