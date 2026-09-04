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
    """OKX 公开行情。

    ``proxy_url`` 是必需的运维参数而不是可选优化：本机直连 www.okx.com 与
    aws.okx.com 均超时（实测 25s），走 SOCKS5 后 297ms 返回 200。币安不要走
    代理——直连 170ms、走代理 470ms，加了只会更慢。
    """

    def __init__(
        self,
        *,
        base_url: str = "https://www.okx.com",
        timeout: int = 5,
        proxy_url: str = "",
    ):
        self.base_url = str(base_url or "https://www.okx.com").rstrip("/")
        self.timeout = int(timeout or 5)
        normalized_proxy = str(proxy_url or "").strip()
        self.proxies = (
            {"http": normalized_proxy, "https": normalized_proxy} if normalized_proxy else None
        )
        # instId -> ctVal。合约面值，取一次就够，不会变。
        self._contract_values: dict[str, float] = {}

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _first_data_item(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = self._get(path, params)
        data = payload.get("data")
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            raise ValueError(f"okx_empty_data:{path}")
        return data[0]

    def contract_value(self, inst_id: str) -> float:
        """一张合约代表多少个币（ctVal）。

        这个数不能省。OKX 永续的 ``sz`` 是**合约张数**不是币量，各标的面值
        差到十万倍：ETH 0.1、SOL 1、XRP 100、DOGE 1000、BNB 0.01。直接拿
        ``sz * price`` 当名义额，DOGE 会被低估 1000 倍（阈值永远触发不了）、
        BNB 会被高估 100 倍（疯狂误触发）。
        """
        normalized = str(inst_id or "").strip().upper()
        if not normalized:
            return 0.0
        if normalized in self._contract_values:
            return self._contract_values[normalized]
        payload = self._get("/api/v5/public/instruments", {"instType": "SWAP"})
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("instId") or "").strip().upper()
            value = _safe_float(item.get("ctVal"))
            if key and value > 0:
                self._contract_values[key] = value
        return self._contract_values.get(normalized, 0.0)

    def fetch_liquidations(self, symbol: str, *, limit: int = 100) -> list[dict[str, Any]]:
        """全市场爆仓单。

        这条一直是空的：币安的 forceOrders 是 USER_DATA，公开 REST 拿不到
        全市场爆仓，所以 liquidationNotionalUsd 这道阈值（250000）从部署至今
        没有过任何数据，爆仓聚合窗口恒为 0。OKX 的这个接口是公开的。
        """
        inst_id = format_okx_inst_id(symbol)
        underlying = "-".join(inst_id.split("-")[:2])
        payload = self._get(
            "/api/v5/public/liquidation-orders",
            {
                "instType": "SWAP",
                "state": "filled",
                "uly": underlying,
                "limit": int(limit or 100),
            },
        )
        ct_val = self.contract_value(inst_id)
        if ct_val <= 0:
            # 拿不到面值就不发事件：宁可这一维度继续为空，也不要发一个
            # 量级错掉几个数量级的名义额去驱动阈值判定。
            return []
        normalized_symbol = normalize_okx_symbol(inst_id)
        events: list[dict[str, Any]] = []
        for row in payload.get("data") or []:
            if not isinstance(row, dict):
                continue
            for detail in row.get("details") or []:
                if not isinstance(detail, dict):
                    continue
                price = _safe_float(detail.get("bkPx"))
                size = _safe_float(detail.get("sz"))
                if price <= 0 or size <= 0:
                    continue
                quantity = size * ct_val
                event = {
                    "event_type": "liquidation",
                    "symbol": normalized_symbol,
                    "exchange": "okx",
                    "price": price,
                    "quantity": quantity,
                    "notionalUsd": round(price * quantity, 4),
                }
                side = str(detail.get("side") or "").strip().upper()
                if side:
                    event["side"] = side
                timestamp = detail.get("ts")
                if timestamp not in (None, ""):
                    event["event_time_ms"] = int(_safe_float(timestamp))
                events.append(event)
        return events

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
