package com.ruoyi.dca.service.impl;

import com.ruoyi.dca.service.IAuditStrategyTriggerService;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 旧 DCA 触发审计服务已退役。
 * 当前仅保留兼容统计与清理返回，避免控制面继续依赖旧触发表。
 */
@Service
public class AuditStrategyTriggerServiceImpl implements IAuditStrategyTriggerService {

    private static final String LEGACY_TRIGGER_RETIRED_MESSAGE =
        "旧 DCA 触发审计已退役，请使用运行时决策审计控制台。";

    @Override
    public Map<String, Object> selectTriggerStatistics(Map<String, Object> params) {
        Map<String, Object> statistics = new LinkedHashMap<>();
        statistics.put("retired", true);
        statistics.put("message", LEGACY_TRIGGER_RETIRED_MESSAGE);
        statistics.put("totalTriggers", 0L);
        statistics.put("triggerTypeCount", Map.of());
        statistics.put("resultCount", Map.of());
        statistics.put("phaseCount", Map.of());
        return statistics;
    }

    @Override
    public Map<String, Object> selectUserTriggerStatistics(Long userId) {
        return selectTriggerStatistics(Map.of("userId", userId));
    }

    @Override
    public Map<String, Object> selectStrategyTriggerStatistics(Long strategyId) {
        return selectTriggerStatistics(Map.of("strategyId", strategyId));
    }

    @Override
    public int cleanExpiredLogs(Integer days) {
        return 0;
    }
}
