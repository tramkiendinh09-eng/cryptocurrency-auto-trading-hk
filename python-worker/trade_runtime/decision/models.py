"""
决策模型模块

定义交易决策相关的数据模型，包括Agent观点和主管决策模型。
"""

from pydantic import BaseModel


class AgentView(BaseModel):
    """Agent观点模型

    存储单个Agent对市场的分析和判断结果。

    Attributes:
        bias: 市场倾向，可选值为 "bullish"（看涨）、"bearish"（看跌）、"neutral"（中性）
        confidence: 置信度，范围0-100
        reason: 判断理由描述
        ttl: 观点有效期（秒）
        risk_note: 风险提示
    """
    bias: str
    confidence: int
    reason: str
    ttl: int
    risk_note: str


class SupervisorDecision(BaseModel):
    """主管决策模型

    汇总各Agent观点后形成的最终交易决策。

    Attributes:
        action: 交易动作，可选值为 "LONG"（做多）、"SHORT"（做空）、"CLOSE"（平仓）、"HOLD"（持有）、"SKIP"（跳过）
        side: 交易方向，可选值为 "long"、"short"、"flat"
        confidence: 决策置信度，范围0-100
        size_hint: 仓位大小建议（占账户权益比例）
        leverage_hint: 杠杆建议，默认为3倍
        holding_window: 建议持仓时间窗口
        invalidation: 失效条件描述
        summary_reason: 决策理由摘要
        model_code: 使用的模型代码
        model_provider: 模型提供商
    """
    action: str
    side: str
    confidence: int
    size_hint: float
    leverage_hint: int = 3
    holding_window: str = "15m-4h"
    invalidation: str = ""
    summary_reason: str = ""
    model_code: str = ""
    model_provider: str = ""

    model_config = {
        "protected_namespaces": (),
    }

