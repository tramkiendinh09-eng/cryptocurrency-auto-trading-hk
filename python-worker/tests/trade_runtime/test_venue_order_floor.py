"""可下区间必须按标的算，而不是一个全局的 5 USDT。

这条链路上线时没有测试，代价是两笔置信度 60+ 的 ETH 信号：模型照着提示词
里那个"最小下单额 5 USDT"给出 10 和 15 USDT 的仓位，两单都建好、发出去，
然后被交易所过滤器以"低于该标的最小名义金额"静默拒掉。ETH 的真实下限是
21.6 USDT。
"""

import pytest

from trade_runtime.decision.nodes.supervisor_agent import _sizing_constraints
from trade_runtime.decision.sizing import venue_order_floor
from trade_runtime.execution.symbol_filters import BinanceSymbolFilters

EXCHANGE_INFO = {
    "symbols": [
        {
            "symbol": "ETHUSDT",
            "quantityPrecision": 3,
            "filters": [
                {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "10000"},
                {"filterType": "MIN_NOTIONAL", "notional": "20"},
            ],
        },
        {
            "symbol": "SOLUSDT",
            "quantityPrecision": 2,
            "filters": [
                {"filterType": "LOT_SIZE", "stepSize": "0.01", "minQty": "0.01", "maxQty": "100000"},
                {"filterType": "MIN_NOTIONAL", "notional": "5"},
            ],
        },
    ]
}


@pytest.fixture
def venue(monkeypatch):
    """把共享的交易所过滤器换成固定快照，测试不依赖真实行情。"""

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return EXCHANGE_INFO

    monkeypatch.setattr(
        "trade_runtime.execution.symbol_filters.requests.get",
        lambda url, timeout=None, **kwargs: _Response(),
    )
    instance = BinanceSymbolFilters()
    monkeypatch.setattr(
        "trade_runtime.execution.symbol_filters.shared_binance_filters",
        lambda **kwargs: instance,
    )
    return instance


class TestVenueOrderFloor:
    def test_eth_floor_is_four_times_sol(self, venue):
        eth, _, eth_source = venue_order_floor("ETHUSDT", 2400.0)
        sol, _, sol_source = venue_order_floor("SOLUSDT", 100.0)
        assert eth_source == sol_source == "venue"
        assert eth == pytest.approx(21.6)
        assert sol == pytest.approx(5.0)
        assert eth > sol * 4

    def test_step_is_reported_so_size_is_not_truncated_away(self, venue):
        """成交向下截断到步进整数倍。一笔 12 USDT 的 BNB 单落进 7.01 的
        仓位，就是因为没人告诉模型步进存在。"""
        _, step, _ = venue_order_floor("SOLUSDT", 100.0)
        assert step == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "symbol,price,expected_source",
        [
            ("FAKEUSDT", 100.0, "fallback:unknown_symbol"),
            ("ETHUSDT", 0.0, "fallback:no_price"),
            ("ETHUSDT", -5.0, "fallback:no_price"),
        ],
    )
    def test_fallback_paths_are_labelled(self, venue, symbol, price, expected_source):
        """兜底值必须带上来源，让调用方知道这个数是猜的而不是查来的。"""
        notional, step, source = venue_order_floor(symbol, price, 5.0)
        assert source == expected_source
        assert notional == 5.0
        assert step == 0.0

    def test_unreachable_exchange_does_not_break_the_decision(self, monkeypatch):
        """交易所信息拿不到不能让决策链断掉——退回兜底值继续走。"""

        def _boom(**kwargs):
            raise RuntimeError("network down")

        monkeypatch.setattr(
            "trade_runtime.execution.symbol_filters.shared_binance_filters", _boom
        )
        notional, step, source = venue_order_floor("ETHUSDT", 2400.0, 5.0)
        assert source == "fallback:filters_unavailable"
        assert notional == 5.0


class TestSizingConstraintsUseTheSymbolsOwnFloor:
    """提示词里给模型看的区间，必须是这个标的自己的区间。"""

    def _constraints(self, symbol, price, equity=100.0):
        state = {"symbol": symbol, "account_equity": equity, "feature_snapshot": {"price": price}}
        return _sizing_constraints(state, {"max_position_ratio": 0.3, "maxLeverage": 12})

    def test_eth_demands_a_much_larger_hint_than_sol(self, venue):
        eth = self._constraints("ETHUSDT", 2400.0)
        sol = self._constraints("SOLUSDT", 100.0)
        assert eth["min_order_notional_usdt"] == pytest.approx(21.6)
        assert sol["min_order_notional_usdt"] == pytest.approx(5.0)
        # 10 倍杠杆、100 USDT 权益：21.6/(100*10)=0.0216，5/(100*10)=0.005
        assert eth["min_viable_size_hint"] == pytest.approx(0.022)
        assert sol["min_viable_size_hint"] == pytest.approx(0.005)

    def test_the_old_global_constant_would_have_understated_eth_by_4x(self, venue):
        """回归守卫：这正是上线时丢掉两笔 ETH 信号的那个数。

        断言写成"相对 SOL 的倍数"而不是一个硬编码常量，这样杠杆策略再变
        也不会把这条守卫变成一句空话。倍数关系落在 min_order_notional 上：
        size_hint 那一侧要向上取整到三位小数，SOL 这种很小的值被取整抬高的
        比例更大（0.0083→0.009），杠杆越高、两者的比值被压得越扁。
        """
        eth = self._constraints("ETHUSDT", 2400.0)
        sol = self._constraints("SOLUSDT", 100.0)
        assert eth["min_order_notional_usdt"] > sol["min_order_notional_usdt"] * 4
        assert eth["min_viable_size_hint"] > sol["min_viable_size_hint"] * 3

    def test_constraints_say_which_symbol_and_where_the_number_came_from(self, venue):
        eth = self._constraints("ETHUSDT", 2400.0)
        assert eth["min_order_notional_symbol"] == "ETHUSDT"
        assert eth["min_order_notional_source"] == "venue"
        assert eth["notional_step_usdt"] == pytest.approx(2.4)

    def test_leverage_still_lowers_the_floor(self, venue):
        """杠杆越高、够到最小下单额需要的保证金越少——小账户的入场全靠这个。"""
        eth = self._constraints("ETHUSDT", 2400.0)
        assert eth["min_viable_size_hint_at_max_leverage"] < eth["min_viable_size_hint"]
        # 12 倍上限下 21.6/(100*12) = 0.018
        assert eth["min_viable_size_hint_at_max_leverage"] == pytest.approx(0.018)

    def test_symbol_too_expensive_for_the_account_is_flagged_untradeable(self, venue):
        """够不到就得明说，让模型直接 SKIP，而不是给一个必被拒的仓位。"""
        tiny = self._constraints("ETHUSDT", 2400.0, equity=5.0)
        assert tiny["any_size_tradeable"] is False

    def test_missing_price_falls_back_without_raising(self, venue):
        state = {"symbol": "ETHUSDT", "account_equity": 100.0}
        result = _sizing_constraints(state, {"max_position_ratio": 0.3})
        assert result["min_order_notional_source"] == "fallback:no_price"
