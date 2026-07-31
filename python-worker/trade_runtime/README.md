# AI加密货币交易系统 - 项目流程概述

## 一、系统架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              交易运行时系统架构                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐               │
│  │ 数据摄入层    │───▶│ 触发策略评估      │───▶│ 决策图执行       │               │
│  │ (Ingestion)  │    │ (Trigger Policy) │    │ (Decision Graph)│               │
│  └──────────────┘    └──────────────────┘    └─────────────────┘               │
│        │                    │                       │                          │
│        ▼                    ▼                       ▼                          │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐               │
│  │ - 市场行情    │    │ - 事件强度分类    │    │ - 多Agent协作    │               │
│  │ - 新闻资讯    │    │ - 信号组合匹配    │    │ - 主管决策       │               │
│  │ - 链上数据    │    │ - 冷却期/预算控制 │    │ - 风控检查       │               │
│  │ - 社交舆情    │    │ - LLM调用预算     │    │ - 订单执行       │               │
│  └──────────────┘    └──────────────────┘    └─────────────────┘               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 二、核心模块说明

### 1. 主入口 (main.py)
- **文件**: `python-worker/main.py`
- **功能**: 解析工作配置，启动交易运行时
- **环境变量**: `WORKER_PROFILE`, `TRADE_RUNTIME_LOG_LEVEL`

### 2. 运行时应用 (app.py)
- **文件**: `python-worker/trade_runtime/app.py`
- **功能**: 管理交易运行时的执行流程
- **核心类**: `TradeRuntimeApp`, `RuntimeContext`

### 3. 配置管理 (config.py)
- **文件**: `python-worker/trade_runtime/config.py`
- **功能**: 定义运行时配置模型
- **核心类**: `RuntimeConfig`, `RuntimeBootstrap`, `RuntimeExchangeAccount`

### 4. 决策图 (decision/graph.py)
- **文件**: `python-worker/trade_runtime/decision/graph.py`
- **功能**: 构建和管理交易决策的执行流程图
- **核心函数**: `build_decision_graph()`

### 5. 触发策略 (trigger_policy.py)
- **文件**: `python-worker/trade_runtime/trigger_policy.py`
- **功能**: 评估是否应该触发交易决策
- **核心函数**: `evaluate_trigger_policy()`, `classify_event_strength_from_policy()`

### 6. 执行路由 (execution/router.py)
- **文件**: `python-worker/trade_runtime/execution/router.py`
- **功能**: 将订单路由到正确的交易所执行
- **核心类**: `ExecutionRouter`

## 三、决策流程详解

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           决策图执行流程                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. ingest_context (摄入上下文)                                              │
│     │  - 摄入事件包(event_bundle)                                           │
│     │  - 摄入特征快照(feature_snapshot)                                      │
│     │  - 构建决策上下文                                                      │
│     ▼                                                                       │
│  2. build_feature_snapshot (构建特征快照)                                    │
│     │  - 从多数据源构建特征                                                  │
│     │  - 市场特征: 价格变化、成交量、资金费率                                 │
│     │  - 新闻特征: 情绪得分                                                  │
│     │  - 链上特征: 资金流向                                                  │
│     │  - 社交特征: 舆情得分                                                  │
│     ▼                                                                       │
│  3. classify (事件强度分类)                                                   │
│     │  - 根据触发策略分类事件强度                                            │
│     │  - strong: 强事件，需要LLM决策                                         │
│     │  - normal: 普通事件，规则决策                                          │
│     │  - noise: 噪音事件，跳过                                               │
│     ▼                                                                       │
│  4. retrieve_memory (检索记忆)                                               │
│     │  - 检索短期记忆(最近交易历史)                                           │
│     │  - 检索长期记忆(历史决策和结果)                                         │
│     ▼                                                                       │
│  5. multi_agent (多Agent并行处理)                                            │
│     │  - market_agent: 市场分析                                             │
│     │  - news_agent: 新闻分析                                               │
│     │  - onchain_agent: 链上分析                                            │
│     │  - social_agent: 社交分析                                             │
│     ▼                                                                       │
│  6. deliberation_node (审议节点) - 可选                                      │
│     │  - Agent间审议讨论                                                    │
│     │  - 生成审议摘要                                                       │
│     ▼                                                                       │
│  7. supervisor (主管决策)                                                    │
│     │  - 汇总各Agent观点                                                    │
│     │  - 调用LLM生成最终决策                                                 │
│     │  - 输出: action, side, confidence, size_hint                          │
│     ▼                                                                       │
│  8. risk_gate (风控检查)                                                     │
│     │  - 仓位限制检查                                                       │
│     │  - 日亏损检查                                                         │
│     │  - 连续失败检查                                                       │
│     │  - 数据源状态检查                                                     │
│     ▼                                                                       │
│  9. execute_order (执行订单)                                                 │
│     │  - 根据运行模式执行订单                                                │
│     │  - paper: 模拟成交                                                    │
│     │  - shadow: 影子模式                                                   │
│     │  - live: 实盘下单                                                     │
│     ▼                                                                       │
│  10. audit (审计记录)                                                        │
│     │  - 记录决策日志                                                       │
│     │  - 发送回调通知                                                       │
│     ▼                                                                       │
│     END                                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 四、关键数据结构

### DecisionState (决策状态)
```python
{
    # 基础信息
    "trace_id": "abc123",           # 追踪ID
    "symbol": "BTCUSDT",            # 交易品种
    "exchange": "binance",          # 交易所

    # 事件数据
    "event_bundle": [...],          # 事件包列表
    "event_strength": "strong",     # 事件强度
    "feature_snapshot": {...},      # 特征快照

    # 触发信息
    "dispatch_mode": "LLM_ALLOWED", # 分发模式
    "selected_agents": [...],       # 选中的Agent

    # Agent观点
    "market_view": {...},           # 市场观点
    "news_view": {...},             # 新闻观点
    "onchain_view": {...},          # 链上观点
    "social_view": {...},           # 社交观点

    # 决策结果
    "supervisor_decision": {
        "action": "OPEN_LONG",      # 动作
        "side": "long",             # 方向
        "confidence": 75,           # 信心度
        "size_hint": 0.35,          # 仓位建议
    },
    "risk_result": {...},           # 风控结果
    "execution_result": {...},      # 执行结果

    # 账户状态
    "account_equity": 10000.0,      # 账户权益
    "daily_pnl": 150.0,             # 日盈亏
    "current_position_side": "flat", # 当前仓位方向
}
```

### SupervisorDecision (主管决策)
```python
{
    "action": "OPEN_LONG",          # 动作类型
    "side": "long",                 # 方向(long/short/flat)
    "confidence": 75,               # 信心度(0-100)
    "size_hint": 0.35,              # 仓位建议(0-1)
    "leverage_hint": 3,             # 杠杆建议
    "holding_window": "15m-4h",     # 预期持仓时间
    "invalidation": "price_drop_5%", # 失效条件
    "summary_reason": "...",        # 决策原因
}
```

## 五、运行模式

### paper (模拟交易)
- 不实际下单
- 直接返回模拟成交结果
- 用于策略测试和验证

### shadow (影子模式)
- 不实际下单
- 记录决策但不执行
- 用于实盘前验证

### live (实盘模式)
- 实际下单到交易所
- 支持失败重试
- 用于真实交易

## 六、触发策略配置

```python
{
    # 触发模式
    "triggerMode": "EVENT_GATED",

    # 市场触发条件
    "marketTrigger": {
        "priceChangePct": 2.5,           # 价格变化阈值(%)
        "ruleOnlyPriceChangePct": 1.0,   # 规则模式阈值(%)
        "liquidationNotionalUsd": 250000, # 清算金额阈值(USD)
        "fundingRateAbs": 0.001,         # 资金费率阈值
    },

    # 新闻触发条件
    "newsTrigger": {
        "scoreThreshold": 0.9,           # 强信号阈值
        "ruleOnlyScoreThreshold": 0.7,   # 规则模式阈值
    },

    # 链上触发条件
    "onchainTrigger": {
        "scoreThreshold": 0.9,
        "flowUsdThreshold": 1000000,     # 资金流阈值(USD)
    },

    # 社交触发条件
    "socialTrigger": {
        "scoreThreshold": 0.85,
    },

    # 信号组合触发矩阵
    "triggerMatrix": [
        {
            "code": "strong_news_then_break",
            "sources": ["news", "market"],
            "targetDispatchMode": "LLM_ALLOWED"
        },
    ],

    # 冷却期策略
    "cooldownPolicy": {
        "globalSeconds": 180,            # 全局冷却期(秒)
    },

    # LLM预算策略
    "llmBudgetPolicy": {
        "perSymbolDailyLimit": 30,       # 每品种每日限制
        "rollingWindowLimit": 3,         # 滑动窗口限制
        "rollingWindowMinutes": 20,      # 滑动窗口时间(分钟)
    },
}
```

## 七、风控规则

```python
{
    "max_position_ratio": 0.4,           # 最大仓位比例(40%)
    "max_daily_loss": -500.0,            # 最大日亏损(USD)
    "max_consecutive_failures": 3,       # 最大连续失败次数
    "live_order_requires_healthy_account": True,  # 实盘需要健康账户
}
```

## 八、快速上手

### 1. 启动系统
```bash
# 设置环境变量
export TRADE_RUNTIME_LOG_LEVEL=INFO
export WORKER_PROFILE=trade_runtime

# 启动
python -m python-worker.main
```

### 2. 核心文件阅读顺序
1. `main.py` - 入口文件
2. `trade_runtime/app.py` - 运行时应用
3. `trade_runtime/config.py` - 配置模型
4. `trade_runtime/decision/graph.py` - 决策图
5. `trade_runtime/trigger_policy.py` - 触发策略
6. `trade_runtime/decision/nodes/supervisor_agent.py` - 主管决策
7. `trade_runtime/execution/router.py` - 执行路由

### 3. 测试文件
- `python-worker/tests/trade_runtime/test_app.py` - 应用测试
