"""
执行路由模块 - 订单执行的路由和分发

负责将交易订单路由到正确的交易所执行客户端，支持Binance和OKX交易所。

执行路由器的职责:
1. 根据交易所类型选择正确的执行客户端
2. 根据运行模式决定订单执行方式
3. 处理订单执行失败重试
4. 规范化订单执行结果

运行模式:
- paper: 模拟交易模式
  - 不实际下单
  - 直接返回模拟成交结果
  - 用于策略测试和验证

- shadow: 影子模式
  - 不实际下单
  - 记录决策但不执行
  - 用于实盘前验证

- live: 实盘模式
  - 实际下单到交易所
  - 支持失败重试
  - 用于真实交易

订单执行流程:
```
订单请求
    │
    ▼
检查订单有效性(quote/quantity > 0)
    │
    ├─► 无效: 返回SKIPPED状态
    │
    └─► 有效:
            │
            ├─► paper模式: 返回模拟成交结果
            │
            ├─► shadow模式: 返回PENDING状态
            │
            └─► live模式:
                    │
                    ▼
                选择交易所适配器(Binance/OKX)
                    │
                    ▼
                执行下单(支持重试)
                    │
                    ▼
                返回执行结果
```

支持的交易所:
- Binance Futures: 币安合约
- OKX Futures: OKX合约
"""

from trade_runtime.execution.binance_futures import BinanceFuturesExecutionAdapter
from trade_runtime.execution.clients import coerce_binance_execution_client
from trade_runtime.execution.okx_futures import OkxFuturesExecutionAdapter


class ExecutionRouter:
    """执行路由器

    根据交易所类型和运行模式，将订单路由到相应的执行客户端。

    Attributes:
        binance_client: Binance执行客户端
        okx_client: OKX执行客户端
        max_live_attempts: 实盘订单最大重试次数
    """

    def __init__(self, binance_client, okx_client, max_live_attempts: int = 2):
        """初始化执行路由器

        Args:
            binance_client: Binance执行客户端
            okx_client: OKX执行客户端
            max_live_attempts: 实盘订单最大重试次数，默认为2
        """
        self.binance_client = binance_client
        self.okx_client = okx_client
        self.max_live_attempts = max(1, max_live_attempts)

    def _live_adapter(self, exchange: str):
        """获取实盘执行适配器

        Args:
            exchange: 交易所代码，"binance" 或 "okx"

        Returns:
            对应交易所的执行适配器实例
        """
        return (
            BinanceFuturesExecutionAdapter(coerce_binance_execution_client(self.binance_client))
            if exchange == "binance"
            else OkxFuturesExecutionAdapter(self.okx_client)
        )

    def _is_retriable_failure(self, result: dict) -> bool:
        """判断订单失败是否可重试

        Args:
            result: 订单执行结果

        Returns:
            bool: 是否可重试
        """
        if result.get("status") != "failed":
            return False
        error = str(result.get("error") or "").lower()
        retriable_markers = (
            "timeout",
            "temporarily unavailable",
            "temporary unavailable",
            "connection reset",
            "network",
            "rate limit",
            "too many requests",
            "service unavailable",
        )
        return any(marker in error for marker in retriable_markers)

    def _should_use_enhanced_order(self, exchange: str, order: dict) -> bool:
        """判断是否使用增强订单类型

        Args:
            exchange: 交易所代码
            order: 订单信息

        Returns:
            bool: 是否使用增强订单
        """
        if exchange != "okx":
            return False
        order_type = str(order.get("order_type") or "market").strip().lower()
        return order_type == "limit" or bool(order.get("okx_enhanced_execution", False))

    def _place_live_order(self, adapter, exchange: str, order: dict) -> dict:
        """下单执行

        Args:
            adapter: 执行适配器
            exchange: 交易所代码
            order: 订单信息

        Returns:
            dict: 执行结果
        """
        if exchange == "okx" and hasattr(adapter, "place_order"):
            return adapter.place_order(order)
        if self._should_use_enhanced_order(exchange, order) and hasattr(adapter, "place_order"):
            return adapter.place_order(order)
        return adapter.place_market_order(order)

    def _normalize_mode(self, mode: str) -> str:
        normalized = str(mode or "paper").strip().lower()
        if normalized not in {"paper", "shadow", "live"}:
            raise ValueError(f"Unsupported runtime mode: {mode}")
        return normalized

    def _order_context(self, order: dict) -> dict:
        price = float(order.get("price", 0) or 0)
        quote = float(order.get("quote", 0) or 0)
        quantity_base = float(order.get("quantity_base") or 0)
        fill_quantity = round(quantity_base, 8) if quantity_base > 0 else round(quote / price, 8) if price > 0 else 0.0
        return {
            "price": price,
            "quote": quote,
            "quantity_base": quantity_base,
            "fill_quantity": fill_quantity,
        }

    def _result(
        self,
        *,
        mode: str,
        exchange: str,
        order_id: str,
        status: str,
        order_status: str,
        context: dict,
        fill_quantity: float,
        position_quantity: float,
    ) -> dict:
        return {
            "status": status,
            "is_live": mode == "live",
            "exchange": exchange,
            "order_id": order_id,
            "order_status": order_status,
            "fill_price": context["price"],
            "fill_quantity": fill_quantity,
            "position_quantity": position_quantity,
            "entry_price": context["price"],
        }

    def _simulated_order_id(self, mode: str, order: dict) -> str:
        if mode == "paper":
            order_ref = str(order.get("trace_id") or order.get("client_id") or order.get("symbol") or "")
            return f"paper-{order_ref}"
        return f"shadow-{order.get('symbol', '')}"

    def _execute_non_live_order(self, *, mode: str, exchange: str, order: dict, context: dict) -> dict:
        if mode == "paper":
            return self._result(
                mode=mode,
                exchange=exchange,
                order_id=self._simulated_order_id(mode, order),
                status="filled",
                order_status="FILLED",
                context=context,
                fill_quantity=context["fill_quantity"],
                position_quantity=context["fill_quantity"],
            )
        return self._result(
            mode=mode,
            exchange=exchange,
            order_id=self._simulated_order_id(mode, order),
            status="pending",
            order_status="PENDING",
            context=context,
            fill_quantity=0.0,
            position_quantity=0.0,
        )

    def _execute_live_order(self, *, exchange: str, order: dict) -> dict:
        adapter = self._live_adapter(exchange)
        result = self._place_live_order(adapter, exchange, order)
        attempts = 1
        while attempts < self.max_live_attempts and self._is_retriable_failure(result):
            result = self._place_live_order(adapter, exchange, order)
            attempts += 1
        return result

    def execute(self, *, mode: str, exchange: str, order: dict) -> dict:
        """执行订单

        根据运行模式（paper/shadow/live）执行订单：
        - paper模式：模拟成交，返回成功结果
        - shadow模式：影子模式，不实际下单
        - live模式：实盘下单，支持重试

        Args:
            mode: 运行模式，"paper"、"shadow" 或 "live"
            exchange: 交易所代码
            order: 订单信息，包含symbol、side、quote、price等字段

        Returns:
            dict: 执行结果，包含status、order_id、fill_price、fill_quantity等字段
        """
        mode = self._normalize_mode(mode)
        context = self._order_context(order)
        if context["quote"] <= 0 and context["quantity_base"] <= 0:
            return self._result(
                mode=mode,
                exchange=exchange,
                order_id="",
                status="skipped",
                order_status="SKIPPED",
                context=context,
                fill_quantity=0.0,
                position_quantity=0.0,
            )
        if mode in {"paper", "shadow"}:
            return self._execute_non_live_order(mode=mode, exchange=exchange, order=order, context=context)
        return self._execute_live_order(exchange=exchange, order=order)
