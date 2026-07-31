from trade_runtime.task_queue_client import RuntimeTaskQueueClient


def test_pull_task_uses_runtime_taskqueue_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"taskId": "task-1", "taskType": "TRADE_RUNTIME_REPLAY"}}

    def fake_post(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.task_queue_client.requests.post", fake_post)

    client = RuntimeTaskQueueClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    payload = client.pull_task(worker_id="runtime-worker-1")

    assert captured["url"] == "http://localhost:8080/dca/taskqueue/pull"
    assert captured["params"] == {"workerId": "runtime-worker-1"}
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3
    assert payload["taskId"] == "task-1"


def test_save_task_result_uses_result_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, params, json, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.task_queue_client.requests.post", fake_post)

    client = RuntimeTaskQueueClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.save_task_result("task-1", {"success": True})

    assert captured["url"] == "http://localhost:8080/dca/taskqueue/result"
    assert captured["params"] == {"taskId": "task-1"}
    assert captured["json"]["success"] is True


def test_update_task_status_uses_status_endpoint(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

    def fake_put(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.task_queue_client.requests.put", fake_put)

    client = RuntimeTaskQueueClient(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    client.update_task_status("task-1", "completed", '{"success":true}')

    assert captured["url"] == "http://localhost:8080/dca/taskqueue/status"
    assert captured["params"] == {
        "taskId": "task-1",
        "status": "completed",
        "result": '{"success":true}',
    }
