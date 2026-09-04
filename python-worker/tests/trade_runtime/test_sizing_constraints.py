"""仓位与杠杆口径。

背景：杠杆此前只作为订单元数据发给交易所，不参与仓位计算，于是
100 USDT 的账户敞口永远不超过 max_position_ratio × 100 = 30 USDT，
配置里的 maxLeverage 形同虚设。现在 size_hint 表示动用多少权益作为
保证金，敞口 = 权益 × size_hint × 杠杆。默认 10 倍，硬上限 12 倍。
"""
from __future__ import annotations

import pytest

from trade_runtime.decision.sizing import (
    DEFAULT_LEVERAGE,
    DEFAULT_MIN_POSITION_RATIO,
    LEVERAGE_HARD_CEILING,
    MIN_LEVERAGE,
    leverage_ceiling,
    min_viable_size_hint,
    order_notional,
    position_ratio_floor,
    resolve_leverage,
)
from trade_runtime.decision.nodes.supervisor_agent import _clamp_size_hint, _sizing_constraints
from trade_runtime.risk.guard import RiskGuard


class TestResolveLeverage:
    def test_defaults_to_ten_when_model_says_nothing(self):
        assert resolve_leverage({"maxLeverage": 12}, {}) == 10.0
        assert DEFAULT_LEVERAGE == 10.0

    def test_model_hint_is_honoured_within_the_range(self):
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": 11}) == 11.0

    def test_hint_above_ceiling_is_clamped(self):
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": 50}) == 12.0

    def test_config_ceiling_below_hard_ceiling_wins(self):
        assert resolve_leverage({"maxLeverage": 8}, {"leverage_hint": 9}) == 8.0

    def test_a_ceiling_below_the_floor_still_wins(self):
        """配置把上限压到 10 以下是一个刻意的限制，不该被 MIN_LEVERAGE 顶开
        ——否则"调低上限"反而会调高实际杠杆。"""
        assert resolve_leverage({"maxLeverage": 3}, {"leverage_hint": 9}) == 3.0
        assert resolve_leverage({"maxLeverage": 3}, {}) == 3.0

    def test_config_above_hard_ceiling_is_capped(self):
        """配置写错一个零，不该变成 100 倍杠杆。"""
        assert leverage_ceiling({"maxLeverage": 100}) == LEVERAGE_HARD_CEILING
        assert resolve_leverage({"maxLeverage": 100}, {"leverage_hint": 100}) == 12.0

    def test_never_below_the_floor(self):
        """用户是风险偏好型，要的是 10-12 这个区间，1-9 倍不在选项里。

        提到 10 的依据见 sizing.py 的注释：模型从不主动选高杠杆（线上 7 笔
        入场的 leverage_hint 全部取下界），所以这条下界就是实际杠杆。
        """
        assert MIN_LEVERAGE == 10.0
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": 0}) == 10.0
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": -2}) == 10.0
        # 区间下方的合法数值会被抬到下界，而不是照单全收
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": 6}) == 10.0
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": 1}) == 10.0

    def test_garbage_hint_falls_back_to_default(self):
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": "abc"}) == 10.0
        assert resolve_leverage({"maxLeverage": 12}, {"leverage_hint": None}) == 10.0

    def test_missing_config_falls_back_to_the_conservative_default(self):
        """读不到配置时不能放开到硬上限——那等于"配置丢了反而敢加杠杆"。
        12 倍是明确设定出来的上限，不该由"没读到配置"赋予。"""
        assert leverage_ceiling(None) == DEFAULT_LEVERAGE
        assert leverage_ceiling({}) == DEFAULT_LEVERAGE
        assert resolve_leverage(None, {"leverage_hint": 12}) == DEFAULT_LEVERAGE


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
    def _c(self, equity=100.0, ratio=0.8, max_lev=12):
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
        assert c["default_leverage"] == 10
        assert c["min_leverage"] == 10
        assert c["max_leverage"] == 12

    def test_floor_uses_default_leverage_and_drops_at_max(self):
        c = self._c()
        # 5 USDT 兜底下限 / (100 权益 × 10 倍) = 0.005
        assert c["min_viable_size_hint"] == 0.005
        # 12 倍下是 5/(100×12) = 0.0042，取整到 0.005
        assert c["min_viable_size_hint_at_max_leverage"] == 0.005

    def test_the_size_that_was_rejected_before_is_now_viable(self):
        """线上那次 OPEN_SHORT 给的是 0.04：无杠杆时 4 USDT 敞口不够
        交易所最小下单额，默认杠杆下是 40 USDT，可以下。"""
        c = self._c()
        assert 0.04 >= c["min_viable_size_hint"]
        assert order_notional(100.0, 0.04, c["default_leverage"]) == 40.0

    def test_max_size_hint_caps_margin_not_exposure(self):
        c = self._c()
        assert c["max_size_hint"] == 0.8
        # 上限约束的是保证金：80% 权益 × 10 倍 = 8 倍权益的敞口
        assert order_notional(100.0, c["max_size_hint"], 10.0) == pytest.approx(800.0)

    def test_tiny_account_is_not_tradeable_even_at_max_leverage(self):
        # 0.5 USDT 权益：12 倍下也要 0.834 的 size_hint 才够到 5 USDT 最小
        # 下单额，超过 0.8 的仓位上限。
        c = self._c(equity=0.5)
        assert c["any_size_tradeable"] is False

    def test_ceiling_from_config_is_respected(self):
        """上限低于默认倍数时，默认倍数被压下来而不是反过来。"""
        c = self._c(max_lev=4)
        assert c["max_leverage"] == 4
        assert c["default_leverage"] == 4
        assert c["min_leverage"] == 4

    def test_config_ceiling_below_default_lowers_the_default(self):
        c = self._c(max_lev=2)
        assert c["max_leverage"] == 2
        assert c["default_leverage"] == 2


class TestPositionRatioFloor:
    """size_hint 的下界。

    模型一直贴着交易所最小下单额给量（线上实测 0.02~0.03，而上限是 0.80），
    于是杠杆调多少都看不出区别。这条下界与 MIN_LEVERAGE 是同一件事的两半，
    测试也照着那一组写。
    """

    def test_default_floor(self):
        assert DEFAULT_MIN_POSITION_RATIO == 0.05
        assert position_ratio_floor({}, 0.8) == 0.05
        assert position_ratio_floor(None, 0.8) == 0.05

    def test_config_overrides_the_default(self):
        assert position_ratio_floor({"minPositionRatio": 0.12}, 0.8) == 0.12
        assert position_ratio_floor({"min_position_ratio": 0.12}, 0.8) == 0.12

    def test_zero_is_a_legal_value_meaning_no_floor(self):
        assert position_ratio_floor({"minPositionRatio": 0}, 0.8) == 0.0

    def test_a_ceiling_below_the_floor_still_wins(self):
        """理由同 resolve_leverage：上限是刻意设下的限制，不该被下界顶开，
        否则调低仓位上限反而会调高实际仓位。"""
        assert position_ratio_floor({}, 0.02) == 0.02

    def test_forbidding_positions_is_not_undone_by_the_floor(self):
        assert position_ratio_floor({}, 0.0) == 0.0

    def test_garbage_falls_back_to_the_default(self):
        assert position_ratio_floor({"minPositionRatio": "abc"}, 0.8) == 0.05
        assert position_ratio_floor({"minPositionRatio": -1}, 0.8) == 0.05

    def test_floor_reaches_the_worker_through_model_dump(self):
        """和 maxLeverage 一样只存在于 runtimeFlagsJson 里：不显式声明字段，
        pydantic 就会在 model_dump 时把它丢掉，下界静默退回代码默认值。"""
        from trade_runtime.config import RuntimeConfig

        dumped = RuntimeConfig.model_validate(
            {"defaultMode": "paper", "runtimeFlagsJson": '{"minPositionRatio": 0.12}'}
        ).model_dump()
        assert dumped["min_position_ratio"] == 0.12
        assert position_ratio_floor(dumped, 0.8) == 0.12

    def test_the_floor_is_what_the_model_is_told(self):
        c = _sizing_constraints(
            {"account_equity": 100.0},
            {"max_position_ratio": 0.8, "maxLeverage": 12, "minPositionRatio": 0.05},
        )
        assert c["min_size_hint"] == 0.05
        # 下界必须高于够得着最小下单额的那条线，否则这条下界毫无作用
        assert c["min_size_hint"] > c["min_viable_size_hint"]

    def test_open_size_below_the_floor_is_raised(self):
        state = {"runtime_config": {"max_position_ratio": 0.8, "minPositionRatio": 0.05}}
        assert _clamp_size_hint(state, {"action": "OPEN_LONG", "size_hint": 0.02})["size_hint"] == 0.05
        assert _clamp_size_hint(state, {"action": "OPEN_SHORT", "size_hint": 0.02})["size_hint"] == 0.05

    def test_a_size_already_inside_the_range_is_untouched(self):
        state = {"runtime_config": {"max_position_ratio": 0.8, "minPositionRatio": 0.05}}
        assert _clamp_size_hint(state, {"action": "OPEN_LONG", "size_hint": 0.3})["size_hint"] == 0.3

    def test_zero_with_an_open_action_is_not_turned_into_a_position(self):
        """OPEN 配 size_hint=0 是自相矛盾的输入，保守的读法是模型并不想建仓
        ——不该由下界凭空造出一个仓位。"""
        state = {"runtime_config": {"max_position_ratio": 0.8, "minPositionRatio": 0.05}}
        assert _clamp_size_hint(state, {"action": "OPEN_LONG", "size_hint": 0})["size_hint"] == 0.0

    def test_closing_is_never_raised(self):
        """CLOSE 与 REDUCE 的 size_hint 语义是平掉多少，抬高它就成了强行加仓。"""
        state = {"runtime_config": {"max_position_ratio": 0.8, "minPositionRatio": 0.05}}
        assert _clamp_size_hint(state, {"action": "CLOSE", "size_hint": 0.01})["size_hint"] == 1.0
        assert _clamp_size_hint(state, {"action": "REDUCE", "size_hint": 0.01})["size_hint"] == 0.01

    def test_adding_is_bounded_by_headroom_not_lifted_past_it(self):
        state = {
            "runtime_config": {"max_position_ratio": 0.8, "minPositionRatio": 0.05},
            "account_equity": 100.0,
            "current_position_notional": 78.0,
        }
        # 只剩 0.02 的余量，下界不能把它顶到 0.05
        assert _clamp_size_hint(state, {"action": "ADD_LONG", "size_hint": 0.01})["size_hint"] == pytest.approx(0.02)


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
        assert dumped["max_leverage"] == 10.0
        assert leverage_ceiling(dumped) == 10.0

    def test_end_to_end_default_and_ceiling(self):
        dumped = self._config('{"maxLeverage": 12}')
        assert resolve_leverage(dumped, {}) == 10.0
        # 区间下方的建议被抬到下界
        assert resolve_leverage(dumped, {"leverage_hint": 8}) == 10.0
        assert resolve_leverage(dumped, {"leverage_hint": 50}) == 12.0

    def test_garbage_value_falls_back_rather_than_raising(self):
        assert self._config('{"maxLeverage": "abc"}')["max_leverage"] == 10.0
        assert self._config('{"maxLeverage": 0}')["max_leverage"] == 10.0
        assert self._config('{"maxLeverage": -5}')["max_leverage"] == 10.0
