package com.ruoyi.dca.service.impl;

import java.util.Date;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import com.ruoyi.dca.domain.AuditOperationLog;
import com.ruoyi.dca.mapper.AuditOperationLogMapper;
import com.ruoyi.dca.service.IAuditOperationLogService;

/**
 * 操作审计日志 服务层实现
 *
 * @author ruoyi
 */
@Service
public class AuditOperationLogServiceImpl implements IAuditOperationLogService
{
    @Autowired
    private AuditOperationLogMapper auditOperationLogMapper;

    /**
     * 查询操作审计日志信息
     *
     * @param id 操作审计日志主键
     * @return 操作审计日志信息
     */
    @Override
    public AuditOperationLog selectAuditOperationLogById(Long id)
    {
        return auditOperationLogMapper.selectAuditOperationLogById(id);
    }

    /**
     * 查询操作审计日志列表
     *
     * @param auditOperationLog 操作审计日志信息
     * @return 操作审计日志集合
     */
    @Override
    public List<AuditOperationLog> selectAuditOperationLogList(AuditOperationLog auditOperationLog)
    {
        return auditOperationLogMapper.selectAuditOperationLogList(auditOperationLog);
    }

    /**
     * 新增操作审计日志
     *
     * @param auditOperationLog 操作审计日志信息
     * @return 结果
     */
    @Override
    public int insertAuditOperationLog(AuditOperationLog auditOperationLog)
    {
        if (auditOperationLog.getOperationTime() == null)
        {
            auditOperationLog.setOperationTime(new Date());
        }
        return auditOperationLogMapper.insertAuditOperationLog(auditOperationLog);
    }

    /**
     * 修改操作审计日志
     *
     * @param auditOperationLog 操作审计日志信息
     * @return 结果
     */
    @Override
    public int updateAuditOperationLog(AuditOperationLog auditOperationLog)
    {
        return auditOperationLogMapper.updateAuditOperationLog(auditOperationLog);
    }

    /**
     * 批量删除操作审计日志
     *
     * @param ids 需要删除的操作审计日志主键集合
     * @return 结果
     */
    @Override
    public int deleteAuditOperationLogByIds(Long[] ids)
    {
        return auditOperationLogMapper.deleteAuditOperationLogByIds(ids);
    }

    /**
     * 删除操作审计日志信息
     *
     * @param id 操作审计日志主键
     * @return 结果
     */
    @Override
    public int deleteAuditOperationLogById(Long id)
    {
        return auditOperationLogMapper.deleteAuditOperationLogById(id);
    }

    /**
     * 查询操作日志统计信息
     *
     * @param params 查询参数
     * @return 统计信息
     */
    @Override
    public Map<String, Object> selectOperationStatistics(Map<String, Object> params)
    {
        return auditOperationLogMapper.selectOperationStatistics(params);
    }

    /**
     * 查询用户操作统计
     *
     * @param userId 用户ID
     * @return 操作统计
     */
    @Override
    public Map<String, Object> selectUserOperationStatistics(Long userId)
    {
        return auditOperationLogMapper.selectUserOperationStatistics(userId);
    }

    /**
     * 查询模块操作统计
     *
     * @param module 模块名称
     * @return 操作统计
     */
    @Override
    public Map<String, Object> selectModuleOperationStatistics(String module)
    {
        return auditOperationLogMapper.selectModuleOperationStatistics(module);
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
        return auditOperationLogMapper.cleanExpiredLogs(days);
    }

    /**
     * 记录操作日志
     *
     * @param userId 用户ID
     * @param username 用户名
     * @param module 操作模块
     * @param operation 操作类型
     * @param description 操作描述
     * @param requestMethod 请求方法
     * @param requestUrl 请求URL
     * @param requestIp 请求IP
     * @param requestParams 请求参数
     * @param responseData 返回结果
     * @param status 操作状态
     * @param errorMsg 错误信息
     * @param executionTime 执行时间
     * @return 结果
     */
    @Override
    public int recordOperation(Long userId, String username, String module, String operation,
                              String description, String requestMethod, String requestUrl, String requestIp,
                              String requestParams, String responseData, Integer status, String errorMsg, Long executionTime)
    {
        AuditOperationLog log = new AuditOperationLog();
        log.setUserId(userId);
        log.setUsername(username);
        log.setModule(module);
        log.setOperation(operation);
        log.setDescription(description);
        log.setRequestMethod(requestMethod);
        log.setRequestUrl(requestUrl);
        log.setRequestIp(requestIp);
        log.setRequestParams(requestParams);
        log.setResponseData(responseData);
        log.setStatus(status);
        log.setErrorMsg(errorMsg);
        log.setExecutionTime(executionTime);
        log.setOperationTime(new Date());

        return insertAuditOperationLog(log);
    }
}
