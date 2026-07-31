from trade_runtime.risk.guard import RiskGuard


def test_risk_guard_blocks_when_daily_loss_limit_exceeded():
    guard = RiskGuard(
        max_position_ratio=0.4,
        max_daily_loss=-500.0,
        max_consecutive_failures=3,
    )
    result = guard.evaluate(
        account_equity=10000,
        requested_notional=1500,
        daily_pnl=-800,
        consecutive_failures=0,
    )
    assert result["passed"] is False
    assert result["reason"] == "daily_loss_limit"


def test_risk_guard_blocks_when_market_source_is_abnormal():
    guard = RiskGuard(
        max_position_ratio=0.4,
        max_daily_loss=-500.0,
        max_consecutive_failures=3,
    )
    result = guard.evaluate(
        account_equity=10000,
        requested_notional=1500,
        daily_pnl=0,
        consecutive_failures=0,
        market_source_status="stale",
    )
    assert result["passed"] is False
    assert result["rule_code"] == "market_source_abnormal"
    assert result["reason"] == "market_source_abnormal"


def test_risk_guard_does_not_block_when_only_aux_source_health_events_are_degraded():
    guard = RiskGuard(
        max_position_ratio=0.4,
        max_daily_loss=-500.0,
        max_consecutive_failures=3,
    )
    result = guard.evaluate(
        account_equity=10000,
        requested_notional=1500,
        daily_pnl=0,
        consecutive_failures=0,
        market_source_status="ready",
        event_bundle=[
            {
                "event_type": "source_health",
                "source_type": "news",
                "source_status": "unavailable",
            },
            {
                "event_type": "source_health",
                "source_type": "social",
                "source_status": "stale",
            },
        ],
    )
    assert result["passed"] is True
    assert result["rule_code"] == "pass"
    assert result["reason"] == "pass"


def test_risk_guard_blocks_when_halt_on_data_gap_is_enabled_for_aux_source_degradation():
    guard = RiskGuard(
        max_position_ratio=0.4,
        max_daily_loss=-500.0,
        max_consecutive_failures=3,
    )
    result = guard.evaluate(
        account_equity=10000,
        requested_notional=1500,
        daily_pnl=0,
        consecutive_failures=0,
        market_source_status="ready",
        feature_snapshot={
            "aux_source_status": "aux_source_degraded",
            "degraded_sources": ["social"],
            "source_health": {"social": "empty"},
        },
        halt_on_data_gap=True,
        event_bundle=[
            {
                "event_type": "source_health",
                "source_type": "social",
                "source_status": "empty",
            }
        ],
    )
    assert result["passed"] is False
    assert result["rule_code"] == "data_gap"
    assert result["reason"] == "data_gap"


def test_risk_guard_allows_ready_empty_and_filtered_stale_aux_sources():
    guard = RiskGuard(
        max_position_ratio=0.4,
        max_daily_loss=-500.0,
        max_consecutive_failures=3,
    )
    result = guard.evaluate(
        account_equity=10000,
        requested_notional=1500,
        daily_pnl=0,
        consecutive_failures=0,
        market_source_status="ready",
        feature_snapshot={
            "aux_source_status": "ready",
            "degraded_sources": [],
            "source_health": {"news": "ready_empty", "onchain": "stale_items_filtered"},
        },
        halt_on_data_gap=True,
        event_bundle=[
            {"event_type": "source_health", "source_type": "news", "source_status": "ready_empty"},
            {"event_type": "source_health", "source_type": "onchain", "source_status": "stale_items_filtered"},
        ],
    )

    assert result["passed"] is True
    assert result["rule_code"] == "pass"


def test_risk_guard_blocks_when_projected_position_exceeds_limit():
    guard = RiskGuard(
        max_position_ratio=0.25,
        max_daily_loss=-500.0,
        max_consecutive_failures=3,
    )
    result = guard.evaluate(
        account_equity=10000,
        requested_notional=1000,
        current_position_notional=2000,
        daily_pnl=0,
        consecutive_failures=0,
    )
    assert result["passed"] is False
    assert result["rule_code"] == "position_limit"
    assert result["reason"] == "position_limit"
