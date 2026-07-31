class OkxFuturesExecutionAdapter:
    def __init__(self, client, max_status_checks: int = 2):
        self.client = client
        self.max_status_checks = max(1, max_status_checks)

    def _fallback_result(self, order: dict) -> dict:
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        quantity_base = float(order.get("quantity_base") or 0)
        fill_quantity = round(quantity_base, 8) if quantity_base > 0 else round(quote / price, 8) if price > 0 else 0.0
        return {
            "status": "filled",
            "is_live": True,
            "exchange": "okx",
            "order_id": f"okx-{order['symbol']}",
            "order_status": "FILLED",
            "fill_price": price,
            "fill_quantity": fill_quantity,
            "position_quantity": fill_quantity,
            "entry_price": price,
        }

    def _failed_result(self, order: dict, error: str) -> dict:
        price = float(order.get("price", 0) or 0)
        return {
            "status": "failed",
            "is_live": True,
            "exchange": "okx",
            "order_id": "",
            "order_status": "REJECTED",
            "fill_price": price,
            "fill_quantity": 0.0,
            "position_quantity": 0.0,
            "entry_price": price,
            "error": error,
        }

    def _no_position_result(self, order: dict, message: str) -> dict:
        """返回无持仓的结果"""
        price = float(order.get("price", 0) or 0)
        return {
            "status": "skipped",
            "is_live": True,
            "exchange": "okx",
            "order_id": "",
            "order_status": "SKIPPED",
            "fill_price": price,
            "fill_quantity": 0.0,
            "position_quantity": 0.0,
            "entry_price": price,
            "message": message,
        }

    def _is_error_payload(self, payload: dict) -> bool:
        code = str(payload.get("code") or "")
        if code not in {"", "0"} and "msg" in payload:
            return True
        data = payload.get("data") or []
        if not data:
            return False
        item = data[0]
        item_code = str(item.get("sCode") or "")
        return item_code not in {"", "0"}

    def _payload_item(self, payload: dict) -> dict:
        data = payload.get("data") or []
        return data[0] if data else {}

    def _is_adapter_result(self, payload: dict) -> bool:
        return "order_status" in payload and "fill_quantity" in payload

    def _follow_order_status(self, order: dict, payload: dict) -> dict:
        item = self._payload_item(payload)
        order_id = item.get("ordId")
        if self.client is None or not hasattr(self.client, "get_order_status") or order_id in (None, ""):
            return payload
        for _ in range(self.max_status_checks):
            item = self._payload_item(payload)
            state = str(item.get("state") or "").upper()
            if state in {"FILLED", "CANCELED", "REJECTED", "EXPIRED"}:
                break
            try:
                follow_up = self.client.get_order_status(order["symbol"], order_id)
            except Exception as exc:
                return self._failed_result(order, str(exc))
            if not isinstance(follow_up, dict):
                break
            if self._is_error_payload(follow_up):
                return self._failed_result(order, self._error_message(follow_up))
            payload = follow_up
        return payload

    def _normalize_submitted_payload(self, order: dict, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return self._failed_result(order, "invalid_okx_response")
        if self._is_error_payload(payload):
            return self._failed_result(order, self._error_message(payload))
        payload = self._follow_order_status(order, payload)
        if not isinstance(payload, dict):
            return self._failed_result(order, "invalid_okx_response")
        if self._is_adapter_result(payload):
            return payload
        if not (payload.get("data") or []):
            return self._failed_result(order, "invalid_okx_response")
        if self._is_error_payload(payload):
            return self._failed_result(order, self._error_message(payload))
        return self._normalize_response(order, payload)

    def _error_message(self, payload: dict, fallback: str = "okx_order_failed") -> str:
        data = payload.get("data") or []
        item = data[0] if data else {}
        return str(item.get("sMsg") or payload.get("msg") or fallback)

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
        data = payload.get("data") or []
        item = data[0] if data else {}
        state = str(item.get("state") or "").upper()
        has_fill_detail = item.get("avgPx") not in (None, "") or item.get("fillSz") not in (None, "") or item.get("accFillSz") not in (None, "")
        if not state:
            state = "LIVE" if item.get("ordId") and not has_fill_detail else fallback["order_status"]
        default_fill_quantity = fallback["fill_quantity"]
        if state in {"LIVE", "NEW", "PENDING", "CANCELED", "EXPIRED", "REJECTED"}:
            default_fill_quantity = 0.0
        fill_price = float(item.get("avgPx") or fallback["fill_price"] or 0)
        fill_quantity = self._normalize_fill_quantity(order, item.get("fillSz") or item.get("accFillSz"), default_fill_quantity)
        if state == "FILLED":
            order_status = "FILLED"
        elif state == "LIVE":
            order_status = "PENDING"
        else:
            order_status = state
        return {
            "status": self._result_status(order_status),
            "is_live": True,
            "exchange": "okx",
            "order_id": str(item.get("ordId") or fallback["order_id"]),
            "order_status": order_status,
            "fill_price": fill_price,
            "fill_quantity": fill_quantity,
            "position_quantity": fill_quantity,
            "entry_price": fill_price,
        }

    def _normalize_fill_quantity(self, order: dict, raw_fill_size, default_fill_quantity: float) -> float:
        if raw_fill_size in (None, ""):
            return float(default_fill_quantity or 0)
        if self.client is not None and hasattr(self.client, "base_quantity_from_contracts"):
            try:
                return float(self.client.base_quantity_from_contracts(order["symbol"], raw_fill_size))
            except Exception:
                return 0.0
        return float(raw_fill_size or default_fill_quantity or 0)

    def _is_close_action(self, order: dict) -> bool:
        """判断是否为平仓操作"""
        action = str(order.get("action") or "").upper()
        reduce_only = bool(order.get("reduce_only", False))
        # 只有明确的 CLOSE/REDUCE 动作才使用专用平仓方法
        # reduce_only 的限价单可能是普通挂单，不强制使用平仓方法
        return action in {"CLOSE", "REDUCE", "CLOSE_LONG", "CLOSE_SHORT", "REDUCE_LONG", "REDUCE_SHORT"}

    def _get_position_side_for_close(self, order: dict) -> str:
        """获取平仓方向"""
        position_side = str(order.get("position_side") or "").lower()
        if position_side in {"long", "short"}:
            return position_side
        action = str(order.get("action") or "").upper()
        if action == "CLOSE_LONG" or "LONG" in action:
            return "long"
        if action == "CLOSE_SHORT" or "SHORT" in action:
            return "short"
        side = str(order.get("side") or "").upper()
        if side == "SELL":
            return "long"
        if side == "BUY":
            return "short"
        return "long"

    def _ensure_position_mode(self) -> None:
        """确保双向持仓模式"""
        if self.client is not None and hasattr(self.client, "ensure_dual_position_mode"):
            try:
                self.client.ensure_dual_position_mode()
            except Exception:
                pass

    def _has_close_methods(self) -> bool:
        """检查 client 是否有专用平仓方法"""
        return (
            self.client is not None
            and hasattr(self.client, "close_long")
            and hasattr(self.client, "close_short")
        )

    def _has_open_methods(self) -> bool:
        return (
            self.client is not None
            and hasattr(self.client, "open_long")
            and hasattr(self.client, "open_short")
        )

    def _is_open_action(self, order: dict) -> bool:
        order_type = str(order.get("order_type") or "market").strip().lower()
        if order_type != "market" or bool(order.get("reduce_only", False)):
            return False
        action = str(order.get("action") or "").upper()
        if action.startswith("CLOSE") or action.startswith("REDUCE"):
            return False
        if action.startswith("OPEN") or action.startswith("ADD"):
            return "LONG" in action or "SHORT" in action
        position_side = str(order.get("position_side") or "").lower()
        side = str(order.get("side") or "").upper()
        return (position_side == "long" and side == "BUY") or (position_side == "short" and side == "SELL")

    def _get_position_side_for_open(self, order: dict) -> str:
        position_side = str(order.get("position_side") or "").lower()
        if position_side in {"long", "short"}:
            return position_side
        action = str(order.get("action") or "").upper()
        if "SHORT" in action:
            return "short"
        if "LONG" in action:
            return "long"
        side = str(order.get("side") or "").upper()
        return "short" if side == "SELL" else "long"

    def _order_base_quantity(self, order: dict) -> float:
        quantity = float(order.get("quantity_base") or 0.0)
        if quantity > 0:
            return quantity
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        return round(quote / price, 8) if price > 0 and quote > 0 else 0.0

    def _order_leverage(self, order: dict) -> int:
        leverage = int(float(order.get("leverage") or 10))
        return max(1, leverage)

    def place_order(self, order: dict) -> dict:
        if self.client is None:
            return self._failed_result(order, "live_execution_client_unavailable")

        # 确保双向持仓模式
        self._ensure_position_mode()

        # 判断是否为平仓操作，且 client 支持专用平仓方法
        if self._is_close_action(order) and self._has_close_methods():
            return self._execute_close_order(order)

        if self._is_open_action(order) and self._has_open_methods():
            return self._execute_open_order(order)

        # 开仓操作或普通挂单
        if not hasattr(self.client, "place_order"):
            return self.place_market_order(order)
        try:
            payload = self.client.place_order(order)
        except Exception as exc:
            return self._failed_result(order, str(exc))
        return self._normalize_submitted_payload(order, payload)


    def _execute_open_order(self, order: dict) -> dict:
        if self.client is None:
            return self._failed_result(order, "live_execution_client_unavailable")

        symbol = str(order.get("symbol", ""))
        position_side = self._get_position_side_for_open(order)
        quantity = self._order_base_quantity(order)
        leverage = self._order_leverage(order)
        td_mode = str(order.get("td_mode") or "cross")

        try:
            if position_side == "long":
                payload = self.client.open_long(symbol, quantity, leverage, td_mode=td_mode)
            else:
                payload = self.client.open_short(symbol, quantity, leverage, td_mode=td_mode)
        except Exception as exc:
            return self._failed_result(order, str(exc))

        return self._normalize_submitted_payload(order, payload)

    def _execute_close_order(self, order: dict) -> dict:
        """执行平仓操作"""
        if self.client is None:
            return self._failed_result(order, "live_execution_client_unavailable")

        symbol = str(order.get("symbol", ""))
        position_side = self._get_position_side_for_close(order)
        td_mode = str(order.get("td_mode") or "cross")

        # 计算平仓数量
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        quantity = float(order.get("quantity_base") or 0.0)
        if quantity <= 0 and price > 0 and quote > 0:
            quantity = round(quote / price, 8)

        # 使用专用平仓方法
        try:
            if position_side == "long":
                payload = self.client.close_long(symbol, quantity, td_mode=td_mode)
            else:
                payload = self.client.close_short(symbol, quantity, td_mode=td_mode)
        except Exception as exc:
            return self._failed_result(order, str(exc))

        # 检查是否无持仓
        if isinstance(payload, dict) and payload.get("status") == "NO_POSITION":
            return self._no_position_result(order, payload.get("message", "No position found"))

        return self._normalize_submitted_payload(order, payload)

    def place_market_order(self, order: dict) -> dict:
        if self.client is None:
            return self._failed_result(order, "live_execution_client_unavailable")

        # 确保双向持仓模式
        self._ensure_position_mode()

        # 判断是否为平仓操作，且 client 支持专用平仓方法
        if self._is_close_action(order) and self._has_close_methods():
            return self._execute_close_order(order)

        if self._is_open_action(order) and self._has_open_methods():
            return self._execute_open_order(order)

        try:
            payload = self.client.place_market_order(order)
        except Exception as exc:
            return self._failed_result(order, str(exc))
        return self._normalize_submitted_payload(order, payload)
