from trade_runtime.execution.clients import FuturesExecutionClient


class BinanceFuturesExecutionAdapter:
    def __init__(self, client: FuturesExecutionClient | None, max_status_checks: int = 2):
        self.client = client
        self.max_status_checks = max(1, max_status_checks)

    def _calculate_quantity(self, order: dict) -> float:
        quantity_base = float(order.get("quantity_base") or 0)
        if quantity_base > 0:
            return round(quantity_base, 8)
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        return round(quote / price, 8) if price > 0 else 0.0

    def _fallback_result(self, order: dict) -> dict:
        price = float(order.get("price", 0) or 0)
        fill_quantity = self._calculate_quantity(order)
        return {
            "status": "filled",
            "is_live": True,
            "exchange": "binance",
            "order_id": f"binance-{order['symbol']}",
            "order_status": "FILLED",
            "fill_price": price,
            "fill_quantity": fill_quantity,
            "position_quantity": fill_quantity,
            "entry_price": price,
        }

    def _failed_result(self, order: dict, error: str) -> dict:
        return {
            "status": "failed",
            "is_live": True,
            "exchange": "binance",
            "order_id": "",
            "order_status": "REJECTED",
            "fill_price": float(order.get("price", 0) or 0),
            "fill_quantity": 0.0,
            "position_quantity": 0.0,
            "entry_price": float(order.get("price", 0) or 0),
            "error": error,
        }

    def _is_error_payload(self, payload: dict) -> bool:
        return "msg" in payload and not payload.get("orderId") and not payload.get("status")

    def _result_status(self, order_status: str) -> str:
        normalized = str(order_status or "").upper()
        if normalized == "FILLED":
            return "filled"
        if normalized in {"NEW", "PENDING"}:
            return "pending"
        if normalized == "PARTIALLY_FILLED":
            return "partial"
        if normalized == "CANCELED":
            return "canceled"
        if normalized == "EXPIRED":
            return "expired"
        if normalized in {"REJECTED"}:
            return "failed"
        return "submitted"

    def _normalize_response(self, order: dict, payload: dict) -> dict:
        fallback = self._fallback_result(order)
        order_status = str(payload.get("status") or fallback["order_status"]).upper()
        default_fill_quantity = fallback["fill_quantity"]
        if order_status in {"NEW", "PENDING", "CANCELED", "EXPIRED", "REJECTED"}:
            default_fill_quantity = 0.0
        fill_quantity = float(payload.get("executedQty") or default_fill_quantity or 0)
        fill_price = float(payload.get("avgPrice") or 0)
        if fill_price <= 0:
            cumulative_quote_qty = float(payload.get("cummulativeQuoteQty") or 0)
            if cumulative_quote_qty > 0 and fill_quantity > 0:
                fill_price = cumulative_quote_qty / fill_quantity
            else:
                fill_price = fallback["fill_price"]
        return {
            "status": self._result_status(order_status),
            "is_live": True,
            "exchange": "binance",
            "order_id": str(payload.get("orderId") or fallback["order_id"]),
            "order_status": order_status,
            "fill_price": fill_price,
            "fill_quantity": fill_quantity,
            "position_quantity": fill_quantity,
            "entry_price": fill_price,
        }

    def place_market_order(self, order: dict) -> dict:
        if self.client is None:
            return self._failed_result(order, "live_execution_client_unavailable")
        try:
            payload = self.client.place_market_order(order)
        except Exception as exc:
            return self._failed_result(order, str(exc))
        if not isinstance(payload, dict):
            return self._failed_result(order, "invalid_binance_response")
        if self._is_error_payload(payload):
            return self._failed_result(order, str(payload.get("msg") or "binance_order_failed"))
        order_id = payload.get("orderId")
        if (
            hasattr(self.client, "get_order_status")
            and order_id not in (None, "")
        ):
            for _ in range(self.max_status_checks):
                order_status = str(payload.get("status") or "").upper()
                if order_status in {"FILLED", "CANCELED", "REJECTED", "EXPIRED"}:
                    break
                try:
                    follow_up = self.client.get_order_status(order["symbol"], order_id)
                except Exception as exc:
                    return self._failed_result(order, str(exc))
                if not isinstance(follow_up, dict):
                    break
                if self._is_error_payload(follow_up):
                    return self._failed_result(order, str(follow_up.get("msg") or "binance_order_failed"))
                payload = {**payload, **follow_up}
        return self._normalize_response(order, payload)

