package com.ruoyi.dca.mapper;

import java.util.List;
import com.ruoyi.dca.domain.NotifyChannel;
import org.apache.ibatis.annotations.Param;

/**
 * 通知渠道Mapper接口
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface NotifyChannelMapper {
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
     * 根据渠道类型查询
     *
     * @param channelType 渠道类型
     * @return 通知渠道列表
     */
    public List<NotifyChannel> selectByChannelType(String channelType);

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
     * 删除通知渠道
     *
     * @param id 通知渠道主键
     * @return 结果
     */
    public int deleteNotifyChannelById(Long id);

    /**
     * 批量删除通知渠道
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteNotifyChannelByIds(Long[] ids);

    /**
     * 更新渠道启用状态
     *
     * @param id 渠道ID
     * @param isEnabled 是否启用
     * @return 结果
     */
    public int updateEnabledStatus(@Param("id") Long id, @Param("isEnabled") Integer isEnabled);

    /**
     * 批量更新渠道启用状态
     *
     * @param ids 渠道ID列表
     * @param isEnabled 是否启用
     * @return 结果
     */
    public int batchUpdateEnabledStatus(@Param("ids") List<Long> ids, @Param("isEnabled") Integer isEnabled);

    /**
     * 检查渠道名称是否唯一
     *
     * @param channelName 渠道名称
     * @param userId 用户ID
     * @return 数量
     */
    public int checkChannelNameUnique(@Param("channelName") String channelName, @Param("userId") Long userId);

    /**
     * 统计各类型渠道数量
     *
     * @return 统计结果
     */
    public List<java.util.Map<String, Object>> countByType();
}
