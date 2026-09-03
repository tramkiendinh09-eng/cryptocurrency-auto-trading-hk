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
    # 向上取整到三位小数，避免边界上算出刚好差一点的单子。
    # 先 round 掉浮点噪声再取整：21.6/300 在 float 下是 0.07200000000000001，
    # 直接 ceil 会跳到 0.073，凭空多要 1.4% 的保证金。
    return math.ceil(round(raw * 1000, 6)) / 1000

#: 查不到交易所过滤器时用的兜底最小下单额（USDT）。
#: 兜底值偏小是有意的：宁可让一单被交易所拒掉，也不要凭空抬高下界、
#: 把本来能开的仓位挡在门外——前者丢一次信号，后者是永久性的。
FALLBACK_MIN_ORDER_NOTIONAL_USDT = 5.0


def venue_order_floor(
    symbol: str,
    price: float,
    fallback_min_notional: float = FALLBACK_MIN_ORDER_NOTIONAL_USDT,
) -> tuple[float, float, str]:
    """取这个标的此刻真实的最小下单额与下单粒度。

    最小下单额**不是**一个全局常量，而各处代码此前都当成常量在用（5 USDT）。
    实测这批标的：SOL/XRP/DOGE/SUI 约 5，BNB 7.1，NVDA 6.7，而 ETH 是
    21.6——差了四倍多。后果不是理论上的：模型照着"5 USDT 下限"给 ETH 定了
    10 和 15 USDT 两单，两单都建好、发出去，然后被交易所过滤器静默拒掉，
    信号直接丢失。

    返回 (最小下单额, 一个步进值多少钱, 数据来源)。查不到过滤器时退回兜底
    值并标注来源，让调用方知道这个数是猜的。

    Args:
        symbol: 交易对
        price: 当前价格，最小下单额随价格变（步进是按币量定的）
        fallback_min_notional: 查不到时的兜底值

    Returns:
        tuple[float, float, str]: (min_notional, notional_step, source)
    """
    fallback = max(float(fallback_min_notional or 0.0), 0.0)
    resolved_price = _optional_float(price) or 0.0
    if resolved_price <= 0:
        return fallback, 0.0, "fallback:no_price"
    try:
        # 延迟导入：symbol_filters 会发网络请求取 exchangeInfo，不该在
        # 本模块被 import 时就产生副作用。execution 不反向依赖 decision，
        # 所以这里不构成循环导入。
        from trade_runtime.execution.symbol_filters import shared_binance_filters

        spec = shared_binance_filters().get(symbol)
    except Exception:
        # 交易所信息拿不到（离线、限流）不能让决策链断掉：退回兜底值。
        return fallback, 0.0, "fallback:filters_unavailable"
    if spec is None:
        return fallback, 0.0, "fallback:unknown_symbol"
    try:
        floor = float(spec.min_tradable_notional(resolved_price))
        step = float(spec.notional_step(resolved_price))
    except Exception:
        return fallback, 0.0, "fallback:filter_error"
    if floor <= 0:
        return fallback, 0.0, "fallback:no_constraint"
    return floor, max(step, 0.0), "venue"
