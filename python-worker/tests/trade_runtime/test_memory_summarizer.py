from trade_runtime.memory.outcome import calculate_outcome_metrics
from trade_runtime.memory.summarizer import should_store_memory_candidate


def test_calculate_outcome_metrics_for_long_hold():
    metrics = calculate_outcome_metrics(
        entry_price=100.0,
        side="long",
        future_prices=[101.0, 99.0, 103.0],
        realized_pnl=20.0,
    )

    assert metrics["final_move_pct"] == 3.0
    assert metrics["mfe_pct"] == 3.0
    assert metrics["mae_pct"] == -1.0
    assert metrics["realized_pnl"] == 20.0


def test_should_store_memory_candidate_rejects_low_evidence():
    candidate = {"lesson_text": "追多一定赚钱", "confidence": 0.9, "evidence_count": 0, "quality_score": 0.9}

    assert should_store_memory_candidate(candidate) is False


def test_should_store_memory_candidate_accepts_quality_with_evidence():
    candidate = {"lesson_text": "强新闻需量价确认", "confidence": 0.7, "evidence_count": 3, "quality_score": 0.65}

    assert should_store_memory_candidate(candidate) is True
