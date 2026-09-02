import base64
import hashlib
import hmac
import json

from trade_runtime.execution.binance_futures import BinanceFuturesExecutionAdapter
from trade_runtime.execution.clients import BinanceRestExecutionClient, LegacyBinanceExecutionClient, OKX_NOFX_ORDER_TAG, OkxRestExecutionClient


def test_legacy_binance_execution_client_converts_order_dict_to_legacy_signature():
    captured = {}

    class StubLegacyClient:
        def place_market_order(self, symbol, side, quantity):
            captured["symbol"] = symbol
            captured["side"] = side
            captured["quantity"] = quantity
            return {"orderId": 123456, "status": "NEW"}

    client = LegacyBinanceExecutionClient(StubLegacyClient())
    payload = client.place_market_order(
        {"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000}
    )

    assert captured["symbol"] == "BTCUSDT"
    assert captured["side"] == "BUY"
    assert captured["quantity"] == 0.05384615
    assert payload["orderId"] == 123456


def test_legacy_binance_execution_client_delegates_order_status_lookup():
    captured = {}

    class StubLegacyClient:
        def get_order_status(self, symbol, order_id):
            captured["symbol"] = symbol
            captured["order_id"] = order_id
            return {"orderId": order_id, "status": "FILLED"}

    client = LegacyBinanceExecutionClient(StubLegacyClient())
    payload = client.get_order_status("BTCUSDT", 123456)

    assert captured["symbol"] == "BTCUSDT"
    assert captured["order_id"] == 123456
    assert payload["status"] == "FILLED"


def test_binance_futures_adapter_supports_wrapped_legacy_client():
    class StubLegacyClient:
        def place_market_order(self, symbol, side, quantity):
            assert symbol == "BTCUSDT"
            assert side == "BUY"
            assert quantity == 0.05384615
            return {
                "orderId": 123456,
                "status": "NEW",
            }

        def get_order_status(self, symbol, order_id):
            assert symbol == "BTCUSDT"
            assert order_id == 123456
            return {
                "orderId": 123456,
                "status": "FILLED",
                "executedQty": 0.0546875,
                "cummulativeQuoteQty": 3500.0,
                "price": 0,
            }

    adapter = BinanceFuturesExecutionAdapter(LegacyBinanceExecutionClient(StubLegacyClient()))
    result = adapter.place_market_order(
        {"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000}
    )

    assert result["order_id"] == "123456"
    assert result["order_status"] == "FILLED"
    assert result["fill_quantity"] == 0.0546875
    assert result["fill_price"] == 64000.0


def test_binance_rest_execution_client_places_market_order_with_signed_request():
    captured = {}

    class StubSession:
        headers = {}

        def request(self, method, url, timeout=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["timeout"] = timeout
            captured["kwargs"] = kwargs

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"orderId": 123456, "status": "NEW"}

            return Response()

    class StubFilters:
        """Keeps this test hermetic; filter behaviour is covered separately."""

        def resolve_quantity(self, symbol, quantity, price):
            from trade_runtime.execution.symbol_filters import QuantityDecision

            # BTCUSDT trades on a 0.001 grid: 0.05384615 -> 0.053
            snapped = int(quantity * 1000) / 1000
            return QuantityDecision(snapped, True, "", snapped * price)

        def format_quantity(self, symbol, quantity):
            return f"{quantity:.3f}"

    client = BinanceRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        testnet=True,
        session=StubSession(),
        timestamp_supplier=lambda: 1713268800000,
        symbol_filters=StubFilters(),
    )
    payload = client.place_market_order({"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000})

    assert captured["method"] == "POST"
    assert captured["url"] == "https://demo-fapi.binance.com/fapi/v1/order"
    assert captured["timeout"] == 10
    assert captured["kwargs"]["params"]["symbol"] == "BTCUSDT"
    assert captured["kwargs"]["params"]["side"] == "BUY"
    assert captured["kwargs"]["params"]["type"] == "MARKET"
    # step-aligned, not the raw 0.05384615 the venue would have rejected
    assert captured["kwargs"]["params"]["quantity"] == "0.053"
    assert captured["kwargs"]["params"]["timestamp"] == 1713268800000
    assert captured["kwargs"]["params"]["signature"]
    assert payload["orderId"] == 123456


def test_binance_rest_execution_client_queries_order_status_with_signed_request():
    captured = {}

    class StubSession:
        headers = {}

        def request(self, method, url, timeout=None, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["timeout"] = timeout
            captured["kwargs"] = kwargs

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {
                        "orderId": 123456,
                        "status": "FILLED",
                        "executedQty": "0.05384615",
                        "cummulativeQuoteQty": "3500.0",
                    }

            return Response()

    client = BinanceRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        session=StubSession(),
        timestamp_supplier=lambda: 1713268800001,
    )
    payload = client.get_order_status("BTCUSDT", 123456)

    assert captured["method"] == "GET"
    assert captured["url"] == "https://fapi.binance.com/fapi/v1/order"
    assert captured["kwargs"]["params"]["symbol"] == "BTCUSDT"
    assert captured["kwargs"]["params"]["orderId"] == 123456
    assert captured["kwargs"]["params"]["timestamp"] == 1713268800001
    assert captured["kwargs"]["params"]["signature"]
    assert payload["status"] == "FILLED"


def test_okx_rest_execution_client_places_market_order_with_signed_request():
    captured = {}
    timestamp = "2026-04-14T12:00:00.000Z"
    body = f'{{"instId":"BTC-USDT-SWAP","tdMode":"cross","side":"buy","ordType":"market","sz":"0.05384615","tag":"{OKX_NOFX_ORDER_TAG}"}}'
    expected_sign = base64.b64encode(
        hmac.new(
            b"secret-1",
            f"{timestamp}POST/api/v5/trade/order{body}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    class StubSession:
        def post(self, url, headers=None, data=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            captured["timeout"] = timeout

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"data": [{"ordId": "98765", "state": "live"}]}

            return Response()

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: timestamp,
    )
    payload = client.place_market_order(
        {"symbol": "BTCUSDT", "side": "BUY", "quote": 3500, "price": 65000}
    )

    assert captured["url"] == "https://www.okx.com/api/v5/trade/order"
    assert captured["headers"]["OK-ACCESS-KEY"] == "key-1"
    assert captured["headers"]["OK-ACCESS-PASSPHRASE"] == "pass-1"
    assert captured["headers"]["OK-ACCESS-TIMESTAMP"] == timestamp
    assert captured["headers"]["OK-ACCESS-SIGN"] == expected_sign
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["data"] == body
    assert payload["data"][0]["ordId"] == "98765"


def test_okx_rest_execution_client_queries_order_status_with_signed_request():
    captured = {}
    timestamp = "2026-04-14T12:00:00.000Z"
    query = "/api/v5/trade/order?instId=BTC-USDT-SWAP&ordId=98765"
    expected_sign = base64.b64encode(
        hmac.new(
            b"secret-1",
            f"{timestamp}GET{query}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    class StubSession:
        def get(self, url, headers=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"data": [{"ordId": "98765", "state": "filled"}]}

            return Response()

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: timestamp,
    )
    payload = client.get_order_status("BTCUSDT", "98765")

    assert captured["url"] == "https://www.okx.com/api/v5/trade/order?instId=BTC-USDT-SWAP&ordId=98765"
    assert captured["headers"]["OK-ACCESS-SIGN"] == expected_sign
    assert payload["data"][0]["state"] == "filled"


def test_okx_rest_execution_client_places_enhanced_limit_order_with_contract_size_and_position_side():
    captured = {"gets": [], "posts": []}
    timestamp = "2026-04-14T12:00:00.000Z"

    class StubSession:
        def get(self, url, headers=None, timeout=None):
            captured["gets"].append({"url": url, "headers": headers, "timeout": timeout})

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
                                "ctMult": "1",
                                "lotSz": "1",
                                "minSz": "1",
                                "maxMktSz": "1000",
                                "tickSz": "0.1",
                            }
                        ],
                    }

            return Response()

        def post(self, url, headers=None, data=None, timeout=None):
            captured["posts"].append({"url": url, "headers": headers, "data": data, "timeout": timeout})

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"code": "0", "data": [{"ordId": "limit-1", "state": "live"}]}

            return Response()

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: timestamp,
    )

    payload = client.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "position_side": "long",
            "order_type": "limit",
            "limit_price": 65000.126,
            "quantity_base": 0.05384615,
            "reduce_only": True,
            "client_id": "trace-1",
        }
    )

    assert captured["gets"][0]["url"] == (
        "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=BTC-USDT-SWAP"
    )
    submitted = json.loads(captured["posts"][0]["data"])
    assert submitted == {
        "instId": "BTC-USDT-SWAP",
        "tdMode": "cross",
        "side": "sell",
        "ordType": "limit",
        "sz": "5",
        "posSide": "long",
        "px": "65000.1",
        "clOrdId": "trace-1",
        "tag": OKX_NOFX_ORDER_TAG,
        "reduceOnly": "true",
    }
    assert payload["data"][0]["ordId"] == "limit-1"


def test_okx_rest_execution_client_sets_leverage_before_enhanced_order():
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
                    return {"code": "0", "data": [{"ordId": "okx-lev-1", "state": "live"}]}

            return Response()

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: "2026-04-14T12:00:00.000Z",
    )

    client.place_order(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "position_side": "long",
            "order_type": "limit",
            "limit_price": 65000,
            "quantity_base": 0.05,
            "leverage": 3,
        }
    )

    assert captured["posts"][0]["url"] == "https://www.okx.com/api/v5/account/set-leverage"
    assert captured["posts"][0]["data"] == {
        "instId": "BTC-USDT-SWAP",
        "lever": "3",
        "mgnMode": "cross",
        "posSide": "long",
    }
    assert captured["posts"][1]["url"] == "https://www.okx.com/api/v5/trade/order"


def test_okx_rest_execution_client_open_long_payload_matches_nofx_fields():
    captured = {}
    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=object(),
        timestamp_supplier=lambda: "2026-04-14T12:00:00.000Z",
    )
    client.ensure_dual_position_mode = lambda: "long_short_mode"
    client.cancel_all_orders = lambda symbol: 0
    client.set_leverage = lambda symbol, leverage, *, td_mode="cross", position_side="": {"code": "0"}
    client.get_instrument = lambda symbol: {
        "instId": "BTC-USDT-SWAP",
        "ctVal": 0.01,
        "lotSz": "1",
        "minSz": 1,
        "maxMktSz": 1000,
        "tickSz": "0.1",
    }
    client._generate_cl_ord_id = lambda prefix="": f"{OKX_NOFX_ORDER_TAG}fixed"

    def request_json(method, request_path, payload=None):
        captured["method"] = method
        captured["request_path"] = request_path
        captured["payload"] = payload
        return {"code": "0", "data": [{"ordId": "open-long-1", "sCode": "0"}]}

    client._request_json = request_json

    result = client.open_long("BTCUSDT", 0.05, 3, td_mode="cross")

    assert captured["method"] == "POST"
    assert captured["request_path"] == "/api/v5/trade/order"
    assert captured["payload"] == {
        "instId": "BTC-USDT-SWAP",
        "tdMode": "cross",
        "side": "buy",
        "posSide": "long",
        "ordType": "market",
        "sz": "5",
        "clOrdId": f"{OKX_NOFX_ORDER_TAG}fixed",
        "tag": OKX_NOFX_ORDER_TAG,
    }
    assert result["data"][0]["ordId"] == "open-long-1"


def test_okx_rest_execution_client_rejects_size_below_minimum_instead_of_expanding_risk():
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

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: "2026-04-14T12:00:00.000Z",
    )

    try:
        client.place_order(
            {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "limit",
                "limit_price": 65000,
                "quantity_base": 0.001,
            }
        )
    except ValueError as exc:
        assert "okx_order_size_below_minimum" in str(exc)
    else:
        raise AssertionError("expected size below minimum to be rejected")


def test_okx_rest_execution_client_reads_balance_and_positions_with_base_quantity_conversion():
    captured = []

    class StubSession:
        def get(self, url, headers=None, timeout=None):
            captured.append(url)

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    if "account/balance" in url:
                        return {
                            "code": "0",
                            "data": [
                                {
                                    "totalEq": "10000.5",
                                    "details": [
                                        {"ccy": "USDT", "availBal": "9500.25", "upl": "12.5"},
                                    ],
                                }
                            ],
                        }
                    if "public/instruments" in url:
                        return {
                            "code": "0",
                            "data": [
                                {
                                    "instId": "BTC-USDT-SWAP",
                                    "ctVal": "0.01",
                                    "ctMult": "1",
                                    "lotSz": "1",
                                    "minSz": "1",
                                    "maxMktSz": "1000",
                                    "tickSz": "0.1",
                                }
                            ],
                        }
                    return {
                        "code": "0",
                        "data": [
                            {
                                "instId": "BTC-USDT-SWAP",
                                "posSide": "long",
                                "pos": "5",
                                "avgPx": "64000",
                                "markPx": "65000",
                                "upl": "50",
                                "lever": "3",
                                "liqPx": "50000",
                                "margin": "1000",
                                "mgnMode": "cross",
                                "cTime": "1713268800000",
                                "uTime": "1713268860000",
                            }
                        ],
                    }

            return Response()

    client = OkxRestExecutionClient(
        api_key="key-1",
        api_secret="secret-1",
        passphrase="pass-1",
        session=StubSession(),
        timestamp_supplier=lambda: "2026-04-14T12:00:00.000Z",
    )

    balance = client.get_balance()
    positions = client.get_positions(symbol="BTCUSDT")

    assert balance == {
        "total_equity": 10000.5,
        "available_balance": 9500.25,
        "total_unrealized_profit": 12.5,
        "currency": "USDT",
    }
    assert positions == [
        {
            "symbol": "BTCUSDT",
            "positionAmt": 0.05,
            "entryPrice": 64000.0,
            "markPrice": 65000.0,
            "unRealizedProfit": 50.0,
            "leverage": 3.0,
            "liquidationPrice": 50000.0,
            "side": "long",
            "mgnMode": "cross",
            "createdTime": "1713268800000",
            "updatedTime": "1713268860000",
        }
    ]
