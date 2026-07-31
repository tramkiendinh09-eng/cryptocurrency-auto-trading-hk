package com.ruoyi.dca.service.trade.impl;

import com.ruoyi.dca.domain.trade.TradeRuntimeBootstrap;
import com.ruoyi.dca.domain.trade.TradeActionSummary;
import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.domain.trade.TradeRuntimeOverview;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.mapper.trade.TradeRuntimeOverviewMapper;
import com.ruoyi.dca.service.trade.ITradeRuntimeConfigService;
import com.ruoyi.dca.service.trade.ITradeRuntimeOverviewService;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeParseException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class TradeRuntimeOverviewServiceImpl implements ITradeRuntimeOverviewService {

    private static final int RECENT_LIMIT = 5;

    @Autowired
    private ITradeRuntimeConfigService runtimeConfigService;

    @Autowired
    private TradeRuntimeOverviewMapper tradeRuntimeOverviewMapper;

    @Override
    public TradeRuntimeOverview getOverview() {
        TradeRuntimeOverview overview = new TradeRuntimeOverview();
        overview.setRuntimeConfig(resolveOverviewRuntimeConfig());
        overview.setEventCount(defaultLong(tradeRuntimeOverviewMapper.countEventRaws()));
        overview.setSignalCount(defaultLong(tradeRuntimeOverviewMapper.countSignalEvents()));
        overview.setDecisionCount(defaultLong(tradeRuntimeOverviewMapper.countDecisionRuns()));
        overview.setRiskHitCount(defaultLong(tradeRuntimeOverviewMapper.countRiskGuardHits()));
        overview.setActivePositionCount(defaultLong(tradeRuntimeOverviewMapper.countActivePositions()));
        overview.setTotalUnrealizedPnl(defaultDecimal(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()));
        PnlSnapshot latestPnlSnapshot = tradeRuntimeOverviewMapper.selectLatestPnlSnapshot();
        overview.setLatestPnlSnapshot(latestPnlSnapshot);
        overview.setLatestDailyPnl(resolveLatestDailyPnl(latestPnlSnapshot));
        overview.setMaxDrawdownPct(latestPnlSnapshot == null ? BigDecimal.ZERO : defaultDecimal(latestPnlSnapshot.getMaxDrawdownPct()));
        reconcileLatestPnlSnapshot(overview, latestPnlSnapshot);
        DecisionRun latestDecisionRun = tradeRuntimeOverviewMapper.selectLatestDecisionRun();
        if (latestDecisionRun != null) {
            overview.setLatestDispatchMode(latestDecisionRun.getDispatchMode());
            overview.setLastTriggerReason(latestDecisionRun.getTriggerReason());
            overview.setLastTriggerSource(latestDecisionRun.getTriggerSource());
            overview.setLastSelectedAgentsJson(latestDecisionRun.getSelectedAgentsJson());
            overview.setLastCombinationMatchJson(latestDecisionRun.getCombinationMatchJson());
        }
        overview.setCooldownSuppressionCount(defaultLong(tradeRuntimeOverviewMapper.countCooldownBlockedDecisionRuns()));
        overview.setBudgetSuppressionCount(defaultLong(tradeRuntimeOverviewMapper.countBudgetBlockedDecisionRuns()));
        overview.setRecentEvents(tradeRuntimeOverviewMapper.selectRecentEventRaws(RECENT_LIMIT));
        overview.setRecentSignals(tradeRuntimeOverviewMapper.selectRecentSignalEvents(RECENT_LIMIT));
        overview.setActiveSignalWindows(tradeRuntimeOverviewMapper.selectActiveSignalWindows(RECENT_LIMIT, TradeRuntimeTimeUtils.nowSqlDateTime()));
        overview.setRecentAgentConclusions(tradeRuntimeOverviewMapper.selectRecentAgentConclusions(RECENT_LIMIT));
        overview.setRecentDecisions(tradeRuntimeOverviewMapper.selectRecentDecisionRuns(RECENT_LIMIT));
        overview.setRecentRiskHits(tradeRuntimeOverviewMapper.selectRecentRiskGuardHits(RECENT_LIMIT));
        overview.setRecentFills(tradeRuntimeOverviewMapper.selectRecentExchangeFills(RECENT_LIMIT));
        overview.setRecentTradeActions(tradeRuntimeOverviewMapper.selectRecentTradeActionSummaries(RECENT_LIMIT));
        overview.setRecentOrders(tradeRuntimeOverviewMapper.selectRecentExchangeOrders(RECENT_LIMIT));
        overview.setRecentPositions(tradeRuntimeOverviewMapper.selectRecentPositionSnapshots(RECENT_LIMIT));
        overview.setExecutionStats(buildExecutionStats());
        return overview;
    }

    private TradeRuntimeConfig resolveOverviewRuntimeConfig() {
        TradeRuntimeConfig currentConfig = runtimeConfigService.getCurrentConfig();
        List<TradeRuntimeBootstrap> bootstraps = runtimeConfigService.listBootstrapConfigs();
        if (bootstraps == null || bootstraps.isEmpty()) {
            return currentConfig;
        }
        for (TradeRuntimeBootstrap bootstrap : bootstraps) {
            if (bootstrap != null && bootstrap.getRuntimeConfig() != null) {
                return bootstrap.getRuntimeConfig();
            }
        }
        return currentConfig;
    }

    private Long defaultLong(Long value) {
        return value == null ? 0L : value;
    }

    private BigDecimal defaultDecimal(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value;
    }

    private BigDecimal resolveLatestDailyPnl(PnlSnapshot latestPnlSnapshot) {
        if (latestPnlSnapshot == null) {
            return BigDecimal.ZERO;
        }
        if (!shouldPreserveDailyPnlForCurrentUtcDay(latestPnlSnapshot.getCreatedAt())) {
            return BigDecimal.ZERO;
        }
        return defaultDecimal(latestPnlSnapshot.getDailyPnl());
    }

    private void reconcileLatestPnlSnapshot(TradeRuntimeOverview overview, PnlSnapshot latestPnlSnapshot) {
        if (overview == null || latestPnlSnapshot == null) {
            return;
        }
        String createdAt = latestPnlSnapshot.getCreatedAt();
        if (createdAt == null || createdAt.isBlank()) {
            return;
        }
        List<TradeActionSummary> tradeActions = tradeRuntimeOverviewMapper.selectTradeActionSummariesAfter(createdAt);
        if (tradeActions == null || tradeActions.isEmpty()) {
            return;
        }
        BigDecimal accountEquity = defaultDecimal(latestPnlSnapshot.getAccountEquity());
        BigDecimal dailyPnl = resolveLatestDailyPnl(latestPnlSnapshot);
        BigDecimal peakAccountEquity = defaultDecimal(latestPnlSnapshot.getPeakAccountEquity());
        if (peakAccountEquity.compareTo(BigDecimal.ZERO) <= 0) {
            peakAccountEquity = accountEquity;
        }
        BigDecimal maxDrawdownPct = defaultDecimal(latestPnlSnapshot.getMaxDrawdownPct());
        for (TradeActionSummary tradeAction : tradeActions) {
            BigDecimal realizedPnl = defaultDecimal(tradeAction == null ? null : tradeAction.getRealizedPnl());
            if (realizedPnl.compareTo(BigDecimal.ZERO) == 0) {
                continue;
            }
            accountEquity = accountEquity.add(realizedPnl);
            if (accountEquity.compareTo(peakAccountEquity) > 0) {
                peakAccountEquity = accountEquity;
            }
            if (shouldPreserveDailyPnlForCurrentUtcDay(tradeAction == null ? null : tradeAction.getCreatedAt())) {
                dailyPnl = dailyPnl.add(realizedPnl);
            }
            BigDecimal drawdownPct = calculateDrawdownPct(peakAccountEquity, accountEquity);
            if (drawdownPct.compareTo(maxDrawdownPct) > 0) {
                maxDrawdownPct = drawdownPct;
            }
        }
        latestPnlSnapshot.setAccountEquity(accountEquity);
        latestPnlSnapshot.setDailyPnl(dailyPnl);
        latestPnlSnapshot.setPeakAccountEquity(peakAccountEquity);
        latestPnlSnapshot.setMaxDrawdownPct(maxDrawdownPct);
        overview.setLatestPnlSnapshot(latestPnlSnapshot);
        overview.setLatestDailyPnl(dailyPnl);
        overview.setMaxDrawdownPct(maxDrawdownPct);
    }

    private boolean shouldPreserveDailyPnlForCurrentUtcDay(String createdAt) {
        if (createdAt == null || createdAt.isBlank()) {
            return true;
        }
        LocalDate snapshotUtcDate = resolveSnapshotUtcDate(createdAt);
        if (snapshotUtcDate == null) {
            return true;
        }
        return snapshotUtcDate.equals(LocalDate.now(ZoneOffset.UTC));
    }

    private LocalDate resolveSnapshotUtcDate(String createdAt) {
        String normalized = createdAt == null ? null : createdAt.trim();
        if (normalized == null || normalized.isBlank()) {
            return null;
        }
        try {
            return LocalDateTime.parse(normalized, TradeRuntimeTimeUtils.SQL_DATETIME_FORMATTER)
                .atZone(TradeRuntimeTimeUtils.DATABASE_ZONE)
                .withZoneSameInstant(ZoneOffset.UTC)
                .toLocalDate();
        } catch (DateTimeParseException ignored) {
            // Fall through to ISO-8601 parsers.
        }
        try {
            return OffsetDateTime.parse(normalized).withOffsetSameInstant(ZoneOffset.UTC).toLocalDate();
        } catch (DateTimeParseException ignored) {
            // Fall through to Instant parser.
        }
        try {
            return Instant.parse(normalized).atZone(ZoneOffset.UTC).toLocalDate();
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }

    private BigDecimal calculateDrawdownPct(BigDecimal peakAccountEquity, BigDecimal accountEquity) {
        if (peakAccountEquity == null || accountEquity == null || peakAccountEquity.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO;
        }
        if (accountEquity.compareTo(peakAccountEquity) >= 0) {
            return BigDecimal.ZERO;
        }
        return peakAccountEquity.subtract(accountEquity)
            .multiply(new BigDecimal("100"))
            .divide(peakAccountEquity, 8, RoundingMode.HALF_UP);
    }

    private Map<String, Long> buildExecutionStats() {
        Map<String, Long> executionStats = createDefaultExecutionStats();
        List<Map<String, Object>> rows = tradeRuntimeOverviewMapper.selectExecutionStatusCounts();
        long total = 0L;
        if (rows == null) {
            return executionStats;
        }
        for (Map<String, Object> row : rows) {
            long count = toLong(row.get("total"));
            executionStats.put(normalizeExecutionStatus(row.get("executionStatus")), count);
            total += count;
        }
        executionStats.put("total", total);
        return executionStats;
    }

    private Map<String, Long> createDefaultExecutionStats() {
        Map<String, Long> executionStats = new LinkedHashMap<>();
        executionStats.put("total", 0L);
        executionStats.put("filled", 0L);
        executionStats.put("submitted", 0L);
        executionStats.put("pending", 0L);
        executionStats.put("partial", 0L);
        executionStats.put("canceled", 0L);
        executionStats.put("expired", 0L);
        executionStats.put("failed", 0L);
        executionStats.put("blocked", 0L);
        executionStats.put("skipped", 0L);
        return executionStats;
    }

    private String normalizeExecutionStatus(Object rawStatus) {
        if (rawStatus == null) {
            return "pending";
        }
        String status = rawStatus.toString().trim().toLowerCase(Locale.ROOT);
        switch (status) {
            case "filled":
            case "submitted":
            case "pending":
            case "partial":
            case "canceled":
            case "expired":
            case "failed":
            case "blocked":
            case "skipped":
                return status;
            default:
                return "pending";
        }
    }

    private Long toLong(Object value) {
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        if (value == null) {
            return 0L;
        }
        try {
            return Long.parseLong(value.toString());
        } catch (NumberFormatException e) {
            return 0L;
        }
    }
}
