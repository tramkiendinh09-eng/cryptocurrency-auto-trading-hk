from __future__ import annotations

from trade_runtime.decision.state import DecisionState
from trade_runtime.memory.retriever import retrieve_memory


def retrieve_memory_node(state: DecisionState) -> DecisionState:
    return retrieve_memory(dict(state))
