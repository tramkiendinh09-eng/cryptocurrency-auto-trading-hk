package com.ruoyi.dca.service;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.NotifyRecord;

/**
 * 通知记录Service接口
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface INotifyRecordService {
    /**
     * 查询通知记录
     *
     * @param id 通知记录主键
     * @return 通知记录
     */
    public NotifyRecord selectNotifyRecordById(Long id);

    /**
     * 查询通知记录列表
     *
     * @param notifyRecord 通知记录
     * @return 通知记录集合
     */
    public List<NotifyRecord> selectNotifyRecordList(NotifyRecord notifyRecord);

    /**
     * 根据渠道ID查询通知记录
     *
     * @param channelId 渠道ID
     * @return 通知记录列表
     */
    public List<NotifyRecord> selectByChannelId(Long channelId);

    /**
     * 新增通知记录
     *
     * @param notifyRecord 通知记录
     * @return 结果
     */
    public int insertNotifyRecord(NotifyRecord notifyRecord);

    /**
     * 批量删除通知记录
     *
     * @param ids 需要删除的通知记录主键集合
     * @return 结果
     */
    public int deleteNotifyRecordByIds(Long[] ids);

    /**
     * 删除通知记录信息
     *
     * @param id 通知记录主键
     * @return 结果
     */
    public int deleteNotifyRecordById(Long id);

    /**
     * 发送通知
     *
     * @param channelId 渠道ID
     * @param title 标题
     * @param content 内容
     * @return 结果
     */
    public Map<String, Object> sendNotification(Long channelId, String title, String content);

    public Map<String, Object> sendNotification(Long channelId, String title, String content, String traceId);

    /**
     * 批量发送通知
     *
     * @param channelIds 渠道ID列表
     * @param title 标题
     * @param content 内容
     * @return 结果
     */
    public Map<String, Object> batchSendNotification(List<Long> channelIds, String title, String content);

    /**
     * 根据用户ID发送通知
     *
     * @param userId 用户ID
     * @param title 标题
     * @param content 内容
     * @return 结果
     */
    public Map<String, Object> sendByUserId(Long userId, String title, String content);

    /**
     * 使用模板发送通知
     *
     * @param channelId 渠道ID
     * @param templateId 模板ID
     * @param variables 模板变量
     * @return 结果
     */
    public Map<String, Object> sendByTemplate(Long channelId, Long templateId, Map<String, Object> variables);

    /**
     * 重试失败的通知
     *
     * @param id 记录ID
     * @return 结果
     */
    public Map<String, Object> retrySend(Long id);

    /**
     * 批量重试失败的通知
     *
     * @return 重试结果
     */
    public Map<String, Object> batchRetryFailed();

    /**
     * 清空过期的成功记录
     *
     * @param days 保留天数
     * @return 删除数量
     */
    public int cleanExpiredRecords(Integer days);

    /**
     * 统计发送状态数量
     *
     * @return 统计结果
     */
    public Map<String, Object> getStatusStatistics();

    /**
     * 统计各渠道发送数量
     *
     * @return 统计结果
     */
    public Map<String, Object> getChannelStatistics();

    /**
     * 获取发送统计概览
     *
     * @return 统计概览
     */
    public Map<String, Object> getSendOverview();

    /**
     * 获取发送失败统计
     *
     * @param days 天数
     * @return 统计结果
     */
    public List<Map<String, Object>> getFailedStats(Integer days);
}
