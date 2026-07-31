from __future__ import annotations

from datetime import datetime, timezone
import logging
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
