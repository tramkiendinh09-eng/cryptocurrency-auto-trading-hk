"""OKX 爆仓单：补上一个从部署至今恒为 0 的维度。

币安的 forceOrders 是 USER_DATA，公开 REST 没有全市场爆仓来源，所以
liquidationNotionalUsd（250000）这道阈值一直没有过任何数据。OKX 的
liquidation-orders 是公开的，但本机直连 OKX 超时，必须走代理。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trade_runtime.ingestion.okx_rest import OkxRestMarketClient
from trade_runtime.runtime_inputs import RuntimeInputAssembler


class _FakeClient(OkxRestMarketClient):
    """只替换网络层，其余逻辑（面值换算、字段拼装）走真实实现。"""

    def __init__(self, instruments, orders):
        super().__init__(timeout=1, proxy_url="socks5h://user:pw@127.0.0.1:1")
        self._instruments = instruments
        self._orders = orders
        self.calls = 0

    def _get(self, path, params):
        if path.endswith('/instruments'):
            return {"code": "0", "data": self._instruments}
        self.calls += 1
        return {"code": "0", "data": self._orders}


INSTRUMENTS = [
    {"instId": "SOL-USDT-SWAP", "ctVal": "1"},
    {"instId": "DOGE-USDT-SWAP", "ctVal": "1000"},
    {"instId": "BNB-USDT-SWAP", "ctVal": "0.01"},
]


def _orders(rows):
    return [{"details": [
        {"bkPx": px, "sz": sz, "side": side, "ts": str(ts)} for px, sz, side, ts in rows
    ]}]


def test_contract_value_is_applied_to_notional():
    """sz 是合约张数不是币量，各标的面值差到十万倍。

    直接拿 sz*price 当名义额，DOGE 会被低估 1000 倍（250000 的阈值永远触发
    不了），BNB 会被高估 100 倍（疯狂误触发）。
    """
    client = _FakeClient(INSTRUMENTS, _orders([("0.09", "10", "SELL", 1788500000000)]))
    events = client.fetch_liquidations("DOGEUSDT")
    assert len(events) == 1
    # 10 张 × 面值 1000 DOGE × 0.09 = 900 USDT，而不是 10 × 0.09 = 0.9
    assert events[0]["quantity"] == pytest.approx(10_000.0)
    assert events[0]["notionalUsd"] == pytest.approx(900.0)


def test_event_shape_matches_what_the_aggregator_reads():
    """下游 _liquidation_notional_sum 只认 event_type=liquidation + notionalUsd。"""
    client = _FakeClient(INSTRUMENTS, _orders([("103.4", "5", "SELL", 1788500000000)]))
    event = client.fetch_liquidations("SOLUSDT")[0]
    assert event["event_type"] == "liquidation"
    assert event["symbol"] == "SOLUSDT"
    assert event["exchange"] == "okx"
    assert event["side"] == "SELL"
    assert event["notionalUsd"] == pytest.approx(517.0)


def test_no_events_when_contract_value_is_unknown():
    """拿不到面值就不发事件——宁可这一维度继续为空，也不要发一个量级
    错掉几个数量级的名义额去驱动阈值判定。"""
    client = _FakeClient([], _orders([("103.4", "5", "SELL", 1788500000000)]))
    assert client.fetch_liquidations("SOLUSDT") == []


def _assembler(clock):
    a = RuntimeInputAssembler.__new__(RuntimeInputAssembler)
    a._okx_liquidation_client = None
    a._okx_liquidation_fetched_at = {}
    a._okx_liquidation_seen = {}
    a.current_time_supplier = lambda: clock[0]
    return a


def test_repeated_liquidations_are_not_counted_twice(monkeypatch):
    """接口每次返回最近 N 笔，不去重的话 15m/60m/240m 三个聚合窗口会把
    同一批爆仓反复累加。新闻源上刚踩过同一个坑。"""
    monkeypatch.setenv("OKX_PROXY_URL", "socks5h://user:pw@127.0.0.1:1")
    clock = [datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)]
    a = _assembler(clock)
    a._okx_liquidation_client = _FakeClient(
        INSTRUMENTS, _orders([("103.4", "5", "SELL", 1788500000000)]))

    assert len(a._okx_liquidation_events("SOLUSDT")) == 1
    # 节流窗口内不再请求
    assert a._okx_liquidation_events("SOLUSDT") == []
    # 窗口过后仍是同一批数据 -> 不该再产生事件
    clock[0] += timedelta(seconds=61)
    assert a._okx_liquidation_events("SOLUSDT") == []


def test_stock_perps_are_skipped(monkeypatch):
    """NVDA/MU 这些股票永续是币安独有的，OKX 没有对应合约。"""
    monkeypatch.setenv("OKX_PROXY_URL", "socks5h://user:pw@127.0.0.1:1")
    clock = [datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)]
    assert _assembler(clock)._okx_liquidation_events("NVDAUSDT") == []


def test_disabled_without_a_proxy(monkeypatch):
    """本机直连 OKX 超时，没配代理就该安静地什么都不做。"""
    monkeypatch.delenv("OKX_PROXY_URL", raising=False)
    clock = [datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)]
    assert _assembler(clock)._okx_liquidation_events("SOLUSDT") == []


def test_upstream_failure_does_not_break_the_market_path(monkeypatch):
    monkeypatch.setenv("OKX_PROXY_URL", "socks5h://user:pw@127.0.0.1:1")
    clock = [datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)]
    a = _assembler(clock)

    class _Boom(_FakeClient):
        def _get(self, path, params):
            raise RuntimeError("proxy down")

    a._okx_liquidation_client = _Boom(INSTRUMENTS, [])
    assert a._okx_liquidation_events("SOLUSDT") == []
