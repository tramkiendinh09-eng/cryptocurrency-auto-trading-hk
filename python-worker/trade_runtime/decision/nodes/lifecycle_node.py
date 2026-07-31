from __future__ import annotations

from trade_runtime.decision.state import DecisionState
from trade_runtime.memory.trade_lifecycle import apply_trade_lifecycle_status, process_trade_lifecycle


def lifecycle_node(state: DecisionState) -> DecisionState:
    lifecycle_status = process_trade_lifecycle(
        state=dict(state),
        lifecycle_manager=state.get("lifecycle_manager"),
        account_context=state.get("runtime_account_context"),
    )
    return apply_trade_lifecycle_status(dict(state), lifecycle_status)
