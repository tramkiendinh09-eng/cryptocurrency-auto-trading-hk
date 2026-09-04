from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import xml.etree.ElementTree as ET
from math import log1p
from typing import Any, Callable

import requests

from feed_adapter.models import UpstreamUnavailableError
from feed_adapter.symbols import matches_symbol

logger = logging.getLogger(__name__)


def _default_fetch_json(url: str, timeout: int, user_agent: str) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("social_payload_not_dict")
    return payload


class RedditSocialProvider:
    def __init__(
        self,
        *,
        listing_urls: list[str],
        fetch_json: Callable[..., dict[str, Any]] | None = None,
        timeout: int = 8,
        user_agent: str = "web4-first-feed-adapter/1.0",
    ):
        self.listing_urls = list(listing_urls)
        self.fetch_json = fetch_json or _default_fetch_json
        self.timeout = timeout
        self.user_agent = user_agent

    def fetch(self, symbol: str) -> list[dict]:
        items: list[dict] = []
        failures = 0
        for url in self.listing_urls:
            logger.info(
                "feed_adapter_upstream_request provider=social symbol=%s url=%s timeout=%s",
                symbol or "-",
                url,
                self.timeout,
            )
            try:
                payload = self.fetch_json(url, self.timeout, self.user_agent)
            except TypeError:
                payload = self.fetch_json(url, self.timeout)
            except Exception as exc:
                failures += 1
                logger.warning(
                    "feed_adapter_upstream_error provider=social symbol=%s url=%s error=%s",
                    symbol or "-",
                    url,
                    exc,
                )
                continue
            items.extend(self._parse_items(symbol, url, payload))
        if failures == len(self.listing_urls) and self.listing_urls:
            raise UpstreamUnavailableError("social_upstream_unavailable")
        return items

    def _parse_items(self, symbol: str, url: str, payload: dict[str, Any]) -> list[dict]:
        children = payload.get("data", {}).get("children", [])
        if not isinstance(children, list):
            logger.info(
                "feed_adapter_upstream_result provider=social symbol=%s url=%s total_items=0 symbol_filtered=0 returned_items=0",
                symbol or "-",
                url,
            )
            return []
        resolved: list[dict] = []
        total_items = 0
        symbol_filtered = 0
        for child in children:
            total_items += 1
            if not isinstance(child, dict):
                continue
            data = child.get("data") or {}
            if not isinstance(data, dict):
                continue
            title = str(data.get("title") or "").strip()
            body = str(data.get("selftext") or "").strip()
            if not matches_symbol(symbol, title, body):
                symbol_filtered += 1
                continue
            subreddit = str(data.get("subreddit") or "").strip() or "unknown"
            created_utc = data.get("created_utc")
            resolved.append(
                {
                    "symbol": symbol,
                    "headline": title,
                    "score": self._normalize_score(data.get("score"), data.get("num_comments")),
                    "author": str(data.get("author") or "").strip(),
                    "source": f"reddit:r/{subreddit}",
                    "event_time": self._to_iso8601(created_utc),
                }
            )
        logger.info(
            "feed_adapter_upstream_result provider=social symbol=%s url=%s total_items=%s symbol_filtered=%s returned_items=%s",
            symbol or "-",
            url,
            total_items,
            symbol_filtered,
            len(resolved),
        )
        return resolved

    def _normalize_score(self, score: Any, comments: Any) -> float:
        try:
            score_value = float(score or 0)
        except (TypeError, ValueError):
            score_value = 0.0
        try:
            comment_value = float(comments or 0)
        except (TypeError, ValueError):
            comment_value = 0.0
        normalized = 0.55 + min(log1p(score_value + comment_value) / 10.0, 0.4)
        return round(min(normalized, 0.95), 2)

    def _to_iso8601(self, value: Any) -> str:
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            return ""
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RedditRssSocialProvider:
    """Reddit 社区帖子，走 RSS。

    这个源从上线起就没拿到过数据，一直被当成"Reddit 封了机房 IP"。实测不是：
    ``/new.json`` 返回 403，而 ``/new/.rss`` **直连就返回 200**。坏的原因是
    用错了端点，跟出口 IP 无关，也不需要代理。

    **刻意不产出方向，因此不会触发决策。** trigger_policy 里 social 信号要求
    ``social_direction != "neutral"`` 才会 fire，而 RSS 没有赞数与评论数
    （``.json`` 才有），要产出方向就只能手搓褒贬词表——那是凭空造一个没人
    验证过的信号，而社交数据没有历史归档，没法像 ready/watch 那样用回测证伪。

    所以这里只做上下文：把真实帖子标题交给模型自己读。模型判断标题情感比任何
    关键词表都强，而且这条路径不消耗 LLM 预算——今天刚量过，这套系统的瓶颈
    不是触发信号太少，是 watch 级信号吃掉了 92% 的预算，把唯一被证明有优势的
    ready 挤了出去。再塞一个未经验证的方向源进去是重复同一个错误。
    """

    #: 明确写死为中性。改这个值等于让这个源开始产生触发信号，
    #: 那需要先有办法验证它的方向性，而不是调一个常量。
    _CONTEXT_ONLY_SCORE = 0.0

    def __init__(
        self,
        *,
        listing_urls: list[str],
        fetch_text: Callable[..., str] | None = None,
        current_time_supplier: Callable[[], datetime] | None = None,
        timeout: int = 8,
        user_agent: str = "web4-first-feed-adapter/1.0",
        max_age_hours: int = 24,
        document_cache_seconds: int = 0,
    ):
        self.listing_urls = list(listing_urls)
        self.fetch_text = fetch_text or _default_fetch_rss_text
        self.current_time_supplier = current_time_supplier or (lambda: datetime.now(timezone.utc))
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_age_hours = max(int(max_age_hours or 0), 0)
        # 同一篇 RSS 在这个窗口内只抓一次，所有标的共用。
        #
        # 不加这层会直接被 Reddit 限流：12 个标的 x 4 个子版 = 一轮 48 次请求，
        # 实测第二个标的就开始 429。新闻源上是同一套做法（document_cache_seconds），
        # 目的一样——让上游请求量与标的数量脱钩。
        self.document_cache_seconds = max(int(document_cache_seconds or 0), 0)
        self._documents: dict[str, tuple] = {}
        # (标的, 条目 id) -> 首次发出时间。理由同新闻源：RSS 每轮返回同一批
        # 条目，不去重的话同一个帖子会被反复当成新事件。
        self._emitted: dict[tuple[str, str], datetime] = {}

    def fetch(self, symbol: str) -> list[dict]:
        items: list[dict] = []
        failures = 0
        for url in self.listing_urls:
            logger.info(
                "feed_adapter_upstream_request provider=social symbol=%s url=%s timeout=%s",
                symbol or "-", url, self.timeout,
            )
            try:
                payload = self._fetch_document(url)
            except Exception as exc:
                failures += 1
                logger.warning(
                    "feed_adapter_upstream_error provider=social symbol=%s url=%s error=%s",
                    symbol or "-", url, exc,
                )
                continue
            items.extend(self._parse_entries(symbol, url, payload))
        if failures == len(self.listing_urls) and self.listing_urls:
            raise UpstreamUnavailableError("social_upstream_unavailable")
        return items

    def _fetch_document(self, url: str) -> str:
        """取一篇 RSS 原文，命中缓存则不走网络。"""
        now = self.current_time_supplier().astimezone(timezone.utc)
        cached = self._documents.get(url)
        if cached is not None and self.document_cache_seconds > 0:
            fetched_at, payload = cached
            age = (now - fetched_at).total_seconds()
            if age < self.document_cache_seconds:
                logger.debug(
                    "feed_adapter_document_cache provider=social url=%s cache_status=hit age_seconds=%.2f",
                    url, age,
                )
                return payload
        try:
            try:
                payload = self.fetch_text(url, self.timeout, self.user_agent)
            except TypeError:
                payload = self.fetch_text(url, self.timeout)
        except Exception:
            # 失败也要记进缓存，否则一次 429 会让 12 个标的把这个子版各重试
            # 一遍，正好把限流坐实。用一段空文档占位：解析出 0 条，且在窗口内
            # 不再打上游。
            self._documents[url] = (now, "")
            raise
        self._documents[url] = (now, payload)
        return payload

    def _parse_entries(self, symbol: str, url: str, xml_payload: str) -> list[dict]:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(xml_payload)
        except ET.ParseError as exc:
            logger.warning(
                "feed_adapter_upstream_error provider=social symbol=%s url=%s error=parse:%s",
                symbol or "-", url, exc,
            )
            return []
        now = self.current_time_supplier().astimezone(timezone.utc)
        resolved: list[dict] = []
        total = 0
        symbol_filtered = 0
        repeat_filtered = 0
        for entry in root.findall("a:entry", ns):
            total += 1
            title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
            body = (entry.findtext("a:content", default="", namespaces=ns) or "").strip()
            if not matches_symbol(symbol, title, body):
                symbol_filtered += 1
                continue
            entry_id = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
            link_el = entry.find("a:link", ns)
            link = (link_el.get("href") if link_el is not None else "") or ""
            identity = entry_id or link or title
            if self._already_emitted(symbol, identity, now):
                repeat_filtered += 1
                continue
            author = (entry.findtext("a:author/a:name", default="", namespaces=ns) or "").strip()
            published = (entry.findtext("a:published", default="", namespaces=ns) or "").strip()
            resolved.append(
                {
                    "symbol": str(symbol or "").strip().upper(),
                    "headline": title,
                    "url": link,
                    # 恒为 0：见类文档，这个源刻意不产生触发信号
                    "score": self._CONTEXT_ONLY_SCORE,
                    "author": author,
                    "source": "reddit_rss",
                    "event_time": published or now.isoformat().replace("+00:00", "Z"),
                }
            )
        logger.info(
            "feed_adapter_upstream_result provider=social symbol=%s url=%s total_items=%s symbol_filtered=%s repeat_filtered=%s returned_items=%s",
            symbol or "-", url, total, symbol_filtered, repeat_filtered, len(resolved),
        )
        return resolved

    def _already_emitted(self, symbol: str, identity: str, now: datetime) -> bool:
        if not identity:
            # 无标识时宁可重复发，也不要把所有无标识条目合并成同一条
            return False
        key = (str(symbol or "").strip().upper(), identity)
        ttl = timedelta(hours=self.max_age_hours or 24)
        if self._emitted:
            for expired in [k for k, seen in self._emitted.items() if now - seen > ttl]:
                self._emitted.pop(expired, None)
        if key in self._emitted:
            return True
        self._emitted[key] = now
        return False


def _default_fetch_rss_text(url: str, timeout: int, user_agent: str) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
    response.raise_for_status()
    return response.text
