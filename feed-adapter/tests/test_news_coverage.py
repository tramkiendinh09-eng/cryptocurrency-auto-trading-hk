"""新闻链路的三个回归点。

这三条都对应线上真实发生过的故障，不是补充覆盖率用的。
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from feed_adapter.providers.news import RssNewsProvider
from feed_adapter.symbols import DEFAULT_SYMBOL_KEYWORDS, keywords_for_symbol, matches_symbol


# 线上 runtime config 的 allowedSymbols。新增标的时这里要同步补关键词，
# 否则该标的的新闻会静默恒为 0。
LIVE_SYMBOLS = [
    "SNDKUSDT", "SKHYNIXUSDT", "MUUSDT", "WDCUSDT", "SAMSUNGUSDT", "NVDAUSDT",
    "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT", "SUIUSDT",
]


class TestSymbolCoverage:
    @pytest.mark.parametrize("symbol", LIVE_SYMBOLS)
    def test_every_live_symbol_has_explicit_keywords(self, symbol):
        """没有映射时会退化成搜标的名本身（"nvdausdt"），新闻永远为 0。

        这正是线上 12 个标的里 10 个新闻恒为 0 的原因，必须挡住。
        """
        assert symbol in DEFAULT_SYMBOL_KEYWORDS, (
            f"{symbol} 缺少关键词映射，它的新闻会静默恒为 0"
        )
        assert keywords_for_symbol(symbol) != [symbol.lower()]

    def test_semiconductor_symbols_match_company_names(self):
        assert matches_symbol("NVDAUSDT", "Nvidia beats on earnings", "")
        assert matches_symbol("MUUSDT", "Micron raises guidance", "")
        assert matches_symbol("SKHYNIXUSDT", "SK Hynix HBM supply deal", "")
        assert matches_symbol("SNDKUSDT", "SanDisk spins off", "")
        assert matches_symbol("WDCUSDT", "Western Digital cuts capacity", "")
        assert matches_symbol("SAMSUNGUSDT", "Samsung foundry outlook", "")

    def test_binance_alone_does_not_match_bnb(self):
        """"binance" 会命中所有交易所新闻，不能作为 BNB 的关键词。"""
        assert not matches_symbol("BNBUSDT", "Binance lists a new token", "")
        assert matches_symbol("BNBUSDT", "BNB rallies", "")


def _rss(*titles: str) -> str:
    items = "".join(
        f"<item><title>{t}</title><description></description>"
        f"<pubDate>Wed, 02 Sep 2026 12:00:00 GMT</pubDate></item>"
        for t in titles
    )
    return f"<rss><channel>{items}</channel></rss>"


class TestDocumentCache:
    def test_one_fetch_serves_every_symbol(self):
        """按标的缓存挡不住重复抓取：12 个标的会把同一篇 RSS 抓 12 遍。"""
        calls = []

        def fake_fetch(url, timeout, user_agent=None):
            calls.append(url)
            return _rss("Nvidia earnings beat", "Micron guidance raised")

        provider = RssNewsProvider(
            feed_urls=["https://example.test/rss"],
            fetch_text=fake_fetch,
            current_time_supplier=lambda: datetime(2026, 9, 2, 12, 30, tzinfo=timezone.utc),
            document_cache_seconds=180,
        )

        assert len(provider.fetch("NVDAUSDT")) == 1
        assert len(provider.fetch("MUUSDT")) == 1
        assert provider.fetch("SNDKUSDT") == []
        assert len(calls) == 1, f"同一篇 RSS 被抓了 {len(calls)} 次，应当只抓 1 次"

    def test_cache_expires(self):
        calls = []
        now = [datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)]

        def fake_fetch(url, timeout, user_agent=None):
            calls.append(url)
            return _rss("Nvidia earnings beat")

        provider = RssNewsProvider(
            feed_urls=["https://example.test/rss"],
            fetch_text=fake_fetch,
            current_time_supplier=lambda: now[0],
            document_cache_seconds=180,
            max_age_hours=0,
        )
        provider.fetch("NVDAUSDT")
        now[0] = now[0].replace(minute=4)   # 超过 180 秒
        provider.fetch("NVDAUSDT")
        assert len(calls) == 2

    def test_disabled_cache_fetches_every_time(self):
        calls = []

        def fake_fetch(url, timeout, user_agent=None):
            calls.append(url)
            return _rss("Nvidia earnings beat")

        provider = RssNewsProvider(
            feed_urls=["https://example.test/rss"],
            fetch_text=fake_fetch,
            current_time_supplier=lambda: datetime(2026, 9, 2, 12, 30, tzinfo=timezone.utc),
            document_cache_seconds=0,
        )
        provider.fetch("NVDAUSDT")
        provider.fetch("NVDAUSDT")
        assert len(calls) == 2


class TestScoring:
    def _score(self, title: str) -> float:
        provider = RssNewsProvider(
            feed_urls=[],
            current_time_supplier=lambda: datetime(2026, 9, 2, 12, 30, tzinfo=timezone.utc),
        )
        return provider._score_item(title, "", "2026-09-02T12:00:00Z")

    def test_substring_no_longer_counts_as_an_event(self):
        """三个字母的 "sec" 曾经命中 second / sector / cybersecurity，
        把大量普通报道误抬到 0.80 触发线以上。"""
        for noise in ("Delays IPO to second quarter",
                      "The sector rallied today",
                      "A cybersecurity vendor raised funding"):
            assert self._score(noise) < 0.80, noise

    def test_real_sec_still_counts(self):
        assert self._score("SEC approves the filing") >= 0.80

    def test_equity_event_words_count(self):
        for headline in ("Nvidia earnings beat estimates",
                         "Micron raises guidance",
                         "New export control on chip tools",
                         "Analyst downgrade for Samsung"):
            assert self._score(headline) >= 0.80, headline

    def test_routine_coverage_stays_below_threshold(self):
        assert self._score("Nvidia announces a developer conference") < 0.80

class TestFreshness:
    """时效是触发的前提，不是加分项。

    线上抓到过一条 16.5 小时前的财报标题，因为命中 "earnings" 拿到
    0.85 分、越过 newsTrigger 的 0.80，然后在整个 24 小时保留窗口里
    每 300 秒重新触发一次。
    """

    def _provider(self):
        return RssNewsProvider(
            feed_urls=[],
            current_time_supplier=lambda: datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
        )

    def test_fresh_event_triggers(self):
        score = self._provider()._score_item(
            "Nvidia earnings beat", "", "2026-09-02T09:00:00Z"   # 3 小时前
        )
        assert score >= 0.80

    def test_stale_event_stays_below_trigger(self):
        score = self._provider()._score_item(
            "Nvidia earnings beat", "", "2026-09-01T19:30:00Z"   # 16.5 小时前
        )
        # 0.70 是 worker 的 ruleOnlyScoreThreshold：越过它就会产生一次
        # RULE_ONLY 分发，那也是触发，所以要压在它之下而不只是 0.80 之下。
        assert score < 0.70, "旧新闻不应产生任何分发"

    def test_boundary_is_the_fresh_window(self):
        p = self._provider()
        just_inside = p._score_item("Micron guidance raised", "", "2026-09-02T04:30:00Z")   # 7.5h
        just_outside = p._score_item("Micron guidance raised", "", "2026-09-02T03:30:00Z")  # 8.5h
        assert just_inside >= 0.80
        assert just_outside < 0.80

    def test_missing_publish_time_is_treated_as_stale(self):
        """拿不到发布时间就当不新鲜——宁可漏触发，也不要按来历不明的条目开仓。"""
        assert self._provider()._score_item("Nvidia earnings beat", "", "") < 0.80

    def test_stale_items_are_still_returned_as_context(self):
        """封的是触发资格，不是可见性：旧新闻仍要进模型的上下文。"""
        rss = (
            "<rss><channel><item><title>Nvidia earnings beat</title>"
            "<description></description>"
            "<pubDate>Tue, 01 Sep 2026 19:30:00 GMT</pubDate></item></channel></rss>"
        )
        provider = RssNewsProvider(
            feed_urls=["https://example.test/rss"],
            fetch_text=lambda url, timeout, ua=None: rss,
            current_time_supplier=lambda: datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            max_age_hours=24,
        )
        items = provider.fetch("NVDAUSDT")
        assert len(items) == 1, "旧新闻仍应返回"
        assert items[0]["score"] < 0.80, "但不应越过触发线"
