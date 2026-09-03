"""下单规模与杠杆的统一口径。

抽成一处是因为同一个数字要在三个地方算出完全一样的结果：
风控判定（risk_guard_node）、实际下单（execution_node）、以及写给模型看的
可下区间（supervisor_agent）。任意两处算得不一样，都会表现成"风控放行了
但下不出去"或者"模型按区间给的值被拒"这类很难查的问题。

口径：
    size_hint  —— 动用多少比例的账户权益**作为保证金**
    敞口       —— 权益 × size_hint × 杠杆
    保证金     —— 权益 × size_hint（即敞口 / 杠杆）

杠杆此前只作为订单元数据发给交易所，不参与仓位计算，于是 100 USDT 的
账户敞口永远不超过 max_position_ratio × 100 = 30 USDT，配置里的
maxLeverage 形同虚设。合约本来就该用少量保证金撬动敞口，这里把它接回去。
"""

from __future__ import annotations

from typing import Any


#: 模型没给 leverage_hint 时用的倍数。
DEFAULT_LEVERAGE = 3.0

#: 硬上限。运行时配置里的 maxLeverage 可以更低，但不能更高——
#: 把这条写死在代码里，是为了让"配置写错一个零"不至于变成 100 倍杠杆。
LEVERAGE_HARD_CEILING = 10.0


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def leverage_ceiling(runtime_config: Any) -> float:
    """取本次允许的最高杠杆。

    配置里写了就用配置值，但一律夹在硬上限之内——把上限写死在代码里，
    是为了让"配置多打一个零"不至于变成 100 倍杠杆。

    配置读不到时退回 DEFAULT_LEVERAGE 而不是硬上限：杠杆太小的代价是
    一单被拒，太大的代价是爆仓，所以缺省必须往保守一侧倒。10 倍是明确
    设定出来的上限，不该由"没读到配置"这件事赋予。
    """
    ceiling = None
    if isinstance(runtime_config, dict):
        raw = (
            runtime_config.get("max_leverage")
            if runtime_config.get("max_leverage") is not None
            else runtime_config.get("maxLeverage")
        )
        ceiling = _optional_float(raw)
    if ceiling is None or ceiling <= 0:
        return DEFAULT_LEVERAGE
    return min(float(ceiling), LEVERAGE_HARD_CEILING)


def resolve_leverage(runtime_config: Any, decision: Any) -> float:
    """定出这一单实际使用的杠杆。

    模型给的 leverage_hint 只是建议：币安的杠杆是账户级状态，一个无界的
    建议不只是这一单下得不对，它会改掉该标的之后每一单的保证金模式。
    所以一律夹在 [1, ceiling] 内；没给或给了非法值时退回默认倍数。
    """
    raw = None
    if isinstance(decision, dict):
        raw = _optional_float(decision.get("leverage") or decision.get("leverage_hint"))
    ceiling = leverage_ceiling(runtime_config)
    if raw is None or raw <= 0:
        raw = DEFAULT_LEVERAGE
    return max(1.0, min(float(raw), ceiling))


def order_notional(account_equity: float, size_hint: float, leverage: float) -> float:
    """按保证金口径算敞口。"""
    equity = max(float(account_equity or 0.0), 0.0)
    hint = max(float(size_hint or 0.0), 0.0)
    lev = max(float(leverage or 1.0), 1.0)
    return equity * hint * lev


def min_viable_size_hint(
    account_equity: float,
    leverage: float,
    min_order_notional: float,
) -> float | None:
    """低于这个 size_hint，敞口就够不到交易所的最小下单额。

    杠杆越高这条下界越低——这正是小账户能开出仓位的原因：100 USDT 权益、
    5 USDT 最小下单额，无杠杆时要 0.05，3 倍杠杆下只要 0.017。
    """
    import math

    equity = float(account_equity or 0.0)
    if equity <= 0:
        return None
    lev = max(float(leverage or 1.0), 1.0)
    raw = float(min_order_notional) / (equity * lev)
    # 向上取整到三位小数，避免边界上算出刚好差一点的单子
    return math.ceil(raw * 1000) / 1000
