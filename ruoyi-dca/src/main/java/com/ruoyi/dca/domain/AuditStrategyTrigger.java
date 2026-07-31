package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;
import java.math.BigDecimal;
import java.util.Date;

/**
 * 策略触发日志对象 audit_strategy_trigger
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class AuditStrategyTrigger extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 策略ID */
    @Excel(name = "策略ID")
    private Long strategyId;

    /** 用户ID */
    @Excel(name = "用户ID")
    private Long userId;

    /** 触发类型: scheduled/drop_check/rise_check/manual */
    @Excel(name = "触发类型")
    private String triggerType;

    /** 触发前价格 */
    @Excel(name = "触发前价格")
    private BigDecimal beforePrice;

    /** 触发后价格 */
    @Excel(name = "触发后价格")
    private BigDecimal afterPrice;

    /** 价格变化率(%) */
    @Excel(name = "价格变化率")
    private BigDecimal priceChange;

    /** 阈值 */
    @Excel(name = "阈值")
    private BigDecimal threshold;

    /** 触发的阶段 */
    @Excel(name = "触发阶段")
    private Integer phase;

    /** 触发结果: triggered/skipped/paused */
    @Excel(name = "触发结果")
    private String result;

    /** 结果描述 */
    private String resultDesc;

    /** 策略快照 JSON */
    private String strategySnapshot;

    /** 触发时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "触发时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date triggerTime;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setStrategyId(Long strategyId) {
        this.strategyId = strategyId;
    }

    public Long getStrategyId() {
        return strategyId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public Long getUserId() {
        return userId;
    }

    public void setTriggerType(String triggerType) {
        this.triggerType = triggerType;
    }

    public String getTriggerType() {
        return triggerType;
    }

    public void setBeforePrice(BigDecimal beforePrice) {
        this.beforePrice = beforePrice;
    }

    public BigDecimal getBeforePrice() {
        return beforePrice;
    }

    public void setAfterPrice(BigDecimal afterPrice) {
        this.afterPrice = afterPrice;
    }

    public BigDecimal getAfterPrice() {
        return afterPrice;
    }

    public void setPriceChange(BigDecimal priceChange) {
        this.priceChange = priceChange;
    }

    public BigDecimal getPriceChange() {
        return priceChange;
    }

    public void setThreshold(BigDecimal threshold) {
        this.threshold = threshold;
    }

    public BigDecimal getThreshold() {
        return threshold;
    }

    public void setPhase(Integer phase) {
        this.phase = phase;
    }

    public Integer getPhase() {
        return phase;
    }

    public void setResult(String result) {
        this.result = result;
    }

    public String getResult() {
        return result;
    }

    public void setResultDesc(String resultDesc) {
        this.resultDesc = resultDesc;
    }

    public String getResultDesc() {
        return resultDesc;
    }

    public void setStrategySnapshot(String strategySnapshot) {
        this.strategySnapshot = strategySnapshot;
    }

    public String getStrategySnapshot() {
        return strategySnapshot;
    }

    public void setTriggerTime(Date triggerTime) {
        this.triggerTime = triggerTime;
    }

    public Date getTriggerTime() {
        return triggerTime;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("strategyId", getStrategyId())
            .append("userId", getUserId())
            .append("triggerType", getTriggerType())
            .append("beforePrice", getBeforePrice())
            .append("afterPrice", getAfterPrice())
            .append("priceChange", getPriceChange())
            .append("threshold", getThreshold())
            .append("phase", getPhase())
            .append("result", getResult())
            .append("resultDesc", getResultDesc())
            .append("strategySnapshot", getStrategySnapshot())
            .append("triggerTime", getTriggerTime())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
