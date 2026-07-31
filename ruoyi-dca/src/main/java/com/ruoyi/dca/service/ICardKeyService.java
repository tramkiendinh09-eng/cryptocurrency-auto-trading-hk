package com.ruoyi.dca.service;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.CardKey;
import com.ruoyi.dca.domain.dto.CardActivateDTO;
import com.ruoyi.dca.domain.dto.CardKeyBatchDTO;
import com.ruoyi.dca.domain.vo.CardUsageVO;

/**
 * 卡密Service接口
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public interface ICardKeyService {
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
     * 根据用户ID查询激活的卡密
     *
     * @param userId 用户ID
     * @return 卡密
     */
    public CardKey selectByUserId(Long userId);

    /**
     * 根据机器码查询激活的卡密列表
     *
     * @param machineCode 机器码
     * @return 卡密列表
     */
    public List<CardKey> selectByMachineCode(String machineCode);

    /**
     * 批量生成卡密
     *
     * @param batchDto 批量生成DTO
     * @return 生成的卡密列表
     */
    public List<CardKey> generateCards(CardKeyBatchDTO batchDto);

    /**
     * 激活卡密
     *
     * @param cardKey 卡密
     * @param userId 用户ID
     * @param machineCode 机器码
     * @return 结果
     */
    public CardKey activateCard(String cardKey, Long userId, String machineCode);

    /**
     * 激活卡密（使用DTO）
     *
     * @param dto 激活DTO
     * @return 结果
     */
    public CardKey activateCard(CardActivateDTO dto);

    /**
     * 验证卡密有效性
     *
     * @param cardKey 卡密
     * @return 验证结果信息
     */
    public Map<String, Object> validateCard(String cardKey);

    /**
     * 检查用户卡密是否过期
     *
     * @param userId 用户ID
     * @return 是否过期
     */
    public boolean checkExpire(Long userId);

    /**
     * 获取卡密使用统计
     *
     * @param cardId 卡密ID
     * @return 使用统计
     */
    public CardUsageVO getCardUsage(Long cardId);

    /**
     * 绑定机器码
     *
     * @param cardId 卡密ID
     * @param machineCode 机器码
     * @return 结果
     */
    public int bindMachine(Long cardId, String machineCode);

    /**
     * 解绑用户
     *
     * @param userId 用户ID
     * @return 结果
     */
    public int unbindUser(Long userId);

    /**
     * 新增卡密
     *
     * @param cardKey 卡密
     * @return 结果
     */
    public int insertCardKey(CardKey cardKey);

    /**
     * 修改卡密
     *
     * @param cardKey 卡密
     * @return 结果
     */
    public int updateCardKey(CardKey cardKey);

    /**
     * 批量删除卡密
     *
     * @param ids 需要删除的卡密主键集合
     * @return 结果
     */
    public int deleteCardKeyByIds(Long[] ids);

    /**
     * 删除卡密信息
     *
     * @param id 卡密主键
     * @return 结果
     */
    public int deleteCardKeyById(Long id);

    /**
     * 禁用卡密
     *
     * @param id 卡密ID
     * @return 结果
     */
    public int disableCard(Long id);

    /**
     * 启用卡密
     *
     * @param id 卡密ID
     * @return 结果
     */
    public int enableCard(Long id);

    /**
     * 查询即将过期的卡密
     *
     * @param days 天数
     * @return 卡密列表
     */
    public List<CardKey> selectExpiringCards(Integer days);

    /**
     * 查询已过期的卡密
     *
     * @return 卡密列表
     */
    public List<CardKey> selectExpiredCards();

    /**
     * 批量更新过期卡密状态
     *
     * @return 更新数量
     */
    public int batchUpdateExpiredStatus();

    /**
     * 统计各状态卡密数量
     *
     * @return 统计结果
     */
    public Map<String, Object> getStatusStatistics();

    /**
     * 统计各类型卡密数量
     *
     * @return 统计结果
     */
    public Map<String, Object> getTypeStatistics();

    /**
     * 获取卡密统计概览
     *
     * @return 统计概览
     */
    public Map<String, Object> getCardOverview();
}
