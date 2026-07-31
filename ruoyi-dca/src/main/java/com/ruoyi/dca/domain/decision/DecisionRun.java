package com.ruoyi.dca.domain.decision;

import com.fasterxml.jackson.annotation.JsonAlias;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 决策运行实体类
 *
 * 记录一次完整的交易决策运行信息，包括：
 * - 基本信息：追踪ID、交易品种、运行模式
 * - 决策结果：动作、置信度、原因
 * - 触发信息：触发原因、分发模式、选中Agent
 * - 记忆数据：短期记忆、长期记忆
 * - Agent运行记录
 *
 * @author ruoyi-dca
 */
public class DecisionRun {
    /** 主键ID */
    private Long id;

    /** 追踪ID */
    private String traceId;

    /** 交易品种 */
    private String symbol;

    /** 运行模式：paper/shadow/live */
    private String mode;

    /** 决策动作 */
    private String action;

    /** 置信度（0-100） */
    private Integer confidence;

    /** 决策原因摘要 */
    private String summaryReason;

    /** 使用的模型代码 */
    private String modelCode;

    /** 模型提供商 */
    private String modelProvider;

    /** 提示来源：inline/template */
    private String promptSource;

    /** 绑定的模板代码 */
    private String bindingTemplateCode;

    /** 备用模板代码 */
    private String fallbackTemplateCode;

    /** 解析后的模板代码 */
    private String resolvedTemplateCode;

    /** 是否使用了备用模板 */
    private Boolean promptTemplateFallbackUsed;

    /** 触发原因 */
    private String triggerReason;

    /** 触发来源 */
    private String triggerSource;

    /** 分发模式：NO_DISPATCH/RULE_ONLY/LLM_ALLOWED */
    private String dispatchMode;

    /** 选中的Agent列表（JSON） */
    private String selectedAgentsJson;

    /** 组合匹配信息（JSON） */
    private String combinationMatchJson;

    /** 活跃信号引用（JSON） */
    private String activeSignalRefsJson;

    /** 是否被冷却期阻止 */
    private Boolean cooldownBlocked;

    /** 是否被预算限制阻止 */
    private Boolean budgetBlocked;

    /** 事件强度：noise/normal/strong */
    private String eventStrength;

    /** 执行状态 */
    private String executionStatus;

    /** 订单状态 */
    private String orderStatus;

    /** 创建时间 */
    private String createdAt;

    /** 特征快照 */
    private FeatureSnapshot featureSnapshot;

    /** 市场数据源配置 */
    private Map<String, Object> marketSourceConfig = new LinkedHashMap<>();

    /** 短期记忆 */
    private Map<String, Object> shortTermMemory = new LinkedHashMap<>();

    /** 长期记忆 */
    private Map<String, Object> longTermMemory = new LinkedHashMap<>();

    /** 记忆使用情况 */
    private Map<String, Object> memoryUsage = new LinkedHashMap<>();

    /** 交易后记忆生成状态 */
    private Map<String, Object> tradeMemoryStatus = new LinkedHashMap<>();

    private String tradeMemoryStatusJson;

    /** 生命周期记录状态 */
    private Map<String, Object> lifecycleStatus = new LinkedHashMap<>();

    private String lifecycleStatusJson;

    /** 信号事件列表 */
    private List<SignalEvent> signalEvents;

    /** 信号窗口状态列表 */
    private List<SignalWindowState> signalWindowStates;

    /** Agent运行记录列表 */
    private List<AgentRun> agentRuns;

    /** Agent观察记录列表 */
    private List<AgentObservation> agentObservations;

    /** Agent结论记录列表 */
    private List<AgentConclusion> agentConclusions;

    /** Agent消息列表 */
    private List<AgentMessage> agentMessages;

    /** 决策动作列表 */
    private List<DecisionAction> decisionActions;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTraceId() {
        return traceId;
    }

    @JsonAlias("trace_id")
    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public Integer getConfidence() {
        return confidence;
    }

    public void setConfidence(Integer confidence) {
        this.confidence = confidence;
    }

    public String getSummaryReason() {
        return summaryReason;
    }

    @JsonAlias("summary_reason")
    public void setSummaryReason(String summaryReason) {
        this.summaryReason = summaryReason;
    }

    public String getModelCode() {
        return modelCode;
    }

    @JsonAlias("model_code")
    public void setModelCode(String modelCode) {
        this.modelCode = modelCode;
    }

    public String getModelProvider() {
        return modelProvider;
    }

    @JsonAlias("model_provider")
    public void setModelProvider(String modelProvider) {
        this.modelProvider = modelProvider;
    }

    public String getPromptSource() {
        return promptSource;
    }

    @JsonAlias("prompt_source")
    public void setPromptSource(String promptSource) {
        this.promptSource = promptSource;
    }

    public String getBindingTemplateCode() {
        return bindingTemplateCode;
    }

    @JsonAlias("binding_template_code")
    public void setBindingTemplateCode(String bindingTemplateCode) {
        this.bindingTemplateCode = bindingTemplateCode;
    }

    public String getFallbackTemplateCode() {
        return fallbackTemplateCode;
    }

    @JsonAlias("fallback_template_code")
    public void setFallbackTemplateCode(String fallbackTemplateCode) {
        this.fallbackTemplateCode = fallbackTemplateCode;
    }

    public String getResolvedTemplateCode() {
        return resolvedTemplateCode;
    }

    @JsonAlias("resolved_template_code")
    public void setResolvedTemplateCode(String resolvedTemplateCode) {
        this.resolvedTemplateCode = resolvedTemplateCode;
    }

    public Boolean getPromptTemplateFallbackUsed() {
        return promptTemplateFallbackUsed;
    }

    @JsonAlias("prompt_template_fallback_used")
    public void setPromptTemplateFallbackUsed(Boolean promptTemplateFallbackUsed) {
        this.promptTemplateFallbackUsed = promptTemplateFallbackUsed;
    }

    public String getTriggerReason() {
        return triggerReason;
    }

    @JsonAlias("trigger_reason")
    public void setTriggerReason(String triggerReason) {
        this.triggerReason = triggerReason;
    }

    public String getTriggerSource() {
        return triggerSource;
    }

    @JsonAlias("trigger_source")
    public void setTriggerSource(String triggerSource) {
        this.triggerSource = triggerSource;
    }

    public String getDispatchMode() {
        return dispatchMode;
    }

    @JsonAlias("dispatch_mode")
    public void setDispatchMode(String dispatchMode) {
        this.dispatchMode = dispatchMode;
    }

    public String getSelectedAgentsJson() {
        return selectedAgentsJson;
    }

    @JsonAlias("selected_agents_json")
    public void setSelectedAgentsJson(String selectedAgentsJson) {
        this.selectedAgentsJson = selectedAgentsJson;
    }

    public String getCombinationMatchJson() {
        return combinationMatchJson;
    }

    @JsonAlias("combination_match_json")
    public void setCombinationMatchJson(String combinationMatchJson) {
        this.combinationMatchJson = combinationMatchJson;
    }

    public String getActiveSignalRefsJson() {
        return activeSignalRefsJson;
    }

    @JsonAlias("active_signal_refs_json")
    public void setActiveSignalRefsJson(String activeSignalRefsJson) {
        this.activeSignalRefsJson = activeSignalRefsJson;
    }

    public Boolean getCooldownBlocked() {
        return cooldownBlocked;
    }

    @JsonAlias("cooldown_blocked")
    public void setCooldownBlocked(Boolean cooldownBlocked) {
        this.cooldownBlocked = cooldownBlocked;
    }

    public Boolean getBudgetBlocked() {
        return budgetBlocked;
    }

    @JsonAlias("budget_blocked")
    public void setBudgetBlocked(Boolean budgetBlocked) {
        this.budgetBlocked = budgetBlocked;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }

    public String getEventStrength() {
        return eventStrength;
    }

    @JsonAlias("event_strength")
    public void setEventStrength(String eventStrength) {
        this.eventStrength = eventStrength;
    }

    public FeatureSnapshot getFeatureSnapshot() {
        return featureSnapshot;
    }

    @JsonAlias("feature_snapshot")
    public void setFeatureSnapshot(FeatureSnapshot featureSnapshot) {
        this.featureSnapshot = featureSnapshot;
    }

    public Map<String, Object> getMarketSourceConfig() {
        return marketSourceConfig;
    }

    @JsonAlias("market_source_config")
    public void setMarketSourceConfig(Map<String, Object> marketSourceConfig) {
        this.marketSourceConfig = marketSourceConfig == null ? new LinkedHashMap<>() : new LinkedHashMap<>(marketSourceConfig);
    }

    public Map<String, Object> getShortTermMemory() {
        return shortTermMemory;
    }

    @JsonAlias("short_term_memory")
    public void setShortTermMemory(Map<String, Object> shortTermMemory) {
        this.shortTermMemory = shortTermMemory == null ? new LinkedHashMap<>() : new LinkedHashMap<>(shortTermMemory);
    }

    public Map<String, Object> getLongTermMemory() {
        return longTermMemory;
    }

    @JsonAlias("long_term_memory")
    public void setLongTermMemory(Map<String, Object> longTermMemory) {
        this.longTermMemory = longTermMemory == null ? new LinkedHashMap<>() : new LinkedHashMap<>(longTermMemory);
    }

    public Map<String, Object> getMemoryUsage() {
        return memoryUsage;
    }

    @JsonAlias("memory_usage")
    public void setMemoryUsage(Map<String, Object> memoryUsage) {
        this.memoryUsage = memoryUsage == null ? new LinkedHashMap<>() : new LinkedHashMap<>(memoryUsage);
    }

    public Map<String, Object> getTradeMemoryStatus() {
        return tradeMemoryStatus;
    }

    @JsonAlias("trade_memory_status")
    public void setTradeMemoryStatus(Map<String, Object> tradeMemoryStatus) {
        this.tradeMemoryStatus = tradeMemoryStatus == null ? new LinkedHashMap<>() : new LinkedHashMap<>(tradeMemoryStatus);
    }

    public String getTradeMemoryStatusJson() {
        return tradeMemoryStatusJson;
    }

    public void setTradeMemoryStatusJson(String tradeMemoryStatusJson) {
        this.tradeMemoryStatusJson = tradeMemoryStatusJson;
    }

    public Map<String, Object> getLifecycleStatus() {
        return lifecycleStatus;
    }

    @JsonAlias("lifecycle_status")
    public void setLifecycleStatus(Map<String, Object> lifecycleStatus) {
        this.lifecycleStatus = lifecycleStatus == null ? new LinkedHashMap<>() : new LinkedHashMap<>(lifecycleStatus);
    }

    public String getLifecycleStatusJson() {
        return lifecycleStatusJson;
    }

    public void setLifecycleStatusJson(String lifecycleStatusJson) {
        this.lifecycleStatusJson = lifecycleStatusJson;
    }

    public String getExecutionStatus() {
        return executionStatus;
    }

    @JsonAlias("execution_status")
    public void setExecutionStatus(String executionStatus) {
        this.executionStatus = executionStatus;
    }

    public String getOrderStatus() {
        return orderStatus;
    }

    @JsonAlias("order_status")
    public void setOrderStatus(String orderStatus) {
        this.orderStatus = orderStatus;
    }

    public List<SignalEvent> getSignalEvents() {
        return signalEvents;
    }

    @JsonAlias("signal_events")
    public void setSignalEvents(List<SignalEvent> signalEvents) {
        this.signalEvents = signalEvents;
    }

    public List<SignalWindowState> getSignalWindowStates() {
        return signalWindowStates;
    }

    @JsonAlias("signal_window_states")
    public void setSignalWindowStates(List<SignalWindowState> signalWindowStates) {
        this.signalWindowStates = signalWindowStates;
    }

    public List<AgentRun> getAgentRuns() {
        return agentRuns;
    }

    @JsonAlias("agent_runs")
    public void setAgentRuns(List<AgentRun> agentRuns) {
        this.agentRuns = agentRuns;
    }

    public List<AgentObservation> getAgentObservations() {
        return agentObservations;
    }

    @JsonAlias("agent_observations")
    public void setAgentObservations(List<AgentObservation> agentObservations) {
        this.agentObservations = agentObservations;
    }

    public List<AgentConclusion> getAgentConclusions() {
        return agentConclusions;
    }

    @JsonAlias("agent_conclusions")
    public void setAgentConclusions(List<AgentConclusion> agentConclusions) {
        this.agentConclusions = agentConclusions;
    }

    public List<AgentMessage> getAgentMessages() {
        return agentMessages;
    }

    @JsonAlias("agent_messages")
    public void setAgentMessages(List<AgentMessage> agentMessages) {
        this.agentMessages = agentMessages;
    }

    public List<DecisionAction> getDecisionActions() {
        return decisionActions;
    }

    @JsonAlias("decision_actions")
    public void setDecisionActions(List<DecisionAction> decisionActions) {
        this.decisionActions = decisionActions;
    }
}

