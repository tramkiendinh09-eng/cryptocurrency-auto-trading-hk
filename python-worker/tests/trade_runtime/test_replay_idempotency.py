from trade_runtime.replay_runner import TradeReplayRunner


def test_replay_runner_uses_stable_replay_trace_and_keeps_event_order():
    captured = {"runner_call": None}

    class FakeReplayClient:
        def get_trace_source(self, trace_id):
            return {"traceId": trace_id, "symbol": "BTCUSDT", "exchangeCode": "binance", "eventBundle": []}

        def ensure_session(self, *, source_trace_id, session_id=None, replay_trace_id=None):
            return {"id": session_id or 9, "replay_trace_id": f"replay-{session_id or 9}-{source_trace_id}"}

        def list_source_events(self, trace_id):
            return [
                {"event_time": 3, "payload": {"event_type": "social", "score": 0.4}, "symbol": "BTCUSDT", "exchange_code": "binance"},
                {"event_time": 1, "payload": {"event_type": "news", "score": 0.8}, "symbol": "BTCUSDT", "exchange_code": "binance"},
                {"event_time": 2, "payload": {"event_type": "onchain", "flow": "exchange_outflow"}, "symbol": "BTCUSDT", "exchange_code": "binance"},
            ]

        def post_replay_event(self, payload):
            return None

        def update_replay_session(self, payload):
            return None

    class FakeRuntimeRunner:
        def run_once(self, **kwargs):
            captured["runner_call"] = kwargs
            return {"execution_result": {"status": "filled", "order_status": "FILLED"}}

    runner = TradeReplayRunner(replay_client=FakeReplayClient(), runtime_runner=FakeRuntimeRunner())

    result = runner.run_trace("source-trace-1", session_id=9)

    assert result["source_trace_id"] == "source-trace-1"
    assert result["replay_trace_id"] == "replay-9-source-trace-1"
    assert result["event_count"] == 3
    assert result["events_in_order"] is True
    assert [item["event_type"] for item in captured["runner_call"]["event_bundle"]] == ["news", "onchain", "social"]


def test_replay_runner_is_idempotent_for_same_session():
    class FakeReplayClient:
        def get_trace_source(self, trace_id):
            return {"traceId": trace_id, "symbol": "BTCUSDT", "exchangeCode": "binance", "eventBundle": [{"event_type": "news", "score": 0.8}]}

        def ensure_session(self, *, source_trace_id, session_id=None, replay_trace_id=None):
            return {"id": session_id or 9, "replay_trace_id": f"replay-{session_id or 9}-{source_trace_id}"}

        def list_source_events(self, trace_id):
            return [{"event_time": 1, "payload": {"event_type": "news", "score": 0.8}, "symbol": "BTCUSDT", "exchange_code": "binance"}]

        def post_replay_event(self, payload):
            return None

        def update_replay_session(self, payload):
            return None

    class FakeRuntimeRunner:
        def run_once(self, **kwargs):
            return {"execution_result": {"status": "filled", "order_status": "FILLED"}}

    runner = TradeReplayRunner(replay_client=FakeReplayClient(), runtime_runner=FakeRuntimeRunner())

    first = runner.run_trace("source-trace-1", session_id=9)
    second = runner.run_trace("source-trace-1", session_id=9)

    assert first["replay_trace_id"] == second["replay_trace_id"]
