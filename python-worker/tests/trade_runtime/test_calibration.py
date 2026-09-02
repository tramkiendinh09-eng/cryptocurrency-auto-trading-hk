import json

import pytest

from trade_runtime.calibration.history import (
    HistoryBundle,
    TimeAlignedSeries,
    load_history,
)
from trade_runtime.calibration.replay import (
    build_frames,
    evaluate_frames,
    forward_return_pct,
    replay_thresholds,
    summarize_window,
)
from trade_runtime.calibration.sweep import (
    evaluate_replay,
    recommend,
    sweep_threshold,
)

_BASE_MS = 1_700_000_000_000


def _candles(count=800, *, start_price=70_000.0, step=0.0, spike_at=None, spike_pct=0.0):
    candles = []
    price = start_price
    for index in range(count):
        price = start_price + step * index
        if spike_at is not None and index >= spike_at:
            price = price * (1.0 + spike_pct / 100.0)
        candles.append(
            {
                "event_type": "market_kline",
                "symbol": "BTCUSDT",
                "exchange": "binance",
                "interval": "1m",
                "open_time": str(_BASE_MS + index * 60_000),
                "close_time": str(_BASE_MS + index * 60_000 + 59_999),
                "open": price,
                "high": price * 1.001,
                "low": price * 0.999,
                "close": price,
                "volume": 100.0,
                "quote_volume": price * 100.0,
            }
        )
    return candles


def _bundle(candles=None, *, mark_multiplier=1.0, funding_rate=0.0001, open_interest_step=1.0):
    candles = candles if candles is not None else _candles()
    marks = [dict(candle, close=candle["close"] * mark_multiplier) for candle in candles]
    return HistoryBundle(
        symbol="BTCUSDT",
        start_ms=_BASE_MS,
        end_ms=_BASE_MS + len(candles) * 60_000,
        candles=candles,
        mark_candles=marks,
        open_interest=[
            {
                "timestamp": _BASE_MS + index * 300_000,
                "open_interest": 1000.0 + index * open_interest_step,
                "open_interest_value": 7e7,
            }
            for index in range(max(2, len(candles) // 5))
        ],
        funding_rates=[
            {"timestamp": _BASE_MS + index * 8 * 3_600_000, "funding_rate": funding_rate, "mark_price": 70_000.0}
            for index in range(3)
        ],
    )


def _config(**market_trigger):
    base = {
        "priceChangePct": 2.5,
        "ruleOnlyPriceChangePct": 1.0,
        "priceAccelerationPct": 1.2,
        "fundingRateAbs": 0.0,
        "markPriceDeviationPct": 0.0,
    }
    base.update(market_trigger)
    return {"marketTrigger": base}


class _StubFetcher:
    """替网络的桩，形状与真实端点返回一致。"""

    def __init__(self):
        self.calls = []

    def paged_klines(self, path, symbol, interval, start_ms, end_ms):
        self.calls.append(path)
        return [
            [_BASE_MS + index * 60_000, "70000", "70100", "69900", "70050", "10", _BASE_MS + index * 60_000 + 59_999, "700500"]
            for index in range(3)
        ]

    def get(self, path, params):
        self.calls.append(path)
        if "openInterestHist" in path:
            return [
                {"timestamp": _BASE_MS, "sumOpenInterest": "100", "sumOpenInterestValue": "7000000"},
                {"timestamp": _BASE_MS + 300_000, "sumOpenInterest": "101", "sumOpenInterestValue": "7100000"},
            ]
        if "fundingRate" in path:
            return [{"fundingTime": _BASE_MS, "fundingRate": "0.0001", "markPrice": "70000"}]
        return []


def test_time_aligned_series_never_reads_ahead():
    series = TimeAlignedSeries(
        [
            {"timestamp": 100, "value": "a"},
            {"timestamp": 200, "value": "b"},
            {"timestamp": 300, "value": "c"},
        ]
    )

    assert series.at(50) is None
    assert series.at(100)["value"] == "a"
    # 199 只能看到 100 那条，不能提前拿到 200 的样本
    assert series.at(199)["value"] == "a"
    assert series.at(200)["value"] == "b"
    assert series.at(10_000)["value"] == "c"


def test_time_aligned_series_handles_empty_input():
    assert TimeAlignedSeries([]).at(123) is None


def test_load_history_caches_and_reuses(tmp_path):
    fetcher = _StubFetcher()
    bundle = load_history(
        "btc/usdt",
        start_ms=_BASE_MS,
        end_ms=_BASE_MS + 3 * 60_000,
        cache_dir=tmp_path,
        fetcher=fetcher,
    )

    assert bundle.symbol == "BTCUSDT"
    assert len(bundle.candles) == 3
    assert len(bundle.mark_candles) == 3
    assert bundle.candles[0]["close"] == 70_050.0
    assert bundle.candles[0]["quote_volume"] == 700_500.0
    first_call_count = len(fetcher.calls)
    assert first_call_count > 0

    cached_files = list(tmp_path.glob("*.json"))
    assert len(cached_files) == 1
    payload = json.loads(cached_files[0].read_text(encoding="utf-8"))
    assert payload["symbol"] == "BTCUSDT"

    # 第二次必须命中缓存，不再打网络
    reused = load_history(
        "BTCUSDT",
        start_ms=_BASE_MS,
        end_ms=_BASE_MS + 3 * 60_000,
        cache_dir=tmp_path,
        fetcher=fetcher,
    )
    assert len(fetcher.calls) == first_call_count
    assert reused.candles == bundle.candles


class _WindowedOpenInterestFetcher(_StubFetcher):
    """复刻 openInterestHist 的真实行为。

    当 ``endTime - startTime`` 超过 ``limit × period`` 时，币安会**忽略
    startTime**，只返回贴着 endTime 的最后 500 条——不逐页收窄 endTime
    的分页循环会因此只拿到窗口末尾。
    """

    period_ms = 300_000
    limit = 500

    def __init__(self, *, total_samples=1200, first_ts=_BASE_MS):
        super().__init__()
        self.samples = [
            {
                "timestamp": first_ts + index * self.period_ms,
                "sumOpenInterest": str(100 + index),
                "sumOpenInterestValue": str(7_000_000 + index),
            }
            for index in range(total_samples)
        ]

    def get(self, path, params):
        self.calls.append(path)
        if "openInterestHist" not in path:
            return super().get(path, params)
        start = int(params["startTime"])
        end = int(params["endTime"])
        # 真实端点的 startTime 是排他的：一页首样本落在 startTime + period 上
        window = [item for item in self.samples if start < item["timestamp"] <= end]
        if (end - start) > self.limit * self.period_ms:
            # 窗口过宽 → 忽略 startTime，返回末尾 500 条
            window = [item for item in self.samples if item["timestamp"] <= end]
        return window[-self.limit :]


def test_open_interest_pagination_covers_whole_window(tmp_path):
    total = 1200
    fetcher = _WindowedOpenInterestFetcher(total_samples=total)
    period_ms = _WindowedOpenInterestFetcher.period_ms
    # startTime 排他，所以窗口起点要比首样本早一个 period 才能包含它
    start_ms = _BASE_MS - period_ms
    end_ms = _BASE_MS + total * period_ms

    bundle = load_history(
        "BTCUSDT",
        start_ms=start_ms,
        end_ms=end_ms,
        cache_dir=tmp_path,
        fetcher=fetcher,
    )

    # 单页上限 500，整段 1200 条必须靠多页取全，而不是只拿到末尾那 500 条
    assert len(bundle.open_interest) == total
    assert bundle.open_interest[0]["timestamp"] == _BASE_MS
    stamps = [row["timestamp"] for row in bundle.open_interest]
    assert stamps == sorted(stamps)
    assert len(set(stamps)) == len(stamps), "分页边界不得产生重复样本"


def test_open_interest_pagination_survives_retention_gap(tmp_path):
    # 早于保留期的页返回空，但更近的页有数据——不能见空就停
    period_ms = _WindowedOpenInterestFetcher.period_ms
    first_ts = _BASE_MS + 900 * period_ms
    fetcher = _WindowedOpenInterestFetcher(total_samples=600, first_ts=first_ts)
    end_ms = first_ts + 600 * period_ms

    bundle = load_history(
        "BTCUSDT",
        start_ms=_BASE_MS,
        end_ms=end_ms,
        cache_dir=tmp_path,
        fetcher=fetcher,
    )

    assert len(bundle.open_interest) == 600
    assert bundle.open_interest[0]["timestamp"] == first_ts


def test_load_history_rejects_inverted_window(tmp_path):
    with pytest.raises(ValueError):
        load_history("BTCUSDT", start_ms=_BASE_MS, end_ms=_BASE_MS - 1, cache_dir=tmp_path, fetcher=_StubFetcher())


def test_coverage_flags_liquidation_history_as_unavailable():
    coverage = _bundle().coverage()

    # 爆仓维度没有公开历史来源，必须显式标注而不是留 0
    assert coverage["liquidation_history"] == "unavailable_public_rest"
    assert coverage["candle_minutes"] == 800


def test_replay_uses_production_policy_and_respects_warmup():
    bundle = _bundle(_candles(800))

    result = replay_thresholds(bundle, runtime_config=_config(), warmup_bars=500)

    assert result.coverage["warmup_bars_skipped"] == 500
    assert result.coverage["replayed_steps"] == 300
    assert len(result.steps) == 300
    # 线上 15 秒轮询 × 60 样本 = 15 分钟；离线 1 分钟步长应换算成 15 个样本
    assert result.coverage["history_limit_samples"] == 15
    assert result.inert_dimensions


def test_replay_flat_market_produces_no_dispatch():
    bundle = _bundle(_candles(700, step=0.0))

    result = replay_thresholds(bundle, runtime_config=_config(), warmup_bars=500)

    assert result.counts() == {"NO_DISPATCH": len(result.steps)}
    assert result.dispatched == []


def test_replay_price_spike_triggers_llm_allowed():
    # 500 根预热后突然跳涨 5%，应越过 priceChangePct=2.5 进入 LLM_ALLOWED
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))

    result = replay_thresholds(bundle, runtime_config=_config(), warmup_bars=500)

    assert result.llm_allowed, "价格跳涨应产生 LLM_ALLOWED 触发"
    assert any("price_break" in step.signal_types for step in result.dispatched)


def test_replay_threshold_change_alters_trigger_count():
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))

    # 必须关掉加速度触发再比：它会在同样的步上独立触发，
    # 掩盖掉价格阈值本身的影响，让两组 dispatch 数相同。
    strict = replay_thresholds(
        bundle,
        runtime_config=_config(ruleOnlyPriceChangePct=99.0, priceAccelerationPct=0.0),
        warmup_bars=500,
    )
    loose = replay_thresholds(
        bundle,
        runtime_config=_config(ruleOnlyPriceChangePct=0.01, priceAccelerationPct=0.0),
        warmup_bars=500,
    )

    assert len(strict.dispatched) == 0
    assert len(loose.dispatched) > 0


def test_replay_signal_counts_isolate_each_threshold():
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))

    result = replay_thresholds(bundle, runtime_config=_config(), warmup_bars=500)
    counts = result.signal_type_counts()

    # 价格与加速度是两个独立维度，扫描一个时必须能把另一个摘开
    assert counts.get("price_break", 0) > 0
    assert counts.get("price_acceleration", 0) > 0


def test_replay_funding_threshold_gates_on_configured_value():
    bundle = _bundle(_candles(700), funding_rate=0.001)

    disabled = replay_thresholds(bundle, runtime_config=_config(fundingRateAbs=0.0), warmup_bars=500)
    enabled = replay_thresholds(bundle, runtime_config=_config(fundingRateAbs=0.0005), warmup_bars=500)

    assert not any("funding_rate_extreme" in step.signal_types for step in disabled.steps)
    assert any("funding_rate_extreme" in step.signal_types for step in enabled.steps)


def test_replay_mark_deviation_uses_mark_price_series():
    # 标记价高出最新价 0.5%，越过 markPriceDeviationPct=0.25
    bundle = _bundle(_candles(700), mark_multiplier=1.005)

    result = replay_thresholds(bundle, runtime_config=_config(markPriceDeviationPct=0.25), warmup_bars=500)

    assert any("mark_price_deviation" in step.signal_types for step in result.steps)


def test_replay_carries_cooldown_state_across_steps():
    bundle = _bundle(_candles(700, spike_at=550, spike_pct=5.0))

    result = replay_thresholds(
        bundle,
        runtime_config={
            "marketTrigger": _config()["marketTrigger"],
            "cooldownPolicy": {"globalSeconds": 3600},
        },
        warmup_bars=500,
    )

    # 冷却期跨步生效，否则重放会高估 LLM 触发次数
    assert any(step.cooldown_blocked for step in result.steps)


def test_replay_rejects_empty_history():
    bundle = HistoryBundle(symbol="BTCUSDT", start_ms=_BASE_MS, end_ms=_BASE_MS + 60_000)

    with pytest.raises(ValueError):
        replay_thresholds(bundle, runtime_config=_config())


def test_forward_return_pct_is_bounded_by_available_candles():
    candles = _candles(10, step=100.0)

    assert forward_return_pct(candles, from_index=0, horizon_minutes=2) > 0
    # 越界时返回 0 而不是抛异常或读到不存在的未来
    assert forward_return_pct(candles, from_index=8, horizon_minutes=5) == 0.0
    assert forward_return_pct(candles, from_index=-1, horizon_minutes=1) == 0.0


def test_summarize_window_reports_volatility_percentiles():
    summary = summarize_window(_bundle(_candles(600, step=10.0)))

    assert summary["days"] > 0
    assert summary["total_change_pct"] > 0
    assert summary["minute_abs_change_p50"] <= summary["minute_abs_change_p99"]


def test_evaluate_replay_scores_direction_not_raw_return():
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))
    result = replay_thresholds(bundle, runtime_config=_config(), warmup_bars=500)

    metrics = evaluate_replay(result, bundle, horizon_minutes=10)

    assert metrics["trigger_count"] == len(result.dispatched)
    assert 0.0 <= metrics["hit_rate"] <= 1.0
    assert metrics["triggers_per_day"] >= 0.0


def test_evaluate_replay_filters_by_signal_type():
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))
    result = replay_thresholds(bundle, runtime_config=_config(), warmup_bars=500)

    filtered = evaluate_replay(result, bundle, horizon_minutes=10, signal_type_filter="price_break")
    unfiltered = evaluate_replay(result, bundle, horizon_minutes=10)

    assert filtered["trigger_count"] <= unfiltered["trigger_count"]


def test_sweep_threshold_walks_the_grid_independently():
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))

    outcome = sweep_threshold(
        bundle,
        threshold_key="ruleOnlyPriceChangePct",
        values=[0.01, 1.0, 99.0],
        base_config=_config(),
        horizon_minutes=10,
        warmup_bars=500,
    )

    assert [point.value for point in outcome.points] == [0.01, 1.0, 99.0]
    # 阈值越松触发越多，这是网格有效的最基本证据
    assert outcome.points[0].trigger_count >= outcome.points[-1].trigger_count
    assert outcome.coverage["liquidation_history"] == "unavailable_public_rest"
    assert outcome.notes


def test_frame_reuse_matches_full_replay():
    """复用帧必须与整段重跑逐步一致，否则优化就改变了语义。"""
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))
    config = _config()

    direct = replay_thresholds(bundle, runtime_config=config, warmup_bars=500)
    prepared = build_frames(bundle, warmup_bars=500)
    reused = evaluate_frames(prepared, runtime_config=config)

    assert len(reused.steps) == len(direct.steps)
    assert [step.dispatch_mode for step in reused.steps] == [step.dispatch_mode for step in direct.steps]
    assert [step.signal_types for step in reused.steps] == [step.signal_types for step in direct.steps]
    assert [step.cooldown_blocked for step in reused.steps] == [step.cooldown_blocked for step in direct.steps]


def test_frames_are_reusable_across_different_thresholds():
    """同一份帧喂不同阈值必须得到不同结果，且不互相污染。"""
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))
    prepared = build_frames(bundle, warmup_bars=500)

    loose = evaluate_frames(prepared, runtime_config=_config(ruleOnlyPriceChangePct=0.01, priceAccelerationPct=0.0))
    strict = evaluate_frames(prepared, runtime_config=_config(ruleOnlyPriceChangePct=99.0, priceAccelerationPct=0.0))
    loose_again = evaluate_frames(prepared, runtime_config=_config(ruleOnlyPriceChangePct=0.01, priceAccelerationPct=0.0))

    assert len(loose.dispatched) > len(strict.dispatched)
    # 第三次必须与第一次完全一致——帧被前一次评估改写过就会不等
    assert [step.dispatch_mode for step in loose_again.steps] == [step.dispatch_mode for step in loose.steps]


def test_build_frames_excludes_threshold_dependent_fields():
    bundle = _bundle(_candles(600))
    prepared = build_frames(bundle, warmup_bars=500)

    assert prepared.frames
    # event_strength 依赖阈值，不能进与阈值无关的帧
    assert all("event_strength" not in frame["feature_snapshot"] for frame in prepared.frames)
    assert all("kline_price_change_pct" in frame["feature_snapshot"] for frame in prepared.frames)


def test_sweep_accepts_prebuilt_frames():
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))
    prepared = build_frames(bundle, warmup_bars=500)

    with_frames = sweep_threshold(
        bundle,
        threshold_key="ruleOnlyPriceChangePct",
        values=[0.01, 99.0],
        base_config=_config(),
        horizon_minutes=10,
        frames=prepared,
    )
    without_frames = sweep_threshold(
        bundle,
        threshold_key="ruleOnlyPriceChangePct",
        values=[0.01, 99.0],
        base_config=_config(),
        horizon_minutes=10,
        warmup_bars=500,
    )

    assert [point.trigger_count for point in with_frames.points] == [
        point.trigger_count for point in without_frames.points
    ]


def test_sweep_isolates_the_dimension_under_test():
    # 加速度维度会在同样的 K 线上独立触发；不隔离的话，
    # 价格阈值取 0.01 和 99 会得到同样的 dispatch 数
    bundle = _bundle(_candles(700, spike_at=600, spike_pct=5.0))

    isolated = sweep_threshold(
        bundle,
        threshold_key="ruleOnlyPriceChangePct",
        values=[0.01, 99.0],
        base_config=_config(priceAccelerationPct=1.2),
        horizon_minutes=10,
        warmup_bars=500,
    )
    combined = sweep_threshold(
        bundle,
        threshold_key="ruleOnlyPriceChangePct",
        values=[0.01, 99.0],
        base_config=_config(priceAccelerationPct=1.2),
        horizon_minutes=10,
        warmup_bars=500,
        isolate=False,
    )

    assert isolated.points[0].trigger_count > isolated.points[1].trigger_count
    # 不隔离时另一个维度把差异吃掉了
    assert combined.points[0].trigger_count == combined.points[1].trigger_count
    assert any("已关闭" in note for note in isolated.notes)


def test_sweep_isolation_keeps_both_price_change_levels():
    from trade_runtime.calibration.sweep import _isolate_dimension

    isolated = _isolate_dimension(_config(fundingRateAbs=0.0005), "priceChangePct")

    # 强/弱两级属于同一维度，扫其一时不能把另一个关掉
    assert isolated["marketTrigger"]["ruleOnlyPriceChangePct"] == 1.0
    assert isolated["marketTrigger"]["fundingRateAbs"] == 0.0


def test_sweep_isolation_masks_price_change_when_testing_others():
    from trade_runtime.calibration.sweep import _isolate_dimension

    isolated = _isolate_dimension(_config(), "fundingRateAbs")

    # 价格维度没有「置 0 即关闭」的语义，只能抬到不可达的值
    assert isolated["marketTrigger"]["priceChangePct"] >= 1e9
    assert isolated["marketTrigger"]["ruleOnlyPriceChangePct"] >= 1e9


def test_sweep_does_not_mutate_base_config():
    bundle = _bundle(_candles(600))
    base = _config()
    original = json.dumps(base, sort_keys=True)

    sweep_threshold(
        bundle,
        threshold_key="ruleOnlyPriceChangePct",
        values=[0.5, 5.0],
        base_config=base,
        horizon_minutes=10,
        warmup_bars=500,
    )

    assert json.dumps(base, sort_keys=True) == original


def test_recommend_declines_when_no_value_meets_frequency_band():
    bundle = _bundle(_candles(700))
    outcome = sweep_threshold(
        bundle,
        threshold_key="ruleOnlyPriceChangePct",
        values=[50.0, 99.0],
        base_config=_config(),
        horizon_minutes=10,
        warmup_bars=500,
    )

    verdict = recommend(outcome)

    # 样本不足时必须拒绝推荐，而不是硬选一个最优
    assert verdict["recommended"] is None
    assert "样本不足" in verdict["reason"] or "没有取值" in verdict["reason"]
    assert verdict["candidates"]
