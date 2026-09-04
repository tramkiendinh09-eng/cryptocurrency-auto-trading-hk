"""死区内砍亏损单的闸门。

实测 122 个 ready 信号，收益按持仓时长拆开（扣费后）：
    15m -0.084%  30m -0.088%  45m -0.025%  60m +0.010%
    90m +0.174%(t=2.57)  120m +0.249%(t=3.32)  180m +0.492%(t=4.16)
60 分钟之前没有优势，是负的。同批信号最大浮亏中位数 -0.44%、p25 -0.845%，
开仓后先逆向是常态。

线上代价：4 笔平仓全亏，WDC 第 24 分钟(-0.63%)、SNDK 第 42 分钟(-1.11%)
被模型主动 CLOSE，都没碰到 2% 硬止损；SNDK 砍在最深浮亏附近，之后按原方向
+6.31%(240m)。
"""
from __future__ import annotations

import json

from trade_runtime.decision.nodes.supervisor_agent import _apply_min_hold_guard


def _state(*, held, side="long", severity="", pnl_pct=-0.8, min_hold=None):
    flags = {} if min_hold is None else {"minHoldMinutesBeforeDiscretionaryClose": min_hold}
    risk = {}
    if severity or pnl_pct is not None:
        risk = {"severity": severity, "position_risk_context": {"pnl_pct": pnl_pct}}
    return {
        "current_position_side": side,
        "current_position_quantity": 1.0,
        "current_position_holding_minutes": held,
        "position_risk_result": risk,
        "runtime_config": {"runtime_flags_json": json.dumps(flags)},
    }


def _close(reason="model wants out"):
    return {"action": "CLOSE", "side": "long", "size_hint": 1.0, "summary_reason": reason}


def test_losing_close_inside_the_dead_zone_is_downgraded_to_hold():
    out = _apply_min_hold_guard(_state(held=24), _close())
    assert out["action"] == "HOLD"
    assert out["size_hint"] == 0.0
    assert out["min_hold_guard"]["held_minutes"] == 24
    assert "min_hold_guard" in out["summary_reason"]
    assert "model wants out" in out["summary_reason"], "原始理由必须保留下来"


def test_close_after_the_window_is_untouched():
    out = _apply_min_hold_guard(_state(held=95), _close())
    assert out["action"] == "CLOSE"


def test_taking_profit_early_is_not_blocked():
    """结论只针对"砍亏损单"。浮盈为正时照常放行。"""
    out = _apply_min_hold_guard(_state(held=20, pnl_pct=3.2), _close("+3.2% take profit"))
    assert out["action"] == "CLOSE"


def test_risk_close_severity_is_not_blocked():
    """2% 级别的真失效不是噪声，不该拦。"""
    out = _apply_min_hold_guard(_state(held=10, severity="close", pnl_pct=-2.1), _close())
    assert out["action"] == "CLOSE"


def test_reduce_severity_is_still_blocked_because_hard_stop_covers_it():
    """reduce 级(1.6%)仍在闸门内——再跌 0.4% 就由 2% 硬止损接手，
    而硬止损走 app.py 的独立路径，不经过这里。"""
    out = _apply_min_hold_guard(_state(held=30, severity="reduce", pnl_pct=-1.6), _close())
    assert out["action"] == "HOLD"


def test_gate_is_off_when_set_to_zero():
    out = _apply_min_hold_guard(_state(held=5, min_hold=0), _close())
    assert out["action"] == "CLOSE"


def test_unknown_holding_time_fails_open():
    """读不到持仓时长就放行——宁可放行，也不要因为缺数据把仓位锁住。"""
    out = _apply_min_hold_guard(_state(held=None), _close())
    assert out["action"] == "CLOSE"


def test_flat_book_is_untouched():
    out = _apply_min_hold_guard(_state(held=5, side="flat"), _close())
    assert out["action"] == "CLOSE"


def test_non_close_actions_are_untouched():
    for action in ("HOLD", "REDUCE", "OPEN_LONG", "SKIP"):
        payload = {"action": action, "side": "long", "size_hint": 0.5}
        assert _apply_min_hold_guard(_state(held=5), payload)["action"] == action


def test_default_window_is_sixty_minutes():
    """未配置时用 60 分钟——期望收益转正的那个点，不是显著的 90。
    只拦明确为负的区间，是这批数据能支持的最小干预。"""
    assert _apply_min_hold_guard(_state(held=59), _close())["action"] == "HOLD"
    assert _apply_min_hold_guard(_state(held=60), _close())["action"] == "CLOSE"
