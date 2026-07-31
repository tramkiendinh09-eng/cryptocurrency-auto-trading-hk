package com.ruoyi.dca.domain;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;

import java.util.Date;

/**
 * 通知记录对象 notify_record
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class NotifyRecord extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 渠道ID */
    @Excel(name = "渠道ID")
    private Long channelId;

    private String traceId;

    /** 渠道类型 */
    @Excel(name = "渠道类型")
    private String channelType;

    /** 渠道名称 */
    @Excel(name = "渠道名称")
    private String channelName;

    /** 通知标题 */
    @Excel(name = "通知标题")
    private String title;

    /** 通知内容 */
    private String content;

    /** 发送状态: 0待发送 1发送中 2成功 3失败 */
    @Excel(name = "发送状态", readConverterExp = "0=待发送,1=发送中,2=成功,3=失败")
    private Integer status;

    /** 重试次数 */
    @Excel(name = "重试次数")
    private Integer retryCount;

    /** 错误信息 */
    private String errorMsg;

    /** 目标接收人 */
    @Excel(name = "目标接收人")
    private String recipient;

    /** 模板ID */
    private Long templateId;

    /** 模板变量(JSON) */
    private String templateVars;

    /** 发送时间 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @Excel(name = "发送时间", width = 30, dateFormat = "yyyy-MM-dd HH:mm:ss")
    private Date sendTime;

    /** 扩展数据(JSON) */
    private String extData;

    public void setId(Long id) {
        this.id = id;
    }

    public Long getId() {
        return id;
    }

    public void setChannelId(Long channelId) {
        this.channelId = channelId;
    }

    public Long getChannelId() {
        return channelId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setChannelType(String channelType) {
        this.channelType = channelType;
    }

    public String getChannelType() {
        return channelType;
    }

    public void setChannelName(String channelName) {
        this.channelName = channelName;
    }

    public String getChannelName() {
        return channelName;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getTitle() {
        return title;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getContent() {
        return content;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }

    public Integer getStatus() {
        return status;
    }

    public void setRetryCount(Integer retryCount) {
        this.retryCount = retryCount;
    }

    public Integer getRetryCount() {
        return retryCount;
    }

    public void setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public void setRecipient(String recipient) {
        this.recipient = recipient;
    }

    public String getRecipient() {
        return recipient;
    }

    public void setTemplateId(Long templateId) {
        this.templateId = templateId;
    }

    public Long getTemplateId() {
        return templateId;
    }

    public void setTemplateVars(String templateVars) {
        this.templateVars = templateVars;
    }

    public String getTemplateVars() {
        return templateVars;
    }

    public void setSendTime(Date sendTime) {
        this.sendTime = sendTime;
    }

    public Date getSendTime() {
        return sendTime;
    }

    public void setExtData(String extData) {
        this.extData = extData;
    }

    public String getExtData() {
        return extData;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("channelId", getChannelId())
            .append("traceId", getTraceId())
            .append("channelType", getChannelType())
            .append("channelName", getChannelName())
            .append("title", getTitle())
            .append("content", getContent())
            .append("status", getStatus())
            .append("retryCount", getRetryCount())
            .append("errorMsg", getErrorMsg())
            .append("recipient", getRecipient())
            .append("templateId", getTemplateId())
            .append("templateVars", getTemplateVars())
            .append("sendTime", getSendTime())
            .append("extData", getExtData())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
