from __future__ import annotations

from uuid import uuid4

from trade_runtime.decision.state import DecisionState
from trade_runtime.decision.timestamps import stamp_state_timestamp
from trade_runtime.runtime_inputs import normalize_event_bundle, resolve_market_source_status


def _resolve_symbol(state: DecisionState) -> str:
    if state.get("symbol"):
        return str(state.get("symbol"))
    for event in normalize_event_bundle(state.get("event_bundle")):
        symbol = str(event.get("symbol", "")).strip()
        if symbol:
            return symbol
    return ""


def _resolve_exchange(state: DecisionState) -> str:
    if state.get("exchange"):
        return str(state.get("exchange")).strip().lower()
    for event in normalize_event_bundle(state.get("event_bundle")):
        exchange = str(event.get("exchange", "")).strip().lower()
        if exchange:
            return exchange
    return "binance"


def ingest_context_node(state: DecisionState) -> DecisionState:
    state["trace_id"] = str(state.get("trace_id") or uuid4().hex)
    state["event_bundle"] = normalize_event_bundle(state.get("event_bundle"))
    state["symbol"] = _resolve_symbol(state)
    state["exchange"] = _resolve_exchange(state)
    state["market_source_status"] = resolve_market_source_status(
        state.get("event_bundle"),
        default=str(state.get("market_source_status") or "ready").strip().lower() or "ready",
    )
    stamp_state_timestamp(state, "ingestedAt")
    return state
