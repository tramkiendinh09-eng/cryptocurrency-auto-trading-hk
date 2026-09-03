"""Exchange symbol filters (LOT_SIZE / MIN_NOTIONAL) for Binance USD-M futures.

Why this exists
---------------
The execution clients size an order as ``round(quote / price, 8)`` and send it
straight to ``/fapi/v1/order``. Binance rejects anything that is not a multiple
of the symbol's ``stepSize`` or whose notional falls under ``minNotional``, so
the first real order on a fresh account fails with an opaque ``-1111 Precision
is over the maximum defined for this asset`` or ``-4164 Order's notional must be
no smaller than X``.

None of this shows up in paper mode, because paper never talks to the exchange.

The numbers matter a great deal on a small account. As of this writing:

    symbol      stepSize   minQty    minNotional
    BTCUSDT     0.001      0.001     50 USDT
    ETHUSDT     0.001      0.001     20 USDT
    SOLUSDT     0.01       0.01       5 USDT

A 20 USDT account running the default ``maxPositionRatio`` of 0.40 asks for an
8 USDT position, which is under the BTC and ETH minimums — every such order is
rejected by the venue. Refusing locally, with a reason, beats discovering that
from an exchange error code.

Rounding is always **down** to the step. Rounding up would place more risk than
the supervisor asked for, and "slightly too small" is a recoverable outcome in a
way that "silently larger than intended" is not.

The one wrinkle is that the caller divides ``quote / price`` in binary floating
point before this module ever sees the number, and that division lands one ULP
*below* the exact value whenever the answer is a clean step multiple:
``5.0325 / 100.65`` is ``0.049999999999999996``, not ``0.05``. Rounding that
down costs a whole step — 0.05 SOL becomes 0.04, a fifth of the position, for no
reason anyone can see. So a ratio sitting within a hair of a step boundary is
snapped back onto it before the round-down. That is not rounding up: the
tolerance is far too small to promote a size anybody deliberately asked for.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal, InvalidOperation
from typing import Any

import requests

logger = logging.getLogger(__name__)

#: 判定"这个比值其实就是整数倍"的相对容差。取 1e-9 是因为它比 float
#: 往返误差（约 1e-16 相对）大了七个数量级，又远小于任何有意义的下单量
#: 差异——不可能把谁真正想要的仓位放大一个步进。
_STEP_SNAP_TOLERANCE = Decimal("1e-9")

_DEFAULT_BASE_URL = "https://fapi.binance.com"
_TESTNET_BASE_URL = "https://demo-fapi.binance.com"


@dataclass(frozen=True)
class SymbolFilter:
    symbol: str
    step_size: Decimal
    min_qty: Decimal
    max_qty: Decimal
    min_notional: Decimal
    quantity_precision: int

    def quantize(self, quantity: Decimal) -> Decimal:
        """Snap down to the venue's step size.

        Representation error from the caller's float division is corrected
        first — see the module docstring — otherwise a quantity that is exactly
        a step multiple loses an entire step.
        """
        if self.step_size <= 0:
            return quantity
        ratio = quantity / self.step_size
        nearest = ratio.to_integral_value(rounding=ROUND_HALF_UP)
        if nearest > 0 and abs(ratio - nearest) <= _STEP_SNAP_TOLERANCE * nearest:
            ratio = nearest
        steps = ratio.to_integral_value(rounding=ROUND_DOWN)
        return steps * self.step_size

    def _round_up_to_step(self, quantity: Decimal) -> Decimal:
        if self.step_size <= 0:
            return quantity
        steps = (quantity / self.step_size).to_integral_value(rounding=ROUND_UP)
        return steps * self.step_size

    def min_tradable_notional(self, price: Any) -> Decimal:
        """The smallest notional this venue actually accepts at ``price``.

        ``resolve_quantity`` answers "may I send this size?"; sizing needs the
        inverse — "what is the smallest size worth sending?" — and there is no
        single answer across symbols. Three constraints stack: the quantity has
        to be a whole number of ``step_size``, no smaller than ``min_qty``, and
        worth at least ``min_notional``. Whichever binds hardest wins, and which
        one that is changes per symbol: ETHUSDT is held up by its 20 USDT
        ``min_notional`` while BTCUSDT is held up by a 0.001 step worth far more
        than its 50 USDT minimum.

        Returns 0 ("no opinion") when the price is unusable.
        """
        px = _to_decimal(price)
        if px <= 0:
            return Decimal("0")
        quantity = self.min_qty if self.min_qty > 0 else self.step_size
        if self.min_notional > 0:
            quantity = max(quantity, self._round_up_to_step(self.min_notional / px))
        quantity = self._round_up_to_step(quantity)
        if quantity <= 0:
            return Decimal("0")
        return quantity * px

    def notional_step(self, price: Any) -> Decimal:
        """What one ``step_size`` is worth — the granularity of any order.

        Fills round **down** to a step, so on a small account this is not a
        rounding detail: a 12 USDT BNBUSDT order became a 7.01 USDT position
        because 0.017 BNB truncated to 0.01. The model can avoid most of that
        waste, but only if it is told the step exists.
        """
        px = _to_decimal(price)
        if px <= 0 or self.step_size <= 0:
            return Decimal("0")
        return self.step_size * px


@dataclass(frozen=True)
class QuantityDecision:
    """Outcome of applying the venue filters to a requested size."""

    quantity: float
    accepted: bool
    reason: str = ""
    notional: float = 0.0

    @property
    def rejected(self) -> bool:
        return not self.accepted


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


class BinanceSymbolFilters:
    """Caches ``/fapi/v1/exchangeInfo`` and applies the filters to an order size.

    exchangeInfo is a large, rarely-changing document, so it is fetched once and
    reused for ``ttl_seconds``. A refresh failure keeps the previous snapshot:
    stale filters are far better than blocking the order path on a transient
    network error.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        testnet: bool = False,
        timeout: int = 10,
        ttl_seconds: float = 3600.0,
        time_fn=time.monotonic,
    ):
        self.base_url = (base_url or (_TESTNET_BASE_URL if testnet else _DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = int(timeout or 10)
        self.ttl_seconds = float(ttl_seconds)
        self.time_fn = time_fn
        self._filters: dict[str, SymbolFilter] = {}
        self._fetched_at: float | None = None
        self._lock = threading.Lock()

    # -- loading ---------------------------------------------------------

    def _fetch(self) -> dict[str, SymbolFilter]:
        response = requests.get(f"{self.base_url}/fapi/v1/exchangeInfo", timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        symbols = payload.get("symbols") if isinstance(payload, dict) else None
        if not isinstance(symbols, list):
            raise ValueError("binance_exchange_info_unexpected_payload")
        parsed: dict[str, SymbolFilter] = {}
        for entry in symbols:
            if not isinstance(entry, dict):
                continue
            symbol = str(entry.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            by_type = {
                str(item.get("filterType")): item
                for item in entry.get("filters", [])
                if isinstance(item, dict)
            }
            lot = by_type.get("LOT_SIZE") or by_type.get("MARKET_LOT_SIZE") or {}
            notional = by_type.get("MIN_NOTIONAL") or {}
            parsed[symbol] = SymbolFilter(
                symbol=symbol,
                step_size=_to_decimal(lot.get("stepSize"), "0"),
                min_qty=_to_decimal(lot.get("minQty"), "0"),
                max_qty=_to_decimal(lot.get("maxQty"), "0"),
                min_notional=_to_decimal(notional.get("notional"), "0"),
                quantity_precision=int(entry.get("quantityPrecision") or 8),
            )
        return parsed

    def _ensure_loaded(self, *, force: bool = False) -> None:
        with self._lock:
            fresh = (
                self._fetched_at is not None
                and (self.time_fn() - self._fetched_at) < self.ttl_seconds
            )
            if self._filters and fresh and not force:
                return
            try:
                self._filters = self._fetch()
                self._fetched_at = self.time_fn()
            except Exception as exc:
                # Keep whatever we already had; an expired cache still describes
                # the venue far better than no filter at all.
                logger.warning("binance exchangeInfo refresh failed error=%s", exc.__class__.__name__)
                if not self._filters:
                    raise

    def get(self, symbol: str) -> SymbolFilter | None:
        normalized = str(symbol or "").strip().upper()
        if not normalized:
            return None
        try:
            self._ensure_loaded()
        except Exception:
            return None
        found = self._filters.get(normalized)
        if found is None and self._filters:
            # A newly listed symbol: one forced refresh before giving up.
            try:
                self._ensure_loaded(force=True)
            except Exception:
                return None
            found = self._filters.get(normalized)
        return found

    # -- application -----------------------------------------------------

    def resolve_quantity(self, symbol: str, quantity: float, price: float) -> QuantityDecision:
        """Snap a requested quantity onto the venue's grid.

        Returns ``accepted=False`` with a reason when the order cannot legally be
        placed, so the caller can record a skip instead of firing a doomed
        request at the exchange.
        """
        requested = _to_decimal(quantity)
        px = _to_decimal(price)
        if requested <= 0:
            return QuantityDecision(0.0, False, "quantity_not_positive")

        spec = self.get(symbol)
        if spec is None:
            # Unknown symbol: pass the request through untouched rather than
            # inventing a constraint. The venue remains the authority.
            logger.warning("no exchange filter for symbol=%s; sending unadjusted", symbol)
            return QuantityDecision(float(requested), True, "filters_unavailable", float(requested * px))

        adjusted = spec.quantize(requested)
        if spec.max_qty > 0 and adjusted > spec.max_qty:
            adjusted = spec.quantize(spec.max_qty)

        if adjusted <= 0:
            return QuantityDecision(
                0.0,
                False,
                f"below_step_size:requested={requested} step={spec.step_size}",
            )
        if spec.min_qty > 0 and adjusted < spec.min_qty:
            return QuantityDecision(
                float(adjusted),
                False,
                f"below_min_qty:adjusted={adjusted} min={spec.min_qty}",
            )

        notional = adjusted * px if px > 0 else Decimal("0")
        if spec.min_notional > 0 and px > 0 and notional < spec.min_notional:
            return QuantityDecision(
                float(adjusted),
                False,
                f"below_min_notional:notional={notional:.4f} min={spec.min_notional}",
                float(notional),
            )

        return QuantityDecision(float(adjusted), True, "", float(notional))

    def format_quantity(self, symbol: str, quantity: float) -> str:
        """Render a quantity without scientific notation or trailing noise."""
        spec = self.get(symbol)
        value = _to_decimal(quantity)
        if spec is not None and spec.step_size > 0:
            exponent = spec.step_size.normalize().as_tuple().exponent
            decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
            return f"{value:.{decimals}f}"
        return f"{value:.8f}".rstrip("0").rstrip(".")


_shared_filters: dict[str, BinanceSymbolFilters] = {}
_shared_lock = threading.Lock()


def shared_binance_filters(*, testnet: bool = False) -> BinanceSymbolFilters:
    """Process-wide cache so every client shares one exchangeInfo snapshot."""
    key = "testnet" if testnet else "live"
    with _shared_lock:
        instance = _shared_filters.get(key)
        if instance is None:
            instance = BinanceSymbolFilters(testnet=testnet)
            _shared_filters[key] = instance
        return instance
