from trade_runtime.ingestion.kline_indicators import (
    atr_pct,
    ema_trend,
    price_change_pct,
    quote_volume_ratio,
    rsi,
    summarize_kline_context,
)


def _candles(count=80):
    candles = []
    for index in range(count):
        close = 100.0 + index
        candles.append(
            {
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "quote_volume": 1000.0 + index * 10,
            }
        )
    return candles


def test_kline_indicators_calculate_price_volume_and_technical_context():
    candles = _candles(80)

    assert price_change_pct(candles, minutes=15, interval_minutes=1) == 9.1463
    assert quote_volume_ratio(candles, minutes=15, interval_minutes=1) == 1.0955
    assert atr_pct(candles, period=14) > 0
    assert 0 <= rsi(candles, period=14) <= 100
    assert ema_trend(candles, fast=20, slow=50) == "bullish"


def test_summarize_kline_context_returns_expected_windows():
    summary = summarize_kline_context({"1m": _candles(80), "15m": _candles(30)})

    assert set(summary["price_change_pct"].keys()) == {"15m", "60m", "240m"}
    assert summary["price_change_pct"]["15m"] == 9.1463
    assert summary["quote_volume_ratio"]["15m"] == 1.0955
    assert summary["rsi_14"]["15m"] > 0
    assert summary["ema_trend"]["15m"] == "bullish"


def test_summarize_kline_context_sorts_candles_and_adds_volume_price_summaries():
    ascending = [
        {
            "open_time": str(1_000 + index),
            "open": 100.0 + index,
            "high": 101.0 + index,
            "low": 99.0 + index,
            "close": 100.0 + index,
            "quote_volume": 1000.0 + index * 100,
        }
        for index in range(40)
    ]

    summary = summarize_kline_context({"1m": list(reversed(ascending))})

    assert summary["price_change_pct"]["15m"] > 0
    period_15m = next(item for item in summary["period_summaries"] if item["window"] == "15m")
    assert period_15m["source"] == "kline_ohlcv"
    assert period_15m["sample_count"] == 15
    assert period_15m["expected_sample_count"] == 15
    assert period_15m["start_price"] == 125.0
    assert period_15m["end_price"] == 139.0
    assert period_15m["quote_volume_sum"] > 0
    assert period_15m["quote_volume_ratio"] > 1.0
    assert "15m:price_up_volume_expands" in summary["volume_price_signals"]
    period_60m = next(item for item in summary["period_summaries"] if item["window"] == "60m")
    assert period_60m["status"] == "insufficient"
    assert period_60m["sample_count"] == 40
    assert period_60m["expected_sample_count"] == 60
