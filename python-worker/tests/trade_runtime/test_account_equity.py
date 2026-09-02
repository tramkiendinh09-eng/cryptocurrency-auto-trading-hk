"""Equity must come from the venue, not from the control plane's placeholder.

DEFAULT_ACCOUNT_EQUITY is 10000 USDT and only a pnl_snapshot replaces it, so an
account that has never filled an order sizes every position off 10000 no matter
what it actually holds.
"""

import pytest

from trade_runtime.account_equity import AccountEquitySync


class _Balance:
    def __init__(self, equity=20.0, unrealized=0.0, boom=False):
        self.equity = equity
        self.unrealized = unrealized
        self.boom = boom
        self.calls = 0

    def get_balance(self):
        self.calls += 1
        if self.boom:
            raise RuntimeError("-2015 invalid API key")
        return {
            "total_equity": self.equity,
            "available_balance": self.equity,
            "total_unrealized_profit": self.unrealized,
            "currency": "USDT",
        }


class _Router:
    def __init__(self, binance=None, okx=None):
        self.binance_client = binance
        self.okx_client = okx


class _Callback:
    def __init__(self, boom=False):
        self.snapshots = []
        self.boom = boom

    def post_pnl_snapshot(self, payload):
        if self.boom:
            raise RuntimeError("backend down")
        self.snapshots.append(payload)


def _sync(**overrides):
    clock = overrides.pop("clock", {"now": 0.0})
    return AccountEquitySync(
        interval_seconds=overrides.pop("interval_seconds", 60.0),
        time_fn=lambda: clock["now"],
    ), clock


def test_publishes_real_equity_in_live_mode():
    syncer, _ = _sync()
    client = _Balance(equity=20.0, unrealized=-0.35)
    callback = _Callback()

    result = syncer.sync(
        execution_router=_Router(binance=client),
        callback_client=callback,
        mode="live",
        exchange="binance",
        trace_id="t-1",
    )

    assert result is not None
    assert len(callback.snapshots) == 1
    snapshot = callback.snapshots[0]
    assert snapshot["accountEquity"] == pytest.approx(20.0)
    assert snapshot["unrealizedPnl"] == pytest.approx(-0.35)
    assert snapshot["mode"] == "live"
    assert snapshot["traceId"] == "t-1"


def test_paper_mode_is_never_synced():
    """Paper has no real account; mixing a live balance into it would lie."""
    syncer, _ = _sync()
    client = _Balance()
    callback = _Callback()

    assert (
        syncer.sync(
            execution_router=_Router(binance=client),
            callback_client=callback,
            mode="paper",
            exchange="binance",
        )
        is None
    )
    assert client.calls == 0
    assert callback.snapshots == []


def test_shadow_mode_is_synced():
    syncer, _ = _sync()
    client = _Balance()
    callback = _Callback()

    syncer.sync(
        execution_router=_Router(binance=client),
        callback_client=callback,
        mode="shadow",
        exchange="binance",
    )
    assert len(callback.snapshots) == 1


def test_sync_is_throttled():
    """Balance moves slowly next to a 15 second poll."""
    syncer, clock = _sync(interval_seconds=60.0)
    client = _Balance()
    callback = _Callback()
    router = _Router(binance=client)

    for _ in range(5):
        clock["now"] += 5.0
        syncer.sync(execution_router=router, callback_client=callback, mode="live", exchange="binance")
    assert client.calls == 1

    clock["now"] += 120.0
    syncer.sync(execution_router=router, callback_client=callback, mode="live", exchange="binance")
    assert client.calls == 2


def test_force_bypasses_throttle():
    syncer, _ = _sync()
    client = _Balance()
    callback = _Callback()
    router = _Router(binance=client)

    syncer.sync(execution_router=router, callback_client=callback, mode="live", exchange="binance")
    syncer.sync(execution_router=router, callback_client=callback, mode="live", exchange="binance", force=True)
    assert client.calls == 2


def test_balance_failure_does_not_raise_and_backs_off():
    """An unreachable balance endpoint must not stop signal evaluation."""
    syncer, clock = _sync(interval_seconds=60.0)
    client = _Balance(boom=True)
    callback = _Callback()
    router = _Router(binance=client)

    assert syncer.sync(execution_router=router, callback_client=callback, mode="live", exchange="binance") is None
    clock["now"] += 5.0
    syncer.sync(execution_router=router, callback_client=callback, mode="live", exchange="binance")
    # the failed attempt still counts against the interval
    assert client.calls == 1
    assert callback.snapshots == []


def test_non_positive_equity_is_not_published():
    """Zero reads as a permissions problem, not an empty account."""
    syncer, _ = _sync()
    callback = _Callback()

    syncer.sync(
        execution_router=_Router(binance=_Balance(equity=0.0)),
        callback_client=callback,
        mode="live",
        exchange="binance",
    )
    assert callback.snapshots == []


def test_missing_balance_endpoint_is_skipped():
    class _NoBalance:
        pass

    syncer, _ = _sync()
    callback = _Callback()
    assert (
        syncer.sync(
            execution_router=_Router(binance=_NoBalance()),
            callback_client=callback,
            mode="live",
            exchange="binance",
        )
        is None
    )


def test_routes_to_the_exchange_in_play():
    syncer, _ = _sync()
    binance, okx = _Balance(equity=20.0), _Balance(equity=99.0)
    callback = _Callback()

    syncer.sync(
        execution_router=_Router(binance=binance, okx=okx),
        callback_client=callback,
        mode="live",
        exchange="okx",
    )
    assert okx.calls == 1
    assert binance.calls == 0
    assert callback.snapshots[0]["accountEquity"] == pytest.approx(99.0)


def test_callback_failure_is_swallowed():
    syncer, _ = _sync()
    assert (
        syncer.sync(
            execution_router=_Router(binance=_Balance()),
            callback_client=_Callback(boom=True),
            mode="live",
            exchange="binance",
        )
        is None
    )
