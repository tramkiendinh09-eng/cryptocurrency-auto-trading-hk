"""Keep the control plane's account equity in step with the venue.

Why this exists
---------------
``TradeRuntimeConfigServiceImpl`` seeds ``accountEquity`` from the constant
``DEFAULT_ACCOUNT_EQUITY = 10000.00`` and only ever replaces it from the latest
``pnl_snapshot`` row. ``pnl_snapshot`` is written after a fill, so an account
that has never traded keeps reporting 10000 USDT forever — and every position
limit is a fraction of that number.

On a 20 USDT account with ``maxPositionRatio`` 0.40 that is the difference
between an 8 USDT position and a 4000 USDT one. Nothing in the tree ever asked
the exchange for a balance: ``OkxRestExecutionClient.get_balance`` existed but
had no callers, and the Binance client had no equivalent at all.

This module closes the loop by posting a pnl snapshot carrying the venue's real
equity, so the next bootstrap reads a true number.

Paper mode is deliberately excluded: there is no real account behind it, and
overwriting the simulated equity with a live balance would silently mix the two.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SYNC_INTERVAL_SECONDS = 60.0

# Modes with a real account behind them.
_REAL_MODES = {"live", "shadow"}


def _client_for(execution_router: Any, exchange: str) -> Any:
    if execution_router is None:
        return None
    normalized = str(exchange or "").strip().lower()
    attribute = "okx_client" if normalized == "okx" else "binance_client"
    return getattr(execution_router, attribute, None)


class AccountEquitySync:
    """Throttled equity refresh.

    Balance is account state that moves slowly relative to the poll interval, so
    this refreshes at most once per ``interval_seconds``. A failure is logged and
    skipped rather than raised: an unreachable balance endpoint must not stop the
    runtime from evaluating signals.
    """

    def __init__(
        self,
        *,
        interval_seconds: float = DEFAULT_SYNC_INTERVAL_SECONDS,
        time_fn=time.monotonic,
    ):
        self.interval_seconds = float(interval_seconds)
        self.time_fn = time_fn
        self._last_sync_at: float | None = None
        self.last_equity: float | None = None

    def _due(self) -> bool:
        if self._last_sync_at is None:
            return True
        return (self.time_fn() - self._last_sync_at) >= self.interval_seconds

    def sync(
        self,
        *,
        execution_router: Any,
        callback_client: Any,
        mode: str,
        exchange: str,
        trace_id: str = "",
        force: bool = False,
    ) -> dict[str, Any] | None:
        """Fetch venue equity and publish it as a pnl snapshot.

        Returns the balance payload when a sync happened, otherwise ``None``.
        """
        normalized_mode = str(mode or "").strip().lower()
        if normalized_mode not in _REAL_MODES:
            return None
        if not force and not self._due():
            return None
        if callback_client is None or not hasattr(callback_client, "post_pnl_snapshot"):
            return None

        client = _client_for(execution_router, exchange)
        get_balance = getattr(client, "get_balance", None)
        if not callable(get_balance):
            logger.debug("no balance endpoint for exchange=%s; equity sync skipped", exchange)
            return None

        try:
            balance = get_balance()
        except Exception as exc:
            # Mark the attempt so a persistently failing venue is not retried on
            # every single poll.
            self._last_sync_at = self.time_fn()
            logger.warning(
                "account equity sync failed exchange=%s error=%s", exchange, exc.__class__.__name__
            )
            return None

        if not isinstance(balance, dict):
            self._last_sync_at = self.time_fn()
            return None

        try:
            equity = float(balance.get("total_equity") or 0.0)
        except (TypeError, ValueError):
            equity = 0.0
        if equity <= 0:
            # A zero balance is far more likely to be a permissions problem than
            # a genuinely empty account; writing it would hand the risk limits a
            # meaningless denominator.
            self._last_sync_at = self.time_fn()
            logger.warning("account equity sync returned non-positive equity exchange=%s", exchange)
            return None

        try:
            unrealized = float(balance.get("total_unrealized_profit") or 0.0)
        except (TypeError, ValueError):
            unrealized = 0.0

        payload = {
            "traceId": trace_id or "",
            "mode": normalized_mode,
            "accountEquity": equity,
            "unrealizedPnl": unrealized,
            "realizedPnl": 0.0,
            "dailyPnl": 0.0,
            "maxDrawdownPct": 0.0,
            "peakAccountEquity": max(equity, self.last_equity or 0.0),
            "source": "venue_balance_sync",
        }
        try:
            callback_client.post_pnl_snapshot(payload)
        except Exception as exc:
            self._last_sync_at = self.time_fn()
            logger.warning("posting equity snapshot failed error=%s", exc.__class__.__name__)
            return None

        self._last_sync_at = self.time_fn()
        if self.last_equity is None or abs(equity - self.last_equity) > 1e-9:
            logger.info(
                "account equity synced exchange=%s mode=%s equity=%.4f unrealized=%.4f",
                exchange,
                normalized_mode,
                equity,
                unrealized,
            )
        self.last_equity = equity
        return balance
