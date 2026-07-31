from trade_runtime.strategy.wyckoff_shortterm import analyze_wyckoff_shortterm


def _fifteen_minute_breakout_candles():
    candles = []
    rows = [
        (100.0, 100.5, 1000.0),
        (100.5, 100.7, 1100.0),
        (100.7, 100.6, 900.0),
        (100.6, 101.0, 950.0),
        (101.0, 101.2, 1000.0),
        (101.2, 101.1, 950.0),
        (101.1, 101.4, 1000.0),
        (101.4, 103.2, 2600.0),
    ]
    for index, (opened, closed, quote_volume) in enumerate(rows):
        candles.append(
            {
                "event_type": "market_kline",
                "interval": "15m",
                "open_time": str(1_714_000_000_000 + index * 900_000),
                "open": opened,
                "high": max(opened, closed) + (0.3 if index < len(rows) - 1 else 0.35),
                "low": min(opened, closed) - 0.2,
                "close": closed,
                "quote_volume": quote_volume,
            }
        )
    return candles


def _replace_last_candle(candles, **overrides):
    updated = [dict(item) for item in candles]
    updated[-1].update(overrides)
    return updated


def _one_hour_bearish_candles():
    candles = []
    rows = [
        (106.0, 105.5, 3000.0),
        (105.5, 105.0, 3100.0),
        (105.0, 104.7, 3200.0),
        (104.7, 104.3, 3300.0),
        (104.3, 104.0, 3400.0),
        (104.0, 103.7, 3500.0),
        (103.7, 103.3, 3600.0),
        (103.3, 103.0, 3700.0),
        (103.0, 102.6, 3800.0),
        (102.6, 102.3, 3900.0),
        (102.3, 102.0, 4000.0),
        (102.0, 101.6, 4100.0),
    ]
    for index, (opened, closed, quote_volume) in enumerate(rows):
        candles.append(
            {
                "event_type": "market_kline",
                "interval": "1h",
                "open_time": str(1_714_000_000_000 + index * 3_600_000),
                "open": opened,
                "high": max(opened, closed) + 0.25,
                "low": min(opened, closed) - 0.2,
                "close": closed,
                "quote_volume": quote_volume,
            }
        )
    return candles


def _effort_without_result_breakout_candles():
    candles = []
    rows = [
        (100.00, 100.05, 800.0),
        (100.05, 100.10, 850.0),
        (100.10, 100.08, 900.0),
        (100.08, 100.15, 950.0),
        (100.15, 100.18, 1800.0),
        (100.18, 100.16, 1900.0),
        (100.16, 100.20, 2000.0),
        (100.20, 100.36, 2100.0),
    ]
    for index, (opened, closed, quote_volume) in enumerate(rows):
        candles.append(
            {
                "event_type": "market_kline",
                "interval": "15m",
                "open_time": str(1_714_000_000_000 + index * 900_000),
                "open": opened,
                "high": max(opened, closed) + 0.05,
                "low": min(opened, closed) - 0.05,
                "close": closed,
                "quote_volume": quote_volume,
            }
        )
    return candles


def test_analyze_wyckoff_shortterm_detects_bullish_breakout_setup():
    result = analyze_wyckoff_shortterm(
        {"15m": _fifteen_minute_breakout_candles()},
        latest_price=103.2,
        mark_price=103.1,
        funding_rate=-0.00005,
        oi_change_pct=1.4,
        price_source="trade",
        config={"requireRetestForReady": False, "maxReadyExtensionPct": 2.0},
    )

    assert result["status"] == "ready"
    assert result["phase"] == "markup"
    assert result["entry_bias"] == "bullish"
    assert result["trigger"] == "breakout_long"
    assert result["trade_readiness"] == "ready"
    assert result["range_high"] >= 101.7
    assert result["range_low"] <= 100.8


def test_analyze_wyckoff_shortterm_returns_insufficient_without_enough_15m_bars():
    result = analyze_wyckoff_shortterm({"15m": _fifteen_minute_breakout_candles()[:4]})

    assert result == {
        "status": "insufficient",
        "phase": "context_insufficient",
        "entry_bias": "neutral",
        "trigger": "none",
        "trade_readiness": "avoid",
        "confidence": 0.0,
        "no_trade_reason": "not_enough_15m_bars",
    }


def test_analyze_wyckoff_shortterm_does_not_mark_ready_for_marginal_breakout():
    candles = _replace_last_candle(
        _fifteen_minute_breakout_candles(),
        close=101.75,
        high=101.95,
        quote_volume=2100.0,
    )

    result = analyze_wyckoff_shortterm({"15m": candles}, latest_price=101.75, mark_price=101.73, price_source="trade")

    assert result["trigger"] == "breakout_long"
    assert result["trade_readiness"] != "ready"


def test_analyze_wyckoff_shortterm_does_not_mark_ready_for_low_volume_breakout():
    candles = _replace_last_candle(_fifteen_minute_breakout_candles(), quote_volume=950.0)

    result = analyze_wyckoff_shortterm({"15m": candles}, latest_price=103.2, mark_price=103.1, price_source="trade")

    assert result["trigger"] == "breakout_long"
    assert result["trade_readiness"] != "ready"


def test_analyze_wyckoff_shortterm_downgrades_ready_signal_when_one_hour_trend_conflicts():
    result = analyze_wyckoff_shortterm(
        {
            "15m": _fifteen_minute_breakout_candles(),
            "1h": _one_hour_bearish_candles(),
        },
        latest_price=103.2,
        mark_price=103.1,
        price_source="trade",
    )

    assert result["trigger"] == "breakout_long"
    assert result["trade_readiness"] != "ready"


def test_analyze_wyckoff_shortterm_effort_without_result_blocks_ready_breakout():
    result = analyze_wyckoff_shortterm(
        {"15m": _effort_without_result_breakout_candles()},
        latest_price=100.36,
        mark_price=100.35,
        price_source="trade",
    )

    assert result["trigger"] == "breakout_long"
    assert result["effort_result"] == "effort_without_result"
    assert result["trade_readiness"] != "ready"


def test_analyze_wyckoff_shortterm_blocks_breakout_without_retest():
    result = analyze_wyckoff_shortterm(
        {"15m": _fifteen_minute_breakout_candles()},
        latest_price=103.2,
        mark_price=103.1,
        price_source="trade",
        config={"requireRetestForReady": True, "trapCooldownBars": 1, "retestMaxDistancePct": 0.01},
    )

    assert result["trigger"] == "breakout_long"
    assert result["trade_readiness"] == "watch"
    assert result["no_trade_reason"] == "breakout_retest_required"


def test_analyze_wyckoff_shortterm_blocks_extended_chase_breakout():
    result = analyze_wyckoff_shortterm(
        {"15m": _fifteen_minute_breakout_candles()},
        latest_price=103.2,
        mark_price=103.1,
        price_source="trade",
        config={"requireRetestForReady": False, "maxReadyExtensionPct": 0.2},
    )

    assert result["trigger"] == "breakout_long"
    assert result["trade_readiness"] == "watch"
    assert result["no_trade_reason"] == "breakout_extension_too_far_chase_risk"


def test_analyze_wyckoff_shortterm_blocks_high_trap_risk_breakout():
    candles = _replace_last_candle(
        _fifteen_minute_breakout_candles(),
        open=101.4,
        high=106.0,
        low=101.2,
        close=103.2,
        quote_volume=4000.0,
    )

    result = analyze_wyckoff_shortterm(
        {"15m": candles},
        latest_price=103.2,
        mark_price=103.1,
        price_source="trade",
        config={"requireRetestForReady": False, "maxReadyExtensionPct": 10, "trapVolumeRatio": 1.2, "trapWickRatio": 0.45},
    )

    assert result["trigger"] == "breakout_long"
    assert result["trade_readiness"] == "avoid"
    assert result["trap_risk"] == "high"
    assert result["no_trade_reason"] == "potential_bull_trap"
