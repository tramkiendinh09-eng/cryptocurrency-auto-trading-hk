"""Reddit 社交源：坏在用错端点，不是 IP 被封。

/new.json 返回 403，/new/.rss 直连返回 200。这个源从上线起就没拿到过数据，
一直被当成"Reddit 封了机房 IP"。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from feed_adapter.providers.social import RedditRssSocialProvider

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


def _atom(entries: list[tuple[str, str, str]]) -> str:
    body = ''.join(
        '<entry><title>{t}</title><content>{c}</content>'
        '<id>{i}</id><link href="{i}"/><published>2026-09-04T11:00:00+00:00</published>'
        '<author><name>/u/tester</name></author></entry>'.format(t=t, c=c, i=i)
        for t, c, i in entries
    )
    return '<feed xmlns="http://www.w3.org/2005/Atom">%s</feed>' % body


class _Clock:
    def __init__(self, start):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


def _provider(xml, clock):
    return RedditRssSocialProvider(
        listing_urls=['https://www.reddit.com/r/CryptoCurrency/new/.rss'],
        fetch_text=lambda url, timeout, user_agent=None: xml,
        current_time_supplier=clock,
    )


def test_posts_are_returned_as_context():
    clock = _Clock(NOW)
    xml = _atom([('Solana network upgrade lands', 'body', 'https://redd.it/a1')])
    rows = _provider(xml, clock).fetch('SOLUSDT')
    assert len(rows) == 1
    assert rows[0]['headline'] == 'Solana network upgrade lands'
    assert rows[0]['url'] == 'https://redd.it/a1'
    assert rows[0]['source'] == 'reddit_rss'


def test_score_is_always_neutral_so_this_source_never_triggers():
    """刻意设计：trigger_policy 要求 social_direction != "neutral" 才 fire。

    RSS 没有赞数与评论数，要产出方向就只能手搓褒贬词表——那是凭空造一个
    没人验证过的信号，而社交数据没有历史归档，做不了回测证伪。所以这个源
    只做上下文，把真实标题交给模型自己读。
    """
    clock = _Clock(NOW)
    xml = _atom([
        ('Solana to the moon, massive pump incoming', 'x', 'https://redd.it/b1'),
        ('Solana crashing hard, sell everything', 'x', 'https://redd.it/b2'),
    ])
    rows = _provider(xml, clock).fetch('SOLUSDT')
    assert len(rows) == 2
    # 无论标题多么明显地看多或看空，分数都是 0
    assert all(r['score'] == 0.0 for r in rows)


def test_symbol_filtering_still_applies():
    clock = _Clock(NOW)
    xml = _atom([('Bitcoin ETF inflows hit record', 'x', 'https://redd.it/c1')])
    assert _provider(xml, clock).fetch('SOLUSDT') == []
    assert len(_provider(xml, _Clock(NOW)).fetch('BTCUSDT')) == 1


def test_the_same_post_is_not_re_emitted():
    """RSS 每轮返回同一批条目，不去重的话同一个帖子会被反复当成新事件——
    新闻源和 OKX 爆仓单上都踩过同一个坑。"""
    clock = _Clock(NOW)
    xml = _atom([('Solana upgrade', 'x', 'https://redd.it/d1')])
    provider = _provider(xml, clock)
    assert len(provider.fetch('SOLUSDT')) == 1
    clock.advance(minutes=5)
    assert provider.fetch('SOLUSDT') == []


def test_a_new_post_still_comes_through_after_an_old_one():
    clock = _Clock(NOW)
    first = _atom([('Solana upgrade', 'x', 'https://redd.it/e1')])
    holder = {'xml': first}
    provider = RedditRssSocialProvider(
        listing_urls=['https://x/rss'],
        fetch_text=lambda url, timeout, user_agent=None: holder['xml'],
        current_time_supplier=clock,
    )
    assert len(provider.fetch('SOLUSDT')) == 1
    holder['xml'] = _atom([
        ('Solana upgrade', 'x', 'https://redd.it/e1'),
        ('Solana outage report', 'x', 'https://redd.it/e2'),
    ])
    clock.advance(minutes=5)
    fresh = provider.fetch('SOLUSDT')
    assert [r['url'] for r in fresh] == ['https://redd.it/e2']


def test_malformed_xml_does_not_raise():
    clock = _Clock(NOW)
    assert _provider('not xml at all', clock).fetch('SOLUSDT') == []


def test_one_rss_is_downloaded_once_for_all_symbols():
    """12 个标的 x 4 个子版 = 一轮 48 次请求，实测第二个标的就开始 429。

    上游请求量必须与标的数量脱钩——新闻源上是同一套做法。
    """
    clock = _Clock(NOW)
    calls = []
    xml = _atom([
        ("Solana upgrade lands", "x", "https://redd.it/f1"),
        ("Bitcoin ETF inflows", "x", "https://redd.it/f2"),
    ])

    def fetch(url, timeout, user_agent=None):
        calls.append(url)
        return xml

    provider = RedditRssSocialProvider(
        listing_urls=["https://x/rss"],
        fetch_text=fetch,
        current_time_supplier=clock,
        document_cache_seconds=300,
    )
    provider.fetch("SOLUSDT")
    provider.fetch("BTCUSDT")
    provider.fetch("ETHUSDT")
    assert len(calls) == 1, "同一个刷新窗口内只该下载一次"

    clock.advance(seconds=301)
    provider.fetch("SOLUSDT")
    assert len(calls) == 2, "窗口过后应重新下载"


def test_cache_disabled_by_default_still_fetches_each_time():
    clock = _Clock(NOW)
    calls = []
    provider = RedditRssSocialProvider(
        listing_urls=["https://x/rss"],
        fetch_text=lambda url, timeout, user_agent=None: (calls.append(url), _atom([]))[1],
        current_time_supplier=clock,
    )
    provider.fetch("SOLUSDT")
    provider.fetch("BTCUSDT")
    assert len(calls) == 2


def test_a_failed_fetch_is_also_cached():
    """一次 429 不该让 12 个标的把同一个子版各重试一遍——那正好把限流坐实。"""
    clock = _Clock(NOW)
    calls = []

    def boom(url, timeout, user_agent=None):
        calls.append(url)
        raise RuntimeError("429 Too Many Requests")

    provider = RedditRssSocialProvider(
        listing_urls=["https://x/rss"],
        fetch_text=boom,
        current_time_supplier=clock,
        document_cache_seconds=300,
    )
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"):
        try:
            provider.fetch(symbol)
        except Exception:
            pass
    assert len(calls) == 1, "失败之后窗口内不该再打上游"

    clock.advance(seconds=301)
    try:
        provider.fetch("BTCUSDT")
    except Exception:
        pass
    assert len(calls) == 2, "窗口过后应重试"
