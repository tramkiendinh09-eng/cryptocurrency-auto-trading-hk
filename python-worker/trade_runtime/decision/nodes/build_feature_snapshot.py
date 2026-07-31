from __future__ import annotations

from trade_runtime.decision.state import DecisionState
from trade_runtime.runtime_inputs import build_feature_snapshot_from_events
from trade_runtime.runtime_inputs import build_signal_window_states_from_events


def build_feature_snapshot_node(state: DecisionState) -> DecisionState:
    derived_snapshot = build_feature_snapshot_from_events(state.get("event_bundle"))
    derived_signal_window_states = build_signal_window_states_from_events(state.get("event_bundle"))
    current_snapshot = state.get("feature_snapshot")
    if not isinstance(current_snapshot, dict):
        current_snapshot = {}
    feature_snapshot = dict(derived_snapshot)
    feature_snapshot.update({key: value for key, value in current_snapshot.items() if value not in (None, "")})
    state["feature_snapshot"] = feature_snapshot
    current_signal_window_states = state.get("signal_window_states")
    if isinstance(current_signal_window_states, list) and current_signal_window_states:
        state["signal_window_states"] = current_signal_window_states
    else:
        state["signal_window_states"] = derived_signal_window_states
    return state
