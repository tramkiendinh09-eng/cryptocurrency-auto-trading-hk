package com.ruoyi.dca.domain.position;

import java.math.BigDecimal;

/**
 * 持仓快照实体类
 *
 * 记录持仓状态的快照信息，包括持仓方向、数量、入场价格、未实现盈亏等。
 * 用于追踪持仓变化历史和计算盈亏。
 *
 * @author ruoyi-dca
 */
public class PositionSnapshot {
    /** 主键ID */
    private Long id;

    /** 用户ID */
    private Long userId;

    /** 追踪ID */
    private String traceId;

    /** Original entry trace ID */
    private String entryTraceId;

    /** 交易所代码 */
    private String exchangeCode;

    /** 交易品种 */
    private String symbol;

    /** 持仓方向：long/short */
    private String side;

    /** 持仓数量 */
    private BigDecimal positionQuantity;

    /** 入场价格 */
    private BigDecimal entryPrice;

    /** 未实现盈亏 */
    private BigDecimal unrealizedPnl;

    /** 创建时间 */
    private String createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getEntryTraceId() {
        return entryTraceId;
    }

    public void setEntryTraceId(String entryTraceId) {
        this.entryTraceId = entryTraceId;
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

    public BigDecimal getPositionQuantity() {
        return positionQuantity;
    }

    public void setPositionQuantity(BigDecimal positionQuantity) {
        this.positionQuantity = positionQuantity;
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

