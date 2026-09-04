"""一篇报道只该触发一次。

RSS 里一条新闻会挂 max_age_hours（默认 24 小时），而适配器每 180 秒轮询一次，
于是同一篇报道被当成新事件重复发出最多约 480 次。实测 NVDAUSDT 近 6 小时
888 条新闻事件里只有 188 个不同标题，最重复的一条发了 31 次——news 触发器
按分数判定，同一条信息把触发和 LLM 预算反复消耗掉，而模型每次看到的是同
一件事。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from feed_adapter.providers.news import RssNewsProvider


def _feed(items: list[tuple[str, str, str]], published: datetime) -> str:
    body = ''.join(
        '<item><title>{t}</title><description>{d}</description>'
        '<link>{l}</link><guid>{l}</guid><pubDate>{p}</pubDate></item>'.format(
            t=title, d=summary, l=link,
            p=published.strftime('%a, %d %b %Y %H:%M:%S +0000'))
        for title, summary, link in items
    )
    return '<rss><channel>%s</channel></rss>' % body


class _Clock:
    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


def _provider(xml: str, clock: _Clock) -> RssNewsProvider:
    return RssNewsProvider(
        feed_urls=['https://example.test/rss'],
        fetch_text=lambda url, timeout, user_agent=None: xml,
        current_time_supplier=clock,
        max_age_hours=24,
    )


NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


def test_a_repeated_article_stops_being_a_trigger():
    clock = _Clock(NOW)
    xml = _feed([('Nvidia to acquire Hugging Face for $13B',
                  'acquisition news', 'https://example.test/a1')], NOW)
    provider = _provider(xml, clock)

    first = provider.fetch('NVDAUSDT')
    assert len(first) == 1
    assert first[0]['repeat'] is False
    first_score = first[0]['score']

    # 同一篇文章，下一轮轮询
    clock.advance(minutes=3)
    second = provider.fetch('NVDAUSDT')
    assert len(second) == 1, '不该丢弃——它仍是给模型的上下文'
    assert second[0]['repeat'] is True
    assert second[0]['score'] < first_score, '重复条目的分数必须被压下来'
    # 压到触发线以下：newsTrigger.scoreThreshold 0.80，worker 侧
    # ruleOnlyScoreThreshold 0.70，两道都要过不去
    assert second[0]['score'] <= 0.65


def test_url_is_carried_so_downstream_can_dedupe():
    """url 此前完全没进 payload，实测 event_raw 里 url 的不同取值数是 0。"""
    clock = _Clock(NOW)
    xml = _feed([('Micron guidance raised', 'earnings', 'https://example.test/m1')], NOW)
    rows = _provider(xml, clock).fetch('MUUSDT')
    assert rows[0]['url'] == 'https://example.test/m1'


def test_distinct_articles_each_get_their_own_trigger():
    clock = _Clock(NOW)
    xml = _feed([
        ('Micron guidance raised', 'earnings beat', 'https://example.test/m1'),
        ('Micron announces capacity cut', 'production cut', 'https://example.test/m2'),
    ], NOW)
    rows = _provider(xml, clock).fetch('MUUSDT')
    assert len(rows) == 2
    assert all(r['repeat'] is False for r in rows), '不同文章不能被互相去重掉'


def test_the_same_article_still_triggers_for_a_different_symbol():
    """一条同时提到多个标的的报道，对每个标的各算一次首次出现。"""
    clock = _Clock(NOW)
    xml = _feed([('Nvidia and Micron both rally on AI demand',
                  'chip demand', 'https://example.test/x1')], NOW)
    provider = _provider(xml, clock)
    assert provider.fetch('NVDAUSDT')[0]['repeat'] is False
    assert provider.fetch('MUUSDT')[0]['repeat'] is False
    assert provider.fetch('NVDAUSDT')[0]['repeat'] is True


def test_seen_entries_expire_so_memory_does_not_grow_forever():
    clock = _Clock(NOW)
    xml = _feed([('Micron old story', 'x', 'https://example.test/o1')], NOW)
    provider = _provider(xml, clock)
    provider.fetch('MUUSDT')
    assert len(provider._emitted) == 1
    # 超过 max_age_hours 之后记录应被清掉
    clock.advance(hours=25)
    provider._mark_emitted('SOLUSDT', 'https://example.test/other', clock.now)
    assert ('MUUSDT', 'https://example.test/o1') not in provider._emitted


def test_items_without_identity_are_never_merged_together():
    """标识为空时宁可重复发，也不要把所有无标识条目当成同一条合并掉。"""
    clock = _Clock(NOW)
    provider = _provider(_feed([], NOW), clock)
    assert provider._mark_emitted('MUUSDT', '', clock.now) is False
    assert provider._mark_emitted('MUUSDT', '', clock.now) is False
