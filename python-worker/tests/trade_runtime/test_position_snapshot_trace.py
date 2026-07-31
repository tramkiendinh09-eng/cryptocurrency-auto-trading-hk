from trade_runtime.decision.graph import build_decision_graph
from trade_runtime.decision.nodes.execution_node import execution_node


def test_position_snapshot_callback_includes_trace_id():
    class StubRiskGuard:
        def evaluate(self, **kwargs):
            return {"passed": True, "reason": "pass"}

    class StubCallbackClient:
        def __init__(self):
            self.position_payloads = []

        def post_order_request(self, payload):
            return None

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            return None

        def post_decision_audit(self, payload):
            return None

        def post_pnl_snapshot(self, payload):
            return None

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"{mode}-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()
    graph = build_decision_graph()
    graph.invoke(
        {
            "trace_id": "trace-position-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "paper",
            "risk_guard": StubRiskGuard(),
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert callback_client.position_payloads[0]["traceId"] == "trace-position-1"


def test_position_snapshot_callback_carries_runtime_user_id_when_available():
    class StubCallbackClient:
        def __init__(self):
            self.position_payloads = []

        def post_order_request(self, payload):
            return None

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            return None

        def post_decision_audit(self, payload):
            return None

        def post_pnl_snapshot(self, payload):
            return None

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"{mode}-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()
    graph = build_decision_graph()
    graph.invoke(
        {
            "trace_id": "trace-position-user-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "feature_snapshot": {"price_change_pct": 6.4},
            "mode": "paper",
            "risk_guard": type("StubRiskGuard", (), {"evaluate": lambda self, **kwargs: {"passed": True, "reason": "pass"}})(),
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
            "strategy_context": {"user_id": 42},
        }
    )

    assert callback_client.position_payloads[0]["userId"] == 42


def test_execution_node_posts_zero_position_snapshot_after_close_fill():
    class StubCallbackClient:
        def __init__(self):
            self.position_payloads = []

        def post_order_request(self, payload):
            return None

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

        def post_exchange_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            return None

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"{mode}-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 64000.0,
                "fill_quantity": 0.5,
                "position_quantity": 0.5,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-close-1",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "event_bundle": [{"event_type": "market_tick", "price": 64000.0}],
            "account_equity": 10000.0,
            "current_position_side": "long",
            "current_position_quantity": 0.5,
            "current_position_notional": 32000.0,
            "supervisor_decision": {
                "action": "CLOSE",
                "side": "long",
                "size_hint": 1.0,
            },
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    assert state["execution_result"]["status"] == "filled"
    assert callback_client.position_payloads[-1]["positionQuantity"] == 0.0


def test_execution_node_reduces_short_by_position_quantity_not_entry_notional():
    class StubCallbackClient:
        def __init__(self):
            self.order_requests = []
            self.fills = []
            self.position_payloads = []

        def post_order_request(self, payload):
            self.order_requests.append(payload)

        def post_exchange_order(self, payload):
            return None

        def post_paper_trade_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            self.fills.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-short-reduce-quantity-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "mode": "paper",
            "event_bundle": [{"event_type": "market_tick", "price": 2338.38}],
            "account_equity": 10000.0,
            "current_position_side": "short",
            "current_position_quantity": 0.77524722,
            "current_position_notional": 1800.00000528,
            "entry_price": 2321.84,
            "supervisor_decision": {"action": "REDUCE", "side": "short", "size_hint": 0.5},
            "risk_result": {"passed": True, "reason": "pass"},
            "callback_client": callback_client,
        }
    )

    assert callback_client.order_requests[-1]["quantityBase"] == 0.38762361
    assert callback_client.fills[-1]["fillPrice"] == 2338.38
    assert callback_client.fills[-1]["fillQuantity"] == 0.38762361
    assert state["execution_result"]["fill_quantity"] == 0.38762361
    assert state["current_position_quantity"] == 0.38762361
    assert callback_client.position_payloads[-1]["positionQuantity"] == 0.38762361


def test_execution_node_closes_short_by_remaining_quantity_not_entry_notional():
    class StubCallbackClient:
        def __init__(self):
            self.order_requests = []
            self.fills = []
            self.position_payloads = []

        def post_order_request(self, payload):
            self.order_requests.append(payload)

        def post_exchange_order(self, payload):
            return None

        def post_paper_trade_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            self.fills.append(payload)

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-short-close-quantity-1",
            "symbol": "ETHUSDT",
            "exchange": "okx",
            "mode": "paper",
            "event_bundle": [{"event_type": "market_tick", "price": 2340.46}],
            "account_equity": 10000.0,
            "current_position_side": "short",
            "current_position_quantity": 0.09901311,
            "current_position_notional": 229.89259932,
            "entry_price": 2321.84,
            "supervisor_decision": {"action": "CLOSE", "side": "short", "size_hint": 1.0},
            "risk_result": {"passed": True, "reason": "pass"},
            "callback_client": callback_client,
        }
    )

    assert callback_client.order_requests[-1]["quantityBase"] == 0.09901311
    assert callback_client.fills[-1]["fillPrice"] == 2340.46
    assert callback_client.fills[-1]["fillQuantity"] == 0.09901311
    assert state["execution_result"]["fill_quantity"] == 0.09901311
    assert state["current_position_quantity"] == 0.0
    assert callback_client.position_payloads[-1]["positionQuantity"] == 0.0


def test_add_operation_keeps_current_trace_and_carries_entry_trace_id():
    """ADD操作应该使用entry_trace_id而不是当前决策的trace_id"""
    class StubCallbackClient:
        def __init__(self):
            self.position_payloads = []

        def post_order_request(self, payload):
            return None

        def post_exchange_order(self, payload):
            return None

        def post_paper_trade_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            return None

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"{mode}-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 65000.0,
                "fill_quantity": 0.1,
                "position_quantity": 0.6,
                "entry_price": 64500.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-add-1",  # ADD决策的trace_id
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "account_equity": 10000.0,
            "current_position_side": "long",
            "current_position_quantity": 0.5,
            "current_position_notional": 32000.0,
            "entry_price": 64000.0,
            "entry_trace_id": "trace-open-1",  # 原始OPEN决策的trace_id
            "supervisor_decision": {"action": "ADD_LONG", "side": "long", "size_hint": 0.1},  # 提供 size_hint
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    # 验证：position_snapshot应该使用entry_trace_id，而不是当前决策的trace_id
    assert callback_client.position_payloads[-1]["traceId"] == "trace-add-1"
    assert callback_client.position_payloads[-1]["entryTraceId"] == "trace-open-1"


def test_reduce_operation_keeps_current_trace_and_carries_entry_trace_id():
    """REDUCE操作应该使用entry_trace_id而不是当前决策的trace_id"""
    class StubCallbackClient:
        def __init__(self):
            self.position_payloads = []

        def post_order_request(self, payload):
            return None

        def post_exchange_order(self, payload):
            return None

        def post_paper_trade_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            return None

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"{mode}-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 65000.0,
                "fill_quantity": 0.25,
                "position_quantity": 0.25,
                "entry_price": 64000.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-reduce-1",  # REDUCE决策的trace_id
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "account_equity": 10000.0,
            "current_position_side": "long",
            "current_position_quantity": 0.5,
            "current_position_notional": 32000.0,
            "entry_price": 64000.0,
            "entry_trace_id": "trace-open-1",  # 原始OPEN决策的trace_id
            "supervisor_decision": {"action": "REDUCE", "side": "long", "size_hint": 0.5},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    # 验证：position_snapshot应该使用entry_trace_id，而不是当前决策的trace_id
    assert callback_client.position_payloads[-1]["traceId"] == "trace-reduce-1"
    assert callback_client.position_payloads[-1]["entryTraceId"] == "trace-open-1"


def test_close_operation_keeps_current_trace_and_carries_entry_trace_id():
    """CLOSE操作应该使用entry_trace_id"""
    class StubCallbackClient:
        def __init__(self):
            self.position_payloads = []

        def post_order_request(self, payload):
            return None

        def post_exchange_order(self, payload):
            return None

        def post_paper_trade_order(self, payload):
            return None

        def post_exchange_fill(self, payload):
            return None

        def post_position_snapshot(self, payload):
            self.position_payloads.append(payload)

    class StubExecutionRouter:
        def execute(self, *, mode, exchange, order):
            return {
                "status": "filled",
                "is_live": False,
                "exchange": exchange,
                "order_id": f"{mode}-{order['symbol']}",
                "order_status": "FILLED",
                "fill_price": 65000.0,
                "fill_quantity": 0.5,
                "position_quantity": 0.0,
                "entry_price": 0.0,
            }

    callback_client = StubCallbackClient()
    state = execution_node(
        {
            "trace_id": "trace-close-1",  # CLOSE决策的trace_id
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "mode": "paper",
            "event_bundle": [{"event_type": "market_tick", "price": 65000.0}],
            "account_equity": 10000.0,
            "current_position_side": "long",
            "current_position_quantity": 0.5,
            "current_position_notional": 32000.0,
            "entry_price": 64000.0,
            "entry_trace_id": "trace-open-1",  # 原始OPEN决策的trace_id
            "supervisor_decision": {"action": "CLOSE", "side": "long"},
            "risk_result": {"passed": True, "reason": "pass"},
            "execution_router": StubExecutionRouter(),
            "callback_client": callback_client,
        }
    )

    # 验证：position_snapshot应该使用entry_trace_id
    assert callback_client.position_payloads[-1]["traceId"] == "trace-close-1"
    assert callback_client.position_payloads[-1]["entryTraceId"] == "trace-open-1"
