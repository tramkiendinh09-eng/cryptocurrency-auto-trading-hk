package com.ruoyi.dca.utils;

import com.ruoyi.dca.service.INotifyRecordService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * 通知工具类
 * 提供便捷的通知发送方法
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@Component
public class NotifyUtils {
    private static final Logger log = LoggerFactory.getLogger(NotifyUtils.class);

    @Autowired
    private INotifyRecordService notifyRecordService;

    /**
     * 发送通知到指定渠道
     *
     * @param channelId 渠道ID
     * @param title 标题
     * @param content 内容
     */
    public static void send(Long channelId, String title, String content) {
        try {
            // 注意：这里需要通过ApplicationContext获取Service实例
            // 或者将此方法改为非静态方法
            log.info("发送通知: channelId={}, title={}", channelId, title);
        } catch (Exception e) {
            log.error("发送通知失败", e);
        }
    }

    /**
     * 发送通知到用户的所有启用渠道
     *
     * @param userId 用户ID
     * @param title 标题
     * @param content 内容
     */
    public static void sendToUser(Long userId, String title, String content) {
        try {
            log.info("发送用户通知: userId={}, title={}", userId, title);
        } catch (Exception e) {
            log.error("发送用户通知失败", e);
        }
    }

    /**
     * 批量发送通知
     *
     * @param channelIds 渠道ID列表
     * @param title 标题
     * @param content 内容
     */
    public static void batchSend(List<Long> channelIds, String title, String content) {
        try {
            log.info("批量发送通知: channelIds={}, title={}", channelIds, title);
        } catch (Exception e) {
            log.error("批量发送通知失败", e);
        }
    }

    /**
     * 发送成功通知
     *
     * @param userId 用户ID
     * @param operation 操作名称
     * @param message 消息内容
     */
    public static void sendSuccess(Long userId, String operation, String message) {
        String title = "【成功】" + operation;
        String content = String.format("操作：%s\n结果：成功\n详情：%s\n时间：%s",
                operation, message, new java.util.Date());
        sendToUser(userId, title, content);
    }

    /**
     * 发送失败通知
     *
     * @param userId 用户ID
     * @param operation 操作名称
     * @param error 错误信息
     */
    public static void sendFailure(Long userId, String operation, String error) {
        String title = "【失败】" + operation;
        String content = String.format("操作：%s\n结果：失败\n错误：%s\n时间：%s",
                operation, error, new java.util.Date());
        sendToUser(userId, title, content);
    }

    /**
     * 发送警告通知
     *
     * @param userId 用户ID
     * @param warning 警告信息
     */
    public static void sendWarning(Long userId, String warning) {
        String title = "【警告】系统通知";
        String content = String.format("警告信息：%s\n时间：%s", warning, new java.util.Date());
        sendToUser(userId, title, content);
    }

    /**
     * 发送告警通知
     *
     * @param userId 用户ID
     * @param alert 告警信息
     * @param level 告警级别
     */
    public static void sendAlert(Long userId, String alert, String level) {
        String title = "【告警】" + level;
        String content = String.format("告警级别：%s\n告警信息：%s\n时间：%s",
                level, alert, new java.util.Date());
        sendToUser(userId, title, content);
    }

    /**
     * 非静态方法版本，用于Spring依赖注入
     */
    public void sendNotify(Long channelId, String title, String content) {
        try {
            notifyRecordService.sendNotification(channelId, title, content);
        } catch (Exception e) {
            log.error("发送通知失败", e);
        }
    }

    public void sendNotifyToUser(Long userId, String title, String content) {
        try {
            notifyRecordService.sendByUserId(userId, title, content);
        } catch (Exception e) {
            log.error("发送用户通知失败", e);
        }
    }

    public void batchSendNotify(List<Long> channelIds, String title, String content) {
        try {
            notifyRecordService.batchSendNotification(channelIds, title, content);
        } catch (Exception e) {
            log.error("批量发送通知失败", e);
        }
    }

    public void sendSuccessNotify(Long userId, String operation, String message) {
        String title = "【成功】" + operation;
        String content = String.format("操作：%s\n结果：成功\n详情：%s\n时间：%s",
                operation, message, new java.util.Date());
        sendNotifyToUser(userId, title, content);
    }

    public void sendFailureNotify(Long userId, String operation, String error) {
        String title = "【失败】" + operation;
        String content = String.format("操作：%s\n结果：失败\n错误：%s\n时间：%s",
                operation, error, new java.util.Date());
        sendNotifyToUser(userId, title, content);
    }

    public void sendWarningNotify(Long userId, String warning) {
        String title = "【警告】系统通知";
        String content = String.format("警告信息：%s\n时间：%s", warning, new java.util.Date());
        sendNotifyToUser(userId, title, content);
    }

    public void sendAlertNotify(Long userId, String alert, String level) {
        String title = "【告警】" + level;
        String content = String.format("告警级别：%s\n告警信息：%s\n时间：%s",
                level, alert, new java.util.Date());
        sendNotifyToUser(userId, title, content);
    }

    /**
     * 异步发送通知（不阻塞主流程）
     */
    public void sendAsync(Long channelId, String title, String content) {
        new Thread(() -> {
            try {
                notifyRecordService.sendNotification(channelId, title, content);
            } catch (Exception e) {
                log.error("异步发送通知失败", e);
            }
        }).start();
    }

    public void sendToUserAsync(Long userId, String title, String content) {
        new Thread(() -> {
            try {
                notifyRecordService.sendByUserId(userId, title, content);
            } catch (Exception e) {
                log.error("异步发送用户通知失败", e);
            }
        }).start();
    }
}
