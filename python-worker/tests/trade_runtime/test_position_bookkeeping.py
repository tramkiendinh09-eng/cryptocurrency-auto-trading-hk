"""仓位账目：记的必须是真实发生过的仓位，且浮盈要跟着行情走。

两个都是线上实际发生的问题：

1. 被交易所拒掉的两笔 ETH 单，各留下一条 exit_time 永远为空的持仓生命
   周期，记着两笔从未存在过的仓位——因为那段代码只看模型给了什么动作，
   从不检查这一单成没成交。
2. BNB 那笔实际浮盈 +0.11 USDT，控制台显示 0——因为 position_snapshot
   只在成交时写入，而成交那一刻开仓价必然等于成交价，浮盈算出来就是 0，
   之后再没有任何东西更新它。
"""

import pytest

from trade_runtime.decision.nodes.execution_node import execution_node
from trade_runtime.memory.trade_lifecycle import process_trade_lifecycle


class _RecordingLifecycleManager:
    def __init__(self):
        self.entries = []
        self.closes = []

    def record_entry(self, **kwargs):
        self.entries.append(kwargs)
        return {"status": "recorded", "operation": "entry"}

    def record_exit(self, **kwargs):
        self.closes.append(kwargs)
        return {"status": "recorded", "operation": "exit"}


def _open_state(execution_result):
    return {
        "trace_id": "trace-eth-1",
        "symbol": "ETHUSDT",
        "exchange": "binance",
        "supervisor_decision": {"action": "OPEN_SHORT", "side": "short", "size_hint": 0.05},
        "execution_result": execution_result,
    }


class TestLifecycleRequiresAnActualFill:
    """生命周期记的是仓位，不是意图。"""

    def test_venue_rejected_order_records_no_lifecycle(self):
        """这就是那两条幽灵 ETH 记录的成因。

        router 即使返回 skipped 也会带上 entry_price，所以"有价格"这个
        前置条件照样满足——必须显式判断成交状态。
        """
        manager = _RecordingLifecycleManager()
        result = process_trade_lifecycle(
            state=_open_state(
                {
                    "status": "skipped",
                    "order_status": "SKIPPED",
                    "reason": "venue_filter:below_min_notional:notional=15.0000 min=20",
                    "entry_price": 2395.35,
                    "fill_price": 2395.35,
                }
            ),
            lifecycle_manager=manager,
        )
        assert manager.entries == []
        assert result["status"] == "skipped"
        assert result["reason"] == "execution_not_filled:skipped"

    @pytest.mark.parametrize(
        "status", ["skipped", "blocked", "failed", "canceled", "expired", "pending", "submitted"]
    )
    def test_no_lifecycle_for_any_non_filling_status(self, status):
        manager = _RecordingLifecycleManager()
        process_trade_lifecycle(
            state=_open_state({"status": status, "entry_price": 2395.35}),
            lifecycle_manager=manager,
        )
        assert manager.entries == []

    def test_filled_order_still_records_normally(self):
        """守卫不能把正常路径一起挡掉。"""
        manager = _RecordingLifecycleManager()
        result = process_trade_lifecycle(
            state=_open_state({"status": "filled", "entry_price": 2395.35, "fill_quantity": 0.009}),
            lifecycle_manager=manager,
        )
        assert result["status"] == "recorded"
        assert len(manager.entries) == 1
        assert manager.entries[0]["symbol"] == "ETHUSDT"
        assert manager.entries[0]["side"] == "short"

    def test_unknown_status_still_records(self):
        """状态未知时按"动过"处理：漏记一次仓位变化比凭空记一次更难发现。"""
        manager = _RecordingLifecycleManager()
        process_trade_lifecycle(
            state=_open_state({"entry_price": 2395.35}),
            lifecycle_manager=manager,
        )
        assert len(manager.entries) == 1


class _SnapshotClient:
    def __init__(self):
        self.position_snapshots = []

    def post_decision_audit(self, payload):
        return None

    def post_exchange_order(self, payload):
        return None

    def post_position_snapshot(self, payload):
        self.position_snapshots.append(payload)


class TestOpenPositionIsMarkedToMarket:
    """控制台的收益读的是 sum(unrealized_pnl)，所以这个数不刷新就等于没有。"""

    def _hold_state(self, client, price):
        return {
            "trace_id": "trace-hold-1",
            "symbol": "BNBUSDT",
            "exchange": "binance",
            "mode": "paper",
            "account_equity": 100.0,
            "current_position_side": "long",
            "current_position_quantity": 0.01,
            "entry_price": 701.16,
            "entry_trace_id": "trace-open-1",
            "event_bundle": [{"event_type": "market_tick", "price": price}],
            "supervisor_decision": {"action": "HOLD", "side": "long", "size_hint": 0.0},
            "callback_client": client,
        }

    def test_hold_refreshes_unrealized_pnl_at_the_current_price(self):
        client = _SnapshotClient()
        execution_node(self._hold_state(client, 712.48))
        assert len(client.position_snapshots) == 1
        snapshot = client.position_snapshots[0]
        # (712.48 - 701.16) * 0.01 —— 线上那笔 BNB 的真实浮盈
        assert snapshot["unrealizedPnl"] == pytest.approx(0.1132)
        assert snapshot["symbol"] == "BNBUSDT"
        assert snapshot["side"] == "long"
        assert snapshot["positionQuantity"] == pytest.approx(0.01)
        assert snapshot["entryPrice"] == pytest.approx(701.16)

    def test_short_pnl_has_the_opposite_sign(self):
        client = _SnapshotClient()
        state = self._hold_state(client, 100.77)
        state.update(
            {
                "symbol": "SOLUSDT",
                "current_position_side": "short",
                "current_position_quantity": 0.05,
                "entry_price": 100.27,
                "supervisor_decision": {"action": "HOLD", "side": "short", "size_hint": 0.0},
            }
        )
        execution_node(state)
        # 空单价格涨了就是亏——线上那笔 SOL 平仓时正好是 -0.025
        assert client.position_snapshots[0]["unrealizedPnl"] == pytest.approx(-0.025)

    def test_hold_links_back_to_the_opening_trace(self):
        """刷新出来的快照要挂在原来那次开仓上，否则对不上账。"""
        client = _SnapshotClient()
        execution_node(self._hold_state(client, 712.48))
        assert client.position_snapshots[0]["entryTraceId"] == "trace-open-1"

    def test_flat_hold_writes_nothing(self):
        client = _SnapshotClient()
        state = self._hold_state(client, 712.48)
        state.update({"current_position_side": "flat", "current_position_quantity": 0.0})
        execution_node(state)
        assert client.position_snapshots == []

    def test_missing_price_writes_nothing(self):
        """算错的浮盈比没更新的浮盈更糟。"""
        client = _SnapshotClient()
        state = self._hold_state(client, 712.48)
        state["event_bundle"] = []
        execution_node(state)
        assert client.position_snapshots == []

    def test_plain_skip_does_not_write(self):
        """RULE_ONLY 的 SKIP 每分钟都有，按那个频率写会灌满这张表。"""
        client = _SnapshotClient()
        state = self._hold_state(client, 712.48)
        state["supervisor_decision"] = {"action": "SKIP", "side": "long", "size_hint": 0.0}
        execution_node(state)
        assert client.position_snapshots == []
