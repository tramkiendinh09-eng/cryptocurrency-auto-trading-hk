"""
决策图模块 - 交易决策的核心流程编排

构建和管理交易决策的执行流程图，定义各节点之间的路由逻辑。

决策流程图结构:
```
ingest_context (摄入上下文)
       │
       ▼
build_feature_snapshot (构建特征快照)
       │
       ▼
classify (事件强度分类)
       │
       ▼
retrieve_memory (检索记忆)
       │
       ├─────────────────────────────────────────────┐
       │                                             │
       ▼                                             ▼
multi_agent (多Agent并行处理) ──────────────► 单Agent路由
       │                    │
       │                    ├─► market_agent (市场Agent)
       │                    ├─► news_agent (新闻Agent)
       │                    ├─► onchain_agent (链上Agent)
       │                    └─► social_agent (社交Agent)
       │
       ▼
deliberation_node (审议节点) - 可选
       │
       ▼
supervisor (主管决策)
       │
       ▼
risk_gate (风控检查)
       │
       ▼
execute_order (执行订单)
       │
       ▼
audit (审计记录)
       │
       ▼
      END
```

节点说明:
- ingest_context: 摄入事件包和特征快照，构建决策上下文
- build_feature_snapshot: 从多数据源构建特征快照
- classify: 根据触发策略分类事件强度(strong/normal/noise)
- retrieve_memory: 检索短期和长期记忆
- multi_agent: 并行调用多个专业Agent进行分析
- deliberation_node: Agent间审议讨论(可选)
- supervisor: 汇总各Agent观点，做出最终决策
- risk_gate: 风控检查，决定是否执行
- execute_order: 执行订单
- audit: 记录审计日志
"""

from langgraph.graph import END, StateGraph

from trade_runtime.config import _parse_json_object

from trade_runtime.decision.dispatch import derive_dispatch_mode, has_explicit_dispatch_mode, llm_dispatch_allowed, normalize_selected_agents
from trade_runtime.decision.nodes.audit import audit_node
from trade_runtime.decision.nodes.build_feature_snapshot import build_feature_snapshot_node
from trade_runtime.decision.nodes.classify import classify_event_strength
from trade_runtime.decision.deliberation import should_run_deliberation
from trade_runtime.decision.nodes.deliberation_node import deliberation_node
from trade_runtime.decision.nodes.execution_node import execution_node
from trade_runtime.decision.nodes.ingest_context import ingest_context_node
from trade_runtime.decision.nodes.lifecycle_node import lifecycle_node
from trade_runtime.decision.nodes.market_agent import market_agent
from trade_runtime.decision.nodes.multi_agent_node import multi_agent_node
from trade_runtime.decision.nodes.news_agent import news_agent
from trade_runtime.decision.nodes.onchain_agent import onchain_agent
from trade_runtime.decision.nodes.risk_guard_node import risk_guard_node
from trade_runtime.decision.nodes.retrieve_memory import retrieve_memory_node
from trade_runtime.decision.nodes.social_agent import social_agent
from trade_runtime.decision.nodes.supervisor_agent import supervisor_agent
from trade_runtime.decision.state import DecisionState
from trade_runtime.risk.guard import is_healthy_aux_source_status


def _has_market_source_issue(state: DecisionState) -> bool:
    """检查市场数据源是否存在问题

    Args:
        state: 决策状态

    Returns:
        bool: 是否存在市场数据源问题
    """
    normalized_status = str(state.get("market_source_status", "")).strip().lower()
    if normalized_status in {"abnormal", "stale", "degraded", "unavailable"}:
        return True
    for event in state.get("event_bundle") or []:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type", "")).strip().lower()
        if event_type in {"stale", "source_abnormal", "market_source_abnormal"}:
            return True
    return False


def _halt_on_data_gap_enabled(state: DecisionState) -> bool:
    """检查是否启用了数据缺失时暂停功能

    Args:
        state: 决策状态

    Returns:
        bool: 是否启用数据缺失暂停
    """
    runtime_config = state.get("runtime_config") or {}
    policy = _parse_json_object(runtime_config.get("runtime_flags_json") or runtime_config.get("runtimeFlagsJson"))
    value = policy.get("haltOnDataGap")
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _has_aux_source_issue(state: DecisionState) -> bool:
    """检查辅助数据源是否存在问题

    Args:
        state: 决策状态

    Returns:
        bool: 是否存在辅助数据源问题
    """
    feature_snapshot = state.get("feature_snapshot") or {}
    if not isinstance(feature_snapshot, dict):
        feature_snapshot = {}
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
    return False


def _route_after_classify(state: DecisionState) -> str:
    """分类后的路由决策

    根据事件强度和数据源状态决定下一步路由：
    - 数据源异常时进入风控检查
    - 强事件进入多Agent或单Agent处理
    - 噪音事件直接进入审计

    Args:
        state: 决策状态

    Returns:
        str: 下一个节点名称
    """
    if _has_market_source_issue(state):
        return "risk_gate"
    if _halt_on_data_gap_enabled(state) and _has_aux_source_issue(state):
        return "risk_gate"
    dispatch_mode = derive_dispatch_mode(state)
    if has_explicit_dispatch_mode(state):
        return "audit" if dispatch_mode == "NO_DISPATCH" else "multi_agent"
    event_strength = state.get("event_strength")
    if event_strength == "noise":
        return "audit"
    if event_strength == "strong":
        return _route_strong_event(state)
    return "multi_agent"


def _strong_event_requires_multi_agent(state: DecisionState) -> bool:
    """判断强事件是否需要多Agent处理

    Args:
        state: 决策状态

    Returns:
        bool: 是否需要多Agent处理
    """
    if derive_dispatch_mode(state) != "LLM_ALLOWED":
        return False
    selected_agents = normalize_selected_agents(state.get("selected_agents"))
    if len(selected_agents) >= 2:
        return True
    trigger_context = state.get("trigger_context") or state.get("trigger_matrix_context") or {}
    if isinstance(trigger_context, dict):
        sources = trigger_context.get("sources") or trigger_context.get("source_types")
        if isinstance(sources, list) and len({str(item or "").strip().lower() for item in sources if str(item or "").strip()}) >= 2:
            return True
    if not has_explicit_dispatch_mode(state):
        return True
    return False


def _route_strong_event(state: DecisionState) -> str:
    """路由强事件到合适的Agent

    根据特征快照和事件类型计算各Agent的得分，
    选择得分最高的Agent处理。

    Args:
        state: 决策状态

    Returns:
        str: 目标Agent节点名称
    """
    if _strong_event_requires_multi_agent(state):
        return "multi_agent"
    feature_snapshot = state.get("feature_snapshot", {})
    event_bundle = state.get("event_bundle") or []

    source_scores = {
        "market_agent": abs(float(feature_snapshot.get("price_change_pct", 0.0) or 0.0)) / 5.0,
        "news_agent": abs(float(feature_snapshot.get("news_score", 0.0) or 0.0)) / 0.9,
        "onchain_agent": abs(float(feature_snapshot.get("onchain_flow_bias", 0.0) or 0.0)) / 0.9,
        "social_agent": abs(float(feature_snapshot.get("social_score", 0.0) or 0.0)) / 0.9,
    }

    for event in event_bundle:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type", "")).strip().lower()
        if event_type == "news":
            source_scores["news_agent"] += 0.1
        elif event_type == "onchain":
            source_scores["onchain_agent"] += 0.1
        elif event_type == "social":
            source_scores["social_agent"] += 0.1
        elif event_type.startswith("market") or event_type in {"ticker", "liquidation", "mark_price", "funding_rate"}:
            source_scores["market_agent"] += 0.1

    return max(source_scores, key=source_scores.get)


def _route_after_market_agent(state: DecisionState) -> str:
    """市场Agent处理后的路由

    Args:
        state: 决策状态

    Returns:
        str: 下一个节点名称
    """
    return "supervisor" if state.get("event_strength") == "strong" else "news_agent"


def _route_after_news_agent(state: DecisionState) -> str:
    """新闻Agent处理后的路由

    Args:
        state: 决策状态

    Returns:
        str: 下一个节点名称
    """
    return "supervisor" if state.get("event_strength") == "strong" else "onchain_agent"


def _route_after_onchain_agent(state: DecisionState) -> str:
    """链上Agent处理后的路由

    Args:
        state: 决策状态

    Returns:
        str: 下一个节点名称
    """
    return "supervisor" if state.get("event_strength") == "strong" else "social_agent"


def _route_after_multi_agent(state: DecisionState) -> str:
    """多Agent处理后的路由

    Args:
        state: 决策状态

    Returns:
        str: 下一个节点名称
    """
    if not llm_dispatch_allowed(state):
        return "audit"
    return "deliberation_node" if should_run_deliberation(state) else "supervisor"


def build_decision_graph():
    """构建决策图

    创建并配置交易决策的状态图，定义所有节点和边：
    - ingest_context: 摄入上下文
    - build_feature_snapshot: 构建特征快照
    - classify: 分类事件强度
    - retrieve_memory: 检索记忆
    - multi_agent: 多Agent并行处理
    - deliberation_node: 审议节点
    - market_agent/news_agent/onchain_agent/social_agent: 单Agent处理
    - supervisor: 主管决策
    - risk_gate: 风控检查
    - execute_order: 执行订单
    - audit: 审计记录

    Returns:
        CompiledGraph: 编译后的决策图
    """
    graph = StateGraph(DecisionState)
    graph.add_node("ingest_context", ingest_context_node)
    graph.add_node("build_feature_snapshot", build_feature_snapshot_node)
    graph.add_node("classify", classify_event_strength)
    graph.add_node("retrieve_memory", retrieve_memory_node)
    graph.add_node("multi_agent", multi_agent_node)
    graph.add_node("deliberation_node", deliberation_node)
    graph.add_node("market_agent", market_agent)
    graph.add_node("news_agent", news_agent)
    graph.add_node("onchain_agent", onchain_agent)
    graph.add_node("social_agent", social_agent)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("risk_gate", risk_guard_node)
    graph.add_node("execute_order", execution_node)
    graph.add_node("trade_lifecycle", lifecycle_node)
    graph.add_node("audit", audit_node)
    graph.set_entry_point("ingest_context")
    graph.add_edge("ingest_context", "build_feature_snapshot")
    graph.add_edge("build_feature_snapshot", "classify")
    graph.add_edge("classify", "retrieve_memory")
    graph.add_conditional_edges(
        "retrieve_memory",
        _route_after_classify,
        {
            "multi_agent": "multi_agent",
            "market_agent": "market_agent",
            "news_agent": "news_agent",
            "onchain_agent": "onchain_agent",
            "social_agent": "social_agent",
            "risk_gate": "risk_gate",
            "audit": "audit",
        },
    )
    graph.add_conditional_edges(
        "multi_agent",
        _route_after_multi_agent,
        {
            "audit": "audit",
            "deliberation_node": "deliberation_node",
            "supervisor": "supervisor",
        },
    )
    graph.add_conditional_edges(
        "market_agent",
        _route_after_market_agent,
        {
            "supervisor": "supervisor",
            "news_agent": "news_agent",
        },
    )
    graph.add_conditional_edges(
        "news_agent",
        _route_after_news_agent,
        {
            "supervisor": "supervisor",
            "onchain_agent": "onchain_agent",
        },
    )
    graph.add_conditional_edges(
        "onchain_agent",
        _route_after_onchain_agent,
        {
            "supervisor": "supervisor",
            "social_agent": "social_agent",
        },
    )
    graph.add_edge("social_agent", "supervisor")
    graph.add_edge("deliberation_node", "supervisor")
    graph.add_edge("supervisor", "risk_gate")
    graph.add_edge("risk_gate", "execute_order")
    graph.add_edge("execute_order", "trade_lifecycle")
    graph.add_edge("trade_lifecycle", "audit")
    graph.add_edge("audit", END)
    return graph.compile()
