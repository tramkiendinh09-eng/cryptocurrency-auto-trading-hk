"""Binance USD-M futures REST client for the derivative signals.

Why this exists
---------------
mark_price, funding_rate and liquidation events were only ever produced by
``binance_ws``. ``BinancePublicMarketFeed`` — the REST path the runtime falls
back to — returned nothing but last price and quote volume, and open interest
had no Binance producer at all.

That leaves a large part of the market trigger surface permanently inert
whenever the websocket is unavailable: ``fundingRateAbs``,
``markPriceDeviationPct`` and every open-interest signal have thresholds and
evaluation code, but never any data to evaluate. The gating then runs on price
change and klines alone, which is exactly the information that says least about
crowded positioning.

Every endpoint used here is public and unauthenticated.

A note on liquidations
----------------------
Exchange-reported liquidations come from the ``!forceOrder@arr`` websocket
stream; ``/fapi/v1/forceOrders`` is USER_DATA and only reports *your own*
liquidations. There is no public REST source for market-wide liquidations, so
this module does not synthesise ``liquidation`` events. It reports open interest
instead, which is the observable that actually moves during a deleveraging
cascade, and leaves it labelled as what it is.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def normalize_binance_symbol(symbol: str) -> str:
    return str(symbol or "").replace("/", "").replace("-", "").strip().upper()


class BinanceRestMarketClient:
    def __init__(self, *, base_url: str = "https://fapi.binance.com", timeout: int = 5):
        self.base_url = str(base_url or "https://fapi.binance.com").rstrip("/")
        self.timeout = int(timeout or 5)

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        response = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_binance_symbol(symbol)
        payload = self._get("/fapi/v1/ticker/24hr", {"symbol": normalized})
        if not isinstance(payload, dict):
            raise ValueError("binance_ticker_unexpected_payload")
        return {
            "event_type": "market_tick",
            "symbol": str(payload.get("symbol") or normalized),
            "exchange": "binance",
            "price": _safe_float(payload.get("lastPrice")),
            "volume": _safe_float(payload.get("volume")),
            "quote_volume": _safe_float(payload.get("quoteVolume")),
            "price_change_pct": _safe_float(payload.get("priceChangePercent")),
            "event_time": str(payload.get("closeTime") or ""),
        }

    def fetch_premium_index(self, symbol: str) -> list[dict[str, Any]]:
        """mark price + funding rate, in one call.

        /fapi/v1/premiumIndex carries both, so the two events that the mark_price
        websocket stream used to emit together stay together here as well.
        """
        normalized = normalize_binance_symbol(symbol)
        payload = self._get("/fapi/v1/premiumIndex", {"symbol": normalized})
        if not isinstance(payload, dict):
            return []
        event_time = str(payload.get("time") or "")
        events: list[dict[str, Any]] = []
        mark_price = _safe_float(payload.get("markPrice"))
        index_price = _safe_float(payload.get("indexPrice"))
        if mark_price > 0:
            event: dict[str, Any] = {
                "event_type": "mark_price",
                "symbol": normalized,
                "exchange": "binance",
                "price": mark_price,
                "event_time": event_time,
            }
            if index_price > 0:
                event["index_price"] = index_price
                # The trigger computes its own deviation from the tick price;
                # this is the mark-vs-index basis, which is a different thing.
                event["mark_index_basis_pct"] = round((mark_price - index_price) / index_price * 100.0, 6)
            events.append(event)
        funding_rate = payload.get("lastFundingRate")
        if funding_rate not in (None, ""):
            events.append(
                {
                    "event_type": "funding_rate",
                    "symbol": normalized,
                    "exchange": "binance",
                    "funding_rate": _safe_float(funding_rate),
                    "next_funding_time": str(payload.get("nextFundingTime") or ""),
                    "event_time": event_time,
                }
            )
        return events

    def fetch_open_interest(self, symbol: str, *, mark_price: float = 0.0) -> dict[str, Any]:
        normalized = normalize_binance_symbol(symbol)
        payload = self._get("/fapi/v1/openInterest", {"symbol": normalized})
        if not isinstance(payload, dict):
            return {}
        open_interest = _safe_float(payload.get("openInterest"))
        if open_interest <= 0:
            return {}
        event = {
            "event_type": "open_interest",
            "symbol": normalized,
            "exchange": "binance",
            "open_interest": open_interest,
            "event_time": str(payload.get("time") or ""),
        }
        # openInterest is denominated in contracts; the USD notional is what the
        # size-based thresholds are written against.
        if mark_price > 0:
            event["open_interest_notional_usd"] = round(open_interest * mark_price, 2)
        return event

    # --- single-event accessors -------------------------------------------
    # RuntimeInputAssembler._enhanced_market_events calls fetch_mark_price /
    # fetch_funding_rate / fetch_open_interest / fetch_candles duck-typed on
    # whichever REST client it holds. These mirror OkxRestMarketClient so the
    # same enhancement path works for Binance.

    def fetch_mark_price(self, symbol: str) -> dict[str, Any]:
        for event in self.fetch_premium_index(symbol):
            if event.get("event_type") == "mark_price":
                return event
        return {}

    def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        for event in self.fetch_premium_index(symbol):
            if event.get("event_type") == "funding_rate":
                return event
        return {}

    def fetch_candles(self, symbol: str, *, interval: str = "1m", limit: int = 120) -> list[dict[str, Any]]:
        normalized = normalize_binance_symbol(symbol)
        payload = self._get(
            "/fapi/v1/klines",
            {"symbol": normalized, "interval": interval, "limit": max(1, int(limit or 120))},
        )
        if not isinstance(payload, list):
            return []
        candles: list[dict[str, Any]] = []
        for row in payload:
            # [openTime, open, high, low, close, volume, closeTime,
            #  quoteAssetVolume, trades, takerBuyBase, takerBuyQuote, ignore]
            if not isinstance(row, list) or len(row) < 8:
                continue
            candles.append(
                {
                    "event_type": "market_kline",
                    "symbol": normalized,
                    "exchange": "binance",
                    "interval": interval,
                    "open_time": str(row[0] or ""),
                    "close_time": str(row[6] or ""),
                    "open": _safe_float(row[1]),
                    "high": _safe_float(row[2]),
                    "low": _safe_float(row[3]),
                    "close": _safe_float(row[4]),
                    "volume": _safe_float(row[5]),
                    "quote_volume": _safe_float(row[7]),
                    "event_time": str(row[0] or ""),
                }
            )
        return candles

    def fetch_open_interest_change_pct(self, symbol: str, *, period: str = "5m", limit: int = 4) -> float:
        """Percentage change in open-interest notional over the sampled window.

        A sharp fall means positions are being closed — the observable side of a
        deleveraging cascade. Returns 0.0 when the series is unusable, so callers
        can treat "no signal" and "no data" the same way.
        """
        normalized = normalize_binance_symbol(symbol)
        payload = self._get(
            "/futures/data/openInterestHist",
            {"symbol": normalized, "period": period, "limit": max(2, int(limit or 4))},
        )
        if not isinstance(payload, list) or len(payload) < 2:
            return 0.0
        rows = [row for row in payload if isinstance(row, dict)]
        if len(rows) < 2:
            return 0.0
        first = _safe_float(rows[0].get("sumOpenInterestValue"))
        last = _safe_float(rows[-1].get("sumOpenInterestValue"))
        if first <= 0:
            return 0.0
        return round((last - first) / first * 100.0, 6)


class BinanceFuturesRestFeed:
    """REST replacement for the websocket market feed.

    Returns the payload shape ``BinanceMarketMessageParser`` expects, with the
    derivative events attached under ``_market_events`` — the same key
    ``runtime_inputs._supplemental_market_events`` reads for the websocket path,
    so nothing downstream needs to know which transport produced them.
    """

    def __init__(
        self,
        *,
        timeout: int = 5,
        derivative_min_refresh_seconds: float = 30.0,
        client: BinanceRestMarketClient | None = None,
        time_fn=time.monotonic,
    ):
        self.client = client or BinanceRestMarketClient(timeout=timeout)
        # Funding settles every 8h and open interest updates about once a minute,
        # so re-fetching them on every poll only spends rate-limit weight.
        self.derivative_min_refresh_seconds = float(derivative_min_refresh_seconds)
        self.time_fn = time_fn
        self._derivative_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    def _derivative_events(self, symbol: str) -> list[dict[str, Any]]:
        now = self.time_fn()
        cached = self._derivative_cache.get(symbol)
        if cached is not None and (now - cached[0]) < self.derivative_min_refresh_seconds:
            return [dict(item) for item in cached[1]]

        events: list[dict[str, Any]] = []
        mark_price = 0.0
        # Each source is fetched independently: a derivative endpoint failing must
        # never cost us the price tick, which is what keeps the source healthy.
        try:
            premium_events = self.client.fetch_premium_index(symbol)
            events.extend(premium_events)
            for event in premium_events:
                if event.get("event_type") == "mark_price":
                    mark_price = _safe_float(event.get("price"))
        except Exception as exc:
            logger.warning("binance premiumIndex fetch failed symbol=%s error=%s", symbol, exc.__class__.__name__)
        try:
            oi_event = self.client.fetch_open_interest(symbol, mark_price=mark_price)
            if oi_event:
                try:
                    change_pct = self.client.fetch_open_interest_change_pct(symbol)
                    if change_pct:
                        oi_event["open_interest_change_pct"] = change_pct
                except Exception as exc:
                    logger.warning(
                        "binance openInterestHist fetch failed symbol=%s error=%s", symbol, exc.__class__.__name__
                    )
                events.append(oi_event)
        except Exception as exc:
            logger.warning("binance openInterest fetch failed symbol=%s error=%s", symbol, exc.__class__.__name__)

        if events:
            self._derivative_cache[symbol] = (now, [dict(item) for item in events])
        return events

    def fetch(self, symbol: str) -> dict[str, Any]:
        ticker = self.client.fetch_ticker(symbol)
        payload: dict[str, Any] = {
            "s": ticker["symbol"],
            "c": ticker["price"],
            "q": ticker["quote_volume"],
        }
        derivative_events = self._derivative_events(symbol)
        if derivative_events:
            payload["_market_events"] = derivative_events
        return payload
