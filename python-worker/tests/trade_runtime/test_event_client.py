from trade_runtime.event_client import RuntimeEventClient


def test_post_event_uses_event_ingest_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.event_client.requests.post", fake_post)

    client = RuntimeEventClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_event(
        trace_id="trace-1",
        event={
            "event_type": "market_tick",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "price": 65000.5,
            "volume": 12.4,
        },
    )

    assert captured["url"] == "http://localhost:8080/dca/event/ingest"
    assert captured["json"]["traceId"] == "trace-1"
    assert captured["json"]["eventType"] == "market_tick"
    assert captured["json"]["symbol"] == "BTCUSDT"
    assert captured["json"]["exchange"] == "binance"
    assert '"price": 65000.5' in captured["json"]["payloadJson"]
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_get_market_history_uses_age_limited_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"price": 101.0}]}

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.event_client.requests.get", fake_get)

    client = RuntimeEventClient(base_url="http://localhost:8080/", bearer_token="", timeout=7)
    result = client.get_market_history(symbol="ETHUSDT", exchange="okx", limit=48, max_age_minutes=300)

    assert result == [{"price": 101.0}]
    assert captured["url"] == "http://localhost:8080/dca/event/market-history"
    assert captured["params"] == {"symbol": "ETHUSDT", "exchange": "okx", "limit": 48, "maxAgeMinutes": 300}
    assert "Authorization" not in captured["headers"]
    assert captured["timeout"] == 7
