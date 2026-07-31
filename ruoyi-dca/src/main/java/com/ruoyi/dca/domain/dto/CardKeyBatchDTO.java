package com.ruoyi.dca.domain.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;
import java.io.Serializable;
import java.util.Map;

/**
 * 卡密批量生成DTO
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class CardKeyBatchDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    /** 生成数量 */
    @NotNull(message = "生成数量不能为空")
    @Min(value = 1, message = "生成数量至少为1")
    @Max(value = 1000, message = "生成数量最多为1000")
    private Integer count;

    /** 卡密类型: time/permanent/count/trial */
    @NotBlank(message = "卡密类型不能为空")
    private String cardType;

    /** 卡密等级: basic/pro/premium */
    @NotBlank(message = "卡密等级不能为空")
    private String cardLevel;

    /** 有效天数（时间版） */
    private Integer days;

    /** 次数限制（次数版） */
    private Integer counts;

    /** 功能开关 */
    private Map<String, Boolean> featureFlags;

    /** 批次号（可选，不传则自动生成） */
    private String batchNo;

    /** 备注 */
    private String remark;

    public void setCount(Integer count) {
        this.count = count;
    }

    public Integer getCount() {
        return count;
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

    public void setFeatureFlags(Map<String, Boolean> featureFlags) {
        this.featureFlags = featureFlags;
    }

    public Map<String, Boolean> getFeatureFlags() {
        return featureFlags;
    }

    public void setBatchNo(String batchNo) {
        this.batchNo = batchNo;
    }

    public String getBatchNo() {
        return batchNo;
    }

    public void setRemark(String remark) {
        this.remark = remark;
    }

    public String getRemark() {
        return remark;
    }
}
