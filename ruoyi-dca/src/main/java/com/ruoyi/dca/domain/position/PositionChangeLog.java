package com.ruoyi.dca.domain.position;

import java.math.BigDecimal;

public class PositionChangeLog {
    private Long id;
    private String traceId;
    private String exchangeCode;
    private String symbol;
    private String side;
    private String changeType;
    private BigDecimal beforeQuantity;
    private BigDecimal afterQuantity;
    private BigDecimal deltaQuantity;
    private BigDecimal entryPrice;
    private BigDecimal unrealizedPnl;
    private String createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getExchangeCode() {
        return exchangeCode;
    }

    public void setExchangeCode(String exchangeCode) {
        this.exchangeCode = exchangeCode;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getSide() {
        return side;
    }

    public void setSide(String side) {
        this.side = side;
    }

    public String getChangeType() {
        return changeType;
    }

    public void setChangeType(String changeType) {
        this.changeType = changeType;
    }

    public BigDecimal getBeforeQuantity() {
        return beforeQuantity;
    }

    public void setBeforeQuantity(BigDecimal beforeQuantity) {
        this.beforeQuantity = beforeQuantity;
    }

    public BigDecimal getAfterQuantity() {
        return afterQuantity;
    }

    public void setAfterQuantity(BigDecimal afterQuantity) {
        this.afterQuantity = afterQuantity;
    }

    public BigDecimal getDeltaQuantity() {
        return deltaQuantity;
    }

    public void setDeltaQuantity(BigDecimal deltaQuantity) {
        this.deltaQuantity = deltaQuantity;
    }

    public BigDecimal getEntryPrice() {
        return entryPrice;
    }

    public void setEntryPrice(BigDecimal entryPrice) {
        this.entryPrice = entryPrice;
    }

    public BigDecimal getUnrealizedPnl() {
        return unrealizedPnl;
    }

    public void setUnrealizedPnl(BigDecimal unrealizedPnl) {
        this.unrealizedPnl = unrealizedPnl;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
