from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from trade_runtime.config import parse_object_json


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True, default=str)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
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
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(int(float(value)), 0)
    except (TypeError, ValueError):
        return None


def resolve_prompt_current_time(state: dict[str, Any]) -> str:
    return str(
        state.get("current_time")
        or state.get("supervisedAt")
        or state.get("decision_time")
        or ""
    ).strip()


def resolve_current_position_holding_minutes(state: dict[str, Any]) -> int | str:
    explicit_value = _safe_int(state.get("current_position_holding_minutes"))
    if explicit_value is not None:
        return explicit_value
    opened_at = _parse_datetime(state.get("current_position_opened_at"))
    current_time = _parse_datetime(resolve_prompt_current_time(state))
    if opened_at is None or current_time is None:
        return ""
    holding_seconds = (current_time - opened_at).total_seconds()
    if holding_seconds < 0:
        return 0
    return int(holding_seconds // 60)


def _normalize_market_history(state: dict[str, Any]) -> list[dict[str, Any]]:
    history = state.get("market_context_history")
    if not isinstance(history, list) or not history:
        history = [
            item
            for item in state.get("event_bundle") or []
            if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() == "market_tick"
        ]
    if not isinstance(history, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        observed_at = _parse_datetime(entry.get("observed_at") or entry.get("timestamp") or entry.get("event_time"))
        if observed_at is not None:
            entry["_observed_at_dt"] = observed_at
        entry["price"] = _safe_float(entry.get("price") or entry.get("last_price"))
        entry["volume"] = _safe_float(entry.get("volume") or entry.get("base_volume"))
        entry["quote_volume"] = _safe_float(
            entry.get("quote_volume") or entry.get("quoteVolume") or entry.get("turnover") or entry.get("volume")
        )
        normalized.append(entry)
    return normalized


def _window_history(history: list[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    if not history:
        return []
    latest_time = next((item.get("_observed_at_dt") for item in reversed(history) if item.get("_observed_at_dt")), None)
    if latest_time is None:
        return history[-min(len(history), max(2, minutes // 5)) :]
    threshold = latest_time - timedelta(minutes=minutes)
    return [item for item in history if item.get("_observed_at_dt") is None or item["_observed_at_dt"] >= threshold]


def _period_summary(history: list[dict[str, Any]], window: str) -> dict[str, Any]:
    prices = [_safe_float(item.get("price")) for item in history if _safe_float(item.get("price")) > 0]
    quote_volumes = [_safe_float(item.get("quote_volume")) for item in history if _safe_float(item.get("quote_volume")) > 0]
    if len(prices) < 2:
        return {"window": window, "sample_count": len(prices), "status": "insufficient"}
    start_price = prices[0]
    end_price = prices[-1]
    high_price = max(prices)
    low_price = min(prices)
    price_change_pct = ((end_price - start_price) / start_price) * 100.0 if start_price > 0 else 0.0
    quote_volume_change_pct = 0.0
    if len(quote_volumes) >= 2 and quote_volumes[0] > 0:
        quote_volume_change_pct = ((quote_volumes[-1] - quote_volumes[0]) / quote_volumes[0]) * 100.0
    return {
        "window": window,
        "sample_count": len(prices),
        "start_price": round(start_price, 8),
        "end_price": round(end_price, 8),
        "high_price": round(high_price, 8),
        "low_price": round(low_price, 8),
        "price_change_pct": round(price_change_pct, 6),
        "range_pct": round(((high_price - low_price) / start_price) * 100.0 if start_price > 0 else 0.0, 6),
        "quote_volume_start": round(quote_volumes[0], 6) if quote_volumes else 0.0,
        "quote_volume_end": round(quote_volumes[-1], 6) if quote_volumes else 0.0,
        "quote_volume_change_pct": round(quote_volume_change_pct, 6),
    }


def _volume_price_signals(period_summaries: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    for summary in period_summaries:
        if summary.get("status") == "insufficient":
            continue
        price_change = _safe_float(summary.get("price_change_pct"))
        volume_change = _safe_float(summary.get("quote_volume_change_pct"))
        window = str(summary.get("window") or "")
        if price_change >= 1.0 and volume_change >= 20.0:
            signals.append(f"{window}:price_up_volume_expands")
        elif price_change <= -1.0 and volume_change >= 20.0:
            signals.append(f"{window}:price_down_volume_expands")
        elif abs(price_change) <= 0.5 and volume_change >= 30.0:
            signals.append(f"{window}:effort_without_result")
        elif abs(price_change) >= 1.0 and volume_change <= -20.0:
            signals.append(f"{window}:price_move_volume_divergence")
    return signals


def _enrich_candle_series(candles: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """
    Enrich candle data with derived metrics for Wyckoff analysis.

    For each candle, calculate:
    - body_pct: Body size as percentage of total range
    - upper_wick_pct: Upper wick as percentage of range
    - lower_wick_pct: Lower wick as percentage of range
    - change_pct: Price change from previous candle
    - volume_ratio: Volume relative to previous 4-candle average
    """
    if not candles or limit <= 0:
        return []

    sorted_candles = sorted([c for c in candles if isinstance(c, dict)], key=lambda x: float(x.get("open_time") or x.get("event_time") or 0))
    if len(sorted_candles) < 2:
        return []

    result = []
    for i, candle in enumerate(sorted_candles[-limit:]):
        o = _safe_float(candle.get("open") or candle.get("o"))
        h = _safe_float(candle.get("high") or candle.get("h"))
        l = _safe_float(candle.get("low") or candle.get("l"))
        c = _safe_float(candle.get("close") or candle.get("c"))
        v = _safe_float(candle.get("quote_volume") or candle.get("quoteVolume") or candle.get("turnover"))

        range_val = h - l if h > l else 1
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        enriched = {
            "open_time": candle.get("open_time") or candle.get("event_time"),
            "open": round(o, 4),
            "high": round(h, 4),
            "low": round(l, 4),
            "close": round(c, 4),
            "quote_volume": round(v, 2),
            "body_pct": round(body / range_val, 4) if range_val > 0 else 0,
            "upper_wick_pct": round(upper_wick / range_val, 4) if range_val > 0 else 0,
            "lower_wick_pct": round(lower_wick / range_val, 4) if range_val > 0 else 0,
        }

        # Calculate change from previous candle
        if i > 0 and result:
            prev_close = result[-1]["close"]
            if prev_close > 0:
                enriched["change_pct"] = round((c - prev_close) / prev_close * 100, 4)

        # Calculate volume ratio relative to previous 4 candles
        actual_idx = len(sorted_candles) - limit + i
        if actual_idx >= 4:
            prev_volumes = []
            for j in range(1, 5):
                prev_candle = sorted_candles[actual_idx - j]
                prev_v = _safe_float(prev_candle.get("quote_volume") or prev_candle.get("quoteVolume") or prev_candle.get("turnover"))
                prev_volumes.append(prev_v)
            avg_volume = sum(prev_volumes) / 4 if prev_volumes else 1
            enriched["volume_ratio"] = round(v / avg_volume, 4) if avg_volume > 0 else 0

        result.append(enriched)

    return result


def _build_kline_series(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """
    Build K-line series data from feature_snapshot for Wyckoff analysis.

    Returns:
        dict with:
        - "15m": Last 20 enriched 15m candles
        - "1h": Last 12 enriched 1h candles
    """
    feature_snapshot = state.get("feature_snapshot")
    if not isinstance(feature_snapshot, dict):
        return {}

    wyckoff_bars = feature_snapshot.get("wyckoff_15m_bars")
    if isinstance(wyckoff_bars, dict) and isinstance(wyckoff_bars.get("bars"), list) and wyckoff_bars.get("bars"):
        return {"15m": [dict(item) for item in wyckoff_bars.get("bars") if isinstance(item, dict)]}

    candles_by_interval = feature_snapshot.get("candles_by_interval")
    if not isinstance(candles_by_interval, dict):
        return {}

    result = {}

    # 15m candles: last 20 bars
    fifteen = candles_by_interval.get("15m") or []
    if fifteen:
        result["15m"] = _enrich_candle_series(fifteen, limit=20)

    # 1h candles: last 12 bars
    one_hour = candles_by_interval.get("1h") or candles_by_interval.get("60m") or []
    if one_hour:
        result["1h"] = _enrich_candle_series(one_hour, limit=12)

    return result


def _wyckoff_context(history: list[dict[str, Any]], period_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    usable_summaries = [item for item in period_summaries if item.get("status") != "insufficient"]
    if period_summaries and all(str(item.get("source") or "") == "kline_ohlcv" for item in period_summaries) and not usable_summaries:
        return {"phase": "context_insufficient", "confidence": 0.0, "reason": "not_enough_kline_history"}
    usable = [item for item in history if _safe_float(item.get("price")) > 0]
    if not usable_summaries and len(usable) < 3:
        return {"phase": "context_insufficient", "confidence": 0.0, "reason": "not_enough_market_history"}
    latest_summary = next(iter(usable_summaries), {})
    price_change = _safe_float(latest_summary.get("price_change_pct"))
    volume_ratio = _safe_float(latest_summary.get("quote_volume_ratio"))
    volume_change = _safe_float(latest_summary.get("quote_volume_change_pct"))
    range_pct = _safe_float(latest_summary.get("range_pct"))
    volume_expands = volume_ratio >= 1.2 if volume_ratio > 0 else volume_change >= 20.0
    high_effort = volume_ratio >= 1.5 if volume_ratio > 0 else volume_change >= 20.0
    if price_change >= 2.0 and volume_expands:
        phase = "markup"
        reason = "rising_price_with_expanding_volume"
        confidence = 0.72
    elif price_change <= -2.0 and volume_expands:
        phase = "markdown"
        reason = "falling_price_with_expanding_volume"
        confidence = 0.72
    elif abs(price_change) <= 0.8 and range_pct <= 2.0 and high_effort:
        phase = "accumulation_or_distribution"
        reason = "range_bound_high_effort_requires_confirmation"
        confidence = 0.55
    elif abs(price_change) <= 1.0:
        phase = "range"
        reason = "price_balanced_in_range"
        confidence = 0.5
    else:
        phase = "transition"
        reason = "mixed_volume_price_structure"
        confidence = 0.45
    return {"phase": phase, "confidence": confidence, "reason": reason}


def _build_period_summaries(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _period_summary(_window_history(history, 15), "15m"),
        _period_summary(_window_history(history, 60), "60m"),
        _period_summary(_window_history(history, 240), "240m"),
    ]



def _source_events(state: dict[str, Any], event_type: str, limit: int = 10) -> list[dict[str, Any]]:
    events = [
        dict(item)
        for item in state.get("event_bundle") or []
        if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() == event_type
    ]
    return events[-limit:]


def _prompt_quality_config(state: dict[str, Any]) -> dict[str, Any]:
    runtime_config = state.get("runtime_config")
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    runtime_flags = parse_object_json(runtime_config.get("runtime_flags") or runtime_config.get("runtimeFlags"))
    runtime_flags_json = parse_object_json(runtime_config.get("runtime_flags_json") or runtime_config.get("runtimeFlagsJson"))
    prompt_quality = parse_object_json(runtime_config.get("promptQuality") or runtime_config.get("prompt_quality"))
    merged_flags = {**runtime_flags_json, **runtime_flags}
    prompt_quality.update(parse_object_json(merged_flags.get("promptQuality") or merged_flags.get("prompt_quality")))
    return prompt_quality


def _recent_ttl_seconds(state: dict[str, Any], key: str, default_seconds: int) -> int:
    prompt_quality = _prompt_quality_config(state)
    value = prompt_quality.get(key)
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return default_seconds


def _filter_recent_events_by_ttl(
    state: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    ttl_seconds: int,
) -> tuple[list[dict[str, Any]], int, int]:
    current_time = _parse_datetime(resolve_prompt_current_time(state))
    duplicate_count = 0
    threshold = current_time - timedelta(seconds=ttl_seconds) if current_time is not None else None
    filtered: list[dict[str, Any]] = []
    stale_count = 0
    seen: set[str] = set()
    for event in events:
        event_time = _parse_datetime(event.get("event_time") or event.get("timestamp") or event.get("ts"))
        if threshold is not None and event_time is not None and event_time < threshold:
            stale_count += 1
            continue
        fingerprint = str(
            event.get("id")
            or event.get("event_id")
            or event.get("txHash")
            or event.get("tx_hash")
            or event.get("hash")
            or event.get("url")
            or event.get("headline")
            or json.dumps(event, sort_keys=True, default=str)
        )
        if fingerprint in seen:
            duplicate_count += 1
            continue
        seen.add(fingerprint)
        filtered.append(event)
    return filtered, stale_count, duplicate_count


def _build_recent_news_context(state: dict[str, Any]) -> dict[str, Any]:
    events = _source_events(state, "news")
    events, stale_count, duplicate_count = _filter_recent_events_by_ttl(
        state,
        events,
        ttl_seconds=_recent_ttl_seconds(state, "recentNewsTtlSeconds", 7200),
    )
    if not events:
        return {
            "event_count": 0,
            "events": [],
            "summary": "no_recent_news",
            "stale_items_filtered": stale_count,
            "duplicate_items_filtered": duplicate_count,
        }
    strongest = max(events, key=lambda item: abs(_safe_float(item.get("score"))), default={})
    return {
        "event_count": len(events),
        "stale_items_filtered": stale_count,
        "duplicate_items_filtered": duplicate_count,
        "max_abs_score": _safe_float(strongest.get("score")),
        "strongest_headline": str(strongest.get("headline") or "").strip(),
        "latest_headline": str(events[-1].get("headline") or "").strip(),
        "events": events,
    }


def _build_recent_onchain_context(state: dict[str, Any]) -> dict[str, Any]:
    events = _source_events(state, "onchain")
    events, stale_count, duplicate_count = _filter_recent_events_by_ttl(
        state,
        events,
        ttl_seconds=_recent_ttl_seconds(state, "recentOnchainTtlSeconds", 7200),
    )
    if not events:
        return {
            "event_count": 0,
            "events": [],
            "summary": "no_recent_onchain",
            "stale_items_filtered": stale_count,
            "duplicate_items_filtered": duplicate_count,
        }
    inflow = sum(_safe_float(item.get("amountUsd")) for item in events if item.get("flow") == "exchange_inflow")
    outflow = sum(_safe_float(item.get("amountUsd")) for item in events if item.get("flow") == "exchange_outflow")
    net_flow = outflow - inflow
    direction = "net_outflow" if net_flow > 0 else "net_inflow" if net_flow < 0 else "balanced"
    return {
        "event_count": len(events),
        "stale_items_filtered": stale_count,
        "duplicate_items_filtered": duplicate_count,
        "total_inflow_usd": round(inflow, 4),
        "total_outflow_usd": round(outflow, 4),
        "net_flow_usd": round(net_flow, 4),
        "direction": direction,
        "events": events,
    }

def _build_market_context(state: dict[str, Any]) -> dict[str, Any]:
    feature_snapshot = state.get("feature_snapshot")
    if not isinstance(feature_snapshot, dict):
        feature_snapshot = {}
    event_bundle = state.get("event_bundle")
    if not isinstance(event_bundle, list):
        event_bundle = []

    latest_market_tick = next(
        (
            item
            for item in reversed(event_bundle)
            if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() == "market_tick"
        ),
        {},
    )
    latest_mark_price = next(
        (
            item
            for item in reversed(event_bundle)
            if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() == "mark_price"
        ),
        {},
    )
    latest_funding = next(
        (
            item
            for item in reversed(event_bundle)
            if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() == "funding_rate"
        ),
        {},
    )
    liquidation_events = [
        item
        for item in event_bundle
        if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() == "liquidation"
    ]
    largest_liquidation = max(
        liquidation_events,
        key=lambda item: _safe_float(item.get("notionalUsd") or item.get("notional_usd")),
        default={},
    )
    latest_market_metric = next(
        (
            item
            for item in reversed(event_bundle)
            if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() == "market_metric"
        ),
        {},
    )

    latest_trade_price = _safe_float(
        latest_market_metric.get("latest_trade_price")
        or feature_snapshot.get("latest_trade_price")
        or latest_market_tick.get("price")
        or feature_snapshot.get("last_price")
        or feature_snapshot.get("price")
    )
    mark_price = _safe_float(
        latest_mark_price.get("price")
        or feature_snapshot.get("mark_price")
        or feature_snapshot.get("markPrice")
    )
    latest_kline_close = _safe_float(
        latest_market_metric.get("latest_kline_close")
        or feature_snapshot.get("latest_kline_close")
    )
    market_tick_staleness_seconds = _safe_float(
        latest_market_metric.get("market_tick_staleness_seconds")
        or feature_snapshot.get("market_tick_staleness_seconds")
    )
    trade_tick_status = str(
        latest_market_metric.get("trade_tick_status")
        or feature_snapshot.get("trade_tick_status")
        or ("stale" if market_tick_staleness_seconds > 90 else "ready")
    ).strip()
    trade_tick_age_seconds = _safe_float(
        latest_market_metric.get("trade_tick_age_seconds")
        or feature_snapshot.get("trade_tick_age_seconds")
        or market_tick_staleness_seconds
    )
    effective_price = _safe_float(
        latest_market_metric.get("effective_price")
        or feature_snapshot.get("effective_price")
    )
    effective_price_source = str(
        latest_market_metric.get("effective_price_source")
        or feature_snapshot.get("effective_price_source")
        or ""
    ).strip()
    if effective_price <= 0:
        price_candidates = (
            (
                (mark_price, "mark_price"),
                (latest_kline_close, "kline_close"),
                (latest_trade_price, "trade"),
            )
            if trade_tick_status == "stale"
            else (
                (latest_trade_price, "trade"),
                (mark_price, "mark_price"),
                (latest_kline_close, "kline_close"),
            )
        )
        for candidate_price, candidate_source in price_candidates:
            if candidate_price > 0:
                effective_price = candidate_price
                effective_price_source = candidate_source
                break
    elif not effective_price_source:
        effective_price_source = "effective_price"
    latest_price = effective_price if effective_price > 0 else latest_trade_price
    stale_trade_price = _safe_float(
        latest_market_metric.get("stale_trade_price")
        or feature_snapshot.get("stale_trade_price")
        or (latest_trade_price if trade_tick_status == "stale" else 0.0)
    )
    mark_price_deviation_pct = 0.0
    if effective_price > 0 and mark_price > 0:
        mark_price_deviation_pct = ((mark_price - effective_price) / effective_price) * 100.0

    market_history = _normalize_market_history(state)
    period_summaries = _build_period_summaries(market_history)
    volume_price_signals = _volume_price_signals(period_summaries)
    kline_context = {
        "price_change_pct": feature_snapshot.get("kline_price_change_pct") or {},
        "quote_volume_ratio": feature_snapshot.get("kline_quote_volume_ratio") or {},
        "atr_pct": feature_snapshot.get("atr_pct") or {},
        "rsi_14": feature_snapshot.get("rsi_14") or {},
        "ema_trend": feature_snapshot.get("ema_trend") or {},
        "period_summaries": feature_snapshot.get("kline_period_summaries") or [],
        "volume_price_signals": feature_snapshot.get("kline_volume_price_signals") or [],
        "wyckoff_shortterm": feature_snapshot.get("wyckoff_shortterm") or {},
    }
    latest_kline_context = None
    for item in reversed(market_history):
        if isinstance(item.get("kline_context"), dict) and item.get("kline_context"):
            latest_kline_context = item.get("kline_context")
            break
    has_feature_snapshot_volume_signals = "kline_volume_price_signals" in feature_snapshot
    has_feature_snapshot_wyckoff_shortterm = "wyckoff_shortterm" in feature_snapshot
    if isinstance(latest_kline_context, dict):
        if not kline_context["period_summaries"]:
            kline_context["period_summaries"] = latest_kline_context.get("period_summaries") or []
        if not has_feature_snapshot_volume_signals and not kline_context["volume_price_signals"]:
            kline_context["volume_price_signals"] = latest_kline_context.get("volume_price_signals") or []
        if not has_feature_snapshot_wyckoff_shortterm and not kline_context["wyckoff_shortterm"]:
            kline_context["wyckoff_shortterm"] = latest_kline_context.get("wyckoff_shortterm") or {}
    kline_period_summaries = kline_context.get("period_summaries") if isinstance(kline_context, dict) else []
    kline_volume_price_signals = kline_context.get("volume_price_signals") if isinstance(kline_context, dict) else []
    if isinstance(kline_period_summaries, list) and kline_period_summaries:
        period_summaries = kline_period_summaries
    if isinstance(kline_period_summaries, list) and kline_period_summaries and isinstance(kline_volume_price_signals, list):
        volume_price_signals = kline_volume_price_signals
    wyckoff_shortterm = (
        kline_context.get("wyckoff_shortterm")
        if isinstance(kline_context, dict) and isinstance(kline_context.get("wyckoff_shortterm"), dict)
        else feature_snapshot.get("wyckoff_shortterm") or {}
    )
    derivatives_context = {
        "mark_price": _safe_float(latest_market_metric.get("mark_price") or mark_price),
        "mark_price_deviation_pct": _safe_float(
            latest_market_metric.get("mark_price_deviation_pct") or feature_snapshot.get("mark_price_deviation_pct")
        ),
        "funding_rate": _safe_float(latest_market_metric.get("funding_rate") or feature_snapshot.get("funding_rate")),
        "open_interest": _safe_float(latest_market_metric.get("open_interest") or feature_snapshot.get("open_interest")),
    }
    liquidation_context = {
        "notional_15m": _safe_float(
            latest_market_metric.get("liquidation_notional_15m") or feature_snapshot.get("liquidation_notional_15m")
        ),
        "notional_60m": _safe_float(
            latest_market_metric.get("liquidation_notional_60m") or feature_snapshot.get("liquidation_notional_60m")
        ),
        "notional_240m": _safe_float(
            latest_market_metric.get("liquidation_notional_240m") or feature_snapshot.get("liquidation_notional_240m")
        ),
        "largest_notional_usd": _safe_float(
            latest_market_metric.get("largest_liquidation_notional_usd")
            or largest_liquidation.get("notionalUsd")
            or largest_liquidation.get("notional_usd")
        ),
        "largest_side": str(
            latest_market_metric.get("largest_liquidation_side")
            or largest_liquidation.get("side")
            or largest_liquidation.get("liquidationSide")
            or ""
        ).strip(),
    }
    kline_series = _build_kline_series(state)
    wyckoff_15m_bars = feature_snapshot.get("wyckoff_15m_bars") if isinstance(feature_snapshot.get("wyckoff_15m_bars"), dict) else {}

    return {
        "symbol": str(state.get("symbol") or feature_snapshot.get("symbol") or "").strip(),
        "event_strength": str(state.get("event_strength") or "").strip(),
        "price_change_pct": _safe_float(feature_snapshot.get("price_change_pct")),
        "latest_price": latest_price,
        "latest_trade_price": latest_trade_price,
        "stale_trade_price": stale_trade_price,
        "trade_tick_status": trade_tick_status,
        "trade_tick_age_seconds": trade_tick_age_seconds,
        "effective_price": effective_price,
        "effective_price_source": effective_price_source,
        "market_tick_staleness_seconds": market_tick_staleness_seconds,
        "latest_kline_close": latest_kline_close,
        "latest_volume": _safe_float(latest_market_tick.get("volume") or latest_market_tick.get("baseVolume")),
        "latest_quote_volume": _safe_float(
            latest_market_tick.get("quoteVolume")
            or latest_market_tick.get("turnover")
            or latest_market_tick.get("quote_volume")
        ),
        "mark_price": mark_price,
        "mark_price_deviation_pct": round(mark_price_deviation_pct, 6),
        "funding_rate": _safe_float(
            latest_funding.get("funding_rate")
            or latest_funding.get("fundingRate")
            or feature_snapshot.get("funding_rate")
        ),
        "largest_liquidation_notional_usd": _safe_float(
            largest_liquidation.get("notionalUsd") or largest_liquidation.get("notional_usd")
        ),
        "largest_liquidation_side": str(
            largest_liquidation.get("side") or largest_liquidation.get("liquidationSide") or ""
        ).strip(),
        "largest_liquidation_price": _safe_float(largest_liquidation.get("price")),
        "source_event_types": [
            str(item.get("event_type") or "").strip().lower()
            for item in event_bundle
            if isinstance(item, dict) and str(item.get("event_type") or "").strip()
        ],
        "history_sample_count": len(market_history),
        "period_summaries": period_summaries,
        "volume_price_signals": volume_price_signals,
        "wyckoff_context": _wyckoff_context(market_history, period_summaries),
        "wyckoff_shortterm": wyckoff_shortterm,
        "wyckoff_15m_bars": wyckoff_15m_bars,
        "position_risk_context": feature_snapshot.get("position_risk_context") or {},
        "kline_context": kline_context,
        "derivatives_context": derivatives_context,
        "liquidation_context": liquidation_context,
        "kline_series": kline_series,
        "snapshot_market_fields": {
            key: feature_snapshot[key]
            for key in (
                "price_change_pct",
                "price_acceleration_pct",
                "funding_rate",
                "mark_price_deviation_pct",
                "volume_change_pct",
                "volume_ratio",
                "open_interest_change_pct",
                "liquidation_notional_usd",
                "effective_price",
                "effective_price_source",
                "market_tick_staleness_seconds",
            )
            if key in feature_snapshot
        },
    }


def _safe_memory_payload(state: dict[str, Any], key: str) -> dict[str, Any]:
    value = state.get(key)
    return value if isinstance(value, dict) else {}


_PROMPT_SUPERVISOR_DECISION_WINDOW_SECONDS = 7200


def _normalize_memory_json_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return text
    return parsed if isinstance(parsed, (dict, list)) else str(parsed).strip()


def _compact_memory_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        text = f"{value:.8f}".rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value).strip()


def _memory_detail_parts(prefix: str, value: Any) -> list[str]:
    normalized = _normalize_memory_json_value(value)
    if isinstance(normalized, dict):
        parts = [
            f"{key}={_compact_memory_text(item_value)}"
            for key, item_value in normalized.items()
            if _compact_memory_text(item_value)
        ]
        return [f"{prefix}={', '.join(parts)}"] if parts else []
    if isinstance(normalized, list):
        parts = [_compact_memory_text(item_value) for item_value in normalized if _compact_memory_text(item_value)]
        return [f"{prefix}={'; '.join(parts)}"] if parts else []
    text = _compact_memory_text(normalized)
    return [f"{prefix}={text}"] if text else []


def _prompt_experience_text(item: dict[str, Any]) -> str:
    lesson = str(item.get("lesson_text") or item.get("lessonText") or "").strip()
    tags = [
        str(tag).strip()
        for tag in (item.get("event_tags") or item.get("eventTags") or [])
        if str(tag).strip()
    ]
    parts: list[str] = []
    if lesson:
        parts.append(lesson)
    if tags:
        parts.append(f"tags={', '.join(tags)}")
    parts.extend(_memory_detail_parts("evidence", item.get("evidence_json") or item.get("evidenceJson") or item.get("evidence")))
    parts.extend(_memory_detail_parts("outcome", item.get("outcome_json") or item.get("outcomeJson") or item.get("outcome")))
    quality_score = item.get("quality_score")
    if quality_score in (None, ""):
        quality_score = item.get("qualityScore")
    confidence = item.get("confidence")
    if quality_score not in (None, ""):
        parts.append(f"quality_score={_compact_memory_text(_safe_float(quality_score))}")
    if confidence not in (None, ""):
        parts.append(f"confidence={_compact_memory_text(_safe_float(confidence))}")
    return " | ".join(part for part in parts if part)


def _prompt_experience_item(item: dict[str, Any]) -> dict[str, Any]:
    memory_id = item.get("id")
    if memory_id is None:
        memory_id = item.get("memory_id") or item.get("memoryId")
    lesson = str(item.get("lesson_text") or item.get("lessonText") or "").strip()
    tags = [
        str(tag).strip()
        for tag in (item.get("event_tags") or item.get("eventTags") or [])
        if str(tag).strip()
    ]
    prompt_item: dict[str, Any] = {
        "memory_id": memory_id,
        "agent_code": str(item.get("agent_code") or item.get("agentCode") or "").strip(),
        "memory_type": str(item.get("memory_type") or item.get("memoryType") or "").strip(),
        "lesson": lesson,
        "tags": tags,
        "quality_score": _safe_float(item.get("quality_score") or item.get("qualityScore")),
        "confidence": _safe_float(item.get("confidence")),
        "experience_text": _prompt_experience_text(item),
    }
    source_trace_id = str(item.get("source_trace_id") or item.get("sourceTraceId") or "").strip()
    created_at = str(item.get("created_at") or item.get("createdAt") or "").strip()
    if source_trace_id:
        prompt_item["source_trace_id"] = source_trace_id
    if created_at:
        prompt_item["created_at"] = created_at
    evidence = _normalize_memory_json_value(item.get("evidence_json") or item.get("evidenceJson") or item.get("evidence"))
    outcome = _normalize_memory_json_value(item.get("outcome_json") or item.get("outcomeJson") or item.get("outcome"))
    if isinstance(evidence, (dict, list)) and evidence:
        prompt_item["evidence"] = evidence
    if isinstance(outcome, (dict, list)) and outcome:
        prompt_item["outcome"] = outcome
    return prompt_item


def build_prompt_long_term_memory(state: dict[str, Any]) -> dict[str, Any]:
    memory = _safe_memory_payload(state, "long_term_memory")
    items = memory.get("items")
    if not isinstance(items, list):
        items = []
    experience_items = [_prompt_experience_item(item) for item in items if isinstance(item, dict)]
    payload: dict[str, Any] = {
        "status": str(memory.get("status") or "").strip(),
        "reason": str(memory.get("reason") or "").strip(),
        "selected_count": int(memory.get("selected_count") or len(experience_items)),
        "max_items": int(memory.get("max_items") or len(experience_items)),
        "experience_items": experience_items,
    }
    used_memory_ids = (_safe_memory_payload(state, "memory_usage").get("used_memory_ids") or [])
    if isinstance(used_memory_ids, list):
        payload["used_memory_ids"] = list(used_memory_ids)
    return {
        key: value
        for key, value in payload.items()
        if value not in ("", None) and not (isinstance(value, list) and not value and key not in {"experience_items", "used_memory_ids"})
    }


def _prompt_supervisor_decision_window_seconds(short_term_memory: dict[str, Any]) -> int:
    bucket = short_term_memory.get("supervisor_decision")
    if isinstance(bucket, dict):
        window_seconds = _safe_int(bucket.get("window_seconds"))
        if window_seconds:
            return window_seconds
    ttl_policy = short_term_memory.get("ttl_policy")
    if isinstance(ttl_policy, dict):
        window_seconds = _safe_int(ttl_policy.get("supervisor_decision"))
        if window_seconds:
            return window_seconds
    return _PROMPT_SUPERVISOR_DECISION_WINDOW_SECONDS


def _prompt_supervisor_decision_item(item: dict[str, Any]) -> dict[str, Any]:
    payload = dict(item)
    if "action" not in payload:
        content = item.get("content")
        if isinstance(content, dict):
            payload = dict(content)
        else:
            for key in ("contentJson", "content_json"):
                parsed = _normalize_memory_json_value(item.get(key))
                if isinstance(parsed, dict):
                    payload = dict(parsed)
                    break
    action = str(payload.get("action") or "SKIP").strip().upper() or "SKIP"
    side = str(payload.get("side") or "").strip()
    if not side or side == "flat":
        if "LONG" in action:
            side = "long"
        elif "SHORT" in action:
            side = "short"
        else:
            side = "flat"
    holding_window = str(payload.get("holding_window") or payload.get("holdingWindow") or "").strip() or "15m-4h"
    invalidation = str(payload.get("invalidation") or "").strip()
    if not invalidation and action in {"HOLD", "SKIP"}:
        invalidation = "no_trade_condition"
    result: dict[str, Any] = {
        "action": action,
        "side": side,
        "confidence": int(_safe_float(payload.get("confidence"))),
        "size_hint": _safe_float(payload.get("size_hint") or payload.get("sizeHint")),
        "leverage_hint": max(int(_safe_float(payload.get("leverage_hint") or payload.get("leverageHint") or 1)), 1),
        "holding_window": holding_window,
        "invalidation": invalidation,
        "summary_reason": str(payload.get("summary_reason") or item.get("summary_text") or "").strip(),
    }
    for extra_key in ("model_code", "model_provider"):
        extra_value = str(payload.get(extra_key) or item.get(extra_key) or "").strip()
        if extra_value:
            result[extra_key] = extra_value
    return result


def build_prompt_short_term_memory(state: dict[str, Any]) -> dict[str, Any]:
    base = _safe_memory_payload(state, "short_term_memory")
    prompt_memory = dict(base)
    recent_supervisor_decisions = state.get("recent_supervisor_decisions")
    if isinstance(recent_supervisor_decisions, list) and recent_supervisor_decisions:
        supervisor_items = [
            _prompt_supervisor_decision_item(item)
            for item in recent_supervisor_decisions
            if isinstance(item, dict)
        ]
    else:
        supervisor_bucket = base.get("supervisor_decision")
        raw_items = supervisor_bucket.get("items") if isinstance(supervisor_bucket, dict) else []
        supervisor_items = [
            _prompt_supervisor_decision_item(item)
            for item in raw_items
            if isinstance(item, dict)
        ]
    if supervisor_items:
        window_seconds = _prompt_supervisor_decision_window_seconds(base)
        prompt_memory["supervisor_decision"] = {
            "window_seconds": window_seconds,
            "items": supervisor_items,
            "sample_count": len(supervisor_items),
        }
        ttl_policy = prompt_memory.get("ttl_policy")
        ttl_policy = dict(ttl_policy) if isinstance(ttl_policy, dict) else {}
        ttl_policy["supervisor_decision"] = window_seconds
        prompt_memory["ttl_policy"] = ttl_policy
    return prompt_memory


def _prompt_short_term_counts(short_term_memory: dict[str, Any]) -> dict[str, int]:
    return {
        key: int((short_term_memory.get(key) or {}).get("sample_count") or 0)
        for key in ("market", "news", "onchain", "social", "supervisor_decision")
    }


def build_prompt_memory_usage(
    state: dict[str, Any],
    *,
    short_term_memory: dict[str, Any] | None = None,
    long_term_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    usage = dict(_safe_memory_payload(state, "memory_usage"))
    prompt_short_term_memory = short_term_memory if isinstance(short_term_memory, dict) else build_prompt_short_term_memory(state)
    prompt_long_term_memory = long_term_memory if isinstance(long_term_memory, dict) else build_prompt_long_term_memory(state)
    usage["short_term_counts"] = _prompt_short_term_counts(prompt_short_term_memory)
    usage["long_term_count"] = int(prompt_long_term_memory.get("selected_count") or len(prompt_long_term_memory.get("experience_items") or []))
    if not str(usage.get("trace_id") or "").strip():
        usage["trace_id"] = str(state.get("trace_id") or "").strip()
    if not str(usage.get("symbol") or "").strip():
        usage["symbol"] = str(state.get("symbol") or "").strip()
    return usage


def synchronize_prompt_memory_state(state: dict[str, Any]) -> None:
    prompt_short_term_memory = build_prompt_short_term_memory(state)
    state["short_term_memory"] = prompt_short_term_memory
    state["memory_usage"] = build_prompt_memory_usage(state, short_term_memory=prompt_short_term_memory)


_PROMPT_INTERNAL_STRATEGY_KEYS = {
    "ai_model_config",
    "prompt_bindings",
    "agent_profiles",
    "resolved_agent_configs",
}


def _sanitize_prompt_position_guard(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    sanitized = dict(value)
    sanitized.pop("stop_loss_pct", None)
    sanitized.pop("stopLossPct", None)
    sanitized.pop("take_profit_pct", None)
    sanitized.pop("takeProfitPct", None)
    return sanitized


def build_prompt_strategy_context(state: dict[str, Any]) -> dict[str, Any]:
    strategy_context = state.get("strategy_context")
    if not isinstance(strategy_context, dict):
        return {}
    payload = {
        key: value
        for key, value in strategy_context.items()
        if key not in _PROMPT_INTERNAL_STRATEGY_KEYS
    }
    if "position_guard" in payload:
        payload["position_guard"] = _sanitize_prompt_position_guard(payload.get("position_guard"))
    if "positionGuard" in payload:
        payload["positionGuard"] = _sanitize_prompt_position_guard(payload.get("positionGuard"))
    return payload



def _agent_domain(agent_code: str) -> str:
    normalized = str(agent_code or "").strip().lower()
    if "market" in normalized:
        return "market"
    if "news" in normalized:
        return "news"
    if "onchain" in normalized:
        return "onchain"
    if "social" in normalized:
        return "social"
    return ""


def _domain_event_types(domain: str) -> set[str]:
    if domain == "market":
        return {"market_tick", "mark_price", "funding_rate", "open_interest", "liquidation", "position_risk"}
    if domain == "news":
        return {"news"}
    if domain == "onchain":
        return {"onchain"}
    if domain == "social":
        return {"social"}
    return set()


def _filter_events_for_domain(state: dict[str, Any], domain: str) -> list[dict[str, Any]]:
    event_types = _domain_event_types(domain)
    events = state.get("event_bundle")
    if not isinstance(events, list) or not event_types:
        return []
    filtered = [
        dict(item)
        for item in events
        if isinstance(item, dict) and str(item.get("event_type") or "").strip().lower() in event_types
    ]
    if domain == "news":
        filtered, _, _ = _filter_recent_events_by_ttl(
            state,
            filtered,
            ttl_seconds=_recent_ttl_seconds(state, "recentNewsTtlSeconds", 7200),
        )
    elif domain == "onchain":
        filtered, _, _ = _filter_recent_events_by_ttl(
            state,
            filtered,
            ttl_seconds=_recent_ttl_seconds(state, "recentOnchainTtlSeconds", 7200),
        )
    return filtered


def _domain_state(state: dict[str, Any], domain: str) -> dict[str, Any]:
    scoped = dict(state)
    if domain:
        scoped["event_bundle"] = _filter_events_for_domain(state, domain)
    return scoped


def _domain_short_term_memory(state: dict[str, Any], domain: str) -> dict[str, Any]:
    memory = _safe_memory_payload(state, "short_term_memory")
    if not domain:
        return memory
    scoped: dict[str, Any] = {}
    if domain in memory:
        scoped[domain] = memory.get(domain)
    if "ttl_policy" in memory:
        ttl_policy = memory.get("ttl_policy")
        if isinstance(ttl_policy, dict):
            scoped["ttl_policy"] = {domain: ttl_policy.get(domain)} if domain in ttl_policy else {}
    return scoped


def _empty_recent_context(domain: str) -> dict[str, Any]:
    return {"event_count": 0, "events": [], "summary": f"not_{domain}_agent_scope"}

def build_supervisor_render_context(state: dict[str, Any]) -> dict[str, Any]:
    runtime_config = state.get("runtime_config") or {}
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    risk_limits = {
        "max_position_ratio": runtime_config.get("max_position_ratio"),
        "max_daily_loss": runtime_config.get("max_daily_loss"),
        "max_consecutive_failures": runtime_config.get("max_consecutive_failures"),
        "live_order_requires_healthy_account": runtime_config.get("live_order_requires_healthy_account"),
    }
    current_time = resolve_prompt_current_time(state)
    prompt_short_term_memory = build_prompt_short_term_memory(state)
    prompt_long_term_memory = build_prompt_long_term_memory(state)
    prompt_memory_usage = build_prompt_memory_usage(
        state,
        short_term_memory=prompt_short_term_memory,
        long_term_memory=prompt_long_term_memory,
    )
    recent_supervisor_decisions = state.get("recent_supervisor_decisions")
    if not isinstance(recent_supervisor_decisions, list) or not recent_supervisor_decisions:
        recent_supervisor_decisions = (prompt_short_term_memory.get("supervisor_decision") or {}).get("items") or []
    return {
        "trace_id": str(state.get("trace_id") or "").strip(),
        "symbol": str(state.get("symbol") or "").strip(),
        "exchange": str(state.get("exchange") or "").strip(),
        "event_strength": str(state.get("event_strength") or "").strip(),
        "current_position_side": str(state.get("current_position_side") or "flat").strip(),
        "current_position_quantity": state.get("current_position_quantity", 0.0) or 0.0,
        "current_position_notional": state.get("current_position_notional", 0.0) or 0.0,
        "current_position_opened_at": state.get("current_position_opened_at") or "",
        "current_time": current_time,
        "current_position_holding_minutes": resolve_current_position_holding_minutes(
            {**state, "current_time": current_time}
        ),
        "account_equity": state.get("account_equity", 0.0) or 0.0,
        "daily_pnl": state.get("daily_pnl", 0.0) or 0.0,
        "strategy_context_json": _json_dumps(build_prompt_strategy_context(state)),
        "deliberation_policy_json": _json_dumps(state.get("deliberation_policy") or {}),
        "agent_messages_json": _json_dumps(state.get("agent_messages") or []),
        "deliberation_summary": str(state.get("deliberation_summary") or "").strip(),
        "deliberation_referee_review_json": _json_dumps(state.get("deliberation_referee_review") or {}),
        "recent_news_context_json": _json_dumps(_build_recent_news_context(state)),
        "recent_onchain_context_json": _json_dumps(_build_recent_onchain_context(state)),
        "market_view_json": _json_dumps(state.get("market_view") or {}),
        "news_view_json": _json_dumps(state.get("news_view") or {}),
        "onchain_view_json": _json_dumps(state.get("onchain_view") or {}),
        "social_view_json": _json_dumps(state.get("social_view") or {}),
        "runtime_risk_limits_json": _json_dumps(risk_limits),
        "market_source_status": str(state.get("market_source_status") or "").strip(),
        "market_source_context_json": _json_dumps(state.get("market_source_context") or {}),
        "market_context_json": _json_dumps(_build_market_context(state)),
        "position_risk_context_json": _json_dumps(
            ((state.get("feature_snapshot") or {}).get("position_risk_context") if isinstance(state.get("feature_snapshot"), dict) else {}) or {}
        ),
        "short_term_memory_json": _json_dumps(prompt_short_term_memory),
        "long_term_memory_json": _json_dumps(prompt_long_term_memory),
        "memory_usage_json": _json_dumps(prompt_memory_usage),
        "previous_supervisor_decisions_json": _json_dumps(recent_supervisor_decisions),
    }


def build_agent_render_context(
    state: dict[str, Any],
    *,
    agent_code: str,
    rule_view: dict[str, Any] | None = None,
) -> dict[str, Any]:
    domain = _agent_domain(agent_code)
    scoped_state = _domain_state(state, domain)
    prompt_long_term_memory = build_prompt_long_term_memory(state)
    prompt_memory_usage = build_prompt_memory_usage(state)
    return {
        "trace_id": str(state.get("trace_id") or "").strip(),
        "agent_code": str(agent_code or "").strip(),
        "symbol": str(state.get("symbol") or "").strip(),
        "exchange": str(state.get("exchange") or "").strip(),
        "mode": str(state.get("mode") or "").strip(),
        "event_strength": str(state.get("event_strength") or "").strip(),
        "feature_snapshot_json": _json_dumps(state.get("feature_snapshot") or {}),
        "event_bundle_json": _json_dumps(scoped_state.get("event_bundle") or []),
        "recent_news_context_json": _json_dumps(
            _build_recent_news_context(state) if domain == "news" else _empty_recent_context("news")
        ),
        "recent_onchain_context_json": _json_dumps(
            _build_recent_onchain_context(state) if domain == "onchain" else _empty_recent_context("onchain")
        ),
        "strategy_context_json": _json_dumps(build_prompt_strategy_context(state)),
        "market_context_json": _json_dumps(_build_market_context(state) if domain == "market" else {}),
        "position_risk_context_json": _json_dumps(
            ((state.get("feature_snapshot") or {}).get("position_risk_context") if isinstance(state.get("feature_snapshot"), dict) else {}) or {}
        ),
        "market_view_json": _json_dumps(state.get("market_view") or {} if domain == "market" else {}),
        "news_view_json": _json_dumps(state.get("news_view") or {} if domain == "news" else {}),
        "onchain_view_json": _json_dumps(state.get("onchain_view") or {} if domain == "onchain" else {}),
        "social_view_json": _json_dumps(state.get("social_view") or {} if domain == "social" else {}),
        "short_term_memory_json": _json_dumps(_domain_short_term_memory(state, domain)),
        "long_term_memory_json": _json_dumps(prompt_long_term_memory),
        "memory_usage_json": _json_dumps(prompt_memory_usage),
        "rule_view_json": _json_dumps(rule_view or {}),
    }
