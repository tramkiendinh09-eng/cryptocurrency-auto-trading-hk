package com.ruoyi.dca.mapper;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.AuditAiCallLog;
import org.apache.ibatis.annotations.Param;

/**
 * AI调用日志 数据层
 *
 * @author ruoyi
 */
public interface AuditAiCallLogMapper
{
    /**
     * 查询AI调用日志
     *
     * @param id AI调用日志主键
     * @return AI调用日志
     */
    public AuditAiCallLog selectAuditAiCallLogById(Long id);

    /**
     * 查询AI调用日志列表
     *
     * @param auditAiCallLog AI调用日志
     * @return AI调用日志集合
     */
    public List<AuditAiCallLog> selectAuditAiCallLogList(AuditAiCallLog auditAiCallLog);

    /**
     * 新增AI调用日志
     *
     * @param auditAiCallLog AI调用日志
     * @return 结果
     */
    public int insertAuditAiCallLog(AuditAiCallLog auditAiCallLog);

    /**
     * 修改AI调用日志
     *
     * @param auditAiCallLog AI调用日志
     * @return 结果
     */
    public int updateAuditAiCallLog(AuditAiCallLog auditAiCallLog);

    /**
     * 删除AI调用日志
     *
     * @param id AI调用日志主键
     * @return 结果
     */
    public int deleteAuditAiCallLogById(Long id);

    /**
     * 批量删除AI调用日志
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteAuditAiCallLogByIds(Long[] ids);

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
    public Map<String, Object> selectUserAiCallStatistics(@Param("userId") Long userId);

    /**
     * 查询场景AI调用统计
     *
     * @param scene 调用场景
     * @return 调用统计
     */
    public Map<String, Object> selectSceneAiCallStatistics(@Param("scene") String scene);

    /**
     * 查询模型调用统计
     *
     * @param model 模型名称
     * @return 调用统计
     */
    public Map<String, Object> selectModelAiCallStatistics(@Param("model") String model);

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
    public int cleanExpiredLogs(@Param("days") Integer days);

    /**
     * 查询每个模型的调用统计
     *
     * @return 模型使用统计列表
     */
    public List<Map<String, Object>> selectModelUsageStats();

    /**
     * 根据模型代码查询调用次数
     *
     * @param model 模型代码/名称
     * @return 调用次数
     */
    public int selectCallCountByModel(@Param("model") String model);
}
