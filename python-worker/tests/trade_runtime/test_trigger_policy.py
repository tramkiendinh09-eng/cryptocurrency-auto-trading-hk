from datetime import datetime, timedelta, timezone

from trade_runtime.config import RuntimeConfig
from trade_runtime.trigger_policy import (
    classify_event_strength_from_policy,
    evaluate_trigger_policy,
    resolve_trigger_policy,
)


def test_trigger_policy_returns_no_dispatch_for_noise_events():
    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 0.4, "event_strength": "noise"},
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=RuntimeConfig(defaultMode="shadow", liveEnabled=False).model_dump(),
        strategy_context=None,
        trigger_state={},
        now=datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "NO_DISPATCH"
    assert decision["llm_allowed"] is False
    assert decision["should_dispatch"] is False
    assert decision["trigger_reason"] == "noise_threshold_not_met"
    assert decision["active_signals"] == []


def test_trigger_policy_escalates_strong_news_to_llm_allowed():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson="""
        {
          "newsTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7},
          "cooldownPolicy":{"globalSeconds":180},
          "llmBudgetPolicy":{"perSymbolDailyLimit":4,"perSymbolWindowLimit":2,"windowSeconds":3600}
        }
        """,
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "news", "symbol": "BTCUSDT", "headline": "ETF approval", "score": 0.96}],
        feature_snapshot={"symbol": "BTCUSDT", "news_score": 0.96, "event_strength": "strong"},
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["llm_allowed"] is True
    assert decision["should_dispatch"] is True
    assert decision["trigger_source"] == "news"
    assert decision["selected_agents"] == ["market_agent", "news_agent"]
    assert decision["budget_blocked"] is False
    assert decision["cooldown_blocked"] is False


def test_trigger_policy_matches_windowed_combination_and_upgrades_to_llm_allowed():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson="""
        {
          "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
          "signalMemoryPolicy":{
            "news":{"ttlSeconds":900,"combineWithinSeconds":900},
            "market":{"ttlSeconds":300,"combineWithinSeconds":300}
          },
          "triggerMatrix":[
            {"code":"strong_news_then_break","sources":["news","market"],"targetDispatchMode":"LLM_ALLOWED"}
          ],
          "llmBudgetPolicy":{"perSymbolDailyLimit":4,"perSymbolWindowLimit":2,"windowSeconds":3600}
        }
        """,
    ).model_dump()

    now = datetime(2026, 4, 17, 8, 5, tzinfo=timezone.utc)
    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 66200.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 1.3, "event_strength": "normal"},
        signal_window_states=[
            {
                "source_type": "news",
                "signal_type": "headline",
                "direction": "bullish",
                "strength_score": 0.94,
                "decay_score": 0.88,
                "opened_at": (now - timedelta(minutes=5)).isoformat(),
                "expires_at": (now + timedelta(minutes=10)).isoformat(),
                "last_event_at": (now - timedelta(minutes=5)).isoformat(),
                "last_confirmed_at": (now - timedelta(minutes=5)).isoformat(),
                "dedupe_key": "news:etf-approval",
                "combine_until_at": (now + timedelta(minutes=10)).isoformat(),
                "active": True,
            }
        ],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=now,
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["llm_allowed"] is True
    assert decision["combination_match"]["code"] == "strong_news_then_break"
    assert decision["trigger_source"] == "combination"
    assert decision["selected_agents"] == ["market_agent", "news_agent"]


def test_trigger_policy_matches_windowed_combination_when_rule_uses_upgrade_to_alias():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson="""
        {
          "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
          "newsTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7},
          "onchainTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7,"flowUsdThreshold":1000000,"ruleOnlyFlowUsdThreshold":250000},
          "signalMemoryPolicy":{
            "news":{"ttlSeconds":900,"combineWithinSeconds":900},
            "onchain":{"ttlSeconds":3600,"combineWithinSeconds":2400},
            "market":{"ttlSeconds":300,"combineWithinSeconds":300}
          },
          "triggerMatrix":[
            {"code":"news_onchain_market_confirmation","sources":["news","onchain","market"],"upgradeTo":"LLM_ALLOWED"}
          ],
          "llmBudgetPolicy":{"perSymbolDailyLimit":4,"perSymbolWindowLimit":2,"windowSeconds":3600}
        }
        """,
    ).model_dump()

    now = datetime(2026, 4, 17, 8, 6, tzinfo=timezone.utc)
    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 66200.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 1.4, "event_strength": "normal"},
        signal_window_states=[
            {
                "source_type": "news",
                "signal_type": "headline",
                "direction": "bullish",
                "strength_score": 0.94,
                "decay_score": 0.88,
                "opened_at": (now - timedelta(minutes=5)).isoformat(),
                "expires_at": (now + timedelta(minutes=10)).isoformat(),
                "last_event_at": (now - timedelta(minutes=5)).isoformat(),
                "last_confirmed_at": (now - timedelta(minutes=5)).isoformat(),
                "dedupe_key": "news:etf-approval",
                "combine_until_at": (now + timedelta(minutes=10)).isoformat(),
                "active": True,
            },
            {
                "source_type": "onchain",
                "signal_type": "flow",
                "direction": "bullish",
                "strength_score": 0.92,
                "decay_score": 0.84,
                "opened_at": (now - timedelta(minutes=4)).isoformat(),
                "expires_at": (now + timedelta(minutes=30)).isoformat(),
                "last_event_at": (now - timedelta(minutes=4)).isoformat(),
                "last_confirmed_at": (now - timedelta(minutes=4)).isoformat(),
                "dedupe_key": "onchain:exchange_outflow",
                "combine_until_at": (now + timedelta(minutes=30)).isoformat(),
                "active": True,
            },
        ],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=now,
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["llm_allowed"] is True
    assert decision["combination_match"]["code"] == "news_onchain_market_confirmation"
    assert decision["trigger_source"] == "combination"
    assert decision["selected_agents"] == ["market_agent", "news_agent", "onchain_agent"]


def test_trigger_policy_applies_cooldown_and_downgrades_repeated_llm_dispatch():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson="""
        {
          "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
          "cooldownPolicy":{"globalSeconds":180},
          "llmBudgetPolicy":{"perSymbolDailyLimit":4,"perSymbolWindowLimit":4,"windowSeconds":3600}
        }
        """,
    ).model_dump()

    first = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 3.8, "event_strength": "strong"},
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
    )

    second = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65100.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 3.6, "event_strength": "strong"},
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state=first["trigger_state"],
        now=datetime(2026, 4, 17, 8, 1, tzinfo=timezone.utc),
    )

    assert first["dispatch_mode"] == "LLM_ALLOWED"
    assert second["dispatch_mode"] == "RULE_ONLY"
    assert second["llm_allowed"] is False
    assert second["cooldown_blocked"] is True
    assert second["rule_only_reason"] == "cooldown_blocked"


def test_trigger_policy_escalates_ready_wyckoff_shortterm_signal_to_llm_allowed():
    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2285.0}],
        feature_snapshot={
            "symbol": "ETHUSDT",
            "price_change_pct": 0.05,
            "market_window_price_change_pct": 0.08,
            "event_strength": "noise",
            "wyckoff_shortterm": {
                "status": "ready",
                "phase": "markup",
                "entry_bias": "bullish",
                "trigger": "breakout_long",
                "trade_readiness": "ready",
                "confidence": 0.78,
            },
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=RuntimeConfig(defaultMode="shadow", liveEnabled=False).model_dump(),
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["llm_allowed"] is True
    assert decision["trigger_source"] == "market"
    assert any(item["signal_type"] == "wyckoff_shortterm" for item in decision["active_signals"])
    assert len(decision["selected_agents"]) >= 2


def test_trigger_policy_keeps_wyckoff_watch_out_of_the_llm_budget():
    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "ETHUSDT", "price": 2285.0}],
        feature_snapshot={
            "symbol": "ETHUSDT",
            "price_change_pct": 0.05,
            "market_window_price_change_pct": 0.08,
            "event_strength": "noise",
            "wyckoff_shortterm": {
                "status": "watch",
                "phase": "markup",
                "entry_bias": "bullish",
                "trigger": "breakout_long",
                "trade_readiness": "watch",
                "confidence": 0.72,
                "no_trade_reason": "breakout_retest_required",
            },
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=RuntimeConfig(defaultMode="shadow", liveEnabled=False).model_dump(),
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 17, 8, 1, tzinfo=timezone.utc),
    )

    # 这条断言反转过一次，两次都有据可依，记下来免得再来回改：
    #
    # 最早是 NO_DISPATCH——ready 要七项条件连续全过，差一项就降级成 watch
    # 然后被整条丢掉。当时为了让系统敢开仓，把 watch 提到了 LLM_ALLOWED，
    # 那一步没有数据支撑，只是「总得先动起来」。
    #
    # 现在有数据了（calibration/readiness_edge.py，30 天、209 分钟持仓）：
    #
    #     ready   n=163   均 +0.3904%   t=3.11  显著为正   扣费后 +0.3104%
    #     watch   n=1773  均 +0.0092%   t=0.25  与 0 无异   扣费后 -0.0708% 转负
    #
    # 两组差异 t=2.92 显著，而 watch : ready = 10.9 : 1——按数量分配预算的话
    # watch 会拿走约 92%，把唯一被证明有优势的信号挤出去。所以 watch 降回
    # RULE_ONLY：它仍然进信号合成、仍然提供上下文，只是不再触发 LLM 决策。
    assert decision["dispatch_mode"] == "RULE_ONLY"
    assert decision["llm_allowed"] is False
    # 关键：信号本身没有被丢掉，只是不占预算——这正是与最早那版 NO_DISPATCH
    # 的区别。
    assert any(item["signal_type"] == "wyckoff_shortterm" for item in decision["active_signals"])


def test_wyckoff_watch_carries_less_weight_than_ready():
    """watch 比 ready 弱是事实，放进来不等于同权重。"""
    from trade_runtime.trigger_policy import _ready_wyckoff_shortterm_signal

    base = {
        "phase": "markup",
        "entry_bias": "bullish",
        "trigger": "breakout_long",
        "confidence": 0.75,
    }
    ready = _ready_wyckoff_shortterm_signal({"wyckoff_shortterm": {**base, "trade_readiness": "ready"}})
    watch = _ready_wyckoff_shortterm_signal({"wyckoff_shortterm": {**base, "trade_readiness": "watch"}})
    assert ready is not None and watch is not None
    assert watch["strength_score"] < ready["strength_score"]
    # 打折之后仍要高于噪声，否则等于没放进来
    assert watch["strength_score"] > 0.5
    assert watch["trade_readiness"] == "watch"


def test_wyckoff_avoid_is_still_dropped():
    """放宽到 watch 不等于什么都收：avoid 是"结构本身不成立"。"""
    from trade_runtime.trigger_policy import _ready_wyckoff_shortterm_signal

    assert _ready_wyckoff_shortterm_signal(
        {
            "wyckoff_shortterm": {
                "phase": "range",
                "entry_bias": "bullish",
                "trigger": "breakout_long",
                "trade_readiness": "avoid",
                "confidence": 0.58,
            }
        }
    ) is None


def test_wyckoff_watch_and_ready_are_not_deduped_into_one():
    """watch 升级成 ready 是一次新的、更强的信号，不能被前一条 watch 去重掉。"""
    from trade_runtime.trigger_policy import _ready_wyckoff_shortterm_signal

    base = {"phase": "markup", "entry_bias": "bullish", "trigger": "breakout_long", "confidence": 0.75}
    ready = _ready_wyckoff_shortterm_signal({"wyckoff_shortterm": {**base, "trade_readiness": "ready"}})
    watch = _ready_wyckoff_shortterm_signal({"wyckoff_shortterm": {**base, "trade_readiness": "watch"}})
    assert ready["trade_readiness"] != watch["trade_readiness"]


def test_resolve_trigger_policy_merges_runtime_defaults_and_strategy_overrides():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson="""
        {
          "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
          "newsTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7}
        }
        """,
    ).model_dump()

    strategy_context = {
        "strategy_config": {
            "triggerPolicy": {
                "marketTrigger": {"priceChangePct": 3.2},
                "socialTrigger": {"ruleOnlyScoreThreshold": 0.6},
            }
        }
    }

    resolved = resolve_trigger_policy(runtime_config=runtime_config, strategy_context=strategy_context)

    assert resolved["market_trigger"]["ruleOnlyPriceChangePct"] == 1.0
    assert resolved["market_trigger"]["priceChangePct"] == 3.2
    assert resolved["social_trigger"]["ruleOnlyScoreThreshold"] == 0.6


def test_trigger_policy_filters_disabled_specialists_from_selected_agents():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson="""
        {
          "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
          "socialTrigger":{"scoreThreshold":0.85,"ruleOnlyScoreThreshold":0.65},
          "triggerMatrix":[
            {"code":"social_market_confirmation","sources":["social","market"],"targetDispatchMode":"LLM_ALLOWED"}
          ],
          "llmBudgetPolicy":{"perSymbolDailyLimit":4,"perSymbolWindowLimit":2,"windowSeconds":3600}
        }
        """,
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[
            {"event_type": "social", "symbol": "BTCUSDT", "score": 0.91},
            {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 66200.0},
        ],
        feature_snapshot={"symbol": "BTCUSDT", "social_score": 0.91, "price_change_pct": 1.4, "event_strength": "strong"},
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={
            "agent_profiles": [
                {"agent_code": "market_agent", "enabled": True},
                {"agent_code": "social_agent", "enabled": False},
            ]
        },
        trigger_state={},
        now=datetime(2026, 4, 17, 8, 6, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["selected_agents"] == ["market_agent"]


def test_trigger_policy_filters_disabled_uppercase_specialist_profiles():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson="""
        {
          "marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0},
          "newsTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7},
          "onchainTrigger":{"scoreThreshold":0.9,"ruleOnlyScoreThreshold":0.7,"flowUsdThreshold":1000000,"ruleOnlyFlowUsdThreshold":250000},
          "triggerMatrix":[
            {"code":"news_onchain_market_confirmation","sources":["news","onchain","market"],"targetDispatchMode":"LLM_ALLOWED"}
          ],
          "llmBudgetPolicy":{"perSymbolDailyLimit":4,"perSymbolWindowLimit":2,"windowSeconds":3600}
        }
        """,
    ).model_dump()
    now = datetime(2026, 4, 17, 8, 6, tzinfo=timezone.utc)

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 66200.0}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 1.4, "event_strength": "normal"},
        signal_window_states=[
            {
                "source_type": "news",
                "direction": "bullish",
                "strength_score": 0.94,
                "decay_score": 0.88,
                "expires_at": (now + timedelta(minutes=10)).isoformat(),
                "active": True,
            },
            {
                "source_type": "onchain",
                "direction": "bullish",
                "strength_score": 0.92,
                "decay_score": 0.84,
                "expires_at": (now + timedelta(minutes=30)).isoformat(),
                "active": True,
            },
        ],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={
            "agent_profiles": [
                {"agent_code": "MARKET_AGENT", "enabled": True},
                {"agent_code": "NEWS_AGENT", "enabled": True},
                {"agent_code": "ONCHAIN_AGENT", "enabled": True},
                {"agent_code": "SOCIAL_AGENT", "enabled": False},
            ]
        },
        trigger_state={},
        now=now,
    )

    assert decision["selected_agents"] == ["market_agent", "news_agent", "onchain_agent"]


def test_resolve_trigger_policy_includes_default_liquidation_threshold():
    resolved = resolve_trigger_policy(
        runtime_config=RuntimeConfig(defaultMode="shadow", liveEnabled=False).model_dump(),
        strategy_context={},
    )

    assert resolved["market_trigger"]["liquidationNotionalUsd"] == 250000
    assert resolved["market_trigger"]["fundingRateAbs"] == 0.0
    assert resolved["market_trigger"]["markPriceDeviationPct"] == 0.0


def test_market_price_acceleration_threshold_creates_llm_signal():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0,"priceAccelerationPct":1.2}}',
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={
            "symbol": "BTCUSDT",
            "price_change_pct": 0.2,
            "market_price_acceleration_pct": 1.3,
            "event_strength": "strong",
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["trigger_source"] == "market"
    assert decision["active_signals"][0]["signal_type"] == "price_acceleration"


def test_market_window_price_change_threshold_creates_llm_signal():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"priceChangePct":2.5,"ruleOnlyPriceChangePct":1.0}}',
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={
            "symbol": "BTCUSDT",
            "price_change_pct": 0.0,
            "market_window_price_change_pct": -3.0,
            "event_strength": "strong",
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["trigger_source"] == "market"
    assert decision["active_signals"][0]["signal_type"] == "price_break"
    assert decision["active_signals"][0]["direction"] == "bearish"


def test_funding_rate_threshold_creates_llm_signal():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"fundingRateAbs":0.001}}',
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "funding_rate", "symbol": "BTCUSDT", "funding_rate": -0.0012}],
        feature_snapshot={"symbol": "BTCUSDT", "price_change_pct": 0.0, "funding_rate": -0.0012, "event_strength": "strong"},
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["trigger_source"] == "market"
    assert decision["active_signals"][0]["signal_type"] == "funding_rate_extreme"
    assert decision["active_signals"][0]["direction"] == "bearish"


def test_mark_price_deviation_threshold_creates_llm_signal():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"markPriceDeviationPct":1.0}}',
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "mark_price", "symbol": "BTCUSDT", "price": 101.2}],
        feature_snapshot={
            "symbol": "BTCUSDT",
            "price_change_pct": 0.0,
            "mark_price_deviation_pct": 1.2,
            "event_strength": "strong",
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["trigger_source"] == "market"
    assert decision["active_signals"][0]["signal_type"] == "mark_price_deviation"


def test_kline_price_change_threshold_creates_llm_signal():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"klinePriceChangePct15m":1.0}}',
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={
            "symbol": "BTCUSDT",
            "price_change_pct": 0.0,
            "kline_price_change_pct": {"15m": -1.4},
            "event_strength": "strong",
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["trigger_source"] == "market"
    assert decision["active_signals"][0]["signal_type"] == "kline_price_change_15m"
    assert decision["active_signals"][0]["direction"] == "bearish"


def test_liquidation_aggregate_threshold_creates_llm_signal():
    runtime_config = RuntimeConfig(
        defaultMode="shadow",
        liveEnabled=False,
        runtimeFlagsJson='{"marketTrigger":{"liquidationNotional60mUsd":500000}}',
    ).model_dump()

    decision = evaluate_trigger_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot={
            "symbol": "BTCUSDT",
            "price_change_pct": 0.0,
            "liquidation_notional_60m": 600000.0,
            "event_strength": "strong",
        },
        signal_window_states=[],
        runtime_account_context={"current_position_side": "flat"},
        runtime_config=runtime_config,
        strategy_context={},
        trigger_state={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert decision["dispatch_mode"] == "LLM_ALLOWED"
    assert decision["trigger_source"] == "market"
    assert decision["active_signals"][0]["signal_type"] == "liquidation_aggregate_60m"


def test_classify_event_strength_from_policy_returns_noise_below_rule_only_threshold():
    feature_snapshot = {"symbol": "BTCUSDT", "price_change_pct": 0.8}

    level = classify_event_strength_from_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot=feature_snapshot,
        runtime_config=RuntimeConfig(defaultMode="shadow", liveEnabled=False).model_dump(),
        strategy_context={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert level == "noise"


def test_classify_event_strength_from_policy_returns_normal_at_rule_only_threshold():
    feature_snapshot = {"symbol": "BTCUSDT", "price_change_pct": 1.2}

    level = classify_event_strength_from_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot=feature_snapshot,
        runtime_config=RuntimeConfig(defaultMode="shadow", liveEnabled=False).model_dump(),
        strategy_context={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert level == "normal"


def test_classify_event_strength_from_policy_returns_strong_at_llm_threshold():
    feature_snapshot = {"symbol": "BTCUSDT", "price_change_pct": 2.8}

    level = classify_event_strength_from_policy(
        event_bundle=[{"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0}],
        feature_snapshot=feature_snapshot,
        runtime_config=RuntimeConfig(defaultMode="shadow", liveEnabled=False).model_dump(),
        strategy_context={},
        now=datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert level == "strong"
