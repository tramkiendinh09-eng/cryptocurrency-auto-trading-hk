from trade_runtime.decision.nodes.execution_node import execution_node


def test_execution_node_posts_status_and_order_status_together():
    class StubCallbackClient:
        def __init__(self):
            self.exchange_orders = []

        def post_exchange_order(self, payload):
            self.exchange_orders.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "paper-BTCUSDT",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 10000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "supervisor_decision": {
                "action": "OPEN_LONG",
                "side": "long",
                "confidence": 82,
                "size_hint": 0.2,
            },
            "risk_result": {"passed": True, "reason": "pass"},
            "callback_client": callback_client,
            "execution_router": StubExecutionRouter(),
        }
    )

    assert state["execution_result"]["status"] == "filled"
    assert state["execution_result"]["order_status"] == "FILLED"
    payload = callback_client.exchange_orders[0]
    assert payload["status"] == "filled"
    assert payload["executionStatus"] == "filled"
    assert payload["orderStatus"] == "FILLED"


def test_execution_node_applies_filled_position_effects_in_live_mode():
    class StubCallbackClient:
        def __init__(self):
            self.position_snapshots = []
            self.paper_orders = []

        def post_order_request(self, payload):
            return None

        def post_exchange_order(self, payload):
            return None

        def post_paper_trade_order(self, payload):
            self.paper_orders.append(payload)

        def post_exchange_fill(self, payload):
            return None

        def post_position_snapshot(self, payload):
            self.position_snapshots.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "order_status": "FILLED",
                "order_id": "live-close-1",
                "fill_price": 65000.0,
                "fill_quantity": 0.5,
                "position_quantity": 0.5,
                "entry_price": 65000.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-live-close-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "live",
            "account_equity": 10000.0,
            "current_position_side": "long",
            "current_position_quantity": 0.5,
            "current_position_notional": 32000.0,
            "entry_price": 64000.0,
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "supervisor_decision": {"action": "CLOSE", "side": "long", "size_hint": 1.0},
            "risk_result": {"passed": True, "reason": "pass"},
            "callback_client": callback_client,
            "execution_router": StubExecutionRouter(),
        }
    )

    assert state["execution_result"]["realized_pnl_delta"] == 500.0
    assert state["execution_result"]["account_equity"] == 10500.0
    assert state["current_position_quantity"] == 0.0
    assert callback_client.position_snapshots[-1]["positionQuantity"] == 0.0
    assert callback_client.paper_orders == []
