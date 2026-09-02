from __future__ import annotations

import base64
from datetime import datetime, timezone
import inspect
import hashlib
import hmac
import json
import logging
from decimal import Decimal, ROUND_DOWN
from typing import Any, Protocol
from urllib.parse import urlencode

import requests

from trade_runtime.execution.symbol_filters import shared_binance_filters

logger = logging.getLogger(__name__)


OKX_NOFX_ORDER_TAG = base64.b64decode("NGMzNjNjODFlZGM1QkNERQ==").decode("utf-8")


class FuturesExecutionClient(Protocol):
    def place_market_order(self, order: dict[str, Any]) -> dict[str, Any]:
        ...

    def get_order_status(self, symbol: str, order_id: str | int) -> dict[str, Any] | None:
        ...


class BinanceRestExecutionClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        timeout: int = 10,
        session: Any | None = None,
        timestamp_supplier: Any | None = None,
        symbol_filters: Any | None = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = bool(testnet)
        self.base_url = "https://demo-fapi.binance.com" if testnet else "https://fapi.binance.com"
        self.timeout = timeout
        self.session = session or requests.Session()
        if hasattr(self.session, "headers"):
            self.session.headers.update({"X-MBX-APIKEY": api_key})
        self.timestamp_supplier = timestamp_supplier or (lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
        # Venue filters (LOT_SIZE / MIN_NOTIONAL). Injected in tests; shared in
        # production so one exchangeInfo snapshot serves every client.
        self._symbol_filters = symbol_filters
        self._leverage_applied: set[tuple[str, int]] = set()

    @property
    def symbol_filters(self) -> Any:
        if self._symbol_filters is None:
            self._symbol_filters = shared_binance_filters(testnet=self.testnet)
        return self._symbol_filters

    def set_leverage(self, symbol: str, leverage: Any) -> dict[str, Any]:
        """Set leverage for a symbol.

        Binance keeps leverage as account state, not an order parameter, so
        without this call orders inherit whatever the account was last set to —
        possibly 20x from a previous manual session. On a small account that is
        the difference between a position the risk limits sized and one they
        never sanctioned.
        """
        try:
            leverage_int = int(float(leverage))
        except (TypeError, ValueError):
            raise ValueError("binance_invalid_leverage")
        if leverage_int <= 0:
            raise ValueError("binance_invalid_leverage")
        normalized = str(symbol or "").strip().upper()
        return self._request(
            "POST",
            "/fapi/v1/leverage",
            params=self._signed_params({"symbol": normalized, "leverage": leverage_int}),
        )

    def _apply_leverage(self, order: dict[str, Any]) -> None:
        requested = order.get("leverage")
        if requested in (None, ""):
            return
        symbol = str(order.get("symbol") or "").strip().upper()
        try:
            leverage_int = int(float(requested))
        except (TypeError, ValueError):
            logger.warning("ignoring invalid leverage=%r symbol=%s", requested, symbol)
            return
        if leverage_int <= 0 or (symbol, leverage_int) in self._leverage_applied:
            return
        try:
            self.set_leverage(symbol, leverage_int)
        except Exception as exc:
            # Never block the order on this: the account already has *some*
            # leverage, and the risk gate has already bounded the notional.
            logger.warning("set_leverage failed symbol=%s leverage=%s error=%s", symbol, leverage_int, exc)
            return
        self._leverage_applied.add((symbol, leverage_int))

    def _generate_signature(self, params: dict[str, Any]) -> str:
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _signed_params(self, params: dict[str, Any]) -> dict[str, Any]:
        signed = dict(params)
        signed["timestamp"] = self.timestamp_supplier()
        signed["signature"] = self._generate_signature(signed)
        return signed

    def _request(self, method: str, endpoint: str, *, params: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.base_url}{endpoint}",
            params=params or {},
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def _calculate_quantity(self, order: dict[str, Any]) -> float:
        quantity_base = float(order.get("quantity_base") or 0)
        if quantity_base > 0:
            return round(quantity_base, 8)
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        return round(quote / price, 8) if price > 0 else 0.0

    def place_market_order(self, order: dict[str, Any]) -> dict[str, Any]:
        symbol = str(order["symbol"]).strip().upper()
        requested = self._calculate_quantity(order)
        price = float(order.get("price", 0) or 0)

        decision = self.symbol_filters.resolve_quantity(symbol, requested, price)
        if decision.rejected:
            # Refuse locally rather than trading an exchange error code for a
            # reason. The caller records this as a skip with the cause intact.
            logger.warning(
                "order rejected by venue filters symbol=%s requested=%s reason=%s",
                symbol,
                requested,
                decision.reason,
            )
            return {
                "code": -4164,
                "msg": f"local_filter_rejected:{decision.reason}",
                "symbol": symbol,
                "requestedQuantity": requested,
                "adjustedQuantity": decision.quantity,
                "notional": decision.notional,
            }

        self._apply_leverage(order)
        params = {
            "symbol": symbol,
            "side": order["side"],
            "type": "MARKET",
            "quantity": self.symbol_filters.format_quantity(symbol, decision.quantity),
        }
        if order.get("reduce_only") or order.get("reduceOnly"):
            params["reduceOnly"] = "true"
        return self._request(
            "POST",
            "/fapi/v1/order",
            params=self._signed_params(params),
        )

    def get_order_status(self, symbol: str, order_id: str | int) -> dict[str, Any] | None:
        return self._request(
            "GET",
            "/fapi/v1/order",
            params=self._signed_params({"symbol": symbol, "orderId": order_id}),
        )

    def get_balance(self) -> dict[str, Any]:
        """Real USD-M futures equity.

        Nothing previously asked the venue what the account was worth, so
        position sizing ran on the control plane's 10000 USDT placeholder until
        an execution produced the first pnl snapshot. On a small account that
        placeholder is the difference between a sanely sized order and one
        several hundred times too large.
        """
        payload = self._request(
            "GET",
            "/fapi/v2/account",
            params=self._signed_params({}),
        )
        assets = payload.get("assets") if isinstance(payload, dict) else None
        usdt: dict[str, Any] = {}
        if isinstance(assets, list):
            for item in assets:
                if isinstance(item, dict) and str(item.get("asset") or "").upper() == "USDT":
                    usdt = item
                    break

        def _f(source: dict[str, Any], key: str) -> float:
            try:
                return float(source.get(key) or 0.0)
            except (TypeError, ValueError):
                return 0.0

        # totalMarginBalance already includes unrealised PnL, which is the
        # figure the risk limits are written against.
        equity = _f(payload, "totalMarginBalance") or _f(payload, "totalWalletBalance")
        return {
            "total_equity": equity,
            "available_balance": _f(payload, "availableBalance") or _f(usdt, "availableBalance"),
            "total_unrealized_profit": _f(payload, "totalUnrealizedProfit"),
            "wallet_balance": _f(payload, "totalWalletBalance"),
            "currency": "USDT",
        }


class LegacyBinanceExecutionClient:
    def __init__(self, client: Any):
        self.client = client

    def _calculate_quantity(self, order: dict[str, Any]) -> float:
        quantity_base = float(order.get("quantity_base") or 0)
        if quantity_base > 0:
            return round(quantity_base, 8)
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        return round(quote / price, 8) if price > 0 else 0.0

    def place_market_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return self.client.place_market_order(
            order["symbol"],
            order["side"],
            self._calculate_quantity(order),
        )

    def get_order_status(self, symbol: str, order_id: str | int) -> dict[str, Any] | None:
        if not hasattr(self.client, "get_order_status"):
            return None
        return self.client.get_order_status(symbol, order_id)


class OkxRestExecutionClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        passphrase: str,
        base_url: str = "https://www.okx.com",
        demo_trading: bool = False,
        timeout: int = 10,
        session: Any | None = None,
        timestamp_supplier: Any | None = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = base_url.rstrip("/")
        self.demo_trading = demo_trading
        self.timeout = timeout
        self.session = session or requests.Session()
        self.timestamp_supplier = timestamp_supplier or self._default_timestamp
        self._instrument_cache: dict[str, dict[str, Any]] = {}
        self._position_mode: str | None = None
        self._position_mode_detected: bool = False

    def _default_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _calculate_size(self, order: dict[str, Any]) -> float:
        quantity_base = float(order.get("quantity_base") or 0)
        if quantity_base > 0:
            return round(quantity_base, 8)
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        return round(quote / price, 8) if price > 0 else 0.0

    def _base_quantity(self, order: dict[str, Any]) -> float:
        quantity_base = order.get("quantity_base")
        if quantity_base not in (None, ""):
            return float(quantity_base or 0)
        return self._calculate_size(order)

    def _to_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _instrument_id(self, symbol: str) -> str:
        if "-" in symbol and symbol.endswith("-SWAP"):
            return symbol
        if symbol.endswith("USDT"):
            return f"{symbol[:-4]}-USDT-SWAP"
        return f"{symbol}-SWAP"

    def _symbol_from_instrument_id(self, inst_id: str) -> str:
        if inst_id.endswith("-USDT-SWAP"):
            return inst_id.replace("-USDT-SWAP", "USDT").replace("-", "")
        return inst_id.replace("-SWAP", "").replace("-", "")

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        message = f"{timestamp}{method.upper()}{request_path}{body}"
        digest = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _headers(self, *, method: str, request_path: str, body: str = "") -> dict[str, str]:
        timestamp = self.timestamp_supplier()
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": self._sign(timestamp, method, request_path, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        if self.demo_trading:
            headers["x-simulated-trading"] = "1"
        return headers

    def _request_json(self, method: str, request_path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":")) if payload is not None else ""
        headers = self._headers(method=method, request_path=request_path, body=body)
        if method.upper() == "POST":
            response = self.session.post(
                f"{self.base_url}{request_path}",
                headers=headers,
                data=body,
                timeout=self.timeout,
            )
        else:
            response = self.session.get(
                f"{self.base_url}{request_path}",
                headers=headers,
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()

    def _format_step_value(self, value: float, step: Any) -> str:
        step_decimal = Decimal(str(step or "0"))
        value_decimal = Decimal(str(value or 0))
        if step_decimal <= 0:
            formatted = format(value_decimal.normalize(), "f")
        else:
            rounded = (value_decimal / step_decimal).to_integral_value(rounding=ROUND_DOWN) * step_decimal
            formatted = format(rounded.normalize(), "f")
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return formatted or "0"

    def get_instrument(self, symbol: str) -> dict[str, Any]:
        inst_id = self._instrument_id(symbol)
        cached = self._instrument_cache.get(inst_id)
        if cached is not None:
            return cached
        request_path = f"/api/v5/public/instruments?instType=SWAP&instId={inst_id}"
        payload = self._request_json("GET", request_path)
        data = payload.get("data") or []
        if not data:
            raise ValueError(f"okx_instrument_not_found:{inst_id}")
        item = data[0]
        instrument = {
            "instId": item.get("instId") or inst_id,
            "ctVal": self._to_float(item.get("ctVal")),
            "ctMult": self._to_float(item.get("ctMult")) or 1.0,
            "lotSz": str(item.get("lotSz") or "1"),
            "minSz": self._to_float(item.get("minSz")),
            "maxMktSz": self._to_float(item.get("maxMktSz")),
            "tickSz": str(item.get("tickSz") or "0.1"),
        }
        self._instrument_cache[inst_id] = instrument
        return instrument

    def _contract_size(self, order: dict[str, Any], instrument: dict[str, Any]) -> str:
        ct_val = float(instrument.get("ctVal") or 0)
        if ct_val <= 0:
            raise ValueError("okx_invalid_contract_value")
        contracts = self._base_quantity(order) / ct_val
        max_market_size = float(instrument.get("maxMktSz") or 0)
        if str(order.get("order_type") or "market").lower() == "market" and max_market_size > 0:
            contracts = min(contracts, max_market_size)
        min_size = float(instrument.get("minSz") or 0)
        if min_size > 0 and contracts < min_size:
            raise ValueError(f"okx_order_size_below_minimum:{contracts}<{min_size}")
        return self._format_step_value(contracts, instrument.get("lotSz"))

    def base_quantity_from_contracts(self, symbol: str, contracts: Any) -> float:
        instrument = self.get_instrument(symbol)
        return round(self._to_float(contracts) * float(instrument.get("ctVal") or 0), 8)

    def set_leverage(self, symbol: str, leverage: Any, *, td_mode: str = "cross", position_side: str = "") -> dict[str, Any]:
        try:
            leverage_int = int(float(leverage))
        except (TypeError, ValueError):
            raise ValueError("okx_invalid_leverage")
        if leverage_int <= 0:
            raise ValueError("okx_invalid_leverage")
        payload = {
            "instId": self._instrument_id(symbol),
            "lever": str(leverage_int),
            "mgnMode": td_mode or "cross",
        }
        normalized_side = str(position_side or "").strip().lower()
        if normalized_side in {"long", "short"}:
            payload["posSide"] = normalized_side
        return self._request_json("POST", "/api/v5/account/set-leverage", payload)

    def place_market_order(self, order: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "instId": self._instrument_id(str(order.get("symbol", ""))),
            "tdMode": "cross",
            "side": str(order.get("side", "buy")).lower(),
            "ordType": "market",
            "sz": f"{self._calculate_size(order):.8f}".rstrip("0").rstrip("."),
            "tag": OKX_NOFX_ORDER_TAG,
        }
        request_path = "/api/v5/trade/order"
        body = json.dumps(payload, separators=(",", ":"))
        response = self.session.post(
            f"{self.base_url}{request_path}",
            headers=self._headers(method="POST", request_path=request_path, body=body),
            data=body,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        symbol = str(order.get("symbol", ""))
        instrument = self.get_instrument(symbol)
        order_type = str(order.get("order_type") or "market").strip().lower()
        post_only = bool(order.get("post_only", False)) or order_type == "post_only"
        if post_only:
            order_type = "limit"
        td_mode = str(order.get("td_mode") or "cross")
        position_side = str(order.get("position_side") or "").strip().lower()
        if order.get("leverage") not in (None, ""):
            self.set_leverage(symbol, order.get("leverage"), td_mode=td_mode, position_side=position_side)
        payload = {
            "instId": instrument["instId"],
            "tdMode": td_mode,
            "side": str(order.get("side", "buy")).lower(),
            "ordType": "post_only" if post_only else "limit" if order_type == "limit" else "market",
            "sz": self._contract_size(order, instrument),
        }
        if position_side in {"long", "short"}:
            payload["posSide"] = position_side
        if order_type == "limit":
            payload["px"] = self._format_step_value(float(order.get("limit_price") or order.get("price") or 0), instrument.get("tickSz"))
        payload["tag"] = OKX_NOFX_ORDER_TAG
        client_id = str(order.get("client_id") or order.get("trace_id") or "").strip()
        if client_id:
            payload["clOrdId"] = client_id[:32]
        if bool(order.get("reduce_only", False)):
            payload["reduceOnly"] = "true"
        request_path = "/api/v5/trade/order"
        return self._request_json("POST", request_path, payload)

    def get_balance(self) -> dict[str, Any]:
        payload = self._request_json("GET", "/api/v5/account/balance")
        data = payload.get("data") or []
        account = data[0] if data else {}
        usdt_detail = {}
        for detail in account.get("details") or []:
            if str(detail.get("ccy") or "").upper() == "USDT":
                usdt_detail = detail
                break
        return {
            "total_equity": self._to_float(account.get("totalEq")),
            "available_balance": self._to_float(usdt_detail.get("availBal")),
            "total_unrealized_profit": self._to_float(usdt_detail.get("upl")),
            "currency": "USDT",
        }

    def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        request_path = "/api/v5/account/positions?instType=SWAP"
        if symbol:
            request_path = f"{request_path}&instId={self._instrument_id(symbol)}"
        payload = self._request_json("GET", request_path)
        positions = []
        for item in payload.get("data") or []:
            contracts = self._to_float(item.get("pos"))
            if contracts == 0:
                continue
            inst_id = str(item.get("instId") or "")
            position_symbol = self._symbol_from_instrument_id(inst_id)
            base_quantity = self.base_quantity_from_contracts(position_symbol, abs(contracts))
            positions.append(
                {
                    "symbol": position_symbol,
                    "positionAmt": base_quantity,
                    "entryPrice": self._to_float(item.get("avgPx")),
                    "markPrice": self._to_float(item.get("markPx")),
                    "unRealizedProfit": self._to_float(item.get("upl")),
                    "leverage": self._to_float(item.get("lever")),
                    "liquidationPrice": self._to_float(item.get("liqPx")),
                    "side": str(item.get("posSide") or "").lower(),
                    "mgnMode": item.get("mgnMode") or "",
                    "createdTime": item.get("cTime") or "",
                    "updatedTime": item.get("uTime") or "",
                }
            )
        return positions

    def get_order_status(self, symbol: str, order_id: str | int) -> dict[str, Any] | None:
        request_path = f"/api/v5/trade/order?instId={self._instrument_id(symbol)}&ordId={order_id}"
        response = self.session.get(
            f"{self.base_url}{request_path}",
            headers=self._headers(method="GET", request_path=request_path),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _history_query_path(
        self,
        endpoint: str,
        *,
        symbol: str | None = None,
        limit: int = 100,
        begin: int | str | None = None,
        end: int | str | None = None,
    ) -> str:
        normalized_limit = max(1, min(int(limit or 100), 100))
        params: list[tuple[str, str]] = [("instType", "SWAP"), ("limit", str(normalized_limit))]
        if symbol:
            params.append(("instId", self._instrument_id(str(symbol))))
        if begin not in (None, ""):
            params.append(("begin", str(begin)))
        if end not in (None, ""):
            params.append(("end", str(end)))
        return f"{endpoint}?{urlencode(params)}"

    def get_order_history(
        self,
        symbol: str | None = None,
        limit: int = 100,
        begin: int | str | None = None,
        end: int | str | None = None,
    ) -> dict[str, Any]:
        request_path = self._history_query_path(
            "/api/v5/trade/orders-history",
            symbol=symbol,
            limit=limit,
            begin=begin,
            end=end,
        )
        return self._request_json("GET", request_path)

    def get_fills_history(
        self,
        symbol: str | None = None,
        limit: int = 100,
        begin: int | str | None = None,
        end: int | str | None = None,
    ) -> dict[str, Any]:
        request_path = self._history_query_path(
            "/api/v5/trade/fills-history",
            symbol=symbol,
            limit=limit,
            begin=begin,
            end=end,
        )
        return self._request_json("GET", request_path)

    # ==================== 仓位模式检测与设置 ====================

    def detect_position_mode(self) -> str:
        """
        检测当前账户的仓位模式

        Returns:
            str: "long_short_mode" (双向持仓) 或 "net_mode" (单向持仓)
        """
        if self._position_mode_detected and self._position_mode:
            return self._position_mode
        try:
            payload = self._request_json("GET", "/api/v5/account/config")
            data = payload.get("data") or []
            if data:
                self._position_mode = str(data[0].get("posMode") or "net_mode")
            else:
                self._position_mode = "net_mode"
        except Exception:
            self._position_mode = "net_mode"
        self._position_mode_detected = True
        return self._position_mode or "net_mode"

    def set_position_mode(self, mode: str = "long_short_mode") -> bool:
        """
        设置仓位模式

        Args:
            mode: "long_short_mode" (双向持仓) 或 "net_mode" (单向持仓)

        Returns:
            bool: 是否设置成功
        """
        try:
            self._request_json("POST", "/api/v5/account/set-position-mode", {"posMode": mode})
            self._position_mode = mode
            return True
        except Exception:
            return False

    def ensure_dual_position_mode(self) -> str:
        """
        确保账户使用双向持仓模式，如果不是则尝试切换

        Returns:
            str: 当前仓位模式
        """
        current_mode = self.detect_position_mode()
        if current_mode != "long_short_mode":
            self.set_position_mode("long_short_mode")
            current_mode = self.detect_position_mode()
        return current_mode

    # ==================== 客户端订单ID生成 ====================

    def _generate_cl_ord_id(self, prefix: str = "") -> str:
        """生成客户端订单ID (最大32字符)"""
        import time
        import random
        import string
        timestamp = int(time.time() * 1000) % 10000000000
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        cl_ord_id = f"{prefix}{timestamp}{random_str}"
        return cl_ord_id[:32]

    # ==================== 开仓专用方法 ====================

    def open_long(self, symbol: str, quantity: float, leverage: int = 10, *, td_mode: str = "cross") -> dict[str, Any]:
        """
        开多仓

        Args:
            symbol: 交易对 (如 BTCUSDT)
            quantity: 数量 (基础资产，如 BTC)
            leverage: 杠杆倍数
            td_mode: 保证金模式 ("cross" 或 "isolated")

        Returns:
            dict: 订单结果
        """
        # 确保双向持仓模式
        self.ensure_dual_position_mode()
        # 取消该交易对的挂单
        self.cancel_all_orders(symbol)
        # 设置杠杆
        try:
            self.set_leverage(symbol, leverage, td_mode=td_mode, position_side="long")
        except Exception:
            pass
        # 获取合约信息
        instrument = self.get_instrument(symbol)
        ct_val = float(instrument.get("ctVal") or 0)
        if ct_val <= 0:
            raise ValueError(f"okx_invalid_ctVal_for_{symbol}")
        # 计算合约张数
        contracts = quantity / ct_val
        max_mkt_sz = float(instrument.get("maxMktSz") or 0)
        if max_mkt_sz > 0 and contracts > max_mkt_sz:
            contracts = max_mkt_sz
        sz_str = self._format_step_value(contracts, instrument.get("lotSz"))
        # 下单
        payload = {
            "instId": instrument["instId"],
            "tdMode": td_mode,
            "side": "buy",
            "posSide": "long",
            "ordType": "market",
            "sz": sz_str,
            "clOrdId": self._generate_cl_ord_id("L"),
            "tag": OKX_NOFX_ORDER_TAG,
        }
        return self._request_json("POST", "/api/v5/trade/order", payload)

    def open_short(self, symbol: str, quantity: float, leverage: int = 10, *, td_mode: str = "cross") -> dict[str, Any]:
        """
        开空仓

        Args:
            symbol: 交易对 (如 BTCUSDT)
            quantity: 数量 (基础资产，如 BTC)
            leverage: 杠杆倍数
            td_mode: 保证金模式 ("cross" 或 "isolated")

        Returns:
            dict: 订单结果
        """
        # 确保双向持仓模式
        self.ensure_dual_position_mode()
        # 取消该交易对的挂单
        self.cancel_all_orders(symbol)
        # 设置杠杆
        try:
            self.set_leverage(symbol, leverage, td_mode=td_mode, position_side="short")
        except Exception:
            pass
        # 获取合约信息
        instrument = self.get_instrument(symbol)
        ct_val = float(instrument.get("ctVal") or 0)
        if ct_val <= 0:
            raise ValueError(f"okx_invalid_ctVal_for_{symbol}")
        # 计算合约张数
        contracts = quantity / ct_val
        max_mkt_sz = float(instrument.get("maxMktSz") or 0)
        if max_mkt_sz > 0 and contracts > max_mkt_sz:
            contracts = max_mkt_sz
        sz_str = self._format_step_value(contracts, instrument.get("lotSz"))
        # 下单
        payload = {
            "instId": instrument["instId"],
            "tdMode": td_mode,
            "side": "sell",
            "posSide": "short",
            "ordType": "market",
            "sz": sz_str,
            "clOrdId": self._generate_cl_ord_id("S"),
            "tag": OKX_NOFX_ORDER_TAG,
        }
        return self._request_json("POST", "/api/v5/trade/order", payload)

    # ==================== 平仓专用方法 ====================

    def close_long(self, symbol: str, quantity: float = 0, *, td_mode: str = "cross") -> dict[str, Any]:
        """
        平多仓

        Args:
            symbol: 交易对 (如 BTCUSDT)
            quantity: 平仓数量 (基础资产)，0表示全部平仓
            td_mode: 保证金模式

        Returns:
            dict: 订单结果或状态
        """
        # 获取实际持仓
        positions = self.get_positions(symbol)
        actual_qty = 0.0
        actual_mgn_mode = td_mode
        for pos in positions:
            if pos.get("side") == "long":
                actual_qty = float(pos.get("positionAmt") or 0)
                actual_mgn_mode = str(pos.get("mgnMode") or td_mode) or td_mode
                break
        if actual_qty <= 0:
            return {"status": "NO_POSITION", "message": f"No long position found for {symbol}"}
        # 使用实际数量
        if quantity <= 0 or quantity > actual_qty:
            quantity = actual_qty
        # 获取合约信息
        instrument = self.get_instrument(symbol)
        ct_val = float(instrument.get("ctVal") or 0)
        if ct_val <= 0:
            raise ValueError(f"okx_invalid_ctVal_for_{symbol}")
        # 计算合约张数
        contracts = quantity / ct_val
        sz_str = self._format_step_value(contracts, instrument.get("lotSz"))
        # 检测仓位模式
        pos_mode = self.detect_position_mode()
        # 下单
        payload = {
            "instId": instrument["instId"],
            "tdMode": actual_mgn_mode,
            "side": "sell",
            "ordType": "market",
            "sz": sz_str,
            "clOrdId": self._generate_cl_ord_id("CL"),
            "tag": OKX_NOFX_ORDER_TAG,
        }
        if pos_mode == "long_short_mode":
            payload["posSide"] = "long"
        result = self._request_json("POST", "/api/v5/trade/order", payload)
        # 平仓后取消挂单
        self.cancel_all_orders(symbol)
        return result

    def close_short(self, symbol: str, quantity: float = 0, *, td_mode: str = "cross") -> dict[str, Any]:
        """
        平空仓

        Args:
            symbol: 交易对 (如 BTCUSDT)
            quantity: 平仓数量 (基础资产)，0表示全部平仓
            td_mode: 保证金模式

        Returns:
            dict: 订单结果或状态
        """
        # 获取实际持仓
        positions = self.get_positions(symbol)
        actual_qty = 0.0
        actual_mgn_mode = td_mode
        for pos in positions:
            if pos.get("side") == "short":
                actual_qty = float(pos.get("positionAmt") or 0)
                actual_mgn_mode = str(pos.get("mgnMode") or td_mode) or td_mode
                break
        if actual_qty <= 0:
            return {"status": "NO_POSITION", "message": f"No short position found for {symbol}"}
        # 使用实际数量
        if quantity <= 0 or quantity > actual_qty:
            quantity = actual_qty
        # 获取合约信息
        instrument = self.get_instrument(symbol)
        ct_val = float(instrument.get("ctVal") or 0)
        if ct_val <= 0:
            raise ValueError(f"okx_invalid_ctVal_for_{symbol}")
        # 计算合约张数
        contracts = quantity / ct_val
        sz_str = self._format_step_value(contracts, instrument.get("lotSz"))
        # 检测仓位模式
        pos_mode = self.detect_position_mode()
        # 下单
        payload = {
            "instId": instrument["instId"],
            "tdMode": actual_mgn_mode,
            "side": "buy",
            "ordType": "market",
            "sz": sz_str,
            "clOrdId": self._generate_cl_ord_id("CS"),
            "tag": OKX_NOFX_ORDER_TAG,
        }
        if pos_mode == "long_short_mode":
            payload["posSide"] = "short"
        result = self._request_json("POST", "/api/v5/trade/order", payload)
        # 平仓后取消挂单
        self.cancel_all_orders(symbol)
        return result

    # ==================== 止损止盈 ====================

    def set_stop_loss(self, symbol: str, position_side: str, quantity: float, stop_price: float, *, td_mode: str = "cross") -> dict[str, Any]:
        """
        设置止损单

        Args:
            symbol: 交易对
            position_side: 持仓方向 ("long" 或 "short")
            quantity: 数量 (基础资产)
            stop_price: 止损价格
            td_mode: 保证金模式

        Returns:
            dict: 订单结果
        """
        self.ensure_dual_position_mode()
        instrument = self.get_instrument(symbol)
        ct_val = float(instrument.get("ctVal") or 0)
        if ct_val <= 0:
            raise ValueError(f"okx_invalid_ctVal_for_{symbol}")
        contracts = quantity / ct_val
        sz_str = self._format_step_value(contracts, instrument.get("lotSz"))
        side = "sell" if position_side == "long" else "buy"
        payload = {
            "instId": instrument["instId"],
            "tdMode": td_mode,
            "side": side,
            "posSide": position_side,
            "ordType": "conditional",
            "sz": sz_str,
            "slTriggerPx": f"{stop_price:.8f}",
            "slOrdPx": "-1",  # 市价
            "tag": OKX_NOFX_ORDER_TAG,
        }
        return self._request_json("POST", "/api/v5/trade/order-algo", payload)

    def set_take_profit(self, symbol: str, position_side: str, quantity: float, tp_price: float, *, td_mode: str = "cross") -> dict[str, Any]:
        """
        设置止盈单

        Args:
            symbol: 交易对
            position_side: 持仓方向 ("long" 或 "short")
            quantity: 数量 (基础资产)
            tp_price: 止盈价格
            td_mode: 保证金模式

        Returns:
            dict: 订单结果
        """
        self.ensure_dual_position_mode()
        instrument = self.get_instrument(symbol)
        ct_val = float(instrument.get("ctVal") or 0)
        if ct_val <= 0:
            raise ValueError(f"okx_invalid_ctVal_for_{symbol}")
        contracts = quantity / ct_val
        sz_str = self._format_step_value(contracts, instrument.get("lotSz"))
        side = "sell" if position_side == "long" else "buy"
        payload = {
            "instId": instrument["instId"],
            "tdMode": td_mode,
            "side": side,
            "posSide": position_side,
            "ordType": "conditional",
            "sz": sz_str,
            "tpTriggerPx": f"{tp_price:.8f}",
            "tpOrdPx": "-1",  # 市价
            "tag": OKX_NOFX_ORDER_TAG,
        }
        return self._request_json("POST", "/api/v5/trade/order-algo", payload)

    # ==================== 订单管理 ====================

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """
        获取当前挂单

        Args:
            symbol: 交易对 (可选，不传则获取所有)

        Returns:
            list: 挂单列表
        """
        result = []
        # 获取普通挂单
        request_path = "/api/v5/trade/orders-pending?instType=SWAP"
        if symbol:
            request_path += f"&instId={self._instrument_id(symbol)}"
        try:
            payload = self._request_json("GET", request_path)
            for item in payload.get("data") or []:
                result.append({
                    "orderId": item.get("ordId"),
                    "clientId": item.get("clOrdId"),
                    "symbol": self._symbol_from_instrument_id(item.get("instId", "")),
                    "side": str(item.get("side") or "").upper(),
                    "positionSide": str(item.get("posSide") or "").upper(),
                    "orderType": str(item.get("ordType") or "").upper(),
                    "price": self._to_float(item.get("px")),
                    "quantity": self._to_float(item.get("sz")),
                    "status": "NEW",
                })
        except Exception:
            pass
        # 获取算法挂单 (止损止盈)
        algo_request_path = "/api/v5/trade/orders-algo-pending?instType=SWAP&ordType=conditional"
        if symbol:
            algo_request_path += f"&instId={self._instrument_id(symbol)}"
        try:
            algo_payload = self._request_json("GET", algo_request_path)
            for item in algo_payload.get("data") or []:
                sl_price = self._to_float(item.get("slTriggerPx"))
                tp_price = self._to_float(item.get("tpTriggerPx"))
                if sl_price > 0:
                    algo_id = item.get("algoId") or ""
                    result.append({
                        "orderId": f"{algo_id}_sl",
                        "clientId": item.get("algoClOrdId"),
                        "symbol": self._symbol_from_instrument_id(item.get("instId", "")),
                        "side": str(item.get("side") or "").upper(),
                        "positionSide": str(item.get("posSide") or "").upper(),
                        "orderType": "STOP_MARKET",
                        "stopPrice": sl_price,
                        "quantity": self._to_float(item.get("sz")),
                        "status": "NEW",
                    })
                if tp_price > 0:
                    algo_id = item.get("algoId") or ""
                    result.append({
                        "orderId": f"{algo_id}_tp",
                        "clientId": item.get("algoClOrdId"),
                        "symbol": self._symbol_from_instrument_id(item.get("instId", "")),
                        "side": str(item.get("side") or "").upper(),
                        "positionSide": str(item.get("posSide") or "").upper(),
                        "orderType": "TAKE_PROFIT_MARKET",
                        "stopPrice": tp_price,
                        "quantity": self._to_float(item.get("sz")),
                        "status": "NEW",
                    })
        except Exception:
            pass
        return result

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """
        取消单个订单

        Args:
            symbol: 交易对
            order_id: 订单ID

        Returns:
            dict: 取消结果
        """
        inst_id = self._instrument_id(symbol)
        payload = {
            "instId": inst_id,
            "ordId": order_id,
        }
        return self._request_json("POST", "/api/v5/trade/cancel-order", payload)

    def cancel_all_orders(self, symbol: str) -> int:
        """
        取消指定交易对的所有挂单

        Args:
            symbol: 交易对

        Returns:
            int: 取消的订单数量
        """
        canceled_count = 0
        inst_id = self._instrument_id(symbol)
        # 取消普通挂单
        try:
            open_orders = self.get_open_orders(symbol)
            for order in open_orders:
                order_id = str(order.get("orderId") or "")
                if "_sl" in order_id or "_tp" in order_id:
                    # 算法单
                    algo_id = order_id.replace("_sl", "").replace("_tp", "")
                    try:
                        self._request_json("POST", "/api/v5/trade/cancel-algos", [{"instId": inst_id, "algoId": algo_id}])
                        canceled_count += 1
                    except Exception:
                        pass
                else:
                    # 普通单
                    try:
                        self.cancel_order(symbol, order_id)
                        canceled_count += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return canceled_count

    def cancel_stop_loss_orders(self, symbol: str) -> int:
        """取消止损单"""
        return self._cancel_algo_orders_by_type(symbol, "sl")

    def cancel_take_profit_orders(self, symbol: str) -> int:
        """取消止盈单"""
        return self._cancel_algo_orders_by_type(symbol, "tp")

    def _cancel_algo_orders_by_type(self, symbol: str, order_type: str) -> int:
        """取消指定类型的算法单"""
        inst_id = self._instrument_id(symbol)
        canceled_count = 0
        try:
            request_path = f"/api/v5/trade/orders-algo-pending?instType=SWAP&ordType=conditional&instId={inst_id}"
            payload = self._request_json("GET", request_path)
            for item in payload.get("data") or []:
                algo_id = str(item.get("algoId") or "")
                if not algo_id:
                    continue
                if order_type == "sl" and self._to_float(item.get("slTriggerPx")) > 0:
                    self._request_json("POST", "/api/v5/trade/cancel-algos", [{"instId": inst_id, "algoId": algo_id}])
                    canceled_count += 1
                elif order_type == "tp" and self._to_float(item.get("tpTriggerPx")) > 0:
                    self._request_json("POST", "/api/v5/trade/cancel-algos", [{"instId": inst_id, "algoId": algo_id}])
                    canceled_count += 1
        except Exception:
            pass
        return canceled_count


def coerce_binance_execution_client(client: Any) -> FuturesExecutionClient | None:
    if client is None or isinstance(client, LegacyBinanceExecutionClient):
        return client
    try:
        signature = inspect.signature(client.place_market_order)
    except (AttributeError, TypeError, ValueError):
        return client

    positional_params = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional_params) >= 3:
        return LegacyBinanceExecutionClient(client)
    return client
