package com.ruoyi.dca.domain;

import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;
import java.util.Date;

/**
 * 卡密对象 card_key
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class CardKey extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 卡密 */
    @Excel(name = "卡密")
    private String cardKey;

    /** 卡密类型: time/permanent/count/trial */
    @Excel(name = "卡密类型")
    private String cardType;

    /** 卡密等级: basic/pro/premium */
    @Excel(name = "卡密等级")
    private String cardLevel;

    /** 有效天数 */
    @Excel(name = "有效天数")
    private Integer days;

    /** 通知次数限制 */
    @Excel(name = "次数限制")
    private Integer counts;

    /** 功能开关 JSON */
    private String featureFlags;

    /** 状态: unused/activated/expired/disabled */
    @Excel(name = "状态")
    private String status;

    /** 绑定的机器码 */
    private String bindMachine;

    /** 绑定的用户ID */
    private Long bindUserId;

    /** 激活时间 */
    @Excel(name = "激活时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date activeTime;

    /** 过期时间 */
    @Excel(name = "过期时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date expireTime;

    /** 批次号 */
    @Excel(name = "批次号")
    private String batchNo;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
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

    public void setDays(Integer days) {
        this.days = days;
    }

    public Integer getDays() {
        return days;
    }

    public void setCounts(Integer counts) {
        this.counts = counts;
    }

    public Integer getCounts() {
        return counts;
    }

    public void setFeatureFlags(String featureFlags) {
        this.featureFlags = featureFlags;
    }

    public String getFeatureFlags() {
        return featureFlags;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getStatus() {
        return status;
    }

    public void setBindMachine(String bindMachine) {
        this.bindMachine = bindMachine;
    }

    public String getBindMachine() {
        return bindMachine;
    }

    public void setBindUserId(Long bindUserId) {
        this.bindUserId = bindUserId;
    }

    public Long getBindUserId() {
        return bindUserId;
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

    public void setBatchNo(String batchNo) {
        this.batchNo = batchNo;
    }

    public String getBatchNo() {
        return batchNo;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("cardKey", getCardKey())
            .append("cardType", getCardType())
            .append("cardLevel", getCardLevel())
            .append("days", getDays())
            .append("counts", getCounts())
            .append("featureFlags", getFeatureFlags())
            .append("status", getStatus())
            .append("bindMachine", getBindMachine())
            .append("bindUserId", getBindUserId())
            .append("activeTime", getActiveTime())
            .append("expireTime", getExpireTime())
            .append("batchNo", getBatchNo())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
