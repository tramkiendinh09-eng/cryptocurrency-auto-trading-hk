package com.ruoyi.dca.service;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.NotifyChannel;

/**
 * 通知渠道Service接口
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface INotifyChannelService {
    /**
     * 查询通知渠道
     *
     * @param id 通知渠道主键
     * @return 通知渠道
     */
    public NotifyChannel selectNotifyChannelById(Long id);

    /**
     * 查询通知渠道列表
     *
     * @param notifyChannel 通知渠道
     * @return 通知渠道集合
     */
    public List<NotifyChannel> selectNotifyChannelList(NotifyChannel notifyChannel);

    /**
     * 根据用户ID查询启用的渠道
     *
     * @param userId 用户ID
     * @return 通知渠道列表
     */
    public List<NotifyChannel> selectEnabledByUserId(Long userId);

    /**
     * 查询所有启用的渠道
     *
     * @return 通知渠道列表
     */
    public List<NotifyChannel> selectAllEnabled();

    /**
     * 新增通知渠道
     *
     * @param notifyChannel 通知渠道
     * @return 结果
     */
    public int insertNotifyChannel(NotifyChannel notifyChannel);

    /**
     * 修改通知渠道
     *
     * @param notifyChannel 通知渠道
     * @return 结果
     */
    public int updateNotifyChannel(NotifyChannel notifyChannel);

    /**
     * 批量删除通知渠道
     *
     * @param ids 需要删除的通知渠道主键集合
     * @return 结果
     */
    public int deleteNotifyChannelByIds(Long[] ids);

    /**
     * 删除通知渠道信息
     *
     * @param id 通知渠道主键
     * @return 结果
     */
    public int deleteNotifyChannelById(Long id);

    /**
     * 更新渠道启用状态
     *
     * @param id 渠道ID
     * @param isEnabled 是否启用
     * @return 结果
     */
    public int updateEnabledStatus(Long id, Integer isEnabled);

    /**
     * 批量更新渠道启用状态
     *
     * @param ids 渠道ID列表
     * @param isEnabled 是否启用
     * @return 结果
     */
    public int batchUpdateEnabledStatus(List<Long> ids, Integer isEnabled);

    /**
     * 测试发送通知
     *
     * @param id 渠道ID
     * @return 结果
     */
    public Map<String, Object> testSend(Long id);

    /**
     * 测试邮件连接（仅测试SMTP连接）
     *
     * @param id 渠道ID
     * @return 是否成功
     */
    public boolean testMailConnection(Long id);

    /**
     * 验证渠道配置
     *
     * @param notifyChannel 通知渠道
     * @return 验证结果
     */
    public Map<String, Object> validateChannel(NotifyChannel notifyChannel);

    /**
     * 检查渠道名称是否唯一
     *
     * @param notifyChannel 通知渠道
     * @return 结果
     */
    public boolean checkChannelNameUnique(NotifyChannel notifyChannel);

    /**
     * 统计各类型渠道数量
     *
     * @return 统计结果
     */
    public Map<String, Object> getTypeStatistics();
}
