package com.ruoyi.dca.domain.trade;

import com.ruoyi.dca.domain.decision.AgentConclusion;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class TradeRuntimeOverview {
    private TradeRuntimeConfig runtimeConfig;
    private Long eventCount;
    private Long signalCount;
    private Long decisionCount;
    private Long riskHitCount;
    private Long activePositionCount;
    private BigDecimal totalUnrealizedPnl;
    private BigDecimal latestDailyPnl;
    private BigDecimal maxDrawdownPct;
    private PnlSnapshot latestPnlSnapshot;
    private String latestDispatchMode;
    private String lastTriggerReason;
    private String lastTriggerSource;
    private Long cooldownSuppressionCount;
    private Long budgetSuppressionCount;
    private String lastSelectedAgentsJson;
    private String lastCombinationMatchJson;
    private List<EventRaw> recentEvents = new ArrayList<>();
    private List<SignalEvent> recentSignals = new ArrayList<>();
    private List<SignalWindowState> activeSignalWindows = new ArrayList<>();
    private List<AgentConclusion> recentAgentConclusions = new ArrayList<>();
    private List<DecisionRun> recentDecisions = new ArrayList<>();
    private List<RiskGuardHit> recentRiskHits = new ArrayList<>();
    private List<ExchangeFill> recentFills = new ArrayList<>();
    private List<TradeActionSummary> recentTradeActions = new ArrayList<>();
    private List<ExchangeOrder> recentOrders = new ArrayList<>();
    private List<PositionSnapshot> recentPositions = new ArrayList<>();
    private Map<String, Long> executionStats = new LinkedHashMap<>();

    public TradeRuntimeConfig getRuntimeConfig() {
        return runtimeConfig;
    }

    public void setRuntimeConfig(TradeRuntimeConfig runtimeConfig) {
        this.runtimeConfig = runtimeConfig;
    }

    public Long getEventCount() {
        return eventCount;
    }

    public void setEventCount(Long eventCount) {
        this.eventCount = eventCount;
    }

    public Long getSignalCount() {
        return signalCount;
    }

    public void setSignalCount(Long signalCount) {
        this.signalCount = signalCount;
    }

    public Long getDecisionCount() {
        return decisionCount;
    }

    public void setDecisionCount(Long decisionCount) {
        this.decisionCount = decisionCount;
    }

    public Long getRiskHitCount() {
        return riskHitCount;
    }

    public void setRiskHitCount(Long riskHitCount) {
        this.riskHitCount = riskHitCount;
    }

    public Long getActivePositionCount() {
        return activePositionCount;
    }

    public void setActivePositionCount(Long activePositionCount) {
        this.activePositionCount = activePositionCount;
    }

    public BigDecimal getTotalUnrealizedPnl() {
        return totalUnrealizedPnl;
    }

    public void setTotalUnrealizedPnl(BigDecimal totalUnrealizedPnl) {
        this.totalUnrealizedPnl = totalUnrealizedPnl;
    }

    public BigDecimal getLatestDailyPnl() {
        return latestDailyPnl;
    }

    public void setLatestDailyPnl(BigDecimal latestDailyPnl) {
        this.latestDailyPnl = latestDailyPnl;
    }

    public BigDecimal getMaxDrawdownPct() {
        return maxDrawdownPct;
    }

    public void setMaxDrawdownPct(BigDecimal maxDrawdownPct) {
        this.maxDrawdownPct = maxDrawdownPct;
    }

    public PnlSnapshot getLatestPnlSnapshot() {
        return latestPnlSnapshot;
    }

    public void setLatestPnlSnapshot(PnlSnapshot latestPnlSnapshot) {
        this.latestPnlSnapshot = latestPnlSnapshot;
    }

    public String getLatestDispatchMode() {
        return latestDispatchMode;
    }

    public void setLatestDispatchMode(String latestDispatchMode) {
        this.latestDispatchMode = latestDispatchMode;
    }

    public String getLastTriggerReason() {
        return lastTriggerReason;
    }

    public void setLastTriggerReason(String lastTriggerReason) {
        this.lastTriggerReason = lastTriggerReason;
    }

    public String getLastTriggerSource() {
        return lastTriggerSource;
    }

    public void setLastTriggerSource(String lastTriggerSource) {
        this.lastTriggerSource = lastTriggerSource;
    }

    public Long getCooldownSuppressionCount() {
        return cooldownSuppressionCount;
    }

    public void setCooldownSuppressionCount(Long cooldownSuppressionCount) {
        this.cooldownSuppressionCount = cooldownSuppressionCount;
    }

    public Long getBudgetSuppressionCount() {
        return budgetSuppressionCount;
    }

    public void setBudgetSuppressionCount(Long budgetSuppressionCount) {
        this.budgetSuppressionCount = budgetSuppressionCount;
    }

    public String getLastSelectedAgentsJson() {
        return lastSelectedAgentsJson;
    }

    public void setLastSelectedAgentsJson(String lastSelectedAgentsJson) {
        this.lastSelectedAgentsJson = lastSelectedAgentsJson;
    }

    public String getLastCombinationMatchJson() {
        return lastCombinationMatchJson;
    }

    public void setLastCombinationMatchJson(String lastCombinationMatchJson) {
        this.lastCombinationMatchJson = lastCombinationMatchJson;
    }

    public List<EventRaw> getRecentEvents() {
        return recentEvents;
    }

    public void setRecentEvents(List<EventRaw> recentEvents) {
        this.recentEvents = recentEvents;
    }

    public List<SignalEvent> getRecentSignals() {
        return recentSignals;
    }

    public void setRecentSignals(List<SignalEvent> recentSignals) {
        this.recentSignals = recentSignals;
    }

    public List<SignalWindowState> getActiveSignalWindows() {
        return activeSignalWindows;
    }

    public void setActiveSignalWindows(List<SignalWindowState> activeSignalWindows) {
        this.activeSignalWindows = activeSignalWindows;
    }

    public List<AgentConclusion> getRecentAgentConclusions() {
        return recentAgentConclusions;
    }

    public void setRecentAgentConclusions(List<AgentConclusion> recentAgentConclusions) {
        this.recentAgentConclusions = recentAgentConclusions;
    }

    public List<DecisionRun> getRecentDecisions() {
        return recentDecisions;
    }

    public void setRecentDecisions(List<DecisionRun> recentDecisions) {
        this.recentDecisions = recentDecisions;
    }

    public List<RiskGuardHit> getRecentRiskHits() {
        return recentRiskHits;
    }

    public void setRecentRiskHits(List<RiskGuardHit> recentRiskHits) {
        this.recentRiskHits = recentRiskHits;
    }

    public List<ExchangeFill> getRecentFills() {
        return recentFills;
    }

    public void setRecentFills(List<ExchangeFill> recentFills) {
        this.recentFills = recentFills;
    }

    public List<TradeActionSummary> getRecentTradeActions() {
        return recentTradeActions;
    }

    public void setRecentTradeActions(List<TradeActionSummary> recentTradeActions) {
        this.recentTradeActions = recentTradeActions;
    }

    public List<ExchangeOrder> getRecentOrders() {
        return recentOrders;
    }

    public void setRecentOrders(List<ExchangeOrder> recentOrders) {
        this.recentOrders = recentOrders;
    }

    public List<PositionSnapshot> getRecentPositions() {
        return recentPositions;
    }

    public void setRecentPositions(List<PositionSnapshot> recentPositions) {
        this.recentPositions = recentPositions;
    }

    public Map<String, Long> getExecutionStats() {
        return executionStats;
    }

    public void setExecutionStats(Map<String, Long> executionStats) {
        this.executionStats = executionStats;
    }
}
