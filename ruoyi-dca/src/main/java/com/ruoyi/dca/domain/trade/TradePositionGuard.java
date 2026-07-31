package com.ruoyi.dca.domain.trade;

import java.math.BigDecimal;

public class TradePositionGuard {
    private Long id;
    private String guardName;
    private String scopeType;
    private Long strategyId;
    private String symbol;
    private String exchangeCode;
    private BigDecimal stopLossPct;
    private BigDecimal takeProfitPct;
    private Integer maxHoldingMinutes;
    private Boolean enabled;
    private Integer priority;
    private String remark;
    private String createdAt;
    private String updatedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getGuardName() {
        return guardName;
    }

    public void setGuardName(String guardName) {
        this.guardName = guardName;
    }

    public String getScopeType() {
        return scopeType;
    }

    public void setScopeType(String scopeType) {
        this.scopeType = scopeType;
    }

    public Long getStrategyId() {
        return strategyId;
    }

    public void setStrategyId(Long strategyId) {
        this.strategyId = strategyId;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getExchangeCode() {
        return exchangeCode;
    }

    public void setExchangeCode(String exchangeCode) {
        this.exchangeCode = exchangeCode;
    }

    public BigDecimal getStopLossPct() {
        return stopLossPct;
    }

    public void setStopLossPct(BigDecimal stopLossPct) {
        this.stopLossPct = stopLossPct;
    }

    public BigDecimal getTakeProfitPct() {
        return takeProfitPct;
    }

    public void setTakeProfitPct(BigDecimal takeProfitPct) {
        this.takeProfitPct = takeProfitPct;
    }

    public Integer getMaxHoldingMinutes() {
        return maxHoldingMinutes;
    }

    public void setMaxHoldingMinutes(Integer maxHoldingMinutes) {
        this.maxHoldingMinutes = maxHoldingMinutes;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean enabled) {
        this.enabled = enabled;
    }

    public Integer getPriority() {
        return priority;
    }

    public void setPriority(Integer priority) {
        this.priority = priority;
    }

    public String getRemark() {
        return remark;
    }

    public void setRemark(String remark) {
        this.remark = remark;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }

    public String getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(String updatedAt) {
        this.updatedAt = updatedAt;
    }
}
