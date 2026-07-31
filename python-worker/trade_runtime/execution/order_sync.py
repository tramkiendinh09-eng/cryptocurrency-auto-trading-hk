from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


_OKX_ORDER_STATUS_MAP = {
    "live": ("pending", "PENDING"),
    "new": ("pending", "PENDING"),
    "pending": ("pending", "PENDING"),
    "partially_filled": ("partial", "PARTIALLY_FILLED"),
    "filled": ("filled", "FILLED"),
    "canceled": ("canceled", "CANCELED"),
    "cancelled": ("canceled", "CANCELED"),
    "mmp_canceled": ("canceled", "CANCELED"),
    "expired": ("expired", "EXPIRED"),
}


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fee_cost(value: Any) -> float | None:
    fee = _to_float(value)
    if fee is None:
        return None
    return round(-fee, 12)


def _timestamp_ms_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        timestamp_ms = int(float(value))
    except (TypeError, ValueError):
        return None
    if timestamp_ms <= 0:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _raw_payload(item: dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, separators=(",", ":"))


class OkxOrderSyncService:
    def __init__(self, *, okx_client: Any, callback_client: Any):
        self.okx_client = okx_client
        self.callback_client = callback_client

    def sync_once(
        self,
        *,
        symbol: str | None = None,
        mode: str = "live",
        limit: int = 100,
        begin: int | str | None = None,
        end: int | str | None = None,
    ) -> dict[str, Any]:
        normalized_mode = str(mode or "").strip().lower()
        if normalized_mode != "live":
            return {"orders": 0, "fills": 0, "skipped": True}
        if not self._can_sync():
            return {"orders": 0, "fills": 0, "skipped": True}

        orders_payload = self.okx_client.get_order_history(symbol=symbol, limit=limit, begin=begin, end=end)
        fills_payload = self.okx_client.get_fills_history(symbol=symbol, limit=limit, begin=begin, end=end)

        order_count = 0
        for item in self._payload_items(orders_payload):
            payload = self.normalize_order(item, mode=normalized_mode)
            if not payload.get("orderRef"):
                continue
            self.callback_client.post_exchange_order(payload)
            order_count += 1

        fill_count = 0
        for item in self._payload_items(fills_payload):
            payload = self.normalize_fill(item)
            if not payload.get("tradeId"):
                continue
            self.callback_client.post_exchange_fill(payload)
            fill_count += 1

        return {"orders": order_count, "fills": fill_count, "skipped": False}

    def _can_sync(self) -> bool:
        return (
            self.okx_client is not None
            and self.callback_client is not None
            and hasattr(self.okx_client, "get_order_history")
            and hasattr(self.okx_client, "get_fills_history")
            and hasattr(self.callback_client, "post_exchange_order")
            and hasattr(self.callback_client, "post_exchange_fill")
        )

    def _payload_items(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data") or []
        return [item for item in data if isinstance(item, dict)]

    def _symbol_from_item(self, item: dict[str, Any]) -> str:
        inst_id = str(item.get("instId") or "")
        if hasattr(self.okx_client, "_symbol_from_instrument_id"):
            try:
                return str(self.okx_client._symbol_from_instrument_id(inst_id))
            except Exception:
                pass
        if inst_id.endswith("-USDT-SWAP"):
            return inst_id.replace("-USDT-SWAP", "USDT").replace("-", "")
        return inst_id.replace("-SWAP", "").replace("-", "")

    def _base_quantity(self, symbol: str, contracts: Any) -> float | None:
        if contracts in (None, ""):
            return None
        if hasattr(self.okx_client, "base_quantity_from_contracts"):
            try:
                return float(self.okx_client.base_quantity_from_contracts(symbol, contracts))
            except Exception:
                pass
        return _to_float(contracts)

    def _status_pair(self, state: Any) -> tuple[str, str]:
        normalized = str(state or "").strip().lower()
        if normalized in _OKX_ORDER_STATUS_MAP:
            return _OKX_ORDER_STATUS_MAP[normalized]
        if not normalized:
            return "pending", "PENDING"
        return normalized, normalized.upper()

    def normalize_order(self, item: dict[str, Any], *, mode: str = "live") -> dict[str, Any]:
        symbol = self._symbol_from_item(item)
        status, order_status = self._status_pair(item.get("state"))
        order_type = str(item.get("ordType") or "").strip().lower()
        updated_at = _timestamp_ms_to_iso(item.get("uTime"))
        payload = {
            "traceId": str(item.get("clOrdId") or ""),
            "exchangeCode": "okx",
            "symbol": symbol,
            "side": str(item.get("side") or "").upper(),
            "mode": mode,
            "orderRef": str(item.get("ordId") or ""),
            "clientOrderId": str(item.get("clOrdId") or ""),
            "orderType": order_type,
            "positionSide": str(item.get("posSide") or "").lower(),
            "limitPrice": _to_float(item.get("px")),
            "quantityBase": self._base_quantity(symbol, item.get("sz")),
            "filledQuantity": self._base_quantity(symbol, item.get("accFillSz") or item.get("fillSz")),
            "avgFillPrice": _to_float(item.get("avgPx")),
            "fee": _fee_cost(item.get("fee")),
            "feeCcy": item.get("feeCcy") or None,
            "postOnly": order_type == "post_only",
            "status": status,
            "executionStatus": status,
            "orderStatus": order_status,
            "createdAt": _timestamp_ms_to_iso(item.get("cTime")),
            "updatedAt": updated_at,
            "filledAt": updated_at if order_status == "FILLED" else None,
            "rawPayload": _raw_payload(item),
        }
        return payload

    def normalize_fill(self, item: dict[str, Any]) -> dict[str, Any]:
        symbol = self._symbol_from_item(item)
        exec_type = str(item.get("execType") or "")
        return {
            "traceId": str(item.get("clOrdId") or ""),
            "exchangeCode": "okx",
            "symbol": symbol,
            "side": str(item.get("side") or "").upper(),
            "positionSide": str(item.get("posSide") or "").lower(),
            "orderRef": str(item.get("ordId") or ""),
            "tradeId": str(item.get("tradeId") or ""),
            "fillPrice": _to_float(item.get("fillPx")),
            "fillQuantity": self._base_quantity(symbol, item.get("fillSz")),
            "fee": _fee_cost(item.get("fee")),
            "feeCcy": item.get("feeCcy") or None,
            "isMaker": exec_type.upper() == "M",
            "execType": exec_type,
            "realizedPnl": _to_float(item.get("pnl")),
            "filledAt": _timestamp_ms_to_iso(item.get("ts")),
            "rawPayload": _raw_payload(item),
        }
