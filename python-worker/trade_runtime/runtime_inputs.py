from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests

from trade_runtime.features.classifier import EventStrengthClassifier
from trade_runtime.features.snapshot_builder import FeatureSnapshotBuilder
from trade_runtime.ingestion.binance_market import BinanceMarketMessageParser
from trade_runtime.ingestion.news_feed import NewsFeedAdapter
from trade_runtime.ingestion.okx_market import OkxMarketMessageParser
from trade_runtime.ingestion.okx_rest import OkxRestMarketClient
from trade_runtime.ingestion.kline_indicators import summarize_kline_context
from trade_runtime.ingestion.onchain_feed import OnchainFeedAdapter
from trade_runtime.ingestion.social_feed import SocialFeedAdapter
from trade_runtime.strategy.wyckoff_shortterm import analyze_wyckoff_shortterm
from trade_runtime.trigger_policy import classify_event_strength_from_policy
from trade_runtime.active_signal_store import InMemoryActiveSignalStore
from trade_runtime.config import parse_object_json as _parse_object_json


logger = logging.getLogger(__name__)

_WINDOW_TTL_SECONDS = {
    "market": 15 * 60,
    "news": 15 * 60,
    "onchain": 30 * 60,
    "social": 10 * 60,
}

_EXTERNAL_EVENT_DEDUPE_TTL_SECONDS = 24 * 60 * 60
_DEFAULT_MARKET_CONTEXT_HISTORY_LIMIT = 60

_DEFAULT_MARKET_DATA_ENHANCEMENT = {
    "enabled": True,
    "restFallbackEnabled": True,
    "klineEnabled": True,
    "klineIntervals": ["1m", "3m", "15m", "1h", "4h"],
    "klineLimit": 120,
    "marketTickStaleAfterSeconds": 90,
    "liquidationAggregateWindowsMinutes": [15, 60, 240],
}


def _market_data_enhancement_config(runtime_config: dict[str, Any] | None) -> dict[str, Any]:
    config = dict(_DEFAULT_MARKET_DATA_ENHANCEMENT)
    if not isinstance(runtime_config, dict):
        return config
    runtime_flags = _parse_object_json(runtime_config.get("runtime_flags") or runtime_config.get("runtimeFlags"))
    runtime_flags_json = _parse_object_json(
        runtime_config.get("runtimeFlagsJson") or runtime_config.get("runtime_flags_json")
    )
    merged_flags = {**runtime_flags_json, **runtime_flags}
    enhancement = _parse_object_json(
        runtime_config.get("marketDataEnhancement")
        or runtime_config.get("market_data_enhancement")
        or merged_flags.get("marketDataEnhancement")
        or merged_flags.get("market_data_enhancement")
    )
    if enhancement:
        config.update(enhancement)
    intervals = config.get("klineIntervals") or config.get("kline_intervals") or []
    if isinstance(intervals, str):
        intervals = [item.strip() for item in intervals.split(",") if item.strip()]
    config["klineIntervals"] = [str(item).strip() for item in intervals if str(item).strip()] or ["1m"]
    try:
        config["klineLimit"] = max(1, int(config.get("klineLimit") or config.get("kline_limit") or 120))
    except (TypeError, ValueError):
        config["klineLimit"] = 120
    return config


def _wyckoff_shortterm_config(
    runtime_config: dict[str, Any] | None,
    strategy_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config: dict[str, Any] = {}
    runtime_payload = runtime_config if isinstance(runtime_config, dict) else {}
    runtime_flags = _parse_object_json(runtime_payload.get("runtime_flags") or runtime_payload.get("runtimeFlags"))
    runtime_flags_json = _parse_object_json(
        runtime_payload.get("runtimeFlagsJson") or runtime_payload.get("runtime_flags_json")
    )
    for payload in (runtime_flags_json, runtime_flags, runtime_payload):
        section = _parse_object_json(payload.get("wyckoffShortterm") or payload.get("wyckoff_shortterm"))
        if section:
            config.update(section)
    strategy_payload = strategy_context if isinstance(strategy_context, dict) else {}
    strategy_config = strategy_payload.get("strategy_config") if isinstance(strategy_payload.get("strategy_config"), dict) else {}
    trigger_policy = strategy_config.get("triggerPolicy") or strategy_config.get("trigger_policy") or {}
    if isinstance(trigger_policy, dict):
        section = _parse_object_json(trigger_policy.get("wyckoffShortterm") or trigger_policy.get("wyckoff_shortterm"))
        if section:
            config.update(section)
    return config


class BinancePublicMarketFeed:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def fetch(self, symbol: str) -> dict[str, Any]:
        response = requests.get(
            "https://fapi.binance.com/fapi/v1/ticker/24hr",
            params={"symbol": symbol},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return {
            "s": payload["symbol"],
            "c": payload["lastPrice"],
            "q": payload.get("quoteVolume") or payload.get("volume", "0"),
        }


class OkxPublicMarketFeed:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def _format_inst_id(self, symbol: str) -> str:
        normalized = symbol.replace("/", "")
        if normalized.endswith("USDT") and len(normalized) > 4:
            return f"{normalized[:-4]}-USDT-SWAP"
        if normalized.endswith("USDC") and len(normalized) > 4:
            return f"{normalized[:-4]}-USDC-SWAP"
        return normalized

    def fetch(self, symbol: str) -> dict[str, Any]:
        response = requests.get(
            "https://www.okx.com/api/v5/market/ticker",
            params={"instId": self._format_inst_id(symbol)},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


class HttpJsonFeedSupplier:
    def __init__(self, url: str | None, timeout: int = 5):
        self.url = url.strip() if isinstance(url, str) and url.strip() else None
        self.timeout = timeout

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("data", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]

    def fetch(self, symbol: str) -> Any:
        if self.url is None:
            return []
        try:
            response = requests.get(
                self.url,
                params={"symbol": symbol},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return {
                "items": [],
                "source_status": "unavailable",
                "error_message": str(exc),
            }
        items = self._extract_items(payload)
        if not items:
            if isinstance(payload, dict) and any(
                key in payload for key in ("sourceStatus", "source_status", "error", "errorMessage", "error_message")
            ):
                return {
                    "items": [],
                    "source_status": str(payload.get("source_status") or payload.get("sourceStatus") or "empty").strip().lower(),
                    "error_message": str(payload.get("error_message") or payload.get("errorMessage") or payload.get("error") or "").strip(),
                }
            return {"items": [], "source_status": "empty"}
        return items


def normalize_event_bundle(event_bundle: Any) -> list[dict[str, Any]]:
    if not isinstance(event_bundle, list):
        return []
    return [item for item in event_bundle if isinstance(item, dict)]


def resolve_market_source_status(event_bundle: Any, default: str = "ready") -> str:
    for event in normalize_event_bundle(event_bundle):
        event_type = str(event.get("event_type", "")).strip().lower()
        if event_type == "stale":
            return "stale"
        if event_type in {"source_abnormal", "market_source_abnormal"}:
            return "abnormal"
        if event_type == "source_health" and str(event.get("source_type", "")).strip().lower() == "market":
            source_status = str(event.get("source_status", "")).strip().lower()
            if source_status in {"stale", "abnormal", "degraded", "unavailable"}:
                return source_status
    return default


def _market_source_status_event(status: str) -> dict[str, Any]:
    normalized_status = str(status or "").strip().lower()
    return {
        "event_type": "stale" if normalized_status == "stale" else "market_source_abnormal",
        "source_status": normalized_status,
    }


def _promote_market_source_status_from_tick_staleness(
    *,
    event_bundle: list[dict[str, Any]],
    current_status: str,
    current_time: datetime,
    runtime_config: dict[str, Any] | None,
    market_tick_staleness_seconds: float = 0.0,
    effective_price_source: str = "",
) -> str:
    normalized_status = str(current_status or "").strip().lower()
    if normalized_status not in {"", "ready", "healthy"}:
        return normalized_status
    resolved_staleness = _safe_float(market_tick_staleness_seconds)
    if resolved_staleness <= 0:
        resolved_staleness = _market_tick_staleness_seconds(
            _latest_market_event(event_bundle, "market_tick"),
            current_time=current_time,
        )
    stale_after_seconds = max(
        1,
        int(_market_data_enhancement_config(runtime_config).get("marketTickStaleAfterSeconds") or 90),
    )
    if resolved_staleness > stale_after_seconds:
        normalized_effective_price_source = str(effective_price_source or "").strip().lower()
        if normalized_effective_price_source == "mark_price":
            mark_price_staleness = _market_event_staleness_seconds(
                _latest_market_event(event_bundle, "mark_price"),
                current_time=current_time,
            )
            if mark_price_staleness is not None and mark_price_staleness <= stale_after_seconds:
                return normalized_status or "ready"
        return "stale"
    return normalized_status or "ready"


def _market_window_key(symbol: str) -> str:
    return f"market:{symbol}:15m"


def _news_window_key(symbol: str) -> str:
    return f"news:{symbol}:15m"


def _onchain_window_key(symbol: str) -> str:
    return f"onchain:{symbol}:15m"


def _social_window_key(symbol: str) -> str:
    return f"social:{symbol}:15m"


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _supplemental_market_events(payload: dict[str, Any], *, exchange: str, symbol: str) -> list[dict[str, Any]]:
    raw_events = payload.get("_market_events")
    if not isinstance(raw_events, list):
        return []
    normalized_events: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        normalized = dict(event)
        normalized.setdefault("symbol", str(symbol or "").strip().upper())
        normalized.setdefault("exchange", exchange)
        normalized_events.append(normalized)
    return normalized_events


def _latest_funding_rate(event_bundle: list[dict[str, Any]]) -> float:
    for event in reversed(event_bundle):
        if str(event.get("event_type") or "").strip().lower() != "funding_rate":
            continue
        value = event.get("funding_rate")
        if value in (None, ""):
            value = event.get("fundingRate")
        return _safe_float(value)
    return 0.0


def _latest_open_interest(event_bundle: list[dict[str, Any]]) -> float:
    for event in reversed(event_bundle):
        if str(event.get("event_type") or "").strip().lower() != "open_interest":
            continue
        value = event.get("open_interest")
        if value in (None, ""):
            value = event.get("openInterest")
        if value in (None, ""):
            value = event.get("oi")
        return _safe_float(value)
    return 0.0


def _latest_mark_price(event_bundle: list[dict[str, Any]]) -> float:
    return _safe_float(_latest_market_event_value(event_bundle, "mark_price", "price", "markPrice", "mark_price"))


def _liquidation_notional_sum(event_bundle: list[dict[str, Any]]) -> float:
    return round(
        sum(
            _safe_float(event.get("notionalUsd") or event.get("notional_usd"))
            for event in event_bundle
            if str(event.get("event_type") or "").strip().lower() == "liquidation"
        ),
        4,
    )


def _largest_liquidation_notional(event_bundle: list[dict[str, Any]]) -> float:
    return max(
        (
            _safe_float(event.get("notionalUsd") or event.get("notional_usd"))
            for event in event_bundle
            if str(event.get("event_type") or "").strip().lower() == "liquidation"
        ),
        default=0.0,
    )


def _latest_market_event_value(event_bundle: list[dict[str, Any]], event_type: str, *keys: str) -> Any:
    normalized_type = str(event_type or "").strip().lower()
    for event in reversed(event_bundle):
        if str(event.get("event_type") or "").strip().lower() != normalized_type:
            continue
        for key in keys:
            value = event.get(key)
            if value not in (None, ""):
                return value
    return None


def _latest_market_event(event_bundle: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    normalized_type = str(event_type or "").strip().lower()
    for event in reversed(event_bundle):
        if str(event.get("event_type") or "").strip().lower() == normalized_type:
            return event
    return {}


def _interval_time_key(candle: dict[str, Any]) -> float:
    raw = candle.get("open_time") or candle.get("event_time") or candle.get("timestamp") or candle.get("ts") or 0
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _latest_kline_close(candles_by_interval: dict[str, list[dict[str, Any]]] | None) -> float:
    if not isinstance(candles_by_interval, dict):
        return 0.0
    for interval in ("15m", "1h", "1m", "3m", "4h"):
        candles = candles_by_interval.get(interval)
        if not isinstance(candles, list) or not candles:
            continue
        ordered = sorted([item for item in candles if isinstance(item, dict)], key=_interval_time_key)
        if ordered:
            return _safe_float(ordered[-1].get("close") or ordered[-1].get("c"))
    return 0.0


def _compact_wyckoff_15m_bars(candles_by_interval: dict[str, list[dict[str, Any]]] | None, required_bars: int = 8) -> dict[str, Any]:
    if not isinstance(candles_by_interval, dict):
        return {}
    candles = candles_by_interval.get("15m")
    if not isinstance(candles, list) or not candles:
        return {}
    ordered = sorted([item for item in candles if isinstance(item, dict)], key=_interval_time_key)
    if not ordered:
        return {}
    required = max(1, int(required_bars or 8))
    selected = ordered[-required:]
    bars: list[dict[str, Any]] = []
    first_selected_index = max(0, len(ordered) - len(selected))
    for offset, candle in enumerate(selected):
        index = first_selected_index + offset
        quote_volume = _safe_float(candle.get("quote_volume") or candle.get("quoteVolume") or candle.get("turnover"))
        previous_volumes = [
            _safe_float(item.get("quote_volume") or item.get("quoteVolume") or item.get("turnover"))
            for item in ordered[max(0, index - 4) : index]
        ]
        positive_previous_volumes = [item for item in previous_volumes if item > 0]
        previous_average = sum(positive_previous_volumes) / len(positive_previous_volumes) if positive_previous_volumes else 0.0
        bars.append(
            {
                "open_time": candle.get("open_time") or candle.get("event_time") or candle.get("timestamp") or candle.get("ts"),
                "open": _safe_float(candle.get("open") or candle.get("o")),
                "high": _safe_float(candle.get("high") or candle.get("h")),
                "low": _safe_float(candle.get("low") or candle.get("l")),
                "close": _safe_float(candle.get("close") or candle.get("c")),
                "quote_volume": quote_volume,
                "volume_ratio": round(quote_volume / previous_average, 4) if previous_average > 0 else 0.0,
            }
        )
    return {
        "interval": "15m",
        "required_15m_bars": required,
        "provided_15m_bars": len(bars),
        "status": "ready" if len(bars) >= required else "insufficient",
        "bars": bars,
    }


def _market_tick_staleness_seconds(market_tick: dict[str, Any], *, current_time: datetime) -> float:
    return _market_event_staleness_seconds(market_tick, current_time=current_time) or 0.0


def _market_event_staleness_seconds(event: dict[str, Any], *, current_time: datetime) -> float | None:
    observed_at = _parse_event_time(
        event.get("event_time") or event.get("ts") or event.get("timestamp")
    )
    if observed_at is None:
        return None
    return round(max(0.0, (current_time - observed_at).total_seconds()), 1)


def _resolve_effective_market_price(
    *,
    event_bundle: list[dict[str, Any]],
    market_payload: dict[str, Any],
    current_time: datetime,
    latest_trade_price: float = 0.0,
    latest_mark_price: float = 0.0,
    latest_kline_close: float = 0.0,
    effective_price: float = 0.0,
    effective_price_source: str = "",
    market_tick_staleness_seconds: float = 0.0,
    stale_after_seconds: int = 90,
) -> dict[str, Any]:
    market_tick = _latest_market_event(event_bundle, "market_tick")
    resolved_latest_trade_price = _safe_float(
        latest_trade_price or market_tick.get("price") or _payload_value(market_payload, "c", "last", "lastPrice", "price")
    )
    resolved_mark_price = _safe_float(
        latest_mark_price or _latest_market_event_value(event_bundle, "mark_price", "price", "markPrice")
    )
    resolved_latest_kline_close = _safe_float(latest_kline_close)
    resolved_staleness = _safe_float(market_tick_staleness_seconds)
    if resolved_staleness <= 0:
        resolved_staleness = _market_tick_staleness_seconds(market_tick, current_time=current_time)
    resolved_effective_price = _safe_float(effective_price)
    resolved_effective_price_source = str(effective_price_source or "").strip()
    if resolved_effective_price <= 0:
        resolved_effective_price = resolved_latest_trade_price
    if not resolved_effective_price_source:
        resolved_effective_price_source = "trade"
    if resolved_latest_trade_price <= 0:
        if resolved_mark_price > 0:
            resolved_effective_price = resolved_mark_price
            resolved_effective_price_source = "mark_price"
        elif resolved_latest_kline_close > 0:
            resolved_effective_price = resolved_latest_kline_close
            resolved_effective_price_source = "kline_close"
    elif resolved_staleness > max(1, int(stale_after_seconds or 90)):
        if resolved_mark_price > 0:
            resolved_effective_price = resolved_mark_price
            resolved_effective_price_source = "mark_price"
        elif resolved_latest_kline_close > 0:
            resolved_effective_price = resolved_latest_kline_close
            resolved_effective_price_source = "kline_close"
    return {
        "latest_trade_price": resolved_latest_trade_price,
        "mark_price": resolved_mark_price,
        "latest_kline_close": resolved_latest_kline_close,
        "effective_price": resolved_effective_price,
        "effective_price_source": resolved_effective_price_source,
        "market_tick_staleness_seconds": resolved_staleness,
    }


def _largest_liquidation_event(event_bundle: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        (
            event
            for event in event_bundle
            if str(event.get("event_type") or "").strip().lower() == "liquidation"
        ),
        key=lambda event: _safe_float(event.get("notionalUsd") or event.get("notional_usd")),
        default={},
    )


def _payload_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    data = payload.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        for key in keys:
            value = data[0].get(key)
            if value not in (None, ""):
                return value
    return None


def _parse_event_time(value: Any) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.isdigit():
        timestamp = int(normalized)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _news_dedupe_key(event: dict[str, Any]) -> str:
    symbol = str(event.get("symbol", "")).strip().upper()
    headline = str(event.get("headline", "")).strip()
    source = str(event.get("source", "")).strip().lower()
    event_time = str(event.get("event_time", "")).strip()
    return "|".join([symbol, headline, source, event_time])


def _external_event_dedupe_key(event: dict[str, Any]) -> str | None:
    event_type = str(event.get("event_type", "")).strip().lower()
    if event_type == "news":
        return "|".join(
            [
                event_type,
                str(event.get("symbol", "")).strip().upper(),
                str(event.get("source", "")).strip().lower(),
                str(event.get("headline", "")).strip(),
                str(event.get("event_time", "")).strip(),
            ]
        )
    if event_type == "onchain":
        return "|".join(
            [
                event_type,
                str(event.get("symbol", "")).strip().upper(),
                str(event.get("source", "")).strip().lower(),
                str(event.get("wallet", "")).strip(),
                str(event.get("flow", "")).strip().lower(),
                str(event.get("event_time", "")).strip(),
                str(event.get("amountUsd", "")).strip(),
            ]
        )
    if event_type == "social":
        return "|".join(
            [
                event_type,
                str(event.get("symbol", "")).strip().upper(),
                str(event.get("source", "")).strip().lower(),
                str(event.get("author", "")).strip(),
                str(event.get("headline", "")).strip(),
                str(event.get("event_time", "")).strip(),
                str(event.get("score", "")).strip(),
            ]
        )
    return None


def _window_ttl_seconds(window_type: str) -> int:
    return _WINDOW_TTL_SECONDS.get(str(window_type or "").strip().lower(), 15 * 60)


def _prune_accumulator_entries(accumulator: dict[str, Any], now_dt: datetime) -> list[dict[str, Any]]:
    ttl_seconds = _window_ttl_seconds(str(accumulator.get("type") or ""))
    threshold = now_dt - timedelta(seconds=ttl_seconds)
    entries = accumulator.setdefault("entries", [])
    retained = [
        entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("observed_at"), datetime) and entry["observed_at"] >= threshold
    ]
    accumulator["entries"] = retained
    return retained


def _rebuild_accumulator(accumulator: dict[str, Any]) -> None:
    window_type = str(accumulator.get("type") or "").strip().lower()
    entries = [entry for entry in accumulator.get("entries", []) if isinstance(entry, dict)]
    accumulator["count"] = len(entries)
    if window_type == "market":
        first_price = _safe_float(entries[0].get("price")) if entries else 0.0
        last_price = _safe_float(entries[-1].get("price")) if entries else 0.0
        accumulator["first_price"] = first_price if entries else None
        accumulator["last_price"] = last_price if entries else None
    elif window_type == "news":
        accumulator["latest_headline"] = str(entries[-1].get("headline", "") if entries else "")
        accumulator["max_score"] = 0.0
        for entry in entries:
            score = _safe_float(entry.get("score"))
            if abs(score) >= abs(float(accumulator.get("max_score", 0.0) or 0.0)):
                accumulator["max_score"] = score
    elif window_type == "onchain":
        accumulator["latest_flow"] = str(entries[-1].get("flow", "") if entries else "")
        accumulator["flow_bias"] = 0.0
        for entry in entries:
            flow = str(entry.get("flow", "")).strip().lower()
            if flow == "exchange_outflow":
                accumulator["flow_bias"] = 1.0
            elif flow == "exchange_inflow":
                accumulator["flow_bias"] = -1.0
    elif window_type == "social":
        accumulator["max_score"] = 0.0
        for entry in entries:
            score = _safe_float(entry.get("score"))
            if abs(score) >= abs(float(accumulator.get("max_score", 0.0) or 0.0)):
                accumulator["max_score"] = score


def _prune_signal_window_accumulators(accumulators: dict[str, dict[str, Any]], now_dt: datetime) -> None:
    empty_keys: list[str] = []
    for key, accumulator in accumulators.items():
        _prune_accumulator_entries(accumulator, now_dt)
        _rebuild_accumulator(accumulator)
        if int(accumulator.get("count", 0) or 0) <= 0:
            empty_keys.append(key)
    for key in empty_keys:
        accumulators.pop(key, None)


def _update_signal_window_accumulators(
    accumulators: dict[str, dict[str, Any]],
    event_bundle: list[dict[str, Any]],
    *,
    current_time: datetime | None = None,
) -> None:
    now_dt = current_time or datetime.now(timezone.utc)
    for event in event_bundle:
        event_type = str(event.get("event_type", "")).strip().lower()
        symbol = str(event.get("symbol", "")).strip()
        if not symbol:
            continue
        if event_type in {"market_tick", "ticker", "mark_price", "funding_rate", "open_interest", "liquidation"}:
            key = _market_window_key(symbol)
            accumulator = accumulators.setdefault(
                key,
                {"type": "market", "symbol": symbol, "entries": []},
            )
            _prune_accumulator_entries(accumulator, now_dt)
            price = _safe_float(event.get("price"))
            accumulator["entries"].append({"observed_at": now_dt, "price": price})
            _rebuild_accumulator(accumulator)
        elif event_type == "news":
            key = _news_window_key(symbol)
            accumulator = accumulators.setdefault(
                key,
                {"type": "news", "symbol": symbol, "entries": []},
            )
            _prune_accumulator_entries(accumulator, now_dt)
            dedupe_key = _news_dedupe_key(event)
            if dedupe_key and any(entry.get("dedupe_key") == dedupe_key for entry in accumulator.get("entries", [])):
                continue
            score = _safe_float(event.get("score"))
            headline = str(event.get("headline", "")).strip()
            accumulator["entries"].append(
                {
                    "observed_at": now_dt,
                    "dedupe_key": dedupe_key,
                    "headline": headline,
                    "score": score,
                }
            )
            _rebuild_accumulator(accumulator)
        elif event_type == "onchain":
            key = _onchain_window_key(symbol)
            accumulator = accumulators.setdefault(
                key,
                {"type": "onchain", "symbol": symbol, "entries": []},
            )
            _prune_accumulator_entries(accumulator, now_dt)
            flow = str(event.get("flow", "")).strip().lower()
            accumulator["entries"].append({"observed_at": now_dt, "flow": flow})
            _rebuild_accumulator(accumulator)
        elif event_type == "social":
            key = _social_window_key(symbol)
            accumulator = accumulators.setdefault(
                key,
                {"type": "social", "symbol": symbol, "entries": []},
            )
            _prune_accumulator_entries(accumulator, now_dt)
            score = _safe_float(event.get("score"))
            accumulator["entries"].append({"observed_at": now_dt, "score": score})
            _rebuild_accumulator(accumulator)
    _prune_signal_window_accumulators(accumulators, now_dt)


def _signal_window_state_payload(window_key: str, accumulator: dict[str, Any], current_time: datetime | None = None) -> dict[str, Any]:
    now = current_time or datetime.now(timezone.utc)
    window_type = accumulator.get("type")
    symbol = str(accumulator.get("symbol", "") or "")
    direction = "neutral"
    strength_score = 0.0
    signal_type = "signal"
    ttl_seconds = 600
    if window_type == "market":
        first_price = _safe_float(accumulator.get("first_price"))
        last_price = _safe_float(accumulator.get("last_price"))
        price_change_pct = 0.0
        if first_price not in (0.0, None) and last_price:
            price_change_pct = round(((last_price - first_price) / first_price) * 100, 4)
        state = {
            "count": int(accumulator.get("count", 0) or 0),
            "last_price": last_price,
            "price_change_pct": price_change_pct,
        }
        direction = "bullish" if price_change_pct > 0 else "bearish" if price_change_pct < 0 else "neutral"
        strength_score = abs(price_change_pct)
        signal_type = "price_break"
        ttl_seconds = 300
    elif window_type == "news":
        state = {
            "count": int(accumulator.get("count", 0) or 0),
            "latest_headline": str(accumulator.get("latest_headline", "") or ""),
            "max_score": _safe_float(accumulator.get("max_score")),
        }
        direction = "bullish" if state["max_score"] > 0 else "bearish" if state["max_score"] < 0 else "neutral"
        strength_score = abs(state["max_score"])
        signal_type = "headline"
        ttl_seconds = 900
    elif window_type == "onchain":
        state = {
            "count": int(accumulator.get("count", 0) or 0),
            "latest_flow": str(accumulator.get("latest_flow", "") or ""),
            "flow_bias": _safe_float(accumulator.get("flow_bias")),
        }
        direction = "bullish" if state["flow_bias"] > 0 else "bearish" if state["flow_bias"] < 0 else "neutral"
        strength_score = abs(state["flow_bias"])
        signal_type = "flow"
        ttl_seconds = 1800
    else:
        state = {
            "count": int(accumulator.get("count", 0) or 0),
            "max_score": _safe_float(accumulator.get("max_score")),
        }
        direction = "bullish" if state["max_score"] > 0 else "bearish" if state["max_score"] < 0 else "neutral"
        strength_score = abs(state["max_score"])
        signal_type = "sentiment"
        ttl_seconds = 600
    return {
        "symbol": symbol,
        "window_key": window_key,
        "source_type": str(window_type or "").strip(),
        "signal_type": signal_type,
        "direction": direction,
        "strength_score": round(strength_score, 4),
        "decay_score": round(strength_score, 4),
        "opened_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "last_event_at": now.isoformat(),
        "last_confirmed_at": now.isoformat(),
        "dedupe_key": f"{window_type}:{symbol}:{direction}",
        "combine_until_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "active": True,
        "state": state,
    }


def build_signal_window_states_from_events(event_bundle: Any) -> list[dict[str, Any]]:
    normalized_bundle = normalize_event_bundle(event_bundle)
    accumulators: dict[str, dict[str, Any]] = {}
    _update_signal_window_accumulators(accumulators, normalized_bundle)
    return [_signal_window_state_payload(window_key, accumulator) for window_key, accumulator in accumulators.items()]


def build_feature_snapshot_from_events(event_bundle: Any) -> dict[str, Any]:
    normalized_bundle = normalize_event_bundle(event_bundle)
    prices = [
        float(event.get("price"))
        for event in normalized_bundle
        if str(event.get("event_type", "")).strip().lower() in {"market_tick", "ticker", "mark_price", "liquidation"}
        and event.get("price") is not None
    ]
    first_price = prices[0] if prices else 0.0
    last_price = prices[-1] if prices else 0.0
    price_change_pct = 0.0
    if first_price not in (0.0, None) and last_price:
        price_change_pct = round(((last_price - first_price) / first_price) * 100, 4)

    news_score = 0.0
    social_score = 0.0
    onchain_flow_bias = 0.0
    for event in normalized_bundle:
        event_type = str(event.get("event_type", "")).strip().lower()
        if event_type == "news":
            score = float(event.get("score", 0) or 0)
            if abs(score) >= abs(news_score):
                news_score = score
        elif event_type == "social":
            score = float(event.get("score", 0) or 0)
            if abs(score) >= abs(social_score):
                social_score = score
        elif event_type == "onchain":
            flow = str(event.get("flow", "")).strip().lower()
            if flow == "exchange_outflow":
                onchain_flow_bias = 1.0
            elif flow == "exchange_inflow":
                onchain_flow_bias = -1.0

    classifier = EventStrengthClassifier()
    funding_rate = _latest_funding_rate(normalized_bundle)
    liquidation_notional = _largest_liquidation_notional(normalized_bundle)
    return FeatureSnapshotBuilder().build(
        symbol=str(normalized_bundle[0].get("symbol", "")) if normalized_bundle else "",
        price_change_pct=price_change_pct,
        funding_rate=funding_rate,
        oi_change_pct=0.0,
        news_score=news_score,
        social_score=social_score,
        onchain_flow_bias=onchain_flow_bias,
        event_strength=classifier.classify(
            price_change_pct=price_change_pct,
            liquidation_notional=liquidation_notional,
            news_score=news_score,
            social_score=social_score,
            onchain_flow_bias=onchain_flow_bias,
        ),
    )


class RuntimeInputAssembler:
    def __init__(
        self,
        *,
        exchange: str,
        market_payload_supplier: Callable[[str], dict[str, Any]],
        news_items_supplier: Callable[[str], list[dict[str, Any]]] | None = None,
        onchain_items_supplier: Callable[[str], list[dict[str, Any]]] | None = None,
        social_items_supplier: Callable[[str], list[dict[str, Any]]] | None = None,
        feature_snapshot_builder: FeatureSnapshotBuilder | None = None,
        event_strength_classifier: EventStrengthClassifier | None = None,
        stream_publisher: Any | None = None,
        stream_consumer: Any | None = None,
        event_client: Any | None = None,
        active_signal_store: Any | None = None,
        initial_market_context_history: dict[str, list[dict[str, Any]]] | None = None,
        market_context_history_limit: int = _DEFAULT_MARKET_CONTEXT_HISTORY_LIMIT,
        current_time_supplier: Callable[[], datetime] | None = None,
        rest_market_client: Any | None = None,
    ):
        self.exchange = exchange
        self.market_payload_supplier = market_payload_supplier
        self.news_items_supplier = news_items_supplier or (lambda symbol: [])
        self.onchain_items_supplier = onchain_items_supplier or (lambda symbol: [])
        self.social_items_supplier = social_items_supplier or (lambda symbol: [])
        self.news_source_enabled = news_items_supplier is not None
        self.onchain_source_enabled = onchain_items_supplier is not None
        self.social_source_enabled = social_items_supplier is not None
        self.feature_snapshot_builder = feature_snapshot_builder or FeatureSnapshotBuilder()
        self.event_strength_classifier = event_strength_classifier or EventStrengthClassifier()
        self.stream_publisher = stream_publisher
        self.stream_consumer = stream_consumer
        self.event_client = event_client
        self.active_signal_store = active_signal_store or InMemoryActiveSignalStore()
        self.current_time_supplier = current_time_supplier or (lambda: datetime.now(timezone.utc))
        self.rest_market_client = rest_market_client
        try:
            self.market_context_history_limit = max(
                1,
                int(market_context_history_limit or _DEFAULT_MARKET_CONTEXT_HISTORY_LIMIT),
            )
        except (TypeError, ValueError):
            self.market_context_history_limit = _DEFAULT_MARKET_CONTEXT_HISTORY_LIMIT
        self.news_feed_adapter = NewsFeedAdapter()
        self.onchain_feed_adapter = OnchainFeedAdapter()
        self.social_feed_adapter = SocialFeedAdapter()
        self._previous_price_by_symbol: dict[str, float] = {}
        self._signal_window_accumulators: dict[str, dict[str, Any]] = {}
        self._published_external_event_keys: dict[str, datetime] = {}
        self._market_context_history_by_symbol: dict[str, list[dict[str, Any]]] = self._normalize_initial_market_history(
            initial_market_context_history
        )

    def _normalize_initial_market_history(
        self,
        initial_market_context_history: dict[str, list[dict[str, Any]]] | None,
    ) -> dict[str, list[dict[str, Any]]]:
        if not isinstance(initial_market_context_history, dict):
            return {}
        normalized: dict[str, list[dict[str, Any]]] = {}
        for symbol, history in initial_market_context_history.items():
            symbol_key = str(symbol or "").strip().upper()
            if not symbol_key or not isinstance(history, list):
                continue
            normalized[symbol_key] = [dict(item) for item in history if isinstance(item, dict)][-self.market_context_history_limit:]
        return normalized

    def _merge_health_issue(
        self,
        current_issue: dict[str, str] | None,
        *,
        source_status: str,
        source_name: str,
        reason: str,
    ) -> dict[str, str]:
        priority = {
            "unavailable": 5,
            "abnormal": 4,
            "degraded": 3,
            "malformed": 2,
            "stale": 1,
            "empty": 0,
            "stale_items_filtered": 0,
            "ready_empty": 0,
        }
        next_issue = {
            "source_status": source_status,
            "source_name": source_name,
            "reason": reason,
        }
        if current_issue is None:
            return next_issue
        current_priority = priority.get(str(current_issue.get("source_status", "")).strip().lower(), -1)
        next_priority = priority.get(source_status, -1)
        if next_priority > current_priority:
            return next_issue
        return current_issue

    def _parse_market_event(self, payload: dict[str, Any]):
        if self.exchange == "okx":
            return OkxMarketMessageParser().parse(payload)
        return BinanceMarketMessageParser().parse(payload)

    def _prune_published_external_event_keys(self, now_dt: datetime) -> None:
        threshold = now_dt - timedelta(seconds=_EXTERNAL_EVENT_DEDUPE_TTL_SECONDS)
        expired = [key for key, observed_at in self._published_external_event_keys.items() if observed_at < threshold]
        for key in expired:
            self._published_external_event_keys.pop(key, None)

    def _should_emit_external_event(self, event: dict[str, Any], now_dt: datetime) -> bool:
        dedupe_key = _external_event_dedupe_key(event)
        if not dedupe_key:
            return True
        self._prune_published_external_event_keys(now_dt)
        if dedupe_key in self._published_external_event_keys:
            return False
        self._published_external_event_keys[dedupe_key] = now_dt
        return True

    def _price_change_pct(self, symbol: str, current_price: float) -> float:
        previous_price = self._previous_price_by_symbol.get(symbol)
        self._previous_price_by_symbol[symbol] = current_price
        if previous_price in (None, 0):
            return 0.0
        return round(((current_price - previous_price) / previous_price) * 100, 4)

    def _news_score(self, event_bundle: list[dict[str, Any]]) -> float:
        news_scores = [float(event.get("score", 0)) for event in event_bundle if event.get("event_type") == "news"]
        return max(news_scores, default=0.0, key=abs) if news_scores else 0.0

    def _social_score(self, event_bundle: list[dict[str, Any]]) -> float:
        social_scores = [float(event.get("score", 0)) for event in event_bundle if event.get("event_type") == "social"]
        return max(social_scores, default=0.0, key=abs) if social_scores else 0.0

    def _onchain_flow_bias(self, event_bundle: list[dict[str, Any]]) -> float:
        for event in reversed(event_bundle):
            if event.get("event_type") != "onchain":
                continue
            flow = event.get("flow")
            if flow == "exchange_outflow":
                return 1.0
            if flow == "exchange_inflow":
                return -1.0
        return 0.0

    def _stream_source_metadata(self, event: dict[str, Any]) -> dict[str, Any]:
        event_type = str(event.get("event_type", "")).strip().lower()
        source_name = str(event.get("source") or event.get("exchange") or self.exchange or "").strip()
        source_type = event_type or "runtime"
        if event_type in {
            "market_tick",
            "ticker",
            "mark_price",
            "liquidation",
            "funding_rate",
            "open_interest",
            "market_kline",
            "market_metric",
        }:
            source_type = "market"
            source_name = str(event.get("exchange") or self.exchange or "market").strip()
        elif event_type == "news":
            source_type = "news"
            source_name = str(event.get("source") or "news").strip()
        elif event_type == "onchain":
            source_type = "onchain"
            source_name = str(event.get("source") or "onchain").strip()
        elif event_type == "social":
            source_type = "social"
            source_name = str(event.get("source") or "social").strip()
        payload = {
            "source_type": source_type,
            "source_name": source_name or "runtime",
        }
        event_time = str(event.get("event_time") or event.get("timestamp") or event.get("ts") or "").strip()
        if event_time:
            payload["event_time"] = event_time
        return payload

    def _source_enabled(self, source_type: str) -> bool:
        if source_type == "news":
            return self.news_source_enabled
        if source_type == "onchain":
            return self.onchain_source_enabled
        if source_type == "social":
            return self.social_source_enabled
        return False

    def _build_source_health_event(
        self,
        *,
        source_type: str,
        source_status: str,
        source_name: str,
        reason: str = "",
    ) -> dict[str, Any]:
        event = {
            "event_type": "source_health",
            "exchange": "external",
            "source_type": source_type,
            "source_status": source_status,
            "source_name": source_name,
        }
        if reason:
            event["reason"] = reason
        return event

    def _resolve_supplier_payload(
        self,
        supplier_payload: Any,
        *,
        source_type: str,
    ) -> tuple[list[Any], dict[str, Any] | None]:
        if isinstance(supplier_payload, list):
            return supplier_payload, None
        if isinstance(supplier_payload, dict):
            if "items" in supplier_payload:
                items = supplier_payload.get("items")
                return (
                    items if isinstance(items, list) else [],
                    {
                        "source_type": source_type,
                        "source_status": str(supplier_payload.get("source_status") or "ready").strip().lower() or "ready",
                        "source_name": str(supplier_payload.get("source_name") or source_type).strip() or source_type,
                        "reason": str(supplier_payload.get("error_message") or supplier_payload.get("reason") or "").strip(),
                    },
                )
            return [supplier_payload], None
        if supplier_payload in (None, ""):
            return [], None
        return [], {
            "source_type": source_type,
            "source_status": "malformed",
            "source_name": source_type,
            "reason": "supplier_payload_invalid",
        }

    def _detect_source_status(self, event: dict[str, Any], adapter: Any) -> str:
        event_time = _parse_event_time(event.get("event_time"))
        if event_time is None:
            return "ready"
        stale_after_seconds = int(getattr(adapter, "stale_after_seconds", 0) or 0)
        if stale_after_seconds <= 0:
            return "ready"
        age_seconds = (self.current_time_supplier() - event_time).total_seconds()
        if age_seconds > stale_after_seconds:
            return "stale"
        return "ready"

    def _normalize_external_source(
        self,
        *,
        source_type: str,
        supplier: Callable[[str], Any],
        adapter: Any,
        symbol: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not self._source_enabled(source_type):
            return [], []
        supplier_payload = supplier(symbol)
        raw_items, payload_meta = self._resolve_supplier_payload(supplier_payload, source_type=source_type)
        normalized_events: list[dict[str, Any]] = []
        health_events: list[dict[str, Any]] = []
        source_name = str((payload_meta or {}).get("source_name") or source_type).strip() or source_type
        if not raw_items:
            source_status = str((payload_meta or {}).get("source_status") or "ready").strip().lower() or "ready"
            reason = str((payload_meta or {}).get("reason") or "").strip()
            if source_status == "ready":
                source_status = "ready_empty"
                reason = reason or "no_fresh_items"
            health_events.append(
                self._build_source_health_event(
                    source_type=source_type,
                    source_status=source_status,
                    source_name=source_name,
                    reason=reason,
                )
            )
            return normalized_events, health_events
        health_issue: dict[str, str] | None = None
        fresh_item_count = 0
        for item in raw_items:
            try:
                normalized = adapter.normalize(item)
            except Exception as exc:
                health_issue = self._merge_health_issue(
                    health_issue,
                    source_status="malformed",
                    source_name=source_name,
                    reason=str(exc),
                )
                continue
            source_status = self._detect_source_status(normalized, adapter)
            if source_status != "ready":
                if source_status == "stale":
                    source_status = "stale_items_filtered"
                health_issue = self._merge_health_issue(
                    health_issue,
                    source_status=source_status,
                    source_name=str(normalized.get("source") or source_name).strip() or source_name,
                    reason="event_time_stale",
                )
                continue
            normalized_events.append(normalized)
            fresh_item_count += 1
        if fresh_item_count == 0 and health_issue is not None:
            health_events.append(
                self._build_source_health_event(
                    source_type=source_type,
                    source_status=health_issue["source_status"],
                    source_name=health_issue["source_name"],
                    reason=health_issue["reason"],
                )
            )
        return normalized_events, health_events

    def _source_health_summary(self, event_bundle: list[dict[str, Any]]) -> dict[str, str]:
        summary: dict[str, str] = {}
        for event in event_bundle:
            if str(event.get("event_type") or "").strip().lower() != "source_health":
                continue
            source_type = str(event.get("source_type") or "").strip().lower()
            source_status = str(event.get("source_status") or "").strip().lower()
            if source_type and source_status:
                summary[source_type] = source_status
        return summary

    def _append_market_context_history(
        self,
        *,
        symbol: str,
        event_bundle: list[dict[str, Any]],
        market_payload: dict[str, Any],
        current_time: datetime,
        market_metric: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        market_metric = market_metric if isinstance(market_metric, dict) else {}
        liquidation = _largest_liquidation_event(event_bundle)
        market_tick = _latest_market_event(event_bundle, "market_tick")
        resolved_market_price = _resolve_effective_market_price(
            event_bundle=event_bundle,
            market_payload=market_payload,
            current_time=current_time,
            latest_trade_price=_safe_float(market_metric.get("latest_trade_price")),
            latest_mark_price=_safe_float(market_metric.get("mark_price")),
            latest_kline_close=_safe_float(market_metric.get("latest_kline_close")),
            effective_price=_safe_float(market_metric.get("effective_price")),
            effective_price_source=str(market_metric.get("effective_price_source") or ""),
            market_tick_staleness_seconds=_safe_float(market_metric.get("market_tick_staleness_seconds")),
        )
        latest_trade_price = _safe_float(resolved_market_price.get("latest_trade_price"))
        latest_mark_price = _safe_float(resolved_market_price.get("mark_price"))
        latest_kline_close = _safe_float(resolved_market_price.get("latest_kline_close"))
        effective_price = _safe_float(resolved_market_price.get("effective_price"))
        effective_price_source = str(resolved_market_price.get("effective_price_source") or "").strip()
        market_tick_staleness_seconds = _safe_float(resolved_market_price.get("market_tick_staleness_seconds"))
        entry = {
            "observed_at": current_time.isoformat(),
            "symbol": str(symbol or "").strip().upper(),
            "exchange": self.exchange,
            "price": effective_price,
            "latest_trade_price": latest_trade_price,
            "stale_trade_price": latest_trade_price if market_tick_staleness_seconds > 90 and latest_trade_price > 0 else 0.0,
            "trade_tick_status": "stale" if market_tick_staleness_seconds > 90 else "ready",
            "trade_tick_age_seconds": market_tick_staleness_seconds,
            "effective_price": effective_price,
            "effective_price_source": effective_price_source,
            "price_source": effective_price_source,
            "market_tick_staleness_seconds": market_tick_staleness_seconds,
            "latest_kline_close": latest_kline_close,
            "volume": _safe_float(market_tick.get("volume") or _payload_value(market_payload, "v", "vol24h", "volume")),
            "quote_volume": _safe_float(
                market_tick.get("quote_volume")
                or market_tick.get("quoteVolume")
                or market_tick.get("volume")
                or _payload_value(market_payload, "q", "quoteVolume", "volCcy24h", "turnover")
            ),
            "mark_price": _safe_float(_latest_market_event_value(event_bundle, "mark_price", "price", "markPrice")),
            "funding_rate": _safe_float(_latest_market_event_value(event_bundle, "funding_rate", "funding_rate", "fundingRate")),
            "open_interest": _safe_float(_latest_market_event_value(event_bundle, "open_interest", "open_interest", "openInterest", "oi")),
            "largest_liquidation_notional_usd": _safe_float(
                liquidation.get("notionalUsd") or liquidation.get("notional_usd")
            ),
            "largest_liquidation_side": str(liquidation.get("side") or "").strip(),
        }
        history = self._market_context_history_by_symbol.setdefault(str(symbol or "").strip().upper(), [])
        history.append(entry)
        del history[:-self.market_context_history_limit]
        return [dict(item) for item in history]

    def _market_history_trigger_metrics(self, history: list[dict[str, Any]]) -> dict[str, float]:
        prices = [_safe_float(item.get("price")) for item in history if _safe_float(item.get("price")) > 0]
        quote_volumes = [
            _safe_float(item.get("quote_volume"))
            for item in history
            if _safe_float(item.get("quote_volume")) > 0
        ]
        metrics = {
            "market_window_price_change_pct": 0.0,
            "market_price_acceleration_pct": 0.0,
            "market_quote_volume_change_pct": 0.0,
            "mark_price_deviation_pct": 0.0,
        }
        if len(prices) >= 2 and prices[0] > 0:
            metrics["market_window_price_change_pct"] = round(((prices[-1] - prices[0]) / prices[0]) * 100.0, 4)
        if len(prices) >= 3 and prices[0] > 0 and prices[-2] > 0:
            previous_change = ((prices[-2] - prices[0]) / prices[0]) * 100.0
            latest_change = ((prices[-1] - prices[-2]) / prices[-2]) * 100.0
            metrics["market_price_acceleration_pct"] = round(latest_change - previous_change, 4)
        if len(quote_volumes) >= 2 and quote_volumes[0] > 0:
            metrics["market_quote_volume_change_pct"] = round(
                ((quote_volumes[-1] - quote_volumes[0]) / quote_volumes[0]) * 100.0,
                4,
            )
        latest = history[-1] if history else {}
        latest_price = _safe_float(latest.get("effective_price") or latest.get("price"))
        latest_mark_price = _safe_float(latest.get("mark_price"))
        if latest_price > 0 and latest_mark_price > 0:
            metrics["mark_price_deviation_pct"] = round(
                ((latest_mark_price - latest_price) / latest_price) * 100.0,
                4,
            )
        return metrics

    def _oi_change_pct(self, symbol: str) -> float:
        history = self._market_context_history_by_symbol.get(str(symbol or "").strip().upper()) or []
        samples = [_safe_float(item.get("open_interest")) for item in history if _safe_float(item.get("open_interest")) > 0]
        if len(samples) < 2 or samples[0] <= 0:
            return 0.0
        return round(((samples[-1] - samples[0]) / samples[0]) * 100.0, 4)

    def _rest_market_client(self) -> Any:
        if self.rest_market_client is not None:
            return self.rest_market_client
        self.rest_market_client = OkxRestMarketClient()
        return self.rest_market_client

    def _enhanced_market_events(
        self,
        *,
        symbol: str,
        event_bundle: list[dict[str, Any]],
        runtime_config: dict[str, Any] | None,
        strategy_context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        config = _market_data_enhancement_config(runtime_config)
        if self.exchange != "okx" or config.get("enabled") is False:
            return [], {}
        client = self._rest_market_client()
        events: list[dict[str, Any]] = []
        kline_events_by_interval: dict[str, list[dict[str, Any]]] = {}
        stale_after_seconds = max(1, int(config.get("marketTickStaleAfterSeconds") or 90))
        latest_market_tick = _latest_market_event(event_bundle, "market_tick")
        market_tick_staleness_seconds = _market_tick_staleness_seconds(
            latest_market_tick,
            current_time=self.current_time_supplier(),
        )
        if config.get("restFallbackEnabled") is not False and (
            not latest_market_tick or market_tick_staleness_seconds > stale_after_seconds
        ):
            fetch_ticker = getattr(client, "fetch_ticker", None)
            if callable(fetch_ticker):
                try:
                    event = fetch_ticker(symbol)
                except Exception as exc:
                    logger.exception("okx rest enhancement failed method=%s symbol=%s error=%s", "fetch_ticker", symbol, exc)
                else:
                    if isinstance(event, dict) and event.get("event_type"):
                        events.append(event)
        for method_name in ("fetch_mark_price", "fetch_funding_rate", "fetch_open_interest"):
            method = getattr(client, method_name, None)
            if not callable(method):
                continue
            try:
                event = method(symbol)
            except Exception as exc:
                logger.exception("okx rest enhancement failed method=%s symbol=%s error=%s", method_name, symbol, exc)
                continue
            if isinstance(event, dict) and event.get("event_type"):
                events.append(event)
        if config.get("klineEnabled") is not False:
            fetch_candles = getattr(client, "fetch_candles", None)
            if callable(fetch_candles):
                for interval in config.get("klineIntervals") or ["1m"]:
                    try:
                        candles = fetch_candles(symbol, interval=interval, limit=config.get("klineLimit") or 120)
                    except Exception as exc:
                        logger.exception("okx kline enhancement failed interval=%s symbol=%s error=%s", interval, symbol, exc)
                        continue
                    normalized_candles = [dict(item) for item in candles if isinstance(item, dict)]
                    if normalized_candles:
                        kline_events_by_interval[str(interval)] = normalized_candles
                        events.extend(normalized_candles[-3:])
        combined_events = [*event_bundle, *events]
        kline_context = summarize_kline_context(kline_events_by_interval) if kline_events_by_interval else {}
        wyckoff_15m_bars = _compact_wyckoff_15m_bars(kline_events_by_interval)
        latest_market_tick = _latest_market_event(combined_events, "market_tick")
        latest_trade_price = _safe_float(latest_market_tick.get("price"))
        mark_price = _latest_mark_price(combined_events)
        liquidation = _largest_liquidation_event(combined_events)
        observed_at = self.current_time_supplier()
        market_tick_staleness_seconds = _market_tick_staleness_seconds(latest_market_tick, current_time=observed_at)
        stale_after_seconds = max(1, int(config.get("marketTickStaleAfterSeconds") or 90))
        trade_tick_status = "stale" if market_tick_staleness_seconds > stale_after_seconds else "ready"
        latest_kline_close = _latest_kline_close(kline_events_by_interval)
        effective_price_source = "trade"
        effective_price = latest_trade_price
        if latest_trade_price <= 0:
            if mark_price > 0:
                effective_price = mark_price
                effective_price_source = "mark_price"
            elif latest_kline_close > 0:
                effective_price = latest_kline_close
                effective_price_source = "kline_close"
        elif market_tick_staleness_seconds > stale_after_seconds:
            if mark_price > 0:
                effective_price = mark_price
                effective_price_source = "mark_price"
            elif latest_kline_close > 0:
                effective_price = latest_kline_close
                effective_price_source = "kline_close"
        mark_deviation = 0.0
        if effective_price > 0 and mark_price > 0:
            mark_deviation = round(((mark_price - effective_price) / effective_price) * 100.0, 4)
        previous_history = self._market_context_history_by_symbol.get(str(symbol or "").strip().upper()) or []
        previous_open_interest = next(
            (_safe_float(item.get("open_interest")) for item in reversed(previous_history) if _safe_float(item.get("open_interest")) > 0),
            0.0,
        )
        open_interest = _latest_open_interest(combined_events)
        oi_change_pct = 0.0
        if previous_open_interest > 0 and open_interest > 0:
            oi_change_pct = round(((open_interest - previous_open_interest) / previous_open_interest) * 100.0, 4)
        wyckoff_shortterm = analyze_wyckoff_shortterm(
            kline_events_by_interval,
            latest_price=effective_price or latest_trade_price,
            mark_price=mark_price,
            funding_rate=_latest_funding_rate(combined_events),
            oi_change_pct=oi_change_pct,
            price_source=effective_price_source,
            config=_wyckoff_shortterm_config(runtime_config, strategy_context),
        )
        if isinstance(kline_context, dict):
            kline_context["wyckoff_shortterm"] = wyckoff_shortterm
        market_metric = {
            "event_type": "market_metric",
            "symbol": str(symbol or "").strip().upper(),
            "exchange": self.exchange,
            "observed_at": observed_at.isoformat(),
            "latest_price": effective_price,
            "latest_trade_price": latest_trade_price,
            "stale_trade_price": latest_trade_price if trade_tick_status == "stale" and latest_trade_price > 0 else 0.0,
            "trade_tick_status": trade_tick_status,
            "trade_tick_age_seconds": market_tick_staleness_seconds,
            "effective_price": effective_price,
            "effective_price_source": effective_price_source,
            "market_tick_staleness_seconds": market_tick_staleness_seconds,
            "latest_kline_close": latest_kline_close,
            "mark_price": mark_price,
            "mark_price_deviation_pct": mark_deviation,
            "funding_rate": _latest_funding_rate(combined_events),
            "open_interest": open_interest,
            "volume_24h": _safe_float(latest_market_tick.get("volume")),
            "quote_volume_24h": _safe_float(latest_market_tick.get("quote_volume") or latest_market_tick.get("quoteVolume")),
            "liquidation_notional_15m": _liquidation_notional_sum(combined_events),
            "liquidation_notional_60m": _liquidation_notional_sum(combined_events),
            "liquidation_notional_240m": _liquidation_notional_sum(combined_events),
            "largest_liquidation_notional_usd": _safe_float(liquidation.get("notionalUsd") or liquidation.get("notional_usd")),
            "largest_liquidation_side": str(liquidation.get("side") or "").strip(),
            "kline_context": kline_context,
            "wyckoff_shortterm": wyckoff_shortterm,
            "wyckoff_15m_bars": wyckoff_15m_bars,
        }
        return [*events, market_metric], {"kline_context": kline_context, "market_metric": market_metric}

    def build(
        self,
        *,
        symbol: str,
        trace_id: str = "",
        runtime_config: dict[str, Any] | None = None,
        strategy_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current_time = self.current_time_supplier()
        try:
            market_payload = self.market_payload_supplier(symbol)
        except Exception as exc:
            logger.exception(
                "market payload fetch failed symbol=%s exchange=%s error=%s",
                symbol,
                self.exchange,
                exc,
            )
            market_payload = {
                "s": symbol,
                "instId": symbol,
                "c": "0",
                "last": "0",
                "q": "0",
                "vol24h": "0",
                "data": [{"instId": symbol, "last": "0", "vol24h": "0"}],
                "_market_source_status": "unavailable",
                "_market_source_error": str(exc),
            }
        market_source_status = str(market_payload.get("_market_source_status", "")).strip().lower()
        market_event = self._parse_market_event(market_payload)
        event_bundle = [market_event.model_dump(), *_supplemental_market_events(market_payload, exchange=self.exchange, symbol=symbol)]
        enhanced_events, enhanced_context = self._enhanced_market_events(
            symbol=symbol,
            event_bundle=event_bundle,
            runtime_config=runtime_config,
            strategy_context=strategy_context,
        )
        event_bundle.extend(enhanced_events)
        market_metric = (
            enhanced_context.get("market_metric")
            if isinstance(enhanced_context, dict) and isinstance(enhanced_context.get("market_metric"), dict)
            else {}
        )
        market_tick_stale_after_seconds = max(
            1,
            int(_market_data_enhancement_config(runtime_config).get("marketTickStaleAfterSeconds") or 90),
        )
        resolved_market_price = _resolve_effective_market_price(
            event_bundle=event_bundle,
            market_payload=market_payload,
            current_time=current_time,
            latest_trade_price=_safe_float(market_metric.get("latest_trade_price")),
            latest_mark_price=_safe_float(market_metric.get("mark_price")),
            latest_kline_close=_safe_float(market_metric.get("latest_kline_close")),
            effective_price=_safe_float(market_metric.get("effective_price")),
            effective_price_source=str(market_metric.get("effective_price_source") or ""),
            market_tick_staleness_seconds=_safe_float(market_metric.get("market_tick_staleness_seconds")),
            stale_after_seconds=market_tick_stale_after_seconds,
        )
        market_source_status = market_source_status or resolve_market_source_status(event_bundle)
        market_source_status = _promote_market_source_status_from_tick_staleness(
            event_bundle=event_bundle,
            current_status=market_source_status,
            current_time=current_time,
            runtime_config=runtime_config,
            market_tick_staleness_seconds=_safe_float(resolved_market_price.get("market_tick_staleness_seconds")),
            effective_price_source=str(resolved_market_price.get("effective_price_source") or ""),
        )
        if market_source_status in {"stale", "abnormal", "degraded", "unavailable"} and not any(
            str(event.get("event_type") or "").strip().lower()
            == ("stale" if market_source_status == "stale" else "market_source_abnormal")
            for event in event_bundle
        ):
            event_bundle.append(
                _market_source_status_event(market_source_status)
            )
        for normalized_events, health_events in (
            self._normalize_external_source(
                source_type="news",
                supplier=self.news_items_supplier,
                adapter=self.news_feed_adapter,
                symbol=symbol,
            ),
            self._normalize_external_source(
                source_type="onchain",
                supplier=self.onchain_items_supplier,
                adapter=self.onchain_feed_adapter,
                symbol=symbol,
            ),
            self._normalize_external_source(
                source_type="social",
                supplier=self.social_items_supplier,
                adapter=self.social_feed_adapter,
                symbol=symbol,
            ),
        ):
            event_bundle.extend(normalized_events)
            event_bundle.extend(health_events)
        emit_events = [event for event in event_bundle if self._should_emit_external_event(event, current_time)]
        if self.stream_publisher is not None:
            for event in emit_events:
                try:
                    self.stream_publisher.publish(
                        event,
                        trace_id=trace_id,
                        source_metadata=self._stream_source_metadata(event),
                    )
                except Exception as exc:
                    logger.exception(
                        "event emit failed sink=stream trace_id=%s event_type=%s symbol=%s exchange=%s error=%s",
                        trace_id,
                        event.get("event_type"),
                        event.get("symbol"),
                        event.get("exchange"),
                        exc,
                    )
        if self.stream_consumer is not None and self.stream_publisher is not None:
            try:
                self.stream_consumer.consume_available(max_messages=len(emit_events), block_ms=0)
            except Exception as exc:
                logger.exception("event stream consume failed trace_id=%s error=%s", trace_id, exc)
        elif self.event_client is not None:
            for event in emit_events:
                try:
                    self.event_client.post_event(trace_id=trace_id, event=event)
                except Exception as exc:
                    logger.exception(
                        "event emit failed sink=http trace_id=%s event_type=%s symbol=%s exchange=%s error=%s",
                        trace_id,
                        event.get("event_type"),
                        event.get("symbol"),
                        event.get("exchange"),
                        exc,
                    )
        _update_signal_window_accumulators(self._signal_window_accumulators, event_bundle, current_time=current_time)
        raw_signal_window_states = [
            _signal_window_state_payload(window_key, accumulator, current_time=current_time)
            for window_key, accumulator in self._signal_window_accumulators.items()
            if str(accumulator.get("symbol", "")).strip() == symbol
        ]
        signal_window_states = self.active_signal_store.upsert_many(raw_signal_window_states, now=current_time)
        signal_window_states = self.active_signal_store.snapshot(symbol=symbol, now=current_time)
        resolved_market_price = _resolve_effective_market_price(
            event_bundle=event_bundle,
            market_payload=market_payload,
            current_time=current_time,
            latest_trade_price=_safe_float(market_metric.get("latest_trade_price")),
            latest_mark_price=_safe_float(market_metric.get("mark_price")),
            latest_kline_close=_safe_float(market_metric.get("latest_kline_close")),
            effective_price=_safe_float(market_metric.get("effective_price")),
            effective_price_source=str(market_metric.get("effective_price_source") or ""),
            market_tick_staleness_seconds=_safe_float(market_metric.get("market_tick_staleness_seconds")),
            stale_after_seconds=market_tick_stale_after_seconds,
        )
        price_change_reference = _safe_float(
            resolved_market_price.get("effective_price")
            or resolved_market_price.get("latest_trade_price")
            or market_event.price
        )
        price_change_pct = self._price_change_pct(symbol, price_change_reference)
        news_score = self._news_score(event_bundle)
        social_score = self._social_score(event_bundle)
        onchain_flow_bias = self._onchain_flow_bias(event_bundle)
        funding_rate = _latest_funding_rate(event_bundle)
        trigger_feature_snapshot = {
            "symbol": symbol,
            "price_change_pct": price_change_pct,
            "funding_rate": funding_rate,
            "news_score": news_score,
            "social_score": social_score,
            "onchain_flow_bias": onchain_flow_bias,
            "effective_price": _safe_float(resolved_market_price.get("effective_price")),
            "effective_price_source": str(resolved_market_price.get("effective_price_source") or ""),
            "market_tick_staleness_seconds": _safe_float(resolved_market_price.get("market_tick_staleness_seconds")),
        }
        if isinstance(market_metric.get("wyckoff_shortterm"), dict):
            trigger_feature_snapshot["wyckoff_shortterm"] = market_metric.get("wyckoff_shortterm")
        feature_snapshot = self.feature_snapshot_builder.build(
            symbol=symbol,
            price_change_pct=price_change_pct,
            funding_rate=funding_rate,
            oi_change_pct=0.0,
            news_score=news_score,
            social_score=social_score,
            onchain_flow_bias=onchain_flow_bias,
            event_strength=classify_event_strength_from_policy(
                event_bundle=event_bundle,
                feature_snapshot=trigger_feature_snapshot,
                runtime_config=runtime_config,
                strategy_context=strategy_context,
                now=current_time,
            ),
        )
        source_health = self._source_health_summary(event_bundle)
        feature_snapshot["source_health"] = source_health
        healthy_aux_statuses = {"ready", "ready_empty", "stale_items_filtered"}
        feature_snapshot["degraded_sources"] = [
            source for source, status in source_health.items() if status not in healthy_aux_statuses
        ]
        feature_snapshot["aux_source_status"] = "aux_source_degraded" if feature_snapshot["degraded_sources"] else "ready"
        market_context_history = self._append_market_context_history(
            symbol=symbol,
            event_bundle=event_bundle,
            market_payload=market_payload,
            current_time=current_time,
            market_metric=market_metric,
        )
        feature_snapshot.update(self._market_history_trigger_metrics(market_context_history))
        feature_snapshot["oi_change_pct"] = self._oi_change_pct(symbol)
        latest_market_history_entry = market_context_history[-1] if market_context_history else {}
        if isinstance(latest_market_history_entry, dict):
            feature_snapshot["latest_price"] = _safe_float(
                latest_market_history_entry.get("effective_price") or latest_market_history_entry.get("price")
            )
            feature_snapshot["latest_trade_price"] = _safe_float(latest_market_history_entry.get("latest_trade_price"))
            feature_snapshot["stale_trade_price"] = _safe_float(latest_market_history_entry.get("stale_trade_price"))
            feature_snapshot["trade_tick_status"] = str(latest_market_history_entry.get("trade_tick_status") or "")
            feature_snapshot["trade_tick_age_seconds"] = _safe_float(latest_market_history_entry.get("trade_tick_age_seconds"))
            feature_snapshot["effective_price"] = _safe_float(latest_market_history_entry.get("effective_price"))
            feature_snapshot["effective_price_source"] = str(latest_market_history_entry.get("effective_price_source") or "")
            feature_snapshot["market_tick_staleness_seconds"] = _safe_float(
                latest_market_history_entry.get("market_tick_staleness_seconds")
            )
            feature_snapshot["latest_kline_close"] = _safe_float(latest_market_history_entry.get("latest_kline_close"))
        if isinstance(market_metric, dict) and market_metric:
            feature_snapshot["latest_price"] = _safe_float(market_metric.get("latest_price"))
            feature_snapshot["latest_trade_price"] = _safe_float(market_metric.get("latest_trade_price"))
            feature_snapshot["stale_trade_price"] = _safe_float(market_metric.get("stale_trade_price"))
            feature_snapshot["trade_tick_status"] = str(market_metric.get("trade_tick_status") or "")
            feature_snapshot["trade_tick_age_seconds"] = _safe_float(market_metric.get("trade_tick_age_seconds"))
            feature_snapshot["effective_price"] = _safe_float(market_metric.get("effective_price"))
            feature_snapshot["effective_price_source"] = str(market_metric.get("effective_price_source") or "")
            feature_snapshot["market_tick_staleness_seconds"] = _safe_float(market_metric.get("market_tick_staleness_seconds"))
            feature_snapshot["latest_kline_close"] = _safe_float(market_metric.get("latest_kline_close"))
            feature_snapshot["latest_quote_volume"] = _safe_float(market_metric.get("quote_volume_24h"))
            feature_snapshot["mark_price"] = _safe_float(market_metric.get("mark_price"))
            feature_snapshot["mark_price_deviation_pct"] = _safe_float(market_metric.get("mark_price_deviation_pct"))
            feature_snapshot["funding_rate"] = _safe_float(market_metric.get("funding_rate")) or feature_snapshot.get("funding_rate", 0.0)
            feature_snapshot["open_interest"] = _safe_float(market_metric.get("open_interest"))
            feature_snapshot["liquidation_notional_15m"] = _safe_float(market_metric.get("liquidation_notional_15m"))
            feature_snapshot["liquidation_notional_60m"] = _safe_float(market_metric.get("liquidation_notional_60m"))
            feature_snapshot["liquidation_notional_240m"] = _safe_float(market_metric.get("liquidation_notional_240m"))
            feature_snapshot["largest_liquidation_notional_usd"] = _safe_float(
                market_metric.get("largest_liquidation_notional_usd")
            )
            feature_snapshot["largest_liquidation_side"] = str(market_metric.get("largest_liquidation_side") or "")
            if isinstance(market_metric.get("wyckoff_shortterm"), dict):
                feature_snapshot["wyckoff_shortterm"] = market_metric.get("wyckoff_shortterm")
            if isinstance(market_metric.get("wyckoff_15m_bars"), dict) and market_metric.get("wyckoff_15m_bars"):
                feature_snapshot["wyckoff_15m_bars"] = market_metric.get("wyckoff_15m_bars")
        kline_context = enhanced_context.get("kline_context") if isinstance(enhanced_context, dict) else {}
        if isinstance(kline_context, dict) and kline_context:
            feature_snapshot["kline_price_change_pct"] = kline_context.get("price_change_pct") or {}
            feature_snapshot["kline_quote_volume_ratio"] = kline_context.get("quote_volume_ratio") or {}
            feature_snapshot["atr_pct"] = kline_context.get("atr_pct") or {}
            feature_snapshot["rsi_14"] = kline_context.get("rsi_14") or {}
            feature_snapshot["ema_trend"] = kline_context.get("ema_trend") or {}
            feature_snapshot["kline_period_summaries"] = kline_context.get("period_summaries") or []
            feature_snapshot["kline_volume_price_signals"] = kline_context.get("volume_price_signals") or []
            if isinstance(kline_context.get("wyckoff_shortterm"), dict):
                feature_snapshot["wyckoff_shortterm"] = kline_context.get("wyckoff_shortterm")
            if market_context_history:
                market_context_history[-1]["kline_context"] = kline_context
        return {
            "event_bundle": event_bundle,
            "feature_snapshot": feature_snapshot,
            "market_context_history": market_context_history,
            "signal_window_states": signal_window_states,
            "trigger_summary": {
                "active_signal_count": len(signal_window_states),
                "active_sources": sorted(
                    {
                        str(item.get("source_type") or "").strip()
                        for item in signal_window_states
                        if str(item.get("source_type") or "").strip()
                    }
                ),
            },
            "market_source_status": market_source_status,
            "aux_source_status": feature_snapshot["aux_source_status"],
        }
