from trade_runtime.replay_runner import TradeReplayRunner


def test_replay_runner_replays_trace_in_forced_shadow_mode():
    captured = {"session_payloads": [], "event_payloads": [], "runner_call": None}

    class StubReplayClient:
        def get_trace_source(self, trace_id):
            captured["source_trace_id"] = trace_id
            return {
                "traceId": trace_id,
                "symbol": "BTCUSDT",
                "exchangeCode": "binance",
                "eventBundle": [
                    {"event_type": "news", "headline": "ETF inflow", "score": 0.91},
                    {"event_type": "social", "score": 0.65},
                    {"event_type": "onchain", "flow": "exchange_outflow"},
                ],
            }

        def create_replay_session(self, payload):
            captured["session_payloads"].append(payload)
            return {**payload, "id": 18}

        def post_replay_event(self, payload):
            captured["event_payloads"].append(payload)

    class StubRuntimeRunner:
        def run_once(self, **kwargs):
            captured["runner_call"] = kwargs
            return {
                "trace_id": kwargs["trace_id"],
                "mode": kwargs["mode_override"],
                "supervisor_decision": {"action": "OPEN_LONG"},
            }

    replay_runner = TradeReplayRunner(
        replay_client=StubReplayClient(),
        runtime_runner=StubRuntimeRunner(),
        replay_trace_id_supplier=lambda: "trace-replay-1",
    )

    result = replay_runner.run_trace("trace-source-1")

    assert captured["source_trace_id"] == "trace-source-1"
    assert captured["session_payloads"][0]["sourceTraceId"] == "trace-source-1"
    assert captured["session_payloads"][0]["replayTraceId"] == "trace-replay-1"
    assert captured["session_payloads"][0]["mode"] == "shadow"
    assert captured["event_payloads"][0]["sessionId"] == 18
    assert captured["event_payloads"][0]["traceId"] == "trace-replay-1"
    assert captured["runner_call"]["trace_id"] == "trace-replay-1"
    assert captured["runner_call"]["mode_override"] == "shadow"
    assert captured["runner_call"]["feature_snapshot"]["news_score"] == 0.91
    assert captured["runner_call"]["feature_snapshot"]["social_score"] == 0.65
    assert captured["runner_call"]["feature_snapshot"]["onchain_flow_bias"] == 1.0
    assert result["session_id"] == 18
    assert result["replay_trace_id"] == "trace-replay-1"


def test_replay_runner_rejects_missing_event_bundle():
    class StubReplayClient:
        def get_trace_source(self, trace_id):
            return {
                "traceId": trace_id,
                "symbol": "BTCUSDT",
                "exchangeCode": "binance",
                "eventBundle": [],
            }

    replay_runner = TradeReplayRunner(
        replay_client=StubReplayClient(),
        runtime_runner=object(),
        replay_trace_id_supplier=lambda: "trace-replay-2",
    )

    try:
        replay_runner.run_trace("trace-source-empty")
        raised = False
    except ValueError as exc:
        raised = True
        assert "event bundle" in str(exc).lower()

    assert raised is True


def test_replay_runner_requests_trigger_guard_bypass_for_explicit_replay():
    captured = {"runner_call": None}

    class StubReplayClient:
        def get_trace_source(self, trace_id):
            return {
                "traceId": trace_id,
                "symbol": "BTCUSDT",
                "exchangeCode": "binance",
                "eventBundle": [
                    {"event_type": "market_tick", "symbol": "BTCUSDT", "price": 65000.0},
                ],
            }

        def create_replay_session(self, payload):
            return {**payload, "id": 22}

        def post_replay_event(self, payload):
            return None

    class StubRuntimeRunner:
        def run_once(self, **kwargs):
            captured["runner_call"] = kwargs
            return {
                "trace_id": kwargs["trace_id"],
                "dispatch_mode": "LLM_ALLOWED",
            }

    replay_runner = TradeReplayRunner(
        replay_client=StubReplayClient(),
        runtime_runner=StubRuntimeRunner(),
        replay_trace_id_supplier=lambda: "trace-replay-bypass-1",
    )

    replay_runner.run_trace("trace-source-bypass-1")

    assert captured["runner_call"]["mode_override"] == "shadow"
    assert captured["runner_call"]["bypass_trigger_guards"] is True
