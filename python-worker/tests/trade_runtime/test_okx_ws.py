import json

import websocket

from trade_runtime.ingestion.okx_ws import OkxMarketWebSocketClient, OkxWebSocketProfile


class StubMarketApiConfig:
    ws_base_url = "wss://ws.okx.com:8443"
    ws_path = "/ws/v5/public"
    ws_stream_name_template = json.dumps(
        {
            "args": [
                {"channel": "tickers", "instId": "{instId}"},
                {"channel": "mark-price", "instId": "{instId}"},
                {"channel": "funding-rate", "instId": "{instId}"},
                {"channel": "open-interest", "instId": "{instId}"},
                {"channel": "liquidation-orders", "instType": "SWAP"},
            ]
        }
    )
    ws_ping_interval_seconds = 20
    ws_pong_timeout_seconds = 60
    ws_connection_ttl_hours = 24
    ws_control_messages_per_second = 5
    ws_reconnect_attempts = 2


def test_okx_profile_renders_subscribe_args_from_market_api_config():
    profile = OkxWebSocketProfile.from_market_api_config(StubMarketApiConfig())

    assert profile.url == "wss://ws.okx.com:8443/ws/v5/public"
    assert profile.reconnect_attempts == 2
    assert profile.render_subscribe_args("BTCUSDT") == [
        {"channel": "tickers", "instId": "BTC-USDT-SWAP"},
        {"channel": "mark-price", "instId": "BTC-USDT-SWAP"},
        {"channel": "funding-rate", "instId": "BTC-USDT-SWAP"},
        {"channel": "open-interest", "instId": "BTC-USDT-SWAP"},
        {"channel": "liquidation-orders", "instType": "SWAP"},
    ]


def test_okx_profile_accepts_dict_market_api_config_with_camel_case_keys():
    profile = OkxWebSocketProfile.from_market_api_config(
        {
            "wsBaseUrl": "wss://ws.okx.com:8443",
            "wsPath": "/ws/v5/public",
            "wsStreamNameTemplate": json.dumps(
                {
                    "args": [
                        {"channel": "tickers", "instId": "{instId}"},
                        {"channel": "mark-price", "instId": "{instId}"},
                    ]
                }
            ),
            "wsPingIntervalSeconds": 15,
            "wsPongTimeoutSeconds": 45,
            "wsConnectionTtlHours": 12,
            "wsReconnectAttempts": 3,
        }
    )

    assert profile.url == "wss://ws.okx.com:8443/ws/v5/public"
    assert profile.ping_interval_seconds == 15
    assert profile.pong_timeout_seconds == 45
    assert profile.connection_ttl_seconds == 43200.0
    assert profile.reconnect_attempts == 3
    assert profile.render_subscribe_args("BTCUSDT") == [
        {"channel": "tickers", "instId": "BTC-USDT-SWAP"},
        {"channel": "mark-price", "instId": "BTC-USDT-SWAP"},
    ]


def test_okx_client_subscribes_using_profile_args(monkeypatch):
    sent_messages = []

    class StubConnection:
        def send(self, message):
            sent_messages.append(json.loads(message))

        def close(self):
            return None

    monkeypatch.setattr(
        "trade_runtime.ingestion.okx_ws.websocket.create_connection",
        lambda url, timeout: StubConnection(),
    )
    client = OkxMarketWebSocketClient(profile=OkxWebSocketProfile.from_market_api_config(StubMarketApiConfig()))

    client.connect("BTCUSDT")

    assert sent_messages == [
        {
            "op": "subscribe",
            "args": [
                {"channel": "tickers", "instId": "BTC-USDT-SWAP"},
                {"channel": "mark-price", "instId": "BTC-USDT-SWAP"},
                {"channel": "funding-rate", "instId": "BTC-USDT-SWAP"},
                {"channel": "open-interest", "instId": "BTC-USDT-SWAP"},
                {"channel": "liquidation-orders", "instType": "SWAP"},
            ],
        }
    ]


def test_okx_client_attaches_supplemental_events_to_next_ticker(monkeypatch):
    frames = iter(
        [
            json.dumps(
                {
                    "arg": {"channel": "mark-price", "instId": "BTC-USDT-SWAP"},
                    "data": [{"instId": "BTC-USDT-SWAP", "markPx": "65010.5", "ts": "1000"}],
                }
            ),
            json.dumps(
                {
                    "arg": {"channel": "funding-rate", "instId": "BTC-USDT-SWAP"},
                    "data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0.0001", "ts": "1001"}],
                }
            ),
            json.dumps(
                {
                    "arg": {"channel": "open-interest", "instId": "BTC-USDT-SWAP"},
                    "data": [{"instId": "BTC-USDT-SWAP", "oi": "12345", "ts": "1002"}],
                }
            ),
            json.dumps(
                {
                    "arg": {"channel": "liquidation-orders", "instType": "SWAP"},
                    "data": [
                        {
                            "instId": "BTC-USDT-SWAP",
                            "details": [{"bkPx": "64000", "sz": "0.5", "side": "sell", "ts": "1003"}],
                        }
                    ],
                }
            ),
            json.dumps(
                {
                    "arg": {"channel": "tickers", "instId": "BTC-USDT-SWAP"},
                    "data": [{"instId": "BTC-USDT-SWAP", "last": "65020", "vol24h": "10", "ts": "1004"}],
                }
            ),
        ]
    )

    class StubConnection:
        def send(self, message):
            return None

        def recv(self):
            return next(frames)

        def close(self):
            return None

    monkeypatch.setattr(
        "trade_runtime.ingestion.okx_ws.websocket.create_connection",
        lambda url, timeout: StubConnection(),
    )
    client = OkxMarketWebSocketClient(profile=OkxWebSocketProfile.from_market_api_config(StubMarketApiConfig()))

    payload = client.recv("BTCUSDT")

    assert payload["arg"]["channel"] == "tickers"
    assert payload["_market_events"] == [
        {"event_type": "mark_price", "symbol": "BTCUSDT", "exchange": "okx", "price": 65010.5, "event_time": "1000"},
        {"event_type": "funding_rate", "symbol": "BTCUSDT", "exchange": "okx", "funding_rate": 0.0001, "event_time": "1001"},
        {"event_type": "open_interest", "symbol": "BTCUSDT", "exchange": "okx", "open_interest": 12345.0, "event_time": "1002"},
        {
            "event_type": "liquidation",
            "symbol": "BTCUSDT",
            "exchange": "okx",
            "side": "sell",
            "price": 64000.0,
            "quantity": 0.5,
            "notionalUsd": 32000.0,
            "event_time": "1003",
        },
    ]


def test_okx_client_times_out_when_primary_ticker_never_arrives(monkeypatch):
    calls = {"time": 0.0, "recv": 0}

    class StubConnection:
        def send(self, message):
            return None

        def recv(self):
            calls["recv"] += 1
            if calls["recv"] > 5:
                raise AssertionError("recv loop did not stop before exhausting supplemental frames")
            return json.dumps(
                {
                    "arg": {"channel": "mark-price", "instId": "BTC-USDT-SWAP"},
                    "data": [{"instId": "BTC-USDT-SWAP", "markPx": "65010.5", "ts": str(1000 + calls["recv"])}],
                }
            )

        def close(self):
            return None

    def monotonic_time():
        calls["time"] += 1.0
        return calls["time"]

    monkeypatch.setattr(
        "trade_runtime.ingestion.okx_ws.websocket.create_connection",
        lambda url, timeout: StubConnection(),
    )
    client = OkxMarketWebSocketClient(
        profile=OkxWebSocketProfile.from_market_api_config(StubMarketApiConfig()),
        timeout=2.0,
        time_fn=monotonic_time,
    )

    try:
        client.recv("BTCUSDT")
    except websocket.WebSocketTimeoutException as exc:
        assert str(exc) == "okx_ws_primary_payload_timeout"
    else:
        raise AssertionError("expected okx_ws_primary_payload_timeout")
