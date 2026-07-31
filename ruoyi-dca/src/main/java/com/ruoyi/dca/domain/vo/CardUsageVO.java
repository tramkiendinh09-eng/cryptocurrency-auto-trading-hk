package com.ruoyi.dca.domain.vo;

import java.util.Date;

/**
 * 卡密使用统计VO
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class CardUsageVO {
    /** 卡密ID */
    private Long cardId;

    /** 卡密 */
    private String cardKey;

    /** 卡密类型 */
    private String cardType;

    /** 卡密等级 */
    private String cardLevel;

    /** 状态 */
    private String status;

    /** 绑定用户ID */
    private Long bindUserId;

    /** 绑定机器码 */
    private String bindMachine;

    /** 激活时间 */
    private Date activeTime;

    /** 过期时间 */
    private Date expireTime;

    /** 剩余天数 */
    private Long remainingDays;

    /** 剩余次数 */
    private Integer remainingCounts;

    /** 总使用次数 */
    private Long totalUsage;

    /** 最后使用时间 */
    private Date lastUsageTime;

    /** 功能开关 */
    private String featureFlags;

    /** 批次号 */
    private String batchNo;

    public void setCardId(Long cardId) {
        this.cardId = cardId;
    }

    public Long getCardId() {
        return cardId;
    }

    public void setCardKey(String cardKey) {
        this.cardKey = cardKey;
    }

    public String getCardKey() {
        return cardKey;
    }

    public void setCardType(String cardType) {
        this.cardType = cardType;
    }

    public String getCardType() {
        return cardType;
    }

    public void setCardLevel(String cardLevel) {
        this.cardLevel = cardLevel;
    }

    public String getCardLevel() {
        return cardLevel;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getStatus() {
        return status;
    }

    public void setBindUserId(Long bindUserId) {
        this.bindUserId = bindUserId;
    }

    public Long getBindUserId() {
        return bindUserId;
    }

    public void setBindMachine(String bindMachine) {
        this.bindMachine = bindMachine;
    }

    public String getBindMachine() {
        return bindMachine;
    }

    public void setActiveTime(Date activeTime) {
        this.activeTime = activeTime;
    }

    public Date getActiveTime() {
        return activeTime;
    }

    public void setExpireTime(Date expireTime) {
        this.expireTime = expireTime;
    }

    public Date getExpireTime() {
        return expireTime;
    }

    public void setRemainingDays(Long remainingDays) {
        this.remainingDays = remainingDays;
    }

    public Long getRemainingDays() {
        return remainingDays;
    }

    public void setRemainingCounts(Integer remainingCounts) {
        this.remainingCounts = remainingCounts;
    }

    public Integer getRemainingCounts() {
        return remainingCounts;
    }

    public void setTotalUsage(Long totalUsage) {
        this.totalUsage = totalUsage;
    }

    public Long getTotalUsage() {
        return totalUsage;
    }

    public void setLastUsageTime(Date lastUsageTime) {
        this.lastUsageTime = lastUsageTime;
    }

    public Date getLastUsageTime() {
        return lastUsageTime;
    }

    public void setFeatureFlags(String featureFlags) {
        this.featureFlags = featureFlags;
    }

    public String getFeatureFlags() {
        return featureFlags;
    }

    public void setBatchNo(String batchNo) {
        this.batchNo = batchNo;
    }

    public String getBatchNo() {
        return batchNo;
    }
}
