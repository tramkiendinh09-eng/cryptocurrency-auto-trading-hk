from datetime import datetime, timezone

from trade_runtime.position_guard import build_guard_close_order, evaluate_position_guard


def test_evaluate_position_guard_hits_stop_loss_for_long_position():
    result = evaluate_position_guard(
        account_context={
            "current_position_side": "long",
            "current_position_quantity": 1.0,
            "current_position_notional": 100.0,
        },
        position_guard={
            "enabled": True,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.05,
            "max_holding_minutes": 180,
        },
        market_payload={"price": 96.5},
        now=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["reason"] == "stop_loss_pct"
    assert result["thresholds"]["stop_loss_ratio"] == 0.03
    assert result["thresholds"]["stop_loss_percent"] == 3.0


def test_evaluate_position_guard_accepts_explicit_ratio_fields():
    result = evaluate_position_guard(
        account_context={
            "current_position_side": "long",
            "current_position_quantity": 1.0,
            "current_position_notional": 100.0,
        },
        position_guard={
            "enabled": True,
            "stop_loss_ratio": 0.1,
            "take_profit_ratio": 0.3,
        },
        market_payload={"price": 90.0},
        now=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["reason"] == "stop_loss_pct"
    assert result["thresholds"]["threshold_unit"] == "ratio"
    assert result["thresholds"]["stop_loss_ratio"] == 0.1
    assert result["thresholds"]["stop_loss_percent"] == 10.0


def test_evaluate_position_guard_explicit_zero_ratio_overrides_legacy_pct_field():
    result = evaluate_position_guard(
        account_context={
            "current_position_side": "long",
            "current_position_quantity": 1.0,
            "current_position_notional": 100.0,
        },
        position_guard={
            "enabled": True,
            "stop_loss_ratio": 0.0,
            "stop_loss_pct": 0.1,
        },
        market_payload={"price": 80.0},
        now=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is False
    assert result["thresholds"] == {"threshold_unit": "ratio"}


def test_evaluate_position_guard_skips_when_no_open_position():
    result = evaluate_position_guard(
        account_context={
            "current_position_side": "flat",
            "current_position_quantity": 0.0,
            "current_position_notional": 0.0,
        },
        position_guard={"enabled": True, "stop_loss_pct": 0.03},
        market_payload={"price": 96.5},
        now=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is False
    assert result["reason"] is None


def test_build_guard_close_order_uses_position_quantity_and_close_metadata():
    order = build_guard_close_order(
        trace_id="trace-guard-1",
        symbol="ETHUSDT",
        account_context={
            "current_position_side": "short",
            "current_position_quantity": 0.30826727,
            "current_position_notional": 737.06087722,
            "entry_price": 2390.98,
            "td_mode": "cross",
        },
        market_payload={"price": 2355.5},
        trigger_reason="max_holding_minutes",
    )

    assert order["symbol"] == "ETHUSDT"
    assert order["side"] == "BUY"
    assert order["quote"] == 726.12355448
    assert order["price"] == 2355.5
    assert order["action"] == "CLOSE"
    assert order["order_type"] == "market"
    assert order["position_side"] == "short"
    assert order["reduce_only"] is True
    assert order["td_mode"] == "cross"
    assert order["quantity_base"] == 0.30826727
    assert order["reason"] == "position_guard:max_holding_minutes"
