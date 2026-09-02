"""用历史数据驱动**生产**触发策略。

核心约束只有一条：信号判定必须由 ``trigger_policy.evaluate_trigger_policy``
本身作出。本模块不复制任何一条阈值比较逻辑——它只负责把历史序列重建成
生产运行时会构造的 ``feature_snapshot`` / ``event_bundle`` 形状，然后逐分钟
把它们喂给真正的策略函数。

这样做的代价是必须逐字段对齐 ``runtime_inputs`` 的语义；收益是校准出来的
阈值直接就是线上行为，不需要「回测和实盘为什么不一样」这类事后解释。

复刻的语义（对应 ``runtime_inputs`` 的实现）：

``price_change_pct``
    相邻两次轮询之间的价格变化百分比（``_price_change_pct``）。
``market_window_price_change_pct``
    行情历史窗口首尾价差（``_market_history_trigger_metrics``）。窗口长度由
    ``market_context_history_limit`` 决定，默认 60 个样本。
``market_price_acceleration_pct``
    最后一段涨跌减去此前累计涨跌，同上。
``mark_price_deviation_pct``
    ``(mark - last) / last * 100``，故需要标记价 K 线。
``kline_price_change_pct`` / ``atr_pct`` / ``rsi_14`` / ``ema_trend``
    直接调用生产的 ``summarize_kline_context``，输入是截至当前分钟的 K 线切片。
``oi_change_pct``
    行情历史窗口内持仓量首尾变化（``_oi_change_pct``）。

**刻意不复刻的部分**，因为历史数据里根本不存在：``news_score``、
``social_score``、``onchain_flow_bias`` 恒为 0，``liquidation_*`` 恒为 0。
这意味着 ``triggerMatrix`` 里那三条跨源组合规则在校准中永远不会命中，
报告里必须照实说明——它们不是「没触发」，而是「无法评估」。

一个关键的取样对齐问题
----------------------
生产环境每 15 秒轮询一次，历史 K 线最细是 1 分钟。所以离线重放的步长是
1 分钟，比线上稀疏 4 倍。后果是明确的：**窗口类指标覆盖的真实时长变成 4 倍**
（60 个样本 = 60 分钟而非 15 分钟），而 ``price_change_pct`` 变成分钟级
而非 15 秒级涨跌。为了让窗口时长与线上一致，``replay_thresholds`` 默认把
``history_limit`` 按步长换算（线上 60 样本 × 15 秒 = 15 分钟 → 离线 15 个样本），
调用方可以覆盖。这个换算是近似的：同样 15 分钟内，线上看到 60 个价格点、
离线只有 15 个，所以离线的加速度指标天然更平滑、更不容易越过阈值——
即校准出的 ``priceAccelerationPct`` 偏保守。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from ..ingestion.kline_indicators import summarize_kline_context
from ..trigger_policy import classify_event_strength_from_policy, evaluate_trigger_policy
from .history import HistoryBundle, TimeAlignedSeries

logger = logging.getLogger(__name__)

# 线上：poll 15s × history limit 60 = 15 分钟窗口。
_LIVE_POLL_SECONDS = 15
_LIVE_HISTORY_LIMIT = 60
_LIVE_WINDOW_MINUTES = _LIVE_POLL_SECONDS * _LIVE_HISTORY_LIMIT / 60.0

# summarize_kline_context 的 240m 量比要比较前后各 240 根 1m 线。
_KLINE_LOOKBACK_BARS = 500


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class ReplayStep:
    """一个重放步的完整记录，保留到能解释「为什么触发」的粒度。"""

    timestamp_ms: int
    price: float
    dispatch_mode: str
    trigger_reason: str
    trigger_source: str
    signal_types: list[str] = field(default_factory=list)
    cooldown_blocked: bool = False
    budget_blocked: bool = False
    direction: str = ""
    feature_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplayResult:
    """一次完整重放的结果。"""

    symbol: str
    steps: list[ReplayStep] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    # 无法评估的维度，报告必须原样带出，避免把「无数据」读成「无触发」
    inert_dimensions: list[str] = field(default_factory=list)

    @property
    def dispatched(self) -> list[ReplayStep]:
        return [step for step in self.steps if step.dispatch_mode != "NO_DISPATCH"]

    @property
    def llm_allowed(self) -> list[ReplayStep]:
        return [step for step in self.steps if step.dispatch_mode == "LLM_ALLOWED"]

    def counts(self) -> dict[str, int]:
        modes: dict[str, int] = {}
        for step in self.steps:
            modes[step.dispatch_mode] = modes.get(step.dispatch_mode, 0) + 1
        return modes

    def signal_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for step in self.steps:
            for signal_type in step.signal_types:
                counts[signal_type] = counts.get(signal_type, 0) + 1
        return counts


def _build_market_event(candle: dict[str, Any], symbol: str, timestamp_ms: int) -> dict[str, Any]:
    """一根 K 线的收盘 → 一个 market_tick 事件。

    生产环境的 tick 来自 REST ticker 的最新成交价，历史上最接近的等价物是
    1m 收盘价。``quote_volume`` 用该分钟的成交额，与线上 24h 累计额语义不同,
    所以 ``market_quote_volume_change_pct`` 在离线重放里不可比 —— 它不参与
    任何阈值判定，仅出现在快照里，此处不作校准。
    """
    return {
        "event_type": "market_tick",
        "symbol": symbol,
        "exchange": "binance",
        "price": _safe_float(candle.get("close")),
        "volume": _safe_float(candle.get("volume")),
        "quote_volume": _safe_float(candle.get("quote_volume")),
        "event_time": str(timestamp_ms),
    }


def _history_metrics(history: list[dict[str, Any]]) -> dict[str, float]:
    """复刻 ``runtime_inputs._market_history_trigger_metrics``。

    公式与生产逐行对应，包括 round 的位数——差异会直接变成阈值偏移。
    """
    prices = [_safe_float(item.get("price")) for item in history if _safe_float(item.get("price")) > 0]
    metrics = {
        "market_window_price_change_pct": 0.0,
        "market_price_acceleration_pct": 0.0,
        "mark_price_deviation_pct": 0.0,
    }
    if len(prices) >= 2 and prices[0] > 0:
        metrics["market_window_price_change_pct"] = round(((prices[-1] - prices[0]) / prices[0]) * 100.0, 4)
    if len(prices) >= 3 and prices[0] > 0 and prices[-2] > 0:
        previous_change = ((prices[-2] - prices[0]) / prices[0]) * 100.0
        latest_change = ((prices[-1] - prices[-2]) / prices[-2]) * 100.0
        metrics["market_price_acceleration_pct"] = round(latest_change - previous_change, 4)
    latest = history[-1] if history else {}
    latest_price = _safe_float(latest.get("price"))
    latest_mark_price = _safe_float(latest.get("mark_price"))
    if latest_price > 0 and latest_mark_price > 0:
        metrics["mark_price_deviation_pct"] = round(((latest_mark_price - latest_price) / latest_price) * 100.0, 4)
    return metrics


def _oi_change_pct(history: list[dict[str, Any]]) -> float:
    """复刻 ``runtime_inputs._oi_change_pct``：窗口内持仓量首尾变化。"""
    samples = [
        _safe_float(item.get("open_interest")) for item in history if _safe_float(item.get("open_interest")) > 0
    ]
    if len(samples) < 2 or samples[0] <= 0:
        return 0.0
    return round(((samples[-1] - samples[0]) / samples[0]) * 100.0, 4)


@dataclass
class ReplayFrames:
    """与阈值无关的重放帧序列。

    重放的绝大部分开销在指标计算上——``summarize_kline_context`` 每一步都要
    在 500 根 K 线上算 ATR / RSI / EMA / 三窗口量比，而这些**完全不依赖阈值**。
    网格扫描时把这部分算一次复用，比逐个取值重跑整段历史快一个数量级。

    真正依赖阈值的只有两处：``classify_event_strength_from_policy`` 和
    ``evaluate_trigger_policy``，它们都在 ``evaluate_frames`` 里逐帧调用——
    所以复用帧不会削弱「判定必须由生产代码作出」这条约束。
    """

    symbol: str
    frames: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)


def build_frames(
    bundle: HistoryBundle,
    *,
    history_limit: int | None = None,
    warmup_bars: int = _KLINE_LOOKBACK_BARS,
) -> ReplayFrames:
    """把历史重建成逐分钟的 (event_bundle, feature_snapshot) 序列。

    这一步不读取任何阈值，产出可以在整条扫描网格上复用。

    Args:
        bundle: ``load_history`` 的产物
        history_limit: 行情历史窗口样本数；None 表示按线上 15 分钟窗口换算
        warmup_bars: 前多少根 K 线只用于填充指标窗口、不产生判定

    Returns:
        ReplayFrames: 每帧含 ``timestamp_ms`` / ``price`` / ``event_bundle`` /
        ``feature_snapshot``（不含 ``event_strength``，那一项依赖阈值）
    """
    symbol = bundle.symbol
    candles = sorted(bundle.candles, key=lambda item: int(item.get("open_time") or 0))
    if not candles:
        raise ValueError(f"no candles in history bundle for {symbol}")

    # 离线步长 1 分钟，把线上的 15 分钟窗口换算成样本数。
    resolved_history_limit = max(2, int(history_limit or round(_LIVE_WINDOW_MINUTES)))

    mark_series = TimeAlignedSeries(
        [
            {"timestamp": int(item.get("open_time") or 0), "mark_price": _safe_float(item.get("close"))}
            for item in bundle.mark_candles
        ]
    )
    oi_series = TimeAlignedSeries(bundle.open_interest)
    funding_series = TimeAlignedSeries(bundle.funding_rates)

    market_history: list[dict[str, Any]] = []
    previous_price = 0.0
    frames: list[dict[str, Any]] = []
    start_index = min(max(0, int(warmup_bars)), len(candles) - 1)

    for index, candle in enumerate(candles):
        timestamp_ms = int(candle.get("open_time") or 0)
        now_dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
        price = _safe_float(candle.get("close"))
        if price <= 0:
            continue

        mark_row = mark_series.at(timestamp_ms)
        oi_row = oi_series.at(timestamp_ms)
        funding_row = funding_series.at(timestamp_ms)

        market_history.append(
            {
                "observed_at": now_dt.isoformat(),
                "symbol": symbol,
                "price": price,
                "mark_price": _safe_float(mark_row.get("mark_price")) if mark_row else 0.0,
                "open_interest": _safe_float(oi_row.get("open_interest")) if oi_row else 0.0,
                "quote_volume": _safe_float(candle.get("quote_volume")),
            }
        )
        del market_history[:-resolved_history_limit]

        if index < start_index:
            previous_price = price
            continue

        price_change_pct = 0.0
        if previous_price > 0:
            price_change_pct = round(((price - previous_price) / previous_price) * 100.0, 4)
        previous_price = price

        # 只喂截至当前分钟的 K 线——切片右边界是 index+1，绝不能包含未来。
        window_start = max(0, index + 1 - _KLINE_LOOKBACK_BARS)
        kline_slice = candles[window_start : index + 1]
        kline_context = summarize_kline_context({"1m": kline_slice})

        event_bundle = [_build_market_event(candle, symbol, timestamp_ms)]
        if mark_row:
            event_bundle.append(
                {
                    "event_type": "mark_price",
                    "symbol": symbol,
                    "exchange": "binance",
                    "price": _safe_float(mark_row.get("mark_price")),
                    "event_time": str(timestamp_ms),
                }
            )
        if funding_row:
            event_bundle.append(
                {
                    "event_type": "funding_rate",
                    "symbol": symbol,
                    "exchange": "binance",
                    "funding_rate": _safe_float(funding_row.get("funding_rate")),
                    "event_time": str(timestamp_ms),
                }
            )
        if oi_row:
            event_bundle.append(
                {
                    "event_type": "open_interest",
                    "symbol": symbol,
                    "exchange": "binance",
                    "open_interest": _safe_float(oi_row.get("open_interest")),
                    "open_interest_value": _safe_float(oi_row.get("open_interest_value")),
                    "event_time": str(timestamp_ms),
                }
            )

        feature_snapshot: dict[str, Any] = {
            "symbol": symbol,
            "price_change_pct": price_change_pct,
            "funding_rate": _safe_float(funding_row.get("funding_rate")) if funding_row else 0.0,
            "oi_change_pct": _oi_change_pct(market_history),
            # 历史里没有这三类数据，恒为 0；报告会把它们标为不可评估。
            "news_score": 0.0,
            "social_score": 0.0,
            "onchain_flow_bias": 0.0,
            "latest_price": price,
            "effective_price": price,
            "mark_price": _safe_float(mark_row.get("mark_price")) if mark_row else 0.0,
            "open_interest": _safe_float(oi_row.get("open_interest")) if oi_row else 0.0,
            "kline_price_change_pct": kline_context.get("price_change_pct") or {},
            "kline_quote_volume_ratio": kline_context.get("quote_volume_ratio") or {},
            "atr_pct": kline_context.get("atr_pct") or {},
            "rsi_14": kline_context.get("rsi_14") or {},
            "ema_trend": kline_context.get("ema_trend") or {},
            "kline_period_summaries": kline_context.get("period_summaries") or [],
            "kline_volume_price_signals": kline_context.get("volume_price_signals") or [],
        }
        feature_snapshot.update(_history_metrics(market_history))

        frames.append(
            {
                "timestamp_ms": timestamp_ms,
                "now": now_dt,
                "price": price,
                "event_bundle": event_bundle,
                "feature_snapshot": feature_snapshot,
            }
        )

    coverage = bundle.coverage()
    coverage["replayed_steps"] = len(frames)
    coverage["warmup_bars_skipped"] = start_index
    coverage["history_limit_samples"] = resolved_history_limit
    coverage["step_minutes"] = 1

    return ReplayFrames(symbol=symbol, frames=frames, coverage=coverage)


_INERT_DIMENSIONS = [
    # 无历史数据源，不是「阈值合适」而是「无法评估」
    "liquidation_notional_15m/60m/240m (no public REST history)",
    "news_score / social_score / onchain_flow_bias (aux feeds not replayed)",
    "triggerMatrix combinations (require aux sources above)",
    "signal memory windows (ActiveSignalStore not replayed)",
]


def evaluate_frames(
    prepared: ReplayFrames,
    *,
    runtime_config: dict[str, Any],
    strategy_context: dict[str, Any] | None = None,
    keep_snapshots: bool = False,
) -> ReplayResult:
    """用一套阈值判定已构建好的帧序列。

    判定本身仍然全部由生产的 ``classify_event_strength_from_policy`` 和
    ``evaluate_trigger_policy`` 作出，本函数不含任何阈值比较。
    """
    # trigger_state 在步与步之间携带，冷却与 LLM 预算才会真实累积——
    # 少了这一点，重放会高估触发次数（线上被冷却挡掉的会全部放行）。
    trigger_state: dict[str, Any] = {}
    steps: list[ReplayStep] = []

    for frame in prepared.frames:
        # 每帧的快照要独立一份：event_strength 依赖阈值，跨取值复用会串味。
        feature_snapshot = dict(frame["feature_snapshot"])
        event_bundle = frame["event_bundle"]
        now_dt = frame["now"]

        feature_snapshot["event_strength"] = classify_event_strength_from_policy(
            event_bundle=event_bundle,
            feature_snapshot=feature_snapshot,
            runtime_config=runtime_config,
            strategy_context=strategy_context,
            now=now_dt,
        )

        decision = evaluate_trigger_policy(
            event_bundle=event_bundle,
            feature_snapshot=feature_snapshot,
            # 离线不重建信号记忆窗口：它由 ActiveSignalStore 跨轮次维护，
            # 依赖线上 15 秒节奏。留空使重放只反映「当步新生成的信号」,
            # 因而对组合类触发是偏保守的下界。
            signal_window_states=[],
            runtime_account_context={},
            runtime_config=runtime_config,
            strategy_context=strategy_context,
            trigger_state=trigger_state,
            now=now_dt,
        )
        trigger_state = decision.get("trigger_state") or trigger_state

        active_signals = decision.get("active_signals") or []
        steps.append(
            ReplayStep(
                timestamp_ms=frame["timestamp_ms"],
                price=frame["price"],
                dispatch_mode=str(decision.get("dispatch_mode") or "NO_DISPATCH"),
                trigger_reason=str(decision.get("trigger_reason") or ""),
                trigger_source=str(decision.get("trigger_source") or ""),
                signal_types=[str(item.get("signal_type") or "") for item in active_signals],
                cooldown_blocked=bool(decision.get("cooldown_blocked")),
                budget_blocked=bool(decision.get("budget_blocked")),
                direction=str((active_signals[0].get("direction") if active_signals else "") or ""),
                feature_snapshot=dict(feature_snapshot) if keep_snapshots else {},
            )
        )

    return ReplayResult(
        symbol=prepared.symbol,
        steps=steps,
        coverage=dict(prepared.coverage),
        inert_dimensions=list(_INERT_DIMENSIONS),
    )


def replay_thresholds(
    bundle: HistoryBundle,
    *,
    runtime_config: dict[str, Any],
    strategy_context: dict[str, Any] | None = None,
    history_limit: int | None = None,
    warmup_bars: int = _KLINE_LOOKBACK_BARS,
    keep_snapshots: bool = False,
) -> ReplayResult:
    """逐分钟重放历史，用生产触发策略判定每一步。

    单次重放的便捷入口。网格扫描请改用 ``build_frames`` + ``evaluate_frames``,
    避免在每个取值上重复计算与阈值无关的指标。

    Args:
        bundle: ``load_history`` 的产物
        runtime_config: 与线上同形状的运行时配置（含 ``marketTrigger`` 阈值）
        strategy_context: 策略级覆盖，与线上语义一致
        history_limit: 行情历史窗口样本数；None 表示按线上 15 分钟窗口换算
        warmup_bars: 前多少根 K 线只用于填充指标窗口、不产生判定
        keep_snapshots: 是否保留每步完整快照（体积大，默认只在需要诊断时开）

    Returns:
        ReplayResult: 每一步的判定结果与覆盖度说明
    """
    prepared = build_frames(bundle, history_limit=history_limit, warmup_bars=warmup_bars)
    return evaluate_frames(
        prepared,
        runtime_config=runtime_config,
        strategy_context=strategy_context,
        keep_snapshots=keep_snapshots,
    )
def forward_return_pct(
    candles: list[dict[str, Any]], *, from_index: int, horizon_minutes: int
) -> float:
    """从某根 K 线收盘起、horizon 分钟后的收益率。

    用于判断触发是否「有意义」。注意这是**前瞻**收益，只能在评估阶段使用，
    绝不能进入 ``feature_snapshot``。
    """
    target = from_index + horizon_minutes
    if from_index < 0 or target >= len(candles):
        return 0.0
    start = _safe_float(candles[from_index].get("close"))
    end = _safe_float(candles[target].get("close"))
    if start <= 0:
        return 0.0
    return round((end - start) / start * 100.0, 4)


def timestamp_to_index(candles: list[dict[str, Any]]) -> dict[int, int]:
    return {int(candle.get("open_time") or 0): index for index, candle in enumerate(candles)}


def summarize_window(bundle: HistoryBundle) -> dict[str, Any]:
    """历史窗口的基本统计，用于判断这段样本是否有代表性。"""
    candles = sorted(bundle.candles, key=lambda item: int(item.get("open_time") or 0))
    if not candles:
        return {}
    closes = [_safe_float(item.get("close")) for item in candles if _safe_float(item.get("close")) > 0]
    if not closes:
        return {}
    minute_changes = [
        abs((closes[i] - closes[i - 1]) / closes[i - 1] * 100.0) for i in range(1, len(closes)) if closes[i - 1] > 0
    ]
    minute_changes.sort()

    def percentile(sorted_values: list[float], fraction: float) -> float:
        if not sorted_values:
            return 0.0
        index = min(len(sorted_values) - 1, max(0, int(round(fraction * (len(sorted_values) - 1)))))
        return round(sorted_values[index], 4)

    start_dt = datetime.fromtimestamp(int(candles[0]["open_time"]) / 1000.0, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(int(candles[-1]["open_time"]) / 1000.0, tz=timezone.utc)
    return {
        "start_utc": start_dt.isoformat(),
        "end_utc": end_dt.isoformat(),
        "days": round((end_dt - start_dt) / timedelta(days=1), 2),
        "first_close": closes[0],
        "last_close": closes[-1],
        "total_change_pct": round((closes[-1] - closes[0]) / closes[0] * 100.0, 4),
        "max_close": max(closes),
        "min_close": min(closes),
        "minute_abs_change_p50": percentile(minute_changes, 0.50),
        "minute_abs_change_p95": percentile(minute_changes, 0.95),
        "minute_abs_change_p99": percentile(minute_changes, 0.99),
    }
