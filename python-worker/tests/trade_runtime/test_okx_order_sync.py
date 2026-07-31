import json

from trade_runtime.execution.clients import OKX_NOFX_ORDER_TAG, OkxRestExecutionClient
from trade_runtime.execution.order_sync import OkxOrderSyncService


class StubCallbackClient:
    def __init__(self):
        self.orders = []
        self.fills = []

    def post_exchange_order(self, payload):
        self.orders.append(payload)

    def post_exchange_fill(self, payload):
        self.fills.append(payload)


def test_okx_rest_execution_client_uses_post_only_order_type_for_maker_limit_order():
    captured = {"posts": []}

    class StubSession:
        def get(self, url, headers=None, timeout=None):
            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {
                        "code": "0",
                        "data": [
                            {
                                "instId": "BTC-USDT-SWAP",
                                "ctVal": "0.01",
                                "lotSz": "1",
                                "minSz": "1",
                                "maxMktSz": "1000",
                                "tickSz": "0.1",
                            }
                        ],
                    }

            return Response()

        def post(self, url, headers=None, data=None, timeout=None):
            captured["posts"].append({"url": url, "data": json.loads(data)})

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"code": "0", "data": [{"ordId": "post-only-1", "state": "live"}]}

            return Response()

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: "2026-05-11T00:00:00.000Z",
    )

    client.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "position_side": "long",
            "order_type": "limit",
            "limit_price": 65000,
            "quantity_base": 0.05,
            "client_id": "trace-maker-1",
            "post_only": True,
        }
    )

    submitted = captured["posts"][0]["data"]
    assert submitted["ordType"] == "post_only"
    assert submitted["px"] == "65000"
    assert submitted["clOrdId"] == "trace-maker-1"
    assert submitted["tag"] == OKX_NOFX_ORDER_TAG


def test_okx_rest_execution_client_builds_signed_history_queries():
    captured = []

    class StubSession:
        def get(self, url, headers=None, timeout=None):
            captured.append({"url": url, "headers": headers, "timeout": timeout})

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"code": "0", "data": []}

            return Response()

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: "2026-05-11T00:00:00.000Z",
    )

    client.get_order_history(symbol="BTCUSDT", limit=200, begin=1710000000000, end=1710003600000)
    client.get_fills_history(symbol="BTCUSDT", limit=0, begin=1710000000000, end=1710003600000)

    assert captured[0]["url"] == (
        "https://www.okx.com/api/v5/trade/orders-history?"
        "instType=SWAP&limit=100&instId=BTC-USDT-SWAP&begin=1710000000000&end=1710003600000"
    )
    assert captured[1]["url"] == (
        "https://www.okx.com/api/v5/trade/fills-history?"
        "instType=SWAP&limit=100&instId=BTC-USDT-SWAP&begin=1710000000000&end=1710003600000"
    )
    assert captured[0]["headers"]["OK-ACCESS-KEY"] == "key-1"


def test_okx_order_sync_posts_normalized_orders_and_fills_from_live_history():
    class StubOkxClient:
        def get_order_history(self, **kwargs):
            assert kwargs == {"symbol": "BTCUSDT", "limit": 100, "begin": None, "end": None}
            return {
                "code": "0",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "ordId": "okx-order-1",
                        "clOrdId": "trace-sync-1",
                        "side": "buy",
                        "posSide": "long",
                        "ordType": "post_only",
                        "sz": "5",
                        "px": "65000",
                        "accFillSz": "2",
                        "avgPx": "64999.5",
                        "fee": "-0.01",
                        "feeCcy": "USDT",
                        "state": "partially_filled",
                        "cTime": "1710000000000",
                        "uTime": "1710000060000",
                    }
                ],
            }

        def get_fills_history(self, **kwargs):
            assert kwargs == {"symbol": "BTCUSDT", "limit": 100, "begin": None, "end": None}
            return {
                "code": "0",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "tradeId": "okx-trade-1",
                        "ordId": "okx-order-1",
                        "side": "buy",
                        "posSide": "long",
                        "fillPx": "64999.5",
                        "fillSz": "2",
                        "fee": "-0.01",
                        "feeCcy": "USDT",
                        "execType": "M",
                        "pnl": "1.25",
                        "ts": "1710000060000",
                    }
                ],
            }

        def base_quantity_from_contracts(self, symbol, contracts):
            assert symbol == "BTCUSDT"
            return round(float(contracts) * 0.01, 8)

    callbacks = StubCallbackClient()
    service = OkxOrderSyncService(okx_client=StubOkxClient(), callback_client=callbacks)

    result = service.sync_once(symbol="BTCUSDT", mode="live")

    assert result == {"orders": 1, "fills": 1, "skipped": False}
    assert callbacks.orders[0]["exchangeCode"] == "okx"
    assert callbacks.orders[0]["orderRef"] == "okx-order-1"
    assert callbacks.orders[0]["clientOrderId"] == "trace-sync-1"
    assert callbacks.orders[0]["orderStatus"] == "PARTIALLY_FILLED"
    assert callbacks.orders[0]["status"] == "partial"
    assert callbacks.orders[0]["quantityBase"] == 0.05
    assert callbacks.orders[0]["filledQuantity"] == 0.02
    assert callbacks.orders[0]["avgFillPrice"] == 64999.5
    assert callbacks.orders[0]["fee"] == 0.01
    assert callbacks.orders[0]["feeCcy"] == "USDT"
    assert callbacks.orders[0]["postOnly"] is True
    assert callbacks.orders[0]["createdAt"] == "2024-03-09T16:00:00.000Z"
    assert callbacks.orders[0]["updatedAt"] == "2024-03-09T16:01:00.000Z"
    assert callbacks.orders[0]["rawPayload"]

    assert callbacks.fills[0]["exchangeCode"] == "okx"
    assert callbacks.fills[0]["tradeId"] == "okx-trade-1"
    assert callbacks.fills[0]["orderRef"] == "okx-order-1"
    assert callbacks.fills[0]["fillPrice"] == 64999.5
    assert callbacks.fills[0]["fillQuantity"] == 0.02
    assert callbacks.fills[0]["fee"] == 0.01
    assert callbacks.fills[0]["isMaker"] is True
    assert callbacks.fills[0]["execType"] == "M"
    assert callbacks.fills[0]["realizedPnl"] == 1.25
    assert callbacks.fills[0]["filledAt"] == "2024-03-09T16:01:00.000Z"


def test_okx_order_sync_does_not_call_history_endpoints_in_paper_mode():
    class StubOkxClient:
        def get_order_history(self, **kwargs):
            raise AssertionError("paper mode must not query OKX order history")

        def get_fills_history(self, **kwargs):
            raise AssertionError("paper mode must not query OKX fill history")

    service = OkxOrderSyncService(okx_client=StubOkxClient(), callback_client=StubCallbackClient())

    assert service.sync_once(symbol="BTCUSDT", mode="paper") == {"orders": 0, "fills": 0, "skipped": True}


def test_runtime_app_runs_okx_order_sync_after_live_iteration():
    from trade_runtime.app import TradeRuntimeApp
    from trade_runtime.execution.router import ExecutionRouter

    class StubOkxClient:
        def get_order_history(self, **kwargs):
            return {
                "code": "0",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "ordId": "live-loop-order-1",
                        "clOrdId": "trace-loop-1",
                        "side": "sell",
                        "posSide": "short",
                        "ordType": "limit",
                        "sz": "3",
                        "px": "64000",
                        "state": "live",
                        "cTime": "1710000000000",
                        "uTime": "1710000005000",
                    }
                ],
            }

        def get_fills_history(self, **kwargs):
            return {"code": "0", "data": []}

        def base_quantity_from_contracts(self, symbol, contracts):
            return round(float(contracts) * 0.01, 8)

    callbacks = StubCallbackClient()

    class StubRunner:
        def __init__(self):
            self.callback_client = callbacks
            self.execution_router = ExecutionRouter(binance_client=None, okx_client=StubOkxClient())

        def run_once(self, **kwargs):
            return {"status": "ok", "mode": "live", "trace_id": kwargs["trace_id"]}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        trace_id_supplier=lambda: "trace-loop-1",
    )

    result = app.run_once()

    assert result["okx_order_sync_result"] == {"orders": 1, "fills": 0, "skipped": False}
    assert callbacks.orders[0]["orderRef"] == "live-loop-order-1"
    assert callbacks.orders[0]["status"] == "pending"


def test_runtime_app_does_not_query_okx_history_for_paper_iteration():
    from trade_runtime.app import TradeRuntimeApp
    from trade_runtime.execution.router import ExecutionRouter

    class StubOkxClient:
        def get_order_history(self, **kwargs):
            raise AssertionError("paper iteration must not query OKX order history")

        def get_fills_history(self, **kwargs):
            raise AssertionError("paper iteration must not query OKX fill history")

    callbacks = StubCallbackClient()

    class StubRunner:
        def __init__(self):
            self.callback_client = callbacks
            self.execution_router = ExecutionRouter(binance_client=None, okx_client=StubOkxClient())

        def run_once(self, **kwargs):
            return {"status": "ok", "mode": "paper", "trace_id": kwargs["trace_id"]}

    app = TradeRuntimeApp(
        runner=StubRunner(),
        symbol="BTCUSDT",
        exchange="okx",
        trace_id_supplier=lambda: "trace-paper-1",
    )

    result = app.run_once()

    assert "okx_order_sync_result" not in result
    assert callbacks.orders == []
    assert callbacks.fills == []


def test_execution_node_posts_enriched_order_and_fill_payloads_for_paper_mode():
    from trade_runtime.decision.nodes.execution_node import execution_node

    callbacks = StubCallbackClient()
    state = {
        "trace_id": "trace-paper-sync-1",
        "symbol": "BTCUSDT",
        "exchange": "okx",
        "mode": "paper",
        "account_equity": 10000.0,
        "feature_snapshot": {"mark_price": 65000.0},
        "supervisor_decision": {
            "action": "OPEN_LONG",
            "side": "BUY",
            "size_hint": 0.01,
            "order_type": "limit",
            "limit_price": 64900.0,
            "post_only": True,
        },
        "risk_result": {"passed": True, "reason": "pass"},
        "callback_client": callbacks,
        "timestamp_supplier": lambda: "2026-05-11T00:00:00.000Z",
    }

    execution_node(state)

    assert callbacks.orders[0]["exchangeCode"] == "okx"
    assert callbacks.orders[0]["mode"] == "paper"
    assert callbacks.orders[0]["orderRef"] == "paper-trace-paper-sync-1"
    assert callbacks.orders[0]["clientOrderId"] == "trace-paper-sync-1"
    assert callbacks.orders[0]["orderType"] == "limit"
    assert callbacks.orders[0]["postOnly"] is True
    assert callbacks.orders[0]["filledQuantity"] == callbacks.orders[0]["quantityBase"]
    assert callbacks.orders[0]["avgFillPrice"] == 65000.0
    assert callbacks.orders[0]["filledAt"] == "2026-05-11T00:00:00.000Z"
    assert callbacks.orders[0]["rawPayload"]

    assert callbacks.fills[0]["exchangeCode"] == "okx"
    assert callbacks.fills[0]["symbol"] == "BTCUSDT"
    assert callbacks.fills[0]["positionSide"] == "long"
    assert callbacks.fills[0]["tradeId"] == "paper-trace-paper-sync-1-fill"
    assert callbacks.fills[0]["filledAt"] == "2026-05-11T00:00:00.000Z"
    assert callbacks.fills[0]["rawPayload"]
