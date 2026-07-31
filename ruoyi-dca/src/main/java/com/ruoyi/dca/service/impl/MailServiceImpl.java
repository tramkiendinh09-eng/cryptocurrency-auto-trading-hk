package com.ruoyi.dca.service.impl;

import com.ruoyi.dca.domain.vo.MailSendResult;
import com.ruoyi.dca.service.IMailService;
import jakarta.mail.*;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.Map;
import java.util.Properties;

/**
 * 邮件服务实现
 *
 * @author ruoyi
 * @date 2026-04-03
 */
@Service
public class MailServiceImpl implements IMailService {

    private static final Logger log = LoggerFactory.getLogger(MailServiceImpl.class);

    private static final int DEFAULT_TIMEOUT = 10000; // 10秒
    private static final int DEFAULT_CONNECTION_TIMEOUT = 10000; // 10秒
    private static final int DEFAULT_WRITE_TIMEOUT = 10000; // 10秒

    @Override
    public MailSendResult sendTextMail(String to, String subject, String content, Map<String, Object> config) {
        try {
            Session session = createSession(config);
            Message message = createMessage(session, to, subject, config);

            // 设置纯文本内容
            message.setText(content);
            message.setContent(content, "text/plain;charset=UTF-8");

            return sendMessage(message, session, config);
        } catch (Exception e) {
            log.error("发送纯文本邮件失败: to={}, subject={}, error={}", to, subject, e.getMessage(), e);
            return MailSendResult.fail("发送纯文本邮件失败: " + e.getMessage());
        }
    }

    @Override
    public MailSendResult sendHtmlMail(String to, String subject, String htmlContent, Map<String, Object> config) {
        try {
            Session session = createSession(config);
            Message message = createMessage(session, to, subject, config);

            // 设置HTML内容
            message.setContent(htmlContent, "text/html;charset=UTF-8");

            return sendMessage(message, session, config);
        } catch (Exception e) {
            log.error("发送HTML邮件失败: to={}, subject={}, error={}", to, subject, e.getMessage(), e);
            return MailSendResult.fail("发送HTML邮件失败: " + e.getMessage());
        }
    }

    @Override
    public MailSendResult sendTemplateMail(String to, String subject, String templateName,
                                           Map<String, Object> variables, Map<String, Object> config) {
        try {
            // TODO: 实现模板引擎处理（可以使用Thymeleaf或FreeMarker）
            // 目前先返回HTML邮件
            String htmlContent = buildTemplateContent(templateName, variables);
            return sendHtmlMail(to, subject, htmlContent, config);
        } catch (Exception e) {
            log.error("发送模板邮件失败: to={}, template={}, error={}", to, templateName, e.getMessage(), e);
            return MailSendResult.fail("发送模板邮件失败: " + e.getMessage());
        }
    }

    @Override
    public boolean testConnection(Map<String, Object> config) {
        try {
            Session session = createSession(config);
            Transport transport = null;
            try {
                transport = session.getTransport();
                String username = getString(config, "mailUsername");
                String password = getString(config, "mailPassword");
                transport.connect(getSmtpHost(config), getSmtpPort(config), username, password);
                return true;
            } finally {
                if (transport != null) {
                    try {
                        transport.close();
                    } catch (Exception e) {
                        log.warn("关闭Transport失败", e);
                    }
                }
            }
        } catch (Exception e) {
            log.error("测试邮件连接失败: {}", e.getMessage(), e);
            return false;
        }
    }

    /**
     * 创建邮件会话
     */
    private Session createSession(Map<String, Object> config) {
        Properties props = new Properties();

        String smtpHost = getSmtpHost(config);
        Integer smtpPort = getSmtpPort(config);

        // SMTP服务器配置
        props.put("mail.smtp.host", smtpHost);
        props.put("mail.smtp.port", smtpPort);

        // 认证配置
        props.put("mail.smtp.auth", "true");

        // SSL/TLS配置
        boolean useSsl = getBoolean(config, "useSsl", false);
        boolean useTls = getBoolean(config, "useTls", true);

        if (useSsl) {
            props.put("mail.smtp.ssl.enable", "true");
            props.put("mail.smtp.socketFactory.port", smtpPort);
            props.put("mail.smtp.socketFactory.class", "javax.net.ssl.SSLSocketFactory");
            props.put("mail.smtp.socketFactory.fallback", "false");
        } else if (useTls) {
            props.put("mail.smtp.starttls.enable", "true");
            props.put("mail.smtp.starttls.required", "true");
        }

        // 超时配置
        props.put("mail.smtp.connectiontimeout", DEFAULT_CONNECTION_TIMEOUT);
        props.put("mail.smtp.timeout", DEFAULT_TIMEOUT);
        props.put("mail.smtp.writetimeout", DEFAULT_WRITE_TIMEOUT);

        // 调试模式
        if (log.isDebugEnabled()) {
            props.put("mail.debug", "true");
        }

        return Session.getInstance(props, new Authenticator() {
            @Override
            protected PasswordAuthentication getPasswordAuthentication() {
                String username = getString(config, "mailUsername");
                String password = getString(config, "mailPassword");
                return new PasswordAuthentication(username, password);
            }
        });
    }

    /**
     * 创建邮件消息
     */
    private Message createMessage(Session session, String to, String subject, Map<String, Object> config)
            throws Exception {
        Message message = new MimeMessage(session);

        // 发件人
        String from = getString(config, "mailFrom");
        if (isEmpty(from)) {
            from = getString(config, "mailUsername");
        }
        message.setFrom(new InternetAddress(from));

        // 收件人
        message.setRecipients(Message.RecipientType.TO, InternetAddress.parse(to));

        // 主题
        message.setSubject(subject);

        // 发送时间
        message.setSentDate(new Date());

        return message;
    }

    /**
     * 发送消息
     */
    private MailSendResult sendMessage(Message message, Session session, Map<String, Object> config) {
        Transport transport = null;
        try {
            transport = session.getTransport();
            String username = getString(config, "mailUsername");
            String password = getString(config, "mailPassword");

            log.info("开始发送邮件: smtpHost={}, port={}, from={}, to={}",
                    getSmtpHost(config), getSmtpPort(config),
                    message.getFrom(), message.getAllRecipients());

            transport.connect(getSmtpHost(config), getSmtpPort(config), username, password);
            transport.sendMessage(message, message.getAllRecipients());

            log.info("邮件发送成功");
            return MailSendResult.success();
        } catch (Exception e) {
            log.error("邮件发送失败", e);
            return MailSendResult.fail(e.getMessage());
        } finally {
            if (transport != null) {
                try {
                    transport.close();
                } catch (Exception e) {
                    log.warn("关闭Transport失败", e);
                }
            }
        }
    }

    /**
     * 构建模板内容（简单实现，可替换为模板引擎）
     */
    private String buildTemplateContent(String templateName, Map<String, Object> variables) {
        // 这里可以实现模板引擎逻辑
        // 暂时返回简单的HTML
        return "<!DOCTYPE html>" +
                "<html>" +
                "<head>" +
                "<meta charset='UTF-8'>" +
                "<style>" +
                "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }" +
                ".container { max-width: 600px; margin: 0 auto; padding: 20px; }" +
                ".header { background: #007bff; color: white; padding: 20px; text-align: center; }" +
                ".content { padding: 20px; background: #f9f9f9; }" +
                ".footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }" +
                "</style>" +
                "</head>" +
                "<body>" +
                "<div class='container'>" +
                "<div class='header'><h2>" + getString(variables, "title", "通知") + "</h2></div>" +
                "<div class='content'>" +
                "<p>" + getString(variables, "content", "") + "</p>" +
                "</div>" +
                "<div class='footer'>" +
                "<p>本邮件由系统自动发送，请勿回复</p>" +
                "<p>发送时间: " + new Date() + "</p>" +
                "</div>" +
                "</div>" +
                "</body>" +
                "</html>";
    }

    // ==================== 辅助方法 ====================

    private String getSmtpHost(Map<String, Object> config) {
        return getString(config, "smtpHost", "smtp.gmail.com");
    }

    private Integer getSmtpPort(Map<String, Object> config) {
        Object port = config.get("smtpPort");
        if (port instanceof Integer) {
            return (Integer) port;
        }
        if (port instanceof String) {
            try {
                return Integer.parseInt((String) port);
            } catch (NumberFormatException e) {
                // 使用默认值
            }
        }
        return 587; // 默认使用TLS端口
    }

    private String getString(Map<String, Object> map, String key) {
        Object value = map.get(key);
        return value != null ? value.toString() : null;
    }

    private String getString(Map<String, Object> map, String key, String defaultValue) {
        String value = getString(map, key);
        return isEmpty(value) ? defaultValue : value;
    }

    private boolean getBoolean(Map<String, Object> map, String key, boolean defaultValue) {
        Object value = map.get(key);
        if (value instanceof Boolean) {
            return (Boolean) value;
        }
        if (value instanceof String) {
            return Boolean.parseBoolean((String) value);
        }
        return defaultValue;
    }

    private boolean isEmpty(String str) {
        return str == null || str.trim().isEmpty();
    }
}
