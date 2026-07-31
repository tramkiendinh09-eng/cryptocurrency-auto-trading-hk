from __future__ import annotations

from typing import Any

import requests


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def format_okx_inst_id(symbol: str) -> str:
    normalized = str(symbol or "").replace("/", "").replace("-", "").upper()
    if normalized.endswith("SWAP") and "USDT" in normalized:
        normalized = normalized.replace("SWAP", "")
    if normalized.endswith("USDT") and len(normalized) > 4:
        return f"{normalized[:-4]}-USDT-SWAP"
    if normalized.endswith("USDC") and len(normalized) > 4:
        return f"{normalized[:-4]}-USDC-SWAP"
    return str(symbol or "").strip().upper()


def normalize_okx_symbol(inst_id: str) -> str:
    parts = [part for part in str(inst_id or "").strip().upper().split("-") if part and part != "SWAP"]
    return "".join(parts)


class OkxRestMarketClient:
    def __init__(self, *, base_url: str = "https://www.okx.com", timeout: int = 5):
        self.base_url = str(base_url or "https://www.okx.com").rstrip("/")
        self.timeout = int(timeout or 5)

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _first_data_item(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = self._get(path, params)
        data = payload.get("data")
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            raise ValueError(f"okx_empty_data:{path}")
        return data[0]

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        item = self._first_data_item("/api/v5/market/ticker", {"instId": format_okx_inst_id(symbol)})
        quote_volume = item.get("volCcyQuote24h") or item.get("volCcy24h") or item.get("turnover") or 0.0
        return {
            "event_type": "market_tick",
            "symbol": normalize_okx_symbol(item.get("instId") or format_okx_inst_id(symbol)),
            "exchange": "okx",
            "price": _safe_float(item.get("last")),
            "volume": _safe_float(item.get("vol24h")),
            "quote_volume": _safe_float(quote_volume),
            "event_time": str(item.get("ts") or ""),
        }

    def fetch_mark_price(self, symbol: str) -> dict[str, Any]:
        item = self._first_data_item(
            "/api/v5/public/mark-price",
            {"instType": "SWAP", "instId": format_okx_inst_id(symbol)},
        )
        return {
            "event_type": "mark_price",
            "symbol": normalize_okx_symbol(item.get("instId") or format_okx_inst_id(symbol)),
            "exchange": "okx",
            "price": _safe_float(item.get("markPx") or item.get("mark_price") or item.get("price")),
            "event_time": str(item.get("ts") or ""),
        }

    def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        item = self._first_data_item("/api/v5/public/funding-rate", {"instId": format_okx_inst_id(symbol)})
        return {
            "event_type": "funding_rate",
            "symbol": normalize_okx_symbol(item.get("instId") or format_okx_inst_id(symbol)),
            "exchange": "okx",
            "funding_rate": _safe_float(item.get("fundingRate") or item.get("funding_rate")),
            "event_time": str(item.get("ts") or item.get("fundingTime") or ""),
        }

    def fetch_open_interest(self, symbol: str) -> dict[str, Any]:
        item = self._first_data_item(
            "/api/v5/public/open-interest",
            {"instType": "SWAP", "instId": format_okx_inst_id(symbol)},
        )
        return {
            "event_type": "open_interest",
            "symbol": normalize_okx_symbol(item.get("instId") or format_okx_inst_id(symbol)),
            "exchange": "okx",
            "open_interest": _safe_float(item.get("oi") or item.get("openInterest") or item.get("oiCcy")),
            "event_time": str(item.get("ts") or ""),
        }

    def fetch_candles(self, symbol: str, *, interval: str = "1m", limit: int = 120) -> list[dict[str, Any]]:
        payload = self._get(
            "/api/v5/market/candles",
            {"instId": format_okx_inst_id(symbol), "bar": interval, "limit": int(limit or 120)},
        )
        data = payload.get("data")
        if not isinstance(data, list):
            return []
        events: list[dict[str, Any]] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 6:
                continue
            quote_volume = row[7] if len(row) > 7 else row[6] if len(row) > 6 else 0.0
            events.append(
                {
                    "event_type": "market_kline",
                    "symbol": normalize_okx_symbol(format_okx_inst_id(symbol)),
                    "exchange": "okx",
                    "interval": interval,
                    "open_time": str(row[0] or ""),
                    "close_time": str(row[0] or ""),
                    "open": _safe_float(row[1]),
                    "high": _safe_float(row[2]),
                    "low": _safe_float(row[3]),
                    "close": _safe_float(row[4]),
                    "volume": _safe_float(row[5]),
                    "quote_volume": _safe_float(quote_volume),
                    "event_time": str(row[0] or ""),
                }
            )
        return events
