package com.ruoyi.dca.task;

import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.mapper.task.TradeDataCleanupMapper;
import com.ruoyi.dca.service.trade.ITradeRuntimeConfigService;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Function;

@Component
public class TradeDataCleanupTask {

    private static final Logger log = LoggerFactory.getLogger(TradeDataCleanupTask.class);
    private static final int DEFAULT_RETENTION_DAYS = 7;
    private static final int MAX_RETENTION_DAYS = 30;

    @Autowired
    private TradeDataCleanupMapper cleanupMapper;

    @Autowired
    private ITradeRuntimeConfigService runtimeConfigService;

    @Scheduled(cron = "0 30 10 * * ?", zone = "Asia/Shanghai")
    public int cleanExpiredEventAndSignalData() {
        Map<String, Function<String, Integer>> steps = new LinkedHashMap<>();
        steps.put("signal_score", cleanupMapper::deleteSignalScoresBefore);
        steps.put("signal_event", cleanupMapper::deleteSignalEventsBefore);
        steps.put("signal_window_state", cleanupMapper::deleteExpiredSignalWindowStatesBefore);
        steps.put("market_event", cleanupMapper::deleteMarketEventsBefore);
        steps.put("market_kline_snapshot", cleanupMapper::deleteMarketKlineSnapshotsBefore);
        steps.put("market_metric_snapshot", cleanupMapper::deleteMarketMetricSnapshotsBefore);
        steps.put("news_event", cleanupMapper::deleteNewsEventsBefore);
        steps.put("onchain_event", cleanupMapper::deleteOnchainEventsBefore);
        steps.put("social_event", cleanupMapper::deleteSocialEventsBefore);
        steps.put("event_raw", cleanupMapper::deleteEventRawsBefore);
        return runCleanup("event/signal", resolveEventRetentionDays(), steps);
    }

    /**
     * 回放域的清理。此前 replayRetentionDays 被读取、被校验，却没有任何删除路径
     * 使用它——feature_snapshot 与 agent_observation 从部署起就无人回收，两张表
     * 合计每天增长约 278MB。
     */
    @Scheduled(cron = "0 45 10 * * ?", zone = "Asia/Shanghai")
    public int cleanExpiredReplayData() {
        Map<String, Function<String, Integer>> steps = new LinkedHashMap<>();
        steps.put("feature_snapshot", cleanupMapper::deleteFeatureSnapshotsBefore);
        steps.put("agent_observation", cleanupMapper::deleteAgentObservationsBefore);
        return runCleanup("replay", resolveReplayRetentionDays(), steps);
    }

    /**
     * 逐表独立执行，单表失败不影响其余表。
     *
     * 此前是一串顺序调用，任何一步抛异常整个任务就中断。实际发生过：
     * market_event 少了 created_at 列（schema 是从 mapper 反推重建的，
     * 该列没出现在任何 insert 里所以没被还原），第 4 步抛
     * BadSqlGrammarException，**后面 6 步从此每天都不执行**，其中包括
     * event_raw 和 market_metric_snapshot 这两张最大的表。日志里只有一行
     * "Unexpected error occurred in scheduled task"，看不出哪些表没清。
     *
     * 所以这里改成逐表捕获：失败的表单独记名，其余照常清理，末尾汇总。
     */
    private int runCleanup(String domain, int retentionDays, Map<String, Function<String, Integer>> steps) {
        String cutoffTime = TradeRuntimeTimeUtils.formatSqlDateTime(
            TradeRuntimeTimeUtils.nowDatabaseLocalDateTime().minusDays(retentionDays)
        );
        int deletedRows = 0;
        int failedTables = 0;
        for (Map.Entry<String, Function<String, Integer>> step : steps.entrySet()) {
            try {
                deletedRows += step.getValue().apply(cutoffTime);
            } catch (Exception ex) {
                failedTables++;
                log.error("Cleanup failed for table {} before {}: {}", step.getKey(), cutoffTime, ex.getMessage(), ex);
            }
        }
        if (failedTables > 0) {
            log.error("Cleaned {} data before {}, retentionDays={}, deletedRows={}, failedTables={}/{}",
                domain, cutoffTime, retentionDays, deletedRows, failedTables, steps.size());
        } else {
            log.info("Cleaned {} data before {}, retentionDays={}, deletedRows={}",
                domain, cutoffTime, retentionDays, deletedRows);
        }
        return deletedRows;
    }

    private int resolveEventRetentionDays() {
        TradeRuntimeConfig config = runtimeConfigService.getCurrentConfig();
        return clampRetentionDays(config == null ? null : config.getEventRetentionDays());
    }

    private int resolveReplayRetentionDays() {
        TradeRuntimeConfig config = runtimeConfigService.getCurrentConfig();
        return clampRetentionDays(config == null ? null : config.getReplayRetentionDays());
    }

    private int clampRetentionDays(Integer retentionDays) {
        if (retentionDays == null || retentionDays < 1) {
            return DEFAULT_RETENTION_DAYS;
        }
        return Math.min(retentionDays, MAX_RETENTION_DAYS);
    }
}
