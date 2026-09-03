"""仓位与杠杆口径。

背景：杠杆此前只作为订单元数据发给交易所，不参与仓位计算，于是
100 USDT 的账户敞口永远不超过 max_position_ratio × 100 = 30 USDT，
配置里的 maxLeverage 形同虚设。现在 size_hint 表示动用多少权益作为
保证金，敞口 = 权益 × size_hint × 杠杆。默认 3 倍，硬上限 10 倍。
"""
from __future__ import annotations

import pytest

from trade_runtime.decision.sizing import (
    DEFAULT_LEVERAGE,
    LEVERAGE_HARD_CEILING,
    leverage_ceiling,
    min_viable_size_hint,
    order_notional,
    resolve_leverage,
)
from trade_runtime.decision.nodes.supervisor_agent import _sizing_constraints
from trade_runtime.risk.guard import RiskGuard


class TestResolveLeverage:
    def test_defaults_to_three_when_model_says_nothing(self):
        assert resolve_leverage({"maxLeverage": 10}, {}) == 3.0
        assert DEFAULT_LEVERAGE == 3.0

    def test_model_hint_is_honoured_within_the_ceiling(self):
        assert resolve_leverage({"maxLeverage": 10}, {"leverage_hint": 5}) == 5.0

    def test_hint_above_ceiling_is_clamped(self):
        assert resolve_leverage({"maxLeverage": 10}, {"leverage_hint": 50}) == 10.0

    def test_config_ceiling_below_hard_ceiling_wins(self):
        assert resolve_leverage({"maxLeverage": 4}, {"leverage_hint": 9}) == 4.0

    def test_config_above_hard_ceiling_is_capped(self):
        """配置写错一个零，不该变成 100 倍杠杆。"""
        assert leverage_ceiling({"maxLeverage": 100}) == LEVERAGE_HARD_CEILING
        assert resolve_leverage({"maxLeverage": 100}, {"leverage_hint": 100}) == 10.0

    def test_never_below_one(self):
        assert resolve_leverage({"maxLeverage": 10}, {"leverage_hint": 0}) == 3.0
        assert resolve_leverage({"maxLeverage": 10}, {"leverage_hint": -2}) == 3.0

    def test_garbage_hint_falls_back_to_default(self):
        assert resolve_leverage({"maxLeverage": 10}, {"leverage_hint": "abc"}) == 3.0
        assert resolve_leverage({"maxLeverage": 10}, {"leverage_hint": None}) == 3.0

    def test_missing_config_falls_back_to_the_conservative_default(self):
        """读不到配置时不能放开到硬上限——那等于"配置丢了反而敢加杠杆"。
        10 倍是明确设定出来的上限，不该由"没读到配置"赋予。"""
        assert leverage_ceiling(None) == DEFAULT_LEVERAGE
        assert leverage_ceiling({}) == DEFAULT_LEVERAGE
        assert resolve_leverage(None, {"leverage_hint": 10}) == DEFAULT_LEVERAGE


class TestOrderNotional:
    def test_leverage_multiplies_exposure(self):
        """这就是本次改动的要点：同样的 size_hint，敞口随杠杆放大。"""
        assert order_notional(100.0, 0.05, 1.0) == 5.0
        assert order_notional(100.0, 0.05, 3.0) == 15.0
        assert order_notional(100.0, 0.05, 10.0) == 50.0

    def test_negative_inputs_are_floored(self):
        assert order_notional(-100.0, 0.05, 3.0) == 0.0
        assert order_notional(100.0, -0.05, 3.0) == 0.0
        assert order_notional(100.0, 0.05, 0.0) == 5.0


class TestMinViableSizeHint:
    def test_leverage_lowers_the_floor(self):
        """小账户能不能开出仓位，差别就在这里。"""
        assert min_viable_size_hint(100.0, 1.0, 5.0) == 0.05
        assert min_viable_size_hint(100.0, 3.0, 5.0) == 0.017
        assert min_viable_size_hint(100.0, 10.0, 5.0) == 0.005

    def test_zero_equity_has_no_floor(self):
        assert min_viable_size_hint(0.0, 3.0, 5.0) is None


class TestSizingConstraints:
    def _c(self, equity=100.0, ratio=0.3, max_lev=10):
        return _sizing_constraints(
            {"account_equity": equity},
            {"max_position_ratio": ratio, "maxLeverage": max_lev},
        )

    def test_states_that_leverage_scales_exposure(self):
        c = self._c()
        assert c["order_notional_formula"] == "account_equity * size_hint * leverage"
        assert c["margin_formula"] == "account_equity * size_hint"
        assert c["leverage_scales_exposure"] is True

    def test_default_and_ceiling_are_surfaced(self):
        c = self._c()
        assert c["default_leverage"] == 3
        assert c["max_leverage"] == 10

    def test_floor_uses_default_leverage_and_drops_at_max(self):
        c = self._c()
        assert c["min_viable_size_hint"] == 0.017
        assert c["min_viable_size_hint_at_max_leverage"] == 0.005

    def test_the_size_that_was_rejected_before_is_now_viable(self):
        """线上那次 OPEN_SHORT 给的是 0.04：无杠杆时 4 USDT 敞口不够
        交易所最小下单额，3 倍杠杆下是 12 USDT，可以下。"""
        c = self._c()
        assert 0.04 >= c["min_viable_size_hint"]
        assert order_notional(100.0, 0.04, c["default_leverage"]) == 12.0

    def test_max_size_hint_caps_margin_not_exposure(self):
        c = self._c()
        assert c["max_size_hint"] == 0.3

    def test_tiny_account_is_not_tradeable_even_at_max_leverage(self):
        c = self._c(equity=1.0)
        assert c["any_size_tradeable"] is False

    def test_ceiling_from_config_is_respected(self):
        c = self._c(max_lev=4)
        assert c["max_leverage"] == 4
        assert c["default_leverage"] == 3

    def test_config_ceiling_below_default_lowers_the_default(self):
        c = self._c(max_lev=2)
        assert c["max_leverage"] == 2
        assert c["default_leverage"] == 2


class TestRiskGuardMarginBasis:
    def _guard(self):
        return RiskGuard(max_position_ratio=0.3, max_daily_loss=-8.0, max_consecutive_failures=3)

    def _eval(self, notional, leverage):
        return self._guard().evaluate(
            account_equity=100.0,
            requested_notional=notional,
            current_position_notional=0.0,
            check_position_limit=True,
            daily_pnl=0.0,
            consecutive_failures=0,
            leverage=leverage,
        )

    def test_limit_applies_to_margin_not_exposure(self):
        """30 USDT 保证金 × 3 倍 = 90 USDT 敞口，应当放行。
        按敞口口径判定的话这里会被 position_limit 挡掉，杠杆就白加了。"""
        assert self._eval(90.0, 3.0)["passed"] is True

    def test_margin_above_the_ratio_is_still_blocked(self):
        """31% 权益作保证金，超过 0.3，无论杠杆多少都该拦。"""
        r = self._eval(93.0, 3.0)
        assert r["passed"] is False
        assert r["rule_code"] == "position_limit"

    def test_leverage_one_behaves_exactly_as_before(self):
        assert self._eval(30.0, 1.0)["passed"] is True
        assert self._eval(31.0, 1.0)["passed"] is False

    def test_default_leverage_argument_keeps_old_callers_working(self):
        r = self._guard().evaluate(
            account_equity=100.0,
            requested_notional=31.0,
            daily_pnl=0.0,
            consecutive_failures=0,
        )
        assert r["passed"] is False

    @pytest.mark.parametrize("leverage", [3.0, 10.0])
    def test_exposure_ceiling_is_ratio_times_leverage(self, leverage):
        cap = 100.0 * 0.3 * leverage
        assert self._eval(cap, leverage)["passed"] is True
        assert self._eval(cap * 1.02, leverage)["passed"] is False

class TestLeverageReachesTheWorker:
    """maxLeverage 只存在于 runtimeFlagsJson 里。

    RuntimeConfig 给 flags 里每一块策略都开了显式字段，唯独漏了这一个，
    于是 pydantic 在 model_dump 时把它丢掉——数据库里把上限改成 10 也不会
    生效，worker 一直在用代码里的默认倍数。这条链路必须有测试守住。
    """

    def _config(self, flags: str):
        from trade_runtime.config import RuntimeConfig

        return RuntimeConfig.model_validate(
            {"defaultMode": "paper", "runtimeFlagsJson": flags}
        ).model_dump()

    def test_value_survives_model_dump(self):
        dumped = self._config('{"maxLeverage": 10}')
        assert dumped["max_leverage"] == 10.0
        assert leverage_ceiling(dumped) == 10.0

    def test_absent_flag_falls_back_to_default(self):
        dumped = self._config("{}")
        assert dumped["max_leverage"] == 3.0
        assert leverage_ceiling(dumped) == 3.0

    def test_end_to_end_default_and_ceiling(self):
        dumped = self._config('{"maxLeverage": 10}')
        assert resolve_leverage(dumped, {}) == 3.0
        assert resolve_leverage(dumped, {"leverage_hint": 8}) == 8.0
        assert resolve_leverage(dumped, {"leverage_hint": 50}) == 10.0

    def test_garbage_value_falls_back_rather_than_raising(self):
        assert self._config('{"maxLeverage": "abc"}')["max_leverage"] == 3.0
        assert self._config('{"maxLeverage": 0}')["max_leverage"] == 3.0
        assert self._config('{"maxLeverage": -5}')["max_leverage"] == 3.0
