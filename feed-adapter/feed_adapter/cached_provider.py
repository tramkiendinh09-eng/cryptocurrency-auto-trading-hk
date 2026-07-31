from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Callable


logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    fetched_at: datetime
    items: list[dict[str, Any]]


class MinRefreshCachedProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        provider: Any,
        min_refresh_seconds: int,
        current_time_supplier: Callable[[], datetime] | None = None,
    ) -> None:
        self.provider_name = str(provider_name or "").strip() or "unknown"
        self.provider = provider
        self.min_refresh_seconds = max(int(min_refresh_seconds or 0), 0)
        self.current_time_supplier = current_time_supplier or (lambda: datetime.now(timezone.utc))
        self._cache_by_symbol: dict[str, _CacheEntry] = {}

    def fetch(self, symbol: str) -> list[dict[str, Any]]:
        normalized_symbol = str(symbol or "").strip().upper()
        now = self.current_time_supplier().astimezone(timezone.utc)
        cache_entry = self._cache_by_symbol.get(normalized_symbol)
        if cache_entry is not None and self.min_refresh_seconds > 0:
            age_seconds = max((now - cache_entry.fetched_at).total_seconds(), 0.0)
            if age_seconds < self.min_refresh_seconds:
                logger.info(
                    "feed_adapter_cache provider=%s symbol=%s cache_status=hit age_seconds=%.2f min_refresh_seconds=%s items=%s",
                    self.provider_name,
                    normalized_symbol or "-",
                    age_seconds,
                    self.min_refresh_seconds,
                    len(cache_entry.items),
                )
                return list(cache_entry.items)

        items = list(self.provider.fetch(normalized_symbol))
        self._cache_by_symbol[normalized_symbol] = _CacheEntry(
            fetched_at=now,
            items=list(items),
        )
        logger.info(
            "feed_adapter_cache provider=%s symbol=%s cache_status=refresh min_refresh_seconds=%s items=%s",
            self.provider_name,
            normalized_symbol or "-",
            self.min_refresh_seconds,
            len(items),
        )
        return items
