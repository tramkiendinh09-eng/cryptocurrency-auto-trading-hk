package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;
import java.util.Date;

/**
 * AI调用日志对象 audit_ai_call_log
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class AuditAiCallLog extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 用户ID */
    @Excel(name = "用户ID")
    private Long userId;

    /** 调用场景: market_analysis/risk_alert/trade_summary */
    @Excel(name = "调用场景")
    private String scene;

    /** 使用的模型 */
    @Excel(name = "使用模型")
    private String model;

    /** 提示词模板ID */
    private Long templateId;

    /** 提示词内容 */
    private String prompt;

    /** AI响应内容 */
    private String response;

    /** 请求Token数 */
    @Excel(name = "请求Token")
    private Integer promptTokens;

    /** 响应Token数 */
    @Excel(name = "响应Token")
    private Integer completionTokens;

    /** 总Token数 */
    @Excel(name = "总Token")
    private Integer totalTokens;

    /** 调用状态: 0失败 1成功 */
    @Excel(name = "调用状态")
    private Integer status;

    /** 错误信息 */
    private String errorMsg;

    /** 响应时间(ms) */
    @Excel(name = "响应时间")
    private Long responseTime;

    /** 调用时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "调用时间", dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date callTime;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public Long getUserId() {
        return userId;
    }

    public void setScene(String scene) {
        this.scene = scene;
    }

    public String getScene() {
        return scene;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public String getModel() {
        return model;
    }

    public void setTemplateId(Long templateId) {
        this.templateId = templateId;
    }

    public Long getTemplateId() {
        return templateId;
    }

    public void setPrompt(String prompt) {
        this.prompt = prompt;
    }

    public String getPrompt() {
        return prompt;
    }

    public void setResponse(String response) {
        this.response = response;
    }

    public String getResponse() {
        return response;
    }

    public void setPromptTokens(Integer promptTokens) {
        this.promptTokens = promptTokens;
    }

    public Integer getPromptTokens() {
        return promptTokens;
    }

    public void setCompletionTokens(Integer completionTokens) {
        this.completionTokens = completionTokens;
    }

    public Integer getCompletionTokens() {
        return completionTokens;
    }

    public void setTotalTokens(Integer totalTokens) {
        this.totalTokens = totalTokens;
    }

    public Integer getTotalTokens() {
        return totalTokens;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }

    public Integer getStatus() {
        return status;
    }

    public void setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public void setResponseTime(Long responseTime) {
        this.responseTime = responseTime;
    }

    public Long getResponseTime() {
        return responseTime;
    }

    public void setCallTime(Date callTime) {
        this.callTime = callTime;
    }

    public Date getCallTime() {
        return callTime;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("userId", getUserId())
            .append("scene", getScene())
            .append("model", getModel())
            .append("templateId", getTemplateId())
            .append("prompt", getPrompt())
            .append("response", getResponse())
            .append("promptTokens", getPromptTokens())
            .append("completionTokens", getCompletionTokens())
            .append("totalTokens", getTotalTokens())
            .append("status", getStatus())
            .append("errorMsg", getErrorMsg())
            .append("responseTime", getResponseTime())
            .append("callTime", getCallTime())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
