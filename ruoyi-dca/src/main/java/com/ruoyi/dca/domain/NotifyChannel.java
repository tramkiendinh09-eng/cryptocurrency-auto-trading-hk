package com.ruoyi.dca.domain;

import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;

/**
 * 通知渠道对象 notify_channel
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class NotifyChannel extends BaseEntity {
    private static final long serialVersionUID = 1L;

    /** 主键ID */
    private Long id;

    /** 用户ID */
    @Excel(name = "用户ID")
    private Long userId;

    /** 渠道类型: telegram/bark/pushplus/email */
    @Excel(name = "渠道类型")
    private String channelType;

    /** 渠道名称 */
    @Excel(name = "渠道名称")
    private String channelName;

    /** Webhook URL */
    private String webhookUrl;

    /** Token/Key */
    private String token;

    /** 收件人(邮箱或用户ID) */
    private String recipient;

    /** SMTP服务器地址 */
    @Excel(name = "SMTP服务器")
    private String smtpHost;

    /** SMTP端口 */
    @Excel(name = "SMTP端口")
    private Integer smtpPort;

    /** 发件人邮箱账号 */
    @Excel(name = "发件人邮箱")
    private String mailUsername;

    /** 邮箱密码/授权码（加密存储） */
    private String mailPassword;

    /** 发件人显示名称 */
    @Excel(name = "发件人名称")
    private String mailFrom;

    /** 是否启用: 0禁用 1启用 */
    @Excel(name = "是否启用")
    private Integer isEnabled;

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

    public void setWebhookUrl(String webhookUrl) {
        this.webhookUrl = webhookUrl;
    }

    public String getWebhookUrl() {
        return webhookUrl;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public String getToken() {
        return token;
    }

    public void setRecipient(String recipient) {
        this.recipient = recipient;
    }

    public String getRecipient() {
        return recipient;
    }

    public void setIsEnabled(Integer isEnabled) {
        this.isEnabled = isEnabled;
    }

    public Integer getIsEnabled() {
        return isEnabled;
    }

    public void setSmtpHost(String smtpHost) {
        this.smtpHost = smtpHost;
    }

    public String getSmtpHost() {
        return smtpHost;
    }

    public void setSmtpPort(Integer smtpPort) {
        this.smtpPort = smtpPort;
    }

    public Integer getSmtpPort() {
        return smtpPort;
    }

    public void setMailUsername(String mailUsername) {
        this.mailUsername = mailUsername;
    }

    public String getMailUsername() {
        return mailUsername;
    }

    public void setMailPassword(String mailPassword) {
        this.mailPassword = mailPassword;
    }

    public String getMailPassword() {
        return mailPassword;
    }

    public void setMailFrom(String mailFrom) {
        this.mailFrom = mailFrom;
    }

    public String getMailFrom() {
        return mailFrom;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, ToStringStyle.MULTI_LINE_STYLE)
            .append("id", getId())
            .append("userId", getUserId())
            .append("channelType", getChannelType())
            .append("channelName", getChannelName())
            .append("webhookUrl", getWebhookUrl())
            .append("token", getToken())
            .append("recipient", getRecipient())
            .append("smtpHost", getSmtpHost())
            .append("smtpPort", getSmtpPort())
            .append("mailUsername", getMailUsername())
            .append("mailFrom", getMailFrom())
            .append("isEnabled", getIsEnabled())
            .append("remark", getRemark())
            .append("createBy", getCreateBy())
            .append("createTime", getCreateTime())
            .append("updateBy", getUpdateBy())
            .append("updateTime", getUpdateTime())
            .toString();
    }
}
