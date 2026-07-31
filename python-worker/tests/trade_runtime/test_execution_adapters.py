from trade_runtime.execution.binance_futures import BinanceFuturesExecutionAdapter
from trade_runtime.execution.okx_futures import OkxFuturesExecutionAdapter


def test_binance_live_adapter_fails_when_client_is_missing():
    adapter = BinanceFuturesExecutionAdapter(client=None)

    result = adapter.place_market_order({"symbol": "BTCUSDT", "side": "BUY", "price": 65000.0, "quote": 1000.0})

    assert result["status"] == "failed"
    assert result["order_status"] == "REJECTED"
    assert result["error"] == "live_execution_client_unavailable"


def test_okx_live_adapter_fails_when_client_is_missing():
    adapter = OkxFuturesExecutionAdapter(client=None)

    result = adapter.place_market_order({"symbol": "BTCUSDT", "side": "BUY", "price": 65000.0, "quote": 1000.0})

    assert result["status"] == "failed"
    assert result["order_status"] == "REJECTED"
    assert result["error"] == "live_execution_client_unavailable"


def test_okx_live_adapter_uses_enhanced_place_order_and_converts_fill_contracts():
    captured = {}

    class StubOkxClient:
        def place_order(self, order):
            captured["order"] = order
            return {"code": "0", "data": [{"ordId": "okx-1", "state": "filled", "avgPx": "65000", "fillSz": "5"}]}

        def base_quantity_from_contracts(self, symbol, contracts):
            captured["conversion"] = {"symbol": symbol, "contracts": contracts}
            return 0.05

    adapter = OkxFuturesExecutionAdapter(client=StubOkxClient())

    result = adapter.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "position_side": "long",
            "order_type": "limit",
            "limit_price": 65000.0,
            "quantity_base": 0.05,
            "reduce_only": True,
        }
    )

    assert captured["order"]["order_type"] == "limit"
    assert captured["conversion"] == {"symbol": "BTCUSDT", "contracts": "5"}
    assert result["status"] == "filled"
    assert result["order_status"] == "FILLED"
    assert result["fill_quantity"] == 0.05
    assert result["position_quantity"] == 0.05


def test_okx_live_adapter_uses_specialized_open_method_for_market_open():
    captured = {}

    class StubOkxClient:
        def ensure_dual_position_mode(self):
            captured["position_mode_checked"] = True

        def open_long(self, symbol, quantity, leverage, *, td_mode="cross"):
            captured["open_long"] = {
                "symbol": symbol,
                "quantity": quantity,
                "leverage": leverage,
                "td_mode": td_mode,
            }
            return {"code": "0", "data": [{"ordId": "open-long-1", "state": "filled", "avgPx": "65000", "fillSz": "5"}]}

        def open_short(self, symbol, quantity, leverage, *, td_mode="cross"):
            captured["open_short"] = True
            return {"code": "0", "data": [{"ordId": "open-short-1", "state": "filled"}]}

        def place_order(self, order):
            captured["place_order"] = True
            return {"code": "0", "data": [{"ordId": "generic-1", "state": "filled"}]}

        def base_quantity_from_contracts(self, symbol, contracts):
            captured["conversion"] = {"symbol": symbol, "contracts": contracts}
            return 0.05

    adapter = OkxFuturesExecutionAdapter(client=StubOkxClient())

    result = adapter.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "position_side": "long",
            "action": "OPEN_LONG",
            "order_type": "market",
            "quantity_base": 0.05,
            "leverage": 3,
            "td_mode": "cross",
        }
    )

    assert captured["position_mode_checked"] is True
    assert captured["open_long"] == {"symbol": "BTCUSDT", "quantity": 0.05, "leverage": 3, "td_mode": "cross"}
    assert "place_order" not in captured
    assert "open_short" not in captured
    assert captured["conversion"] == {"symbol": "BTCUSDT", "contracts": "5"}
    assert result["status"] == "filled"
    assert result["order_id"] == "open-long-1"


def test_okx_live_adapter_polls_open_ack_before_marking_filled():
    captured = {"status_queries": []}

    class StubOkxClient:
        def ensure_dual_position_mode(self):
            captured["position_mode_checked"] = True

        def open_long(self, symbol, quantity, leverage, *, td_mode="cross"):
            captured["open_long"] = {"symbol": symbol, "quantity": quantity, "leverage": leverage, "td_mode": td_mode}
            return {"code": "0", "data": [{"ordId": "open-long-ack", "sCode": "0"}]}

        def open_short(self, symbol, quantity, leverage, *, td_mode="cross"):
            captured["open_short"] = True
            return {"code": "0", "data": [{"ordId": "open-short-ack", "sCode": "0"}]}

        def get_order_status(self, symbol, order_id):
            captured["status_queries"].append({"symbol": symbol, "order_id": order_id})
            return {
                "code": "0",
                "data": [{"ordId": order_id, "state": "filled", "avgPx": "65000", "accFillSz": "5"}],
            }

        def base_quantity_from_contracts(self, symbol, contracts):
            captured["conversion"] = {"symbol": symbol, "contracts": contracts}
            return 0.05

    adapter = OkxFuturesExecutionAdapter(client=StubOkxClient())

    result = adapter.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "position_side": "long",
            "action": "OPEN_LONG",
            "order_type": "market",
            "quantity_base": 0.05,
            "leverage": 3,
            "td_mode": "cross",
        }
    )

    assert captured["open_long"] == {"symbol": "BTCUSDT", "quantity": 0.05, "leverage": 3, "td_mode": "cross"}
    assert captured["status_queries"] == [{"symbol": "BTCUSDT", "order_id": "open-long-ack"}]
    assert captured["conversion"] == {"symbol": "BTCUSDT", "contracts": "5"}
    assert result["status"] == "filled"
    assert result["order_status"] == "FILLED"
    assert result["fill_price"] == 65000.0
    assert result["fill_quantity"] == 0.05


def test_okx_live_adapter_keeps_unconfirmed_ack_pending_without_status_lookup():
    class StubOkxClient:
        def place_order(self, order):
            return {"code": "0", "data": [{"ordId": "ack-only", "sCode": "0"}]}

    adapter = OkxFuturesExecutionAdapter(client=StubOkxClient())

    result = adapter.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "position_side": "long",
            "order_type": "limit",
            "limit_price": 65000.0,
            "quantity_base": 0.05,
        }
    )

    assert result["status"] == "pending"
    assert result["order_status"] == "PENDING"
    assert result["order_id"] == "ack-only"
    assert result["fill_quantity"] == 0.0
    assert result["position_quantity"] == 0.0


def test_okx_live_adapter_uses_specialized_close_method_for_explicit_side_action():
    captured = {}

    class StubOkxClient:
        def ensure_dual_position_mode(self):
            captured["position_mode_checked"] = True

        def close_long(self, symbol, quantity, *, td_mode="cross"):
            captured["close_long"] = {"symbol": symbol, "quantity": quantity, "td_mode": td_mode}
            return {"code": "0", "data": [{"ordId": "close-long-1", "state": "filled", "avgPx": "65000", "fillSz": "5"}]}

        def close_short(self, symbol, quantity, *, td_mode="cross"):
            captured["close_short"] = True
            return {"code": "0", "data": [{"ordId": "close-short-1", "state": "filled"}]}

        def place_order(self, order):
            captured["place_order"] = True
            return {"code": "0", "data": [{"ordId": "generic-close", "state": "filled"}]}

        def base_quantity_from_contracts(self, symbol, contracts):
            captured["conversion"] = {"symbol": symbol, "contracts": contracts}
            return 0.05

    adapter = OkxFuturesExecutionAdapter(client=StubOkxClient())

    result = adapter.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "position_side": "long",
            "action": "CLOSE_LONG",
            "order_type": "market",
            "quantity_base": 0.05,
            "td_mode": "cross",
        }
    )

    assert captured["close_long"] == {"symbol": "BTCUSDT", "quantity": 0.05, "td_mode": "cross"}
    assert "place_order" not in captured
    assert "close_short" not in captured
    assert captured["conversion"] == {"symbol": "BTCUSDT", "contracts": "5"}
    assert result["status"] == "filled"
    assert result["order_id"] == "close-long-1"


def test_okx_live_adapter_rejects_empty_order_data_without_fill_calculation():
    class StubOkxClient:
        def place_order(self, order):
            return {"code": "0", "data": []}

    adapter = OkxFuturesExecutionAdapter(client=StubOkxClient())

    result = adapter.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 65000.0,
            "quote": 1000.0,
            "order_type": "limit",
            "limit_price": 64950.0,
        }
    )

    assert result["status"] == "failed"
    assert result["order_status"] == "REJECTED"
    assert result["fill_quantity"] == 0.0
    assert result["error"] == "invalid_okx_response"


def test_okx_live_adapter_treats_item_scode_failure_as_failed_order():
    class StubOkxClient:
        def place_order(self, order):
            return {
                "code": "0",
                "data": [
                    {
                        "ordId": "",
                        "sCode": "51008",
                        "sMsg": "insufficient balance",
                    }
                ],
            }

    adapter = OkxFuturesExecutionAdapter(client=StubOkxClient())

    result = adapter.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 65000.0,
            "quote": 1000.0,
            "order_type": "limit",
            "limit_price": 64950.0,
        }
    )

    assert result["status"] == "failed"
    assert result["order_status"] == "REJECTED"
    assert "insufficient balance" in result["error"]
