"""价格轨迹分析工具函数"""

from __future__ import annotations

from typing import Any


def analyze_price_pattern(trajectory: list[dict[str, Any]]) -> str:
    """分析价格轨迹模式

    Args:
        trajectory: 价格轨迹列表，每个元素包含 pnl_pct 字段

    Returns:
        str: 先涨后跌/先跌后涨/横盘震荡/单边上涨/单边下跌/数据不足/波动后回归
    """
    if not trajectory or len(trajectory) < 3:
        return "数据不足"

    pnl_values = [item.get("pnl_pct", 0) for item in trajectory]
    max_pnl = max(pnl_values)
    min_pnl = min(pnl_values)
    max_idx = pnl_values.index(max_pnl)
    min_idx = pnl_values.index(min_pnl)
    final_pnl = pnl_values[-1]

    if max_pnl > 1.0 and min_pnl < -1.0:
        return "先涨后跌" if max_idx < min_idx else "先跌后涨"
    elif max_pnl > 1.0 and final_pnl > 0.5:
        return "单边上涨"
    elif min_pnl < -1.0 and final_pnl < -0.5:
        return "单边下跌"
    elif abs(max_pnl) < 1.0 and abs(min_pnl) < 1.0:
        return "横盘震荡"
    else:
        return "波动后回归"
