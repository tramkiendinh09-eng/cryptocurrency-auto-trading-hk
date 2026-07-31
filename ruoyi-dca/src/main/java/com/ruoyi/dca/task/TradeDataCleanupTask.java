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
        int retentionDays = resolveEventRetentionDays();
        String cutoffTime = TradeRuntimeTimeUtils.formatSqlDateTime(
            TradeRuntimeTimeUtils.nowDatabaseLocalDateTime().minusDays(retentionDays)
        );
        int deletedRows = 0;
        deletedRows += cleanupMapper.deleteSignalScoresBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteSignalEventsBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteExpiredSignalWindowStatesBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteMarketEventsBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteMarketKlineSnapshotsBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteMarketMetricSnapshotsBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteNewsEventsBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteOnchainEventsBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteSocialEventsBefore(cutoffTime);
        deletedRows += cleanupMapper.deleteEventRawsBefore(cutoffTime);
        log.info("Cleaned expired event/signal data before {}, retentionDays={}, deletedRows={}", cutoffTime, retentionDays, deletedRows);
        return deletedRows;
    }

    private int resolveEventRetentionDays() {
        TradeRuntimeConfig config = runtimeConfigService.getCurrentConfig();
        Integer retentionDays = config == null ? null : config.getEventRetentionDays();
        if (retentionDays == null || retentionDays < 1) {
            return DEFAULT_RETENTION_DAYS;
        }
        return Math.min(retentionDays, MAX_RETENTION_DAYS);
    }
}
