import logging

from datetime import datetime, timezone

from feed_adapter.providers.news import RssNewsProvider


def test_rss_news_provider_filters_symbol_and_builds_items():
    xml_payload = """
    <rss>
      <channel>
        <item>
          <title>Bitcoin ETF inflow accelerates</title>
          <description>Spot BTC demand increases.</description>
          <pubDate>Mon, 21 Apr 2026 12:00:00 GMT</pubDate>
          <link>https://example.com/btc</link>
        </item>
        <item>
          <title>Ethereum gas update</title>
          <description>ETH network update.</description>
          <pubDate>Mon, 21 Apr 2026 11:00:00 GMT</pubDate>
          <link>https://example.com/eth</link>
        </item>
      </channel>
    </rss>
    """.strip()

    provider = RssNewsProvider(
        feed_urls=["https://news.example/rss"],
        fetch_text=lambda url, timeout: xml_payload,
        current_time_supplier=lambda: datetime(2026, 4, 21, 7, 3, 23, tzinfo=timezone.utc),
        max_age_hours=4,
    )

    items = provider.fetch("BTCUSDT")

    assert len(items) == 1
    assert items[0]["symbol"] == "BTCUSDT"
    assert items[0]["headline"] == "Bitcoin ETF inflow accelerates"
    assert items[0]["summary"] == "Spot BTC demand increases."
    assert items[0]["source"] == "news.example"
    assert items[0]["score"] >= 0.9


def test_rss_news_provider_filters_out_stale_news_items():
    xml_payload = """
    <rss>
      <channel>
        <item>
          <title>Bitcoin ETF inflow accelerates</title>
          <description>Fresh BTC item.</description>
          <pubDate>Mon, 21 Apr 2026 05:45:58 GMT</pubDate>
          <link>https://example.com/fresh</link>
        </item>
        <item>
          <title>Bitcoin old macro story</title>
          <description>Old BTC item.</description>
          <pubDate>Sun, 20 Apr 2026 16:10:28 GMT</pubDate>
          <link>https://example.com/stale</link>
        </item>
      </channel>
    </rss>
    """.strip()

    provider = RssNewsProvider(
        feed_urls=["https://news.example/rss"],
        fetch_text=lambda url, timeout: xml_payload,
        current_time_supplier=lambda: datetime(2026, 4, 21, 7, 3, 23, tzinfo=timezone.utc),
        max_age_hours=4,
    )

    items = provider.fetch("BTCUSDT")

    assert len(items) == 1
    assert items[0]["headline"] == "Bitcoin ETF inflow accelerates"


def test_rss_news_provider_logs_fetch_and_filter_summary(caplog):
    xml_payload = """
    <rss>
      <channel>
        <item>
          <title>Bitcoin ETF inflow accelerates</title>
          <description>Fresh BTC item.</description>
          <pubDate>Mon, 21 Apr 2026 05:45:58 GMT</pubDate>
        </item>
        <item>
          <title>Bitcoin old macro story</title>
          <description>Old BTC item.</description>
          <pubDate>Sun, 20 Apr 2026 16:10:28 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """.strip()

    provider = RssNewsProvider(
        feed_urls=["https://news.example/rss"],
        fetch_text=lambda url, timeout: xml_payload,
        current_time_supplier=lambda: datetime(2026, 4, 21, 7, 3, 23, tzinfo=timezone.utc),
        max_age_hours=4,
    )

    with caplog.at_level(logging.INFO):
        items = provider.fetch("BTCUSDT")

    assert len(items) == 1
    assert "provider=news" in caplog.text
    assert "url=https://news.example/rss" in caplog.text
    assert "symbol=BTCUSDT" in caplog.text
    assert "total_items=2" in caplog.text
    assert "stale_filtered=1" in caplog.text
    assert "returned_items=1" in caplog.text
    assert "max_age_hours=4" in caplog.text
    assert "current_time_utc=2026-04-21T07:03:23Z" in caplog.text


def test_rss_news_provider_supports_configurable_max_age_hours():
    xml_payload = """
    <rss>
      <channel>
        <item>
          <title>Bitcoin ETF inflow accelerates</title>
          <description>BTC item still relevant.</description>
          <pubDate>Mon, 21 Apr 2026 00:30:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """.strip()

    provider = RssNewsProvider(
        feed_urls=["https://news.example/rss"],
        fetch_text=lambda url, timeout: xml_payload,
        current_time_supplier=lambda: datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc),
        max_age_hours=24,
    )

    items = provider.fetch("BTCUSDT")

    assert len(items) == 1
    assert items[0]["headline"] == "Bitcoin ETF inflow accelerates"
