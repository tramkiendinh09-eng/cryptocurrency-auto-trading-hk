package com.ruoyi.dca.service.impl;

import com.ruoyi.dca.domain.NotifyChannel;
import com.ruoyi.dca.domain.dto.TradeResultDTO;
import com.ruoyi.dca.service.INotifyChannelService;
import com.ruoyi.dca.service.INotifyRecordService;
import com.ruoyi.dca.service.ITaskQueueService;
import com.ruoyi.dca.service.ITradeCallbackService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.Date;
import java.util.List;
import java.util.Map;

@Service
public class TradeCallbackServiceImpl implements ITradeCallbackService {

    private static final Logger log = LoggerFactory.getLogger(TradeCallbackServiceImpl.class);
    private static final String TRADE_NOTIFICATION_TITLE = "交易执行完成";

    @Autowired
    private INotifyChannelService notifyChannelService;

    @Autowired
    private INotifyRecordService notifyRecordService;

    @Autowired
    private ITaskQueueService taskQueueService;

    @Override
    @Transactional
    public void processTradeResult(TradeResultDTO result) {
        try {
            log.info(
                "Processing trade callback: taskId={}, symbol={}, success={}",
                result.getTaskId(),
                result.getSymbol(),
                result.getSuccess()
            );

            TradeResultDTO extractedResult = extractNestedData(result);
            log.info(
                "Extracted callback payload: strategyId={}, userId={}, symbol={}, amount={}, price={}, quantity={}, traceId={}",
                extractedResult.getStrategyId(),
                extractedResult.getUserId(),
                extractedResult.getSymbol(),
                extractedResult.getUsdtAmount(),
                extractedResult.getPrice(),
                extractedResult.getCoinAmount(),
                extractedResult.getTraceId()
            );

            log.info(
                "Legacy DCA persistence retired for runtime callback: taskId={}, strategyId={}, traceId={}",
                extractedResult.getTaskId(),
                extractedResult.getStrategyId(),
                extractedResult.getTraceId()
            );

            if (Boolean.TRUE.equals(extractedResult.getSuccess())) {
                triggerNotification(extractedResult);
            }

            cleanupTaskStatus(extractedResult.getTaskId(), "trade");
            log.info("Trade callback processed successfully: taskId={}", extractedResult.getTaskId());
        } catch (Exception e) {
            log.error("Failed to process trade callback: taskId={}", result.getTaskId(), e);
            throw e;
        }
    }

    @Override
    public void processAlertResult(Long userId, String alertTitle, String alertContent, Map<String, Object> alertData) {
        try {
            log.info("Processing alert callback: userId={}, title={}", userId, alertTitle);
            if (userId == null) {
                log.warn("UserId is null, cannot send alert notification");
                return;
            }

            List<NotifyChannel> channels = notifyChannelService.selectEnabledByUserId(userId);
            if (channels == null || channels.isEmpty()) {
                log.info("No notification channels enabled for userId={}", userId);
                return;
            }

            String traceId = extractTraceId(alertData);
            for (NotifyChannel channel : channels) {
                try {
                    notifyRecordService.sendNotification(channel.getId(), alertTitle, alertContent, traceId);
                    log.info("Alert notification sent successfully: channelId={}, userId={}", channel.getId(), userId);
                } catch (Exception e) {
                    log.error("Failed to send alert notification via channel {}: {}", channel.getId(), e.getMessage(), e);
                }
            }

            cleanupTaskStatus(alertData == null ? null : (String) alertData.get("taskId"), "alert");
            log.info("Alert callback processed successfully: userId={}", userId);
        } catch (Exception e) {
            log.error("Failed to process alert callback: userId={}", userId, e);
        }
    }

    private void cleanupTaskStatus(String taskId, String taskKind) {
        if (taskId == null || taskId.isBlank()) {
            return;
        }
        try {
            taskQueueService.cleanupTaskStatus(taskId);
            log.info("{} task status cleaned up: taskId={}", taskKind, taskId);
        } catch (Exception e) {
            log.warn("Failed to cleanup {} task status: taskId={}", taskKind, taskId, e);
        }
    }

    private TradeResultDTO extractNestedData(TradeResultDTO original) {
        TradeResultDTO result = new TradeResultDTO();
        result.setTaskId(original.getTaskId());
        result.setTimestamp(original.getTimestamp());
        result.setTaskType(original.getTaskType());
        result.setStrategyId(original.getStrategyId());
        result.setTraceId(original.getTraceId());
        result.setUserId(original.getUserId());
        result.setSymbol(original.getSymbol());
        result.setPhase(original.getPhase());
        result.setTradeType(original.getTradeType());

        if (original.getResult() instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> nestedResult = (Map<String, Object>) original.getResult();

            log.debug("Extracting data from nested result: {}", nestedResult);

            if (result.getStrategyId() == null && nestedResult.containsKey("strategy_id")) {
                result.setStrategyId(asLong(nestedResult.get("strategy_id"), "strategy_id"));
            }
            if (result.getUserId() == null && nestedResult.containsKey("user_id")) {
                result.setUserId(asLong(nestedResult.get("user_id"), "user_id"));
            }
            if ((result.getTraceId() == null || result.getTraceId().isBlank()) && nestedResult.containsKey("trace_id")) {
                Object traceId = nestedResult.get("trace_id");
                if (traceId != null) {
                    result.setTraceId(traceId.toString());
                }
            }
            if ((result.getTraceId() == null || result.getTraceId().isBlank()) && nestedResult.containsKey("traceId")) {
                Object traceId = nestedResult.get("traceId");
                if (traceId != null) {
                    result.setTraceId(traceId.toString());
                }
            }
            if (result.getSymbol() == null && nestedResult.containsKey("symbol")) {
                result.setSymbol((String) nestedResult.get("symbol"));
            }
            if (nestedResult.containsKey("usdt_amount")) {
                result.setUsdtAmount(extractBigDecimal(nestedResult.get("usdt_amount")));
            }
            if (nestedResult.containsKey("coin_amount")) {
                result.setCoinAmount(extractBigDecimal(nestedResult.get("coin_amount")));
            }
            if (nestedResult.containsKey("price")) {
                result.setPrice(extractBigDecimal(nestedResult.get("price")));
            }
            if (result.getTaskType() == null && nestedResult.containsKey("task_type")) {
                result.setTaskType((String) nestedResult.get("task_type"));
            }
            if (nestedResult.containsKey("success")) {
                result.setSuccess(Boolean.TRUE.equals(nestedResult.get("success")));
            }
            if (nestedResult.containsKey("error")) {
                result.setError((String) nestedResult.get("error"));
            }
            if (nestedResult.containsKey("skipped")) {
                result.setSkipped(Boolean.TRUE.equals(nestedResult.get("skipped")));
            }
            if (nestedResult.containsKey("skip_reason")) {
                result.setSkipReason((String) nestedResult.get("skip_reason"));
            }
            if (nestedResult.containsKey("is_simulation")) {
                result.setIsSimulation(Boolean.TRUE.equals(nestedResult.get("is_simulation")));
            }
            if (nestedResult.containsKey("order_id")) {
                Object orderId = nestedResult.get("order_id");
                result.setOrderId(orderId != null ? orderId.toString() : null);
            }
            if (nestedResult.containsKey("tx_hash")) {
                result.setTxHash((String) nestedResult.get("tx_hash"));
            }
            if (nestedResult.containsKey("trade_type")) {
                result.setTradeType((String) nestedResult.get("trade_type"));
            }
            if (nestedResult.containsKey("price_change_pct")) {
                result.setPriceChangePct(extractBigDecimal(nestedResult.get("price_change_pct")));
            }
            if (nestedResult.containsKey("gas_price")) {
                result.setGasPrice(extractBigDecimal(nestedResult.get("gas_price")));
            }
            if (nestedResult.containsKey("profit_rate")) {
                result.setProfitRate(extractBigDecimal(nestedResult.get("profit_rate")));
            }

            log.debug(
                "Extracted nested result: strategyId={}, userId={}, symbol={}, amount={}, price={}, success={}",
                result.getStrategyId(),
                result.getUserId(),
                result.getSymbol(),
                result.getUsdtAmount(),
                result.getPrice(),
                result.getSuccess()
            );
        }

        if (result.getUsdtAmount() == null) {
            result.setUsdtAmount(original.getUsdtAmount());
        }
        if (result.getCoinAmount() == null) {
            result.setCoinAmount(original.getCoinAmount());
        }
        if (result.getPrice() == null) {
            result.setPrice(original.getPrice());
        }
        if (result.getSuccess() == null) {
            result.setSuccess(original.getSuccess());
        }
        if (result.getError() == null) {
            result.setError(original.getError());
        }
        if (result.getSkipped() == null) {
            result.setSkipped(original.getSkipped());
        }
        if (result.getSkipReason() == null) {
            result.setSkipReason(original.getSkipReason());
        }
        if (result.getIsSimulation() == null) {
            result.setIsSimulation(original.getIsSimulation());
        }
        if (result.getOrderId() == null) {
            result.setOrderId(original.getOrderId());
        }
        if (result.getTxHash() == null) {
            result.setTxHash(original.getTxHash());
        }
        if (result.getStrategyId() == null) {
            result.setStrategyId(original.getStrategyId());
        }
        if (result.getTraceId() == null) {
            result.setTraceId(original.getTraceId());
        }
        if (result.getUserId() == null) {
            result.setUserId(original.getUserId());
        }

        return result;
    }

    private Long asLong(Object value, String fieldName) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value instanceof String stringValue) {
            try {
                return Long.parseLong(stringValue);
            } catch (NumberFormatException e) {
                log.warn("Failed to parse {}: {}", fieldName, value);
                return null;
            }
        }
        log.warn("Unsupported {} type: {}", fieldName, value.getClass());
        return null;
    }

    private BigDecimal extractBigDecimal(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof BigDecimal bigDecimal) {
            return bigDecimal;
        }
        if (value instanceof Number number) {
            return new BigDecimal(number.toString());
        }
        if (value instanceof String stringValue) {
            try {
                return new BigDecimal(stringValue);
            } catch (NumberFormatException e) {
                log.warn("Failed to parse BigDecimal from string: {}", value);
                return null;
            }
        }
        log.warn("Unknown type for BigDecimal extraction: {}", value.getClass());
        return null;
    }

    @Override
    public void triggerNotification(TradeResultDTO result) {
        try {
            List<NotifyChannel> channels = notifyChannelService.selectEnabledByUserId(result.getUserId());
            if (channels == null || channels.isEmpty()) {
                log.info("No notification channels enabled for userId={}", result.getUserId());
                return;
            }

            String content = buildNotificationContent(result);
            for (NotifyChannel channel : channels) {
                try {
                    notifyRecordService.sendNotification(
                        channel.getId(),
                        TRADE_NOTIFICATION_TITLE,
                        content,
                        result.getTraceId()
                    );
                    log.info("Notification sent: channelId={}, taskId={}", channel.getId(), result.getTaskId());
                } catch (Exception e) {
                    log.error("Failed to send notification via channel {}: {}", channel.getId(), e.getMessage(), e);
                }
            }
        } catch (Exception e) {
            log.error("Failed to trigger notification for taskId={}", result.getTaskId(), e);
        }
    }

    private String buildNotificationContent(TradeResultDTO result) {
        StringBuilder content = new StringBuilder();
        content.append("【交易执行回调】\n");
        content.append("------------------------\n");
        content.append(String.format("交易对: %s%n", result.getSymbol()));
        content.append(String.format("名义金额: %s USDT%n", result.getUsdtAmount()));
        content.append(String.format("成交数量: %s%n", result.getCoinAmount()));
        content.append(String.format("成交价格: %s%n", result.getPrice()));
        content.append(String.format("交易类型: %s%n", result.getTradeType()));
        content.append(String.format("状态: %s%n", Boolean.TRUE.equals(result.getSuccess()) ? "成功" : "失败"));
        if (result.getError() != null && !result.getError().isBlank()) {
            content.append(String.format("失败原因: %s%n", result.getError()));
        }
        if (result.getTimestamp() != null) {
            content.append(String.format("执行时间: %s%n", new Date(result.getTimestamp())));
        }
        if (result.getTraceId() != null && !result.getTraceId().isBlank()) {
            content.append(String.format("TraceId: %s%n", result.getTraceId()));
        }
        content.append("------------------------");
        return content.toString();
    }

    private String extractTraceId(Map<String, Object> payload) {
        if (payload == null || payload.isEmpty()) {
            return null;
        }
        Object camelCase = payload.get("traceId");
        if (camelCase != null && !camelCase.toString().isBlank()) {
            return camelCase.toString();
        }
        Object snakeCase = payload.get("trace_id");
        if (snakeCase != null && !snakeCase.toString().isBlank()) {
            return snakeCase.toString();
        }
        return null;
    }
}
