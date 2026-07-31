import logging

from feed_adapter.service import FeedAdapterService


class StubNewsProvider:
    def fetch(self, symbol: str):
        assert symbol == "BTCUSDT"
        return [{"symbol": symbol, "headline": "ETF inflow", "score": 0.91, "source": "rss"}]


class StubSocialProvider:
    def fetch(self, symbol: str):
        assert symbol == "BTCUSDT"
        return [{"symbol": symbol, "headline": "Reddit post", "score": 0.84, "author": "alice", "source": "reddit"}]


class StubOnchainProvider:
    def fetch(self, symbol: str):
        assert symbol == "BTCUSDT"
        return []


def test_feed_adapter_service_returns_health_payload():
    service = FeedAdapterService(
        news_provider=StubNewsProvider(),
        social_provider=StubSocialProvider(),
        onchain_provider=StubOnchainProvider(),
    )

    payload = service.handle("health", {})

    assert payload == {"status": "ok"}


def test_feed_adapter_service_returns_runtime_news_payload():
    service = FeedAdapterService(
        news_provider=StubNewsProvider(),
        social_provider=StubSocialProvider(),
        onchain_provider=StubOnchainProvider(),
    )

    payload = service.handle("runtime/news", {"symbol": "BTCUSDT"})

    assert payload["source_status"] == "ready"
    assert payload["source_name"] == "news"
    assert payload["items"][0]["symbol"] == "BTCUSDT"
    assert payload["items"][0]["headline"] == "ETF inflow"


def test_feed_adapter_service_returns_ready_empty_onchain_payload():
    service = FeedAdapterService(
        news_provider=StubNewsProvider(),
        social_provider=StubSocialProvider(),
        onchain_provider=StubOnchainProvider(),
    )

    payload = service.handle("runtime/onchain", {"symbol": "BTCUSDT"})

    assert payload["source_status"] == "ready"
    assert payload["source_name"] == "onchain"
    assert payload["items"] == []


def test_feed_adapter_service_logs_runtime_source_summary(caplog):
    service = FeedAdapterService(
        news_provider=StubNewsProvider(),
        social_provider=StubSocialProvider(),
        onchain_provider=StubOnchainProvider(),
    )

    with caplog.at_level(logging.INFO):
        payload = service.handle("runtime/news", {"symbol": "BTCUSDT"})

    assert payload["source_status"] == "ready"
    assert "route=runtime/news" in caplog.text
    assert "source=news" in caplog.text
    assert "symbol=BTCUSDT" in caplog.text
    assert "items=1" in caplog.text
    assert "source_status=ready" in caplog.text
