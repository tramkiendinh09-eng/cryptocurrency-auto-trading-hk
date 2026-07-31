import json

from trade_runtime.memory.outcome import calculate_outcome_metrics
from trade_runtime.memory.summarizer import create_memory_from_evaluated_decision
from trade_runtime.memory.long_term import HybridLongTermMemoryStore, HttpLongTermMemoryStore, McpLongTermMemoryStore
from trade_runtime.prompting.render_context_builder import build_prompt_long_term_memory


class DummyMcpResponse:
    def __init__(self, payload=None, *, headers=None, text=None):
        self.payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.text = text or ""

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def mcp_sse_response(payload, *, headers=None):
    response_headers = {"content-type": "text/event-stream"}
    response_headers.update(headers or {})
    return DummyMcpResponse(
        payload,
        headers=response_headers,
        text=f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n",
    )


def mcp_stdio_frame(payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


class FakeModelClient:
    def __init__(self, content):
        self.content = content
        self.prompts = []

    def call_model(self, *, model_id, prompt):
        self.prompts.append({"model_id": model_id, "prompt": prompt})
        return {"content": self.content}


class RecordingMemoryStore:
    def __init__(self):
        self.created = []

    def create_memory(self, memory):
        self.created.append(dict(memory))
        return {"id": 101, **memory}


class RecordingLifecycleClient:
    def __init__(self, lifecycle):
        self.lifecycle = dict(lifecycle)
        self.updates = []

    def get_lifecycle(self, trace_id):
        return dict(self.lifecycle) if trace_id == self.lifecycle.get("traceId") else None

    def update_lifecycle(self, trace_id, updates):
        payload = {"trace_id": trace_id, **dict(updates)}
        self.updates.append(payload)
        return payload


def test_create_memory_from_evaluated_decision_summarizes_with_model_before_store():
    model = FakeModelClient(
        json.dumps(
            {
                "should_store": True,
                "agent_code": "news_agent",
                "memory_type": "risk_lesson",
                "lesson_text": "Strong news needs volume confirmation before adding risk.",
                "event_tags": ["strong_news", "wyckoff_insufficient"],
                "market_regime": "news_driven_insufficient_market_history",
                "confidence": 0.72,
                "quality_score": 0.7,
                "evidence_count": 3,
            }
        )
    )
    store = RecordingMemoryStore()
    decision_payload = {
        "traceId": "trace-1",
        "symbol": "BTCUSDT",
        "action": "HOLD",
        "side": "long",
        "summaryReason": "held because market history was insufficient",
        "eventStrength": "strong",
    }
    outcome = {"window": "120m", "final_move_pct": 0.3, "mfe_pct": 0.8, "mae_pct": -0.5}

    result = create_memory_from_evaluated_decision(
        decision_payload=decision_payload,
        outcome_metrics=outcome,
        model_client=model,
        memory_store=store,
        model_id=6,
    )

    assert result["status"] == "stored"
    assert model.prompts[0]["model_id"] == 6
    assert "held because market history was insufficient" in model.prompts[0]["prompt"]
    assert store.created[0]["lesson_text"] == "Strong news needs volume confirmation before adding risk."
    assert store.created[0]["source_trace_id"] == "trace-1"
    assert store.created[0]["outcome_json"]["mae_pct"] == -0.5


def test_create_memory_from_evaluated_decision_rejects_unverified_candidate():
    model = FakeModelClient(
        json.dumps(
            {
                "should_store": True,
                "agent_code": "news_agent",
                "memory_type": "risk_lesson",
                "lesson_text": "Always buy strong news.",
                "event_tags": ["strong_news"],
                "confidence": 0.9,
                "quality_score": 0.9,
                "evidence_count": 0,
            }
        )
    )
    store = RecordingMemoryStore()

    result = create_memory_from_evaluated_decision(
        decision_payload={"traceId": "trace-2", "symbol": "BTCUSDT", "action": "OPEN_LONG"},
        outcome_metrics={"window": "120m", "final_move_pct": -1.0},
        model_client=model,
        memory_store=store,
    )

    assert result["status"] == "rejected"
    assert store.created == []


def test_create_memory_from_price_outcome_uses_post_decision_metrics():
    metrics = calculate_outcome_metrics(entry_price=100.0, side="short", future_prices=[99.0, 103.0], realized_pnl=-10.0)

    assert metrics["final_move_pct"] == -3.0
    assert metrics["mfe_pct"] == 1.0
    assert metrics["mae_pct"] == -3.0


def test_trade_lifecycle_manager_record_exit_uses_configured_model_and_persists_memory_status():
    from datetime import datetime, timezone

    from trade_runtime.memory.trade_lifecycle import TradeLifecycleManager

    now = datetime(2026, 5, 25, 2, 34, tzinfo=timezone.utc)
    model = FakeModelClient(
        json.dumps(
            {
                "should_store": True,
                "agent_code": "supervisor_agent",
                "memory_type": "lesson",
                "lesson_text": "Wait for candle confirmation before closing a short on transient squeeze.",
                "event_tags": ["short_squeeze", "risk_control"],
                "confidence": 0.76,
                "quality_score": 0.81,
                "evidence_count": 3,
            }
        )
    )
    store = RecordingMemoryStore()
    lifecycle_client = RecordingLifecycleClient(
        {
            "traceId": "trace-open-1",
            "symbol": "ETHUSDT",
            "exchangeCode": "okx",
            "side": "short",
            "entryPrice": 2200.0,
            "entryTime": "2026-05-25T01:34:00+00:00",
            "entryReason": "range_breakdown",
            "entryConditionsJson": {"price_change_pct": -0.9},
            "agentViewsJson": {"market_view": {"bias": "bearish"}},
            "supervisorDecisionJson": {"action": "OPEN_SHORT"},
            "priceTrajectoryJson": [],
            "maxFavorablePct": 1.2,
            "maxAdversePct": -0.4,
        }
    )
    manager = TradeLifecycleManager(
        lifecycle_client=lifecycle_client,
        memory_store=store,
        model_client=model,
        model_id=77,
        now_supplier=lambda: now,
    )

    result = manager.record_exit(
        trace_id="trace-open-1",
        exit_price=2180.0,
        exit_reason="take_profit",
        generate_memory=True,
    )

    assert model.prompts[0]["model_id"] == 77
    assert result["memory_status"] == "stored"
    assert result["memory"]["lesson_text"] == "Wait for candle confirmation before closing a short on transient squeeze."
    assert lifecycle_client.updates == [
        {
            "trace_id": "trace-open-1",
            "exit_price": 2180.0,
            "exit_time": now,
            "exit_reason": "take_profit",
            "realized_pnl_pct": 0.909091,
            "holding_minutes": 60,
        },
        {
            "trace_id": "trace-open-1",
            "memory_generated": True,
            "lesson_text": "Wait for candle confirmation before closing a short on transient squeeze.",
            "memory_status": "stored",
            "memory_reason": "",
        },
    ]


def test_http_memory_store_create_posts_agent_memory(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"id": 7}}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = HttpLongTermMemoryStore(base_url="http://localhost:8080", bearer_token="abc", timeout=3)

    result = store.create_memory(
        {
            "agent_code": "news_agent",
            "symbol": "BTCUSDT",
            "memory_type": "risk_lesson",
            "lesson_text": "Strong news needs confirmation.",
            "quality_score": 0.7,
            "confidence": 0.8,
        }
    )

    assert captured["url"] == "http://localhost:8080/dca/agent-memory"
    assert captured["json"]["agentCode"] == "news_agent"
    assert captured["json"]["lessonText"] == "Strong news needs confirmation."
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3
    assert result["id"] == 7


def test_http_memory_store_search_passes_tags_to_backend(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": []}

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.get", fake_get)
    store = HttpLongTermMemoryStore(base_url="http://localhost:8080", bearer_token="abc", timeout=3)

    result = store.search(
        agent_code="news_agent",
        symbol="BTCUSDT",
        tags=["strong_news", "breakout"],
        limit=2,
    )

    assert result == []
    assert captured["url"] == "http://localhost:8080/dca/agent-memory/list"
    assert captured["params"]["agentCode"] == "news_agent"
    assert captured["params"]["symbol"] == "BTCUSDT"
    assert captured["params"]["limit"] == 2
    assert captured["params"]["tags"] == ["strong_news", "breakout"]
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 3


def test_http_memory_store_search_preserves_lifecycle_outcome_for_prompt(monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {
                        "id": 7,
                        "agentCode": "supervisor_agent",
                        "symbol": "ETHUSDT",
                        "memoryType": "lesson",
                        "lessonText": "Wait for candle confirmation before closing a short on transient squeeze.",
                        "eventTagsJson": '["risk_control","short_squeeze"]',
                        "evidenceJson": '{"entry_reason":"OPEN_SHORT on breakdown"}',
                        "outcomeJson": '{"realized_pnl_pct":0.909091,"holding_minutes":60,"exit_reason":"take_profit"}',
                        "qualityScore": 0.81,
                        "confidence": 0.76,
                        "sourceTraceId": "trace-open-1",
                    }
                ]
            }

    def fake_get(url, params, headers, timeout):
        return DummyResponse()

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.get", fake_get)
    store = HttpLongTermMemoryStore(base_url="http://localhost:8080", bearer_token="abc", timeout=3)

    result = store.search(agent_code="supervisor_agent", symbol="ETHUSDT", tags=["risk_control"], limit=1)
    prompt_memory = build_prompt_long_term_memory(
        {
            "long_term_memory": {"status": "ready", "items": result, "selected_count": len(result)},
            "memory_usage": {"used_memory_ids": [7]},
        }
    )

    item = prompt_memory["experience_items"][0]
    assert item["outcome"]["realized_pnl_pct"] == 0.909091
    assert item["evidence"]["entry_reason"] == "OPEN_SHORT on breakdown"
    assert "realized_pnl_pct=0.909091" in item["experience_text"]


def test_http_memory_store_record_usage_includes_agent_code_from_search_results(monkeypatch):
    captured_posts = []

    class DummyGetResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {
                        "id": 9,
                        "agentCode": "news_agent",
                        "symbol": "BTCUSDT",
                        "lessonText": "Strong news needs confirmation.",
                    }
                ]
            }

    class DummyPostResponse:
        def raise_for_status(self):
            return None

    def fake_get(url, params, headers, timeout):
        return DummyGetResponse()

    def fake_post(url, json, headers, timeout):
        captured_posts.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return DummyPostResponse()

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.get", fake_get)
    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = HttpLongTermMemoryStore(base_url="http://localhost:8080", bearer_token="abc", timeout=3)

    store.search(agent_code="news_agent", symbol="BTCUSDT", tags=["strong_news"], limit=1)
    store.record_usage(trace_id="trace-1", symbol="BTCUSDT", memory_ids=[9])

    assert captured_posts == [
        {
            "url": "http://localhost:8080/dca/agent-memory/usage",
            "json": {
                "traceId": "trace-1",
                "symbol": "BTCUSDT",
                "memoryId": 9,
                "agentCode": "news_agent",
                "usageContextJson": "{}",
            },
            "headers": {"Accept": "application/json", "Authorization": "Bearer abc"},
            "timeout": 3,
        }
    ]


def test_http_memory_store_create_memory_accepts_ajax_row_count_response(monkeypatch):
    captured_posts = []

    class DummyPostResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 200, "msg": "????", "data": 1}

    def fake_post(url, json, headers, timeout):
        captured_posts.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return DummyPostResponse()

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = HttpLongTermMemoryStore(base_url="http://localhost:8080", bearer_token="abc", timeout=3)
    memory = {
        "memory_key": "supervisor_agent:ETHUSDT:trace-open-1:trade_lifecycle",
        "agent_code": "supervisor_agent",
        "symbol": "ETHUSDT",
        "memory_type": "trade_lifecycle",
        "direction": "long",
        "action": "OPEN_LONG",
        "lesson_text": "Exit faster when breakdown confirms.",
        "quality_score": 0.8,
        "confidence": 0.75,
        "source_trace_id": "trace-open-1",
    }

    created = store.create_memory(memory)

    assert created["memory_key"] == memory["memory_key"]
    assert created["source_trace_id"] == "trace-open-1"
    assert created["id"] is None
    assert captured_posts[0]["url"] == "http://localhost:8080/dca/agent-memory"




def test_mcp_memory_store_stdio_calls_official_memos_mcp(monkeypatch):
    calls = []
    tool_response = {
        "jsonrpc": "2.0",
        "id": "trade-memory-search_memories",
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "text_mem": [
                                {
                                    "cube_id": "MODELSCOPE",
                                    "memories": [
                                        {
                                            "id": "official-1",
                                            "memory": "Avoid revenge trades after two failed breakouts.",
                                            "score": 0.88,
                                        }
                                    ],
                                }
                            ]
                        }
                    ),
                }
            ],
            "isError": False,
        },
    }

    class CompletedProcess:
        returncode = 0
        stdout = mcp_stdio_frame({"jsonrpc": "2.0", "id": "trade-memory-initialize", "result": {}}) + mcp_stdio_frame(tool_response)
        stderr = b""

    def fake_run(command, input=None, stdout=None, stderr=None, env=None, timeout=None, check=None):
        calls.append({"command": command, "input": input, "env": env, "timeout": timeout, "check": check})
        return CompletedProcess()

    monkeypatch.setattr("trade_runtime.memory.long_term.subprocess.run", fake_run)
    store = McpLongTermMemoryStore(
        transport="stdio",
        command="npx",
        args=["-y", "@memtensor/memos-api-mcp@latest"],
        channel="MODELSCOPE",
        env={"MEMOS_API_KEY": "official-key", "MEMOS_USER_ID": "trade-runtime", "MEMOS_CHANNEL": "MODELSCOPE"},
    )

    rows = store.search(agent_code="supervisor_agent", symbol="BTCUSDT", tags=["breakout"], limit=2)

    request_messages = store._parse_stdio_messages(calls[0]["input"])
    assert calls[0]["command"] == ["npx", "-y", "@memtensor/memos-api-mcp@latest"]
    assert calls[0]["timeout"] == 20
    assert calls[0]["env"]["MEMOS_API_KEY"] == "official-key"
    assert [message.get("method") for message in request_messages] == [
        "initialize",
        "notifications/initialized",
        "tools/call",
    ]
    assert request_messages[2]["params"]["name"] == "search_memories"
    assert request_messages[2]["params"]["arguments"]["cube_ids"] == "MODELSCOPE"
    assert rows[0]["id"] == "official-1"
    assert rows[0]["lesson_text"] == "Avoid revenge trades after two failed breakouts."
    assert rows[0]["quality_score"] == 0.88


def test_mcp_memory_store_search_calls_configured_tool_with_20_second_default_timeout(monkeypatch):
    calls = []
    tool_payload = {
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "memories": [
                                {
                                    "id": "memos-1",
                                    "memory": "Avoid adding after weak rebound volume.",
                                    "metadata": {
                                        "agent_code": "supervisor_agent",
                                        "symbol": "BTCUSDT",
                                        "event_tags": ["weak_rebound"],
                                    },
                                    "score": 0.83,
                                }
                            ]
                        }
                    ),
                }
            ]
        }
    }

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        method = (json or {}).get("method")
        if method == "initialize":
            return mcp_sse_response({"result": {"protocolVersion": "2025-03-26"}}, headers={"mcp-session-id": "session-1"})
        if method == "notifications/initialized":
            return DummyMcpResponse(headers={"content-type": "application/json"})
        return mcp_sse_response(tool_payload, headers={"mcp-session-id": "session-1"})

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = McpLongTermMemoryStore(
        mcp_url="http://127.0.0.1:8002/mcp",
        user_id="trade-runtime",
        channel="production",
    )

    rows = store.search(agent_code="supervisor_agent", symbol="BTCUSDT", tags=["weak_rebound"], limit=3)

    assert calls[0]["json"]["method"] == "initialize"
    assert calls[0]["timeout"] == 20
    assert "text/event-stream" in calls[0]["headers"]["Accept"]
    assert "Mcp-Session-Id" not in calls[0]["headers"]
    assert calls[1]["json"]["method"] == "notifications/initialized"
    assert calls[1]["headers"]["Mcp-Session-Id"] == "session-1"
    assert calls[2]["url"] == "http://127.0.0.1:8002/mcp"
    assert calls[2]["timeout"] == 20
    assert calls[2]["headers"]["Mcp-Session-Id"] == "session-1"
    assert calls[2]["json"]["method"] == "tools/call"
    assert calls[2]["json"]["params"]["name"] == "search_memories"
    assert calls[2]["json"]["params"]["arguments"]["user_id"] == "trade-runtime"
    assert calls[2]["json"]["params"]["arguments"]["cube_ids"] == "production"
    assert rows[0]["id"] == "memos-1"
    assert rows[0]["lesson_text"] == "Avoid adding after weak rebound volume."
    assert rows[0]["quality_score"] == 0.83



def test_mcp_memory_store_create_memory_sends_sanitized_trade_experience(monkeypatch):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"json": json, "headers": headers})
        method = (json or {}).get("method")
        if method == "initialize":
            return mcp_sse_response({"result": {"protocolVersion": "2025-03-26"}}, headers={"mcp-session-id": "session-1"})
        if method == "notifications/initialized":
            return DummyMcpResponse(headers={"content-type": "application/json"})
        return mcp_sse_response({"result": {"memory_id": "memos-created-1"}}, headers={"mcp-session-id": "session-1"})

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = McpLongTermMemoryStore(mcp_url="http://127.0.0.1:8002/mcp")

    created = store.create_memory(
        {
            "memory_key": "supervisor_agent:BTCUSDT:trace-1:lesson",
            "agent_code": "supervisor_agent",
            "symbol": "BTCUSDT",
            "event_tags": ["failed_breakout"],
            "lesson_text": "Wait for reclaim confirmation before increasing long risk.",
            "evidence_json": {"signal": "weak close"},
            "outcome_json": {"realized_pnl_pct": -0.8},
            "quality_score": 0.74,
            "confidence": 0.69,
            "source_trace_id": "trace-1",
            "api_key": "must-not-leak",
        }
    )

    tool_call = calls[2]["json"]
    arguments = tool_call["params"]["arguments"]
    assert calls[1]["headers"]["Mcp-Session-Id"] == "session-1"
    assert calls[2]["headers"]["Mcp-Session-Id"] == "session-1"
    assert tool_call["params"]["name"] == "add_memory"
    assert "must-not-leak" not in json.dumps(arguments, ensure_ascii=False)
    assert "Wait for reclaim confirmation" in arguments["memory_content"]
    assert arguments["cube_id"] == "production"
    assert created["id"] == "memos-created-1"
    assert created["lesson_text"] == "Wait for reclaim confirmation before increasing long risk."


def test_hybrid_memory_store_keeps_local_primary_and_uses_mcp_as_best_effort():
    class PrimaryStore:
        def __init__(self):
            self.created = []
            self.usages = []

        def search(self, *, agent_code, symbol, tags, limit):
            return [
                {
                    "id": 1,
                    "agent_code": agent_code,
                    "symbol": symbol,
                    "lesson_text": "Local lesson",
                    "quality_score": 0.6,
                }
            ]

        def create_memory(self, memory):
            self.created.append(memory)
            return {"id": 1, **memory}

        def record_usage(self, *, trace_id, symbol, memory_ids):
            self.usages.append({"trace_id": trace_id, "symbol": symbol, "memory_ids": memory_ids})

    class SecondaryStore:
        def __init__(self):
            self.created = []

        def search(self, *, agent_code, symbol, tags, limit):
            return [
                {
                    "id": "mcp-1",
                    "agent_code": agent_code,
                    "symbol": symbol,
                    "lesson_text": "MCP semantic lesson",
                    "quality_score": 0.9,
                }
            ]

        def create_memory(self, memory):
            self.created.append(memory)
            raise RuntimeError("mcp unavailable")

        def record_usage(self, *, trace_id, symbol, memory_ids):
            raise RuntimeError("mcp unavailable")

    primary = PrimaryStore()
    secondary = SecondaryStore()
    store = HybridLongTermMemoryStore(primary=primary, secondary=secondary)

    created = store.create_memory({"memory_key": "k1", "lesson_text": "Persisted locally first"})
    rows = store.search(agent_code="supervisor_agent", symbol="BTCUSDT", tags=[], limit=5)
    store.record_usage(trace_id="trace-2", symbol="BTCUSDT", memory_ids=[1, "mcp-1"])

    assert created["id"] == 1
    assert primary.created[0]["memory_key"] == "k1"
    assert secondary.created[0]["memory_key"] == "k1"
    assert [row["lesson_text"] for row in rows] == ["MCP semantic lesson", "Local lesson"]
    assert primary.usages[0]["memory_ids"] == [1, "mcp-1"]




def test_mcp_memory_store_search_reads_memos_grouped_search_payload(monkeypatch):
    grouped_payload_text = json.dumps(
        {
            "text_mem": [
                {
                    "cube_id": "production",
                    "memories": [
                        {
                            "id": "grouped-1",
                            "memory": "Reduce risk after failed breakout confirmation.",
                            "metadata": {"symbol": "BTCUSDT"},
                            "score": 0.91,
                        }
                    ],
                }
            ],
            "pref_mem": [{"cube_id": "production", "memories": [], "total_nodes": 0}],
        }
    )

    def fake_post(url, json=None, headers=None, timeout=None):
        method = (json or {}).get("method")
        if method == "initialize":
            return mcp_sse_response({"result": {"protocolVersion": "2025-03-26"}}, headers={"mcp-session-id": "session-1"})
        if method == "notifications/initialized":
            return DummyMcpResponse(headers={"content-type": "application/json"})
        return mcp_sse_response(
            {
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": grouped_payload_text,
                        }
                    ]
                }
            },
            headers={"mcp-session-id": "session-1"},
        )

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = McpLongTermMemoryStore(mcp_url="http://127.0.0.1:8002/mcp")

    rows = store.search(agent_code="supervisor_agent", symbol="BTCUSDT", tags=[], limit=3)

    assert rows[0]["id"] == "grouped-1"
    assert rows[0]["lesson_text"] == "Reduce risk after failed breakout confirmation."
    assert rows[0]["quality_score"] == 0.91


def test_mcp_memory_store_search_ignores_tool_error_text(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        method = (json or {}).get("method")
        if method == "initialize":
            return mcp_sse_response({"result": {"protocolVersion": "2025-03-26"}}, headers={"mcp-session-id": "session-1"})
        if method == "notifications/initialized":
            return DummyMcpResponse(headers={"content-type": "application/json"})
        return mcp_sse_response(
            {"result": {"content": [{"type": "text", "text": "Error: upstream memory unavailable"}]}},
            headers={"mcp-session-id": "session-1"},
        )

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = McpLongTermMemoryStore(mcp_url="http://127.0.0.1:8002/mcp")

    assert store.search(agent_code="supervisor_agent", symbol="BTCUSDT", tags=[], limit=3) == []



def test_mcp_memory_store_create_memory_rejects_tool_error_text(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        method = (json or {}).get("method")
        if method == "initialize":
            return mcp_sse_response({"result": {"protocolVersion": "2025-03-26"}}, headers={"mcp-session-id": "session-1"})
        if method == "notifications/initialized":
            return DummyMcpResponse(headers={"content-type": "application/json"})
        return mcp_sse_response(
            {"result": {"content": [{"type": "text", "text": "Error: failed to add memory"}]}},
            headers={"mcp-session-id": "session-1"},
        )

    monkeypatch.setattr("trade_runtime.memory.long_term.requests.post", fake_post)
    store = McpLongTermMemoryStore(mcp_url="http://127.0.0.1:8002/mcp")

    assert store.create_memory({"memory_key": "k1", "lesson_text": "Never store failed tool calls."}) == {}
