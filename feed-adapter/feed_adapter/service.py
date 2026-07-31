"""
数据适配器服务模块

提供统一的数据源访问接口，支持新闻、社交、链上等多种数据源的获取和缓存。
"""

from __future__ import annotations

import logging
from typing import Any

from feed_adapter.models import UpstreamUnavailableError

logger = logging.getLogger(__name__)


class FeedAdapterService:
    """数据适配器服务

    统一管理多种数据源的访问，包括新闻、社交和链上数据。
    提供健康检查和统一的数据获取接口。

    Attributes:
        news_provider: 新闻数据提供者
        social_provider: 社交数据提供者
        onchain_provider: 链上数据提供者
    """

    def __init__(self, *, news_provider: Any, social_provider: Any, onchain_provider: Any):
        """初始化数据适配器服务

        Args:
            news_provider: 新闻数据提供者
            social_provider: 社交数据提供者
            onchain_provider: 链上数据提供者
        """
        self.news_provider = news_provider
        self.social_provider = social_provider
        self.onchain_provider = onchain_provider

    def handle(self, route: str, query: dict[str, str]) -> dict[str, Any]:
        """处理数据请求

        根据路由路径分发到对应的数据提供者。

        Args:
            route: 请求路由路径
            query: 查询参数，包含symbol等字段

        Returns:
            dict[str, Any]: 响应结果，包含items、source_status等字段
        """
        normalized_route = str(route or "").strip("/")
        if normalized_route == "health":
            return {"status": "ok"}
        if normalized_route == "runtime/news":
            return self._handle_source(normalized_route, "news", query.get("symbol", ""), self.news_provider)
        if normalized_route == "runtime/social":
            return self._handle_source(normalized_route, "social", query.get("symbol", ""), self.social_provider)
        if normalized_route == "runtime/onchain":
            return self._handle_source(normalized_route, "onchain", query.get("symbol", ""), self.onchain_provider)
        return {"error": "not_found", "route": normalized_route}

    def _handle_source(self, route: str, source_name: str, symbol: str, provider: Any) -> dict[str, Any]:
        """处理单个数据源请求

        Args:
            route: 请求路由
            source_name: 数据源名称
            symbol: 交易品种
            provider: 数据提供者

        Returns:
            dict[str, Any]: 响应结果
        """
        normalized_symbol = str(symbol or "").strip().upper()
        logger.info(
            "feed_adapter_request route=%s source=%s symbol=%s",
            route,
            source_name,
            normalized_symbol or "-",
        )
        try:
            items = list(provider.fetch(normalized_symbol))
        except UpstreamUnavailableError as exc:
            logger.warning(
                "feed_adapter_result route=%s source=%s symbol=%s source_status=unavailable error=%s",
                route,
                source_name,
                normalized_symbol or "-",
                str(exc),
            )
            return {
                "items": [],
                "source_status": "unavailable",
                "source_name": source_name,
                "error_message": str(exc),
            }
        logger.info(
            "feed_adapter_result route=%s source=%s symbol=%s source_status=ready items=%s",
            route,
            source_name,
            normalized_symbol or "-",
            len(items),
        )
        return {
            "items": items,
            "source_status": "ready",
            "source_name": source_name,
        }
