package com.ruoyi.dca.mapper;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.NotifyRecord;
import org.apache.ibatis.annotations.Param;

/**
 * 通知记录Mapper接口
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface NotifyRecordMapper {
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
     * 根据状态查询通知记录
     *
     * @param status 状态
     * @return 通知记录列表
     */
    public List<NotifyRecord> selectByStatus(Integer status);

    /**
     * 查询待重试的通知记录
     *
     * @param maxRetryCount 最大重试次数
     * @return 通知记录列表
     */
    public List<NotifyRecord> selectRetryableRecords(@Param("maxRetryCount") Integer maxRetryCount);

    /**
     * 新增通知记录
     *
     * @param notifyRecord 通知记录
     * @return 结果
     */
    public int insertNotifyRecord(NotifyRecord notifyRecord);

    /**
     * 批量新增通知记录
     *
     * @param list 通知记录列表
     * @return 结果
     */
    public int batchInsertNotifyRecord(@Param("list") List<NotifyRecord> list);

    /**
     * 修改通知记录
     *
     * @param notifyRecord 通知记录
     * @return 结果
     */
    public int updateNotifyRecord(NotifyRecord notifyRecord);

    /**
     * 更新发送状态
     *
     * @param id 记录ID
     * @param status 状态
     * @param errorMsg 错误信息
     * @return 结果
     */
    public int updateSendStatus(@Param("id") Long id, @Param("status") Integer status, @Param("errorMsg") String errorMsg);

    /**
     * 增加重试次数
     *
     * @param id 记录ID
     * @return 结果
     */
    public int incrementRetryCount(Long id);

    /**
     * 删除通知记录
     *
     * @param id 通知记录主键
     * @return 结果
     */
    public int deleteNotifyRecordById(Long id);

    /**
     * 批量删除通知记录
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteNotifyRecordByIds(Long[] ids);

    /**
     * 清空过期的成功记录
     *
     * @param days 保留天数
     * @return 删除数量
     */
    public int cleanExpiredRecords(@Param("days") Integer days);

    /**
     * 统计发送状态数量
     *
     * @return 统计结果
     */
    public List<Map<String, Object>> countByStatus();

    /**
     * 统计各渠道发送数量
     *
     * @return 统计结果
     */
    public List<Map<String, Object>> countByChannel();

    /**
     * 统计今日发送数量
     *
     * @return 数量
     */
    public int countTodaySends();

    /**
     * 统计成功率
     *
     * @return 成功率
     */
    public Map<String, Object> getSuccessRate();

    /**
     * 查询发送失败统计
     *
     * @param days 天数
     * @return 统计结果
     */
    public List<Map<String, Object>> getFailedStats(@Param("days") Integer days);
}
