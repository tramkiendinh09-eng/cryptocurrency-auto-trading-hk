from __future__ import annotations

import json
import os
from dataclasses import dataclass


DEFAULT_NEWS_FEED_URLS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

DEFAULT_SOCIAL_LISTING_URLS = [
    "https://www.reddit.com/r/CryptoCurrency/new.json?limit=25",
    "https://www.reddit.com/r/BitcoinMarkets/new.json?limit=25",
]

DEFAULT_ONCHAIN_PAGE_URLS = [
    "https://onchainflows.io/",
]


@dataclass(frozen=True)
class AdapterSettings:
    host: str
    port: int
    request_timeout_seconds: int
    news_max_age_hours: int
    news_min_refresh_seconds: int
    social_min_refresh_seconds: int
    onchain_min_refresh_seconds: int
    onchain_max_age_minutes: int
    user_agent: str
    news_feed_urls: list[str]
    social_listing_urls: list[str]
    onchain_page_urls: list[str]


def _load_json_list(name: str, default: list[str]) -> list[str]:
    raw_value = str(os.getenv(name, "") or "").strip()
    if not raw_value:
        return list(default)
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        payload = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not isinstance(payload, list):
        return list(default)
    resolved = [str(item or "").strip() for item in payload if str(item or "").strip()]
    return resolved or list(default)


def load_settings() -> AdapterSettings:
    return AdapterSettings(
        host=str(os.getenv("FEED_ADAPTER_HOST", "0.0.0.0") or "0.0.0.0").strip(),
        port=int(str(os.getenv("FEED_ADAPTER_PORT", "18080") or "18080").strip()),
        request_timeout_seconds=int(
            str(os.getenv("FEED_ADAPTER_REQUEST_TIMEOUT_SECONDS", "8") or "8").strip()
        ),
        news_max_age_hours=int(
            str(os.getenv("FEED_ADAPTER_NEWS_MAX_AGE_HOURS", "24") or "24").strip()
        ),
        news_min_refresh_seconds=int(
            str(os.getenv("FEED_ADAPTER_NEWS_MIN_REFRESH_SECONDS", "180") or "180").strip()
        ),
        social_min_refresh_seconds=int(
            str(os.getenv("FEED_ADAPTER_SOCIAL_MIN_REFRESH_SECONDS", "300") or "300").strip()
        ),
        onchain_min_refresh_seconds=int(
            str(os.getenv("FEED_ADAPTER_ONCHAIN_MIN_REFRESH_SECONDS", "300") or "300").strip()
        ),
        onchain_max_age_minutes=int(
            str(os.getenv("FEED_ADAPTER_ONCHAIN_MAX_AGE_MINUTES", "30") or "30").strip()
        ),
        user_agent=str(
            os.getenv("FEED_ADAPTER_USER_AGENT", "web4-first-feed-adapter/1.0")
            or "web4-first-feed-adapter/1.0"
        ).strip(),
        news_feed_urls=_load_json_list("FEED_ADAPTER_NEWS_FEED_URLS", DEFAULT_NEWS_FEED_URLS),
        social_listing_urls=_load_json_list(
            "FEED_ADAPTER_SOCIAL_LISTING_URLS",
            DEFAULT_SOCIAL_LISTING_URLS,
        ),
        onchain_page_urls=_load_json_list(
            "FEED_ADAPTER_ONCHAIN_PAGE_URLS",
            DEFAULT_ONCHAIN_PAGE_URLS,
        ),
    )
