"""
特征快照构建器模块 - 构建多数据源的特征快照

负责从多个数据源(市场、新闻、链上、社交)构建统一的特征快照，
供触发策略评估和Agent分析使用。

特征快照结构:
```
{
    # 基础信息
    "symbol": "BTCUSDT",              # 交易品种
    "event_strength": "strong",       # 事件强度

    # 市场特征
    "price_change_pct": 3.5,          # 价格变化百分比
    "funding_rate": 0.0001,           # 资金费率
    "oi_change_pct": 2.1,             # 持仓量变化百分比

    # 新闻特征
    "news_score": 0.85,               # 新闻情绪得分(-1到1)

    # 社交特征
    "social_score": 0.72,             # 社交情绪得分(-1到1)

    # 链上特征
    "onchain_flow_bias": 0.65,        # 链上资金流向偏向(-1到1)
}
```

特征来源:
- price_change_pct: 市场行情WebSocket
- funding_rate: 交易所API
- oi_change_pct: 交易所API
- news_score: 新闻API(经过NLP处理)
- social_score: 社交媒体API(经过情绪分析)
- onchain_flow_bias: 链上数据分析
"""


class FeatureSnapshotBuilder:
    """特征快照构建器

    负责从多个数据源构建统一的特征快照字典。

    使用示例:
        builder = FeatureSnapshotBuilder()
        snapshot = builder.build(
            symbol="BTCUSDT",
            price_change_pct=3.5,
            funding_rate=0.0001,
            oi_change_pct=2.1,
            news_score=0.85,
            social_score=0.72,
            onchain_flow_bias=0.65,
            event_strength="strong",
        )
    """

    def build(
        self,
        *,
        symbol: str,
        price_change_pct: float,
        funding_rate: float,
        oi_change_pct: float,
        news_score: float = 0.0,
        social_score: float = 0.0,
        onchain_flow_bias: float = 0.0,
        event_strength: str = "noise",
    ) -> dict:
        """构建特征快照

        Args:
            symbol: 交易品种
            price_change_pct: 价格变化百分比
            funding_rate: 资金费率
            oi_change_pct: 持仓量变化百分比
            news_score: 新闻情绪得分(-1到1，正值看涨，负值看跌)
            social_score: 社交情绪得分(-1到1，正值看涨，负值看跌)
            onchain_flow_bias: 链上资金流向偏向(-1到1，正值流入，负值流出)
            event_strength: 事件强度(strong/normal/noise)

        Returns:
            dict: 特征快照字典
        """
        return {
            "symbol": symbol,
            "price_change_pct": price_change_pct,
            "funding_rate": funding_rate,
            "oi_change_pct": oi_change_pct,
            "news_score": news_score,
            "social_score": social_score,
            "onchain_flow_bias": onchain_flow_bias,
            "event_strength": event_strength,
        }
