package com.ruoyi.dca.domain.vo;

import java.math.BigDecimal;

/**
 * 持仓分布VO
 *
 * @author ruoyi
 */
public class HoldingDistributionVO {

    /** 币种符号 */
    private String symbol;

    /** 币种名称 */
    private String symbolName;

    /** 持仓数量 */
    private BigDecimal quantity;

    /** 当前价值 (USDT) */
    private BigDecimal value;

    /** 平均成本价 */
    private BigDecimal avgCostPrice;

    /** 当前价格 */
    private BigDecimal currentPrice;

    /** 盈亏金额 (USDT) */
    private BigDecimal profitAmount;

    /** 收益率 (%) */
    private BigDecimal profitRate;

    /** 占比 (%) */
    private BigDecimal percentage;

    // Getters and Setters

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getSymbolName() {
        return symbolName;
    }

    public void setSymbolName(String symbolName) {
        this.symbolName = symbolName;
    }

    public BigDecimal getQuantity() {
        return quantity;
    }

    public void setQuantity(BigDecimal quantity) {
        this.quantity = quantity;
    }

    public BigDecimal getValue() {
        return value;
    }

    public void setValue(BigDecimal value) {
        this.value = value;
    }

    public BigDecimal getAvgCostPrice() {
        return avgCostPrice;
    }

    public void setAvgCostPrice(BigDecimal avgCostPrice) {
        this.avgCostPrice = avgCostPrice;
    }

    public BigDecimal getCurrentPrice() {
        return currentPrice;
    }

    public void setCurrentPrice(BigDecimal currentPrice) {
        this.currentPrice = currentPrice;
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

    public BigDecimal getPercentage() {
        return percentage;
    }

    public void setPercentage(BigDecimal percentage) {
        this.percentage = percentage;
    }
}
