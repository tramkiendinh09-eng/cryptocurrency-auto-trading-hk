"""
触发策略模块 - 决定何时触发交易决策

实现交易触发策略的评估逻辑，是交易系统的"大脑前哨"。

核心功能:
1. 事件强度分类: 将市场事件分为strong/normal/noise三个级别
2. 多源信号评估: 综合评估市场、新闻、链上、社交四类信号
3. 信号组合匹配: 支持多信号组合触发(如"新闻+市场"组合)
4. 冷却期控制: 防止过于频繁的交易决策
5. LLM预算控制: 控制AI模型调用频率和成本

触发策略配置:
- marketTrigger: 市场触发条件(价格变化、清算、资金费率等)
- newsTrigger: 新闻触发条件(情绪得分阈值)
- onchainTrigger: 链上触发条件(大额转账、智能合约活动)
- socialTrigger: 社交触发条件(舆情情绪得分)
- triggerMatrix: 信号组合触发矩阵
- cooldownPolicy: 全局冷却期策略
- llmBudgetPolicy: LLM调用预算策略

分发模式(dispatch_mode):
- NO_DISPATCH: 不触发交易决策
- RULE_ONLY: 仅使用规则决策，不调用LLM
- LLM_ALLOWED: 允许调用LLM进行决策

工作流程:
```
事件包 + 特征快照
       │
       ▼
提取当前信号(市场/新闻/链上/社交)
       │
       ▼
与历史信号窗口合并
       │
       ▼
检查信号组合匹配
       │
       ▼
应用冷却期和预算控制
       │
       ▼
确定分发模式和选中Agent
```
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from trade_runtime.llm_budget import evaluate_llm_budget


_DISPATCH_RANK = {
    "NO_DISPATCH": 0,
    "RULE_ONLY": 1,
    "LLM_ALLOWED": 2,
}

_AGENT_ORDER = ["market_agent", "news_agent", "onchain_agent", "social_agent"]


def _parse_datetime(value: Any) -> datetime | None:
    """解析日期时间值

    支持datetime对象和ISO格式字符串。

    Args:
        value: 日期时间值

    Returns:
        datetime | None: 解析后的datetime对象，失败返回None
    """
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数

    Args:
        value: 待转换值
        default: 默认值

    Returns:
        float: 转换后的浮点数
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数

    Args:
        value: 待转换值
        default: 默认值

    Returns:
        int: 转换后的整数
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _deep_merge(base: Any, override: Any) -> Any:
    """深度合并两个字典

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        Any: 合并后的字典
    """
    if not isinstance(base, dict) or not isinstance(override, dict):
        return deepcopy(override) if override not in (None, "") else deepcopy(base)
    merged = deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _pick(data: dict[str, Any], *keys: str) -> Any:
    """从字典中按优先级选取值

    Args:
        data: 数据字典
        keys: 候选键名列表

    Returns:
        Any: 第一个非空值，全部为空则返回None
    """
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _normalize_dispatch_mode(value: Any) -> str:
    """标准化分发模式

    Args:
        value: 分发模式值

    Returns:
        str: 标准化后的分发模式
    """
    normalized = str(value or "").strip().upper()
    return normalized if normalized in _DISPATCH_RANK else "NO_DISPATCH"


def _is_enabled_flag(value: Any, default: bool = True) -> bool:
    """检查是否为启用标志

    Args:
        value: 标志值
        default: 默认值

    Returns:
        bool: 是否启用
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def _direction_from_value(value: Any) -> str:
    """从数值判断方向

    Args:
        value: 数值

    Returns:
        str: 方向（bullish/bearish/neutral）
    """
    numeric = _safe_float(value)
    if numeric > 0:
        return "bullish"
    if numeric < 0:
        return "bearish"
    return "neutral"


def _direction_from_liquidation_event(event: dict[str, Any], fallback: str = "neutral") -> str:
    """从清算事件判断方向

    Args:
        event: 清算事件
        fallback: 默认方向

    Returns:
        str: 方向
    """
    side = str(event.get("side") or event.get("liquidationSide") or "").strip().upper()
    if side == "SELL":
        return "bearish"
    if side == "BUY":
        return "bullish"
    return fallback


#: 会被送去评估的 Wyckoff 就绪度。
#:
#: 原来只收 ready。ready 要求七项条件连续全过——成交量效果一致、高周期
#: 不冲突、突破被确认、高周期确认、无诱多诱空、回踩站稳、未追高——任何
#: 一项不满足就降级成 watch 然后被整条丢弃，模型连看都看不到。实测这就是
#: 决策几乎恒为 SKIP 的主因：绝大多数 SKIP 的理由都是
#: "Wyckoff status/readiness avoid"。
#:
#: watch 的含义是"结构成立，差一项确认"，那正是值得让模型看一眼再定夺的
#: 情形，而不是应该在门口就拦掉的情形。最终开不开仓仍由模型判断。
_DISPATCHABLE_READINESS = {"ready", "watch"}

#: watch 的强度折算系数。它比 ready 弱是事实，不该同权重参与信号合成，
#: 但打折之后仍要高于噪声，否则等于没放进来。
_WATCH_STRENGTH_FACTOR = 0.8


#: watch 级信号默认不占用 LLM 预算。
#:
#: 30 天历史上量过（calibration/readiness_edge.py，209 分钟持仓的前向收益）：
#:
#:     ready   n=163   均 +0.3904%   t=3.11  显著为正   扣费后 +0.3104%
#:     watch   n=1773  均 +0.0092%   t=0.25  与 0 无异   扣费后 -0.0708% 转负
#:
#: 两组差异 t=2.92 显著。而 watch : ready = 10.9 : 1——按数量分配预算的话
#: watch 会拿走约 92%，把唯一被证明有优势的信号挤出去。
#:
#: 此前把 watch 提到 LLM_ALLOWED 是为了让系统敢开仓（当时没有数据），
#: 现在数据说那一步是错的。watch 仍然进信号合成、仍然提供上下文，只是
#: 不再触发 LLM 决策。想退回旧行为把这个开关打开即可。
_WATCH_DISPATCH_MODE_KEY = "wyckoffWatchDispatchesLlm"


def _wyckoff_dispatch_mode(wyckoff_signal: dict[str, Any], resolved_policy: dict[str, Any]) -> str:
    readiness = str(wyckoff_signal.get("trade_readiness") or "").strip().lower()
    if readiness != "watch":
        return "LLM_ALLOWED"
    raw = resolved_policy.get(_WATCH_DISPATCH_MODE_KEY)
    if raw is None:
        raw = resolved_policy.get("wyckoff_watch_dispatches_llm")
    if isinstance(raw, bool):
        allow = raw
    elif raw in (None, ""):
        allow = False
    else:
        allow = str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}
    return "LLM_ALLOWED" if allow else "RULE_ONLY"


def _ready_wyckoff_shortterm_signal(feature_snapshot: dict[str, Any]) -> dict[str, Any] | None:
    """提取Wyckoff短期信号

    从特征快照中提取可供评估的Wyckoff短期交易信号（ready 或 watch）。

    Args:
        feature_snapshot: 特征快照

    Returns:
        dict[str, Any] | None: 信号数据，无效时返回None
    """
    signal = feature_snapshot.get("wyckoff_shortterm")
    if not isinstance(signal, dict):
        return None
    trigger = str(signal.get("trigger") or "").strip().lower()
    entry_bias = str(signal.get("entry_bias") or "").strip().lower()
    trade_readiness = str(signal.get("trade_readiness") or "").strip().lower()
    if (
        trigger in {"", "none"}
        or entry_bias not in {"bullish", "bearish"}
        or trade_readiness not in _DISPATCHABLE_READINESS
    ):
        return None
    confidence = _safe_float(signal.get("confidence"), 0.0)
    if confidence > 1.0:
        confidence = confidence / 100.0
    strength_score = max(0.5, confidence)
    if trade_readiness == "watch":
        strength_score *= _WATCH_STRENGTH_FACTOR
    return {
        "direction": entry_bias,
        "trigger": trigger,
        "trade_readiness": trade_readiness,
        "strength_score": strength_score,
    }


def _policy_defaults() -> dict[str, Any]:
    """获取默认触发策略配置

    Returns:
        dict[str, Any]: 默认配置字典
    """
    return {
        "triggerMode": "EVENT_GATED",
        "marketTrigger": {
            "priceChangePct": 2.5,
            "ruleOnlyPriceChangePct": 1.0,
            "priceAccelerationPct": 1.2,
            "liquidationNotionalUsd": 250000,
            "fundingRateAbs": 0.0,
            "markPriceDeviationPct": 0.0,
            "klinePriceChangePct15m": 0.0,
            "klinePriceChangePct60m": 0.0,
            "klinePriceChangePct240m": 0.0,
            "liquidationNotional15mUsd": 0.0,
            "liquidationNotional60mUsd": 0.0,
            "liquidationNotional240mUsd": 0.0,
        },
        "newsTrigger": {
            "scoreThreshold": 0.9,
            "ruleOnlyScoreThreshold": 0.7,
        },
        "onchainTrigger": {
            "scoreThreshold": 0.9,
            "ruleOnlyScoreThreshold": 0.7,
            "flowUsdThreshold": 1000000,
            "ruleOnlyFlowUsdThreshold": 250000,
        },
        "socialTrigger": {
            "scoreThreshold": 0.85,
            "ruleOnlyScoreThreshold": 0.65,
        },
        "signalMemoryPolicy": {
            "market": {"ttlSeconds": 300, "decayMode": "linear", "combineWithinSeconds": 300},
            "news": {"ttlSeconds": 900, "decayMode": "linear", "combineWithinSeconds": 900},
            "onchain": {"ttlSeconds": 1800, "decayMode": "linear", "combineWithinSeconds": 1800},
            "social": {"ttlSeconds": 600, "decayMode": "linear", "combineWithinSeconds": 600},
        },
        "triggerMatrix": [
            {"code": "strong_news_then_break", "sources": ["news", "market"], "targetDispatchMode": "LLM_ALLOWED"},
            {"code": "onchain_then_market_weakness", "sources": ["onchain", "market"], "targetDispatchMode": "LLM_ALLOWED"},
            {"code": "social_news_market_chain", "sources": ["social", "news", "market"], "targetDispatchMode": "LLM_ALLOWED"},
        ],
        "cooldownPolicy": {"globalSeconds": 180},
        "llmBudgetPolicy": {"perSymbolDailyLimit": 30, "rollingWindowLimit": 3, "rollingWindowMinutes": 20},
        "dedupePolicy": {"sameDirectionOnly": True, "dedupeWindowSeconds": 300},
        "wyckoffShortterm": {
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
        },
    }


def _resolve_policy(runtime_config: dict[str, Any] | None, strategy_context: dict[str, Any] | None) -> dict[str, Any]:
    """解析触发策略配置

    合并运行时配置和策略上下文中的触发策略配置。

    Args:
        runtime_config: 运行时配置
        strategy_context: 策略上下文

    Returns:
        dict[str, Any]: 合并后的策略配置
    """
    runtime_payload = runtime_config if isinstance(runtime_config, dict) else {}
    strategy_payload = strategy_context if isinstance(strategy_context, dict) else {}
    strategy_config = strategy_payload.get("strategy_config")
    if not isinstance(strategy_config, dict):
        strategy_config = {}

    trigger_policy = _pick(strategy_config, "triggerPolicy", "trigger_policy")
    if not isinstance(trigger_policy, dict):
        trigger_policy = {}
    signal_memory_overrides = _pick(strategy_config, "signalMemoryOverrides", "signal_memory_overrides")
    if not isinstance(signal_memory_overrides, dict):
        signal_memory_overrides = {}
    trigger_matrix_overrides = _pick(strategy_config, "triggerMatrixOverrides", "trigger_matrix_overrides")
    if not isinstance(trigger_matrix_overrides, list):
        trigger_matrix_overrides = []

    defaults = _policy_defaults()
    return {
        "trigger_mode": str(
            _pick(trigger_policy, "triggerMode", "trigger_mode")
            or _pick(runtime_payload, "trigger_mode", "triggerMode")
            or defaults["triggerMode"]
        ).strip().upper(),
        "market_trigger": _deep_merge(
            _deep_merge(defaults["marketTrigger"], _pick(runtime_payload, "market_trigger", "marketTrigger") or {}),
            _pick(trigger_policy, "marketTrigger", "market_trigger") or {},
        ),
        "news_trigger": _deep_merge(
            _deep_merge(defaults["newsTrigger"], _pick(runtime_payload, "news_trigger", "newsTrigger") or {}),
            _pick(trigger_policy, "newsTrigger", "news_trigger") or {},
        ),
        "onchain_trigger": _deep_merge(
            _deep_merge(defaults["onchainTrigger"], _pick(runtime_payload, "onchain_trigger", "onchainTrigger") or {}),
            _pick(trigger_policy, "onchainTrigger", "onchain_trigger") or {},
        ),
        "social_trigger": _deep_merge(
            _deep_merge(defaults["socialTrigger"], _pick(runtime_payload, "social_trigger", "socialTrigger") or {}),
            _pick(trigger_policy, "socialTrigger", "social_trigger") or {},
        ),
        "signal_memory_policy": _deep_merge(
            _deep_merge(defaults["signalMemoryPolicy"], _pick(runtime_payload, "signal_memory_policy", "signalMemoryPolicy") or {}),
            signal_memory_overrides,
        ),
        "trigger_matrix": trigger_matrix_overrides or _pick(runtime_payload, "trigger_matrix", "triggerMatrix") or defaults["triggerMatrix"],
        "cooldown_policy": _deep_merge(defaults["cooldownPolicy"], _pick(runtime_payload, "cooldown_policy", "cooldownPolicy") or {}),
        "llm_budget_policy": _deep_merge(defaults["llmBudgetPolicy"], _pick(runtime_payload, "llm_budget_policy", "llmBudgetPolicy") or {}),
        "dedupe_policy": _deep_merge(defaults["dedupePolicy"], _pick(runtime_payload, "dedupe_policy", "dedupePolicy") or {}),
        "wyckoff_shortterm": _deep_merge(
            _deep_merge(defaults["wyckoffShortterm"], _pick(runtime_payload, "wyckoff_shortterm", "wyckoffShortterm") or {}),
            _pick(trigger_policy, "wyckoffShortterm", "wyckoff_shortterm") or {},
        ),
        "specialist_routing": _pick(strategy_config, "specialistRouting", "specialist_routing") or {},
    }


def resolve_trigger_policy(
    *,
    runtime_config: dict[str, Any] | None,
    strategy_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """解析触发策略配置（公开接口）

    Args:
        runtime_config: 运行时配置
        strategy_context: 策略上下文

    Returns:
        dict[str, Any]: 策略配置
    """
    return _resolve_policy(
        runtime_config if isinstance(runtime_config, dict) else {},
        strategy_context if isinstance(strategy_context, dict) else {},
    )


def _ordered_agents(values: list[str]) -> list[str]:
    unique: list[str] = []
    for item in values:
        normalized = str(item or "").strip().lower()
        if normalized and normalized not in unique:
            unique.append(normalized)
    return sorted(unique, key=lambda item: (_AGENT_ORDER.index(item) if item in _AGENT_ORDER else len(_AGENT_ORDER), item))


def _source_agent_defaults(source_type: str) -> list[str]:
    if source_type == "news":
        return ["market_agent", "news_agent"]
    if source_type == "onchain":
        return ["market_agent", "onchain_agent"]
    if source_type == "social":
        return ["market_agent", "social_agent"]
    return ["market_agent"]


def _resolve_selected_agents(source_types: list[str], strategy_context: dict[str, Any] | None, combination_code: str = "") -> list[str]:
    strategy_payload = strategy_context if isinstance(strategy_context, dict) else {}
    strategy_config = strategy_payload.get("strategy_config")
    if not isinstance(strategy_config, dict):
        strategy_config = {}
    specialist_routing = _pick(strategy_config, "specialistRouting", "specialist_routing")
    if not isinstance(specialist_routing, dict):
        specialist_routing = {}
    enabled_agents = {
        str(profile.get("agent_code") or "").strip().lower()
        for profile in (strategy_payload.get("agent_profiles") or [])
        if isinstance(profile, dict) and _is_enabled_flag(profile.get("enabled"), default=True)
    }

    if combination_code:
        combination_agents = specialist_routing.get(combination_code)
        if isinstance(combination_agents, list) and combination_agents:
            ordered_agents = _ordered_agents([str(item) for item in combination_agents])
            if enabled_agents:
                ordered_agents = [agent_code for agent_code in ordered_agents if agent_code in enabled_agents]
            return ordered_agents

    normalized_source_types = [
        str(source_type or "").strip().lower()
        for source_type in source_types
        if str(source_type or "").strip()
    ]
    market_only_dispatch = len(set(normalized_source_types)) == 1 and normalized_source_types[:1] == ["market"] and not combination_code
    selected: list[str] = []
    for source_type in source_types:
        override_agents = specialist_routing.get(source_type)
        if isinstance(override_agents, list) and override_agents:
            selected.extend(str(item) for item in override_agents)
        elif market_only_dispatch and str(source_type or "").strip().lower() == "market":
            selected.extend(["market_agent", "news_agent", "onchain_agent", "social_agent"])
        else:
            selected.extend(_source_agent_defaults(source_type))
    ordered_selected = _ordered_agents(selected)
    if enabled_agents:
        ordered_selected = [agent_code for agent_code in ordered_selected if agent_code in enabled_agents]
    return ordered_selected


def _candidate_signal(
    *,
    symbol: str,
    source_type: str,
    signal_type: str,
    direction: str,
    strength_score: float,
    dispatch_mode: str,
    now: datetime,
    signal_memory_policy: dict[str, Any],
    dedupe_key: str,
) -> dict[str, Any]:
    source_policy = signal_memory_policy.get(source_type) if isinstance(signal_memory_policy, dict) else {}
    if not isinstance(source_policy, dict):
        source_policy = {}
    ttl_seconds = max(1, _safe_int(_pick(source_policy, "ttlSeconds", "ttl_seconds"), 300))
    combine_seconds = max(
        ttl_seconds,
        _safe_int(_pick(source_policy, "combineWithinSeconds", "combine_within_seconds"), ttl_seconds),
    )
    return {
        "symbol": symbol,
        "source_type": source_type,
        "signal_type": signal_type,
        "direction": direction,
        "strength_score": round(strength_score, 4),
        "decay_score": round(strength_score, 4),
        "opened_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "last_event_at": now.isoformat(),
        "last_confirmed_at": now.isoformat(),
        "dedupe_key": dedupe_key,
        "combine_until_at": (now + timedelta(seconds=combine_seconds)).isoformat(),
        "active": True,
        "dispatch_mode": dispatch_mode,
        "current_signal": True,
    }


def _normalize_signal_window_state(signal_window_state: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    source_type = str(signal_window_state.get("source_type") or "").strip().lower()
    if not source_type:
        window_key = str(signal_window_state.get("window_key") or signal_window_state.get("windowKey") or "").strip().lower()
        if ":" in window_key:
            source_type = window_key.split(":", 1)[0]
    if not source_type:
        return None

    active = signal_window_state.get("active")
    if active is None:
        active = signal_window_state.get("is_active")
    expires_at = _parse_datetime(signal_window_state.get("expires_at") or signal_window_state.get("expiresAt"))
    combine_until_at = _parse_datetime(signal_window_state.get("combine_until_at") or signal_window_state.get("combineUntilAt"))
    if expires_at is not None and expires_at < now:
        return None
    if combine_until_at is not None and combine_until_at < now:
        return None
    if active is False or str(active).strip() == "0":
        return None

    state_payload = signal_window_state.get("state")
    if not isinstance(state_payload, dict):
        state_payload = {}

    direction = str(signal_window_state.get("direction") or "").strip().lower()
    if not direction:
        direction = _direction_from_value(
            signal_window_state.get("strength_score")
            or state_payload.get("price_change_pct")
            or state_payload.get("max_score")
            or state_payload.get("flow_bias")
        )
    if direction == "neutral":
        return None

    strength_score = abs(
        _safe_float(
            signal_window_state.get("decay_score")
            or signal_window_state.get("strength_score")
            or state_payload.get("price_change_pct")
            or state_payload.get("max_score")
            or state_payload.get("flow_bias")
        )
    )
    return {
        "symbol": str(signal_window_state.get("symbol") or state_payload.get("symbol") or "").strip(),
        "source_type": source_type,
        "signal_type": str(signal_window_state.get("signal_type") or signal_window_state.get("signalType") or source_type).strip().lower(),
        "direction": direction,
        "strength_score": round(strength_score, 4),
        "decay_score": round(abs(_safe_float(signal_window_state.get("decay_score"), strength_score)), 4),
        "opened_at": str(signal_window_state.get("opened_at") or signal_window_state.get("openedAt") or ""),
        "expires_at": expires_at.isoformat() if expires_at is not None else "",
        "last_event_at": str(signal_window_state.get("last_event_at") or signal_window_state.get("lastEventAt") or ""),
        "last_confirmed_at": str(signal_window_state.get("last_confirmed_at") or signal_window_state.get("lastConfirmedAt") or ""),
        "dedupe_key": str(signal_window_state.get("dedupe_key") or signal_window_state.get("dedupeKey") or signal_window_state.get("window_key") or signal_window_state.get("windowKey") or f"{source_type}:window").strip(),
        "combine_until_at": combine_until_at.isoformat() if combine_until_at is not None else (expires_at.isoformat() if expires_at is not None else ""),
        "active": True,
        "dispatch_mode": _normalize_dispatch_mode(signal_window_state.get("dispatch_mode") or "RULE_ONLY"),
        "current_signal": False,
    }


def _current_signals(
    event_bundle: list[dict[str, Any]],
    feature_snapshot: dict[str, Any],
    resolved_policy: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    symbol = str(
        feature_snapshot.get("symbol")
        or next((item.get("symbol") for item in event_bundle if isinstance(item, dict) and item.get("symbol")), "")
        or ""
    ).strip()
    signals: list[dict[str, Any]] = []

    position_risk_event = next(
        (
            item
            for item in reversed(event_bundle)
            if str(item.get("event_type") or "").strip().lower() == "position_risk"
        ),
        None,
    )
    if isinstance(position_risk_event, dict):
        risk_direction = str(position_risk_event.get("direction") or "risk").strip().lower() or "risk"
        severity = str(position_risk_event.get("severity") or "review").strip().lower()
        severity_score = {"review": 1.0, "reduce": 1.5, "close": 2.0}.get(severity, 1.0)
        signals.append(
            _candidate_signal(
                symbol=symbol or str(position_risk_event.get("symbol") or "").strip(),
                source_type="position_risk",
                signal_type=f"position_risk_{severity}",
                direction=risk_direction,
                strength_score=severity_score,
                dispatch_mode="LLM_ALLOWED",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"position_risk:{position_risk_event.get('position_side') or risk_direction}:{severity}",
            )
        )

    snapshot_price_change_pct = _safe_float(feature_snapshot.get("price_change_pct"))
    window_price_change_pct = _safe_float(feature_snapshot.get("market_window_price_change_pct"))
    price_change_pct = (
        window_price_change_pct
        if abs(window_price_change_pct) > abs(snapshot_price_change_pct)
        else snapshot_price_change_pct
    )
    market_direction = _direction_from_value(price_change_pct)
    market_strong = _safe_float(_pick(resolved_policy["market_trigger"], "priceChangePct", "price_change_pct"), 2.5)
    market_rule = _safe_float(_pick(resolved_policy["market_trigger"], "ruleOnlyPriceChangePct", "rule_only_price_change_pct"), 1.0)
    if abs(price_change_pct) >= market_rule and market_direction != "neutral":
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="market",
                signal_type="price_break",
                direction=market_direction,
                strength_score=abs(price_change_pct) / max(market_strong, 0.0001),
                dispatch_mode="LLM_ALLOWED" if abs(price_change_pct) >= market_strong else "RULE_ONLY",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"market:{market_direction}",
            )
        )

    wyckoff_signal = _ready_wyckoff_shortterm_signal(feature_snapshot)
    if wyckoff_signal is not None:
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="market",
                signal_type="wyckoff_shortterm",
                direction=str(wyckoff_signal.get("direction") or "neutral"),
                strength_score=_safe_float(wyckoff_signal.get("strength_score"), 0.5),
                dispatch_mode=_wyckoff_dispatch_mode(wyckoff_signal, resolved_policy),
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                # 就绪度进 dedupe key：watch 升级成 ready 是一次新的、更强的
                # 信号，不能被 5 分钟内那条 watch 去重掉。
                dedupe_key=(
                    f"market:wyckoff:{str(wyckoff_signal.get('trigger') or 'ready').strip().lower()}"
                    f":{str(wyckoff_signal.get('trade_readiness') or 'ready').strip().lower()}"
                ),
            )
        )

    price_acceleration_pct = _safe_float(feature_snapshot.get("market_price_acceleration_pct"))
    acceleration_direction = _direction_from_value(price_acceleration_pct)
    acceleration_threshold = _safe_float(
        _pick(resolved_policy["market_trigger"], "priceAccelerationPct", "price_acceleration_pct"),
        0.0,
    )
    if acceleration_threshold > 0 and abs(price_acceleration_pct) >= acceleration_threshold and acceleration_direction != "neutral":
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="market",
                signal_type="price_acceleration",
                direction=acceleration_direction,
                strength_score=abs(price_acceleration_pct) / max(acceleration_threshold, 0.0001),
                dispatch_mode="LLM_ALLOWED",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"market:acceleration:{acceleration_direction}",
            )
        )

    funding_rate = _safe_float(feature_snapshot.get("funding_rate"))
    funding_threshold = _safe_float(_pick(resolved_policy["market_trigger"], "fundingRateAbs", "funding_rate_abs"), 0.0)
    funding_direction = _direction_from_value(funding_rate)
    if funding_threshold > 0 and abs(funding_rate) >= funding_threshold and funding_direction != "neutral":
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="market",
                signal_type="funding_rate_extreme",
                direction=funding_direction,
                strength_score=abs(funding_rate) / max(funding_threshold, 0.0001),
                dispatch_mode="LLM_ALLOWED",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"market:funding:{funding_direction}",
            )
        )

    mark_price_deviation_pct = _safe_float(feature_snapshot.get("mark_price_deviation_pct"))
    mark_deviation_threshold = _safe_float(
        _pick(resolved_policy["market_trigger"], "markPriceDeviationPct", "mark_price_deviation_pct"),
        0.0,
    )
    mark_direction = _direction_from_value(mark_price_deviation_pct)
    if mark_deviation_threshold > 0 and abs(mark_price_deviation_pct) >= mark_deviation_threshold and mark_direction != "neutral":
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="market",
                signal_type="mark_price_deviation",
                direction=mark_direction,
                strength_score=abs(mark_price_deviation_pct) / max(mark_deviation_threshold, 0.0001),
                dispatch_mode="LLM_ALLOWED",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"market:mark_deviation:{mark_direction}",
            )
        )

    kline_price_changes = feature_snapshot.get("kline_price_change_pct")
    if not isinstance(kline_price_changes, dict):
        kline_price_changes = {}
    for window, threshold_key in (
        ("15m", "klinePriceChangePct15m"),
        ("60m", "klinePriceChangePct60m"),
        ("240m", "klinePriceChangePct240m"),
    ):
        threshold = _safe_float(_pick(resolved_policy["market_trigger"], threshold_key), 0.0)
        change_pct = _safe_float(kline_price_changes.get(window), 0.0)
        direction = _direction_from_value(change_pct)
        if threshold > 0 and abs(change_pct) >= threshold and direction != "neutral":
            signals.append(
                _candidate_signal(
                    symbol=symbol,
                    source_type="market",
                    signal_type=f"kline_price_change_{window}",
                    direction=direction,
                    strength_score=abs(change_pct) / max(threshold, 0.0001),
                    dispatch_mode="LLM_ALLOWED",
                    now=now,
                    signal_memory_policy=resolved_policy["signal_memory_policy"],
                    dedupe_key=f"market:kline:{window}:{direction}",
                )
            )

    for window, threshold_key, snapshot_key in (
        ("15m", "liquidationNotional15mUsd", "liquidation_notional_15m"),
        ("60m", "liquidationNotional60mUsd", "liquidation_notional_60m"),
        ("240m", "liquidationNotional240mUsd", "liquidation_notional_240m"),
    ):
        threshold = _safe_float(_pick(resolved_policy["market_trigger"], threshold_key), 0.0)
        notional = _safe_float(feature_snapshot.get(snapshot_key), 0.0)
        if threshold > 0 and notional >= threshold:
            signals.append(
                _candidate_signal(
                    symbol=symbol,
                    source_type="market",
                    signal_type=f"liquidation_aggregate_{window}",
                    direction=str(feature_snapshot.get("largest_liquidation_side") or "neutral").strip().lower() or "neutral",
                    strength_score=notional / max(threshold, 0.0001),
                    dispatch_mode="LLM_ALLOWED",
                    now=now,
                    signal_memory_policy=resolved_policy["signal_memory_policy"],
                    dedupe_key=f"market:liquidation:{window}",
                )
            )

    liquidation_events = [item for item in event_bundle if str(item.get("event_type") or "").strip().lower() == "liquidation"]
    liquidation_threshold = _safe_float(
        _pick(resolved_policy["market_trigger"], "liquidationNotionalUsd", "liquidation_notional_usd"),
        250000,
    )
    liquidation_event = max(
        liquidation_events,
        key=lambda item: _safe_float(item.get("notionalUsd") or item.get("notional_usd")),
        default=None,
    )
    liquidation_notional = (
        _safe_float(liquidation_event.get("notionalUsd") or liquidation_event.get("notional_usd"))
        if isinstance(liquidation_event, dict)
        else 0.0
    )
    liquidation_direction = (
        _direction_from_liquidation_event(liquidation_event, fallback=market_direction)
        if isinstance(liquidation_event, dict)
        else "neutral"
    )
    if liquidation_notional >= liquidation_threshold and liquidation_direction != "neutral":
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="market",
                signal_type="liquidation",
                direction=liquidation_direction,
                strength_score=liquidation_notional / max(liquidation_threshold, 1.0),
                dispatch_mode="LLM_ALLOWED",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"market:liquidation:{liquidation_direction}",
            )
        )

    news_score = _safe_float(feature_snapshot.get("news_score"))
    news_direction = _direction_from_value(news_score)
    news_strong = _safe_float(_pick(resolved_policy["news_trigger"], "scoreThreshold", "score_threshold"), 0.9)
    news_rule = _safe_float(_pick(resolved_policy["news_trigger"], "ruleOnlyScoreThreshold", "rule_only_score_threshold"), 0.7)
    if abs(news_score) >= news_rule and news_direction != "neutral":
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="news",
                signal_type="headline",
                direction=news_direction,
                strength_score=abs(news_score) / max(news_strong, 0.0001),
                dispatch_mode="LLM_ALLOWED" if abs(news_score) >= news_strong else "RULE_ONLY",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"news:{news_direction}",
            )
        )

    onchain_score = _safe_float(feature_snapshot.get("onchain_flow_bias"))
    onchain_direction = _direction_from_value(onchain_score)
    onchain_events = [item for item in event_bundle if str(item.get("event_type") or "").strip().lower() == "onchain"]
    onchain_amount = max((_safe_float(item.get("amountUsd")) for item in onchain_events), default=0.0)
    onchain_amount_strong = _safe_float(
        _pick(resolved_policy["onchain_trigger"], "flowUsdThreshold", "flow_usd_threshold"),
        1000000,
    )
    onchain_amount_rule = _safe_float(
        _pick(resolved_policy["onchain_trigger"], "ruleOnlyFlowUsdThreshold", "rule_only_flow_usd_threshold"),
        250000,
    )
    onchain_score_strong = _safe_float(_pick(resolved_policy["onchain_trigger"], "scoreThreshold", "score_threshold"), 0.9)
    onchain_score_rule = _safe_float(_pick(resolved_policy["onchain_trigger"], "ruleOnlyScoreThreshold", "rule_only_score_threshold"), 0.7)
    if onchain_direction != "neutral" and (onchain_amount >= onchain_amount_rule or abs(onchain_score) >= onchain_score_rule):
        strong_hit = onchain_amount >= onchain_amount_strong or abs(onchain_score) >= onchain_score_strong
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="onchain",
                signal_type="flow",
                direction=onchain_direction,
                strength_score=max(
                    onchain_amount / max(onchain_amount_strong, 1.0),
                    abs(onchain_score) / max(onchain_score_strong, 0.0001),
                ),
                dispatch_mode="LLM_ALLOWED" if strong_hit else "RULE_ONLY",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"onchain:{onchain_direction}",
            )
        )

    social_score = _safe_float(feature_snapshot.get("social_score"))
    social_direction = _direction_from_value(social_score)
    social_strong = _safe_float(_pick(resolved_policy["social_trigger"], "scoreThreshold", "score_threshold"), 0.85)
    social_rule = _safe_float(_pick(resolved_policy["social_trigger"], "ruleOnlyScoreThreshold", "rule_only_score_threshold"), 0.65)
    if abs(social_score) >= social_rule and social_direction != "neutral":
        signals.append(
            _candidate_signal(
                symbol=symbol,
                source_type="social",
                signal_type="sentiment",
                direction=social_direction,
                strength_score=abs(social_score) / max(social_strong, 0.0001),
                dispatch_mode="LLM_ALLOWED" if abs(social_score) >= social_strong else "RULE_ONLY",
                now=now,
                signal_memory_policy=resolved_policy["signal_memory_policy"],
                dedupe_key=f"social:{social_direction}",
            )
        )

    return signals


def _match_combination(active_signals: list[dict[str, Any]], trigger_matrix: Any) -> dict[str, Any] | None:
    if not isinstance(trigger_matrix, list):
        return None
    for item in trigger_matrix:
        if not isinstance(item, dict):
            continue
        sources = item.get("sources") or item.get("sourceTypes") or []
        if not isinstance(sources, list) or not sources:
            continue
        direction = ""
        matched_signals: list[dict[str, Any]] = []
        for source in sources:
            source_name = str(source).strip().lower()
            source_signal = next(
                (
                    signal
                    for signal in active_signals
                    if signal.get("source_type") == source_name
                    and signal.get("direction") != "neutral"
                    and (not direction or signal.get("direction") == direction)
                ),
                None,
            )
            if source_signal is None:
                matched_signals = []
                break
            if not direction:
                direction = str(source_signal.get("direction") or "")
            matched_signals.append(source_signal)
        if len(matched_signals) != len(sources):
            continue
        return {
            "code": str(item.get("code") or "combination_match").strip(),
            "sources": [str(source).strip().lower() for source in sources],
            "direction": direction,
            "target_dispatch_mode": _normalize_dispatch_mode(
                item.get("targetDispatchMode")
                or item.get("target_dispatch_mode")
                or item.get("upgradeTo")
                or item.get("upgrade_to")
                or "RULE_ONLY"
            ),
        }
    return None


def classify_event_strength_from_policy(
    *,
    event_bundle: Any,
    feature_snapshot: Any,
    runtime_config: dict[str, Any] | None,
    strategy_context: dict[str, Any] | None,
    now: Any = None,
) -> str:
    """根据策略配置分类事件强度

    根据触发策略配置判断当前事件的强度级别：
    - strong: 有LLM_ALLOWED级别的信号
    - normal: 有RULE_ONLY级别的信号
    - noise: 无有效信号

    Args:
        event_bundle: 事件包
        feature_snapshot: 特征快照
        runtime_config: 运行时配置
        strategy_context: 策略上下文
        now: 当前时间

    Returns:
        str: 事件强度（strong/normal/noise）
    """
    now_dt = _parse_datetime(now) or datetime.now(timezone.utc)
    normalized_event_bundle = [item for item in event_bundle if isinstance(item, dict)] if isinstance(event_bundle, list) else []
    normalized_feature_snapshot = feature_snapshot if isinstance(feature_snapshot, dict) else {}
    resolved_policy = resolve_trigger_policy(
        runtime_config=runtime_config,
        strategy_context=strategy_context,
    )
    current_signals = _current_signals(
        event_bundle=normalized_event_bundle,
        feature_snapshot=normalized_feature_snapshot,
        resolved_policy=resolved_policy,
        now=now_dt,
    )
    if any(signal.get("dispatch_mode") == "LLM_ALLOWED" for signal in current_signals):
        return "strong"
    if current_signals:
        return "normal"
    return "noise"


def evaluate_trigger_policy(
    *,
    event_bundle: Any,
    feature_snapshot: Any,
    signal_window_states: Any,
    runtime_account_context: Any,
    runtime_config: Any,
    strategy_context: Any,
    trigger_state: dict[str, Any] | None = None,
    now: Any = None,
    bypass_budget: bool = False,
    bypass_cooldown: bool = False,
) -> dict[str, Any]:
    """评估触发策略

    综合评估是否应该触发交易决策，包括：
    1. 从事件和特征快照中提取信号
    2. 与历史信号窗口状态合并
    3. 检查信号组合匹配
    4. 应用冷却期和预算控制
    5. 确定分发模式和选中的Agent

    Args:
        event_bundle: 事件包列表
        feature_snapshot: 特征快照
        signal_window_states: 信号窗口状态列表
        runtime_account_context: 运行时账户上下文（未使用）
        runtime_config: 运行时配置
        strategy_context: 策略上下文
        trigger_state: 触发状态（冷却期、预算等）
        now: 当前时间
        bypass_budget: 是否绕过预算控制
        bypass_cooldown: 是否绕过冷却期

    Returns:
        dict[str, Any]: 评估结果，包含：
            - dispatch_mode: 分发模式
            - llm_allowed: 是否允许LLM调用
            - should_dispatch: 是否应该分发
            - trigger_reason: 触发原因
            - trigger_source: 触发来源
            - selected_agents: 选中的Agent列表
            - active_signals: 活跃信号列表
            - combination_match: 组合匹配信息
            - cooldown_blocked: 是否被冷却期阻止
            - budget_blocked: 是否被预算阻止
            - rule_only_reason: 仅规则模式原因
            - budget_usage: 预算使用情况
            - trigger_state: 更新后的触发状态
    """
    del runtime_account_context

    now_dt = _parse_datetime(now) or datetime.now(timezone.utc)
    normalized_event_bundle = [item for item in event_bundle if isinstance(item, dict)] if isinstance(event_bundle, list) else []
    normalized_feature_snapshot = feature_snapshot if isinstance(feature_snapshot, dict) else {}
    normalized_signal_window_states = [item for item in signal_window_states if isinstance(item, dict)] if isinstance(signal_window_states, list) else []
    resolved_policy = _resolve_policy(
        runtime_config if isinstance(runtime_config, dict) else {},
        strategy_context if isinstance(strategy_context, dict) else {},
    )

    state_payload = trigger_state if isinstance(trigger_state, dict) else {}
    next_trigger_state = {
        "cooldowns": dict(state_payload.get("cooldowns") or {}),
        "dedupe": dict(state_payload.get("dedupe") or {}),
        "budget_state": dict(state_payload.get("budget_state") or {}),
    }

    current_signals = _current_signals(
        event_bundle=normalized_event_bundle,
        feature_snapshot=normalized_feature_snapshot,
        resolved_policy=resolved_policy,
        now=now_dt,
    )
    memory_signals = [
        normalized
        for normalized in (
            _normalize_signal_window_state(signal_window_state, now_dt)
            for signal_window_state in normalized_signal_window_states
        )
        if normalized is not None
    ]
    active_signals = memory_signals + current_signals

    base_dispatch_mode = "NO_DISPATCH"
    trigger_reason = "noise_threshold_not_met"
    trigger_source = ""
    primary_signal = None
    if current_signals:
        primary_signal = max(
            current_signals,
            key=lambda item: (_DISPATCH_RANK.get(item.get("dispatch_mode"), 0), item.get("strength_score", 0.0)),
        )
        base_dispatch_mode = _normalize_dispatch_mode(primary_signal.get("dispatch_mode"))
        trigger_source = str(primary_signal.get("source_type") or "")
        trigger_reason = f"{trigger_source}_threshold_met" if trigger_source else "threshold_met"
    else:
        event_strength = str(normalized_feature_snapshot.get("event_strength") or "").strip().lower()
        if event_strength == "strong":
            base_dispatch_mode = "LLM_ALLOWED"
            trigger_reason = "strong_event_classified"
        elif event_strength == "normal":
            base_dispatch_mode = "RULE_ONLY"
            trigger_reason = "normal_event_classified"

    combination_match = _match_combination(active_signals, resolved_policy["trigger_matrix"])
    if combination_match is not None and _DISPATCH_RANK[combination_match["target_dispatch_mode"]] > _DISPATCH_RANK[base_dispatch_mode]:
        base_dispatch_mode = combination_match["target_dispatch_mode"]
        trigger_source = "combination"
        trigger_reason = f"combination:{combination_match['code']}"

    symbol = str(
        normalized_feature_snapshot.get("symbol")
        or next((item.get("symbol") for item in normalized_event_bundle if item.get("symbol")), "")
        or ""
    ).strip()
    direction = ""
    if combination_match is not None:
        direction = combination_match["direction"]
    elif primary_signal is not None:
        direction = str(primary_signal.get("direction") or "")

    source_types = combination_match["sources"] if combination_match is not None else ([str(primary_signal.get("source_type") or "")] if primary_signal is not None else [])
    cooldown_seconds = max(0, _safe_int(_pick(resolved_policy["cooldown_policy"], "globalSeconds", "global_seconds"), 0))
    # 冷却键带上 signal_type，让不同的行情维度各占各的窗口。
    #
    # 此前是 symbol:source:direction，而 Wyckoff 的 source 就是 "market"——
    # 和 price_break、mark_price_deviation 共用同一个键。于是一个价格突破先
    # 占了 5 分钟冷却，3 分钟后真正的 Wyckoff ready 就被挡在门外，连模型都
    # 看不到。实测近 6 小时 12 个 ready 信号里，5 个是这样丢掉的。
    #
    # 这不是"少几次机会"：CALIBRATION.md 里 price_break 全网格 hit_rate
    # 0.45~0.47，低于 0.5051 的基准；而 Wyckoff ready 是 30 天 163 个样本、
    # 均 +0.3904%、t=3.11 显著为正。没有优势的维度在挤掉唯一有优势的那个。
    cooldown_signal_type = str(
        (primary_signal or {}).get("signal_type") or ""
    ).strip().lower() or "none"
    cooldown_key = (
        f"{symbol}:{trigger_source or 'none'}:{cooldown_signal_type}:{direction or 'neutral'}"
    )
    last_cooldown_at = _parse_datetime(next_trigger_state["cooldowns"].get(cooldown_key))
    cooldown_blocked = (
        base_dispatch_mode == "LLM_ALLOWED"
        and not bypass_cooldown
        and cooldown_seconds > 0
        and last_cooldown_at is not None
        and (now_dt - last_cooldown_at).total_seconds() < cooldown_seconds
    )

    budget_result = {
        "allowed": True,
        "blocked": False,
        "reason_code": "",
        "usage": {"per_symbol_daily": 0, "per_symbol_window": 0, "global_daily": 0},
        "state": next_trigger_state["budget_state"],
    }
    budget_blocked = False
    if base_dispatch_mode == "LLM_ALLOWED" and not cooldown_blocked:
        budget_result = evaluate_llm_budget(
            symbol=symbol,
            llm_budget_policy=resolved_policy["llm_budget_policy"],
            budget_state=next_trigger_state["budget_state"],
            now=now_dt,
            consume=True,
            bypass=bypass_budget,
        )
        next_trigger_state["budget_state"] = budget_result["state"]
        budget_blocked = budget_result["blocked"]

    dispatch_mode = base_dispatch_mode
    llm_allowed = dispatch_mode == "LLM_ALLOWED"
    rule_only_reason = ""
    if cooldown_blocked:
        dispatch_mode = "RULE_ONLY"
        llm_allowed = False
        rule_only_reason = "cooldown_blocked"
    elif budget_blocked:
        dispatch_mode = "RULE_ONLY"
        llm_allowed = False
        rule_only_reason = "budget_blocked"

    if base_dispatch_mode == "LLM_ALLOWED" and not cooldown_blocked and not budget_blocked and not bypass_cooldown:
        next_trigger_state["cooldowns"][cooldown_key] = now_dt.isoformat()

    return {
        "dispatch_mode": dispatch_mode,
        "llm_allowed": dispatch_mode == "LLM_ALLOWED",
        "should_dispatch": dispatch_mode != "NO_DISPATCH",
        "trigger_reason": trigger_reason,
        "trigger_source": trigger_source,
        "selected_agents": [] if dispatch_mode == "NO_DISPATCH" else _resolve_selected_agents(source_types, strategy_context if isinstance(strategy_context, dict) else {}, combination_match["code"] if combination_match is not None else ""),
        "active_signals": active_signals,
        "combination_match": combination_match or {},
        "cooldown_blocked": cooldown_blocked,
        "budget_blocked": budget_blocked,
        "rule_only_reason": rule_only_reason,
        "budget_usage": budget_result["usage"],
        "trigger_state": next_trigger_state,
    }
