from __future__ import annotations

import threading
import time

from trade_runtime.route_scheduler import RouteScheduler, RouteSchedulerConfig, RouteTask


def test_route_scheduler_runs_serial_mode_without_overlap():
    lock = threading.Lock()
    observed = {"active": 0, "max_active": 0}

    def execute(symbol):
        with lock:
            observed["active"] += 1
            observed["max_active"] = max(observed["max_active"], observed["active"])
        time.sleep(0.02)
        with lock:
            observed["active"] -= 1
        return {"symbol": symbol}

    scheduler = RouteScheduler(RouteSchedulerConfig(mode="SERIAL", max_concurrency=4))
    results = scheduler.run(
        [
            RouteTask(index=0, symbol="BTCUSDT", exchange="binance", trace_id="trace-1", execute=lambda: execute("BTCUSDT")),
            RouteTask(index=1, symbol="ETHUSDT", exchange="okx", trace_id="trace-2", execute=lambda: execute("ETHUSDT")),
        ]
    )

    assert observed["max_active"] == 1
    assert results == [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}]


def test_route_scheduler_limits_thread_pool_concurrency_to_configured_cap():
    lock = threading.Lock()
    observed = {"active": 0, "max_active": 0}

    def execute(symbol):
        with lock:
            observed["active"] += 1
            observed["max_active"] = max(observed["max_active"], observed["active"])
        time.sleep(0.05)
        with lock:
            observed["active"] -= 1
        return {"symbol": symbol}

    scheduler = RouteScheduler(RouteSchedulerConfig(mode="THREAD_POOL", max_concurrency=2))
    scheduler.run(
        [
            RouteTask(index=0, symbol="BTCUSDT", exchange="binance", trace_id="trace-1", execute=lambda: execute("BTCUSDT")),
            RouteTask(index=1, symbol="ETHUSDT", exchange="okx", trace_id="trace-2", execute=lambda: execute("ETHUSDT")),
            RouteTask(index=2, symbol="SOLUSDT", exchange="binance", trace_id="trace-3", execute=lambda: execute("SOLUSDT")),
        ]
    )

    assert observed["max_active"] == 2


def test_route_scheduler_preserves_input_order_and_captures_route_errors():
    scheduler = RouteScheduler(RouteSchedulerConfig(mode="THREAD_POOL", max_concurrency=3))

    results = scheduler.run(
        [
            RouteTask(
                index=0,
                symbol="BTCUSDT",
                exchange="binance",
                trace_id="trace-1",
                execute=lambda: {"route": "btc"},
            ),
            RouteTask(
                index=1,
                symbol="ETHUSDT",
                exchange="okx",
                trace_id="trace-2",
                execute=lambda: (_ for _ in ()).throw(ValueError("route exploded")),
            ),
            RouteTask(
                index=2,
                symbol="SOLUSDT",
                exchange="binance",
                trace_id="trace-3",
                execute=lambda: {"route": "sol"},
            ),
        ]
    )

    assert results[0] == {"route": "btc"}
    assert results[1] == {
        "status": "error",
        "symbol": "ETHUSDT",
        "exchange": "okx",
        "trace_id": "trace-2",
        "error": "route exploded",
    }
    assert results[2] == {"route": "sol"}
