package com.ruoyi.dca.domain.trade;

import java.math.BigDecimal;

public class TradeRuntimeAccountContext {
    private BigDecimal accountEquity;
    private BigDecimal dailyPnl;
    private BigDecimal realizedPnl;
    private BigDecimal unrealizedPnl;
    private String currentPositionSide;
    private BigDecimal currentPositionQuantity;
    private BigDecimal currentPositionNotional;
    private BigDecimal entryPrice;
    private BigDecimal maxDrawdownPct;
    private BigDecimal peakAccountEquity;
    private String currentPositionOpenedAt;
    private String currentTime;
    private Integer currentPositionHoldingMinutes;
    private Integer consecutiveFailures;
    private String entryTraceId;

    public BigDecimal getAccountEquity() {
        return accountEquity;
    }

    public void setAccountEquity(BigDecimal accountEquity) {
        this.accountEquity = accountEquity;
    }

    public BigDecimal getDailyPnl() {
        return dailyPnl;
    }

    public void setDailyPnl(BigDecimal dailyPnl) {
        this.dailyPnl = dailyPnl;
    }

    public BigDecimal getRealizedPnl() {
        return realizedPnl;
    }

    public void setRealizedPnl(BigDecimal realizedPnl) {
        this.realizedPnl = realizedPnl;
    }

    public BigDecimal getUnrealizedPnl() {
        return unrealizedPnl;
    }

    public void setUnrealizedPnl(BigDecimal unrealizedPnl) {
        this.unrealizedPnl = unrealizedPnl;
    }

    public String getCurrentPositionSide() {
        return currentPositionSide;
    }

    public void setCurrentPositionSide(String currentPositionSide) {
        this.currentPositionSide = currentPositionSide;
    }

    public BigDecimal getCurrentPositionQuantity() {
        return currentPositionQuantity;
    }

    public void setCurrentPositionQuantity(BigDecimal currentPositionQuantity) {
        this.currentPositionQuantity = currentPositionQuantity;
    }

    public BigDecimal getCurrentPositionNotional() {
        return currentPositionNotional;
    }

    public void setCurrentPositionNotional(BigDecimal currentPositionNotional) {
        this.currentPositionNotional = currentPositionNotional;
    }

    public BigDecimal getEntryPrice() {
        return entryPrice;
    }

    public void setEntryPrice(BigDecimal entryPrice) {
        this.entryPrice = entryPrice;
    }

    public BigDecimal getMaxDrawdownPct() {
        return maxDrawdownPct;
    }

    public void setMaxDrawdownPct(BigDecimal maxDrawdownPct) {
        this.maxDrawdownPct = maxDrawdownPct;
    }

    public BigDecimal getPeakAccountEquity() {
        return peakAccountEquity;
    }

    public void setPeakAccountEquity(BigDecimal peakAccountEquity) {
        this.peakAccountEquity = peakAccountEquity;
    }

    public String getCurrentPositionOpenedAt() {
        return currentPositionOpenedAt;
    }

    public void setCurrentPositionOpenedAt(String currentPositionOpenedAt) {
        this.currentPositionOpenedAt = currentPositionOpenedAt;
    }

    public String getCurrentTime() {
        return currentTime;
    }

    public void setCurrentTime(String currentTime) {
        this.currentTime = currentTime;
    }

    public Integer getCurrentPositionHoldingMinutes() {
        return currentPositionHoldingMinutes;
    }

    public void setCurrentPositionHoldingMinutes(Integer currentPositionHoldingMinutes) {
        this.currentPositionHoldingMinutes = currentPositionHoldingMinutes;
    }

    public Integer getConsecutiveFailures() {
        return consecutiveFailures;
    }

    public void setConsecutiveFailures(Integer consecutiveFailures) {
        this.consecutiveFailures = consecutiveFailures;
    }

    public String getEntryTraceId() {
        return entryTraceId;
    }

    public void setEntryTraceId(String entryTraceId) {
        this.entryTraceId = entryTraceId;
    }
}
