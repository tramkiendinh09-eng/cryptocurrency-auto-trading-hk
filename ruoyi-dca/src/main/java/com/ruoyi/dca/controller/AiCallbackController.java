package com.ruoyi.dca.controller;

import java.util.Date;
import java.util.List;
import java.util.Map;
import com.ruoyi.common.annotation.Anonymous;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.dca.domain.AuditAiCallLog;
import com.ruoyi.dca.service.IAuditAiCallLogService;
import com.ruoyi.dca.service.IAiModelConfigService;

/**
 * AI回调接口 - 供Python Worker调用
 *
 * @author ruoyi
 */
@RestController
@Anonymous
@RequestMapping("/dca/callback/ai")
public class AiCallbackController
{
    @Autowired
    private IAuditAiCallLogService auditAiCallLogService;

    @Autowired
    private IAiModelConfigService aiModelConfigService;

    /**
     * 记录AI调用日志（内部接口，供Python Worker调用）
     */
    @PostMapping("/logCall")
    public AjaxResult logAiCall(@RequestBody Map<String, Object> params)
    {
        try
        {
            // 创建AI调用日志对象
            AuditAiCallLog log = new AuditAiCallLog();

            // 基本信息
            log.setModel(resolveText(params, "model", "modelCode"));
            log.setPrompt((String) params.get("prompt"));
            log.setResponse((String) params.get("response"));

            // Token使用情况
            Object promptTokens = params.get("promptTokens");
            if (promptTokens != null)
            {
                log.setPromptTokens(((Number) promptTokens).intValue());
            }

            Object completionTokens = params.get("completionTokens");
            if (completionTokens != null)
            {
                log.setCompletionTokens(((Number) completionTokens).intValue());
            }

            Object totalTokens = params.get("totalTokens");
            if (totalTokens != null)
            {
                log.setTotalTokens(((Number) totalTokens).intValue());
            }

            // 调用状态
            Object status = params.get("status");
            if (status != null)
            {
                log.setStatus(((Number) status).intValue());
            }
            else
            {
                log.setStatus(1); // 默认成功
            }

            // 错误信息
            log.setErrorMsg((String) params.get("errorMsg"));

            // 响应时间
            Object responseTime = params.get("responseTime");
            if (responseTime != null)
            {
                log.setResponseTime(((Number) responseTime).longValue());
            }

            // 调用场景
            log.setScene((String) params.get("scene"));

            // 用户ID
            Object userId = params.get("userId");
            if (userId != null)
            {
                log.setUserId(((Number) userId).longValue());
            }

            // 提示词模板ID
            Object templateId = params.get("templateId");
            if (templateId != null)
            {
                log.setTemplateId(((Number) templateId).longValue());
            }

            // 调用时间
            log.setCallTime(new Date());

            // 保存日志
            int rows = auditAiCallLogService.insertAuditAiCallLog(log);

            // 如果调用成功，更新模型使用次数
            if (log.getStatus() == 1)
            {
                String modelCode = (String) params.get("modelCode");
                if (modelCode != null)
                {
                    aiModelConfigService.incrementUsageByModelCode(modelCode);
                }
            }

            return rows > 0 ? AjaxResult.success("日志记录成功") : AjaxResult.error("日志记录失败");
        }
        catch (Exception e)
        {
            return AjaxResult.error("记录日志异常: " + e.getMessage());
        }
    }

    /**
     * 获取最近的AI调用历史记录（供Python Worker调用，用于上下文分析）
     * 注意：此接口强制要求userId，确保多用户数据隔离
     */
    @PostMapping("/getRecentHistory")
    public AjaxResult getRecentHistory(@RequestBody Map<String, Object> params)
    {
        try
        {
            // 获取参数 - userId是必填的，确保多用户数据隔离
            Object userIdObj = params.get("userId");
            if (userIdObj == null)
            {
                return AjaxResult.error("userId参数不能为空，必须指定用户ID");
            }

            Long userId;
            try
            {
                userId = ((Number) userIdObj).longValue();
            }
            catch (Exception e)
            {
                return AjaxResult.error("userId参数格式错误");
            }

            if (userId == null || userId <= 0)
            {
                return AjaxResult.error("userId参数无效，必须为正整数");
            }

            // 获取场景参数（可选）
            Object sceneObj = params.get("scene");
            String scene = sceneObj != null ? sceneObj.toString() : "market_analysis";

            // 获取数量限制参数（可选）
            Object limitObj = params.get("limit");
            int limit = 10; // 默认返回最近10条
            if (limitObj != null)
            {
                try
                {
                    limit = ((Number) limitObj).intValue();
                    if (limit <= 0 || limit > 50)
                    {
                        limit = 10; // 限制最多50条
                    }
                }
                catch (Exception e)
                {
                    limit = 10; // 格式错误时使用默认值
                }
            }

            // 构建查询条件 - 强制按userId过滤
            AuditAiCallLog query = new AuditAiCallLog();
            query.setUserId(userId);  // 必须按用户ID过滤
            query.setScene(scene);
            query.setStatus(1); // 只查询成功的记录

            // 查询最近的记录（只查询该用户的数据）
            List<AuditAiCallLog> historyList = auditAiCallLogService.selectAuditAiCallLogList(query);

            // 限制返回数量
            if (historyList.size() > limit)
            {
                historyList = historyList.subList(0, limit);
            }

            // 转换为简化的Map格式返回
            List<Map<String, Object>> result = new java.util.ArrayList<>();
            for (AuditAiCallLog log : historyList)
            {
                Map<String, Object> item = new java.util.HashMap<>();
                item.put("id", log.getId());
                item.put("callTime", log.getCallTime());
                item.put("model", log.getModel());
                item.put("prompt", log.getPrompt());
                item.put("response", log.getResponse());
                item.put("totalTokens", log.getTotalTokens());
                item.put("responseTime", log.getResponseTime());
                result.add(item);
            }

            return AjaxResult.success(result);
        }
        catch (Exception e)
        {
            return AjaxResult.error("获取历史记录失败: " + e.getMessage());
        }
    }

    private String resolveText(Map<String, Object> params, String... keys)
    {
        if (params == null || keys == null)
        {
            return null;
        }
        for (String key : keys)
        {
            Object value = params.get(key);
            if (value == null)
            {
                continue;
            }
            String normalized = String.valueOf(value).trim();
            if (!normalized.isEmpty())
            {
                return normalized;
            }
        }
        return null;
    }
}
