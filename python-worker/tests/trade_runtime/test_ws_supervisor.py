from trade_runtime.ingestion.ws_supervisor import MarketWebSocketSupervisor


def test_ws_supervisor_uses_rest_fallback_after_receive_error():
    captured = {"sleep": []}

    class StubClient:
        def connect(self, symbol):
            return None

        def recv(self, symbol):
            raise RuntimeError("socket closed")

        def close(self):
            return None

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "65000.0", "q": "12.0"},
        sleep=captured["sleep"].append,
    )

    payload = supervisor.fetch("BTCUSDT")

    assert payload["_market_source_status"] == "degraded"
    assert payload["s"] == "BTCUSDT"
    assert supervisor.reconnect_count == 1
    assert captured["sleep"] == [1.0]


def test_ws_supervisor_prefers_rest_fallback_over_cached_payload_after_receive_error():
    captured = {"sleep": []}
    state = {"calls": 0}

    class StubClient:
        def connect(self, symbol):
            return None

        def recv(self, symbol):
            state["calls"] += 1
            if state["calls"] == 1:
                return {"s": symbol, "p": "65000.0", "q": "12.0"}
            raise RuntimeError("socket closed")

        def close(self):
            return None

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "65100.0", "q": "13.0"},
        sleep=captured["sleep"].append,
    )

    first = supervisor.fetch("BTCUSDT")
    second = supervisor.fetch("BTCUSDT")

    assert first["_market_source_status"] == "ready"
    assert first["p"] == "65000.0"
    assert second["_market_source_status"] == "degraded"
    assert second["p"] == "65100.0"
    assert captured["sleep"] == [1.0]


def test_ws_supervisor_marks_cached_payload_stale_when_heartbeat_expires():
    clock = {"value": 0.0}

    class StubClient:
        def connect(self, symbol):
            return None

        def recv(self, symbol):
            if clock["value"] == 0.0:
                return {"s": symbol, "p": "65000.0", "q": "12.0"}
            return None

        def close(self):
            return None

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "64000.0", "q": "10.0"},
        stale_after_seconds=5.0,
        heartbeat_timeout_seconds=10.0,
        time_fn=lambda: clock["value"],
        sleep=lambda seconds: None,
    )

    first = supervisor.fetch("BTCUSDT")
    clock["value"] = 6.0
    second = supervisor.fetch("BTCUSDT")

    assert first["_market_source_status"] == "ready"
    assert second["_market_source_status"] == "stale"
    assert second["s"] == "BTCUSDT"


def test_ws_supervisor_uses_client_heartbeat_to_keep_connection_ready_without_new_payload():
    clock = {"value": 0.0}

    class StubClient:
        def __init__(self):
            self.last_heartbeat_at = None
            self.calls = 0

        def connect(self, symbol):
            return None

        def recv(self, symbol):
            self.calls += 1
            if self.calls == 1:
                self.last_heartbeat_at = clock["value"]
                return {"s": symbol, "p": "65000.0", "q": "12.0"}
            self.last_heartbeat_at = clock["value"]
            return None

        def get_last_heartbeat_at(self):
            return self.last_heartbeat_at

        def close(self):
            return None

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "64000.0", "q": "10.0"},
        stale_after_seconds=5.0,
        heartbeat_timeout_seconds=10.0,
        time_fn=lambda: clock["value"],
        sleep=lambda seconds: None,
    )

    first = supervisor.fetch("BTCUSDT")
    clock["value"] = 8.0
    second = supervisor.fetch("BTCUSDT")

    assert first["_market_source_status"] == "ready"
    assert second["_market_source_status"] == "ready"
    assert second["s"] == "BTCUSDT"


def test_ws_supervisor_reconnects_stale_connection_within_same_fetch():
    clock = {"value": 0.0}
    captured = {"closes": 0}
    instances = []

    class StubClient:
        def __init__(self):
            self.instance_id = len(instances) + 1
            instances.append(self)

        def connect(self, symbol):
            return None

        def recv(self, symbol):
            if self.instance_id == 1 and clock["value"] == 0.0:
                return {"s": symbol, "p": "65000.0", "q": "12.0"}
            if self.instance_id == 1:
                return None
            return {"s": symbol, "p": "65010.0", "q": "11.0"}

        def close(self):
            captured["closes"] += 1

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "64000.0", "q": "10.0"},
        stale_after_seconds=5.0,
        heartbeat_timeout_seconds=10.0,
        time_fn=lambda: clock["value"],
        sleep=lambda seconds: None,
    )

    first = supervisor.fetch("BTCUSDT")
    clock["value"] = 6.0
    second = supervisor.fetch("BTCUSDT")
    third = supervisor.fetch("BTCUSDT")

    assert first["_market_source_status"] == "ready"
    assert second["_market_source_status"] == "ready"
    assert second["p"] == "65010.0"
    assert third["_market_source_status"] == "ready"
    assert captured["closes"] == 1
    assert len(instances) == 2


def test_ws_supervisor_reconnects_abnormal_connection_within_same_fetch():
    clock = {"value": 0.0}
    captured = {"closes": 0}
    instances = []

    class StubClient:
        def __init__(self):
            self.instance_id = len(instances) + 1
            instances.append(self)

        def connect(self, symbol):
            return None

        def recv(self, symbol):
            if self.instance_id == 1 and clock["value"] == 0.0:
                return {"s": symbol, "p": "65000.0", "q": "12.0"}
            if self.instance_id == 1:
                return None
            return {"s": symbol, "p": "64980.0", "q": "9.0"}

        def close(self):
            captured["closes"] += 1

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "64000.0", "q": "10.0"},
        stale_after_seconds=5.0,
        heartbeat_timeout_seconds=10.0,
        time_fn=lambda: clock["value"],
        sleep=lambda seconds: None,
    )

    first = supervisor.fetch("BTCUSDT")
    clock["value"] = 12.0
    second = supervisor.fetch("BTCUSDT")
    third = supervisor.fetch("BTCUSDT")

    assert first["_market_source_status"] == "ready"
    assert second["_market_source_status"] == "ready"
    assert second["p"] == "64980.0"
    assert third["_market_source_status"] == "ready"
    assert captured["closes"] == 1
    assert len(instances) == 2


def test_ws_supervisor_uses_exponential_backoff_for_consecutive_reconnects():
    captured = {"sleep": []}

    class StubClient:
        def connect(self, symbol):
            return None

        def recv(self, symbol):
            raise RuntimeError("socket closed")

        def close(self):
            return None

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol},
        base_backoff_seconds=1.0,
        max_backoff_seconds=8.0,
        sleep=captured["sleep"].append,
    )

    supervisor.fetch("BTCUSDT")
    supervisor.fetch("BTCUSDT")
    supervisor.fetch("BTCUSDT")

    assert captured["sleep"] == [1.0, 2.0, 4.0]


def test_ws_supervisor_resets_reconnect_count_after_successful_recovery():
    captured = {"sleep": []}
    state = {"calls": 0}

    class StubClient:
        def connect(self, symbol):
            return None

        def recv(self, symbol):
            state["calls"] += 1
            if state["calls"] <= 2:
                raise RuntimeError("socket closed")
            return {"s": symbol, "p": "65100.0"}

        def close(self):
            return None

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol},
        sleep=captured["sleep"].append,
    )

    degraded = supervisor.fetch("BTCUSDT")
    ready = supervisor.fetch("BTCUSDT")

    assert degraded["_market_source_status"] == "degraded"
    assert ready["_market_source_status"] == "ready"
    assert supervisor.reconnect_count == 0


def test_ws_supervisor_rotates_connection_after_ttl_expiry():
    clock = {"value": 0.0}
    captured = {"connects": 0, "closes": 0}

    class StubClient:
        def connect(self, symbol):
            captured["connects"] += 1

        def recv(self, symbol):
            return {"s": symbol, "p": "65010.0", "q": "8.0"}

        def close(self):
            captured["closes"] += 1

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol},
        connection_ttl_seconds=10.0,
        time_fn=lambda: clock["value"],
        sleep=lambda seconds: None,
    )

    first = supervisor.fetch("BTCUSDT")
    clock["value"] = 11.0
    second = supervisor.fetch("BTCUSDT")

    assert first["_market_source_status"] == "ready"
    assert second["_market_source_status"] == "ready"
    assert captured["connects"] == 2
    assert captured["closes"] == 1


def test_ws_supervisor_reconnects_within_same_fetch_after_receive_error():
    captured = {"sleep": [], "closes": 0}
    instances = []

    class StubClient:
        def __init__(self):
            self.instance_id = len(instances) + 1
            instances.append(self)

        def connect(self, symbol):
            return None

        def recv(self, symbol):
            if self.instance_id == 1:
                raise RuntimeError("socket closed")
            return {"s": symbol, "p": "65100.0", "q": "13.0"}

        def close(self):
            captured["closes"] += 1

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "64000.0", "q": "10.0"},
        sleep=captured["sleep"].append,
    )

    payload = supervisor.fetch("BTCUSDT")

    assert payload["_market_source_status"] == "ready"
    assert payload["p"] == "65100.0"
    assert captured["sleep"] == [1.0]
    assert captured["closes"] == 1
    assert len(instances) == 2
    assert supervisor.reconnect_count == 0


def test_ws_supervisor_reconnects_within_same_fetch_when_heartbeat_is_stale():
    clock = {"value": 0.0}
    captured = {"sleep": [], "closes": 0}
    instances = []

    class StubClient:
        def __init__(self):
            self.instance_id = len(instances) + 1
            instances.append(self)

        def connect(self, symbol):
            return None

        def recv(self, symbol):
            if self.instance_id == 1 and clock["value"] == 0.0:
                return {"s": symbol, "p": "65000.0", "q": "12.0"}
            if self.instance_id == 1:
                return None
            return {"s": symbol, "p": "65010.0", "q": "11.0"}

        def close(self):
            captured["closes"] += 1

    supervisor = MarketWebSocketSupervisor(
        source_name="binance_ws",
        client_factory=StubClient,
        rest_payload_supplier=lambda symbol: {"s": symbol, "p": "64000.0", "q": "10.0"},
        stale_after_seconds=5.0,
        heartbeat_timeout_seconds=10.0,
        time_fn=lambda: clock["value"],
        sleep=captured["sleep"].append,
    )

    first = supervisor.fetch("BTCUSDT")
    clock["value"] = 6.0
    second = supervisor.fetch("BTCUSDT")

    assert first["_market_source_status"] == "ready"
    assert second["_market_source_status"] == "ready"
    assert second["p"] == "65010.0"
    assert captured["sleep"] == [1.0]
    assert captured["closes"] == 1
    assert len(instances) == 2
