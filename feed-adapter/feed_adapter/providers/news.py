from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import logging
import re
from typing import Callable
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests

from feed_adapter.models import UpstreamUnavailableError
from feed_adapter.symbols import matches_symbol

logger = logging.getLogger(__name__)


# 命中其一给 +0.2。这一步是有实际后果的：newsTrigger.scoreThreshold 是
# 0.80，而基础分 0.65 + 新鲜度 0.10 只有 0.75 —— 不命中任何一个词的新闻
# 永远过不了触发线。原表全是加密与宏观口径，半导体标的结构上无法达标。
_EVENT_KEYWORDS = (
    # 加密 / 宏观（原有）
    "etf", "sec", "liquidation", "hack", "exploit", "inflow", "outflow", "fomc", "cpi",
    # 股票口径的事件词。只收"能让价格跳"的，不收 chip / memory 这类行业泛称——
    # 后者几乎出现在每一篇报道里，加进来等于把这道阈值取消掉。
    "earnings", "guidance", "forecast", "outlook", "downgrade", "upgrade",
    "export control", "sanction", "tariff", "recall", "lawsuit", "antitrust",
    "shortage", "capacity cut", "production cut", "supply deal", "acquisition",
)

# 超过这个时长的条目仍然返回（作为给模型的背景），但分数封顶在触发线
# 以下，不再充当触发器。
_FRESH_WINDOW_HOURS = 8

# 已经发过的条目同样封顶——一篇文章只该触发一次。
#
# RSS 里一条新闻会挂 max_age_hours（默认 24 小时），而适配器每 180 秒轮询
# 一次，于是同一篇报道被当成新事件重复发出最多约 480 次。实测 NVDAUSDT
# 近 6 小时 888 条新闻事件里只有 188 个不同标题，最重复的一条发了 31 次。
# 后果不是"多几条噪声"：news 触发器按分数判定，同一条信息会把触发和 LLM
# 预算反复消耗掉，而模型每次看到的是同一件事。
#
# 处理方式沿用过期条目那一套：不丢弃，仍然返回给模型当上下文，只是把分数
# 压到触发线以下。丢弃会让"最近有哪些新闻"这个上下文凭空缺一块。
# 封到基础分：worker 侧还有一道 ruleOnlyScoreThreshold（默认 0.7）会把
# 0.7~0.8 之间的分数判成 RULE_ONLY，那同样是一次触发。取 0.65 让过期条目
# 落在两道门槛之下，真正只作为上下文存在。
_STALE_SCORE_CAP = 0.65


def _item_identity(link: str, guid: str, title: str) -> str:
    """一条新闻的稳定标识。

    优先 guid（RSS 规范里就是干这个的），其次 link，最后退回标题。Google News
    的 guid 与 link 都带跳转参数，但同一篇文章在多轮轮询里是稳定的，够用。
    """
    for candidate in (guid, link, title):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


@dataclass
class _Document:
    fetched_at: datetime
    payload: str


def _default_fetch_text(url: str, timeout: int, user_agent: str) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
    response.raise_for_status()
    return response.text


class RssNewsProvider:
    def __init__(
        self,
        *,
        feed_urls: list[str],
        fetch_text: Callable[..., str] | None = None,
        current_time_supplier: Callable[[], datetime] | None = None,
        timeout: int = 8,
        max_age_hours: int = 24,
        user_agent: str = "web4-first-feed-adapter/1.0",
        document_cache_seconds: int = 0,
    ):
        self.feed_urls = list(feed_urls)
        self.fetch_text = fetch_text or _default_fetch_text
        self.current_time_supplier = current_time_supplier or (lambda: datetime.now(timezone.utc))
        self.timeout = timeout
        self.max_age_hours = max(int(max_age_hours or 0), 0)
        self.user_agent = user_agent
        # 同一篇 RSS 在这个窗口内只抓一次，所有标的共用
        self.document_cache_seconds = max(int(document_cache_seconds or 0), 0)
        self._documents: dict[str, _Document] = {}
        # (标的, 条目标识) -> 首次发出的时间。按 max_age_hours 过期清理，
        # 免得进程跑久了无限增长。
        self._emitted: dict[tuple[str, str], datetime] = {}

    def _fetch_document(self, url: str) -> str:
        """取一篇 RSS 原文，命中缓存则不走网络。"""
        now = self.current_time_supplier().astimezone(timezone.utc)
        cached = self._documents.get(url)
        if cached is not None and self.document_cache_seconds > 0:
            age = max((now - cached.fetched_at).total_seconds(), 0.0)
            if age < self.document_cache_seconds:
                logger.info(
                    "feed_adapter_document_cache provider=news url=%s cache_status=hit age_seconds=%.2f",
                    url,
                    age,
                )
                return cached.payload
        logger.info(
            "feed_adapter_upstream_request provider=news url=%s timeout=%s",
            url,
            self.timeout,
        )
        try:
            payload = self.fetch_text(url, self.timeout, self.user_agent)
        except TypeError:
            # 老式的两参数 fetch_text（测试里常这么注入）
            payload = self.fetch_text(url, self.timeout)
        if self.document_cache_seconds > 0:
            self._documents[url] = _Document(fetched_at=now, payload=payload)
        return payload

    def fetch(self, symbol: str) -> list[dict]:
        items: list[dict] = []
        failures = 0
        for url in self.feed_urls:
            try:
                xml_payload = self._fetch_document(url)
            except Exception as exc:
                failures += 1
                logger.warning(
                    "feed_adapter_upstream_error provider=news symbol=%s url=%s error=%s",
                    symbol or "-",
                    url,
                    exc,
                )
                continue
            items.extend(self._parse_items(symbol, url, xml_payload))
        if failures == len(self.feed_urls) and self.feed_urls:
            raise UpstreamUnavailableError("news_upstream_unavailable")
        return items

    def _parse_items(self, symbol: str, url: str, xml_payload: str) -> list[dict]:
        root = ET.fromstring(xml_payload)
        source_name = urlparse(url).netloc or "rss"
        resolved: list[dict] = []
        total_items = 0
        symbol_filtered = 0
        stale_filtered = 0
        repeat_capped = 0
        latest_event_time = ""
        oldest_event_time = ""
        current_time_utc = self.current_time_supplier().astimezone(timezone.utc).replace(microsecond=0)
        for item in root.findall(".//item"):
            total_items += 1
            title = (item.findtext("title") or "").strip()
            summary = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or "").strip()
            if not matches_symbol(symbol, title, summary):
                symbol_filtered += 1
                continue
            event_time = self._to_iso8601(item.findtext("pubDate"))
            if event_time:
                if not latest_event_time or event_time > latest_event_time:
                    latest_event_time = event_time
                if not oldest_event_time or event_time < oldest_event_time:
                    oldest_event_time = event_time
            if self._is_stale(event_time):
                stale_filtered += 1
                continue
            identity = _item_identity(link, guid, title)
            already_emitted = self._mark_emitted(symbol, identity, current_time_utc)
            if already_emitted:
                repeat_capped += 1
            score = self._score_item(title, summary, event_time)
            if already_emitted:
                score = min(score, _STALE_SCORE_CAP)
            resolved.append(
                {
                    "symbol": symbol,
                    "headline": title,
                    "summary": summary,
                    # url 此前完全没进 payload，下游想按文章去重都无从下手
                    # （实测 event_raw 里 url 的不同取值数是 0）。
                    "url": link,
                    "score": score,
                    "source": source_name,
                    "event_time": event_time,
                    "repeat": already_emitted,
                }
            )
        logger.info(
            "feed_adapter_upstream_result provider=news symbol=%s url=%s source=%s total_items=%s symbol_filtered=%s stale_filtered=%s repeat_capped=%s returned_items=%s max_age_hours=%s current_time_utc=%s latest_event_time=%s oldest_event_time=%s",
            symbol or "-",
            url,
            source_name,
            total_items,
            symbol_filtered,
            stale_filtered,
            repeat_capped,
            len(resolved),
            self.max_age_hours,
            current_time_utc.isoformat().replace("+00:00", "Z"),
            latest_event_time or "-",
            oldest_event_time or "-",
        )
        return resolved

    def _mark_emitted(self, symbol: str, identity: str, now: datetime) -> bool:
        """记下这条已经发过，并回答"之前发过吗"。

        标识为空时一律当作新条目——宁可重复发，也不要把所有无标识的条目
        当成同一条给合并掉。
        """
        if not identity:
            return False
        key = (str(symbol or "").strip().upper(), identity)
        ttl = timedelta(hours=self.max_age_hours or 24)
        if self._emitted:
            expired = [k for k, seen_at in self._emitted.items() if now - seen_at > ttl]
            for k in expired:
                self._emitted.pop(k, None)
        previous = self._emitted.get(key)
        if previous is not None:
            return True
        self._emitted[key] = now
        return False

    def _to_iso8601(self, value: str | None) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        try:
            parsed = parsedate_to_datetime(normalized)
        except (TypeError, ValueError, IndexError):
            return ""
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _is_stale(self, event_time: str) -> bool:
        if not event_time:
            return False
        try:
            published_at = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        except ValueError:
            return False
        if self.max_age_hours <= 0:
            return False
        return (self.current_time_supplier() - published_at).total_seconds() > (self.max_age_hours * 60 * 60)

    def _score_item(self, title: str, summary: str, event_time: str) -> float:
        score = 0.65
        text = f"{title} {summary}".lower()
        # 必须按词匹配。原来是子串包含，三个字母的 "sec" 会命中
        # second / sector / secretly / cybersecurity —— 实测 255 条里
        # 有 24 条是这样被误抬到触发线以上的。
        if any(re.search(rf"\b{re.escape(word)}\b", text) for word in _EVENT_KEYWORDS):
            score += 0.2

        published_at = None
        if event_time:
            try:
                published_at = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            except ValueError:
                published_at = None

        if published_at is None:
            # 拿不到发布时间就当它不新鲜，宁可漏触发也不要按旧闻开仓
            return round(min(score, _STALE_SCORE_CAP), 2)

        fresh_since = self.current_time_supplier() - timedelta(hours=_FRESH_WINDOW_HOURS)
        if published_at < fresh_since:
            return round(min(score, _STALE_SCORE_CAP), 2)

        score += 0.1
        return round(min(score, 0.95), 2)
