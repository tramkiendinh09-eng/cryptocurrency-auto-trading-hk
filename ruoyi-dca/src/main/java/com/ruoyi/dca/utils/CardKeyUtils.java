package com.ruoyi.dca.utils;

import java.security.SecureRandom;
import java.util.HashMap;
import java.util.Map;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * 卡密工具类
 *
 * @author ruoyi
 * @date 2026-04-02
 */
public class CardKeyUtils {
    private static final String CHAR_LOWER = "abcdefghijklmnopqrstuvwxyz";
    private static final String CHAR_UPPER = CHAR_LOWER.toUpperCase();
    private static final String DIGIT = "0123456789";
    private static final String ALPHANUMERIC = CHAR_LOWER + CHAR_UPPER + DIGIT;

    private static final SecureRandom RANDOM = new SecureRandom();

    /**
     * 生成随机字符串
     *
     * @param length 长度
     * @return 随机字符串
     */
    public static String generateRandomString(int length) {
        StringBuilder result = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            result.append(ALPHANUMERIC.charAt(RANDOM.nextInt(ALPHANUMERIC.length())));
        }
        return result.toString();
    }

    /**
     * 生成卡密
     *
     * @param level 等级
     * @return 卡密
     */
    public static String generateCardKey(String level) {
        long timestamp = System.currentTimeMillis();
        String random = generateRandomString(8);
        return String.format("%s-%d-%s", level.toUpperCase(), timestamp, random);
    }

    /**
     * 生成批次号
     *
     * @param cardType 卡密类型
     * @param cardLevel 卡密等级
     * @param date 日期（YYYY-MM-DD）
     * @return 批次号
     */
    public static String generateBatchNo(String cardType, String cardLevel, String date) {
        String random = generateRandomString(8).toUpperCase();
        return String.format("%s-%s-%s-%s", cardType, cardLevel, date, random);
    }

    /**
     * 功能开关Map转JSON
     *
     * @param featureFlags 功能开关Map
     * @param objectMapper ObjectMapper
     * @return JSON字符串
     */
    public static String featureFlagsToJson(Map<String, Boolean> featureFlags, ObjectMapper objectMapper) {
        if (featureFlags == null || featureFlags.isEmpty()) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(featureFlags);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("功能开关序列化失败", e);
        }
    }

    /**
     * JSON转功能开关Map
     *
     * @param json JSON字符串
     * @param objectMapper ObjectMapper
     * @return 功能开关Map
     */
    @SuppressWarnings("unchecked")
    public static Map<String, Boolean> jsonToFeatureFlags(String json, ObjectMapper objectMapper) {
        if (json == null || json.isEmpty()) {
            return new HashMap<>();
        }
        try {
            return objectMapper.readValue(json, Map.class);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("功能开关反序列化失败", e);
        }
    }

    /**
     * 验证卡密格式
     *
     * @param cardKey 卡密
     * @return 是否有效
     */
    public static boolean isValidCardKeyFormat(String cardKey) {
        if (cardKey == null || cardKey.isEmpty()) {
            return false;
        }
        // 格式: LEVEL-TIMESTAMP-RANDOM
        String[] parts = cardKey.split("-");
        if (parts.length != 3) {
            return false;
        }
        try {
            Long.parseLong(parts[1]);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /**
     * 计算剩余天数
     *
     * @param expireTime 过期时间（毫秒）
     * @return 剩余天数
     */
    public static long calculateRemainingDays(long expireTime) {
        long remaining = expireTime - System.currentTimeMillis();
        return Math.max(0, remaining / (1000 * 60 * 60 * 24));
    }

    /**
     * 格式化卡密状态显示
     *
     * @param status 状态
     * @return 显示文本
     */
    public static String formatStatus(String status) {
        if (status == null) {
            return "未知";
        }
        switch (status) {
            case "unused":
                return "未使用";
            case "activated":
                return "已激活";
            case "expired":
                return "已过期";
            case "disabled":
                return "已禁用";
            default:
                return status;
        }
    }

    /**
     * 格式化卡密类型显示
     *
     * @param cardType 卡密类型
     * @return 显示文本
     */
    public static String formatCardType(String cardType) {
        if (cardType == null) {
            return "未知";
        }
        switch (cardType) {
            case "time":
                return "时间版";
            case "permanent":
                return "永久版";
            case "count":
                return "次数版";
            case "trial":
                return "试用版";
            default:
                return cardType;
        }
    }

    /**
     * 格式化卡密等级显示
     *
     * @param cardLevel 卡密等级
     * @return 显示文本
     */
    public static String formatCardLevel(String cardLevel) {
        if (cardLevel == null) {
            return "未知";
        }
        switch (cardLevel) {
            case "basic":
                return "基础版";
            case "pro":
                return "专业版";
            case "premium":
                return "旗舰版";
            default:
                return cardLevel;
        }
    }
}
