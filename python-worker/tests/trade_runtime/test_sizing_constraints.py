"""仓位约束：模型必须知道多小的单子下不出去。

线上唯一一次 OPEN_SHORT 给的是 size_hint 0.04 —— 100 USDT 权益对应
4 USDT 名义价值，低于交易所最小下单额，即使不被超时丢掉也会被拒。
"""
from __future__ import annotations

from trade_runtime.decision.nodes.supervisor_agent import _sizing_constraints


class TestSizingConstraints:
    def test_small_account_lower_bound(self):
        """100 USDT + 5 USDT 最小下单额 → size_hint 不能低于 0.05。"""
        c = _sizing_constraints({"account_equity": 100.0},
                                {"max_position_ratio": 0.3, "max_leverage": 3})
        assert c["min_viable_size_hint"] == 0.05
        assert c["max_size_hint"] == 0.3
        assert c["any_size_tradeable"] is True

    def test_the_size_that_was_actually_returned_is_below_the_floor(self):
        c = _sizing_constraints({"account_equity": 100.0},
                                {"max_position_ratio": 0.3})
        assert 0.04 < c["min_viable_size_hint"], "0.04 应当落在可下区间之外"

    def test_bigger_account_has_a_lower_floor(self):
        c = _sizing_constraints({"account_equity": 1000.0},
                                {"max_position_ratio": 0.3})
        assert c["min_viable_size_hint"] == 0.01

    def test_ratio_below_floor_means_nothing_is_tradeable(self):
        """上限比例比最小下单额还小时，任何仓位都开不出来，要让模型直接 SKIP。"""
        c = _sizing_constraints({"account_equity": 100.0},
                                {"max_position_ratio": 0.03})
        assert c["any_size_tradeable"] is False

    def test_zero_equity_is_not_tradeable(self):
        c = _sizing_constraints({"account_equity": 0.0},
                                {"max_position_ratio": 0.3})
        assert c["min_viable_size_hint"] is None
        assert c["any_size_tradeable"] is False

    def test_leverage_ceiling_is_surfaced(self):
        c = _sizing_constraints({"account_equity": 100.0},
                                {"max_position_ratio": 0.3, "maxLeverage": 5})
        assert c["max_leverage"] == 5

    def test_leverage_defaults_when_unset(self):
        c = _sizing_constraints({"account_equity": 100.0},
                                {"max_position_ratio": 0.3})
        assert c["max_leverage"] == 3

    def test_states_that_leverage_does_not_scale_exposure(self):
        """这套实现里名义价值 = 权益 × size_hint，杠杆只影响保证金。
        不写明的话，模型会以为调高 leverage_hint 就能放大仓位。"""
        c = _sizing_constraints({"account_equity": 100.0}, {"max_position_ratio": 0.3})
        assert c["order_notional_formula"] == "account_equity * size_hint"
        assert c["leverage_scales_margin_not_notional"] is True
