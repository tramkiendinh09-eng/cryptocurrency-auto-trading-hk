from __future__ import annotations

from typing import Any


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _time_key(candle: dict[str, Any]) -> float:
    raw = candle.get("open_time") or candle.get("event_time") or candle.get("timestamp") or candle.get("ts") or 0
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _sort_candles(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted([item for item in candles if isinstance(item, dict)], key=_time_key)


def _close(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("close") or candle.get("close_price") or candle.get("c"))


def _high(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("high") or candle.get("high_price") or candle.get("h"))


def _low(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("low") or candle.get("low_price") or candle.get("l"))


def _quote_volume(candle: dict[str, Any]) -> float:
    return _safe_float(candle.get("quote_volume") or candle.get("quoteVolume") or candle.get("turnover"))


def _bars_for_minutes(minutes: int, interval_minutes: int) -> int:
    if minutes <= 0 or interval_minutes <= 0:
        return 1
    return max(1, int(minutes / interval_minutes))


def _window_candles(candles: list[dict[str, Any]], minutes: int, interval_minutes: int) -> list[dict[str, Any]]:
    bars = _bars_for_minutes(minutes, interval_minutes)
    return candles[-bars:] if bars > 0 else candles[-1:]


def price_change_pct(candles: list[dict[str, Any]], minutes: int, interval_minutes: int = 1) -> float:
    candles = _sort_candles(candles)
    if len(candles) < 2:
        return 0.0
    bars = _bars_for_minutes(minutes, interval_minutes)
    latest = _close(candles[-1])
    base_index = max(0, len(candles) - 1 - bars)
    base = _close(candles[base_index])
    if latest <= 0 or base <= 0:
        return 0.0
    return round(((latest - base) / base) * 100.0, 4)


def quote_volume_ratio(candles: list[dict[str, Any]], minutes: int, interval_minutes: int = 1) -> float:
    candles = _sort_candles(candles)
    bars = _bars_for_minutes(minutes, interval_minutes)
    if len(candles) < bars * 2:
        return 0.0
    current = candles[-bars:]
    previous = candles[-bars * 2 : -bars]
    current_sum = sum(_quote_volume(item) for item in current)
    previous_sum = sum(_quote_volume(item) for item in previous)
    if current_sum <= 0 or previous_sum <= 0:
        return 0.0
    return round(current_sum / previous_sum, 4)


def _ema(values: list[float], period: int) -> float:
    if len(values) < period or period <= 0:
        return 0.0
    ema = sum(values[:period]) / period
    multiplier = 2.0 / (period + 1)
    for value in values[period:]:
        ema = (value - ema) * multiplier + ema
    return ema


def atr_pct(candles: list[dict[str, Any]], period: int = 14) -> float:
    candles = _sort_candles(candles)
    if len(candles) <= period:
        return 0.0
    true_ranges: list[float] = []
    for index in range(1, len(candles)):
        high = _high(candles[index])
        low = _low(candles[index])
        previous_close = _close(candles[index - 1])
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    if len(true_ranges) < period:
        return 0.0
    atr = sum(true_ranges[:period]) / period
    for value in true_ranges[period:]:
        atr = (atr * (period - 1) + value) / period
    latest_close = _close(candles[-1])
    if latest_close <= 0:
        return 0.0
    return round((atr / latest_close) * 100.0, 4)


def rsi(candles: list[dict[str, Any]], period: int = 14) -> float:
    candles = _sort_candles(candles)
    closes = [_close(item) for item in candles]
    if len(closes) <= period:
        return 0.0
    gains = 0.0
    losses = 0.0
    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        if change > 0:
            gains += change
        else:
            losses += abs(change)
    average_gain = gains / period
    average_loss = losses / period
    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        if change > 0:
            average_gain = (average_gain * (period - 1) + change) / period
            average_loss = (average_loss * (period - 1)) / period
        else:
            average_gain = (average_gain * (period - 1)) / period
            average_loss = (average_loss * (period - 1) + abs(change)) / period
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return round(100.0 - (100.0 / (1.0 + relative_strength)), 4)


def ema_trend(candles: list[dict[str, Any]], fast: int = 20, slow: int = 50) -> str:
    candles = _sort_candles(candles)
    closes = [_close(item) for item in candles if _close(item) > 0]
    fast_ema = _ema(closes, fast)
    slow_ema = _ema(closes, slow)
    if fast_ema <= 0 or slow_ema <= 0:
        return "neutral"
    if fast_ema > slow_ema:
        return "bullish"
    if fast_ema < slow_ema:
        return "bearish"
    return "neutral"


def _interval_minutes(interval: str) -> int:
    normalized = str(interval or "").strip().lower()
    if normalized.endswith("m"):
        return max(1, int(normalized[:-1] or 1))
    if normalized.endswith("h"):
        return max(1, int(normalized[:-1] or 1) * 60)
    if normalized.endswith("d"):
        return max(1, int(normalized[:-1] or 1) * 1440)
    return 1


def period_summary(candles: list[dict[str, Any]], window: str, minutes: int, interval_minutes: int = 1) -> dict[str, Any]:
    candles = _sort_candles(candles)
    expected_bars = _bars_for_minutes(minutes, interval_minutes)
    window_items = _window_candles(candles, minutes, interval_minutes)
    prices = [_close(item) for item in window_items if _close(item) > 0]
    if len(prices) < expected_bars or len(prices) < 2:
        return {
            "window": window,
            "sample_count": len(prices),
            "expected_sample_count": expected_bars,
            "status": "insufficient",
            "source": "kline_ohlcv",
        }
    start_price = prices[0]
    end_price = prices[-1]
    quote_volume_sum = sum(_quote_volume(item) for item in window_items)
    bars = len(window_items)
    previous_items = candles[-bars * 2 : -bars] if bars > 0 and len(candles) >= bars * 2 else []
    previous_quote_volume_sum = sum(_quote_volume(item) for item in previous_items)
    quote_volume_ratio_value = 0.0
    if quote_volume_sum > 0 and previous_quote_volume_sum > 0:
        quote_volume_ratio_value = quote_volume_sum / previous_quote_volume_sum
    return {
        "window": window,
        "source": "kline_ohlcv",
        "sample_count": len(prices),
        "expected_sample_count": expected_bars,
        "start_price": round(start_price, 8),
        "end_price": round(end_price, 8),
        "high_price": round(max(_high(item) for item in window_items), 8),
        "low_price": round(min(_low(item) for item in window_items), 8),
        "price_change_pct": round(((end_price - start_price) / start_price) * 100.0 if start_price > 0 else 0.0, 6),
        "range_pct": round(((max(prices) - min(prices)) / start_price) * 100.0 if start_price > 0 else 0.0, 6),
        "quote_volume_sum": round(quote_volume_sum, 6),
        "previous_quote_volume_sum": round(previous_quote_volume_sum, 6),
        "quote_volume_ratio": round(quote_volume_ratio_value, 6),
    }


def volume_price_signals(period_summaries: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    for summary in period_summaries:
        if summary.get("status") == "insufficient":
            continue
        price_change = _safe_float(summary.get("price_change_pct"))
        volume_ratio = _safe_float(summary.get("quote_volume_ratio"))
        window = str(summary.get("window") or "")
        if price_change >= 1.0 and volume_ratio >= 1.2:
            signals.append(f"{window}:price_up_volume_expands")
        elif price_change <= -1.0 and volume_ratio >= 1.2:
            signals.append(f"{window}:price_down_volume_expands")
        elif abs(price_change) <= 0.5 and volume_ratio >= 1.5:
            signals.append(f"{window}:effort_without_result")
        elif abs(price_change) >= 1.0 and 0 < volume_ratio <= 0.8:
            signals.append(f"{window}:price_move_volume_divergence")
    return signals


def summarize_kline_context(candles_by_interval: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    primary_interval = "1m" if candles_by_interval.get("1m") else next(iter(candles_by_interval.keys()), "1m")
    primary = _sort_candles(candles_by_interval.get(primary_interval) or [])
    interval_minutes = _interval_minutes(primary_interval)
    windows = {"15m": 15, "60m": 60, "240m": 240}
    period_summaries = [
        period_summary(primary, window=window, minutes=minutes, interval_minutes=interval_minutes)
        for window, minutes in windows.items()
    ]
    return {
        "price_change_pct": {
            window: price_change_pct(primary, minutes=minutes, interval_minutes=interval_minutes)
            for window, minutes in windows.items()
        },
        "quote_volume_ratio": {
            window: quote_volume_ratio(primary, minutes=minutes, interval_minutes=interval_minutes)
            for window, minutes in windows.items()
        },
        "atr_pct": {
            "15m": atr_pct(primary),
            "60m": atr_pct(candles_by_interval.get("15m") or primary),
        },
        "rsi_14": {
            "15m": rsi(primary),
            "60m": rsi(candles_by_interval.get("15m") or primary),
        },
        "ema_trend": {
            "15m": ema_trend(primary),
            "60m": ema_trend(candles_by_interval.get("15m") or primary),
        },
        "period_summaries": period_summaries,
        "volume_price_signals": volume_price_signals(period_summaries),
    }
