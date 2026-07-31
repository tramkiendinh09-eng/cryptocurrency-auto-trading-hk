from trade_runtime.decision.state import DecisionState
from trade_runtime.decision.timestamps import stamp_state_timestamp
from trade_runtime.trigger_policy import classify_event_strength_from_policy


def classify_event_strength(state: DecisionState) -> DecisionState:
    feature_snapshot = state.get("feature_snapshot", {})
    event_strength = classify_event_strength_from_policy(
        event_bundle=state.get("event_bundle"),
        feature_snapshot=feature_snapshot,
        runtime_config=state.get("runtime_config"),
        strategy_context=state.get("strategy_context"),
    )
    if isinstance(feature_snapshot, dict):
        feature_snapshot["event_strength"] = event_strength
        state["feature_snapshot"] = feature_snapshot
    state["event_strength"] = event_strength
    stamp_state_timestamp(state, "classifiedAt")
    return state

