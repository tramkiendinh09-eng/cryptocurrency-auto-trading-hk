package com.ruoyi.dca.service.impl;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.core.redis.RedisCache;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.utils.DateUtils;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.dca.domain.CardKey;
import com.ruoyi.dca.domain.dto.CardActivateDTO;
import com.ruoyi.dca.domain.dto.CardKeyBatchDTO;
import com.ruoyi.dca.domain.vo.CardUsageVO;
import com.ruoyi.dca.mapper.CardKeyMapper;
import com.ruoyi.dca.service.ICardKeyService;

/**
 * 卡密Service业务层处理
 *
 * @author ruoyi
 * @date 2026-04-02
 */
@Service
public class CardKeyServiceImpl implements ICardKeyService {
    private static final Logger log = LoggerFactory.getLogger(CardKeyServiceImpl.class);

    /** 卡密缓存前缀 */
    private static final String CARD_KEY_CACHE = "card_key:";
    /** 卡密验证缓存前缀 */
    private static final String CARD_VALIDATE_CACHE = "card_validate:";

    /** 卡密状态 */
    private static final String STATUS_UNUSED = "unused";
    private static final String STATUS_ACTIVATED = "activated";
    private static final String STATUS_EXPIRED = "expired";
    private static final String STATUS_DISABLED = "disabled";

    /** 卡密类型 */
    private static final String TYPE_TIME = "time";        // 时间版
    private static final String TYPE_PERMANENT = "permanent"; // 永久版
    private static final String TYPE_COUNT = "count";      // 次数版
    private static final String TYPE_TRIAL = "trial";      // 试用版

    /** 卡密等级 */
    private static final String LEVEL_BASIC = "basic";     // 基础版
    private static final String LEVEL_PRO = "pro";         // 专业版
    private static final String LEVEL_PREMIUM = "premium"; // 旗舰版

    @Autowired
    private CardKeyMapper cardKeyMapper;

    @Autowired
    private RedisCache redisCache;

    @Autowired
    private ObjectMapper objectMapper;

    /**
     * 查询卡密
     *
     * @param id 卡密主键
     * @return 卡密
     */
    @Override
    public CardKey selectCardKeyById(Long id) {
        return cardKeyMapper.selectCardKeyById(id);
    }

    /**
     * 根据卡密查询
     *
     * @param cardKey 卡密
     * @return 卡密
     */
    @Override
    public CardKey selectByCardKey(String cardKey) {
        return cardKeyMapper.selectByCardKey(cardKey);
    }

    /**
     * 查询卡密列表
     *
     * @param cardKey 卡密
     * @return 卡密
     */
    @Override
    public List<CardKey> selectCardKeyList(CardKey cardKey) {
        return cardKeyMapper.selectCardKeyList(cardKey);
    }

    /**
     * 根据批次号查询卡密列表
     *
     * @param batchNo 批次号
     * @return 卡密集合
     */
    @Override
    public List<CardKey> selectByBatchNo(String batchNo) {
        return cardKeyMapper.selectByBatchNo(batchNo);
    }

    /**
     * 根据用户ID查询激活的卡密
     *
     * @param userId 用户ID
     * @return 卡密
     */
    @Override
    public CardKey selectByUserId(Long userId) {
        String cacheKey = CARD_KEY_CACHE + "user:" + userId;
        CardKey cardKey = redisCache.getCacheObject(cacheKey);
        if (cardKey != null) {
            return cardKey;
        }

        cardKey = cardKeyMapper.selectByUserId(userId);
        if (cardKey != null) {
            redisCache.setCacheObject(cacheKey, cardKey, 5, TimeUnit.MINUTES);
        }
        return cardKey;
    }

    /**
     * 根据机器码查询激活的卡密列表
     *
     * @param machineCode 机器码
     * @return 卡密列表
     */
    @Override
    public List<CardKey> selectByMachineCode(String machineCode) {
        return cardKeyMapper.selectByMachineCode(machineCode);
    }

    /**
     * 批量生成卡密
     *
     * @param batchDto 批量生成DTO
     * @return 生成的卡密列表
     */
    @Override
    @Transactional
    public List<CardKey> generateCards(CardKeyBatchDTO batchDto) {
        // 验证参数
        validateBatchDto(batchDto);

        // 生成批次号
        String batchNo = generateBatchNo(batchDto);

        // 生成卡密列表
        List<CardKey> cardKeyList = new ArrayList<>();
        Date now = new Date();
        Date expireTime = calculateExpireTime(batchDto, now);

        try {
            // 转换功能开关为JSON字符串
            String featureFlagsJson = null;
            if (batchDto.getFeatureFlags() != null && !batchDto.getFeatureFlags().isEmpty()) {
                featureFlagsJson = objectMapper.writeValueAsString(batchDto.getFeatureFlags());
            }

            for (int i = 0; i < batchDto.getCount(); i++) {
                CardKey cardKey = new CardKey();
                cardKey.setCardKey(generateCardKey(batchDto.getCardLevel()));
                cardKey.setCardType(batchDto.getCardType());
                cardKey.setCardLevel(batchDto.getCardLevel());
                cardKey.setDays(batchDto.getDays());
                cardKey.setCounts(batchDto.getCounts());
                cardKey.setFeatureFlags(featureFlagsJson);
                cardKey.setStatus(STATUS_UNUSED);
                cardKey.setExpireTime(expireTime);
                cardKey.setBatchNo(batchNo);
                cardKey.setRemark(batchDto.getRemark());
                cardKey.setCreateTime(now);

                cardKeyList.add(cardKey);
            }

            // 批量插入数据库
            cardKeyMapper.batchInsertCardKey(cardKeyList);

            log.info("批量生成卡密成功: batchNo={}, count={}, type={}, level={}",
                    batchNo, batchDto.getCount(), batchDto.getCardType(), batchDto.getCardLevel());

            return cardKeyList;
        } catch (JsonProcessingException e) {
            log.error("序列化功能开关失败", e);
            throw new ServiceException("功能开关序列化失败");
        }
    }

    /**
     * 激活卡密
     *
     * @param cardKey 卡密
     * @param userId 用户ID
     * @param machineCode 机器码
     * @return 结果
     */
    @Override
    @Transactional
    public CardKey activateCard(String cardKey, Long userId, String machineCode) {
        // 查询卡密
        CardKey card = cardKeyMapper.selectByCardKey(cardKey);
        if (card == null) {
            throw new ServiceException("卡密不存在");
        }

        // 验证卡密状态
        if (STATUS_DISABLED.equals(card.getStatus())) {
            throw new ServiceException("卡密已被禁用");
        }
        if (STATUS_ACTIVATED.equals(card.getStatus())) {
            throw new ServiceException("卡密已被激活");
        }
        if (STATUS_EXPIRED.equals(card.getStatus())) {
            throw new ServiceException("卡密已过期");
        }
        if (!STATUS_UNUSED.equals(card.getStatus())) {
            throw new ServiceException("卡密状态异常");
        }

        // 设置激活信息
        card.setBindUserId(userId);
        card.setBindMachine(machineCode);
        card.setActiveTime(new Date());

        // 激活卡密
        int rows = cardKeyMapper.activateCard(card);
        if (rows == 0) {
            throw new ServiceException("激活卡密失败");
        }

        // 清除缓存
        clearUserCardCache(userId);

        log.info("激活卡密成功: cardKey={}, userId={}, machineCode={}", cardKey, userId, machineCode);

        return card;
    }

    /**
     * 激活卡密（使用DTO）
     *
     * @param dto 激活DTO
     * @return 结果
     */
    @Override
    public CardKey activateCard(CardActivateDTO dto) {
        return activateCard(dto.getCardKey(), dto.getUserId(), dto.getMachineCode());
    }

    /**
     * 验证卡密有效性
     *
     * @param cardKey 卡密
     * @return 验证结果信息
     */
    @Override
    public Map<String, Object> validateCard(String cardKey) {
        Map<String, Object> result = new HashMap<>();

        try {
            // 从缓存获取验证结果
            String cacheKey = CARD_VALIDATE_CACHE + cardKey;
            Map<String, Object> cachedResult = redisCache.getCacheObject(cacheKey);
            if (cachedResult != null) {
                return cachedResult;
            }

            // 查询卡密
            CardKey card = cardKeyMapper.selectByCardKey(cardKey);
            if (card == null) {
                result.put("valid", false);
                result.put("message", "卡密不存在");
                return result;
            }

            // 验证状态
            if (STATUS_DISABLED.equals(card.getStatus())) {
                result.put("valid", false);
                result.put("message", "卡密已被禁用");
                return result;
            }

            if (STATUS_UNUSED.equals(card.getStatus())) {
                result.put("valid", true);
                result.put("message", "卡密未激活");
                result.put("card", card);
                return result;
            }

            if (STATUS_EXPIRED.equals(card.getStatus())) {
                result.put("valid", false);
                result.put("message", "卡密已过期");
                return result;
            }

            if (!STATUS_ACTIVATED.equals(card.getStatus())) {
                result.put("valid", false);
                result.put("message", "卡密状态异常");
                return result;
            }

            // 检查是否过期
            if (card.getExpireTime() != null && card.getExpireTime().before(new Date())) {
                // 自动更新为过期状态
                cardKeyMapper.updateStatus(card.getId(), STATUS_EXPIRED);
                result.put("valid", false);
                result.put("message", "卡密已过期");
                return result;
            }

            // 验证通过
            result.put("valid", true);
            result.put("message", "卡密有效");
            result.put("card", card);

            // 缓存验证结果（1分钟）
            redisCache.setCacheObject(cacheKey, result, 1, TimeUnit.MINUTES);

            return result;
        } catch (Exception e) {
            log.error("验证卡密失败: cardKey={}", cardKey, e);
            result.put("valid", false);
            result.put("message", "验证卡密失败");
            return result;
        }
    }

    /**
     * 检查用户卡密是否过期
     *
     * @param userId 用户ID
     * @return 是否过期
     */
    @Override
    public boolean checkExpire(Long userId) {
        CardKey card = cardKeyMapper.selectByUserId(userId);
        if (card == null) {
            return true;
        }

        if (!STATUS_ACTIVATED.equals(card.getStatus())) {
            return true;
        }

        if (card.getExpireTime() == null) {
            return false; // 永久版
        }

        boolean expired = card.getExpireTime().before(new Date());
        if (expired) {
            // 更新为过期状态
            cardKeyMapper.updateStatus(card.getId(), STATUS_EXPIRED);
            clearUserCardCache(userId);
        }

        return expired;
    }

    /**
     * 获取卡密使用统计
     *
     * @param cardId 卡密ID
     * @return 使用统计
     */
    @Override
    public CardUsageVO getCardUsage(Long cardId) {
        CardKey card = cardKeyMapper.selectCardKeyById(cardId);
        if (card == null) {
            throw new ServiceException("卡密不存在");
        }

        CardUsageVO vo = new CardUsageVO();
        vo.setCardId(card.getId());
        vo.setCardKey(card.getCardKey());
        vo.setCardType(card.getCardType());
        vo.setCardLevel(card.getCardLevel());
        vo.setStatus(card.getStatus());
        vo.setBindUserId(card.getBindUserId());
        vo.setBindMachine(card.getBindMachine());
        vo.setActiveTime(card.getActiveTime());
        vo.setExpireTime(card.getExpireTime());
        vo.setFeatureFlags(card.getFeatureFlags());
        vo.setBatchNo(card.getBatchNo());

        // 计算剩余天数
        if (card.getExpireTime() != null) {
            long remainingDays = (card.getExpireTime().getTime() - System.currentTimeMillis()) / (1000 * 60 * 60 * 24);
            vo.setRemainingDays(Math.max(0, remainingDays));
        }

        // 剩余次数（如果有）
        if (card.getCounts() != null) {
            // TODO: 从使用记录表查询已使用次数
            vo.setRemainingCounts(card.getCounts());
        }

        // 总使用次数（TODO: 从使用记录表统计）
        vo.setTotalUsage(0L);

        // 最后使用时间（TODO: 从使用记录表查询）
        vo.setLastUsageTime(null);

        return vo;
    }

    /**
     * 绑定机器码
     *
     * @param cardId 卡密ID
     * @param machineCode 机器码
     * @return 结果
     */
    @Override
    @Transactional
    public int bindMachine(Long cardId, String machineCode) {
        CardKey card = cardKeyMapper.selectCardKeyById(cardId);
        if (card == null) {
            throw new ServiceException("卡密不存在");
        }

        if (!STATUS_ACTIVATED.equals(card.getStatus())) {
            throw new ServiceException("只能绑定已激活的卡密");
        }

        int rows = cardKeyMapper.bindMachine(cardId, machineCode);
        if (rows > 0 && card.getBindUserId() != null) {
            clearUserCardCache(card.getBindUserId());
        }

        return rows;
    }

    /**
     * 解绑用户
     *
     * @param userId 用户ID
     * @return 结果
     */
    @Override
    @Transactional
    public int unbindUser(Long userId) {
        int rows = cardKeyMapper.unbindUser(userId);
        if (rows > 0) {
            clearUserCardCache(userId);
        }
        return rows;
    }

    /**
     * 新增卡密
     *
     * @param cardKey 卡密
     * @return 结果
     */
    @Override
    public int insertCardKey(CardKey cardKey) {
        cardKey.setCreateTime(new Date());
        if (StringUtils.isEmpty(cardKey.getStatus())) {
            cardKey.setStatus(STATUS_UNUSED);
        }
        return cardKeyMapper.insertCardKey(cardKey);
    }

    /**
     * 修改卡密
     *
     * @param cardKey 卡密
     * @return 结果
     */
    @Override
    public int updateCardKey(CardKey cardKey) {
        return cardKeyMapper.updateCardKey(cardKey);
    }

    /**
     * 批量删除卡密
     *
     * @param ids 需要删除的卡密主键
     * @return 结果
     */
    @Override
    public int deleteCardKeyByIds(Long[] ids) {
        return cardKeyMapper.deleteCardKeyByIds(ids);
    }

    /**
     * 删除卡密信息
     *
     * @param id 卡密主键
     * @return 结果
     */
    @Override
    public int deleteCardKeyById(Long id) {
        return cardKeyMapper.deleteCardKeyById(id);
    }

    /**
     * 禁用卡密
     *
     * @param id 卡密ID
     * @return 结果
     */
    @Override
    public int disableCard(Long id) {
        CardKey card = cardKeyMapper.selectCardKeyById(id);
        if (card == null) {
            throw new ServiceException("卡密不存在");
        }

        int rows = cardKeyMapper.updateStatus(id, STATUS_DISABLED);
        if (rows > 0 && card.getBindUserId() != null) {
            clearUserCardCache(card.getBindUserId());
        }

        return rows;
    }

    /**
     * 启用卡密
     *
     * @param id 卡密ID
     * @return 结果
     */
    @Override
    public int enableCard(Long id) {
        return cardKeyMapper.updateStatus(id, STATUS_UNUSED);
    }

    /**
     * 查询即将过期的卡密
     *
     * @param days 天数
     * @return 卡密列表
     */
    @Override
    public List<CardKey> selectExpiringCards(Integer days) {
        return cardKeyMapper.selectExpiringCards(days);
    }

    /**
     * 查询已过期的卡密
     *
     * @return 卡密列表
     */
    @Override
    public List<CardKey> selectExpiredCards() {
        return cardKeyMapper.selectExpiredCards();
    }

    /**
     * 批量更新过期卡密状态
     *
     * @return 更新数量
     */
    @Override
    @Transactional
    public int batchUpdateExpiredStatus() {
        List<CardKey> expiredCards = cardKeyMapper.selectExpiredCards();
        if (expiredCards.isEmpty()) {
            return 0;
        }

        List<Long> ids = expiredCards.stream()
                .map(CardKey::getId)
                .collect(Collectors.toList());

        int rows = cardKeyMapper.batchUpdateExpiredStatus(ids);

        // 清除相关缓存
        for (CardKey card : expiredCards) {
            if (card.getBindUserId() != null) {
                clearUserCardCache(card.getBindUserId());
            }
        }

        log.info("批量更新过期卡密状态: count={}", rows);
        return rows;
    }

    /**
     * 统计各状态卡密数量
     *
     * @return 统计结果
     */
    @Override
    public Map<String, Object> getStatusStatistics() {
        List<Map<String, Object>> list = cardKeyMapper.countByStatus();
        Map<String, Object> result = new HashMap<>();
        for (Map<String, Object> item : list) {
            result.put(item.get("name").toString(), item.get("value"));
        }
        return result;
    }

    /**
     * 统计各类型卡密数量
     *
     * @return 统计结果
     */
    @Override
    public Map<String, Object> getTypeStatistics() {
        List<Map<String, Object>> list = cardKeyMapper.countByType();
        Map<String, Object> result = new HashMap<>();
        for (Map<String, Object> item : list) {
            result.put(item.get("name").toString(), item.get("value"));
        }
        return result;
    }

    /**
     * 获取卡密统计概览
     *
     * @return 统计概览
     */
    @Override
    public Map<String, Object> getCardOverview() {
        Map<String, Object> overview = new HashMap<>();
        overview.put("statusStats", getStatusStatistics());
        overview.put("typeStats", getTypeStatistics());
        overview.put("expiringCount", selectExpiringCards(7).size());
        overview.put("expiredCount", selectExpiredCards().size());
        return overview;
    }

    // ==================== 私有方法 ====================

    /**
     * 验证批量生成参数
     */
    private void validateBatchDto(CardKeyBatchDTO dto) {
        // 验证卡密类型
        if (!Arrays.asList(TYPE_TIME, TYPE_PERMANENT, TYPE_COUNT, TYPE_TRIAL).contains(dto.getCardType())) {
            throw new ServiceException("无效的卡密类型");
        }

        // 验证卡密等级
        if (!Arrays.asList(LEVEL_BASIC, LEVEL_PRO, LEVEL_PREMIUM).contains(dto.getCardLevel())) {
            throw new ServiceException("无效的卡密等级");
        }

        // 时间版必须设置天数
        if (TYPE_TIME.equals(dto.getCardType()) && dto.getDays() == null) {
            throw new ServiceException("时间版必须设置有效天数");
        }

        // 次数版必须设置次数
        if (TYPE_COUNT.equals(dto.getCardType()) && dto.getCounts() == null) {
            throw new ServiceException("次数版必须设置使用次数");
        }

        // 试用版特殊验证
        if (TYPE_TRIAL.equals(dto.getCardType())) {
            if (dto.getDays() == null || dto.getDays() > 30) {
                throw new ServiceException("试用版天数不能为空且不能超过30天");
            }
            if (!LEVEL_BASIC.equals(dto.getCardLevel())) {
                throw new ServiceException("试用版只能是基础版");
            }
        }
    }

    /**
     * 生成批次号
     */
    private String generateBatchNo(CardKeyBatchDTO dto) {
        if (StringUtils.isNotEmpty(dto.getBatchNo())) {
            return dto.getBatchNo();
        }
        return String.format("%s-%s-%s-%s",
                dto.getCardType(),
                dto.getCardLevel(),
                DateUtils.getDate(),
                UUID.randomUUID().toString().substring(0, 8).toUpperCase());
    }

    /**
     * 计算过期时间
     */
    private Date calculateExpireTime(CardKeyBatchDTO dto, Date baseTime) {
        if (TYPE_PERMANENT.equals(dto.getCardType())) {
            return null; // 永久版无过期时间
        }

        Calendar calendar = Calendar.getInstance();
        calendar.setTime(baseTime);

        if (dto.getDays() != null && dto.getDays() > 0) {
            calendar.add(Calendar.DAY_OF_MONTH, dto.getDays());
        } else if (TYPE_TRIAL.equals(dto.getCardType())) {
            calendar.add(Calendar.DAY_OF_MONTH, 7); // 默认7天试用
        }

        return calendar.getTime();
    }

    /**
     * 生成卡密
     */
    private String generateCardKey(String level) {
        // 格式: LEVEL-TIMESTAMP-RANDOM
        String timestamp = String.valueOf(System.currentTimeMillis());
        String random = UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
        return String.format("%s-%s-%s", level.toUpperCase(), timestamp, random);
    }

    /**
     * 清除用户卡密缓存
     */
    private void clearUserCardCache(Long userId) {
        if (userId != null) {
            redisCache.deleteObject(CARD_KEY_CACHE + "user:" + userId);
        }
    }
}
