"""
决策状态模块 - 定义决策流程中的数据结构

定义交易决策流程中使用的状态字典结构，包含所有节点间传递的数据字段。

状态数据流转:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DecisionState 结构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 基础信息层                                                                   │
│   trace_id: 追踪ID，用于日志追踪和问题排查                                    │
│   symbol: 交易品种(如BTCUSDT)                                                │
│   exchange: 交易所代码(如binance/okx)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 事件数据层                                                                   │
│   event_bundle: 事件包列表，包含触发决策的所有事件                            │
│   event_strength: 事件强度(strong/normal/noise)                              │
│   feature_snapshot: 特征快照，包含市场、新闻、链上、社交等特征                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 触发信息层                                                                   │
│   dispatch_mode: 分发模式(NO_DISPATCH/RULE_ONLY/LLM_ALLOWED)                 │
│   selected_agents: 选中的Agent列表                                           │
│   trigger_reason: 触发原因                                                   │
│   active_signals: 活跃信号列表                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Agent观点层                                                                  │
│   market_view: 市场Agent观点                                                 │
│   news_view: 新闻Agent观点                                                   │
│   onchain_view: 链上Agent观点                                                │
│   social_view: 社交Agent观点                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 决策结果层                                                                   │
│   supervisor_decision: 主管决策结果                                          │
│   risk_result: 风控检查结果                                                  │
│   execution_result: 订单执行结果                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 账户状态层                                                                   │
│   account_equity: 账户权益                                                   │
│   daily_pnl: 日盈亏                                                          │
│   current_position_side: 当前仓位方向(long/short/flat)                       │
│   current_position_quantity: 当前仓位数量                                    │
│   entry_price: 入场价格                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 记忆数据层                                                                   │
│   short_term_memory: 短期记忆(最近交易历史)                                   │
│   long_term_memory: 长期记忆(历史决策和结果)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```
"""

from typing import Any, TypedDict


class DecisionState(TypedDict, total=False):
    """决策状态类型定义

    定义决策图中各节点间传递的状态结构，包含：
    - 基础信息：trace_id、symbol、exchange
    - 事件数据：event_bundle、event_strength、feature_snapshot
    - 触发信息：dispatch_mode、selected_agents、trigger_reason
    - Agent观点：market_view、news_view、onchain_view、social_view
    - 决策结果：supervisor_decision、risk_result、execution_result
    - 账户状态：account_equity、daily_pnl、current_position_side等
    - 记忆数据：short_term_memory、long_term_memory

    Attributes:
        trace_id: 追踪ID
        symbol: 交易品种
        exchange: 交易所代码
        event_bundle: 事件包列表
        event_strength: 事件强度（noise/normal/strong）
        feature_snapshot: 特征快照
        market_context_history: 市场上下文历史
        signal_window_states: 信号窗口状态列表
        strategy_context: 策略上下文
        dispatch_mode: 分发模式（NO_DISPATCH/RULE_ONLY/LLM_ALLOWED）
        selected_agents: 选中的Agent列表
        trigger_reason: 触发原因
        trigger_source: 触发来源
        active_signals: 活跃信号列表
        combination_match: 组合匹配信息
        trigger_strength_source: 触发强度来源
        active_signal_refs: 活跃信号引用
        cooldown_blocked: 是否被冷却期阻止
        budget_blocked: 是否被预算限制阻止
        rule_only_reason: 仅规则模式原因
        suppression_reason_codes: 抑制原因代码
        prompt_bindings: 提示绑定列表
        agent_profiles: Agent配置列表
        deliberation_policy: 审议策略
        agent_messages: Agent消息列表
        deliberation_summary: 审议摘要
        market_view: 市场观点
        news_view: 新闻观点
        onchain_view: 链上观点
        social_view: 社交观点
        ai_call_failed: AI调用是否失败
        agent_llm_errors: Agent LLM错误列表
        supervisor_decision: 主管决策
        audit_payload: 审计数据
        risk_result: 风控结果
        execution_result: 执行结果
        mode: 运行模式
        requested_mode: 请求的模式
        effective_mode: 有效模式
        mode_downgraded: 模式是否降级
        market_source_status: 市场数据源状态
        market_source_context: 市场数据源上下文
        multi_agent_runtime: 多Agent运行时信息
        agent_circuit_breaker: Agent熔断器状态
        runtime_config: 运行时配置
        runtime_account_context: 运行时账户上下文
        exchange_account: 交易所账户
        current_position_side: 当前仓位方向
        current_position_quantity: 当前仓位数量
        current_position_notional: 当前仓位名义价值
        current_position_opened_at: 当前仓位开仓时间
        current_time: 当前决策时间
        current_position_holding_minutes: 当前仓位持仓分钟数
        entry_price: 入场价格
        account_equity: 账户权益
        requested_notional: 请求的名义价值
        daily_pnl: 日盈亏
        realized_pnl: 已实现盈亏
        unrealized_pnl: 未实现盈亏
        max_drawdown_pct: 最大回撤百分比
        peak_account_equity: 峰值账户权益
        consecutive_failures: 连续失败次数
        risk_guard: 风控守卫
        execution_router: 执行路由器
        callback_client: 回调客户端
        decision_model_client: 决策模型客户端
        prompt_template_registry: 提示模板注册表
        memory_store: 记忆存储
        short_term_memory: 短期记忆
        long_term_memory: 长期记忆
        memory_usage: 记忆使用情况
        memory_retrieval_status: 记忆检索状态
        supervisor_prompt_metadata: 主管提示元数据
        pnl_snapshot_payload: 盈亏快照数据
        timestamp_supplier: 时间戳供应器
        ingestedAt: 摄入时间
        classifiedAt: 分类时间
        supervisedAt: 主管决策时间
        riskCheckedAt: 风控检查时间
        executedAt: 执行时间
    """
    trace_id: str
    symbol: str
    exchange: str
    event_bundle: list[dict[str, Any]]
    event_strength: str
    feature_snapshot: dict[str, Any]
    market_context_history: list[dict[str, Any]]
    signal_window_states: list[dict[str, Any]]
    strategy_context: dict[str, Any]
    dispatch_mode: str
    selected_agents: list[str]
    trigger_reason: str
    trigger_source: str
    active_signals: list[dict[str, Any]]
    combination_match: dict[str, Any]
    trigger_strength_source: str
    active_signal_refs: list[str]
    cooldown_blocked: bool
    budget_blocked: bool
    rule_only_reason: str
    suppression_reason_codes: list[str]
    prompt_bindings: list[dict[str, Any]]
    agent_profiles: list[dict[str, Any]]
    resolved_agent_configs: list[dict[str, Any]]
    deliberation_policy: dict[str, Any]
    agent_messages: list[dict[str, Any]]
    deliberation_summary: str
    deliberation_referee_review: dict[str, Any]
    deliberation_referee_error: str
    deliberation_referee_prompt_metadata: dict[str, Any]
    market_view: dict[str, Any]
    news_view: dict[str, Any]
    onchain_view: dict[str, Any]
    social_view: dict[str, Any]
    ai_call_failed: bool
    agent_llm_errors: list[dict[str, Any]]
    supervisor_decision: dict[str, Any]
    audit_payload: dict[str, Any]
    risk_result: dict[str, Any]
    execution_result: dict[str, Any]
    mode: str
    requested_mode: str
    effective_mode: str
    mode_downgraded: bool
    market_source_status: str
    market_source_context: dict[str, Any]
    multi_agent_runtime: dict[str, Any]
    agent_circuit_breaker: dict[str, Any]
    runtime_config: dict[str, Any]
    runtime_account_context: dict[str, Any]
    exchange_account: dict[str, Any]
    current_position_side: str
    current_position_quantity: float
    current_position_notional: float
    current_position_opened_at: str
    current_time: str
    current_position_holding_minutes: int
    entry_price: float
    account_equity: float
    requested_notional: float
    daily_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    max_drawdown_pct: float
    peak_account_equity: float
    consecutive_failures: int
    risk_guard: Any
    execution_router: Any
    callback_client: Any
    decision_model_client: Any
    prompt_template_registry: Any
    memory_store: Any
    lifecycle_manager: Any
    short_term_memory: dict[str, Any]
    long_term_memory: dict[str, Any]
    memory_usage: dict[str, Any]
    memory_retrieval_status: str
    lifecycle_status: dict[str, Any]
    trade_memory_status: dict[str, Any]
    supervisor_prompt_metadata: dict[str, Any]
    pnl_snapshot_payload: dict[str, Any]
    timestamp_supplier: Any
    ingestedAt: str
    classifiedAt: str
    supervisedAt: str
    riskCheckedAt: str
    executedAt: str
