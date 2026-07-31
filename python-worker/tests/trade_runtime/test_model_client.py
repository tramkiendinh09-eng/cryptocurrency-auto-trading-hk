from trade_runtime.decision.model_client import DecisionModelClient


def test_decision_model_client_posts_runtime_model_call(monkeypatch):
    captured = {}

    class StubResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 200,
                "data": {
                    "modelId": 31,
                    "modelCode": "gpt-4.1",
                    "modelProvider": "openai",
                    "content": "{\"action\":\"OPEN_LONG\"}",
                },
            }

    def stub_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return StubResponse()

    monkeypatch.setattr("trade_runtime.decision.model_client.requests.post", stub_post)

    client = DecisionModelClient(base_url="http://localhost:8080", bearer_token="abc", timeout=4)
    result = client.call_model(model_id=31, prompt="Return JSON only")

    assert captured["url"] == "http://localhost:8080/dca/trade/runtime/model-call"
    assert captured["json"] == {"modelId": 31, "prompt": "Return JSON only"}
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 4
    assert result["modelId"] == 31
    assert result["modelCode"] == "gpt-4.1"
    assert result["modelProvider"] == "openai"
    assert result["content"] == "{\"action\":\"OPEN_LONG\"}"
