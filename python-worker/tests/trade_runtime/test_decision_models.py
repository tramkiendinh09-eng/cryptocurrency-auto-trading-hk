from trade_runtime.decision.models import AgentView, SupervisorDecision


def test_supervisor_decision_requires_action_side_and_confidence():
    decision = SupervisorDecision(
        action="OPEN_LONG",
        side="long",
        confidence=82,
        size_hint=0.35,
    )
    assert decision.action == "OPEN_LONG"
    assert decision.side == "long"
    assert decision.confidence == 82
