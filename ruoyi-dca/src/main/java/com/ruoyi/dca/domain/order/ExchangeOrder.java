package com.ruoyi.dca.domain.order;

import java.math.BigDecimal;

/**
 * 交易所订单实体类
 *
 * 记录交易所返回的订单信息，包括订单引用、状态、执行结果等。
 * 用于追踪订单在交易所的实际执行情况。
 *
 * @author ruoyi-dca
 */
public class ExchangeOrder {
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

    /** 订单引用（交易所返回） */
    private String orderRef;

    private String clientOrderId;

    /** 动作类型 */
    private String action;

    /** 订单类型：market/limit */
    private String orderType;

    /** 持仓方向：long/short */
    private String positionSide;

    /** 是否只减仓 */
    private Boolean reduceOnly;

    /** 保证金模式 */
    private String tdMode;

    /** 杠杆倍数 */
    private BigDecimal leverage;

    /** 限价单价格 */
    private BigDecimal limitPrice;

    /** 基础货币数量 */
    private BigDecimal quantityBase;

    /** OKX增强执行标志 */
    private Boolean okxEnhancedExecution;

    private BigDecimal filledQuantity;

    private BigDecimal avgFillPrice;

    private BigDecimal fee;

    private String feeCcy;

    private Boolean postOnly;

    /** 状态（兼容字段） */
    private String status;

    /** 执行状态：filled/pending/failed/blocked */
    private String executionStatus;

    /** 订单状态：NEW/FILLED/PARTIALLY_FILLED/CANCELED */
    private String orderStatus;

    /** 创建时间 */
    private String createdAt;

    private String updatedAt;

    private String filledAt;

    private String rawPayload;

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

    public String getOrderRef() {
        return orderRef;
    }

    public void setOrderRef(String orderRef) {
        this.orderRef = orderRef;
    }

    public String getClientOrderId() {
        return clientOrderId;
    }

    public void setClientOrderId(String clientOrderId) {
        this.clientOrderId = clientOrderId;
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

    public BigDecimal getFilledQuantity() {
        return filledQuantity;
    }

    public void setFilledQuantity(BigDecimal filledQuantity) {
        this.filledQuantity = filledQuantity;
    }

    public BigDecimal getAvgFillPrice() {
        return avgFillPrice;
    }

    public void setAvgFillPrice(BigDecimal avgFillPrice) {
        this.avgFillPrice = avgFillPrice;
    }

    public BigDecimal getFee() {
        return fee;
    }

    public void setFee(BigDecimal fee) {
        this.fee = fee;
    }

    public String getFeeCcy() {
        return feeCcy;
    }

    public void setFeeCcy(String feeCcy) {
        this.feeCcy = feeCcy;
    }

    public Boolean getPostOnly() {
        return postOnly;
    }

    public void setPostOnly(Boolean postOnly) {
        this.postOnly = postOnly;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getExecutionStatus() {
        if (executionStatus == null || executionStatus.isBlank()) {
            return status;
        }
        return executionStatus;
    }

    public void setExecutionStatus(String executionStatus) {
        this.executionStatus = executionStatus;
    }

    public String getOrderStatus() {
        return orderStatus;
    }

    public void setOrderStatus(String orderStatus) {
        this.orderStatus = orderStatus;
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

    public String getFilledAt() {
        return filledAt;
    }

    public void setFilledAt(String filledAt) {
        this.filledAt = filledAt;
    }

    public String getRawPayload() {
        return rawPayload;
    }

    public void setRawPayload(String rawPayload) {
        this.rawPayload = rawPayload;
    }
}

