"""预算按维度分账 + 每小时保底放行。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trade_runtime.config import RuntimeConfig
from trade_runtime.trigger_policy import evaluate_trigger_policy

BASE = datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc)


def _run(kind, state, now, budget=None):
    """kind='wyckoff' 走 Wyckoff ready，kind='price' 走价格突破。"""
    flags = {"cooldownPolicy": {"globalSeconds": 0}}
    if budget:
        flags["llmBudgetPolicy"] = budget
    config = RuntimeConfig.model_validate({
        "defaultMode": "paper",
        "liveEnabled": False,
        "runtimeFlagsJson": __import__("json").dumps(flags),
    }).model_dump()
    wyckoff = {
        "status": "ready", "phase": "markup", "entry_bias": "bullish",
        "trigger": "breakout_long", "trade_readiness": "ready",
        "confidence": 0.8, "no_trade_reason": "",
    } if kind == "wyckoff" else {}
    return evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "SOLUSDT", "price": 100.0}],
        feature_snapshot={
            "symbol": "SOLUSDT",
            "event_strength": "strong",
            "price_change_pct": 0.05 if kind == "wyckoff" else 3.0,
            "wyckoff_shortterm": wyckoff,
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=config,
        strategy_context={},
        trigger_state=state,
        now=now,
    )


def test_price_signals_cannot_starve_wyckoff_ready():
    """实测 2 天 228 个 ready 信号里 156 个（68%）被预算挡掉，而被挡掉的那批
    均收益 +0.28%，是所有分组里最高的——预算先到先得、不看质量，等于随机
    丢掉三分之二有优势的机会。

    ready 与其它维度分账之后，价格突破用光自己的额度不该影响 Wyckoff。
    """
    budget = {"perSymbolDailyLimit": 2, "rollingWindowLimit": 2}
    state = {}
    # 价格维度用光额度
    for i in range(2):
        out = _run("price", state, BASE + timedelta(minutes=i), budget)
        state = out["trigger_state"]
        assert out["dispatch_mode"] == "LLM_ALLOWED"
    exhausted = _run("price", state, BASE + timedelta(minutes=3), budget)
    state = exhausted["trigger_state"]
    assert exhausted["budget_blocked"] is True, "价格维度自己的额度应已用光"

    # Wyckoff ready 有自己的池子，不受影响
    ready = _run("wyckoff", state, BASE + timedelta(minutes=4), budget)
    assert ready["budget_blocked"] is False, "ready 不该被价格维度用光的额度挡住"
    assert ready["dispatch_mode"] == "LLM_ALLOWED"


def test_hourly_floor_releases_one_dispatch():
    """预算保证上限，不保证下限：完全可能整小时一次都没评估。"""
    budget = {"perSymbolDailyLimit": 1, "rollingWindowLimit": 1,
              "minDispatchIntervalSeconds": 3600}
    state = {}
    first = _run("price", state, BASE, budget)
    state = first["trigger_state"]
    assert first["dispatch_mode"] == "LLM_ALLOWED"

    # 额度已用光，十分钟后应被挡
    blocked = _run("price", state, BASE + timedelta(minutes=10), budget)
    state = blocked["trigger_state"]
    assert blocked["budget_blocked"] is True

    # 满一小时后保底放行
    released = _run("price", state, BASE + timedelta(minutes=61), budget)
    assert released["budget_blocked"] is False, "满一小时应保底放行一次"
    assert released["dispatch_mode"] == "LLM_ALLOWED"


def test_floor_is_off_when_not_configured():
    """不配这个键就完全是旧行为，不要凭空放开预算。"""
    budget = {"perSymbolDailyLimit": 1, "rollingWindowLimit": 1}
    state = {}
    state = _run("price", state, BASE, budget)["trigger_state"]
    later = _run("price", state, BASE + timedelta(hours=2), budget)
    assert later["budget_blocked"] is True
