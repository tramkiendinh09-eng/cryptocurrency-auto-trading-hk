import websocket

from trade_runtime.ingestion.binance_ws import BinanceMarketWebSocketClient, BinanceWebSocketProfile


def test_binance_ws_profile_defaults_to_futures_websocket_base_url():
    profile = BinanceWebSocketProfile()

    assert profile.base_url == "wss://fstream.binance.com"


def test_binance_ws_profile_builds_raw_stream_url_with_lowercase_symbol():
    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            base_url="wss://fstream.binance.com",
            path="/ws",
            stream_name_template="{symbol_lower}@ticker",
            combined_enabled=False,
            symbol_lowercase=True,
        )
    )

    assert client.build_url("BTCUSDT") == "wss://fstream.binance.com/ws/btcusdt@ticker"


def test_binance_ws_profile_builds_combined_stream_url_for_multiple_symbols():
    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            base_url="wss://fstream.binance.com",
            path="/stream",
            stream_name_template="{symbol_lower}@ticker",
            combined_enabled=True,
            symbol_lowercase=True,
        )
    )

    assert client.build_url(["BTCUSDT", "ETHUSDT"]) == (
        "wss://fstream.binance.com/stream?streams=btcusdt@ticker/ethusdt@ticker"
    )


def test_binance_ws_profile_builds_combined_stream_url_for_multiple_templates():
    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            base_url="wss://fstream.binance.com",
            path="/ws",
            stream_name_template='["{symbol_lower}@ticker", "{symbol_lower}@markPrice", "{symbol_lower}@forceOrder"]',
            combined_enabled=False,
            symbol_lowercase=True,
        )
    )

    assert client.build_url("BTCUSDT") == (
        "wss://fstream.binance.com/stream?streams=btcusdt@ticker/btcusdt@markPrice/btcusdt@forceOrder"
    )


def test_binance_ws_profile_forces_stream_path_and_lowercase_for_combined_streams():
    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            base_url="wss://fstream.binance.com",
            path="/ws",
            stream_name_template="{symbol}@ticker",
            combined_enabled=True,
            symbol_lowercase=False,
        )
    )

    assert client.build_url(["BTCUSDT", "ETHUSDT"]) == (
        "wss://fstream.binance.com/stream?streams=btcusdt@ticker/ethusdt@ticker"
    )


def test_binance_ws_profile_forces_raw_path_and_lowercase_for_single_stream():
    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            base_url="wss://fstream.binance.com",
            path="/stream",
            stream_name_template="{symbol}@ticker",
            combined_enabled=False,
            symbol_lowercase=False,
        )
    )

    assert client.build_url("BTCUSDT") == "wss://fstream.binance.com/ws/btcusdt@ticker"


def test_binance_ws_client_reuses_combined_connection_and_routes_payloads_by_symbol(monkeypatch):
    created_urls = []
    connections = []

    class StubFrame:
        def __init__(self, data):
            self.data = data

    class StubConnection:
        def __init__(self, frames):
            self.frames = list(frames)
            self.closed = 0

        def recv_data_frame(self, control_frame=False):
            if not self.frames:
                raise websocket.WebSocketTimeoutException("timeout")
            return self.frames.pop(0)

        def close(self):
            self.closed += 1

    def create_connection(url, timeout=None, **kwargs):
        del timeout
        del kwargs
        created_urls.append(url)
        if len(created_urls) == 1:
            connection = StubConnection(
                [
                    (
                        websocket.ABNF.OPCODE_TEXT,
                        StubFrame('{"stream":"btcusdt@ticker","data":{"s":"BTCUSDT","p":"65000.0","q":"12.0"}}'),
                    )
                ]
            )
        else:
            connection = StubConnection(
                [
                    (
                        websocket.ABNF.OPCODE_TEXT,
                        StubFrame('{"stream":"btcusdt@ticker","data":{"s":"BTCUSDT","p":"65010.0","q":"11.0"}}'),
                    ),
                    (
                        websocket.ABNF.OPCODE_TEXT,
                        StubFrame('{"stream":"ethusdt@ticker","data":{"s":"ETHUSDT","p":"3200.0","q":"8.0"}}'),
                    ),
                ]
            )
        connections.append(connection)
        return connection

    monkeypatch.setattr("trade_runtime.ingestion.binance_ws.websocket.create_connection", create_connection)

    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            base_url="wss://fstream.binance.com",
            path="/stream",
            stream_name_template="{symbol_lower}@ticker",
            combined_enabled=True,
            symbol_lowercase=True,
        )
    )

    btc_first = client.recv("BTCUSDT")
    eth_payload = client.recv("ETHUSDT")
    btc_cached = client.recv("BTCUSDT")

    assert btc_first["s"] == "BTCUSDT"
    assert eth_payload["s"] == "ETHUSDT"
    assert btc_cached["s"] == "BTCUSDT"
    assert created_urls == [
        "wss://fstream.binance.com/stream?streams=btcusdt@ticker",
        "wss://fstream.binance.com/stream?streams=btcusdt@ticker/ethusdt@ticker",
    ]
    assert connections[0].closed == 1
    assert connections[1].closed == 0


def test_binance_ws_profile_rejects_combined_stream_count_above_limit():
    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            base_url="wss://fstream.binance.com",
            path="/stream",
            stream_name_template="{symbol_lower}@ticker",
            combined_enabled=True,
            symbol_lowercase=True,
            max_streams_per_connection=2,
        )
    )

    try:
        client.build_url(["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    except ValueError as exc:
        assert str(exc) == "binance_ws_max_streams_exceeded"
    else:
        raise AssertionError("expected binance_ws_max_streams_exceeded")


def test_binance_ws_client_replies_pong_and_continues_to_next_data_frame(monkeypatch):
    class StubFrame:
        def __init__(self, opcode, data):
            self.opcode = opcode
            self.data = data

    class StubConnection:
        def __init__(self):
            self.frames = [
                StubFrame(websocket.ABNF.OPCODE_PING, b"heartbeat-1"),
                StubFrame(websocket.ABNF.OPCODE_TEXT, b'{"data":{"s":"BTCUSDT","p":"65000.0","q":"12.0"}}'),
            ]
            self.pongs = []

        def recv_frame(self):
            if not self.frames:
                raise websocket.WebSocketTimeoutException("timeout")
            return self.frames.pop(0)

        def pong(self, payload=b""):
            self.pongs.append(payload)

        def close(self):
            return None

    connection = StubConnection()
    monkeypatch.setattr(
        "trade_runtime.ingestion.binance_ws.websocket.create_connection",
        lambda url, timeout=None, **kwargs: connection,
    )

    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(control_messages_per_second=5),
        time_fn=lambda: 100.0,
    )

    payload = client.recv("BTCUSDT")

    assert payload["s"] == "BTCUSDT"
    assert connection.pongs == [b"heartbeat-1"]
    assert client.get_last_heartbeat_at() == 100.0


def test_binance_ws_client_collects_supplemental_market_events_until_primary_ticker(monkeypatch):
    class StubFrame:
        def __init__(self, data):
            self.data = data

    class StubConnection:
        def __init__(self):
            self.frames = [
                (
                    websocket.ABNF.OPCODE_TEXT,
                    StubFrame(
                        '{"stream":"btcusdt@markPrice","data":{"e":"markPriceUpdate","s":"BTCUSDT","p":"64980.5","r":"0.0004"}}'
                    ),
                ),
                (
                    websocket.ABNF.OPCODE_TEXT,
                    StubFrame(
                        '{"stream":"btcusdt@forceOrder","data":{"e":"forceOrder","o":{"s":"BTCUSDT","S":"SELL","ap":"64950.0","q":"12.5"}}}'
                    ),
                ),
                (
                    websocket.ABNF.OPCODE_TEXT,
                    StubFrame('{"stream":"btcusdt@ticker","data":{"s":"BTCUSDT","c":"65000.0","q":"12.0"}}'),
                ),
            ]

        def recv_data_frame(self, control_frame=False):
            del control_frame
            if not self.frames:
                raise websocket.WebSocketTimeoutException("timeout")
            return self.frames.pop(0)

        def close(self):
            return None

    monkeypatch.setattr(
        "trade_runtime.ingestion.binance_ws.websocket.create_connection",
        lambda url, timeout=None, **kwargs: StubConnection(),
    )

    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            stream_name_template='["{symbol_lower}@ticker", "{symbol_lower}@markPrice", "{symbol_lower}@forceOrder"]',
            combined_enabled=True,
        )
    )

    payload = client.recv("BTCUSDT")

    assert payload["s"] == "BTCUSDT"
    assert [item["event_type"] for item in payload["_market_events"]] == ["mark_price", "funding_rate", "liquidation"]
    assert payload["_market_events"][0]["price"] == 64980.5
    assert payload["_market_events"][1]["funding_rate"] == 0.0004
    assert payload["_market_events"][2]["notionalUsd"] == 811875.0


def test_binance_ws_client_raises_when_control_message_budget_is_exceeded(monkeypatch):
    clock = {"value": 100.0}

    class StubFrame:
        def __init__(self, opcode, data):
            self.opcode = opcode
            self.data = data

    class StubConnection:
        def __init__(self):
            self.frames = [
                StubFrame(websocket.ABNF.OPCODE_PING, b"heartbeat-1"),
                StubFrame(websocket.ABNF.OPCODE_PING, b"heartbeat-2"),
            ]
            self.pongs = []

        def recv_frame(self):
            if not self.frames:
                raise websocket.WebSocketTimeoutException("timeout")
            return self.frames.pop(0)

        def pong(self, payload=b""):
            self.pongs.append(payload)

        def close(self):
            return None

    connection = StubConnection()
    monkeypatch.setattr(
        "trade_runtime.ingestion.binance_ws.websocket.create_connection",
        lambda url, timeout=None, **kwargs: connection,
    )

    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(control_messages_per_second=1),
        time_fn=lambda: clock["value"],
    )

    try:
        client.recv("BTCUSDT")
    except RuntimeError as exc:
        assert str(exc) == "binance_ws_control_budget_exceeded"
    else:
        raise AssertionError("expected binance_ws_control_budget_exceeded")

    assert connection.pongs == [b"heartbeat-1"]


def test_binance_ws_profile_reads_configured_reconnect_attempts():
    class StubMarketApiConfig:
        ws_reconnect_attempts = 2

    profile = BinanceWebSocketProfile.from_market_api_config(StubMarketApiConfig())

    assert profile.reconnect_attempts == 2


def test_binance_ws_client_times_out_when_primary_ticker_never_arrives(monkeypatch):
    calls = {"time": 0.0, "recv": 0}

    class StubFrame:
        def __init__(self, data):
            self.data = data

    class StubConnection:
        def recv_data_frame(self, control_frame=False):
            del control_frame
            calls["recv"] += 1
            if calls["recv"] > 5:
                raise AssertionError("recv loop did not stop before exhausting supplemental frames")
            return (
                websocket.ABNF.OPCODE_TEXT,
                StubFrame(
                    '{"stream":"btcusdt@markPrice","data":{"e":"markPriceUpdate","s":"BTCUSDT","p":"64980.5","r":"0.0004"}}'
                ),
            )

        def close(self):
            return None

    def monotonic_time():
        calls["time"] += 1.0
        return calls["time"]

    monkeypatch.setattr(
        "trade_runtime.ingestion.binance_ws.websocket.create_connection",
        lambda url, timeout=None, **kwargs: StubConnection(),
    )

    client = BinanceMarketWebSocketClient(
        profile=BinanceWebSocketProfile(
            stream_name_template='["{symbol_lower}@ticker", "{symbol_lower}@markPrice"]',
            combined_enabled=True,
        ),
        timeout=2.0,
        time_fn=monotonic_time,
    )

    try:
        client.recv("BTCUSDT")
    except websocket.WebSocketTimeoutException as exc:
        assert str(exc) == "binance_ws_primary_payload_timeout"
    else:
        raise AssertionError("expected binance_ws_primary_payload_timeout")
