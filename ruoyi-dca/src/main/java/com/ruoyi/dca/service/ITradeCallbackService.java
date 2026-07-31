package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.dto.TradeResultDTO;

import java.util.Map;

/**
 * 交易回调服务接口
 *
 * @author ruoyi
 * @date 2026-04-03
 */
public interface ITradeCallbackService {

    /**
     * 处理 Python Worker 发送的交易结果回调
     *
     * @param result 交易结果 DTO
     */
    void processTradeResult(TradeResultDTO result);

    /**
     * 处理 Python Worker 发送的提醒结果回调
     *
     * @param userId 用户 ID
     * @param alertTitle 提醒标题
     * @param alertContent 提醒内容
     * @param alertData 完整提醒负载
     */
    void processAlertResult(Long userId, String alertTitle, String alertContent, Map<String, Object> alertData);

    /**
     * 发送交易完成通知
     *
     * @param result 交易结果 DTO
     */
    void triggerNotification(TradeResultDTO result);
}
