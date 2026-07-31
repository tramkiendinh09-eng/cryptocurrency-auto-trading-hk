package com.ruoyi.dca.domain.vo;

import java.math.BigDecimal;

/**
 * 仪表盘概览统计VO
 *
 * @author ruoyi
 */
public class DashboardOverviewVO {

    /** 总策略数 */
    private Integer totalStrategies;

    /** 活跃策略数 */
    private Integer activeStrategies;

    /** 今日触发次数 */
    private Integer todayTriggers;

    /** 今日通知数 */
    private Integer todayNotifications;

    /** 总投入金额 (USDT) */
    private BigDecimal totalInvest;

    /** 当前价值 (USDT) */
    private BigDecimal currentValue;

    /** 盈亏金额 (USDT) */
    private BigDecimal profitAmount;

    /** 收益率 (%) */
    private BigDecimal profitRate;

    /** Worker在线状态 */
    private Boolean workerOnline;

    /** Redis连接状态 */
    private Boolean redisConnected;

    /** 队列长度 */
    private Integer queueLength;

    // Getters and Setters

    public Integer getTotalStrategies() {
        return totalStrategies;
    }

    public void setTotalStrategies(Integer totalStrategies) {
        this.totalStrategies = totalStrategies;
    }

    public Integer getActiveStrategies() {
        return activeStrategies;
    }

    public void setActiveStrategies(Integer activeStrategies) {
        this.activeStrategies = activeStrategies;
    }

    public Integer getTodayTriggers() {
        return todayTriggers;
    }

    public void setTodayTriggers(Integer todayTriggers) {
        this.todayTriggers = todayTriggers;
    }

    public Integer getTodayNotifications() {
        return todayNotifications;
    }

    public void setTodayNotifications(Integer todayNotifications) {
        this.todayNotifications = todayNotifications;
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

    public Boolean getWorkerOnline() {
        return workerOnline;
    }

    public void setWorkerOnline(Boolean workerOnline) {
        this.workerOnline = workerOnline;
    }

    public Boolean getRedisConnected() {
        return redisConnected;
    }

    public void setRedisConnected(Boolean redisConnected) {
        this.redisConnected = redisConnected;
    }

    public Integer getQueueLength() {
        return queueLength;
    }

    public void setQueueLength(Integer queueLength) {
        this.queueLength = queueLength;
    }
}
