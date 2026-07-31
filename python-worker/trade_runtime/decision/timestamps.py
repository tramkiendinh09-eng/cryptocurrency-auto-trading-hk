from __future__ import annotations

from datetime import datetime, timezone

from trade_runtime.decision.state import DecisionState


def _default_timestamp_supplier() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def stamp_state_timestamp(state: DecisionState, field_name: str) -> None:
    supplier = state.get("timestamp_supplier")
    timestamp = supplier() if callable(supplier) else _default_timestamp_supplier()
    state[field_name] = timestamp
