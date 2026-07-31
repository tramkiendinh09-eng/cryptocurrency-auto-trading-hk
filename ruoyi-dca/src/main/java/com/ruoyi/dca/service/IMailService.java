package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.vo.MailSendResult;
import java.util.Map;

/**
 * 邮件服务接口
 *
 * @author ruoyi
 * @date 2026-04-03
 */
public interface IMailService {

    /**
     * 发送纯文本邮件
     *
     * @param to 收件人邮箱
     * @param subject 邮件主题
     * @param content 邮件内容
     * @param config SMTP配置（从通知渠道读取）
     * @return 发送结果
     */
    MailSendResult sendTextMail(String to, String subject, String content, Map<String, Object> config);

    /**
     * 发送HTML邮件
     *
     * @param to 收件人邮箱
     * @param subject 邮件主题
     * @param htmlContent HTML内容
     * @param config SMTP配置
     * @return 发送结果
     */
    MailSendResult sendHtmlMail(String to, String subject, String htmlContent, Map<String, Object> config);

    /**
     * 发送模板邮件
     *
     * @param to 收件人邮箱
     * @param subject 邮件主题
     * @param templateName 模板名称
     * @param variables 模板变量
     * @param config SMTP配置
     * @return 发送结果
     */
    MailSendResult sendTemplateMail(String to, String subject, String templateName,
                                    Map<String, Object> variables, Map<String, Object> config);

    /**
     * 测试邮件连接
     *
     * @param config SMTP配置
     * @return 测试结果
     */
    boolean testConnection(Map<String, Object> config);
}
