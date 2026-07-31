package com.ruoyi.dca.domain.memory;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.util.Date;

/**
 * 交易生命周期追踪实体
 * 记录每笔交易从开仓到平仓的完整过程
 */
public class TradeLifecycle {
    private Long id;
    private String traceId;
    private String symbol;
    private String exchangeCode;
    private String side;
    private BigDecimal entryPrice;
    private Date entryTime;
    private String entryReason;
    private String entryConditionsJson;
    private String agentViewsJson;
    private String supervisorDecisionJson;
    private String priceTrajectoryJson;
    private BigDecimal maxFavorablePct;
    private BigDecimal maxAdversePct;
    private Integer holdingMinutes;
    private BigDecimal exitPrice;
    private Date exitTime;
    private String exitReason;
    private BigDecimal realizedPnlPct;
    private Boolean memoryGenerated;
    private String lessonText;
    private String memoryStatus;
    private String memoryReason;
    private String addOperationsJson;
    private String reduceOperationsJson;
    private Date createdAt;
    private Date updatedAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    @JsonProperty("exchangeCode")
    public String getExchangeCode() { return exchangeCode; }
    @JsonAlias("exchange_code")
    public void setExchangeCode(String exchangeCode) { this.exchangeCode = exchangeCode; }
    public String getSide() { return side; }
    public void setSide(String side) { this.side = side; }
    @JsonProperty("entryPrice")
    public BigDecimal getEntryPrice() { return entryPrice; }
    @JsonAlias("entry_price")
    public void setEntryPrice(BigDecimal entryPrice) { this.entryPrice = entryPrice; }
    @JsonProperty("entryTime")
    public Date getEntryTime() { return entryTime; }
    @JsonAlias("entry_time")
    public void setEntryTime(Date entryTime) { this.entryTime = entryTime; }
    @JsonProperty("entryReason")
    public String getEntryReason() { return entryReason; }
    @JsonAlias("entry_reason")
    public void setEntryReason(String entryReason) { this.entryReason = entryReason; }
    @JsonProperty("entryConditionsJson")
    public String getEntryConditionsJson() { return entryConditionsJson; }
    @JsonAlias("entry_conditions_json")
    public void setEntryConditionsJson(String entryConditionsJson) { this.entryConditionsJson = entryConditionsJson; }
    @JsonProperty("agentViewsJson")
    public String getAgentViewsJson() { return agentViewsJson; }
    @JsonAlias("agent_views_json")
    public void setAgentViewsJson(String agentViewsJson) { this.agentViewsJson = agentViewsJson; }
    @JsonProperty("supervisorDecisionJson")
    public String getSupervisorDecisionJson() { return supervisorDecisionJson; }
    @JsonAlias("supervisor_decision_json")
    public void setSupervisorDecisionJson(String supervisorDecisionJson) { this.supervisorDecisionJson = supervisorDecisionJson; }
    @JsonProperty("priceTrajectoryJson")
    public String getPriceTrajectoryJson() { return priceTrajectoryJson; }
    @JsonAlias("price_trajectory_json")
    public void setPriceTrajectoryJson(String priceTrajectoryJson) { this.priceTrajectoryJson = priceTrajectoryJson; }
    @JsonProperty("maxFavorablePct")
    public BigDecimal getMaxFavorablePct() { return maxFavorablePct; }
    @JsonAlias("max_favorable_pct")
    public void setMaxFavorablePct(BigDecimal maxFavorablePct) { this.maxFavorablePct = maxFavorablePct; }
    @JsonProperty("maxAdversePct")
    public BigDecimal getMaxAdversePct() { return maxAdversePct; }
    @JsonAlias("max_adverse_pct")
    public void setMaxAdversePct(BigDecimal maxAdversePct) { this.maxAdversePct = maxAdversePct; }
    @JsonProperty("holdingMinutes")
    public Integer getHoldingMinutes() { return holdingMinutes; }
    @JsonAlias("holding_minutes")
    public void setHoldingMinutes(Integer holdingMinutes) { this.holdingMinutes = holdingMinutes; }
    @JsonProperty("exitPrice")
    public BigDecimal getExitPrice() { return exitPrice; }
    @JsonAlias("exit_price")
    public void setExitPrice(BigDecimal exitPrice) { this.exitPrice = exitPrice; }
    @JsonProperty("exitTime")
    public Date getExitTime() { return exitTime; }
    @JsonAlias("exit_time")
    public void setExitTime(Date exitTime) { this.exitTime = exitTime; }
    @JsonProperty("exitReason")
    public String getExitReason() { return exitReason; }
    @JsonAlias("exit_reason")
    public void setExitReason(String exitReason) { this.exitReason = exitReason; }
    @JsonProperty("realizedPnlPct")
    public BigDecimal getRealizedPnlPct() { return realizedPnlPct; }
    @JsonAlias("realized_pnl_pct")
    public void setRealizedPnlPct(BigDecimal realizedPnlPct) { this.realizedPnlPct = realizedPnlPct; }
    @JsonProperty("memoryGenerated")
    public Boolean getMemoryGenerated() { return memoryGenerated; }
    @JsonAlias("memory_generated")
    public void setMemoryGenerated(Boolean memoryGenerated) { this.memoryGenerated = memoryGenerated; }
    @JsonProperty("lessonText")
    public String getLessonText() { return lessonText; }
    @JsonAlias("lesson_text")
    public void setLessonText(String lessonText) { this.lessonText = lessonText; }
    @JsonProperty("memoryStatus")
    public String getMemoryStatus() { return memoryStatus; }
    @JsonAlias("memory_status")
    public void setMemoryStatus(String memoryStatus) { this.memoryStatus = memoryStatus; }
    @JsonProperty("memoryReason")
    public String getMemoryReason() { return memoryReason; }
    @JsonAlias("memory_reason")
    public void setMemoryReason(String memoryReason) { this.memoryReason = memoryReason; }
    @JsonProperty("addOperationsJson")
    public String getAddOperationsJson() { return addOperationsJson; }
    @JsonAlias("add_operations_json")
    public void setAddOperationsJson(String addOperationsJson) { this.addOperationsJson = addOperationsJson; }
    @JsonProperty("reduceOperationsJson")
    public String getReduceOperationsJson() { return reduceOperationsJson; }
    @JsonAlias("reduce_operations_json")
    public void setReduceOperationsJson(String reduceOperationsJson) { this.reduceOperationsJson = reduceOperationsJson; }
    public Date getCreatedAt() { return createdAt; }
    public void setCreatedAt(Date createdAt) { this.createdAt = createdAt; }
    public Date getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Date updatedAt) { this.updatedAt = updatedAt; }
}
