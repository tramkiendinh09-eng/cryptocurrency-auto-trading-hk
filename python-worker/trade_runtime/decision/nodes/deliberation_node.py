from trade_runtime.decision.deliberation import run_deliberation
from trade_runtime.decision.state import DecisionState


def deliberation_node(state: DecisionState) -> DecisionState:
    return run_deliberation(state)
