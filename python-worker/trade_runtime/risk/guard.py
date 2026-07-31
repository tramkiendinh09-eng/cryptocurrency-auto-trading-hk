"""
风控守卫模块

提供交易风险控制功能，包括仓位限制、日亏损限制、连续失败限制等风控规则。
"""

from __future__ import annotations

from trade_runtime.risk.models import RiskEvaluation


HEALTHY_AUX_SOURCE_STATUSES = frozenset({"", "ready", "healthy", "ready_empty", "stale_items_filtered"})


def is_healthy_aux_source_status(value: object) -> bool:
    """检查辅助数据源状态是否健康

    Args:
        value: 数据源状态值

    Returns:
        bool: 是否为健康状态
    """
    return str(value or "").strip().lower() in HEALTHY_AUX_SOURCE_STATUSES


class RiskGuard:
    """风控守卫

    执行交易前的风险控制检查，包括：
    - 账户健康检查
    - 市场数据源状态检查
    - 辅助数据源状态检查
    - 日亏损限制检查
    - 连续失败次数检查
    - 仓位比例限制检查

    Attributes:
        max_position_ratio: 最大仓位比例
        max_daily_loss: 最大日亏损（负数）
        max_consecutive_failures: 最大连续失败次数
    """

    def __init__(
        self,
        max_position_ratio: float,
        max_daily_loss: float,
        max_consecutive_failures: int,
    ):
        """初始化风控守卫

        Args:
            max_position_ratio: 最大仓位比例，如0.4表示40%
            max_daily_loss: 最大日亏损，负数如-500表示最多亏损500
            max_consecutive_failures: 最大连续失败次数
        """
        self.max_position_ratio = max_position_ratio
        self.max_daily_loss = max_daily_loss
        self.max_consecutive_failures = max_consecutive_failures

    def evaluate(
        self,
        *,
        account_equity: float,
        requested_notional: float,
        current_position_notional: float = 0.0,
        check_position_limit: bool = True,
        daily_pnl: float,
        consecutive_failures: int,
        mode: str | None = None,
        live_order_requires_healthy_account: bool = False,
        exchange_account: dict | None = None,
        market_source_status: str | None = None,
        feature_snapshot: dict | None = None,
        halt_on_data_gap: bool = False,
        event_bundle: list[dict] | None = None,
    ) -> dict:
        """执行风控评估

        按顺序检查各项风控规则，任一规则不通过则返回失败结果。

        Args:
            account_equity: 账户权益
            requested_notional: 请求的名义价值
            current_position_notional: 当前仓位名义价值
            check_position_limit: 是否检查仓位限制
            daily_pnl: 日盈亏
            consecutive_failures: 连续失败次数
            mode: 运行模式
            live_order_requires_healthy_account: 实盘订单是否需要健康账户
            exchange_account: 交易所账户信息
            market_source_status: 市场数据源状态
            feature_snapshot: 特征快照
            halt_on_data_gap: 数据缺失时是否暂停
            event_bundle: 事件包列表

        Returns:
            dict: 风控评估结果，包含passed、reason、rule_code字段
        """
        if self._is_live_account_unhealthy(
            mode=mode,
            live_order_requires_healthy_account=live_order_requires_healthy_account,
            exchange_account=exchange_account,
        ):
            return RiskEvaluation(
                passed=False,
                reason="account_unhealthy",
                rule_code="account_unhealthy",
            ).model_dump()
        if self._is_market_source_abnormal(market_source_status=market_source_status, event_bundle=event_bundle):
            return RiskEvaluation(
                passed=False,
                reason="market_source_abnormal",
                rule_code="market_source_abnormal",
            ).model_dump()
        if self._is_aux_source_degraded(
            feature_snapshot=feature_snapshot,
            halt_on_data_gap=halt_on_data_gap,
            event_bundle=event_bundle,
        ):
            return RiskEvaluation(
                passed=False,
                reason="data_gap",
                rule_code="data_gap",
            ).model_dump()
        if daily_pnl <= self.max_daily_loss:
            return RiskEvaluation(
                passed=False,
                reason="daily_loss_limit",
                rule_code="daily_loss_limit",
            ).model_dump()
        if consecutive_failures >= self.max_consecutive_failures:
            return RiskEvaluation(
                passed=False,
                reason="consecutive_failures",
                rule_code="consecutive_failures",
            ).model_dump()
        projected_position_notional = max(0.0, float(current_position_notional or 0.0)) + max(
            0.0, float(requested_notional or 0.0)
        )
        if check_position_limit and account_equity > 0 and projected_position_notional / account_equity > self.max_position_ratio:
            return RiskEvaluation(
                passed=False,
                reason="position_limit",
                rule_code="position_limit",
            ).model_dump()
        return RiskEvaluation(passed=True, reason="pass", rule_code="pass").model_dump()

    def _is_aux_source_degraded(
        self,
        *,
        feature_snapshot: dict | None,
        halt_on_data_gap: bool,
        event_bundle: list[dict] | None,
    ) -> bool:
        """检查辅助数据源是否降级

        Args:
            feature_snapshot: 特征快照
            halt_on_data_gap: 是否在数据缺失时暂停
            event_bundle: 事件包列表

        Returns:
            bool: 是否降级
        """
        if not halt_on_data_gap:
            return False
        if isinstance(feature_snapshot, dict):
            normalized_aux_status = str(feature_snapshot.get("aux_source_status", "") or "").strip().lower()
            if normalized_aux_status == "aux_source_degraded":
                return True
            degraded_sources = feature_snapshot.get("degraded_sources")
            if isinstance(degraded_sources, list) and any(str(item or "").strip() for item in degraded_sources):
                return True
            source_health = feature_snapshot.get("source_health")
            if isinstance(source_health, dict):
                for source_type, source_status in source_health.items():
                    if str(source_type or "").strip().lower() == "market":
                        continue
                    if not is_healthy_aux_source_status(source_status):
                        return True
        for event in event_bundle or []:
            if not isinstance(event, dict):
                continue
            if str(event.get("event_type", "")).strip().lower() != "source_health":
                continue
            if str(event.get("source_type", "")).strip().lower() == "market":
                continue
            if not is_healthy_aux_source_status(event.get("source_status", "")):
                return True
        return False

    def _is_market_source_abnormal(
        self,
        *,
        market_source_status: str | None,
        event_bundle: list[dict] | None,
    ) -> bool:
        """检查市场数据源是否异常

        Args:
            market_source_status: 市场数据源状态
            event_bundle: 事件包列表

        Returns:
            bool: 是否异常
        """
        normalized_status = (market_source_status or "").strip().lower()
        if normalized_status in {"abnormal", "stale", "degraded", "unavailable"}:
            return True
        for event in event_bundle or []:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("event_type", "")).strip().lower()
            if event_type in {"stale", "source_abnormal", "market_source_abnormal"}:
                return True
        return False

    def _is_live_account_unhealthy(
        self,
        *,
        mode: str | None,
        live_order_requires_healthy_account: bool,
        exchange_account: dict | None,
    ) -> bool:
        """检查实盘账户是否不健康

        Args:
            mode: 运行模式
            live_order_requires_healthy_account: 实盘订单是否需要健康账户
            exchange_account: 交易所账户信息

        Returns:
            bool: 是否不健康
        """
        if str(mode or "").strip().lower() != "live":
            return False
        if not live_order_requires_healthy_account:
            return False
        if not isinstance(exchange_account, dict):
            return True
        health_status = str(exchange_account.get("health_status", "") or "").strip().lower()
        last_validated_at = str(exchange_account.get("last_validated_at", "") or "").strip()
        return health_status != "healthy" or not last_validated_at

