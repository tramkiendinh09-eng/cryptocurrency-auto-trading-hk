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

import os
from typing import Any


#: 模型没给 leverage_hint 时用的倍数。
#:
#: 提到 10 是一次刻意的风险偏好选择，依据是两件事：
#: 一、模型从不主动选高杠杆——线上 7 笔入场的 leverage_hint 全部取区间下界，
#:     所以这条下界就是实际杠杆，改它才有效。
#: 二、ready 信号的前向收益是正期望且显著（30 天 163 个样本，均 +0.3904%、
#:     t=3.11，扣费后 +0.3104%），正期望下放大敞口在统计上是划算的。
#: 对照：放宽止损只放大风险不放大收益——止损位从 0.6% 扫到 4% 再到不止损，
#: 均收益全部落在 +0.28~+0.33 的噪声带内（见 calibration/stop_loss_scan.py）。
DEFAULT_LEVERAGE = 10.0

#: 允许的最低倍数。低于这个数的 leverage_hint 会被抬到这里——用户要的是
#: 10-12 倍这个区间，1-9 倍不在选项里。这条会被更低的 ceiling 压过：配置
#: 明确把上限设到 3，就不该因为这里写了 10 而反过来放大杠杆。
MIN_LEVERAGE = 10.0

#: 硬上限。运行时配置里的 maxLeverage 可以更低，但不能更高——
#: 把这条写死在代码里，是为了让"配置写错一个零"不至于变成 100 倍杠杆。
LEVERAGE_HARD_CEILING = 12.0

#: 开仓时 size_hint 的下界，口径同 size_hint 本身：动用多少比例的权益作为
#: 保证金。设这条的理由和 MIN_LEVERAGE 完全一样——模型一直贴着交易所最小
#: 下单额给量（实测落在 0.02~0.03，而上限是 0.80），于是杠杆调多少都看不出
#: 区别，敞口始终是十几 USDT。下界只对开仓生效：平仓与减仓的 size_hint 语义
#: 是平掉多少，抬高它就变成了强行加仓。
DEFAULT_MIN_POSITION_RATIO = 0.05


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


def position_ratio_floor(runtime_config: Any, max_position_ratio: float) -> float:
    """取开仓时 size_hint 的下界。

    配置里的 ``minPositionRatio`` 覆盖默认值，读不到就用默认值。

    夹在 max_position_ratio 之内的理由与 resolve_leverage 里那条相同：上限是
    刻意设下的限制，不该被这里的下界顶开，否则调低仓位上限反而会调高实际
    仓位。上限本身为 0（即禁止开仓）时下界也是 0。
    """
    ceiling = max(float(max_position_ratio or 0.0), 0.0)
    if ceiling <= 0:
        return 0.0
    floor = None
    if isinstance(runtime_config, dict):
        raw = (
            runtime_config.get("min_position_ratio")
            if runtime_config.get("min_position_ratio") is not None
            else runtime_config.get("minPositionRatio")
        )
        floor = _optional_float(raw)
    if floor is None or floor < 0:
        floor = DEFAULT_MIN_POSITION_RATIO
    return min(float(floor), ceiling)


def resolve_leverage(runtime_config: Any, decision: Any) -> float:
    """定出这一单实际使用的杠杆。

    模型给的 leverage_hint 只是建议：币安的杠杆是账户级状态，一个无界的
    建议不只是这一单下得不对，它会改掉该标的之后每一单的保证金模式。
    所以一律夹在 [MIN_LEVERAGE, ceiling] 内；没给或给了非法值时退回默认
    倍数。

    下界取 min(MIN_LEVERAGE, ceiling) 而不是直接取 MIN_LEVERAGE：配置若把
    上限明确压到 5 以下，那是一个刻意的限制，不该被这里的下界顶开——否则
    "调低上限"反而会调高实际杠杆。
    """
    raw = None
    if isinstance(decision, dict):
        raw = _optional_float(decision.get("leverage") or decision.get("leverage_hint"))
    ceiling = leverage_ceiling(runtime_config)
    floor = min(MIN_LEVERAGE, ceiling)
    if raw is None or raw <= 0:
        raw = DEFAULT_LEVERAGE
    return max(floor, min(float(raw), ceiling))


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

# ---------------------------------------------------------------------------
# 可下仓位区间：写给模型看的那一段
# ---------------------------------------------------------------------------

#: 交易所对单笔委托的最小名义价值。币安 U 本位合约多数交易对是 5 USDT，
#: 个别是 20。给不出准确值时宁可取大：报小了会让模型开出必然被拒的单子。
MIN_ORDER_NOTIONAL_USDT = float(
    os.getenv("TRADE_RUNTIME_MIN_ORDER_NOTIONAL_USDT", "5") or 5
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def current_market_price(state: Any) -> float:
    """从决策状态里取当前价。

    价格决定按标的算出来的最小下单额（步进是按币量定的），所以它是
    sizing_constraints 的输入而不是装饰。取不到价时 venue_order_floor 会
    退回兜底值并标注来源。
    """
    if not isinstance(state, dict):
        return 0.0
    feature_snapshot = state.get("feature_snapshot") or {}
    if isinstance(feature_snapshot, dict):
        position_context = feature_snapshot.get("position_risk_context") or {}
        if isinstance(position_context, dict):
            price = _safe_float(position_context.get("current_price"), 0.0)
            if price > 0:
                return price
        for key in ("effective_price", "latest_price", "price"):
            price = _safe_float(feature_snapshot.get(key), 0.0)
            if price > 0:
                return price
    events = state.get("event_bundle")
    if isinstance(events, list):
        for event in reversed(events):
            if not isinstance(event, dict):
                continue
            price = _safe_float(event.get("effective_price") or event.get("price"), 0.0)
            if price > 0:
                return price
    return 0.0


def sizing_constraints(state: Any, runtime_config: Any) -> dict[str, Any]:
    """算出这一刻、这个标的真正可下的仓位区间。

    口径与本模块其余部分完全一致（同一份实现），否则模型会按一个区间给值、
    风控和下单却按另一个算，出现"照着提示给的数反而被拒"。

    杠杆在这里是有用的：size_hint 是动用多少权益作为保证金，敞口是它乘
    杠杆，所以杠杆越高、能满足交易所最小下单额的 size_hint 下界越低。

    最小下单额必须按标的取。此前用的是一个全局常量 5 USDT，而实测 ETH 的
    真实下限是 21.6——模型照着 5 给 ETH 定了 10 和 15 USDT 两单，建好、发出、
    被交易所过滤器静默拒掉，两次有效信号就这么没了。

    内联提示词与模板渲染上下文都调这一个函数。模板路径此前没有这一段，
    切过去就会整段丢失。
    """
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    equity = _safe_float((state or {}).get("account_equity") if isinstance(state, dict) else None, 0.0)
    max_ratio = _safe_float(runtime_config.get("max_position_ratio"), 0.0)
    ceiling = leverage_ceiling(runtime_config)
    default_leverage = min(DEFAULT_LEVERAGE, ceiling)
    floor_leverage = min(MIN_LEVERAGE, ceiling)

    symbol = (state or {}).get("symbol") if isinstance(state, dict) else None
    price = current_market_price(state)
    min_notional, notional_step, notional_source = venue_order_floor(
        symbol or "",
        price,
        MIN_ORDER_NOTIONAL_USDT,
    )

    # 下界按默认杠杆给：模型可以自己抬到 ceiling，那只会让下界更低。
    min_hint = min_viable_size_hint(equity, default_leverage, min_notional)
    floor_at_max_leverage = min_viable_size_hint(equity, ceiling, min_notional)

    tradeable = (
        floor_at_max_leverage is not None
        and max_ratio > 0
        and floor_at_max_leverage <= max_ratio
    )
    return {
        "account_equity": equity,
        "order_notional_formula": "account_equity * size_hint * leverage",
        "margin_formula": "account_equity * size_hint",
        "leverage_scales_exposure": True,
        "default_leverage": int(default_leverage),
        # 低于这个倍数的 leverage_hint 会被抬上来，所以直接告诉模型区间，
        # 免得它给出一个会被悄悄改掉的值。
        "min_leverage": int(floor_leverage),
        "max_leverage": int(ceiling),
        "min_order_notional_usdt": round(min_notional, 4),
        # 这个下限是这个标的自己的，不是全局值——各标的能差四倍以上。
        "min_order_notional_symbol": symbol or None,
        "min_order_notional_source": notional_source,
        # 成交数量按步进向下截断，所以下单额落在步进整数倍上才不浪费保证金。
        "notional_step_usdt": round(notional_step, 4) if notional_step > 0 else None,
        # 低于这个比例的 size_hint 会被抬上来，理由同 min_leverage：
        # 与其让模型给一个会被悄悄改掉的值，不如直接把区间告诉它。
        "min_size_hint": position_ratio_floor(runtime_config, max_ratio),
        "min_viable_size_hint": min_hint,
        "min_viable_size_hint_at_max_leverage": floor_at_max_leverage,
        "max_size_hint": max_ratio or None,
        "any_size_tradeable": bool(tradeable),
    }
