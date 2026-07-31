package com.ruoyi.dca.mapper;

import java.util.List;
import java.util.Map;
import com.ruoyi.dca.domain.AuditOperationLog;
import org.apache.ibatis.annotations.Param;

/**
 * 操作审计日志 数据层
 *
 * @author ruoyi
 */
public interface AuditOperationLogMapper
{
    /**
     * 查询操作审计日志
     *
     * @param id 操作审计日志主键
     * @return 操作审计日志
     */
    public AuditOperationLog selectAuditOperationLogById(Long id);

    /**
     * 查询操作审计日志列表
     *
     * @param auditOperationLog 操作审计日志
     * @return 操作审计日志集合
     */
    public List<AuditOperationLog> selectAuditOperationLogList(AuditOperationLog auditOperationLog);

    /**
     * 新增操作审计日志
     *
     * @param auditOperationLog 操作审计日志
     * @return 结果
     */
    public int insertAuditOperationLog(AuditOperationLog auditOperationLog);

    /**
     * 修改操作审计日志
     *
     * @param auditOperationLog 操作审计日志
     * @return 结果
     */
    public int updateAuditOperationLog(AuditOperationLog auditOperationLog);

    /**
     * 删除操作审计日志
     *
     * @param id 操作审计日志主键
     * @return 结果
     */
    public int deleteAuditOperationLogById(Long id);

    /**
     * 批量删除操作审计日志
     *
     * @param ids 需要删除的数据主键集合
     * @return 结果
     */
    public int deleteAuditOperationLogByIds(Long[] ids);

    /**
     * 查询操作日志统计信息
     *
     * @param params 查询参数
     * @return 统计信息
     */
    public Map<String, Object> selectOperationStatistics(Map<String, Object> params);

    /**
     * 查询用户操作统计
     *
     * @param userId 用户ID
     * @return 操作统计
     */
    public Map<String, Object> selectUserOperationStatistics(@Param("userId") Long userId);

    /**
     * 查询模块操作统计
     *
     * @param module 模块名称
     * @return 操作统计
     */
    public Map<String, Object> selectModuleOperationStatistics(@Param("module") String module);

    /**
     * 清理过期日志
     *
     * @param days 保留天数
     * @return 删除数量
     */
    public int cleanExpiredLogs(@Param("days") Integer days);
}
