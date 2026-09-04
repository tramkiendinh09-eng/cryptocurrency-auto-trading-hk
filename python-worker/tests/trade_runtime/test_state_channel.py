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


def test_holding_minutes_survives_mixed_timezone_awareness():
    """entry_time 从库里读回来是朴素的 +08:00 字符串，exit_time 是 aware UTC。

    原实现直接相减，抛 TypeError 后被 `except Exception` 吞掉，于是每一笔平仓的
    持仓时长都记成 0——线上那笔实际持有 211 分钟的 SOL 空单，库里就是 0。
    """
    from datetime import datetime, timezone

    from trade_runtime.memory.trade_lifecycle import _holding_minutes

    aware_exit = datetime.fromisoformat("2026-09-03 19:29:59+08:00")
    assert _holding_minutes("2026-09-03 15:58:12", aware_exit) == 211
    # 两边都朴素时也要算对
    assert _holding_minutes("2026-09-04 03:06:09", datetime.fromisoformat("2026-09-04 06:34:05")) == 207
    # 朴素时间按 +08:00 补齐而不是 UTC，否则会平白差出 8 小时
    assert _holding_minutes("2026-09-03 19:00:00", datetime.fromisoformat("2026-09-03 20:00:00+08:00")) == 60
    assert _holding_minutes(None, datetime.now(timezone.utc)) == 0
    assert _holding_minutes("not-a-date", datetime.now(timezone.utc)) == 0


# ----------------------------------------------------------------------
# watch 级 Wyckoff 信号不该占用 LLM 预算
# ----------------------------------------------------------------------


def test_watch_signals_do_not_consume_llm_budget_by_default():
    """30 天历史上量过（calibration/readiness_edge.py，209 分钟持仓）：

        ready   n=163   均 +0.3904%   t=3.11  显著为正   扣费后 +0.3104%
        watch   n=1773  均 +0.0092%   t=0.25  与 0 无异   扣费后 -0.0708% 转负

    两组差异 t=2.92 显著。watch : ready = 10.9 : 1，按数量分配预算 watch 会
    拿走约 92%，把唯一被证明有优势的信号挤出去。
    """
    from trade_runtime.trigger_policy import _wyckoff_dispatch_mode

    assert _wyckoff_dispatch_mode({"trade_readiness": "ready"}, {}) == "LLM_ALLOWED"
    assert _wyckoff_dispatch_mode({"trade_readiness": "watch"}, {}) == "RULE_ONLY"


def test_watch_dispatch_can_be_restored_by_config():
    """旧行为留一个开关，不用改代码就能退回。"""
    from trade_runtime.trigger_policy import _wyckoff_dispatch_mode

    on = {"wyckoffWatchDispatchesLlm": True}
    assert _wyckoff_dispatch_mode({"trade_readiness": "watch"}, on) == "LLM_ALLOWED"
    assert _wyckoff_dispatch_mode({"trade_readiness": "watch"}, {"wyckoffWatchDispatchesLlm": "true"}) == "LLM_ALLOWED"
    # 蛇形键同样认
    assert _wyckoff_dispatch_mode({"trade_readiness": "watch"}, {"wyckoff_watch_dispatches_llm": True}) == "LLM_ALLOWED"


def test_unknown_readiness_still_dispatches():
    """ready 之外只降级 watch，别把其它取值一起误伤。"""
    from trade_runtime.trigger_policy import _wyckoff_dispatch_mode

    assert _wyckoff_dispatch_mode({"trade_readiness": "confirmed"}, {}) == "LLM_ALLOWED"
    assert _wyckoff_dispatch_mode({}, {}) == "LLM_ALLOWED"
