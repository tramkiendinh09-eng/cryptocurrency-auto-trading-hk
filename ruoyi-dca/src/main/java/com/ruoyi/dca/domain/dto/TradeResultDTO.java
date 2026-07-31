package com.ruoyi.dca.domain.dto;

import java.io.Serializable;
import java.math.BigDecimal;

/**
 * 交易结果DTO - 接收Python Worker的交易回调
 *
 * @author ruoyi
 * @date 2026-04-03
 */
public class TradeResultDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    /** 任务ID */
    private String taskId;

    /** 回调时间戳 */
    private Long timestamp;

    /** 任务类型 */
    private String taskType;

    // ========== 交易相关 ==========

    /** 策略ID */
    private Long strategyId;

    private String traceId;

    /** 用户ID */
    private Long userId;

    /** 交易对 */
    private String symbol;

    /** 投资金额(USDT) */
    private BigDecimal usdtAmount;

    /** 获得币数量 */
    private BigDecimal coinAmount;

    /** 成交价格 */
    private BigDecimal price;

    /** 阶段: 1正常 2大跌 3暴涨暂停 */
    private Integer phase;

    /** 交易类型: dca/double_buy */
    private String tradeType;

    // ========== 结果相关 ==========

    /** 是否成功 */
    private Boolean success;

    /** 错误信息 */
    private String error;

    /** 是否跳过 */
    private Boolean skipped;

    /** 跳过原因 */
    private String skipReason;

    /** 是否模拟交易 */
    private Boolean isSimulation;

    /** 订单ID */
    private String orderId;

    /** 交易哈希 */
    private String txHash;

    /** 回调是否发送成功 */
    private Boolean callbackSent;

    /** 价格变化百分比 */
    private BigDecimal priceChangePct;

    /** Gas价格 */
    private BigDecimal gasPrice;

    /** 收益率 */
    private BigDecimal profitRate;

    // ========== Nested Result Support ==========
    /** 原始结果对象（可能包含嵌套的数据） */
    private Object result;

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
    }

    public String getTaskType() {
        return taskType;
    }

    public void setTaskType(String taskType) {
        this.taskType = taskType;
    }

    public Long getStrategyId() {
        return strategyId;
    }

    public void setStrategyId(Long strategyId) {
        this.strategyId = strategyId;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public BigDecimal getUsdtAmount() {
        return usdtAmount;
    }

    public void setUsdtAmount(BigDecimal usdtAmount) {
        this.usdtAmount = usdtAmount;
    }

    public BigDecimal getCoinAmount() {
        return coinAmount;
    }

    public void setCoinAmount(BigDecimal coinAmount) {
        this.coinAmount = coinAmount;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public Integer getPhase() {
        return phase;
    }

    public void setPhase(Integer phase) {
        this.phase = phase;
    }

    public String getTradeType() {
        return tradeType;
    }

    public void setTradeType(String tradeType) {
        this.tradeType = tradeType;
    }

    public Boolean getSuccess() {
        return success;
    }

    public void setSuccess(Boolean success) {
        this.success = success;
    }

    public String getError() {
        return error;
    }

    public void setError(String error) {
        this.error = error;
    }

    public Boolean getSkipped() {
        return skipped;
    }

    public void setSkipped(Boolean skipped) {
        this.skipped = skipped;
    }

    public String getSkipReason() {
        return skipReason;
    }

    public void setSkipReason(String skipReason) {
        this.skipReason = skipReason;
    }

    public Boolean getIsSimulation() {
        return isSimulation;
    }

    public void setIsSimulation(Boolean isSimulation) {
        this.isSimulation = isSimulation;
    }

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public String getTxHash() {
        return txHash;
    }

    public void setTxHash(String txHash) {
        this.txHash = txHash;
    }

    public Boolean getCallbackSent() {
        return callbackSent;
    }

    public void setCallbackSent(Boolean callbackSent) {
        this.callbackSent = callbackSent;
    }

    public BigDecimal getPriceChangePct() {
        return priceChangePct;
    }

    public void setPriceChangePct(BigDecimal priceChangePct) {
        this.priceChangePct = priceChangePct;
    }

    public BigDecimal getGasPrice() {
        return gasPrice;
    }

    public void setGasPrice(BigDecimal gasPrice) {
        this.gasPrice = gasPrice;
    }

    public BigDecimal getProfitRate() {
        return profitRate;
    }

    public void setProfitRate(BigDecimal profitRate) {
        this.profitRate = profitRate;
    }

    public Object getResult() {
        return result;
    }

    public void setResult(Object result) {
        this.result = result;
    }

    @Override
    public String toString() {
        return "TradeResultDTO{" +
                "taskId='" + taskId + '\'' +
                ", timestamp=" + timestamp +
                ", taskType='" + taskType + '\'' +
                ", strategyId=" + strategyId +
                ", traceId='" + traceId + '\'' +
                ", userId=" + userId +
                ", symbol='" + symbol + '\'' +
                ", usdtAmount=" + usdtAmount +
                ", coinAmount=" + coinAmount +
                ", price=" + price +
                ", success=" + success +
                ", skipped=" + skipped +
                ", skipped=" + skipped +
                ", skipped=" + skipped +
                ", isSimulation=" + isSimulation +
                '}';
    }
}
