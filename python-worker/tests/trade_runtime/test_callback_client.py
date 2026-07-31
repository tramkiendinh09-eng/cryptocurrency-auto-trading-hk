import pytest

from trade_runtime.callback_client import RuntimeCallbackClient


def test_post_order_request_uses_runtime_order_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_order_request(
        {
            "traceId": "trace-1",
            "exchangeCode": "binance",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "mode": "paper",
            "quoteAmount": 3500,
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/execution/order"
    assert captured["json"]["traceId"] == "trace-1"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_decision_audit_uses_runtime_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_decision_audit(
        {
            "traceId": "trace-1",
            "symbol": "BTCUSDT",
            "mode": "paper",
            "action": "OPEN_LONG",
            "confidence": 86,
            "modelCode": "gpt-4.1",
            "modelProvider": "openai",
            "summaryReason": "multi-signal aligned",
            "signalEvents": [
                {
                    "traceId": "trace-1",
                    "symbol": "BTCUSDT",
                    "signalType": "news",
                    "featureJson": '{"event_type":"news","headline":"ETF inflow"}',
                }
            ],
            "agentRuns": [
                {
                    "traceId": "trace-1",
                    "symbol": "BTCUSDT",
                    "agentName": "news",
                    "eventStrength": "strong",
                    "status": "completed",
                }
            ],
            "agentObservations": [
                {
                    "traceId": "trace-1",
                    "agentName": "news",
                    "observationType": "event_context",
                    "observationJson": '{"events":[{"event_type":"news","headline":"ETF inflow"}]}',
                }
            ],
            "agentConclusions": [
                {
                    "traceId": "trace-1",
                    "agentName": "news",
                    "bias": "bullish",
                    "confidence": 86,
                    "reason": "ETF inflow",
                }
            ],
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/decision/audit"
    assert captured["json"]["traceId"] == "trace-1"
    assert captured["json"]["modelCode"] == "gpt-4.1"
    assert captured["json"]["modelProvider"] == "openai"
    assert captured["json"]["signalEvents"][0]["signalType"] == "news"
    assert captured["json"]["agentRuns"][0]["agentName"] == "news"
    assert captured["json"]["agentObservations"][0]["observationType"] == "event_context"
    assert captured["json"]["agentConclusions"][0]["agentName"] == "news"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_pnl_snapshot_uses_runtime_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_pnl_snapshot(
        {
            "traceId": "trace-1",
            "mode": "paper",
            "accountEquity": 10250.25,
            "dailyPnl": 120.50,
            "maxDrawdownPct": 4.25,
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/execution/pnl-snapshot"
    assert captured["json"]["traceId"] == "trace-1"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_position_snapshot_uses_runtime_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_position_snapshot(
        {
            "exchangeCode": "binance",
            "symbol": "BTCUSDT",
            "side": "long",
            "positionQuantity": 0.0538,
            "entryPrice": 65000.0,
            "unrealizedPnl": 0,
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/execution/position-snapshot"
    assert captured["json"]["symbol"] == "BTCUSDT"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_pnl_snapshot_raises_on_ajax_result_business_error(monkeypatch):
    class DummyResponse:
        headers = {"Content-Type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 500, "msg": "Duplicate entry pnl_snapshot"}

    monkeypatch.setattr(
        "trade_runtime.callback_client.requests.post",
        lambda url, json, headers, timeout: DummyResponse(),
    )

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)

    with pytest.raises(RuntimeError, match="pnl-snapshot"):
        client.post_pnl_snapshot(
            {
                "traceId": "trace-dup-pnl",
                "mode": "paper",
                "accountEquity": 9980.0,
                "dailyPnl": -20.0,
                "maxDrawdownPct": 0.2,
            }
        )


def test_post_position_snapshot_raises_on_ajax_result_business_error(monkeypatch):
    class DummyResponse:
        headers = {"Content-Type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 500, "msg": "Duplicate entry position_snapshot"}

    monkeypatch.setattr(
        "trade_runtime.callback_client.requests.post",
        lambda url, json, headers, timeout: DummyResponse(),
    )

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)

    with pytest.raises(RuntimeError, match="position-snapshot"):
        client.post_position_snapshot(
            {
                "exchangeCode": "binance",
                "symbol": "BTCUSDT",
                "side": "short",
                "positionQuantity": 0.02,
                "entryPrice": 65000.0,
                "unrealizedPnl": -12.0,
            }
        )


def test_post_exchange_order_uses_runtime_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_exchange_order(
        {
            "traceId": "trace-2",
            "exchangeCode": "binance",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "mode": "paper",
            "orderRef": "paper-BTCUSDT",
            "status": "filled",
            "executionStatus": "filled",
            "orderStatus": "FILLED",
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/execution/exchange-order"
    assert captured["json"]["orderRef"] == "paper-BTCUSDT"
    assert captured["json"]["status"] == "filled"
    assert captured["json"]["executionStatus"] == "filled"
    assert captured["json"]["orderStatus"] == "FILLED"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_exchange_fill_uses_runtime_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_exchange_fill(
        {
            "traceId": "trace-3",
            "orderRef": "paper-BTCUSDT",
            "fillPrice": 65000.0,
            "fillQuantity": 0.0538,
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/execution/exchange-fill"
    assert captured["json"]["orderRef"] == "paper-BTCUSDT"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_risk_guard_hit_uses_runtime_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_risk_guard_hit(
        {
            "traceId": "trace-risk-1",
            "ruleCode": "market_source_abnormal",
            "reason": "market_source_abnormal",
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/execution/risk-guard-hit"
    assert captured["json"]["ruleCode"] == "market_source_abnormal"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_worker_heartbeat_uses_taskqueue_heartbeat_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_worker_heartbeat("runtime-worker-1")

    assert captured["url"] == "http://localhost:8080/dca/taskqueue/heartbeat"
    assert captured["params"] == {"workerId": "runtime-worker-1"}
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_paper_trade_order_uses_replay_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_paper_trade_order(
        {
            "traceId": "trace-paper-1",
            "exchangeCode": "binance",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "mode": "paper",
            "orderRef": "paper-BTCUSDT",
            "quoteAmount": 3500,
            "status": "filled",
            "executionStatus": "filled",
            "orderStatus": "FILLED",
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/replay/paper-order"
    assert captured["json"]["traceId"] == "trace-paper-1"
    assert captured["json"]["executionStatus"] == "filled"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_post_shadow_decision_log_uses_replay_endpoint(monkeypatch):
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

    monkeypatch.setattr("trade_runtime.callback_client.requests.post", fake_post)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.post_shadow_decision_log(
        {
            "traceId": "trace-shadow-1",
            "exchangeCode": "okx",
            "symbol": "ETHUSDT",
            "mode": "shadow",
            "action": "OPEN_LONG",
            "side": "long",
            "confidence": 78,
            "summaryReason": "news and market aligned",
            "executionStatus": "pending",
            "orderStatus": "PENDING",
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/trade/replay/shadow-decision"
    assert captured["json"]["traceId"] == "trace-shadow-1"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_get_recent_supervisor_decisions_includes_mode_when_provided(monkeypatch):
    captured = {}

    class DummyResponse:
        headers = {"Content-Type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 200,
                "data": [
                    {
                        "traceId": "trace-2",
                        "speakerAgent": "supervisor_agent",
                        "messageType": "final_decision",
                        "contentJson": "{\"action\":\"HOLD\"}",
                    }
                ],
            }

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.callback_client.requests.get", fake_get)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    result = client.get_recent_supervisor_decisions(
        "BTCUSDT",
        mode="paper",
        limit=2,
        exclude_trace_id="trace-current",
    )

    assert captured["url"] == "http://localhost:8080/dca/decision/supervisor-history"
    assert captured["params"] == {
        "symbol": "BTCUSDT",
        "mode": "paper",
        "limit": 2,
        "excludeTraceId": "trace-current",
    }
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3
    assert result[0]["traceId"] == "trace-2"


def test_get_recent_supervisor_decisions_uses_decision_history_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        headers = {"Content-Type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 200,
                "data": [
                    {
                        "traceId": "trace-2",
                        "speakerAgent": "supervisor_agent",
                        "messageType": "final_decision",
                        "contentJson": "{\"action\":\"HOLD\"}",
                    }
                ],
            }

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.callback_client.requests.get", fake_get)

    client = RuntimeCallbackClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    result = client.get_recent_supervisor_decisions("BTCUSDT", limit=2, exclude_trace_id="trace-current")

    assert captured["url"] == "http://localhost:8080/dca/decision/supervisor-history"
    assert captured["params"] == {"symbol": "BTCUSDT", "limit": 2, "excludeTraceId": "trace-current"}
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3
    assert result[0]["traceId"] == "trace-2"
