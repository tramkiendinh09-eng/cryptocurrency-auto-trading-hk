from trade_runtime.prompting.prompt_binding_resolver import resolve_prompt_binding


def test_resolve_prompt_binding_prefers_matching_scope_mode_event_strength_and_lowest_priority():
    binding = resolve_prompt_binding(
        [
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.low",
                "priority": 1,
                "enabled": True,
                "mode_scope_json": "[\"shadow\"]",
                "event_strength_scope_json": "[\"normal\",\"strong\"]",
            },
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.high",
                "priority": 20,
                "enabled": True,
                "mode_scope_json": "[\"shadow\"]",
                "event_strength_scope_json": "[\"strong\"]",
            },
            {
                "binding_scope": "MARKET_AGENT",
                "template_code": "trade.market.v1",
                "priority": 99,
                "enabled": True,
            },
        ],
        binding_scope="SUPERVISOR",
        mode="shadow",
        event_strength="strong",
    )

    assert binding is not None
    assert binding["template_code"] == "trade.supervisor.low"


def test_resolve_prompt_binding_prefers_more_specific_binding_over_global_default():
    binding = resolve_prompt_binding(
        [
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.global",
                "priority": 1,
                "enabled": True,
            },
            {
                "binding_scope": "SUPERVISOR",
                "template_code": "trade.supervisor.exact",
                "priority": 50,
                "enabled": True,
                "strategy_id": 88,
                "strategy_version_id": 188,
                "symbol": "BTCUSDT",
                "exchange_code": "BINANCE",
            },
        ],
        binding_scope="SUPERVISOR",
        mode="shadow",
        event_strength="strong",
    )

    assert binding is not None
    assert binding["template_code"] == "trade.supervisor.exact"
