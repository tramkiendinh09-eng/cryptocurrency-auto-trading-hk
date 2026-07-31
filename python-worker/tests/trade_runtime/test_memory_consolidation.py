from datetime import datetime, timedelta, timezone
from pathlib import Path

from trade_runtime.memory.consolidation import LongTermMemoryConsolidationJob


_REPO_ROOT = Path(__file__).resolve().parents[3]


class FakeHistoryClient:
    def __init__(self, runs):
        self.runs = runs

    def list_decision_runs(self):
        return list(self.runs)


class FakeLifecycleClient:
    def __init__(self, rows):
        self.rows = rows
        self.updates = []

    def list_closed_lifecycles(self, limit=20):
        return list(self.rows[:limit])

    def update_lifecycle(self, trace_id, updates):
        payload = {"trace_id": trace_id, **dict(updates)}
        self.updates.append(payload)
        return payload


class FakeModelClient:
    def __init__(self):
        self.calls = []

    def call_model(self, *, model_id, prompt):
        self.calls.append(model_id)
        return {
            "content": '{"should_store":true,"agent_code":"supervisor_agent","memory_type":"risk_lesson","lesson_text":"Validated decisions should wait for enough evidence before adding risk.","event_tags":["risk_control"],"confidence":0.7,"quality_score":0.7,"evidence_count":3}'
        }


def test_closed_lifecycle_retry_query_includes_llm_rejected_status():
    mapper_path = (
        _REPO_ROOT
        / "ruoyi-dca"
        / "src"
        / "main"
        / "resources"
        / "mapper"
        / "dca"
        / "memory"
        / "TradeLifecycleMapper.xml"
    )
    mapper_xml = mapper_path.read_text(encoding="utf-8")
    select_start = mapper_xml.index('<select id="selectClosedLifecycles"')
    select_end = mapper_xml.index("</select>", select_start)
    select_sql = mapper_xml[select_start:select_end]

    assert "memory_status = 'rejected'" in select_sql


class FakeMemoryStore:
    def __init__(self):
        self.created = []

    def create_memory(self, memory):
        self.created.append(dict(memory))
        return {"id": 1, **memory}


def test_memory_consolidation_job_summarizes_mature_decision_once():
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    store = FakeMemoryStore()
    job = LongTermMemoryConsolidationJob(
        decision_history_client=FakeHistoryClient(
            [
                {
                    "traceId": "trace-1",
                    "symbol": "BTCUSDT",
                    "action": "OPEN_LONG",
                    "createdAt": (now - timedelta(hours=3)).isoformat(),
                    "featureSnapshot": {"snapshot": {"shortTermMemory": {"market": {"items": [{"price": 100.0}]}}}},
                }
            ]
        ),
        model_client=FakeModelClient(),
        memory_store=store,
        current_price_supplier=lambda symbol: 103.0,
        now_supplier=lambda: now,
        window_seconds=7200,
    )

    first = job.run_once()
    second = job.run_once()

    assert first["stored_count"] == 1
    assert second["stored_count"] == 0
    assert store.created[0]["source_trace_id"] == "trace-1"
    assert store.created[0]["outcome_json"]["final_move_pct"] == 3.0


def test_memory_consolidation_job_skips_immature_or_unpriced_decisions():
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    store = FakeMemoryStore()
    job = LongTermMemoryConsolidationJob(
        decision_history_client=FakeHistoryClient(
            [
                {
                    "traceId": "trace-young",
                    "symbol": "BTCUSDT",
                    "action": "OPEN_LONG",
                    "createdAt": (now - timedelta(minutes=30)).isoformat(),
                    "featureSnapshot": {"snapshot": {"price": 100.0}},
                },
                {
                    "traceId": "trace-no-price",
                    "symbol": "BTCUSDT",
                    "action": "OPEN_LONG",
                    "createdAt": (now - timedelta(hours=3)).isoformat(),
                    "featureSnapshot": {"snapshot": {}},
                },
            ]
        ),
        model_client=FakeModelClient(),
        memory_store=store,
        current_price_supplier=lambda symbol: 103.0,
        now_supplier=lambda: now,
        window_seconds=7200,
    )

    result = job.run_once()

    assert result["stored_count"] == 0
    assert result["skipped_count"] == 2
    assert store.created == []


def test_memory_consolidation_job_uses_resolved_model_for_closed_lifecycle():
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    store = FakeMemoryStore()
    model_client = FakeModelClient()
    lifecycle_client = FakeLifecycleClient(
        [
            {
                "traceId": "trace-lifecycle-1",
                "symbol": "ETHUSDT",
                "exchangeCode": "okx",
                "side": "long",
                "entryPrice": 100.0,
                "exitPrice": 105.0,
                "realizedPnlPct": 5.0,
                "holdingMinutes": 90,
                "entryReason": "breakout",
                "entryConditionsJson": {"price_change_pct": 2.5},
                "agentViewsJson": {"market_view": {"bias": "bullish"}},
                "supervisorDecisionJson": {"action": "OPEN_LONG"},
                "priceTrajectoryJson": [],
                "exitReason": "target_hit",
            }
        ]
    )
    job = LongTermMemoryConsolidationJob(
        decision_history_client=FakeHistoryClient([]),
        lifecycle_client=lifecycle_client,
        model_client=model_client,
        memory_store=store,
        current_price_supplier=lambda symbol: 105.0,
        now_supplier=lambda: now,
        model_id=88,
        model_id_resolver=lambda payload: 22 if payload.get("symbol") == "ETHUSDT" else None,
    )

    result = job.run_once()

    assert result["stored_count"] == 1
    assert model_client.calls == [22]
    assert lifecycle_client.updates == [
        {
            "trace_id": "trace-lifecycle-1",
            "memory_generated": True,
            "lesson_text": "Validated decisions should wait for enough evidence before adding risk.",
            "memory_status": "stored",
            "memory_reason": "",
        }
    ]


def test_memory_consolidation_job_marks_empty_store_response_as_failure_and_retries_later():
    now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    model_client = FakeModelClient()
    lifecycle_client = FakeLifecycleClient(
        [
            {
                "traceId": "trace-lifecycle-noop-store",
                "symbol": "ETHUSDT",
                "exchangeCode": "okx",
                "side": "long",
                "entryPrice": 100.0,
                "exitPrice": 105.0,
                "realizedPnlPct": 5.0,
                "holdingMinutes": 90,
                "entryReason": "breakout",
                "entryConditionsJson": {"price_change_pct": 2.5},
                "agentViewsJson": {"market_view": {"bias": "bullish"}},
                "supervisorDecisionJson": {"action": "OPEN_LONG"},
                "priceTrajectoryJson": [],
                "exitReason": "target_hit",
            }
        ]
    )

    class NoopMemoryStore:
        def create_memory(self, memory):
            return {}

    job = LongTermMemoryConsolidationJob(
        decision_history_client=FakeHistoryClient([]),
        lifecycle_client=lifecycle_client,
        model_client=model_client,
        memory_store=NoopMemoryStore(),
        current_price_supplier=lambda symbol: 105.0,
        now_supplier=lambda: now,
        model_id=88,
    )

    first = job.run_once()
    second = job.run_once()

    assert first["stored_count"] == 0
    assert first["failed_count"] == 1
    assert second["failed_count"] == 1
    assert model_client.calls == [88, 88]
    assert lifecycle_client.updates == [
        {
            "trace_id": "trace-lifecycle-noop-store",
            "memory_generated": False,
            "lesson_text": "Validated decisions should wait for enough evidence before adding risk.",
            "memory_status": "failed",
            "memory_reason": "memory_store_create_failed",
        },
        {
            "trace_id": "trace-lifecycle-noop-store",
            "memory_generated": False,
            "lesson_text": "Validated decisions should wait for enough evidence before adding risk.",
            "memory_status": "failed",
            "memory_reason": "memory_store_create_failed",
        },
    ]
