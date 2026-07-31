package com.ruoyi.dca.service.impl;

import java.util.*;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import com.ruoyi.common.core.redis.RedisCache;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.dca.domain.NotifyChannel;
import com.ruoyi.dca.mapper.NotifyChannelMapper;
import com.ruoyi.dca.service.INotifyChannelService;
import com.ruoyi.dca.service.IMailService;
import com.ruoyi.dca.domain.vo.MailSendResult;

/**
 * 通知渠道Service业务层处理
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@Service
public class NotifyChannelServiceImpl implements INotifyChannelService {
    private static final Logger log = LoggerFactory.getLogger(NotifyChannelServiceImpl.class);

    /** 渠道类型常量 */
    private static final String TYPE_EMAIL = "email";
    private static final String TYPE_TELEGRAM = "telegram";
    private static final String TYPE_DINGTALK = "dingtalk";
    private static final String TYPE_FEISHU = "feishu";
    private static final String TYPE_WEBHOOK = "webhook";

    @Autowired
    private NotifyChannelMapper notifyChannelMapper;



    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private RedisCache redisCache;

    @Autowired
    private IMailService mailService;

    /**
     * 查询通知渠道
     *
     * @param id 通知渠道主键
     * @return 通知渠道
     */
    @Override
    public NotifyChannel selectNotifyChannelById(Long id) {
        return notifyChannelMapper.selectNotifyChannelById(id);
    }

    /**
     * 查询通知渠道列表
     *
     * @param notifyChannel 通知渠道
     * @return 通知渠道
     */
    @Override
    public List<NotifyChannel> selectNotifyChannelList(NotifyChannel notifyChannel) {
        return notifyChannelMapper.selectNotifyChannelList(notifyChannel);
    }

    /**
     * 根据用户ID查询启用的渠道
     *
     * @param userId 用户ID
     * @return 通知渠道列表
     */
    @Override
    public List<NotifyChannel> selectEnabledByUserId(Long userId) {
        return notifyChannelMapper.selectEnabledByUserId(userId);
    }

    /**
     * 查询所有启用的渠道
     *
     * @return 通知渠道列表
     */
    @Override
    public List<NotifyChannel> selectAllEnabled() {
        return notifyChannelMapper.selectAllEnabled();
    }

    /**
     * 新增通知渠道
     *
     * @param notifyChannel 通知渠道
     * @return 结果
     */
    @Override
    @Transactional
    public int insertNotifyChannel(NotifyChannel notifyChannel) {
        // 验证渠道名称唯一性
        if (!checkChannelNameUnique(notifyChannel)) {
            throw new ServiceException("渠道名称已存在");
        }

        // 验证渠道配置
        Map<String, Object> validateResult = validateChannel(notifyChannel);
        if (!(Boolean) validateResult.get("valid")) {
            throw new ServiceException("渠道配置无效: " + validateResult.get("message"));
        }

        return notifyChannelMapper.insertNotifyChannel(notifyChannel);
    }

    /**
     * 修改通知渠道
     *
     * @param notifyChannel 通知渠道
     * @return 结果
     */
    @Override
    @Transactional
    public int updateNotifyChannel(NotifyChannel notifyChannel) {
        NotifyChannel oldChannel = notifyChannelMapper.selectNotifyChannelById(notifyChannel.getId());
        if (oldChannel == null) {
            throw new ServiceException("通知渠道不存在");
        }

        // 检查名称唯一性（排除自己）
        if (StringUtils.isNotEmpty(notifyChannel.getChannelName())) {
            NotifyChannel checkChannel = new NotifyChannel();
            checkChannel.setChannelName(notifyChannel.getChannelName());
            checkChannel.setUserId(notifyChannel.getUserId());
            List<NotifyChannel> list = notifyChannelMapper.selectNotifyChannelList(checkChannel);
            if (list.stream().anyMatch(c -> !c.getId().equals(notifyChannel.getId()))) {
                throw new ServiceException("渠道名称已存在");
            }
        }

        // 验证渠道配置
        Map<String, Object> validateResult = validateChannel(notifyChannel);
        if (!(Boolean) validateResult.get("valid")) {
            throw new ServiceException("渠道配置无效: " + validateResult.get("message"));
        }

        return notifyChannelMapper.updateNotifyChannel(notifyChannel);
    }

    /**
     * 批量删除通知渠道
     *
     * @param ids 需要删除的通知渠道主键
     * @return 结果
     */
    @Override
    @Transactional
    public int deleteNotifyChannelByIds(Long[] ids) {
        return notifyChannelMapper.deleteNotifyChannelByIds(ids);
    }

    /**
     * 删除通知渠道信息
     *
     * @param id 通知渠道主键
     * @return 结果
     */
    @Override
    @Transactional
    public int deleteNotifyChannelById(Long id) {
        return notifyChannelMapper.deleteNotifyChannelById(id);
    }

    /**
     * 更新渠道启用状态
     *
     * @param id 渠道ID
     * @param isEnabled 是否启用
     * @return 结果
     */
    @Override
    public int updateEnabledStatus(Long id, Integer isEnabled) {
        return notifyChannelMapper.updateEnabledStatus(id, isEnabled);
    }

    /**
     * 批量更新渠道启用状态
     *
     * @param ids 渠道ID列表
     * @param isEnabled 是否启用
     * @return 结果
     */
    @Override
    public int batchUpdateEnabledStatus(List<Long> ids, Integer isEnabled) {
        return notifyChannelMapper.batchUpdateEnabledStatus(ids, isEnabled);
    }

    /**
     * 测试发送通知
     *
     * @param id 渠道ID
     * @return 结果
     */
    @Override
    public Map<String, Object> testSend(Long id) {
        NotifyChannel channel = notifyChannelMapper.selectNotifyChannelById(id);
        if (channel == null) {
            throw new ServiceException("通知渠道不存在");
        }

        String title = "测试通知";
        String content = "这是一条测试通知消息，发送时间: " + new Date();

        try {
            boolean success = sendNotify(channel, title, content);

            Map<String, Object> result = new HashMap<>();
            result.put("success", success);
            result.put("message", success ? "测试发送成功" : "测试发送失败");
            result.put("channel", channel.getChannelName());
            result.put("sendTime", new Date());

            return result;
        } catch (Exception e) {
            log.error("测试发送失败", e);
            throw new ServiceException("测试发送失败: " + e.getMessage());
        }
    }

    /**
     * 测试邮件连接
     *
     * @param id 渠道ID
     * @return 是否成功
     */
    @Override
    public boolean testMailConnection(Long id) {
        NotifyChannel channel = notifyChannelMapper.selectNotifyChannelById(id);
        if (channel == null) {
            throw new ServiceException("通知渠道不存在");
        }

        if (!TYPE_EMAIL.equals(channel.getChannelType())) {
            throw new ServiceException("该渠道不是邮件类型");
        }

        // 构建SMTP配置
        Map<String, Object> config = new HashMap<>();
        config.put("smtpHost", channel.getSmtpHost());
        config.put("smtpPort", channel.getSmtpPort() != null ? channel.getSmtpPort() : 587);
        config.put("mailUsername", channel.getMailUsername());
        config.put("mailPassword", channel.getMailPassword());
        config.put("mailFrom", channel.getMailFrom());

        // 根据端口判断是否使用SSL
        boolean useSsl = channel.getSmtpPort() != null && channel.getSmtpPort() == 465;
        boolean useTls = !useSsl;
        config.put("useSsl", useSsl);
        config.put("useTls", useTls);

        return mailService.testConnection(config);
    }

    /**
     * 验证渠道配置
     *
     * @param notifyChannel 通知渠道
     * @return 验证结果
     */
    @Override
    public Map<String, Object> validateChannel(NotifyChannel notifyChannel) {
        Map<String, Object> result = new HashMap<>();
        result.put("valid", false);
        result.put("message", "");

        if (StringUtils.isEmpty(notifyChannel.getChannelType())) {
            result.put("message", "渠道类型不能为空");
            return result;
        }

        if (StringUtils.isEmpty(notifyChannel.getChannelName())) {
            result.put("message", "渠道名称不能为空");
            return result;
        }

        switch (notifyChannel.getChannelType()) {
            case TYPE_EMAIL -> {
                if (StringUtils.isEmpty(notifyChannel.getRecipient())) {
                    result.put("message", "收件人地址不能为空");
                    return result;
                }
                if (!notifyChannel.getRecipient().matches("^[A-Za-z0-9+_.-]+@(.+)$")) {
                    result.put("message", "收件人地址格式不正确");
                    return result;
                }
            }
            case TYPE_TELEGRAM -> {
                if (StringUtils.isEmpty(notifyChannel.getToken())) {
                    result.put("message", "Telegram Bot Token不能为空");
                    return result;
                }
                if (StringUtils.isEmpty(notifyChannel.getRecipient())) {
                    result.put("message", "Chat ID不能为空");
                    return result;
                }
            }
            case TYPE_DINGTALK, TYPE_FEISHU -> {
                if (StringUtils.isEmpty(notifyChannel.getWebhookUrl())) {
                    result.put("message", "Webhook URL不能为空");
                    return result;
                }
                if (!notifyChannel.getWebhookUrl().startsWith("https://")) {
                    result.put("message", "Webhook URL必须以https://开头");
                    return result;
                }
            }
            case TYPE_WEBHOOK -> {
                if (StringUtils.isEmpty(notifyChannel.getWebhookUrl())) {
                    result.put("message", "Webhook URL不能为空");
                    return result;
                }
            }
            default -> {
                result.put("message", "不支持的通知渠道类型");
                return result;
            }
        }

        result.put("valid", true);
        return result;
    }

    /**
     * 检查渠道名称是否唯一
     *
     * @param notifyChannel 通知渠道
     * @return 结果
     */
    @Override
    public boolean checkChannelNameUnique(NotifyChannel notifyChannel) {
        Long channelId = StringUtils.isNull(notifyChannel.getId()) ? -1L : notifyChannel.getId();
        NotifyChannel info = notifyChannelMapper.selectNotifyChannelById(channelId);

        if (info == null) {
            int count = notifyChannelMapper.checkChannelNameUnique(notifyChannel.getChannelName(), notifyChannel.getUserId());
            return count == 0;
        }

        return !notifyChannel.getChannelName().equals(info.getChannelName());
    }

    /**
     * 统计各类型渠道数量
     *
     * @return 统计结果
     */
    @Override
    public Map<String, Object> getTypeStatistics() {
        List<Map<String, Object>> typeList = notifyChannelMapper.countByType();
        Map<String, Object> result = new HashMap<>();

        for (Map<String, Object> item : typeList) {
            result.put((String) item.get("name"), item.get("value"));
        }

        return result;
    }

    /**
     * 发送通知（内部方法）
     *
     * @param channel 通知渠道
     * @param title 标题
     * @param content 内容
     * @return 是否成功
     */
    private boolean sendNotify(NotifyChannel channel, String title, String content) {
        try {
            switch (channel.getChannelType()) {
                case TYPE_EMAIL:
                    return sendEmail(channel, title, content);

                case TYPE_TELEGRAM:
                    return sendTelegram(channel, title, content);

                case TYPE_DINGTALK:
                    return sendDingTalk(channel, title, content);

                case TYPE_FEISHU:
                    return sendFeishu(channel, title, content);

                case TYPE_WEBHOOK:
                    return sendWebhook(channel, title, content);

                default:
                    log.error("不支持的通知渠道类型: {}", channel.getChannelType());
                    return false;
            }
        } catch (Exception e) {
            log.error("发送通知失败: channel={}, title={}, error={}",
                    channel.getChannelName(), title, e.getMessage());
            return false;
        }
    }

    /**
     * 发送邮件
     */
    private boolean sendEmail(NotifyChannel channel, String title, String content) {
        try {
            // 构建SMTP配置
            Map<String, Object> config = new HashMap<>();
            config.put("smtpHost", channel.getSmtpHost());
            config.put("smtpPort", channel.getSmtpPort() != null ? channel.getSmtpPort() : 587);
            config.put("mailUsername", channel.getMailUsername());
            config.put("mailPassword", channel.getMailPassword());
            config.put("mailFrom", channel.getMailFrom());

            // 根据端口判断是否使用SSL
            boolean useSsl = channel.getSmtpPort() != null && channel.getSmtpPort() == 465;
            boolean useTls = !useSsl; // 非SSL端口使用TLS
            config.put("useSsl", useSsl);
            config.put("useTls", useTls);

            // 发送HTML邮件
            String htmlContent = buildEmailHtml(title, content);
            MailSendResult result = mailService.sendHtmlMail(
                    channel.getRecipient(),
                    title,
                    htmlContent,
                    config
            );

            if (result.isSuccess()) {
                log.info("邮件发送成功: to={}, title={}", channel.getRecipient(), title);
                return true;
            } else {
                log.error("邮件发送失败: to={}, error={}", channel.getRecipient(), result.getErrorMessage());
                return false;
            }

        } catch (Exception e) {
            log.error("发送邮件异常: to={}, error={}", channel.getRecipient(), e.getMessage(), e);
            return false;
        }
    }

    /**
     * 构建邮件HTML内容
     */
    private String buildEmailHtml(String title, String content) {
        return "<!DOCTYPE html>" +
                "<html>" +
                "<head>" +
                "<meta charset='UTF-8'>" +
                "<style>" +
                "body { font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }" +
                ".container { max-width: 600px; margin: 0 auto; background: #ffffff; }" +
                ".header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center; }" +
                ".header h1 { margin: 0; font-size: 24px; font-weight: 500; }" +
                ".content { padding: 30px 20px; }" +
                ".content h2 { color: #667eea; margin-top: 0; }" +
                ".content p { line-height: 1.8; margin-bottom: 15px; }" +
                ".footer { background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 14px; }" +
                ".footer a { color: #667eea; text-decoration: none; }" +
                ".divider { height: 1px; background: #e9ecef; margin: 20px 0; }" +
                ".info-box { background: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; }" +
                "</style>" +
                "</head>" +
                "<body>" +
                "<div class='container'>" +
                "<div class='header'>" +
                "<h1>📧 " + escapeHtml(title) + "</h1>" +
                "</div>" +
                "<div class='content'>" +
                "<div class='info-box'>" +
                "<strong>⏰ 发送时间：</strong>" + new java.util.Date() +
                "</div>" +
                formatContent(content) +
                "</div>" +
                "<div class='footer'>" +
                "<p>本邮件由 <strong>智能交易系统</strong> 自动发送，请勿直接回复</p>" +
                "<div class='divider'></div>" +
                "<p>如有疑问，请联系系统管理员</p>" +
                "</div>" +
                "</div>" +
                "</body>" +
                "</html>";
    }

    /**
     * 格式化内容（将换行符转换为HTML段落）
     */
    private String formatContent(String content) {
        if (StringUtils.isEmpty(content)) {
            return "";
        }
        String[] paragraphs = content.split("\n");
        StringBuilder html = new StringBuilder();
        for (String p : paragraphs) {
            if (StringUtils.isNotEmpty(p.trim())) {
                html.append("<p>").append(escapeHtml(p.trim())).append("</p>");
            }
        }
        return html.toString();
    }

    /**
     * HTML转义
     */
    private String escapeHtml(String text) {
        if (StringUtils.isEmpty(text)) {
            return "";
        }
        return text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&#x27;");
    }

    /**
     * 发送Telegram消息
     */
    private boolean sendTelegram(NotifyChannel channel, String title, String content) {
        try {
            String url = "https://api.telegram.org/bot" + channel.getToken() + "/sendMessage";

            Map<String, Object> message = new HashMap<>();
            message.put("chat_id", channel.getRecipient());
            message.put("text", title + "\n\n" + content);
            message.put("parse_mode", "HTML");

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(message, headers);
            ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.POST, entity, Map.class);

            return response.getStatusCode().is2xxSuccessful() &&
                   Boolean.TRUE.equals(response.getBody().get("ok"));

        } catch (Exception e) {
            log.error("发送Telegram消息失败", e);
            return false;
        }
    }

    /**
     * 发送钉钉消息
     */
    private boolean sendDingTalk(NotifyChannel channel, String title, String content) {
        try {
            Map<String, Object> message = new HashMap<>();
            message.put("msgtype", "text");

            Map<String, String> text = new HashMap<>();
            text.put("content", title + "\n\n" + content);
            message.put("text", text);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(message, headers);
            ResponseEntity<Map> response = restTemplate.exchange(
                    channel.getWebhookUrl(),
                    HttpMethod.POST,
                    entity,
                    Map.class);

            return response.getStatusCode().is2xxSuccessful() &&
                   Integer.valueOf(0).equals(response.getBody().get("errcode"));

        } catch (Exception e) {
            log.error("发送钉钉消息失败", e);
            return false;
        }
    }

    /**
     * 发送飞书消息
     */
    private boolean sendFeishu(NotifyChannel channel, String title, String content) {
        try {
            Map<String, Object> message = new HashMap<>();
            message.put("msg_type", "text");

            Map<String, String> text = new HashMap<>();
            text.put("text", title + "\n\n" + content);
            message.put("content", text);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(message, headers);
            ResponseEntity<Map> response = restTemplate.exchange(
                    channel.getWebhookUrl(),
                    HttpMethod.POST,
                    entity,
                    Map.class);

            return response.getStatusCode().is2xxSuccessful();

        } catch (Exception e) {
            log.error("发送飞书消息失败", e);
            return false;
        }
    }

    /**
     * 发送自定义Webhook
     */
    private boolean sendWebhook(NotifyChannel channel, String title, String content) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("title", title);
            payload.put("content", content);
            payload.put("timestamp", System.currentTimeMillis());
            payload.put("channel", channel.getChannelName());

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(payload, headers);
            ResponseEntity<String> response = restTemplate.exchange(
                    channel.getWebhookUrl(),
                    HttpMethod.POST,
                    entity,
                    String.class);

            return response.getStatusCode().is2xxSuccessful();

        } catch (Exception e) {
            log.error("发送Webhook消息失败", e);
            return false;
        }
    }
}
