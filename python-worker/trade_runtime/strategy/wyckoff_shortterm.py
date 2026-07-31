from __future__ import annotations

from typing import Any


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


_DEFAULT_WYCKOFF_SHORTTERM_CONFIG = {
    "enabled": True,
    "min15mBars": 8,
    "effortLookbackBars": 4,
    "breakoutChangePct": 0.15,
    "breakoutVolumeRatio": 0.9,
    "confirmedBreakoutChangePct": 0.35,
    "confirmedBreakoutVolumeRatio": 1.2,
    "springChangePct": 0.08,
    "springVolumeRatio": 0.9,
    "higherTimeframeConflictPct": 0.15,
    "higherTimeframeConfirmPct": 0.35,
    "rangeBalanceChangePct": 0.4,
    "rangeBalanceRangePct": 2.0,
    "markDeviationPenaltyPct": 0.3,
    "requireRetestForReady": True,
    "retestMaxDistancePct": 0.25,
    "maxReadyExtensionPct": 0.9,
    "trapVolumeRatio": 1.8,
    "trapWickRatio": 0.45,
    "trapCooldownBars": 2,
}


def _pick_config(config: dict[str, Any], key: str, snake_key: str | None = None) -> Any:
    for candidate in (key, snake_key):
        if not candidate:
            continue
        value = config.get(candidate)
        if value not in (None, ""):
            return value
    return _DEFAULT_WYCKOFF_SHORTTERM_CONFIG[key]


def _config_bool(config: dict[str, Any], key: str, snake_key: str | None = None) -> bool:
    value = _pick_config(config, key, snake_key)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def _config_float(config: dict[str, Any], key: str, snake_key: str | None = None) -> float:
    return _safe_float(_pick_config(config, key, snake_key))


def _config_int(config: dict[str, Any], key: str, snake_key: str | None = None) -> int:
    try:
        return int(_pick_config(config, key, snake_key))
    except (TypeError, ValueError):
        return int(_DEFAULT_WYCKOFF_SHORTTERM_CONFIG[key])


def _normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return dict(_DEFAULT_WYCKOFF_SHORTTERM_CONFIG)
    return {**_DEFAULT_WYCKOFF_SHORTTERM_CONFIG, **config}


def _time_key(candle: dict[str, Any]) -> float:
    raw = candle.get("open_time") or candle.get("event_time") or candle.get("timestamp") or candle.get("ts") or 0
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _sort_candles(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted([item for item in candles if isinstance(item, dict)], key=_time_key)


def _open(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("open") or candle.get("o"))


def _high(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("high") or candle.get("h"))


def _low(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("low") or candle.get("l"))


def _close(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("close") or candle.get("c"))


def _quote_volume(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("quote_volume") or candle.get("quoteVolume") or candle.get("turnover"))


def _aggregate_window(candles: list[dict[str, Any]], *, bars: int, window: str) -> dict[str, Any]:
    ordered = _sort_candles(candles)
    if len(ordered) < bars:
        return {"window": window, "status": "insufficient", "sample_count": len(ordered)}
    current = ordered[-bars:]
    previous = ordered[-bars * 2 : -bars] if len(ordered) >= bars * 2 else []
    start_price = _open(current[0])
    end_price = _close(current[-1])
    high_price = max(_high(item) for item in current)
    low_price = min(_low(item) for item in current)
    quote_volume_sum = sum(_quote_volume(item) for item in current)
    previous_quote_volume_sum = sum(_quote_volume(item) for item in previous)
    quote_volume_ratio = 0.0
    if quote_volume_sum > 0 and previous_quote_volume_sum > 0:
        quote_volume_ratio = quote_volume_sum / previous_quote_volume_sum
    price_change_pct = 0.0
    range_pct = 0.0
    if start_price > 0:
        price_change_pct = ((end_price - start_price) / start_price) * 100.0
        range_pct = ((high_price - low_price) / start_price) * 100.0
    return {
        "window": window,
        "source": "kline_ohlcv",
        "sample_count": len(current),
        "start_price": round(start_price, 8),
        "end_price": round(end_price, 8),
        "high_price": round(high_price, 8),
        "low_price": round(low_price, 8),
        "price_change_pct": round(price_change_pct, 6),
        "range_pct": round(range_pct, 6),
        "quote_volume_sum": round(quote_volume_sum, 6),
        "previous_quote_volume_sum": round(previous_quote_volume_sum, 6),
        "quote_volume_ratio": round(quote_volume_ratio, 6),
    }


def _breakout_extension_pct(latest_close: float, boundary: float) -> float:
    if boundary <= 0:
        return 0.0
    return abs((latest_close - boundary) / boundary) * 100.0


def _upper_wick_ratio(candle: dict[str, Any]) -> float:
    high_price = _high(candle)
    low_price = _low(candle)
    body_top = max(_open(candle), _close(candle))
    candle_range = high_price - low_price
    if candle_range <= 0:
        return 0.0
    return max(0.0, (high_price - body_top) / candle_range)


def _lower_wick_ratio(candle: dict[str, Any]) -> float:
    high_price = _high(candle)
    low_price = _low(candle)
    body_bottom = min(_open(candle), _close(candle))
    candle_range = high_price - low_price
    if candle_range <= 0:
        return 0.0
    return max(0.0, (body_bottom - low_price) / candle_range)


def _recent_retest_confirmed(
    candles: list[dict[str, Any]],
    *,
    boundary: float,
    direction: str,
    max_distance_pct: float,
    cooldown_bars: int,
) -> bool:
    if boundary <= 0:
        return False
    if cooldown_bars <= 0:
        return True
    recent = _sort_candles(candles)[-cooldown_bars:]
    for candle in recent:
        if direction == "long":
            distance_pct = abs((_low(candle) - boundary) / boundary) * 100.0
            if distance_pct <= max_distance_pct and _close(candle) >= boundary:
                return True
        if direction == "short":
            distance_pct = abs((_high(candle) - boundary) / boundary) * 100.0
            if distance_pct <= max_distance_pct and _close(candle) <= boundary:
                return True
    return False


def _trap_risk(
    *,
    latest_candle: dict[str, Any],
    direction: str,
    latest_volume_ratio: float,
    trap_volume_ratio: float,
    trap_wick_ratio: float,
) -> tuple[str, str]:
    wick_ratio = _upper_wick_ratio(latest_candle) if direction == "long" else _lower_wick_ratio(latest_candle)
    if latest_volume_ratio >= trap_volume_ratio and wick_ratio >= trap_wick_ratio:
        return "high", f"wick_ratio={wick_ratio:.3f}, volume_ratio={latest_volume_ratio:.3f}"
    if latest_volume_ratio >= trap_volume_ratio or wick_ratio >= trap_wick_ratio:
        return "medium", f"wick_ratio={wick_ratio:.3f}, volume_ratio={latest_volume_ratio:.3f}"
    return "low", f"wick_ratio={wick_ratio:.3f}, volume_ratio={latest_volume_ratio:.3f}"


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def _window_price_change_pct(candles: list[dict[str, Any]], *, bars: int) -> float:
    ordered = _sort_candles(candles)
    if len(ordered) < bars or bars <= 0:
        return 0.0
    start_price = _open(ordered[-bars])
    end_price = _close(ordered[-1])
    if start_price <= 0:
        return 0.0
    return round(((end_price - start_price) / start_price) * 100.0, 4)


def _analyze_effort_result_series(candles: list[dict[str, Any]], lookback: int = 4) -> dict[str, Any]:
    """
    Analyze effort-result relationship across multiple candles.

    Wyckoff effort-result principle:
    - effort_without_result: Volume expands but price doesn't move = potential reversal
    - absorption: Small range consolidation with drying volume = accumulation/distribution
    - price_move_volume_divergence: Price moves significantly with low volume = weak move
    - aligned: Price and volume move together = healthy trend

    Args:
        candles: Sorted list of candle data (oldest first)
        lookback: Number of candles to analyze

    Returns:
        dict with effort_result, effort_score, and evidence
    """
    if len(candles) < lookback + 1:
        return {"effort_result": "insufficient_data", "effort_score": 0.0, "evidence": "not_enough_candles"}

    recent = candles[-lookback:]

    # Calculate cumulative price change and volume
    total_change_pct = 0.0
    total_volume = 0.0

    for candle in recent:
        o = _open(candle)
        c = _close(candle)
        v = _quote_volume(candle)

        if o > 0:
            total_change_pct += (c - o) / o * 100
        total_volume += v

    # Calculate previous period average volume for comparison
    prev_candles = candles[-lookback * 2:-lookback] if len(candles) >= lookback * 2 else candles[:-lookback]
    prev_volume_avg = 0.0
    if prev_candles:
        prev_volume_avg = sum(_quote_volume(c) for c in prev_candles) / len(prev_candles)

    volume_ratio = total_volume / prev_volume_avg if prev_volume_avg > 0 else 1.0

    # Pattern 1: Effort without result - volume expands but price barely moves
    if volume_ratio >= 1.3 and abs(total_change_pct) <= 0.3:
        return {
            "effort_result": "effort_without_result",
            "effort_score": -0.6,
            "evidence": f"volume_ratio={volume_ratio:.2f}, price_change={total_change_pct:.3f}%"
        }

    # Pattern 2: Absorption - small range consolidation with drying volume
    changes = []
    for candle in recent:
        o = _open(candle)
        c = _close(candle)
        if o > 0:
            changes.append(abs((c - o) / o * 100))

    if changes and all(ch < 0.2 for ch in changes) and volume_ratio < 0.8:
        return {
            "effort_result": "absorption",
            "effort_score": 0.3,
            "evidence": "small_range_consolidation_volume_drying"
        }

    # Pattern 3: Price move with volume divergence - price moves but volume contracts
    if abs(total_change_pct) >= 0.5 and 0 < volume_ratio <= 0.7:
        return {
            "effort_result": "price_move_volume_divergence",
            "effort_score": -0.4,
            "evidence": f"price_change={total_change_pct:.3f}%, volume_ratio={volume_ratio:.2f}"
        }

    # Pattern 4: Aligned - price and volume move together
    if abs(total_change_pct) >= 0.2 and volume_ratio >= 1.0:
        direction = "bullish" if total_change_pct > 0 else "bearish"
        return {
            "effort_result": "aligned",
            "effort_score": 0.5,
            "evidence": f"{direction}_move_with_volume_change={total_change_pct:.3f}%"
        }

    return {
        "effort_result": "neutral",
        "effort_score": 0.0,
        "evidence": ""
    }


def analyze_wyckoff_shortterm(
    candles_by_interval: dict[str, list[dict[str, Any]]] | None,
    *,
    latest_price: float = 0.0,
    mark_price: float = 0.0,
    funding_rate: float = 0.0,
    oi_change_pct: float = 0.0,
    price_source: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_config = _normalize_config(config)
    if not _config_bool(resolved_config, "enabled"):
        return {
            "status": "disabled",
            "phase": "disabled",
            "entry_bias": "neutral",
            "trigger": "none",
            "trade_readiness": "avoid",
            "confidence": 0.0,
            "no_trade_reason": "wyckoff_shortterm_disabled",
        }
    if not isinstance(candles_by_interval, dict):
        candles_by_interval = {}
    fifteen = _sort_candles(candles_by_interval.get("15m") or [])
    min_15m_bars = max(1, _config_int(resolved_config, "min15mBars", "min_15m_bars"))
    if len(fifteen) < min_15m_bars:
        return {
            "status": "insufficient",
            "phase": "context_insufficient",
            "entry_bias": "neutral",
            "trigger": "none",
            "trade_readiness": "avoid",
            "confidence": 0.0,
            "no_trade_reason": "not_enough_15m_bars",
        }

    latest_bar = _aggregate_window(fifteen, bars=1, window="15m_bar")
    rolling_hour = _aggregate_window(fifteen, bars=4, window="60m_rollup")
    prior_range = fifteen[-5:-1]
    range_high = max(_high(item) for item in prior_range)
    range_low = min(_low(item) for item in prior_range)
    latest_close = _safe_float(latest_bar.get("end_price")) or _close(fifteen[-1])
    latest_low = _safe_float(latest_bar.get("low_price"))
    latest_high = _safe_float(latest_bar.get("high_price"))
    latest_bar_change_pct = _safe_float(latest_bar.get("price_change_pct"))
    latest_volume_ratio = _safe_float(latest_bar.get("quote_volume_ratio"))
    rolling_hour_change_pct = _safe_float(rolling_hour.get("price_change_pct"))
    rolling_hour_range_pct = _safe_float(rolling_hour.get("range_pct"))
    one_hour = _sort_candles(candles_by_interval.get("1h") or candles_by_interval.get("60m") or [])
    one_hour_change_pct = _window_price_change_pct(one_hour, bars=min(len(one_hour), 4)) if one_hour else 0.0
    higher_timeframe_change_pct = one_hour_change_pct if one_hour else rolling_hour_change_pct
    effective_price = _safe_float(latest_price) or latest_close
    mark_deviation_pct = 0.0
    if effective_price > 0 and mark_price > 0:
        mark_deviation_pct = ((mark_price - effective_price) / effective_price) * 100.0

    breakout_change_pct = _config_float(resolved_config, "breakoutChangePct", "breakout_change_pct")
    breakout_volume_ratio = _config_float(resolved_config, "breakoutVolumeRatio", "breakout_volume_ratio")
    confirmed_breakout_change_pct = _config_float(resolved_config, "confirmedBreakoutChangePct", "confirmed_breakout_change_pct")
    confirmed_breakout_volume_ratio = _config_float(resolved_config, "confirmedBreakoutVolumeRatio", "confirmed_breakout_volume_ratio")
    spring_change_pct = _config_float(resolved_config, "springChangePct", "spring_change_pct")
    spring_volume_ratio = _config_float(resolved_config, "springVolumeRatio", "spring_volume_ratio")
    higher_timeframe_conflict_pct = _config_float(resolved_config, "higherTimeframeConflictPct", "higher_timeframe_conflict_pct")
    higher_timeframe_confirm_pct = _config_float(resolved_config, "higherTimeframeConfirmPct", "higher_timeframe_confirm_pct")
    range_balance_change_pct = _config_float(resolved_config, "rangeBalanceChangePct", "range_balance_change_pct")
    range_balance_range_pct = _config_float(resolved_config, "rangeBalanceRangePct", "range_balance_range_pct")
    mark_deviation_penalty_pct = _config_float(resolved_config, "markDeviationPenaltyPct", "mark_deviation_penalty_pct")
    require_retest_for_ready = _config_bool(resolved_config, "requireRetestForReady", "require_retest_for_ready")
    retest_max_distance_pct = _config_float(resolved_config, "retestMaxDistancePct", "retest_max_distance_pct")
    max_ready_extension_pct = _config_float(resolved_config, "maxReadyExtensionPct", "max_ready_extension_pct")
    trap_volume_ratio = _config_float(resolved_config, "trapVolumeRatio", "trap_volume_ratio")
    trap_wick_ratio = _config_float(resolved_config, "trapWickRatio", "trap_wick_ratio")
    trap_cooldown_bars = max(0, _config_int(resolved_config, "trapCooldownBars", "trap_cooldown_bars"))

    breakout_long = latest_close > range_high and latest_bar_change_pct >= breakout_change_pct and latest_volume_ratio >= breakout_volume_ratio
    breakdown_short = latest_close < range_low and latest_bar_change_pct <= -breakout_change_pct and latest_volume_ratio >= breakout_volume_ratio
    confirmed_breakout_long = breakout_long and latest_bar_change_pct >= confirmed_breakout_change_pct and latest_volume_ratio >= confirmed_breakout_volume_ratio
    confirmed_breakdown_short = breakdown_short and latest_bar_change_pct <= -confirmed_breakout_change_pct and latest_volume_ratio >= confirmed_breakout_volume_ratio
    spring_long = latest_low < range_low and latest_close > range_low and latest_bar_change_pct > spring_change_pct and latest_volume_ratio >= spring_volume_ratio
    upthrust_short = latest_high > range_high and latest_close < range_high and latest_bar_change_pct < -spring_change_pct and latest_volume_ratio >= spring_volume_ratio
    long_retest_confirmed = not require_retest_for_ready or _recent_retest_confirmed(
        fifteen,
        boundary=range_high,
        direction="long",
        max_distance_pct=retest_max_distance_pct,
        cooldown_bars=trap_cooldown_bars,
    )
    short_retest_confirmed = not require_retest_for_ready or _recent_retest_confirmed(
        fifteen,
        boundary=range_low,
        direction="short",
        max_distance_pct=retest_max_distance_pct,
        cooldown_bars=trap_cooldown_bars,
    )
    breakout_extension_pct = _breakout_extension_pct(latest_close, range_high) if breakout_long else 0.0
    breakdown_extension_pct = _breakout_extension_pct(latest_close, range_low) if breakdown_short else 0.0

    # Multi-candle effort-result analysis
    effort_analysis = _analyze_effort_result_series(
        fifteen,
        lookback=max(2, _config_int(resolved_config, "effortLookbackBars", "effort_lookback_bars")),
    )
    effort_result = effort_analysis["effort_result"]
    effort_score = effort_analysis["effort_score"]
    effort_evidence = effort_analysis["evidence"]

    phase = "transition"
    entry_bias = "neutral"
    trigger = "none"
    trade_readiness = "avoid"
    confidence = 0.45
    no_trade_reason = "mixed_shortterm_structure"

    trap_risk = "low"
    trap_evidence = ""
    confirmation_needed: list[str] = []

    higher_timeframe_conflicts_long = one_hour_change_pct <= -higher_timeframe_conflict_pct if one_hour else False
    higher_timeframe_conflicts_short = one_hour_change_pct >= higher_timeframe_conflict_pct if one_hour else False
    higher_timeframe_confirms_long = higher_timeframe_change_pct >= higher_timeframe_confirm_pct
    higher_timeframe_confirms_short = higher_timeframe_change_pct <= -higher_timeframe_confirm_pct

    if breakout_long:
        phase = "markup"
        entry_bias = "bullish"
        trigger = "breakout_long"
        confidence = 0.74
        trap_risk, trap_evidence = _trap_risk(
            latest_candle=fifteen[-1],
            direction="long",
            latest_volume_ratio=latest_volume_ratio,
            trap_volume_ratio=trap_volume_ratio,
            trap_wick_ratio=trap_wick_ratio,
        )
        if effort_result == "effort_without_result":
            trade_readiness = "watch"
            no_trade_reason = "effort_without_result_needs_confirmation"
            confirmation_needed.append("effort_result_alignment")
        elif higher_timeframe_conflicts_long:
            trade_readiness = "avoid"
            confidence = 0.58
            no_trade_reason = "one_hour_trend_conflict"
        elif not confirmed_breakout_long:
            trade_readiness = "watch"
            no_trade_reason = "breakout_confirmation_too_weak"
            confirmation_needed.append("strong_close_and_volume")
        elif not higher_timeframe_confirms_long:
            trade_readiness = "watch"
            no_trade_reason = "higher_timeframe_confirmation_too_weak"
            confirmation_needed.append("higher_timeframe_alignment")
        elif trap_risk == "high":
            trade_readiness = "avoid"
            confidence = 0.56
            no_trade_reason = "potential_bull_trap"
            confirmation_needed.append("post_trap_cooldown")
        elif not long_retest_confirmed:
            trade_readiness = "watch"
            no_trade_reason = "breakout_retest_required"
            confirmation_needed.append("range_high_retest_hold")
        elif max_ready_extension_pct > 0 and breakout_extension_pct > max_ready_extension_pct:
            trade_readiness = "watch"
            no_trade_reason = "breakout_extension_too_far_chase_risk"
            confirmation_needed.append("pullback_retest")
        else:
            trade_readiness = "ready"
            confidence = 0.78
            no_trade_reason = ""
    elif breakdown_short:
        phase = "markdown"
        entry_bias = "bearish"
        trigger = "breakdown_short"
        confidence = 0.74
        trap_risk, trap_evidence = _trap_risk(
            latest_candle=fifteen[-1],
            direction="short",
            latest_volume_ratio=latest_volume_ratio,
            trap_volume_ratio=trap_volume_ratio,
            trap_wick_ratio=trap_wick_ratio,
        )
        if effort_result == "effort_without_result":
            trade_readiness = "watch"
            no_trade_reason = "effort_without_result_needs_confirmation"
            confirmation_needed.append("effort_result_alignment")
        elif higher_timeframe_conflicts_short:
            trade_readiness = "avoid"
            confidence = 0.58
            no_trade_reason = "one_hour_trend_conflict"
        elif not confirmed_breakdown_short:
            trade_readiness = "watch"
            no_trade_reason = "breakdown_confirmation_too_weak"
            confirmation_needed.append("strong_close_and_volume")
        elif not higher_timeframe_confirms_short:
            trade_readiness = "watch"
            no_trade_reason = "higher_timeframe_confirmation_too_weak"
            confirmation_needed.append("higher_timeframe_alignment")
        elif trap_risk == "high":
            trade_readiness = "avoid"
            confidence = 0.56
            no_trade_reason = "potential_bear_trap"
            confirmation_needed.append("post_trap_cooldown")
        elif not short_retest_confirmed:
            trade_readiness = "watch"
            no_trade_reason = "breakdown_retest_required"
            confirmation_needed.append("range_low_retest_reject")
        elif max_ready_extension_pct > 0 and breakdown_extension_pct > max_ready_extension_pct:
            trade_readiness = "watch"
            no_trade_reason = "breakdown_extension_too_far_chase_risk"
            confirmation_needed.append("pullback_retest")
        else:
            trade_readiness = "ready"
            confidence = 0.78
            no_trade_reason = ""
    elif spring_long:
        phase = "accumulation"
        entry_bias = "bullish"
        trigger = "spring_long"
        trade_readiness = "watch"
        confidence = 0.72
        no_trade_reason = "spring_needs_retest_confirmation"
        confirmation_needed.append("spring_retest_hold")
    elif upthrust_short:
        phase = "distribution"
        entry_bias = "bearish"
        trigger = "upthrust_short"
        trade_readiness = "watch"
        confidence = 0.72
        no_trade_reason = "upthrust_needs_retest_confirmation"
        confirmation_needed.append("upthrust_retest_reject")
    elif effort_result == "effort_without_result":
        phase = "range"
        confidence = 0.5
        no_trade_reason = "effort_without_result_needs_confirmation"
    elif abs(rolling_hour_change_pct) <= range_balance_change_pct and rolling_hour_range_pct <= range_balance_range_pct:
        phase = "range"
        confidence = 0.48
        no_trade_reason = "range_balance_no_edge"

    if entry_bias == "bullish":
        if funding_rate < 0:
            confidence += 0.02
        if oi_change_pct > 0.5:
            confidence += 0.03
    elif entry_bias == "bearish":
        if funding_rate > 0:
            confidence += 0.02
        if oi_change_pct > 0.5:
            confidence += 0.03

    if price_source and price_source != "trade":
        confidence -= 0.05
    if trap_risk == "medium":
        confidence -= 0.04
    if abs(mark_deviation_pct) >= mark_deviation_penalty_pct:
        confidence -= 0.03

    return {
        "status": "ready" if trade_readiness == "ready" else "watch" if trade_readiness == "watch" else "avoid",
        "phase": phase,
        "entry_bias": entry_bias,
        "trigger": trigger,
        "trade_readiness": trade_readiness,
        "confidence": _clamp_confidence(confidence),
        "no_trade_reason": no_trade_reason,
        "trap_risk": trap_risk,
        "trap_evidence": trap_evidence,
        "confirmation_needed": confirmation_needed,
        "retest_confirmed": long_retest_confirmed if entry_bias == "bullish" else short_retest_confirmed if entry_bias == "bearish" else False,
        "breakout_extension_pct": round(breakout_extension_pct if entry_bias == "bullish" else breakdown_extension_pct, 6),
        "config": resolved_config,
        "range_high": round(range_high, 8),
        "range_low": round(range_low, 8),
        "effort_result": effort_result,
        "effort_score": effort_score,
        "effort_evidence": effort_evidence,
        "latest_15m_summary": latest_bar,
        "rolling_1h_summary": rolling_hour,
        "higher_timeframe_change_pct": round(higher_timeframe_change_pct, 4),
        "funding_rate": round(_safe_float(funding_rate), 8),
        "oi_change_pct": round(_safe_float(oi_change_pct), 4),
        "price_source": str(price_source or "").strip(),
        "mark_price_deviation_pct": round(mark_deviation_pct, 6),
        "invalidation": (
            f"loss_of_{round(range_low, 4)}"
            if entry_bias == "bullish"
            else f"reclaim_{round(range_high, 4)}"
            if entry_bias == "bearish"
            else "structure_unclear"
        ),
    }
