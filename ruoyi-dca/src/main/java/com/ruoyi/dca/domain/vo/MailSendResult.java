package com.ruoyi.dca.domain.vo;

import java.io.Serializable;
import java.util.Date;

/**
 * 邮件发送结果
 *
 * @author ruoyi
 * @date 2026-04-03
 */
public class MailSendResult implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 是否成功 */
    private boolean success;

    /** 错误消息 */
    private String errorMessage;

    /** 发送时间 */
    private Date sendTime;

    /** 消息ID（邮件服务器返回） */
    private String messageId;

    public MailSendResult() {
        this.sendTime = new Date();
    }

    public MailSendResult(boolean success, String errorMessage) {
        this();
        this.success = success;
        this.errorMessage = errorMessage;
    }

    public static MailSendResult success() {
        return new MailSendResult(true, null);
    }

    public static MailSendResult fail(String errorMessage) {
        return new MailSendResult(false, errorMessage);
    }

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    public Date getSendTime() {
        return sendTime;
    }

    public void setSendTime(Date sendTime) {
        this.sendTime = sendTime;
    }

    public String getMessageId() {
        return messageId;
    }

    public void setMessageId(String messageId) {
        this.messageId = messageId;
    }
}
