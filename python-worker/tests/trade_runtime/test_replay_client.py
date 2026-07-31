from trade_runtime.replay_client import TradeReplayClient


def test_get_trace_source_uses_replay_source_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"traceId": "trace-source-1"}}

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.replay_client.requests.get", fake_get)

    client = TradeReplayClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    payload = client.get_trace_source("trace-source-1")

    assert captured["url"] == "http://localhost:8080/dca/trade/replay/source"
    assert captured["params"] == {"traceId": "trace-source-1"}
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3
    assert payload["traceId"] == "trace-source-1"


def test_create_replay_session_uses_session_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"id": 18}}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.replay_client.requests.post", fake_post)

    client = TradeReplayClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    payload = client.create_replay_session({"sessionName": "replay-trace-source-1"})

    assert captured["url"] == "http://localhost:8080/dca/trade/replay/session"
    assert captured["json"]["sessionName"] == "replay-trace-source-1"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3
    assert payload["id"] == 18


def test_post_replay_event_uses_event_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.replay_client.requests.post", fake_post)

    client = TradeReplayClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_replay_event({"sessionId": 18, "traceId": "trace-replay-1", "eventType": "news"})

    assert captured["url"] == "http://localhost:8080/dca/trade/replay/event"
    assert captured["json"]["sessionId"] == 18
    assert captured["json"]["traceId"] == "trace-replay-1"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3
