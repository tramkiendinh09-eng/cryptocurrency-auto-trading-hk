"""阈值网格扫描与前瞻收益评估。

回答的问题是：把某个阈值设成 X，在这段历史上会触发多少次，这些触发之后
价格实际怎么走。

评价口径
--------
每次触发记录它之后 ``horizon_minutes`` 内的收益率，并按信号方向取符号
（看空信号下跌算正确）。汇总三个量：

``trigger_count``
    触发频次。太高意味着 LLM 预算会被噪音吃光（线上 ``rollingWindowLimit``
    是 20 分钟 3 次、每日 30 次），太低意味着阈值形同虚设。
``hit_rate``
    方向正确的比例。**这不是胜率**——没有考虑手续费、滑点、持仓时间和
    止损，只说明「信号发出后价格是否朝信号指向的方向动过」。
``mean_directional_return_pct``
    方向调整后的平均收益率。同样不含任何交易成本。

必须明确的局限
--------------
1. **这是信号质量评估，不是策略回测。** 触发之后真正的开仓决策由 LLM 和
   风控层作出，本模块完全不模拟那一层。一个 hit_rate 高的阈值不等于赚钱。
2. **单一时间窗的结论会过拟合。** 一段趋势行情能让任何顺势阈值看起来都好。
   ``sweep_threshold`` 因此支持把窗口切成多段分别评估，
   ``stability`` 字段报告各段之间的一致性——不稳定的最优值不该采纳。
3. **前瞻收益只在评估层使用**，绝不进入 ``feature_snapshot``。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .history import HistoryBundle
from .replay import (
    ReplayFrames,
    ReplayResult,
    build_frames,
    evaluate_frames,
    forward_return_pct,
    timestamp_to_index,
)

logger = logging.getLogger(__name__)


@dataclass
class ThresholdPoint:
    """网格上一个取值的评估结果。"""

    value: float
    trigger_count: int
    llm_count: int
    hit_rate: float
    mean_directional_return_pct: float
    median_directional_return_pct: float
    triggers_per_day: float
    cooldown_blocked: int = 0
    budget_blocked: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "trigger_count": self.trigger_count,
            "llm_count": self.llm_count,
            "hit_rate": self.hit_rate,
            "mean_directional_return_pct": self.mean_directional_return_pct,
            "median_directional_return_pct": self.median_directional_return_pct,
            "triggers_per_day": self.triggers_per_day,
            "cooldown_blocked": self.cooldown_blocked,
            "budget_blocked": self.budget_blocked,
        }


@dataclass
class SweepOutcome:
    """一个阈值键在整条网格上的扫描结果。"""

    threshold_key: str
    signal_type_filter: str
    horizon_minutes: int
    points: list[ThresholdPoint] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "threshold_key": self.threshold_key,
            "signal_type_filter": self.signal_type_filter,
            "horizon_minutes": self.horizon_minutes,
            "points": [point.as_dict() for point in self.points],
            "coverage": self.coverage,
            "notes": self.notes,
        }


def _direction_sign(direction: str) -> float:
    normalized = str(direction or "").strip().lower()
    if normalized == "bullish":
        return 1.0
    if normalized == "bearish":
        return -1.0
    return 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return round(ordered[middle], 4)
    return round((ordered[middle - 1] + ordered[middle]) / 2.0, 4)


def evaluate_replay(
    result: ReplayResult,
    bundle: HistoryBundle,
    *,
    horizon_minutes: int,
    signal_type_filter: str = "",
) -> dict[str, Any]:
    """给一次重放算前瞻收益指标。

    Args:
        result: ``replay_thresholds`` 的产物
        bundle: 对应的历史（用于取前瞻价格）
        horizon_minutes: 前瞻多少分钟
        signal_type_filter: 只统计包含该 signal_type 的触发；空串表示全部

    Returns:
        dict: 频次、命中率、方向收益等
    """
    candles = sorted(bundle.candles, key=lambda item: int(item.get("open_time") or 0))
    index_by_ts = timestamp_to_index(candles)

    directional_returns: list[float] = []
    trigger_count = 0
    llm_count = 0
    cooldown_blocked = 0
    budget_blocked = 0

    for step in result.steps:
        if step.dispatch_mode == "NO_DISPATCH":
            continue
        if signal_type_filter and not any(signal_type_filter in item for item in step.signal_types):
            continue
        trigger_count += 1
        if step.dispatch_mode == "LLM_ALLOWED":
            llm_count += 1
        if step.cooldown_blocked:
            cooldown_blocked += 1
        if step.budget_blocked:
            budget_blocked += 1

        sign = _direction_sign(step.direction)
        if sign == 0.0:
            continue
        index = index_by_ts.get(step.timestamp_ms)
        if index is None:
            continue
        forward = forward_return_pct(candles, from_index=index, horizon_minutes=horizon_minutes)
        directional_returns.append(round(forward * sign, 4))

    hit_rate = 0.0
    if directional_returns:
        hits = sum(1 for value in directional_returns if value > 0)
        hit_rate = round(hits / len(directional_returns), 4)

    mean_return = 0.0
    if directional_returns:
        mean_return = round(sum(directional_returns) / len(directional_returns), 4)

    days = max(0.0001, len(candles) / 1440.0)

    return {
        "trigger_count": trigger_count,
        "llm_count": llm_count,
        "hit_rate": hit_rate,
        "mean_directional_return_pct": mean_return,
        "median_directional_return_pct": _median(directional_returns),
        "triggers_per_day": round(trigger_count / days, 3),
        "cooldown_blocked": cooldown_blocked,
        "budget_blocked": budget_blocked,
        "evaluated_returns": len(directional_returns),
    }


def _with_threshold(base_config: dict[str, Any], threshold_key: str, value: float) -> dict[str, Any]:
    """深拷贝一份配置，只改一个 marketTrigger 阈值。"""
    config = {key: (dict(item) if isinstance(item, dict) else item) for key, item in base_config.items()}
    market_trigger = dict(config.get("marketTrigger") or {})
    market_trigger[threshold_key] = value
    config["marketTrigger"] = market_trigger
    return config


# 被扫描阈值之外的其他行情维度，扫描时需要关掉——否则它们会在同样的
# K 线上独立触发，把被测阈值的影响整个掩盖掉（不同取值得到相同的 dispatch 数）。
# 置 0 即关闭：``_current_signals`` 里每个维度都有 ``threshold > 0`` 的前置判断。
_ISOLATABLE_MARKET_THRESHOLDS = (
    "priceAccelerationPct",
    "fundingRateAbs",
    "markPriceDeviationPct",
    "klinePriceChangePct15m",
    "klinePriceChangePct60m",
    "klinePriceChangePct240m",
    "liquidationNotional15mUsd",
    "liquidationNotional60mUsd",
    "liquidationNotional240mUsd",
)

# priceChangePct 与 ruleOnlyPriceChangePct 是同一维度的两级（强/弱），
# 扫其中之一时不能把另一个关掉，否则该维度整体失效。
_PRICE_CHANGE_KEYS = ("priceChangePct", "ruleOnlyPriceChangePct")


def _isolate_dimension(config: dict[str, Any], threshold_key: str) -> dict[str, Any]:
    """关闭被测维度之外的其他行情触发。

    校准 A 的时候让 B 一起触发，测到的是 A∪B，不是 A。
    """
    isolated = {key: (dict(item) if isinstance(item, dict) else item) for key, item in config.items()}
    market_trigger = dict(isolated.get("marketTrigger") or {})
    keep = set(_PRICE_CHANGE_KEYS) if threshold_key in _PRICE_CHANGE_KEYS else {threshold_key}
    for key in _ISOLATABLE_MARKET_THRESHOLDS:
        if key not in keep:
            market_trigger[key] = 0.0
    if threshold_key not in _PRICE_CHANGE_KEYS:
        # 价格变化维度没有「置 0 即关闭」的开关（默认值 2.5 / 1.0 会在
        # _pick 取不到时兜底），只能抬到一个历史上不可能达到的值来屏蔽。
        market_trigger["priceChangePct"] = 1e9
        market_trigger["ruleOnlyPriceChangePct"] = 1e9
    isolated["marketTrigger"] = market_trigger
    return isolated


def sweep_threshold(
    bundle: HistoryBundle,
    *,
    threshold_key: str,
    values: list[float],
    base_config: dict[str, Any],
    horizon_minutes: int = 60,
    signal_type_filter: str = "",
    strategy_context: dict[str, Any] | None = None,
    warmup_bars: int = 500,
    isolate: bool = True,
    frames: ReplayFrames | None = None,
) -> SweepOutcome:
    """在一条网格上逐点重放并评估。

    与阈值无关的指标只算一次（``build_frames``），网格上每个取值复用它，
    再各自跑一遍生产触发策略——冷却与预算状态因此在每个取值内独立累积，
    这正是线上的行为。

    Args:
        bundle: 历史数据
        threshold_key: ``marketTrigger`` 下的键名，如 ``fundingRateAbs``
        values: 候选取值，建议由粗到细两轮
        base_config: 其余阈值保持不变的基线配置
        horizon_minutes: 前瞻窗口
        signal_type_filter: 只统计特定信号类型产生的触发
        strategy_context: 策略级覆盖
        warmup_bars: 指标预热长度
        isolate: 是否关闭其他行情维度。默认 True——单独校准一个阈值时,
            其他维度同时触发会让不同取值得到相同结果。设 False 可以看
            整套阈值组合起来的真实触发频次
        frames: 复用已构建的帧序列；跨多个阈值扫描时传入可省下重复的指标计算

    Returns:
        SweepOutcome: 网格上每点的评估
    """
    points: list[ThresholdPoint] = []
    prepared = frames or build_frames(bundle, warmup_bars=warmup_bars)
    coverage: dict[str, Any] = dict(prepared.coverage)

    for value in values:
        config = _with_threshold(base_config, threshold_key, value)
        if isolate:
            config = _isolate_dimension(config, threshold_key)
        result = evaluate_frames(
            prepared,
            runtime_config=config,
            strategy_context=strategy_context,
        )
        metrics = evaluate_replay(
            result,
            bundle,
            horizon_minutes=horizon_minutes,
            signal_type_filter=signal_type_filter,
        )
        points.append(
            ThresholdPoint(
                value=value,
                trigger_count=metrics["trigger_count"],
                llm_count=metrics["llm_count"],
                hit_rate=metrics["hit_rate"],
                mean_directional_return_pct=metrics["mean_directional_return_pct"],
                median_directional_return_pct=metrics["median_directional_return_pct"],
                triggers_per_day=metrics["triggers_per_day"],
                cooldown_blocked=metrics["cooldown_blocked"],
                budget_blocked=metrics["budget_blocked"],
            )
        )
        logger.info(
            "swept %s=%s triggers=%s hit_rate=%s mean=%s",
            threshold_key,
            value,
            metrics["trigger_count"],
            metrics["hit_rate"],
            metrics["mean_directional_return_pct"],
        )

    notes: list[str] = []
    if isolate:
        notes.append("已关闭被测维度之外的其他行情触发，频次仅反映该维度自身")
    if signal_type_filter:
        notes.append(f"仅统计 signal_type 含 '{signal_type_filter}' 的触发")
    notes.append("hit_rate 与收益均不含手续费、滑点与持仓管理，仅衡量信号方向性")

    return SweepOutcome(
        threshold_key=threshold_key,
        signal_type_filter=signal_type_filter,
        horizon_minutes=horizon_minutes,
        points=points,
        coverage=coverage,
        notes=notes,
    )


def recommend(
    outcome: SweepOutcome,
    *,
    min_triggers_per_day: float = 0.5,
    max_triggers_per_day: float = 12.0,
    min_evaluated: int = 8,
) -> dict[str, Any]:
    """从扫描结果里挑一个可采纳的取值。

    选择逻辑刻意保守：先用频次带把明显不可用的取值排除（太密会打爆 LLM
    预算，太疏则阈值等于没设），再在剩下的里选方向收益最高的。**不**单看
    hit_rate——样本少的时候它极易虚高。

    频次带的依据是线上预算：``rollingWindowLimit`` 20 分钟 3 次、
    ``perSymbolDailyLimit`` 每日 30 次。上界取 12 是给多标的和其他信号源
    留余量。

    Returns:
        dict: 推荐值与理由；样本不足时 ``recommended`` 为 None
    """
    eligible = [
        point
        for point in outcome.points
        if min_triggers_per_day <= point.triggers_per_day <= max_triggers_per_day
        and point.trigger_count >= min_evaluated
    ]
    if not eligible:
        return {
            "threshold_key": outcome.threshold_key,
            "recommended": None,
            "reason": (
                f"没有取值同时满足频次带 [{min_triggers_per_day}, {max_triggers_per_day}]/天 "
                f"且触发数 ≥ {min_evaluated}；样本不足以支持推荐"
            ),
            "candidates": [point.as_dict() for point in outcome.points],
        }

    best = max(eligible, key=lambda point: (point.mean_directional_return_pct, point.hit_rate))
    return {
        "threshold_key": outcome.threshold_key,
        "recommended": best.value,
        "reason": (
            f"在频次带内方向收益最高：{best.triggers_per_day}/天，"
            f"命中率 {best.hit_rate}，平均方向收益 {best.mean_directional_return_pct}%"
        ),
        "recommended_point": best.as_dict(),
        "candidates": [point.as_dict() for point in outcome.points],
    }
