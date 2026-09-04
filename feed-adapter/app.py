import logging

from feed_adapter.cached_provider import MinRefreshCachedProvider
from feed_adapter.config import load_settings
from feed_adapter.providers.news import RssNewsProvider
from feed_adapter.providers.onchain import OnchainFlowsProvider
from feed_adapter.providers.social import RedditRssSocialProvider
from feed_adapter.server import create_server
from feed_adapter.service import FeedAdapterService


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def build_service() -> FeedAdapterService:
    settings = load_settings()
    return FeedAdapterService(
        news_provider=MinRefreshCachedProvider(
            provider_name="news",
            min_refresh_seconds=settings.news_min_refresh_seconds,
            provider=RssNewsProvider(
                feed_urls=settings.news_feed_urls,
                timeout=settings.request_timeout_seconds,
                max_age_hours=settings.news_max_age_hours,
                user_agent=settings.user_agent,
                # 与按标的的刷新窗口同步：一篇 RSS 在一个窗口内只抓一次，
                # 12 个标的共用，上游请求量与标的数量脱钩
                document_cache_seconds=settings.news_min_refresh_seconds,
            ),
        ),
        social_provider=MinRefreshCachedProvider(
            provider_name="social",
            min_refresh_seconds=settings.social_min_refresh_seconds,
            provider=RedditRssSocialProvider(
                listing_urls=settings.social_listing_urls,
                timeout=settings.request_timeout_seconds,
                user_agent=settings.user_agent,
                # 与按标的的刷新窗口同步：一篇 RSS 在一个窗口内只抓一次，
                # 12 个标的共用，否则 Reddit 会直接 429
                document_cache_seconds=settings.social_min_refresh_seconds,
            ),
        ),
        onchain_provider=MinRefreshCachedProvider(
            provider_name="onchain",
            min_refresh_seconds=settings.onchain_min_refresh_seconds,
            provider=OnchainFlowsProvider(
                page_urls=settings.onchain_page_urls,
                timeout=settings.request_timeout_seconds,
                user_agent=settings.user_agent,
                max_age_minutes=settings.onchain_max_age_minutes,
            ),
        ),
    )


def main() -> None:
    configure_logging()
    settings = load_settings()
    logging.getLogger(__name__).info(
        "feed_adapter_settings host=%s port=%s news_max_age_hours=%s news_min_refresh_seconds=%s social_min_refresh_seconds=%s onchain_min_refresh_seconds=%s onchain_max_age_minutes=%s news_feed_count=%s social_feed_count=%s onchain_page_count=%s",
        settings.host,
        settings.port,
        settings.news_max_age_hours,
        settings.news_min_refresh_seconds,
        settings.social_min_refresh_seconds,
        settings.onchain_min_refresh_seconds,
        settings.onchain_max_age_minutes,
        len(settings.news_feed_urls),
        len(settings.social_listing_urls),
        len(settings.onchain_page_urls),
    )
    server = create_server(settings.host, settings.port, build_service())
    print(f"feed-adapter listening on {settings.host}:{settings.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
