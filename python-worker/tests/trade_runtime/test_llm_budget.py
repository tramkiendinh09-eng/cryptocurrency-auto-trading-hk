from datetime import datetime, timezone

from trade_runtime.llm_budget import evaluate_llm_budget


def test_llm_budget_allows_dispatch_within_limits_and_records_symbol_usage():
    result = evaluate_llm_budget(
        symbol="BTCUSDT",
        llm_budget_policy={
            "perSymbolDailyLimit": 2,
            "perSymbolWindowLimit": 1,
            "windowSeconds": 3600,
            "globalDailyLimit": 4,
        },
        budget_state={},
        now=datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
        consume=True,
    )

    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["reason_code"] == ""
    assert result["usage"]["per_symbol_daily"] == 1
    assert result["usage"]["per_symbol_window"] == 1
    assert result["usage"]["global_daily"] == 1
    assert len(result["state"]["symbol_dispatches"]["BTCUSDT"]) == 1


def test_llm_budget_blocks_when_symbol_window_limit_is_exhausted():
    initial = evaluate_llm_budget(
        symbol="BTCUSDT",
        llm_budget_policy={
            "perSymbolDailyLimit": 3,
            "perSymbolWindowLimit": 1,
            "windowSeconds": 3600,
        },
        budget_state={},
        now=datetime(2026, 4, 17, 8, 0, tzinfo=timezone.utc),
        consume=True,
    )

    blocked = evaluate_llm_budget(
        symbol="BTCUSDT",
        llm_budget_policy={
            "perSymbolDailyLimit": 3,
            "perSymbolWindowLimit": 1,
            "windowSeconds": 3600,
        },
        budget_state=initial["state"],
        now=datetime(2026, 4, 17, 8, 15, tzinfo=timezone.utc),
        consume=True,
    )

    assert blocked["allowed"] is False
    assert blocked["blocked"] is True
    assert blocked["reason_code"] == "per_symbol_window_limit_exhausted"
    assert blocked["usage"]["per_symbol_window"] == 1
    assert len(blocked["state"]["symbol_dispatches"]["BTCUSDT"]) == 1


def test_llm_budget_bypass_keeps_forced_dispatch_available():
    blocked_state = {
        "symbol_dispatches": {
            "BTCUSDT": ["2026-04-17T08:00:00+00:00"],
        },
        "global_dispatches": ["2026-04-17T08:00:00+00:00"],
    }

    result = evaluate_llm_budget(
        symbol="BTCUSDT",
        llm_budget_policy={
            "perSymbolDailyLimit": 1,
            "perSymbolWindowLimit": 1,
            "windowSeconds": 3600,
            "globalDailyLimit": 1,
        },
        budget_state=blocked_state,
        now=datetime(2026, 4, 17, 8, 30, tzinfo=timezone.utc),
        consume=False,
        bypass=True,
    )

    assert result["allowed"] is True
    assert result["blocked"] is False
    assert result["reason_code"] == "bypass"
    assert result["usage"]["per_symbol_daily"] == 1
    assert result["usage"]["global_daily"] == 1
