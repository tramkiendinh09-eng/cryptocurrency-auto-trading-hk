package com.ruoyi.dca.mapper;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.CardKey;
import org.apache.ibatis.annotations.Param;

/**
 * 卡密Mapper接口
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface CardKeyMapper {
    /**
     * 查询卡密
     *
     * @param id 卡密主键
     * @return 卡密
     */
    public CardKey selectCardKeyById(Long id);

    /**
     * 根据卡密查询
     *
     * @param cardKey 卡密
     * @return 卡密
     */
    public CardKey selectByCardKey(String cardKey);

    /**
     * 查询卡密列表
     *
     * @param cardKey 卡密
     * @return 卡密集合
     */
    public List<CardKey> selectCardKeyList(CardKey cardKey);

    /**
     * 根据批次号查询卡密列表
     *
     * @param batchNo 批次号
     * @return 卡密集合
     */
    public List<CardKey> selectByBatchNo(String batchNo);

    /**
     * 根据用户ID查询卡密
     *
     * @param userId 用户ID
     * @return 卡密
     */
    public CardKey selectByUserId(Long userId);

    /**
     * 根据机器码查询卡密
     *
     * @param machineCode 机器码
     * @return 卡密列表
     */
    public List<CardKey> selectByMachineCode(String machineCode);

    /**
     * 新增卡密
     *
     * @param cardKey 卡密
     * @return 结果
     */
    public int insertCardKey(CardKey cardKey);

    /**
     * 批量新增卡密
     *
     * @param cardKeyList 卡密列表
     * @return 结果
     */
    public int batchInsertCardKey(@Param("list") List<CardKey> cardKeyList);

    /**
     * 修改卡密
     *
     * @param cardKey 卡密
     * @return 结果
     */
    public int updateCardKey(CardKey cardKey);

    /**
     * 删除卡密
     *
     * @param id 卡密主键
     * @return 结果
     */
    public int deleteCardKeyById(Long id);

    /**
     * 批量删除卡密
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteCardKeyByIds(Long[] ids);

    /**
     * 更新卡密状态
     *
     * @param id 卡密ID
     * @param status 状态
     * @return 结果
     */
    public int updateStatus(@Param("id") Long id, @Param("status") String status);

    /**
     * 激活卡密
     *
     * @param cardKey 卡密
     * @return 结果
     */
    public int activateCard(CardKey cardKey);

    /**
     * 绑定机器码
     *
     * @param id 卡密ID
     * @param machineCode 机器码
     * @return 结果
     */
    public int bindMachine(@Param("id") Long id, @Param("machineCode") String machineCode);

    /**
     * 解绑用户
     *
     * @param userId 用户ID
     * @return 结果
     */
    public int unbindUser(Long userId);

    /**
     * 查询即将过期的卡密
     *
     * @param days 天数
     * @return 卡密列表
     */
    public List<CardKey> selectExpiringCards(@Param("days") Integer days);

    /**
     * 查询已过期的卡密
     *
     * @return 卡密列表
     */
    public List<CardKey> selectExpiredCards();

    /**
     * 批量更新过期卡密状态
     *
     * @param ids 卡密ID列表
     * @return 结果
     */
    public int batchUpdateExpiredStatus(@Param("ids") List<Long> ids);

    /**
     * 统计批次卡密数量
     *
     * @param batchNo 批次号
     * @return 数量
     */
    public int countByBatchNo(String batchNo);

    /**
     * 统计各状态卡密数量
     *
     * @return 统计结果
     */
    public List<Map<String, Object>> countByStatus();

    /**
     * 统计各类型卡密数量
     *
     * @return 统计结果
     */
    public List<Map<String, Object>> countByType();
}
