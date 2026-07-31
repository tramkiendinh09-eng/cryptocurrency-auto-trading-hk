from datetime import datetime, timezone

from trade_runtime.position_risk_watcher import PositionRiskWatcher, evaluate_position_risk


def test_position_risk_watcher_ignores_flat_account():
    result = evaluate_position_risk(
        account_context={"current_position_side": "flat", "current_position_quantity": 0},
        feature_snapshot={"effective_price": 100.0},
        event_bundle=[],
        runtime_config={},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is False
    assert result["has_position"] is False


def test_position_risk_watcher_triggers_review_on_long_adverse_move():
    result = evaluate_position_risk(
        account_context={"current_position_side": "long", "current_position_quantity": 1.5, "entry_price": 100.0},
        feature_snapshot={"effective_price": 99.4, "effective_price_source": "mark_price"},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"reviewAdverseMovePct\":0.5}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["severity"] == "review"
    assert result["action"] == "REVIEW"
    assert result["position_risk_context"]["current_price"] == 99.4
    assert result["position_risk_event"]["event_type"] == "position_risk"
    assert result["bypass_trigger_guards"] is True


def test_position_risk_watcher_uses_effective_price_when_trade_tick_is_stale():
    result = evaluate_position_risk(
        account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": 100.0},
        feature_snapshot={
            "latest_trade_price": 100.0,
            "effective_price": 98.8,
            "effective_price_source": "mark_price",
            "market_tick_staleness_seconds": 600.0,
        },
        event_bundle=[{"event_type": "market_tick", "price": 100.0}],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"reviewAdverseMovePct\":0.5}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["position_risk_context"]["current_price"] == 98.8
    assert result["position_risk_context"]["price_source"] == "mark_price"
    assert result["position_risk_context"]["trade_tick_stale"] is True


def test_position_risk_watcher_escalates_to_hard_close_only_when_enabled():
    disabled = evaluate_position_risk(
        account_context={"current_position_side": "short", "current_position_quantity": 2.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 102.0},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"closeAdverseMovePct\":1.0,\"hardCloseEnabled\":false}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )
    enabled = evaluate_position_risk(
        account_context={"current_position_side": "short", "current_position_quantity": 2.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 102.0},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"closeAdverseMovePct\":1.0,\"hardCloseEnabled\":true}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert disabled["severity"] == "close"
    assert disabled["action"] == "REVIEW"
    assert enabled["severity"] == "close"
    assert enabled["action"] == "CLOSE"


def test_position_risk_watcher_cooldown_suppresses_duplicate_triggers():
    watcher = PositionRiskWatcher()
    runtime_config = {"runtime_flags_json": "{\"positionRiskWatcher\":{\"reviewAdverseMovePct\":0.5,\"cooldownSeconds\":60}}"}

    first = watcher.evaluate(
        account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 99.0},
        event_bundle=[],
        runtime_config=runtime_config,
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )
    second = watcher.evaluate(
        account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 98.9},
        event_bundle=[],
        runtime_config=runtime_config,
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, 30, tzinfo=timezone.utc),
    )

    assert first["triggered"] is True
    assert second["triggered"] is False
    assert second["suppressed_by_cooldown"] is True


def test_position_risk_watcher_triggers_on_profit_giveback():
    result = evaluate_position_risk(
        account_context={
            "current_position_side": "long",
            "current_position_quantity": 1.0,
            "entry_price": 100.0,
            "peak_unrealized_pnl_pct": 1.2,
        },
        feature_snapshot={"effective_price": 100.6},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"profitGivebackPct\":0.4}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["reason"] == "profit_giveback"
    assert result["position_risk_context"]["profit_giveback_pct"] == 0.6
