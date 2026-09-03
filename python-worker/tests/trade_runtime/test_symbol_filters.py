"""Venue filter compliance for Binance USD-M futures orders.

These only matter live: paper mode never reaches the exchange, so a quantity
that violates LOT_SIZE or MIN_NOTIONAL looks perfectly healthy right up until
the first real order is rejected.
"""

from decimal import Decimal

import pytest

from trade_runtime.execution.clients import BinanceRestExecutionClient
from trade_runtime.execution.symbol_filters import BinanceSymbolFilters

EXCHANGE_INFO = {
    "symbols": [
        {
            "symbol": "BTCUSDT",
            "quantityPrecision": 3,
            "filters": [
                {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "1000"},
                {"filterType": "MIN_NOTIONAL", "notional": "50"},
            ],
        },
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


class _InfoStub:
    def __init__(self, payload=None):
        self.calls = 0
        self.payload = EXCHANGE_INFO if payload is None else payload

    def __call__(self, url, timeout=None, **kwargs):
        self.calls += 1
        payload = self.payload

        class _Response:
            def raise_for_status(self):
                return None

            def json(self):
                return payload

        return _Response()


@pytest.fixture
def filters(monkeypatch):
    stub = _InfoStub()
    monkeypatch.setattr("trade_runtime.execution.symbol_filters.requests.get", stub)
    instance = BinanceSymbolFilters()
    instance._stub = stub
    return instance


def test_quantity_rounds_down_to_step_size(filters):
    # 0.0037 BTC on a 0.001 grid becomes 0.003, never 0.004: rounding up would
    # place more risk than the supervisor sized.
    decision = filters.resolve_quantity("BTCUSDT", 0.0037, 77000.0)
    assert decision.accepted
    assert decision.quantity == pytest.approx(0.003)
    assert decision.notional == pytest.approx(231.0)


def test_rejects_quantity_that_rounds_away_entirely(filters):
    """A 20 USDT account asking for an 8 USDT BTC position."""
    decision = filters.resolve_quantity("BTCUSDT", 8.0 / 77000.0, 77000.0)
    assert decision.rejected
    assert decision.quantity == 0.0
    assert "below_step_size" in decision.reason


def test_rejects_notional_below_venue_minimum(filters):
    """ETH survives the step grid but not the 20 USDT notional floor."""
    decision = filters.resolve_quantity("ETHUSDT", 8.0 / 2400.0, 2400.0)
    assert decision.rejected
    assert decision.quantity == pytest.approx(0.003)
    assert "below_min_notional" in decision.reason


def test_accepts_small_order_on_symbol_with_low_minimum(filters):
    """SOL's 5 USDT floor is what makes a 20 USDT account tradable at all."""
    decision = filters.resolve_quantity("SOLUSDT", 8.0 / 99.0, 99.0)
    assert decision.accepted
    assert decision.quantity == pytest.approx(0.08)
    assert decision.notional == pytest.approx(7.92)


def test_clamps_to_max_qty(filters):
    decision = filters.resolve_quantity("BTCUSDT", 5000.0, 77000.0)
    assert decision.accepted
    assert decision.quantity == pytest.approx(1000.0)


def test_unknown_symbol_passes_through_unadjusted(filters):
    """The venue stays the authority; do not invent a constraint."""
    decision = filters.resolve_quantity("DOGEUSDT", 12.5, 0.1)
    assert decision.accepted
    assert decision.quantity == pytest.approx(12.5)
    assert decision.reason == "filters_unavailable"


def test_exchange_info_is_cached(filters):
    for _ in range(5):
        filters.resolve_quantity("BTCUSDT", 0.01, 77000.0)
    # one initial load, plus one forced refresh probing for a missing symbol
    assert filters._stub.calls == 1


def test_stale_cache_survives_refresh_failure(monkeypatch):
    stub = _InfoStub()
    monkeypatch.setattr("trade_runtime.execution.symbol_filters.requests.get", stub)
    clock = {"now": 0.0}
    instance = BinanceSymbolFilters(ttl_seconds=10.0, time_fn=lambda: clock["now"])
    assert instance.resolve_quantity("SOLUSDT", 1.0, 99.0).accepted

    def boom(url, timeout=None, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("trade_runtime.execution.symbol_filters.requests.get", boom)
    clock["now"] = 999.0
    # Expired cache beats no filter: blocking the order path on a transient
    # network error would be worse than using slightly stale step sizes.
    assert instance.resolve_quantity("SOLUSDT", 1.0, 99.0).accepted


def test_format_quantity_uses_step_precision(filters):
    assert filters.format_quantity("SOLUSDT", 0.08) == "0.08"
    assert filters.format_quantity("BTCUSDT", 0.003) == "0.003"
    # no scientific notation reaching the exchange
    assert "e" not in filters.format_quantity("BTCUSDT", 0.000001).lower()


class _RecordingSession:
    def __init__(self, response=None):
        self.headers = {}
        self.requests = []
        self.response = response or {"orderId": 1, "status": "FILLED"}

    def request(self, method, url, params=None, timeout=None, **kwargs):
        self.requests.append({"method": method, "url": url, "params": params})
        payload = self.response

        class _Response:
            def raise_for_status(self):
                return None

            def json(self):
                return payload

        return _Response()


def _client(session, filters):
    return BinanceRestExecutionClient(
        api_key="k",
        api_secret="s",
        session=session,
        symbol_filters=filters,
        timestamp_supplier=lambda: 1700000000000,
    )


def test_place_market_order_rejects_locally_without_calling_exchange(filters):
    session = _RecordingSession()
    client = _client(session, filters)

    result = client.place_market_order(
        {"symbol": "BTCUSDT", "side": "BUY", "price": 77000.0, "quote": 8.0}
    )

    assert result["msg"].startswith("local_filter_rejected:")
    assert "below_step_size" in result["msg"]
    # nothing was sent: an exchange error code is a poor substitute for a reason
    assert session.requests == []


def test_place_market_order_sends_step_aligned_quantity(filters):
    session = _RecordingSession()
    client = _client(session, filters)

    client.place_market_order(
        {"symbol": "SOLUSDT", "side": "BUY", "price": 99.0, "quote": 8.0}
    )

    order_calls = [r for r in session.requests if r["url"].endswith("/fapi/v1/order")]
    assert len(order_calls) == 1
    assert order_calls[0]["params"]["quantity"] == "0.08"


def test_leverage_is_set_once_per_symbol(filters):
    session = _RecordingSession()
    client = _client(session, filters)

    for _ in range(3):
        client.place_market_order(
            {"symbol": "SOLUSDT", "side": "BUY", "price": 99.0, "quote": 8.0, "leverage": 3}
        )

    leverage_calls = [r for r in session.requests if r["url"].endswith("/fapi/v1/leverage")]
    assert len(leverage_calls) == 1
    assert leverage_calls[0]["params"]["leverage"] == 3
    assert leverage_calls[0]["params"]["symbol"] == "SOLUSDT"


def test_order_still_placed_when_leverage_call_fails(filters, monkeypatch):
    """Leverage is account state; the risk gate already bounded the notional."""
    session = _RecordingSession()
    client = _client(session, filters)

    def explode(symbol, leverage):
        raise RuntimeError("-4028 invalid leverage")

    monkeypatch.setattr(client, "set_leverage", explode)
    result = client.place_market_order(
        {"symbol": "SOLUSDT", "side": "BUY", "price": 99.0, "quote": 8.0, "leverage": 125}
    )

    assert result["status"] == "FILLED"


def test_reduce_only_flag_is_forwarded(filters):
    session = _RecordingSession()
    client = _client(session, filters)

    client.place_market_order(
        {"symbol": "SOLUSDT", "side": "SELL", "price": 99.0, "quote": 8.0, "reduce_only": True}
    )

    order_calls = [r for r in session.requests if r["url"].endswith("/fapi/v1/order")]
    assert order_calls[0]["params"]["reduceOnly"] == "true"


# ── leverage ceiling ──────────────────────────────────────────────────────

def test_leverage_hint_is_capped_by_runtime_config():
    """leverage_hint is model output; unbounded it can set 50x on the account."""
    from trade_runtime.decision.nodes.execution_node import _resolve_leverage

    state = {"runtime_config": {"max_leverage": 3}}
    assert _resolve_leverage(state, {"leverage_hint": 50}) == pytest.approx(3.0)
    assert _resolve_leverage(state, {"leverage_hint": 2}) == pytest.approx(2.0)


def test_leverage_falls_back_to_conservative_default():
    """Too little leverage costs a rejected order; too much costs the account."""
    from trade_runtime.decision.nodes.execution_node import (
        DEFAULT_MAX_LEVERAGE,
        _resolve_leverage,
    )

    assert _resolve_leverage({}, {"leverage_hint": 125}) == pytest.approx(DEFAULT_MAX_LEVERAGE)
    assert _resolve_leverage({"runtime_config": {}}, {"leverage_hint": 20}) == pytest.approx(
        DEFAULT_MAX_LEVERAGE
    )


def test_absent_or_invalid_leverage_falls_back_to_the_default():
    """杠杆此前只是发给交易所的一个可选字段，缺省就不带；现在它参与仓位
    计算，"没有杠杆"不再是一个合法状态——缺省即默认 3 倍。"""
    from trade_runtime.decision.nodes.execution_node import (
        DEFAULT_MAX_LEVERAGE,
        _resolve_leverage,
    )

    assert _resolve_leverage({}, {}) == pytest.approx(DEFAULT_MAX_LEVERAGE)
    assert _resolve_leverage({}, {"leverage_hint": 0}) == pytest.approx(DEFAULT_MAX_LEVERAGE)
    assert _resolve_leverage({}, {"leverage_hint": -5}) == pytest.approx(DEFAULT_MAX_LEVERAGE)
    assert _resolve_leverage({}, {"leverage_hint": "abc"}) == pytest.approx(DEFAULT_MAX_LEVERAGE)


# ── trade lifecycle payload contract ──────────────────────────────────────

def test_lifecycle_payload_converts_every_snake_key():
    """A hand-written map had omitted trace_id, so the backend rejected every
    write with "traceId is required" — over HTTP 200, which raise_for_status()
    lets through. The whole reflection loop silently persisted nothing."""
    from trade_runtime.memory.trade_lifecycle import TradeLifecycleClient

    client = TradeLifecycleClient(base_url="http://x", bearer_token="")
    camel = client._to_camel_payload(
        {
            "trace_id": "t1",
            "exchange_code": "binance",
            "entry_price": 99.2,
            "realized_pnl_pct": 1.5,
            "symbol": "SOLUSDT",
            "alreadyCamel": 1,
        }
    )
    assert camel["traceId"] == "t1"
    assert camel["exchangeCode"] == "binance"
    assert camel["entryPrice"] == 99.2
    assert camel["realizedPnlPct"] == 1.5
    assert camel["symbol"] == "SOLUSDT"
    assert camel["alreadyCamel"] == 1
    assert not any("_" in key for key in camel)


def test_lifecycle_datetime_matches_backend_jackson_format():
    """application.yml pins Jackson to `yyyy-MM-dd HH:mm:ss` in GMT+8;
    isoformat() produced microseconds plus an offset and Jackson refused it."""
    from datetime import datetime, timezone

    from trade_runtime.memory.trade_lifecycle import TradeLifecycleClient

    client = TradeLifecycleClient(base_url="http://x", bearer_token="")
    camel = client._to_camel_payload(
        {"entry_time": datetime(2026, 9, 2, 16, 7, 2, 786398, tzinfo=timezone.utc)}
    )
    # UTC 16:07 -> GMT+8 00:07 the next day
    assert camel["entryTime"] == "2026-09-03 00:07:02"


def test_lifecycle_naive_datetime_is_treated_as_utc():
    from datetime import datetime

    from trade_runtime.memory.trade_lifecycle import TradeLifecycleClient

    client = TradeLifecycleClient(base_url="http://x", bearer_token="")
    camel = client._to_camel_payload({"exit_time": datetime(2026, 9, 2, 0, 0, 0)})
    assert camel["exitTime"] == "2026-09-02 08:00:00"


# ── paper fills must obey the same venue rules as live ────────────────────

def _router_with_filters(filters, monkeypatch):
    from trade_runtime.execution import router as router_mod
    monkeypatch.setattr(
        "trade_runtime.execution.symbol_filters.shared_binance_filters",
        lambda testnet=False: filters,
    )
    return router_mod.ExecutionRouter(binance_client=None, okx_client=None)


def test_paper_fill_is_snapped_to_the_venue_grid(filters, monkeypatch):
    """A paper run whose fills the exchange would reject predicts nothing."""
    router = _router_with_filters(filters, monkeypatch)
    result = router.execute(
        mode="paper",
        exchange="binance",
        order={"symbol": "SOLUSDT", "side": "BUY", "price": 99.0, "quote": 8.0},
    )
    assert result["status"] == "filled"
    # 8 / 99 = 0.0808... which the 0.01 grid rounds down to 0.08
    assert result["fill_quantity"] == pytest.approx(0.08)


def test_paper_order_below_venue_minimum_is_skipped(filters, monkeypatch):
    """ETH's 20 USDT floor must stop the simulated fill too, or the paper
    account books trades a real account could never place."""
    router = _router_with_filters(filters, monkeypatch)
    result = router.execute(
        mode="paper",
        exchange="binance",
        order={"symbol": "ETHUSDT", "side": "BUY", "price": 2400.0, "quote": 8.0},
    )
    assert result["status"] == "skipped"
    assert "below_min_notional" in result["reason"]
    assert result["fill_quantity"] == 0.0


def test_paper_fill_unaffected_for_other_venues(filters, monkeypatch):
    router = _router_with_filters(filters, monkeypatch)
    result = router.execute(
        mode="paper",
        exchange="okx",
        order={"symbol": "SOLUSDT", "side": "BUY", "price": 99.0, "quote": 8.0},
    )
    assert result["status"] == "filled"
    assert result["fill_quantity"] > 0
