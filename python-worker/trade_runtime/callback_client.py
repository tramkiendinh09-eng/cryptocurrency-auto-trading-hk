"""
运行时回调客户端模块

提供与后端服务通信的HTTP客户端，用于发送：
- 订单请求
- 决策审计
- 盈亏快照
- 仓位快照
- 交易所订单/成交
- 工作节点心跳
"""

from __future__ import annotations

from typing import Any

import requests


class RuntimeCallbackClient:
    """运行时回调客户端

    通过HTTP API与后端服务通信，发送交易执行结果和状态更新。

    Attributes:
        base_url: 后端服务基础URL
        bearer_token: 认证令牌
        timeout: 请求超时时间（秒）
    """

    def __init__(self, base_url: str, bearer_token: str, timeout: int = 5):
        """初始化回调客户端

        Args:
            base_url: 后端服务基础URL
            bearer_token: 认证令牌
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout

    def build_headers(self) -> dict[str, str]:
        """构建HTTP请求头

        Returns:
            dict[str, str]: 请求头字典
        """
        headers = {
            "Accept": "application/json",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def _validate_response(self, response: requests.Response, endpoint_name: str) -> None:
        response.raise_for_status()
        content_type = str(getattr(response, "headers", {}).get("Content-Type") or "").lower()
        if "json" not in content_type:
            return
        try:
            payload = response.json()
        except ValueError:
            return
        if not isinstance(payload, dict) or "code" not in payload:
            return
        try:
            code = int(payload.get("code"))
        except (TypeError, ValueError):
            return
        if code == 200:
            return
        message = str(payload.get("msg") or payload.get("message") or "unknown business error").strip()
        raise RuntimeError(f"Runtime callback {endpoint_name} failed: {message}")

    def _post(
        self,
        path: str,
        *,
        endpoint_name: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        request_kwargs = {
            "headers": self.build_headers(),
            "timeout": self.timeout,
        }
        if json is not None:
            request_kwargs["json"] = json
        if params is not None:
            request_kwargs["params"] = params
        response = requests.post(f"{self.base_url}{path}", **request_kwargs)
        self._validate_response(response, endpoint_name)

    def _get_json(
        self,
        path: str,
        *,
        endpoint_name: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers=self.build_headers(),
            timeout=self.timeout,
        )
        self._validate_response(response, endpoint_name)
        try:
            payload = response.json()
        except ValueError:
            return None
        return payload.get("data") if isinstance(payload, dict) else payload

    def post_order_request(self, payload: dict[str, Any]) -> None:
        """发送订单请求回调

        Args:
            payload: 订单请求数据
        """
        self._post(
            "/dca/trade/execution/order",
            endpoint_name="order",
            json=payload,
        )

    def post_decision_audit(self, payload: dict[str, Any]) -> None:
        """发送决策审计回调

        Args:
            payload: 决策审计数据
        """
        self._post(
            "/dca/decision/audit",
            endpoint_name="decision-audit",
            json=payload,
        )

    def post_pnl_snapshot(self, payload: dict[str, Any]) -> None:
        """发送盈亏快照回调

        Args:
            payload: 盈亏快照数据
        """
        self._post(
            "/dca/trade/execution/pnl-snapshot",
            endpoint_name="pnl-snapshot",
            json=payload,
        )

    def post_position_snapshot(self, payload: dict[str, Any]) -> None:
        """发送仓位快照回调

        Args:
            payload: 仓位快照数据
        """
        self._post(
            "/dca/trade/execution/position-snapshot",
            endpoint_name="position-snapshot",
            json=payload,
        )

    def post_exchange_order(self, payload: dict[str, Any]) -> None:
        """发送交易所订单回调

        Args:
            payload: 交易所订单数据
        """
        self._post(
            "/dca/trade/execution/exchange-order",
            endpoint_name="exchange-order",
            json=payload,
        )

    def post_exchange_fill(self, payload: dict[str, Any]) -> None:
        """发送交易所成交回调

        Args:
            payload: 交易所成交数据
        """
        self._post(
            "/dca/trade/execution/exchange-fill",
            endpoint_name="exchange-fill",
            json=payload,
        )

    def post_risk_guard_hit(self, payload: dict[str, Any]) -> None:
        self._post(
            "/dca/trade/execution/risk-guard-hit",
            endpoint_name="risk-guard-hit",
            json=payload,
        )

    def post_worker_heartbeat(self, worker_id: str) -> None:
        self._post(
            "/dca/taskqueue/heartbeat",
            endpoint_name="taskqueue-heartbeat",
            params={"workerId": worker_id},
        )

    def post_paper_trade_order(self, payload: dict[str, Any]) -> None:
        self._post(
            "/dca/trade/replay/paper-order",
            endpoint_name="paper-order",
            json=payload,
        )

    def post_shadow_decision_log(self, payload: dict[str, Any]) -> None:
        self._post(
            "/dca/trade/replay/shadow-decision",
            endpoint_name="shadow-decision",
            json=payload,
        )

    def get_recent_supervisor_decisions(
        self,
        symbol: str,
        *,
        mode: str = "",
        limit: int = 2,
        exclude_trace_id: str = "",
    ) -> list[dict[str, Any]]:
        normalized_symbol = str(symbol or "").strip()
        if not self.base_url or not normalized_symbol:
            return []
        params: dict[str, Any] = {
            "symbol": normalized_symbol,
            "limit": max(int(limit or 0), 1),
        }
        normalized_mode = str(mode or "").strip()
        if normalized_mode:
            params["mode"] = normalized_mode
        normalized_exclude_trace_id = str(exclude_trace_id or "").strip()
        if normalized_exclude_trace_id:
            params["excludeTraceId"] = normalized_exclude_trace_id
        data = self._get_json(
            "/dca/decision/supervisor-history",
            endpoint_name="recent-supervisor-decisions",
            params=params,
        )
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []
