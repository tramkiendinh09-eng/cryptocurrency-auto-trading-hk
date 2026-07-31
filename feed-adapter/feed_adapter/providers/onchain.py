from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import logging
import re
from typing import Callable
from urllib.parse import urlparse

import requests

from feed_adapter.models import UpstreamUnavailableError


logger = logging.getLogger(__name__)

_AMOUNT_PATTERN = re.compile(r"^\$(?P<value>[\d,]+(?:\.\d+)?)\s*(?P<unit>[KMBT]?)$", re.IGNORECASE)
_TIME_PATTERN = re.compile(r"^\d{1,2}:\d{2}$")
_SYMBOL_SUFFIXES = ("USDT", "USDC", "USD")
_AMOUNT_MULTIPLIERS = {
    "": 1.0,
    "K": 1_000.0,
    "M": 1_000_000.0,
    "B": 1_000_000_000.0,
    "T": 1_000_000_000_000.0,
}


def _default_fetch_text(url: str, timeout: int, user_agent: str) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
    response.raise_for_status()
    return response.text


def _base_asset_from_symbol(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper().replace("/", "").replace("-", "")
    for suffix in _SYMBOL_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _parse_amount_usd(value: str) -> float | None:
    match = _AMOUNT_PATTERN.match(str(value or "").strip())
    if not match:
        return None
    numeric = float(match.group("value").replace(",", ""))
    unit = match.group("unit").upper()
    return round(numeric * _AMOUNT_MULTIPLIERS.get(unit, 1.0), 4)


def _normalize_flow(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if "exchange outflow" in normalized:
        return "exchange_outflow"
    if "exchange inflow" in normalized:
        return "exchange_inflow"
    return ""


def _normalize_impact(value: str) -> str:
    normalized = str(value or "").strip().lower()
    for token in ("critical", "high", "medium", "low"):
        if token in normalized:
            return token
    return ""


def _resolve_event_time_from_token(value: str, current_time: datetime) -> str:
    normalized = str(value or "").strip()
    if not _TIME_PATTERN.match(normalized):
        return current_time.isoformat().replace("+00:00", "Z")
    hour_text, minute_text = normalized.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    best_candidate: datetime | None = None
    best_age_seconds: float | None = None
    for offset_hours in range(-12, 15):
        candidate_tz = timezone(timedelta(hours=offset_hours))
        local_now = current_time.astimezone(candidate_tz)
        candidate = datetime(
            local_now.year,
            local_now.month,
            local_now.day,
            hour,
            minute,
            tzinfo=candidate_tz,
        ).astimezone(timezone.utc)
        if candidate > current_time:
            candidate -= timedelta(days=1)
        age_seconds = (current_time - candidate).total_seconds()
        if age_seconds < 0:
            continue
        if best_age_seconds is None or age_seconds < best_age_seconds:
            best_candidate = candidate
            best_age_seconds = age_seconds
    if best_candidate is None:
        best_candidate = current_time
    return best_candidate.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_event_time(value: str) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class _TextNodeExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []

    def handle_data(self, data: str) -> None:
        normalized = str(data or "").strip()
        if normalized:
            self.items.append(normalized)


class OnchainFlowsProvider:
    def __init__(
        self,
        *,
        page_urls: list[str],
        fetch_text: Callable[..., str] | None = None,
        current_time_supplier: Callable[[], datetime] | None = None,
        timeout: int = 8,
        user_agent: str = "web4-first-feed-adapter/1.0",
        max_age_minutes: int = 30,
    ) -> None:
        self.page_urls = list(page_urls)
        self.fetch_text = fetch_text or _default_fetch_text
        self.current_time_supplier = current_time_supplier or (lambda: datetime.now(timezone.utc))
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_age_minutes = max(0, int(max_age_minutes or 0))

    def fetch(self, symbol: str) -> list[dict]:
        items: list[dict] = []
        failures = 0
        for url in self.page_urls:
            logger.info(
                "feed_adapter_upstream_request provider=onchain symbol=%s url=%s timeout=%s",
                symbol or "-",
                url,
                self.timeout,
            )
            try:
                html_payload = self.fetch_text(url, self.timeout, self.user_agent)
            except TypeError:
                html_payload = self.fetch_text(url, self.timeout)
            except Exception as exc:
                failures += 1
                logger.warning(
                    "feed_adapter_upstream_error provider=onchain symbol=%s url=%s error=%s",
                    symbol or "-",
                    url,
                    exc,
                )
                continue
            items.extend(self._parse_items(symbol, url, html_payload))
        if failures == len(self.page_urls) and self.page_urls:
            raise UpstreamUnavailableError("onchain_upstream_unavailable")
        return items

    def _extract_text_nodes(self, html_payload: str) -> list[str]:
        parser = _TextNodeExtractor()
        parser.feed(html_payload)
        parser.close()
        return parser.items

    def _parse_items(self, symbol: str, url: str, html_payload: str) -> list[dict]:
        text_nodes = self._extract_text_nodes(html_payload)
        source_name = urlparse(url).netloc or "onchain"
        symbol_asset = _base_asset_from_symbol(symbol)
        current_time = self.current_time_supplier().astimezone(timezone.utc).replace(microsecond=0)
        resolved: list[dict] = []
        raw_candidates = 0
        symbol_filtered = 0
        flow_filtered = 0

        for index, token in enumerate(text_nodes):
            flow = _normalize_flow(token)
            if not flow:
                continue
            raw_candidates += 1
            route_index = next(
                (cursor for cursor in range(index - 1, max(-1, index - 4), -1) if "->" in text_nodes[cursor]),
                None,
            )
            amount_index = next(
                (
                    cursor
                    for cursor in range((route_index or index) - 1, max(-1, index - 6), -1)
                    if _parse_amount_usd(text_nodes[cursor]) is not None
                ),
                None,
            )
            asset_index = next(
                (
                    cursor
                    for cursor in range((amount_index or index) - 1, max(-1, index - 7), -1)
                    if text_nodes[cursor].strip().upper().isalpha() and 2 <= len(text_nodes[cursor].strip()) <= 10
                ),
                None,
            )
            time_index = next(
                (
                    cursor
                    for cursor in range((asset_index or index) + 1, min(len(text_nodes), (amount_index or index) + 1))
                    if _TIME_PATTERN.match(text_nodes[cursor].strip())
                ),
                None,
            )
            if route_index is None or amount_index is None or asset_index is None:
                flow_filtered += 1
                continue
            asset = text_nodes[asset_index].strip().upper()
            if asset != symbol_asset:
                symbol_filtered += 1
                continue
            amount_usd = _parse_amount_usd(text_nodes[amount_index])
            if amount_usd is None:
                flow_filtered += 1
                continue
            route = " ".join(text_nodes[route_index].split())
            summary_parts = [part.strip() for part in text_nodes[route_index + 1 : index] if part.strip() and not _TIME_PATTERN.match(part.strip())]
            summary = " ".join(summary_parts).strip()
            item = {
                "symbol": symbol,
                "asset": asset,
                "wallet": route,
                "route": route,
                "flow": flow,
                "amountUsd": amount_usd,
                "source": source_name,
                "event_time": _resolve_event_time_from_token(
                    text_nodes[time_index] if time_index is not None else "",
                    current_time,
                ),
            }
            impact = _normalize_impact(token)
            if impact:
                item["impact"] = impact
            if summary:
                item["summary"] = summary
            event_time = _parse_event_time(str(item.get("event_time") or ""))
            if self.max_age_minutes > 0 and event_time is not None:
                if (current_time - event_time).total_seconds() > self.max_age_minutes * 60:
                    continue
            resolved.append(item)

        logger.info(
            "feed_adapter_upstream_result provider=onchain symbol=%s url=%s source=%s raw_candidates=%s symbol_filtered=%s flow_filtered=%s returned_items=%s current_time_utc=%s",
            symbol or "-",
            url,
            source_name,
            raw_candidates,
            symbol_filtered,
            flow_filtered,
            len(resolved),
            current_time.isoformat().replace("+00:00", "Z"),
        )
        return resolved


class EmptyOnchainProvider:
    def fetch(self, symbol: str):
        logger.info(
            "feed_adapter_upstream_result provider=onchain symbol=%s returned_items=0 mode=empty_provider",
            str(symbol or "").strip().upper() or "-",
        )
        return []
