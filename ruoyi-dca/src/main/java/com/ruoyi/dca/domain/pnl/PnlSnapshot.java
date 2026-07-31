package com.ruoyi.dca.domain.pnl;

import java.math.BigDecimal;

/**
 * 盈亏快照实体类
 *
 * 记录账户盈亏状态的快照信息，包括账户权益、未实现盈亏、已实现盈亏、
 * 日盈亏、最大回撤等关键指标。
 *
 * @author ruoyi-dca
 */
public class PnlSnapshot {
    /** 主键ID */
    private Long id;

    /** 追踪ID */
    private String traceId;

    /** 运行模式：paper/shadow/live */
    private String mode;

    /** 账户权益 */
    private BigDecimal accountEquity;

    /** 未实现盈亏 */
    private BigDecimal unrealizedPnl;

    /** 已实现盈亏 */
    private BigDecimal realizedPnl;

    /** 日盈亏 */
    private BigDecimal dailyPnl;

    /** 最大回撤百分比 */
    private BigDecimal maxDrawdownPct;

    /** 峰值账户权益 */
    private BigDecimal peakAccountEquity;

    /** 创建时间 */
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

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public BigDecimal getAccountEquity() {
        return accountEquity;
    }

    public void setAccountEquity(BigDecimal accountEquity) {
        this.accountEquity = accountEquity;
    }

    public BigDecimal getUnrealizedPnl() {
        return unrealizedPnl;
    }

    public void setUnrealizedPnl(BigDecimal unrealizedPnl) {
        this.unrealizedPnl = unrealizedPnl;
    }

    public BigDecimal getRealizedPnl() {
        return realizedPnl;
    }

    public void setRealizedPnl(BigDecimal realizedPnl) {
        this.realizedPnl = realizedPnl;
    }

    public BigDecimal getDailyPnl() {
        return dailyPnl;
    }

    public void setDailyPnl(BigDecimal dailyPnl) {
        this.dailyPnl = dailyPnl;
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

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}
