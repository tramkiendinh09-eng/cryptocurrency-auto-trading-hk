from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
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


class InMemoryActiveSignalStore:
    def __init__(self):
        self._signals: dict[str, dict[str, Any]] = {}

    def _build_storage_key(self, signal_window_state: dict[str, Any]) -> str:
        window_key = str(signal_window_state.get("window_key") or signal_window_state.get("windowKey") or "").strip()
        if window_key:
            return window_key
        source_type = str(signal_window_state.get("source_type") or "unknown").strip().lower()
        symbol = str(signal_window_state.get("symbol") or "").strip()
        direction = str(signal_window_state.get("direction") or "neutral").strip().lower()
        dedupe_key = str(
            signal_window_state.get("dedupe_key")
            or signal_window_state.get("dedupeKey")
            or signal_window_state.get("window_key")
            or signal_window_state.get("windowKey")
            or f"{source_type}:{symbol}:{direction}"
        ).strip()
        return "|".join([source_type, symbol, direction, dedupe_key])

    def _is_expired(self, signal_window_state: dict[str, Any], now_dt: datetime) -> bool:
        expires_at = _parse_datetime(signal_window_state.get("expires_at") or signal_window_state.get("expiresAt"))
        if expires_at is not None and expires_at < now_dt:
            return True
        active = signal_window_state.get("active")
        if active is False or str(active).strip() == "0":
            return True
        return False

    def purge_expired(self, *, now: Any = None) -> None:
        now_dt = _parse_datetime(now) or datetime.now(timezone.utc)
        expired_keys = [key for key, value in self._signals.items() if self._is_expired(value, now_dt)]
        for key in expired_keys:
            self._signals.pop(key, None)

    def upsert(self, signal_window_state: dict[str, Any], *, now: Any = None) -> dict[str, Any]:
        now_dt = _parse_datetime(now) or datetime.now(timezone.utc)
        normalized = dict(signal_window_state)
        storage_key = self._build_storage_key(normalized)
        existing = self._signals.get(storage_key)
        if existing is not None and existing.get("opened_at") and not normalized.get("opened_at"):
            normalized["opened_at"] = existing["opened_at"]
        self._signals[storage_key] = normalized
        self.purge_expired(now=now_dt)
        return normalized

    def upsert_many(self, signal_window_states: list[dict[str, Any]], *, now: Any = None) -> list[dict[str, Any]]:
        return [self.upsert(item, now=now) for item in signal_window_states if isinstance(item, dict)]

    def snapshot(self, *, symbol: str | None = None, now: Any = None) -> list[dict[str, Any]]:
        now_dt = _parse_datetime(now) or datetime.now(timezone.utc)
        self.purge_expired(now=now_dt)
        payload = list(self._signals.values())
        if symbol:
            payload = [item for item in payload if str(item.get("symbol") or "").strip() == symbol]
        return [dict(item) for item in payload]
