from trade_runtime.execution.router import ExecutionRouter


def test_execution_router_uses_paper_adapter_for_paper_mode():
    router = ExecutionRouter(binance_client=None, okx_client=None)
    result = router.execute(
        mode="paper",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 500, "price": 25000},
    )
    assert result["is_live"] is False
    assert result["exchange"] == "binance"
    assert result["status"] == "filled"
    assert result["order_status"] == "FILLED"
    assert result["fill_price"] == 25000.0
    assert result["fill_quantity"] == 0.02
    assert result["position_quantity"] == 0.02


def test_execution_router_normalizes_runtime_mode_before_routing():
    router = ExecutionRouter(binance_client=None, okx_client=None)
    result = router.execute(
        mode=" PaPeR ",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 500, "price": 25000},
    )

    assert result["is_live"] is False
    assert result["status"] == "filled"
    assert result["order_status"] == "FILLED"


def test_execution_router_does_not_touch_live_adapter_for_okx_paper_or_shadow(monkeypatch):
    def fail_if_constructed(*args, **kwargs):
        raise AssertionError("live adapter must not be constructed for simulated modes")

    monkeypatch.setattr("trade_runtime.execution.router.OkxFuturesExecutionAdapter", fail_if_constructed)
    router = ExecutionRouter(binance_client=None, okx_client=object())

    paper_result = router.execute(
        mode="paper",
        exchange="okx",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 500, "price": 25000},
    )
    shadow_result = router.execute(
        mode="shadow",
        exchange="okx",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 500, "price": 25000},
    )

    assert paper_result["status"] == "filled"
    assert paper_result["is_live"] is False
    assert shadow_result["status"] == "pending"
    assert shadow_result["is_live"] is False


def test_execution_router_prefers_base_quantity_for_paper_fill_quantity():
    router = ExecutionRouter(binance_client=None, okx_client=None)
    result = router.execute(
        mode="paper",
        exchange="okx",
        order={
            "symbol": "ETHUSDT",
            "side": "BUY",
            "quote": 900.00000264,
            "price": 2338.38,
            "quantity_base": 0.38762361,
            "trace_id": "trace-reduce-quantity-1",
        },
    )

    assert result["order_id"] == "paper-trace-reduce-quantity-1"
    assert result["fill_quantity"] == 0.38762361
    assert result["position_quantity"] == 0.38762361


def test_execution_router_skips_zero_quote_order_in_paper_mode():
    router = ExecutionRouter(binance_client=None, okx_client=None)
    result = router.execute(
        mode="paper",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 0, "price": 25000},
    )

    assert result["is_live"] is False
    assert result["exchange"] == "binance"
    assert result["status"] == "skipped"
    assert result["order_status"] == "SKIPPED"
    assert result["fill_quantity"] == 0.0
    assert result["position_quantity"] == 0.0


def test_execution_router_uses_pending_status_for_shadow_mode():
    router = ExecutionRouter(binance_client=None, okx_client=None)
    result = router.execute(
        mode="shadow",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 500, "price": 25000},
    )

    assert result["is_live"] is False
    assert result["exchange"] == "binance"
    assert result["status"] == "pending"
    assert result["order_status"] == "PENDING"
    assert result["fill_quantity"] == 0.0


def test_execution_router_wraps_legacy_binance_client_for_live_mode():
    captured = {}

    class StubLegacyBinanceClient:
        def place_market_order(self, symbol, side, quantity):
            captured["symbol"] = symbol
            captured["side"] = side
            captured["quantity"] = quantity
            return {
                "orderId": 123456,
                "status": "FILLED",
                "avgPrice": "64000.0",
                "executedQty": "0.0546875",
            }

    router = ExecutionRouter(binance_client=StubLegacyBinanceClient(), okx_client=None)
    result = router.execute(
        mode="live",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000},
    )

    assert captured["symbol"] == "BTCUSDT"
    assert captured["side"] == "BUY"
    assert captured["quantity"] == 0.05384615
    assert result["is_live"] is True
    assert result["exchange"] == "binance"
    assert result["status"] == "filled"
    assert result["order_status"] == "FILLED"
    assert result["fill_price"] == 64000.0


def test_execution_router_downgrades_live_exception_to_failed_result():
    class StubLegacyBinanceClient:
        def place_market_order(self, symbol, side, quantity):
            raise RuntimeError("network timeout")

    router = ExecutionRouter(binance_client=StubLegacyBinanceClient(), okx_client=None)
    result = router.execute(
        mode="live",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000},
    )

    assert result["status"] == "failed"
    assert result["is_live"] is True
    assert result["exchange"] == "binance"
    assert result["order_status"] == "REJECTED"
    assert result["fill_quantity"] == 0.0
    assert "network timeout" in result["error"].lower()


def test_execution_router_retries_transient_live_failure_once(monkeypatch):
    captured = {"calls": 0}

    class StubAdapter:
        def __init__(self, client):
            self.client = client

        def place_market_order(self, order):
            captured["calls"] += 1
            if captured["calls"] == 1:
                return {
                    "status": "failed",
                    "is_live": True,
                    "exchange": "binance",
                    "order_id": "",
                    "order_status": "REJECTED",
                    "fill_price": 65000.0,
                    "fill_quantity": 0.0,
                    "position_quantity": 0.0,
                    "entry_price": 65000.0,
                    "error": "network timeout",
                }
            return {
                "status": "filled",
                "is_live": True,
                "exchange": "binance",
                "order_id": "123456",
                "order_status": "FILLED",
                "fill_price": 64000.0,
                "fill_quantity": 0.0546875,
                "position_quantity": 0.0546875,
                "entry_price": 64000.0,
            }

    monkeypatch.setattr("trade_runtime.execution.router.BinanceFuturesExecutionAdapter", StubAdapter)

    router = ExecutionRouter(binance_client=object(), okx_client=None)
    result = router.execute(
        mode="live",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000},
    )

    assert captured["calls"] == 2
    assert result["status"] == "filled"
    assert result["order_id"] == "123456"


def test_execution_router_does_not_retry_non_retriable_live_failure(monkeypatch):
    captured = {"calls": 0}

    class StubAdapter:
        def __init__(self, client):
            self.client = client

        def place_market_order(self, order):
            captured["calls"] += 1
            return {
                "status": "failed",
                "is_live": True,
                "exchange": "binance",
                "order_id": "",
                "order_status": "REJECTED",
                "fill_price": 65000.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
                "error": "insufficient balance",
            }

    monkeypatch.setattr("trade_runtime.execution.router.BinanceFuturesExecutionAdapter", StubAdapter)

    router = ExecutionRouter(binance_client=object(), okx_client=None)
    result = router.execute(
        mode="live",
        exchange="binance",
        order={"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000},
    )

    assert captured["calls"] == 1
    assert result["status"] == "failed"
    assert "insufficient balance" in result["error"]


def test_execution_router_routes_live_okx_limit_order_to_enhanced_adapter(monkeypatch):
    captured = {"market_calls": 0, "enhanced_calls": 0}

    class StubAdapter:
        def __init__(self, client):
            self.client = client

        def place_market_order(self, order):
            captured["market_calls"] += 1
            return {"status": "failed", "order_status": "REJECTED", "error": "should_not_call_market"}

        def place_order(self, order):
            captured["enhanced_calls"] += 1
            captured["order"] = order
            return {
                "status": "pending",
                "is_live": True,
                "exchange": "okx",
                "order_id": "limit-1",
                "order_status": "PENDING",
                "fill_price": 65000.0,
                "fill_quantity": 0.0,
                "position_quantity": 0.0,
                "entry_price": 65000.0,
            }

    monkeypatch.setattr("trade_runtime.execution.router.OkxFuturesExecutionAdapter", StubAdapter)

    router = ExecutionRouter(binance_client=None, okx_client=object())
    result = router.execute(
        mode="live",
        exchange="okx",
        order={
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quote": 3500,
            "price": 65000,
            "order_type": "limit",
            "limit_price": 64950,
            "position_side": "long",
            "reduce_only": True,
        },
    )

    assert captured["market_calls"] == 0
    assert captured["enhanced_calls"] == 1
    assert captured["order"]["position_side"] == "long"
    assert result["order_id"] == "limit-1"


def test_execution_router_routes_okx_market_order_to_exchange_adapter(monkeypatch):
    captured = {"market_calls": 0, "enhanced_calls": 0}

    class StubAdapter:
        def __init__(self, client):
            self.client = client

        def place_market_order(self, order):
            captured["market_calls"] += 1
            return {
                "status": "filled",
                "is_live": True,
                "exchange": "okx",
                "order_id": "market-1",
                "order_status": "FILLED",
                "fill_price": 65000.0,
                "fill_quantity": 0.05,
                "position_quantity": 0.05,
                "entry_price": 65000.0,
            }

        def place_order(self, order):
            captured["enhanced_calls"] += 1
            captured["order"] = order
            return {
                "status": "filled",
                "is_live": True,
                "exchange": "okx",
                "order_id": "market-1",
                "order_status": "FILLED",
                "fill_price": 65000.0,
                "fill_quantity": 0.05,
                "position_quantity": 0.05,
                "entry_price": 65000.0,
            }

    monkeypatch.setattr("trade_runtime.execution.router.OkxFuturesExecutionAdapter", StubAdapter)

    router = ExecutionRouter(binance_client=None, okx_client=object())
    result = router.execute(
        mode="live",
        exchange="okx",
        order={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quote": 3500,
            "price": 65000,
            "order_type": "market",
            "position_side": "long",
            "reduce_only": False,
        },
    )

    assert captured["market_calls"] == 0
    assert captured["enhanced_calls"] == 1
    assert captured["order"]["position_side"] == "long"
    assert result["order_id"] == "market-1"
