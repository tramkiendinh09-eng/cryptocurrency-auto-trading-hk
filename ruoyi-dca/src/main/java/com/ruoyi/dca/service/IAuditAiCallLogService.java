package com.ruoyi.dca.service;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.AuditAiCallLog;

/**
 * AI调用日志 服务层
 *
 * @author ruoyi
 */
public interface IAuditAiCallLogService
{
    /**
     * 查询AI调用日志信息
     *
     * @param id AI调用日志主键
     * @return AI调用日志信息
     */
    public AuditAiCallLog selectAuditAiCallLogById(Long id);

    /**
     * 查询AI调用日志列表
     *
     * @param auditAiCallLog AI调用日志信息
     * @return AI调用日志集合
     */
    public List<AuditAiCallLog> selectAuditAiCallLogList(AuditAiCallLog auditAiCallLog);

    /**
     * 新增AI调用日志
     *
     * @param auditAiCallLog AI调用日志信息
     * @return 结果
     */
    public int insertAuditAiCallLog(AuditAiCallLog auditAiCallLog);

    /**
     * 修改AI调用日志
     *
     * @param auditAiCallLog AI调用日志信息
     * @return 结果
     */
    public int updateAuditAiCallLog(AuditAiCallLog auditAiCallLog);

    /**
     * 批量删除AI调用日志
     *
     * @param ids 需要删除的AI调用日志主键集合
     * @return 结果
     */
    public int deleteAuditAiCallLogByIds(Long[] ids);

    /**
     * 删除AI调用日志信息
     *
     * @param id AI调用日志主键
     * @return 结果
     */
    public int deleteAuditAiCallLogById(Long id);

    /**
     * 查询AI调用统计信息
     *
     * @param params 查询参数
     * @return 统计信息
     */
    public Map<String, Object> selectAiCallStatistics(Map<String, Object> params);

    /**
     * 查询用户AI调用统计
     *
     * @param userId 用户ID
     * @return 调用统计
     */
    public Map<String, Object> selectUserAiCallStatistics(Long userId);

    /**
     * 查询场景AI调用统计
     *
     * @param scene 调用场景
     * @return 调用统计
     */
    public Map<String, Object> selectSceneAiCallStatistics(String scene);

    /**
     * 查询模型AI调用统计
     *
     * @param model 模型名称
     * @return 调用统计
     */
    public Map<String, Object> selectModelAiCallStatistics(String model);

    /**
     * 查询每日Token消耗趋势
     *
     * @param params 查询参数
     * @return 趋势数据
     */
    public List<Map<String, Object>> selectDailyTokenTrend(Map<String, Object> params);

    /**
     * 查询成本统计
     *
     * @param params 查询参数
     * @return 成本统计
     */
    public Map<String, Object> selectCostStatistics(Map<String, Object> params);

    /**
     * 清理过期日志
     *
     * @param days 保留天数
     * @return 删除数量
     */
    public int cleanExpiredLogs(Integer days);

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
    public int recordAiCall(Long userId, String scene, String model, Long templateId,
                           String prompt, String response, Integer promptTokens,
                           Integer completionTokens, Integer totalTokens,
                           Integer status, String errorMsg, Long responseTime);
}
