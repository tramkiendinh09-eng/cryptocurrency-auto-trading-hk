"""执行状态的共同语义。

一次决策产生的 execution_result 会被多处消费：要不要写持仓快照、要不要
开一段持仓生命周期、要不要记一笔成交。这些问题的答案必须一致，所以
"这次执行到底有没有改变仓位"只应该有一处定义。

此前它散在各处：execution_node 有一份排除列表，trade_lifecycle 干脆
不判断——只看模型说了什么动作。于是被交易所过滤器拒掉的两笔 ETH 单
（下单额低于该标的最小名义金额）留下了两条永不关闭的持仓生命周期，
记录着两笔从未存在过的仓位。
"""

from __future__ import annotations

from typing import Any

#: 这些状态下订单没有（或还没有）改变仓位。
#: "pending"/"submitted" 是还没有结果，其余是明确没成交。
NON_FILLING_EXECUTION_STATUSES = frozenset(
    {
        "pending",
        "submitted",
        "failed",
        "blocked",
        "skipped",
        "canceled",
        "expired",
    }
)


def execution_status_of(execution_result: Any) -> str:
    """取归一化后的执行状态；拿不到时返回空串。"""
    if not isinstance(execution_result, dict):
        return ""
    return str(execution_result.get("status") or "").strip().lower()


def execution_moved_position(execution_result: Any) -> bool:
    """这次执行是否真的改变了仓位。

    缺省为 True：状态未知时按"动过"处理，与历史行为一致——漏记一次仓位
    变化，比凭空记一次不存在的仓位更难发现。调用方若还要求成交数量为正，
    需自行再判一次。
    """
    return execution_status_of(execution_result) not in NON_FILLING_EXECUTION_STATUSES
