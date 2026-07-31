"""
多Agent节点模块 - 并行调用多个专业Agent进行分析

实现决策图中的多Agent并行处理节点，负责同时调用多个专业Agent进行分析。

多Agent架构:
```
                    ┌─────────────────┐
                    │  multi_agent    │
                    │     节点        │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  market_agent   │ │   news_agent    │ │  onchain_agent  │ ...
│   市场分析      │ │    新闻分析     │ │    链上分析     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   汇总观点      │
                    │ market_view     │
                    │ news_view       │
                    │ onchain_view    │
                    │ social_view     │
                    └─────────────────┘
```

专业Agent说明:
- market_agent: 市场分析Agent
  - 分析价格趋势、成交量、技术指标
  - 输出: 市场方向(bullish/bearish/neutral)、信心度、原因

- news_agent: 新闻分析Agent
  - 分析加密货币新闻、政策动态
  - 输出: 新闻情绪方向、信心度、关键事件

- onchain_agent: 链上分析Agent
  - 分析链上转账、智能合约活动
  - 输出: 链上活动方向、信心度、关键数据

- social_agent: 社交分析Agent
  - 分析社交媒体舆情
  - 输出: 社交情绪方向、信心度、热门话题

并行执行优势:
1. 减少总体决策时间
2. 各Agent独立分析，避免相互影响
3. 支持熔断机制，单个Agent失败不影响整体
"""

from trade_runtime.decision.nodes.market_agent import market_agent
from trade_runtime.decision.nodes.news_agent import news_agent
from trade_runtime.decision.nodes.onchain_agent import onchain_agent
from trade_runtime.decision.parallel import run_parallel_specialists
from trade_runtime.decision.nodes.social_agent import social_agent
from trade_runtime.decision.state import DecisionState


# 专业Agent运行器映射表
# 格式: (输出字段名, Agent函数)
SPECIALIST_RUNNERS = (
    ("market_view", market_agent),
    ("news_view", news_agent),
    ("onchain_view", onchain_agent),
    ("social_view", social_agent),
)


def multi_agent_node(state: DecisionState) -> DecisionState:
    """多Agent并行处理节点

    并行调用所有专业Agent进行分析，并将结果写入状态。

    Args:
        state: 决策状态

    Returns:
        DecisionState: 更新后的状态，包含:
            - market_view: 市场分析观点
            - news_view: 新闻分析观点
            - onchain_view: 链上分析观点
            - social_view: 社交分析观点
            - multi_agent_runtime: 运行时信息(耗时等)
            - agent_circuit_breaker: 熔断器状态
    """
    views, runtime, breaker_state = run_parallel_specialists(state, SPECIALIST_RUNNERS)
    for field_name, view in views.items():
        state[field_name] = view
    state["multi_agent_runtime"] = runtime
    state["agent_circuit_breaker"] = breaker_state
    return state
