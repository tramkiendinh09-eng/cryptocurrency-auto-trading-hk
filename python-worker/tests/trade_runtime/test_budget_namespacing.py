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


def _run_mixed(state, now, budget=None, news_score=1.5, wyckoff=True):
    """同一轮里既有强新闻又有 Wyckoff ready —— 线上真实出现的组合。

    news_score 足够强时新闻信号会在 (dispatch_rank, strength_score) 排序里
    盖过 Wyckoff，成为 primary_signal。
    """
    import json

    flags = {"cooldownPolicy": {"globalSeconds": 180}}
    if budget:
        flags["llmBudgetPolicy"] = budget
    config = RuntimeConfig.model_validate({
        "defaultMode": "paper",
        "liveEnabled": False,
        "runtimeFlagsJson": json.dumps(flags),
    }).model_dump()
    snapshot = {
        "symbol": "SOLUSDT",
        "event_strength": "strong",
        "price_change_pct": 0.05,
        "news_score": news_score,
    }
    if wyckoff:
        snapshot["wyckoff_shortterm"] = {
            "status": "ready", "phase": "markup", "entry_bias": "bullish",
            "trigger": "breakout_long", "trade_readiness": "ready",
            "confidence": 0.8, "no_trade_reason": "",
        }
    return evaluate_trigger_policy(
        event_bundle=[
            {"event_type": "market_tick", "symbol": "SOLUSDT", "price": 100.0},
            {"event_type": "news", "symbol": "SOLUSDT", "sentiment_score": news_score},
        ],
        signal_window_states=[],
        feature_snapshot=snapshot,
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=config,
        strategy_context={},
        trigger_state=state,
        now=now,
    )


def test_news_in_same_round_cannot_take_over_the_ready_cooldown_key():
    """ready 的冷却键必须自足，不能借用 primary_signal 选出来的 source。

    实测 24h 内 40 个独立 ready setup 有 23 个整块没进过模型，其中 5 个的
    trigger_source 记的是 news——同一轮里的强新闻当选了 primary，ready 就被
    记到新闻的冷却键/预算池上，按 primary_signal 判断的分账对它们无效。
    """
    # 先让纯新闻（无 Wyckoff）占满它自己的冷却窗口
    state = _run_mixed({}, BASE, wyckoff=False)["trigger_state"]

    # 60 秒后 Wyckoff ready 出现，同轮仍有强新闻。冷却窗口是 180s，
    # 若 ready 沿用新闻的键就会被挡。
    out = _run_mixed(state, BASE + timedelta(seconds=60))
    assert out["cooldown_blocked"] is False, "ready 不该落在新闻的冷却键上"
    assert out["dispatch_mode"] == "LLM_ALLOWED"


def test_ready_still_dedupes_its_own_repeats():
    """自足的键不能变成"永不冷却"——同一个 setup 连报 11 次仍要压住。"""
    state = _run_mixed({}, BASE)["trigger_state"]
    repeat = _run_mixed(state, BASE + timedelta(seconds=30))
    assert repeat["cooldown_blocked"] is True, "180s 内的重复 ready 仍应压住"


def test_news_budget_exhaustion_does_not_block_ready():
    """新闻用光预算之后，ready 仍要能进模型。"""
    budget = {"perSymbolDailyLimit": 2, "rollingWindowLimit": 2}
    state = {}
    for i in range(2):
        state = _run_mixed(state, BASE + timedelta(minutes=i * 10),
                           budget=budget, wyckoff=False)["trigger_state"]
    drained = _run_mixed(state, BASE + timedelta(minutes=30),
                         budget=budget, wyckoff=False)
    state = drained["trigger_state"]
    assert drained["budget_blocked"] is True, "新闻自己的额度应已用光"

    ready = _run_mixed(state, BASE + timedelta(minutes=40), budget=budget)
    assert ready["budget_blocked"] is False, "ready 有独立额度，不该被新闻拖累"
    assert ready["dispatch_mode"] == "LLM_ALLOWED"
