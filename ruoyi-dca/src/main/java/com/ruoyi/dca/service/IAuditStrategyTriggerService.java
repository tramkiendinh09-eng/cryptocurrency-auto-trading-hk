package com.ruoyi.dca.service;

import java.util.Map;

/**
 * 旧 DCA 触发审计服务接口。
 * runtime 重构后仅保留兼容统计与清理契约，不再暴露旧表 CRUD/写入能力。
 */
public interface IAuditStrategyTriggerService {

    Map<String, Object> selectTriggerStatistics(Map<String, Object> params);

    Map<String, Object> selectUserTriggerStatistics(Long userId);

    Map<String, Object> selectStrategyTriggerStatistics(Long strategyId);

    int cleanExpiredLogs(Integer days);
}
