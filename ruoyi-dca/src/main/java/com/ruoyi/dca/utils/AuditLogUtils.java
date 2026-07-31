package com.ruoyi.dca.utils;

import com.ruoyi.dca.service.IAuditAiCallLogService;
import com.ruoyi.dca.service.IAuditOperationLogService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

/**
 * 审计日志工具类。
 * runtime 重构后，旧 DCA trigger 审计已退役，这里不再回落到旧触发表写入。
 */
@Component
public class AuditLogUtils {

    private static final Logger log = LoggerFactory.getLogger(AuditLogUtils.class);

    private static final String LEGACY_TRIGGER_RETIRED_MESSAGE =
        "旧 DCA 触发审计已退役，请使用运行时决策审计控制台。";

    @Autowired
    private IAuditOperationLogService auditOperationLogService;

    @Autowired
    private IAuditAiCallLogService auditAiCallLogService;

    public void recordOperation(Long userId, String username, String module, String operation,
                                String description, String requestMethod, String requestUrl, String requestIp,
                                String requestParams, Integer status, String errorMsg, Long executionTime) {
        try {
            auditOperationLogService.recordOperation(
                userId,
                username,
                module,
                operation,
                description,
                requestMethod,
                requestUrl,
                requestIp,
                requestParams,
                null,
                status,
                errorMsg,
                executionTime
            );
        } catch (Exception e) {
            log.error("记录操作日志失败", e);
        }
    }

    public void recordSuccess(Long userId, String username, String module, String operation,
                              String description, String requestMethod, String requestUrl,
                              String requestIp, Long executionTime) {
        recordOperation(userId, username, module, operation, description, requestMethod,
            requestUrl, requestIp, null, 1, null, executionTime);
    }

    public void recordFailure(Long userId, String username, String module, String operation,
                              String description, String requestMethod, String requestUrl,
                              String requestIp, String errorMsg) {
        recordOperation(userId, username, module, operation, description, requestMethod,
            requestUrl, requestIp, null, 0, errorMsg, null);
    }

    public void recordStrategyCreate(Long userId, String username, String strategyName,
                                     String requestMethod, String requestUrl, String requestIp) {
        recordSuccess(userId, username, "strategy", "create",
            "创建策略: " + strategyName, requestMethod, requestUrl, requestIp, null);
    }

    public void recordStrategyUpdate(Long userId, String username, String strategyName,
                                     String requestMethod, String requestUrl, String requestIp) {
        recordSuccess(userId, username, "strategy", "update",
            "更新策略: " + strategyName, requestMethod, requestUrl, requestIp, null);
    }

    public void recordStrategyDelete(Long userId, String username, String strategyName,
                                     String requestMethod, String requestUrl, String requestIp) {
        recordSuccess(userId, username, "strategy", "delete",
            "删除策略: " + strategyName, requestMethod, requestUrl, requestIp, null);
    }

    public void recordStrategyToggle(Long userId, String username, String strategyName, Integer status,
                                     String requestMethod, String requestUrl, String requestIp) {
        String description = status == 1 ? "启用策略: " + strategyName : "暂停策略: " + strategyName;
        recordSuccess(userId, username, "strategy", "toggle",
            description, requestMethod, requestUrl, requestIp, null);
    }

    public void recordCardKeyOperation(Long userId, String username, String operation, String cardKey,
                                       String requestMethod, String requestUrl, String requestIp) {
        recordSuccess(userId, username, "cardkey", operation,
            operation + "卡密: " + cardKey, requestMethod, requestUrl, requestIp, null);
    }

    public void recordConfigUpdate(Long userId, String username, String configKey,
                                   String requestMethod, String requestUrl, String requestIp) {
        recordSuccess(userId, username, "config", "update",
            "修改配置: " + configKey, requestMethod, requestUrl, requestIp, null);
    }

    public void recordTrigger(Long strategyId, Long userId, String triggerType,
                              BigDecimal beforePrice, BigDecimal afterPrice,
                              BigDecimal priceChange, BigDecimal threshold,
                              Integer phase, String result, String resultDesc, String strategySnapshot) {
        log.warn("{} strategyId={}, userId={}, triggerType={}, result={}",
            LEGACY_TRIGGER_RETIRED_MESSAGE,
            strategyId,
            userId,
            triggerType,
            result);
    }

    public void recordTriggerSuccess(Long strategyId, Long userId, String triggerType,
                                     BigDecimal beforePrice, BigDecimal afterPrice,
                                     BigDecimal priceChange, BigDecimal threshold, Integer phase) {
        recordTrigger(strategyId, userId, triggerType, beforePrice, afterPrice,
            priceChange, threshold, phase, "triggered", "触发成功", null);
    }

    public void recordTriggerSkipped(Long strategyId, Long userId, String triggerType,
                                     BigDecimal beforePrice, BigDecimal afterPrice,
                                     BigDecimal priceChange, BigDecimal threshold, Integer phase, String reason) {
        recordTrigger(strategyId, userId, triggerType, beforePrice, afterPrice,
            priceChange, threshold, phase, "skipped", "跳过: " + reason, null);
    }

    public void recordAiCall(Long userId, String scene, String model, Long templateId,
                             String prompt, String response, Integer promptTokens,
                             Integer completionTokens, Integer totalTokens,
                             Integer status, String errorMsg, Long responseTime) {
        try {
            auditAiCallLogService.recordAiCall(
                userId,
                scene,
                model,
                templateId,
                prompt,
                response,
                promptTokens,
                completionTokens,
                totalTokens,
                status,
                errorMsg,
                responseTime
            );
        } catch (Exception e) {
            log.error("记录 AI 调用日志失败", e);
        }
    }

    public void recordAiCallSuccess(Long userId, String scene, String model, Long templateId,
                                    String prompt, String response, Integer promptTokens,
                                    Integer completionTokens, Integer totalTokens, Long responseTime) {
        recordAiCall(userId, scene, model, templateId, prompt, response,
            promptTokens, completionTokens, totalTokens, 1, null, responseTime);
    }

    public void recordAiCallFailure(Long userId, String scene, String model, Long templateId,
                                    String prompt, String errorMsg) {
        recordAiCall(userId, scene, model, templateId, prompt, null,
            null, null, null, 0, errorMsg, null);
    }

    public void recordMarketAnalysisCall(Long userId, String model, Long templateId,
                                         String prompt, String response, Integer promptTokens,
                                         Integer completionTokens, Integer totalTokens, Long responseTime) {
        recordAiCallSuccess(userId, "market_analysis", model, templateId, prompt, response,
            promptTokens, completionTokens, totalTokens, responseTime);
    }

    public void recordRiskAlertCall(Long userId, String model, Long templateId,
                                    String prompt, String response, Integer promptTokens,
                                    Integer completionTokens, Integer totalTokens, Long responseTime) {
        recordAiCallSuccess(userId, "risk_alert", model, templateId, prompt, response,
            promptTokens, completionTokens, totalTokens, responseTime);
    }

    public void recordTradeSummaryCall(Long userId, String model, Long templateId,
                                       String prompt, String response, Integer promptTokens,
                                       Integer completionTokens, Integer totalTokens, Long responseTime) {
        recordAiCallSuccess(userId, "trade_summary", model, templateId, prompt, response,
            promptTokens, completionTokens, totalTokens, responseTime);
    }
}
