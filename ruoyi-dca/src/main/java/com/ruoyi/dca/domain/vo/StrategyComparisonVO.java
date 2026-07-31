package com.ruoyi.dca.domain.vo;

import java.math.BigDecimal;

/**
 * 策略对比VO
 *
 * @author ruoyi
 */
public class StrategyComparisonVO {

    /** 策略ID */
    private Long strategyId;

    /** 策略名称 */
    private String strategyName;

    /** 交易对 */
    private String symbol;

    /** 总投入 (USDT) */
    private BigDecimal totalInvest;

    /** 当前价值 (USDT) */
    private BigDecimal currentValue;

    /** 盈亏金额 (USDT) */
    private BigDecimal profitAmount;

    /** 收益率 (%) */
    private BigDecimal profitRate;

    /** 触发次数 */
    private Integer triggerCount;

    /** 运行天数 */
    private Integer runningDays;

    // Getters and Setters

    public Long getStrategyId() {
        return strategyId;
    }

    public void setStrategyId(Long strategyId) {
        this.strategyId = strategyId;
    }

    public String getStrategyName() {
        return strategyName;
    }

    public void setStrategyName(String strategyName) {
        this.strategyName = strategyName;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public BigDecimal getTotalInvest() {
        return totalInvest;
    }

    public void setTotalInvest(BigDecimal totalInvest) {
        this.totalInvest = totalInvest;
    }

    public BigDecimal getCurrentValue() {
        return currentValue;
    }

    public void setCurrentValue(BigDecimal currentValue) {
        this.currentValue = currentValue;
    }

    public BigDecimal getProfitAmount() {
        return profitAmount;
    }

    public void setProfitAmount(BigDecimal profitAmount) {
        this.profitAmount = profitAmount;
    }

    public BigDecimal getProfitRate() {
        return profitRate;
    }

    public void setProfitRate(BigDecimal profitRate) {
        this.profitRate = profitRate;
    }

    public Integer getTriggerCount() {
        return triggerCount;
    }

    public void setTriggerCount(Integer triggerCount) {
        this.triggerCount = triggerCount;
    }

    public Integer getRunningDays() {
        return runningDays;
    }

    public void setRunningDays(Integer runningDays) {
        this.runningDays = runningDays;
    }
}
