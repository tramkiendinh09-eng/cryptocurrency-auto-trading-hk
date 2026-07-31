package com.ruoyi.dca.domain.order;

import java.math.BigDecimal;

/**
 * 订单请求实体类
 *
 * 记录交易系统发出的订单请求信息，包括交易品种、方向、金额、订单类型等。
 * 用于审计和追踪订单请求的完整生命周期。
 *
 * @author ruoyi-dca
 */
public class OrderRequest {
    /** 主键ID */
    private Long id;

    /** 追踪ID */
    private String traceId;

    /** 交易所代码 */
    private String exchangeCode;

    /** 交易品种 */
    private String symbol;

    /** 交易方向：BUY/SELL */
    private String side;

    /** 运行模式：paper/shadow/live */
    private String mode;

    /** 报价金额 */
    private BigDecimal quoteAmount;

    /** 动作类型：OPEN_LONG/OPEN_SHORT/CLOSE/REDUCE */
    private String action;

    /** 订单类型：market/limit */
    private String orderType;

    /** 持仓方向：long/short */
    private String positionSide;

    /** 是否只减仓 */
    private Boolean reduceOnly;

    /** 保证金模式：cross/isolated */
    private String tdMode;

    /** 杠杆倍数 */
    private BigDecimal leverage;

    /** 限价单价格 */
    private BigDecimal limitPrice;

    /** 基础货币数量 */
    private BigDecimal quantityBase;

    /** OKX增强执行标志 */
    private Boolean okxEnhancedExecution;

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

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public BigDecimal getQuoteAmount() {
        return quoteAmount;
    }

    public void setQuoteAmount(BigDecimal quoteAmount) {
        this.quoteAmount = quoteAmount;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public String getOrderType() {
        return orderType;
    }

    public void setOrderType(String orderType) {
        this.orderType = orderType;
    }

    public String getPositionSide() {
        return positionSide;
    }

    public void setPositionSide(String positionSide) {
        this.positionSide = positionSide;
    }

    public Boolean getReduceOnly() {
        return reduceOnly;
    }

    public void setReduceOnly(Boolean reduceOnly) {
        this.reduceOnly = reduceOnly;
    }

    public String getTdMode() {
        return tdMode;
    }

    public void setTdMode(String tdMode) {
        this.tdMode = tdMode;
    }

    public BigDecimal getLeverage() {
        return leverage;
    }

    public void setLeverage(BigDecimal leverage) {
        this.leverage = leverage;
    }

    public BigDecimal getLimitPrice() {
        return limitPrice;
    }

    public void setLimitPrice(BigDecimal limitPrice) {
        this.limitPrice = limitPrice;
    }

    public BigDecimal getQuantityBase() {
        return quantityBase;
    }

    public void setQuantityBase(BigDecimal quantityBase) {
        this.quantityBase = quantityBase;
    }

    public Boolean getOkxEnhancedExecution() {
        return okxEnhancedExecution;
    }

    public void setOkxEnhancedExecution(Boolean okxEnhancedExecution) {
        this.okxEnhancedExecution = okxEnhancedExecution;
    }
}

