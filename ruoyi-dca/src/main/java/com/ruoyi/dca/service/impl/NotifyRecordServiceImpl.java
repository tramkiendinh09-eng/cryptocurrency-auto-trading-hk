package com.ruoyi.dca.service.impl;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import java.util.Properties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.core.redis.RedisCache;
import com.ruoyi.common.utils.DateUtils;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.dca.domain.NotifyChannel;
import com.ruoyi.dca.domain.NotifyRecord;
import com.ruoyi.dca.mapper.NotifyChannelMapper;
import com.ruoyi.dca.mapper.NotifyRecordMapper;
import com.ruoyi.dca.service.INotifyRecordService;

/**
 * 通知记录Service业务层处理
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@Service
public class NotifyRecordServiceImpl implements INotifyRecordService {
    private static final Logger log = LoggerFactory.getLogger(NotifyRecordServiceImpl.class);

    /** 发送状态常量 */
    private static final Integer STATUS_PENDING = 0;      // 待发送
    private static final Integer STATUS_SENDING = 1;      // 发送中
    private static final Integer STATUS_SUCCESS = 2;      // 成功
    private static final Integer STATUS_FAILED = 3;       // 失败

    /** 最大重试次数 */
    private static final int MAX_RETRY_COUNT = 3;

    /** 通知聚合缓存前缀 */
    private static final String AGGREGATE_CACHE_PREFIX = "notify_aggregate:";

    @Autowired
    private NotifyRecordMapper notifyRecordMapper;

    @Autowired
    private NotifyChannelMapper notifyChannelMapper;

    @Autowired
    private RedisCache redisCache;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private RestTemplate restTemplate;

    /**
     * 查询通知记录
     *
     * @param id 通知记录主键
     * @return 通知记录
     */
    @Override
    public NotifyRecord selectNotifyRecordById(Long id) {
        return notifyRecordMapper.selectNotifyRecordById(id);
    }

    /**
     * 查询通知记录列表
     *
     * @param notifyRecord 通知记录
     * @return 通知记录
     */
    @Override
    public List<NotifyRecord> selectNotifyRecordList(NotifyRecord notifyRecord) {
        return notifyRecordMapper.selectNotifyRecordList(notifyRecord);
    }

    /**
     * 根据渠道ID查询通知记录
     *
     * @param channelId 渠道ID
     * @return 通知记录列表
     */
    @Override
    public List<NotifyRecord> selectByChannelId(Long channelId) {
        return notifyRecordMapper.selectByChannelId(channelId);
    }

    /**
     * 新增通知记录
     *
     * @param notifyRecord 通知记录
     * @return 结果
     */
    @Override
    public int insertNotifyRecord(NotifyRecord notifyRecord) {
        return notifyRecordMapper.insertNotifyRecord(notifyRecord);
    }

    /**
     * 批量删除通知记录
     *
     * @param ids 需要删除的通知记录主键
     * @return 结果
     */
    @Override
    @Transactional
    public int deleteNotifyRecordByIds(Long[] ids) {
        return notifyRecordMapper.deleteNotifyRecordByIds(ids);
    }

    /**
     * 删除通知记录信息
     *
     * @param id 通知记录主键
     * @return 结果
     */
    @Override
    @Transactional
    public int deleteNotifyRecordById(Long id) {
        return notifyRecordMapper.deleteNotifyRecordById(id);
    }

    /**
     * 发送通知
     *
     * @param channelId 渠道ID
     * @param title 标题
     * @param content 内容
     * @return 结果
     */
    @Override
    @Async
    public Map<String, Object> sendNotification(Long channelId, String title, String content) {
        return sendNotification(channelId, title, content, null);
    }

    @Override
    @Async
    public Map<String, Object> sendNotification(Long channelId, String title, String content, String traceId) {
        Map<String, Object> result = new HashMap<>();

        // 查询渠道
        NotifyChannel channel = notifyChannelMapper.selectNotifyChannelById(channelId);
        if (channel == null) {
            result.put("success", false);
            result.put("message", "通知渠道不存在");
            return result;
        }

        if (channel.getIsEnabled() != 1) {
            result.put("success", false);
            result.put("message", "通知渠道未启用");
            return result;
        }

        // 创建通知记录
        NotifyRecord record = new NotifyRecord();
        record.setChannelId(channelId);
        record.setTraceId(traceId);
        record.setChannelType(channel.getChannelType());
        record.setChannelName(channel.getChannelName());
        record.setTitle(title);
        record.setContent(content);
        record.setStatus(STATUS_SENDING);
        record.setRetryCount(0);
        record.setRecipient(channel.getRecipient());

        notifyRecordMapper.insertNotifyRecord(record);

        // 发送通知
        try {
            boolean success = doSend(channel, title, content);

            // 更新发送状态
            if (success) {
                notifyRecordMapper.updateSendStatus(record.getId(), STATUS_SUCCESS, null);
                result.put("success", true);
                result.put("message", "发送成功");
                result.put("recordId", record.getId());
            } else {
                notifyRecordMapper.updateSendStatus(record.getId(), STATUS_FAILED, "发送失败");
                result.put("success", false);
                result.put("message", "发送失败");
                result.put("recordId", record.getId());
            }

            result.put("channel", channel.getChannelName());
            result.put("sendTime", DateUtils.getNowDate());

        } catch (Exception e) {
            log.error("发送通知异常", e);
            notifyRecordMapper.updateSendStatus(record.getId(), STATUS_FAILED, e.getMessage());
            result.put("success", false);
            result.put("message", "发送异常: " + e.getMessage());
        }

        return result;
    }

    /**
     * 批量发送通知
     *
     * @param channelIds 渠道ID列表
     * @param title 标题
     * @param content 内容
     * @return 结果
     */
    @Override
    public Map<String, Object> batchSendNotification(List<Long> channelIds, String title, String content) {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> results = new ArrayList<>();
        int successCount = 0;
        int failCount = 0;

        for (Long channelId : channelIds) {
            Map<String, Object> sendResult = sendNotification(channelId, title, content);
            results.add(sendResult);

            if (Boolean.TRUE.equals(sendResult.get("success"))) {
                successCount++;
            } else {
                failCount++;
            }
        }

        result.put("total", channelIds.size());
        result.put("successCount", successCount);
        result.put("failCount", failCount);
        result.put("details", results);

        return result;
    }

    /**
     * 根据用户ID发送通知
     *
     * @param userId 用户ID
     * @param title 标题
     * @param content 内容
     * @return 结果
     */
    @Override
    public Map<String, Object> sendByUserId(Long userId, String title, String content) {
        // 查询用户启用的渠道
        List<NotifyChannel> channels = notifyChannelMapper.selectEnabledByUserId(userId);

        if (channels.isEmpty()) {
            Map<String, Object> result = new HashMap<>();
            result.put("success", false);
            result.put("message", "用户未配置启用的通知渠道");
            return result;
        }

        // 批量发送
        List<Long> channelIds = channels.stream()
                .map(NotifyChannel::getId)
                .collect(Collectors.toList());

        return batchSendNotification(channelIds, title, content);
    }

    /**
     * 使用模板发送通知
     *
     * @param channelId 渠道ID
     * @param templateId 模板ID
     * @param variables 模板变量
     * @return 结果
     */
    @Override
    public Map<String, Object> sendByTemplate(Long channelId, Long templateId, Map<String, Object> variables) {
        // TODO: 实现模板发送逻辑
        // 1. 根据templateId查询模板
        // 2. 使用variables替换模板变量
        // 3. 调用sendNotification发送

        Map<String, Object> result = new HashMap<>();
        result.put("success", false);
        result.put("message", "模板发送功能待实现");
        return result;
    }

    /**
     * 重试失败的通知
     *
     * @param id 记录ID
     * @return 结果
     */
    @Override
    public Map<String, Object> retrySend(Long id) {
        Map<String, Object> result = new HashMap<>();

        NotifyRecord record = notifyRecordMapper.selectNotifyRecordById(id);
        if (record == null) {
            result.put("success", false);
            result.put("message", "通知记录不存在");
            return result;
        }

        if (record.getStatus() != STATUS_FAILED) {
            result.put("success", false);
            result.put("message", "只能重试失败的通知");
            return result;
        }

        if (record.getRetryCount() >= MAX_RETRY_COUNT) {
            result.put("success", false);
            result.put("message", "已达到最大重试次数");
            return result;
        }

        // 增加重试次数
        notifyRecordMapper.incrementRetryCount(id);

        // 重新发送
        NotifyChannel channel = notifyChannelMapper.selectNotifyChannelById(record.getChannelId());
        if (channel == null) {
            result.put("success", false);
            result.put("message", "通知渠道不存在");
            return result;
        }

        try {
            boolean success = doSend(channel, record.getTitle(), record.getContent());

            if (success) {
                notifyRecordMapper.updateSendStatus(id, STATUS_SUCCESS, null);
                result.put("success", true);
                result.put("message", "重试成功");
            } else {
                notifyRecordMapper.updateSendStatus(id, STATUS_FAILED, "重试失败");
                result.put("success", false);
                result.put("message", "重试失败");
            }

        } catch (Exception e) {
            log.error("重试发送通知异常", e);
            notifyRecordMapper.updateSendStatus(id, STATUS_FAILED, e.getMessage());
            result.put("success", false);
            result.put("message", "重试异常: " + e.getMessage());
        }

        return result;
    }

    /**
     * 批量重试失败的通知
     *
     * @return 重试结果
     */
    @Override
    @Transactional
    public Map<String, Object> batchRetryFailed() {
        Map<String, Object> result = new HashMap<>();

        // 查询可重试的记录
        List<NotifyRecord> records = notifyRecordMapper.selectRetryableRecords(MAX_RETRY_COUNT);

        if (records.isEmpty()) {
            result.put("total", 0);
            result.put("successCount", 0);
            result.put("failCount", 0);
            result.put("message", "没有需要重试的通知");
            return result;
        }

        int successCount = 0;
        int failCount = 0;
        List<Map<String, Object>> details = new ArrayList<>();

        for (NotifyRecord record : records) {
            Map<String, Object> retryResult = retrySend(record.getId());
            details.add(retryResult);

            if (Boolean.TRUE.equals(retryResult.get("success"))) {
                successCount++;
            } else {
                failCount++;
            }
        }

        result.put("total", records.size());
        result.put("successCount", successCount);
        result.put("failCount", failCount);
        result.put("details", details);
        result.put("message", String.format("批量重试完成，成功%d条，失败%d条", successCount, failCount));

        return result;
    }

    /**
     * 清空过期的成功记录
     *
     * @param days 保留天数
     * @return 删除数量
     */
    @Override
    @Transactional
    public int cleanExpiredRecords(Integer days) {
        return notifyRecordMapper.cleanExpiredRecords(days);
    }

    /**
     * 统计发送状态数量
     *
     * @return 统计结果
     */
    @Override
    public Map<String, Object> getStatusStatistics() {
        List<Map<String, Object>> statusList = notifyRecordMapper.countByStatus();
        Map<String, Object> result = new HashMap<>();

        for (Map<String, Object> item : statusList) {
            result.put((String) item.get("name"), item.get("value"));
        }

        return result;
    }

    /**
     * 统计各渠道发送数量
     *
     * @return 统计结果
     */
    @Override
    public Map<String, Object> getChannelStatistics() {
        List<Map<String, Object>> channelList = notifyRecordMapper.countByChannel();
        Map<String, Object> result = new HashMap<>();

        for (Map<String, Object> item : channelList) {
            result.put((String) item.get("name"), item.get("value"));
        }

        return result;
    }

    /**
     * 获取发送统计概览
     *
     * @return 统计概览
     */
    @Override
    public Map<String, Object> getSendOverview() {
        Map<String, Object> result = new HashMap<>();

        // 今日发送数量
        int todayCount = notifyRecordMapper.countTodaySends();
        result.put("todayCount", todayCount);

        // 状态统计
        result.putAll(getStatusStatistics());

        // 成功率
        Map<String, Object> successRate = notifyRecordMapper.getSuccessRate();
        result.put("successRate", successRate.get("successRate"));
        result.put("weekTotal", successRate.get("total"));
        result.put("weekSuccess", successRate.get("success"));
        result.put("weekFailed", successRate.get("failed"));

        return result;
    }

    /**
     * 获取发送失败统计
     *
     * @param days 天数
     * @return 统计结果
     */
    @Override
    public List<Map<String, Object>> getFailedStats(Integer days) {
        return notifyRecordMapper.getFailedStats(days);
    }

    /**
     * 渠道类型常量
     */
    private static final String TYPE_EMAIL = "email";
    private static final String TYPE_TELEGRAM = "telegram";
    private static final String TYPE_DINGTALK = "dingtalk";
    private static final String TYPE_FEISHU = "feishu";
    private static final String TYPE_WEBHOOK = "webhook";

    /**
     * 执行发送（内部方法）
     */
    private boolean doSend(NotifyChannel channel, String title, String content) {
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
            log.info("Sending email: to={}, title={}", channel.getRecipient(), title);

            // 检查SMTP配置
            if (channel.getSmtpHost() == null || channel.getSmtpHost().isEmpty()) {
                log.error("SMTP host is not configured for channel {}", channel.getId());
                return false;
            }

            if (channel.getMailUsername() == null || channel.getMailUsername().isEmpty()) {
                log.error("Mail username is not configured for channel {}", channel.getId());
                return false;
            }

            if (channel.getMailPassword() == null || channel.getMailPassword().isEmpty()) {
                log.error("Mail password is not configured for channel {}", channel.getId());
                return false;
            }

            // 创建JavaMailSender实例
            JavaMailSenderImpl mailSender = new JavaMailSenderImpl();
            mailSender.setHost(channel.getSmtpHost());
            mailSender.setPort(channel.getSmtpPort() != null ? channel.getSmtpPort() : 587);
            mailSender.setUsername(channel.getMailUsername());
            mailSender.setPassword(channel.getMailPassword());

            // 配置SMTP属性
            Properties props = mailSender.getJavaMailProperties();
            props.put("mail.transport.protocol", "smtp");
            props.put("mail.smtp.auth", "true");
            props.put("mail.smtp.starttls.enable", "true");
            props.put("mail.smtp.starttls.required", "true");
            props.put("mail.smtp.ssl.trust", channel.getSmtpHost());
            props.put("mail.smtp.connectiontimeout", "5000");
            props.put("mail.smtp.timeout", "5000");
            props.put("mail.smtp.writetimeout", "5000");

            // 创建邮件消息
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(channel.getMailUsername()); // 使用配置的发件人邮箱
            message.setTo(channel.getRecipient());
            message.setSubject(title);
            message.setText(content);

            // 发送邮件
            mailSender.send(message);

            log.info("Email sent successfully: to={}, title={}", channel.getRecipient(), title);
            return true;

        } catch (Exception e) {
            log.error("Failed to send email: to={}, title={}, error={}",
                    channel.getRecipient(), title, e.getMessage(), e);
            return false;
        }
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

    /**
     * 聚合通知发送
     * 将相同类型的消息聚合后发送，避免消息轰炸
     *
     * @param channelId 渠道ID
     * @param title 标题
     * @param content 内容
     * @param aggregateKey 聚合键
     * @param aggregateSeconds 聚合时间窗口（秒）
     */
    public void sendWithAggregate(Long channelId, String title, String content,
                                   String aggregateKey, int aggregateSeconds) {
        String cacheKey = AGGREGATE_CACHE_PREFIX + aggregateKey;

        // 使用Redis进行聚合
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> aggregateList = redisCache.getCacheObject(cacheKey);

        if (aggregateList == null) {
            aggregateList = new ArrayList<>();
        }

        // 添加当前消息到聚合列表
        Map<String, Object> message = new HashMap<>();
        message.put("title", title);
        message.put("content", content);
        message.put("time", System.currentTimeMillis());
        aggregateList.add(message);

        // 更新缓存
        redisCache.setCacheObject(cacheKey, aggregateList, aggregateSeconds, java.util.concurrent.TimeUnit.SECONDS);

        // 延迟发送（这里使用异步任务，实际项目中建议使用定时任务）
        CompletableFuture.runAsync(() -> {
            try {
                Thread.sleep(aggregateSeconds * 1000L);

                // 从缓存获取聚合后的消息列表
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> finalList = redisCache.getCacheObject(cacheKey);
                if (finalList != null && !finalList.isEmpty()) {
                    // 构建聚合消息
                    String aggregatedContent = buildAggregatedContent(finalList);

                    // 发送聚合消息
                    sendNotification(channelId, title + "（聚合）", aggregatedContent);

                    // 清除缓存
                    redisCache.deleteObject(cacheKey);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });
    }

    /**
     * 构建聚合消息内容
     */
    private String buildAggregatedContent(List<Map<String, Object>> messages) {
        StringBuilder sb = new StringBuilder();
        sb.append("【聚合消息】共").append(messages.size()).append("条\n\n");

        for (int i = 0; i < messages.size(); i++) {
            Map<String, Object> msg = messages.get(i);
            sb.append(i + 1).append(". ")
              .append(msg.get("content"))
              .append("\n");
        }

        return sb.toString();
    }
}
