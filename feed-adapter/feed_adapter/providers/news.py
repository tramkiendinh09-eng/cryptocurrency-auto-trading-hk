from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import logging
from typing import Callable
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests

from feed_adapter.models import UpstreamUnavailableError
from feed_adapter.symbols import matches_symbol

logger = logging.getLogger(__name__)


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
    ):
        self.feed_urls = list(feed_urls)
        self.fetch_text = fetch_text or _default_fetch_text
        self.current_time_supplier = current_time_supplier or (lambda: datetime.now(timezone.utc))
        self.timeout = timeout
        self.max_age_hours = max(int(max_age_hours or 0), 0)
        self.user_agent = user_agent

    def fetch(self, symbol: str) -> list[dict]:
        items: list[dict] = []
        failures = 0
        for url in self.feed_urls:
            logger.info(
                "feed_adapter_upstream_request provider=news symbol=%s url=%s timeout=%s",
                symbol or "-",
                url,
                self.timeout,
            )
            try:
                xml_payload = self.fetch_text(url, self.timeout, self.user_agent)
            except TypeError:
                xml_payload = self.fetch_text(url, self.timeout)
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
        latest_event_time = ""
        oldest_event_time = ""
        current_time_utc = self.current_time_supplier().astimezone(timezone.utc).replace(microsecond=0)
        for item in root.findall(".//item"):
            total_items += 1
            title = (item.findtext("title") or "").strip()
            summary = (item.findtext("description") or "").strip()
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
            resolved.append(
                {
                    "symbol": symbol,
                    "headline": title,
                    "summary": summary,
                    "score": self._score_item(title, summary, event_time),
                    "source": source_name,
                    "event_time": event_time,
                }
            )
        logger.info(
            "feed_adapter_upstream_result provider=news symbol=%s url=%s source=%s total_items=%s symbol_filtered=%s stale_filtered=%s returned_items=%s max_age_hours=%s current_time_utc=%s latest_event_time=%s oldest_event_time=%s",
            symbol or "-",
            url,
            source_name,
            total_items,
            symbol_filtered,
            stale_filtered,
            len(resolved),
            self.max_age_hours,
            current_time_utc.isoformat().replace("+00:00", "Z"),
            latest_event_time or "-",
            oldest_event_time or "-",
        )
        return resolved

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
        if any(word in text for word in ("etf", "sec", "liquidation", "hack", "exploit", "inflow", "outflow", "fomc", "cpi")):
            score += 0.2
        if event_time:
            try:
                published_at = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            except ValueError:
                published_at = None
            if published_at is not None and published_at >= self.current_time_supplier() - timedelta(hours=8):
                score += 0.1
        return round(min(score, 0.95), 2)
