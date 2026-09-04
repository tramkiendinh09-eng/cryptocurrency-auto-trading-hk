"""LangGraph 状态通道会静默丢弃 DecisionState 里没声明的键。

这条守卫是被一整条断掉的复盘链路逼出来的：entry_trace_id 没声明，于是
盯市快照读不到它、退回当前 trace_id，把 position_snapshot.entry_trace_id
一次次覆盖；平仓时按它去找生命周期记录必然 lifecycle_not_found，上线以来
没有任何一笔交易被记成完整平仓轮次。

丢键不报错也不告警，只有靠测试守住。新增跨节点传递的状态键时，同时在
DecisionState 里声明，并把键名加进下面这张表。
"""
from __future__ import annotations

import pytest
from langgraph.graph import END, StateGraph

from trade_runtime.decision.state import DecisionState

# 这些键由 runner 注入或由某个节点写入，再被另一个节点读取。
CROSS_NODE_KEYS = [
    "entry_trace_id",
    "position_risk_result",
    "supervisor_exit_escalation",
    "recent_supervisor_decisions",
    "supervisor_policy",
    "last_order",
    "runtime_account_context",
    "current_position_side",
    "runtime_config",
]


@pytest.mark.parametrize("key", CROSS_NODE_KEYS)
def test_key_is_declared_on_the_state_channel(key):
    assert key in DecisionState.__annotations__, (
        f"{key} 未在 DecisionState 声明，LangGraph 会在图里把它丢掉"
    )


def _roundtrip(payload: dict) -> dict:
    seen: dict = {}

    def probe(state):
        seen.update({key: state.get(key) for key in payload})
        return state

    graph = StateGraph(DecisionState)
    graph.add_node("probe", probe)
    graph.set_entry_point("probe")
    graph.add_edge("probe", END)
    graph.compile().invoke(payload)
    return seen


def test_declared_keys_survive_the_graph():
    payload = {
        "trace_id": "t-1",
        "entry_trace_id": "ENTRY-XYZ",
        "position_risk_result": {"severity": "close"},
        "supervisor_policy": {"enabledWhen": "RULE_ONLY"},
        "current_position_side": "long",
    }
    seen = _roundtrip(payload)
    assert seen["entry_trace_id"] == "ENTRY-XYZ"
    assert seen["position_risk_result"] == {"severity": "close"}
    assert seen["supervisor_policy"] == {"enabledWhen": "RULE_ONLY"}
    assert seen["current_position_side"] == "long"


def test_an_undeclared_key_really_is_dropped():
    """反向确认这条守卫不是空话：没声明的键确实会消失。"""
    seen = _roundtrip({"trace_id": "t-2", "definitely_not_declared_key": "gone"})
    assert "definitely_not_declared_key" not in DecisionState.__annotations__
    assert seen["definitely_not_declared_key"] is None
