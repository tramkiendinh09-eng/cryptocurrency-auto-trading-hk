package com.ruoyi.dca.service.impl;

import java.util.Date;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.dca.domain.AuditAiCallLog;
import com.ruoyi.dca.mapper.AuditAiCallLogMapper;
import com.ruoyi.dca.service.IAuditAiCallLogService;

/**
 * AI调用日志 服务层实现
 *
 * @author ruoyi
 */
@Service
public class AuditAiCallLogServiceImpl implements IAuditAiCallLogService
{
    @Autowired
    private AuditAiCallLogMapper auditAiCallLogMapper;

    /**
     * 查询AI调用日志信息
     *
     * @param id AI调用日志主键
     * @return AI调用日志信息
     */
    @Override
    public AuditAiCallLog selectAuditAiCallLogById(Long id)
    {
        return auditAiCallLogMapper.selectAuditAiCallLogById(id);
    }

    /**
     * 查询AI调用日志列表
     *
     * @param auditAiCallLog AI调用日志信息
     * @return AI调用日志集合
     */
    @Override
    public List<AuditAiCallLog> selectAuditAiCallLogList(AuditAiCallLog auditAiCallLog)
    {
        return auditAiCallLogMapper.selectAuditAiCallLogList(auditAiCallLog);
    }

    /**
     * 新增AI调用日志
     *
     * @param auditAiCallLog AI调用日志信息
     * @return 结果
     */
    @Override
    public int insertAuditAiCallLog(AuditAiCallLog auditAiCallLog)
    {
        if (auditAiCallLog.getCallTime() == null)
        {
            auditAiCallLog.setCallTime(new Date());
        }
        return auditAiCallLogMapper.insertAuditAiCallLog(auditAiCallLog);
    }

    /**
     * 修改AI调用日志
     *
     * @param auditAiCallLog AI调用日志信息
     * @return 结果
     */
    @Override
    public int updateAuditAiCallLog(AuditAiCallLog auditAiCallLog)
    {
        return auditAiCallLogMapper.updateAuditAiCallLog(auditAiCallLog);
    }

    /**
     * 批量删除AI调用日志
     *
     * @param ids 需要删除的AI调用日志主键集合
     * @return 结果
     */
    @Override
    public int deleteAuditAiCallLogByIds(Long[] ids)
    {
        return auditAiCallLogMapper.deleteAuditAiCallLogByIds(ids);
    }

    /**
     * 删除AI调用日志信息
     *
     * @param id AI调用日志主键
     * @return 结果
     */
    @Override
    public int deleteAuditAiCallLogById(Long id)
    {
        return auditAiCallLogMapper.deleteAuditAiCallLogById(id);
    }

    /**
     * 查询AI调用统计信息
     *
     * @param params 查询参数
     * @return 统计信息
     */
    @Override
    public Map<String, Object> selectAiCallStatistics(Map<String, Object> params)
    {
        return auditAiCallLogMapper.selectAiCallStatistics(params);
    }

    /**
     * 查询用户AI调用统计
     *
     * @param userId 用户ID
     * @return 调用统计
     */
    @Override
    public Map<String, Object> selectUserAiCallStatistics(Long userId)
    {
        return auditAiCallLogMapper.selectUserAiCallStatistics(userId);
    }

    /**
     * 查询场景AI调用统计
     *
     * @param scene 调用场景
     * @return 调用统计
     */
    @Override
    public Map<String, Object> selectSceneAiCallStatistics(String scene)
    {
        return auditAiCallLogMapper.selectSceneAiCallStatistics(scene);
    }

    /**
     * 查询模型AI调用统计
     *
     * @param model 模型名称
     * @return 调用统计
     */
    @Override
    public Map<String, Object> selectModelAiCallStatistics(String model)
    {
        return auditAiCallLogMapper.selectModelAiCallStatistics(model);
    }

    /**
     * 查询每日Token消耗趋势
     *
     * @param params 查询参数
     * @return 趋势数据
     */
    @Override
    public List<Map<String, Object>> selectDailyTokenTrend(Map<String, Object> params)
    {
        return auditAiCallLogMapper.selectDailyTokenTrend(params);
    }

    /**
     * 查询成本统计
     *
     * @param params 查询参数
     * @return 成本统计
     */
    @Override
    public Map<String, Object> selectCostStatistics(Map<String, Object> params)
    {
        return auditAiCallLogMapper.selectCostStatistics(params);
    }

    /**
     * 清理过期日志
     *
     * @param days 保留天数
     * @return 删除数量
     */
    @Override
    public int cleanExpiredLogs(Integer days)
    {
        if (days == null || days <= 0)
        {
            days = 90; // 默认保留90天
        }
        return auditAiCallLogMapper.cleanExpiredLogs(days);
    }

    /**
     * 记录AI调用日志
     *
     * @param userId 用户ID
     * @param scene 调用场景
     * @param model 使用模型
     * @param templateId 提示词模板ID
     * @param prompt 提示词内容
     * @param response AI响应内容
     * @param promptTokens 请求Token数
     * @param completionTokens 响应Token数
     * @param totalTokens 总Token数
     * @param status 调用状态
     * @param errorMsg 错误信息
     * @param responseTime 响应时间
     * @return 结果
     */
    @Override
    public int recordAiCall(Long userId, String scene, String model, Long templateId,
                           String prompt, String response, Integer promptTokens,
                           Integer completionTokens, Integer totalTokens,
                           Integer status, String errorMsg, Long responseTime)
    {
        AuditAiCallLog log = new AuditAiCallLog();
        log.setUserId(userId);
        log.setScene(scene);
        log.setModel(model);
        log.setTemplateId(templateId);
        log.setPrompt(prompt);
        log.setResponse(response);
        log.setPromptTokens(promptTokens);
        log.setCompletionTokens(completionTokens);
        log.setTotalTokens(totalTokens);
        log.setStatus(status);
        log.setErrorMsg(errorMsg);
        log.setResponseTime(responseTime);
        log.setCallTime(new Date());

        return insertAuditAiCallLog(log);
    }
}
