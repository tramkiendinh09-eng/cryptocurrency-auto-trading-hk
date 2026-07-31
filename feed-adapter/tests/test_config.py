from feed_adapter.config import load_settings


def test_load_settings_uses_default_source_refresh_intervals(monkeypatch):
    monkeypatch.delenv("FEED_ADAPTER_NEWS_MIN_REFRESH_SECONDS", raising=False)
    monkeypatch.delenv("FEED_ADAPTER_ONCHAIN_MIN_REFRESH_SECONDS", raising=False)
    monkeypatch.delenv("FEED_ADAPTER_SOCIAL_MIN_REFRESH_SECONDS", raising=False)

    settings = load_settings()

    assert settings.news_min_refresh_seconds == 180
    assert settings.onchain_min_refresh_seconds == 300
    assert settings.social_min_refresh_seconds == 300
