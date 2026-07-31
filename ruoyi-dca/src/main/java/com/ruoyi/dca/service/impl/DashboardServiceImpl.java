package com.ruoyi.dca.service.impl;

import com.ruoyi.common.core.redis.RedisCache;
import com.ruoyi.dca.domain.dto.TaskDTO;
import com.ruoyi.dca.domain.vo.DashboardOverviewVO;
import com.ruoyi.dca.domain.vo.HoldingDistributionVO;
import com.ruoyi.dca.domain.vo.StrategyComparisonVO;
import com.ruoyi.dca.mapper.NotifyRecordMapper;
import com.ruoyi.dca.mapper.runtime.TradeExecutionMapper;
import com.ruoyi.dca.mapper.trade.TradeRuntimeOverviewMapper;
import com.ruoyi.dca.service.IDashboardService;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 运行时仪表盘服务实现。
 *
 * <p>当前仪表盘只消费 runtime 域读模型；旧 DCA 图表接口仅保留退役兼容空壳。</p>
 *
 * @author ruoyi
 */
@Service
public class DashboardServiceImpl implements IDashboardService {

    private static final Logger log = LoggerFactory.getLogger(DashboardServiceImpl.class);

    private static final String WORKER_HEARTBEAT_KEY_PATTERN = "dca:worker:heartbeat:*";
    private static final String WORKER_HEARTBEAT_KEY_PREFIX = "dca:worker:heartbeat:";
    private static final String TASK_QUEUE_KEY = "dca:task:queue";
    private static final String TASK_PRIORITY_QUEUE_KEY = "dca:task:priority:queue";
    private static final String TASK_STATUS_CACHE_KEY = "dca:task:status";
    private static final int RUNTIME_RECENT_LIMIT = 5;
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    @Autowired
    private NotifyRecordMapper notifyRecordMapper;

    @Autowired
    private RedisCache redisCache;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Autowired
    private TradeExecutionMapper tradeExecutionMapper;

    @Autowired
    private TradeRuntimeOverviewMapper tradeRuntimeOverviewMapper;

    @Override
    public DashboardOverviewVO getOverview(Long userId) {
        DashboardOverviewVO overview = new DashboardOverviewVO();
        try {
            Map<String, Object> workerStatus = getRuntimeWorkerStatus();
            overview.setTotalStrategies(0);
            overview.setActiveStrategies(0);
            overview.setTodayTriggers(0);
            overview.setTodayNotifications(Math.toIntExact(toLong(notifyRecordMapper.countTodaySends())));
            overview.setTotalInvest(BigDecimal.ZERO);
            overview.setCurrentValue(BigDecimal.ZERO);
            overview.setProfitAmount(defaultDecimal(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()));
            overview.setProfitRate(BigDecimal.ZERO);
            overview.setWorkerOnline(Boolean.TRUE.equals(workerStatus.get("online")));
            overview.setQueueLength(Math.toIntExact(toLong(workerStatus.get("queueLength"))));
            overview.setRedisConnected(isRedisConnected());
        } catch (Exception e) {
            log.error("获取运行时仪表盘概览失败: userId={}", userId, e);
        }
        return overview;
    }

    @Override
    public Map<String, Object> getOverviewMap(Long userId) {
        Map<String, Object> result = new LinkedHashMap<>();

        try {
            RedisPingResult redisStatus = pingRedis();
            Map<String, Object> workerStatus = getRuntimeWorkerStatus();
            Map<String, Object> notifyStats = buildNotifyStats();
            Map<String, Object> runtimeOverview = buildRuntimeOverviewSnapshot();
            Map<String, Object> riskStats = buildRiskStats(runtimeOverview);
            Map<String, Object> systemStatus = buildSystemStatus(redisStatus, workerStatus);

            result.putAll(runtimeOverview);
            result.put("notifyStats", notifyStats);
            result.put("riskStats", riskStats);
            result.put("workerStatus", workerStatus);
            result.put("systemStatus", systemStatus);
            result.put("workerOnline", workerStatus.getOrDefault("online", false));
            result.put("redisConnected", systemStatus.get("redisConnected"));
            result.put("dbConnected", systemStatus.get("dbConnected"));
            result.put("queueLength", systemStatus.get("queueLength"));
            result.put("apiLatency", systemStatus.get("apiLatency"));
        } catch (Exception e) {
            log.error("获取运行时仪表盘概览 Map 失败: userId={}", userId, e);
            result.putAll(createDefaultRuntimeOverviewSnapshot());
            result.put("notifyStats", buildDefaultNotifyStats());
            result.put("riskStats", buildDefaultRiskStats());
            result.put("workerStatus", createDefaultWorkerStatus());
            result.put("systemStatus", createDefaultSystemStatus());
            result.put("workerOnline", false);
            result.put("redisConnected", false);
            result.put("dbConnected", true);
            result.put("queueLength", 0);
            result.put("apiLatency", 0L);
        }

        return result;
    }

    public Map<String, Object> getProfitLossCurve(Long strategyId) {
        return createRetiredProfitLossCurve();
    }

    public List<HoldingDistributionVO> getHoldingDistribution(Long userId) {
        return Collections.emptyList();
    }

    public Map<String, Object> getAiConsumption(Long userId) {
        return createRetiredAiConsumptionSnapshot();
    }

    public Map<String, Object> getTriggerTrend(Long userId) {
        return createRetiredTriggerTrend();
    }

    public Map<String, Object> getTradeVolume(Long userId) {
        return createRetiredTradeVolume();
    }

    public Map<String, Object> getProfitRate(Long userId) {
        return createRetiredProfitRate();
    }

    public Map<String, Object> getPriceTrend(String symbol, Long userId) {
        return createRetiredPriceTrend(symbol);
    }

    public List<StrategyComparisonVO> getStrategyComparison(Long userId) {
        return Collections.emptyList();
    }

    public List<Map<String, Object>> getRecentTriggers(Long userId, Integer limit) {
        return Collections.emptyList();
    }

    private Map<String, Object> getRuntimeWorkerStatus() {
        Map<String, Object> workerStatus = createDefaultWorkerStatus();
        workerStatus.put("queueLength", getQueueLength());

        try {
            java.util.Collection<String> heartbeatKeys = redisCache.keys(WORKER_HEARTBEAT_KEY_PATTERN);
            if (heartbeatKeys == null || heartbeatKeys.isEmpty()) {
                return workerStatus;
            }

            String latestWorkerId = null;
            Long latestHeartbeat = null;
            for (String key : heartbeatKeys) {
                String rawHeartbeat = stringRedisTemplate.opsForValue().get(key);
                Long heartbeat = parseHeartbeat(rawHeartbeat);
                if (heartbeat == null) {
                    continue;
                }
                if (latestHeartbeat == null || heartbeat > latestHeartbeat) {
                    latestHeartbeat = heartbeat;
                    latestWorkerId = key.replace(WORKER_HEARTBEAT_KEY_PREFIX, "");
                }
            }

            if (latestWorkerId != null) {
                workerStatus.put("online", true);
                workerStatus.put("workerId", latestWorkerId);
                workerStatus.put("lastHeartbeat", formatHeartbeat(latestHeartbeat));
                applyWorkerTaskCounters(workerStatus, latestWorkerId);
            }
        } catch (Exception e) {
            log.warn("Failed to load runtime worker status", e);
        }

        return workerStatus;
    }

    private Integer getQueueLength() {
        try {
            Long priorityLength = stringRedisTemplate.opsForList().size(TASK_PRIORITY_QUEUE_KEY);
            Long normalLength = stringRedisTemplate.opsForList().size(TASK_QUEUE_KEY);
            return Math.toIntExact((priorityLength != null ? priorityLength : 0L)
                + (normalLength != null ? normalLength : 0L));
        } catch (Exception e) {
            log.warn("Failed to get queue length", e);
            return 0;
        }
    }

    private boolean isRedisConnected() {
        return pingRedis().isConnected();
    }

    private RedisPingResult pingRedis() {
        long start = getCurrentTimeNanos();
        try {
            String pong = stringRedisTemplate.execute((RedisCallback<String>) connection -> connection.ping());
            return new RedisPingResult("PONG".equalsIgnoreCase(pong), computeLatency(start));
        } catch (Exception e) {
            log.warn("Redis connectivity check failed", e);
            return new RedisPingResult(false, computeLatency(start));
        }
    }

    private long computeLatency(long startNanos) {
        long duration = Math.max(0, getCurrentTimeNanos() - startNanos);
        return TimeUnit.NANOSECONDS.toMillis(duration);
    }

    private Map<String, Object> buildNotifyStats() {
        Map<String, Object> notifyStats = new HashMap<>();
        Map<String, Object> successRate = notifyRecordMapper.getSuccessRate();
        long weekTotal = toLong(successRate == null ? null : successRate.get("total"));
        long weekSuccess = toLong(successRate == null ? null : successRate.get("success"));
        long weekFailed = toLong(successRate == null ? null : successRate.get("failed"));

        notifyStats.put("successRate", successRate == null ? 100 : successRate.getOrDefault("successRate", 100));
        notifyStats.put("todayCount", notifyRecordMapper.countTodaySends());
        notifyStats.put("weekTotal", weekTotal);
        notifyStats.put("weekSuccess", weekSuccess);
        notifyStats.put("weekFailed", weekFailed);
        return notifyStats;
    }

    private Map<String, Object> buildRuntimeOverviewSnapshot() {
        Map<String, Object> runtimeOverview = createDefaultRuntimeOverviewSnapshot();
        runtimeOverview.put("eventCount", defaultLong(tradeRuntimeOverviewMapper.countEventRaws()));
        runtimeOverview.put("signalCount", defaultLong(tradeRuntimeOverviewMapper.countSignalEvents()));
        runtimeOverview.put("decisionCount", defaultLong(tradeRuntimeOverviewMapper.countDecisionRuns()));
        runtimeOverview.put("riskHitCount", defaultLong(tradeRuntimeOverviewMapper.countRiskGuardHits()));
        runtimeOverview.put("activePositionCount", defaultLong(tradeRuntimeOverviewMapper.countActivePositions()));
        runtimeOverview.put("totalUnrealizedPnl", defaultDecimal(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()));
        runtimeOverview.put("latestPnlSnapshot", tradeRuntimeOverviewMapper.selectLatestPnlSnapshot());
        runtimeOverview.put("recentEvents", defaultList(tradeRuntimeOverviewMapper.selectRecentEventRaws(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("recentSignals", defaultList(tradeRuntimeOverviewMapper.selectRecentSignalEvents(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("recentAgentConclusions", defaultList(tradeRuntimeOverviewMapper.selectRecentAgentConclusions(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("recentDecisions", defaultList(tradeRuntimeOverviewMapper.selectRecentDecisionRuns(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("recentRiskHits", defaultList(tradeRuntimeOverviewMapper.selectRecentRiskGuardHits(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("recentOrders", defaultList(tradeRuntimeOverviewMapper.selectRecentExchangeOrders(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("recentFills", defaultList(tradeRuntimeOverviewMapper.selectRecentExchangeFills(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("recentPositions", defaultList(tradeRuntimeOverviewMapper.selectRecentPositionSnapshots(RUNTIME_RECENT_LIMIT)));
        runtimeOverview.put("executionStats", buildExecutionStats());
        return runtimeOverview;
    }

    private Map<String, Object> createDefaultRuntimeOverviewSnapshot() {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("eventCount", 0L);
        snapshot.put("signalCount", 0L);
        snapshot.put("decisionCount", 0L);
        snapshot.put("riskHitCount", 0L);
        snapshot.put("activePositionCount", 0L);
        snapshot.put("totalUnrealizedPnl", BigDecimal.ZERO);
        snapshot.put("latestPnlSnapshot", null);
        snapshot.put("recentEvents", Collections.emptyList());
        snapshot.put("recentSignals", Collections.emptyList());
        snapshot.put("recentAgentConclusions", Collections.emptyList());
        snapshot.put("recentDecisions", Collections.emptyList());
        snapshot.put("recentRiskHits", Collections.emptyList());
        snapshot.put("recentOrders", Collections.emptyList());
        snapshot.put("recentFills", Collections.emptyList());
        snapshot.put("recentPositions", Collections.emptyList());
        snapshot.put("executionStats", createDefaultExecutionStats());
        return snapshot;
    }

    private Map<String, Object> buildRiskStats(Map<String, Object> runtimeOverview) {
        Map<String, Object> riskStats = new HashMap<>();
        long todayBlocks = toLong(runtimeOverview.get("riskHitCount"));
        long decisionCount = toLong(runtimeOverview.get("decisionCount"));
        double blockRate = decisionCount == 0 ? 0D : (todayBlocks * 100.0D) / decisionCount;
        riskStats.put("todayBlocks", todayBlocks);
        riskStats.put("blockRate", blockRate);
        return riskStats;
    }

    private Map<String, Object> buildExecutionStats() {
        Map<String, Object> executionStats = createDefaultExecutionStats();
        List<Map<String, Object>> rows = tradeExecutionMapper.selectExecutionStatusCounts();
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

    private void applyWorkerTaskCounters(Map<String, Object> workerStatus, String workerId) {
        Map<String, TaskDTO> taskStatusMap = redisCache.getCacheMap(TASK_STATUS_CACHE_KEY);
        if (taskStatusMap == null || taskStatusMap.isEmpty()) {
            return;
        }

        int totalTasks = 0;
        int successTasks = 0;
        int failedTasks = 0;
        for (TaskDTO task : taskStatusMap.values()) {
            if (task == null || !workerId.equals(task.getWorkerId())) {
                continue;
            }
            totalTasks++;
            String status = task.getStatus();
            if (status == null) {
                continue;
            }
            String normalizedStatus = status.trim().toLowerCase(Locale.ROOT);
            if ("completed".equals(normalizedStatus) || "success".equals(normalizedStatus) || "succeeded".equals(normalizedStatus)) {
                successTasks++;
            } else if ("failed".equals(normalizedStatus) || "error".equals(normalizedStatus)) {
                failedTasks++;
            }
        }

        workerStatus.put("totalTasks", totalTasks);
        workerStatus.put("successTasks", successTasks);
        workerStatus.put("failedTasks", failedTasks);
    }

    private Map<String, Object> createDefaultExecutionStats() {
        Map<String, Object> executionStats = new LinkedHashMap<>();
        executionStats.put("total", 0L);
        executionStats.put("filled", 0L);
        executionStats.put("pending", 0L);
        executionStats.put("partial", 0L);
        executionStats.put("canceled", 0L);
        executionStats.put("expired", 0L);
        executionStats.put("failed", 0L);
        executionStats.put("blocked", 0L);
        executionStats.put("skipped", 0L);
        return executionStats;
    }

    private Map<String, Object> buildSystemStatus(RedisPingResult redisStatus, Map<String, Object> workerStatus) {
        Map<String, Object> systemStatus = createDefaultSystemStatus();
        systemStatus.put("workerOnline", workerStatus.getOrDefault("online", false));
        systemStatus.put("redisConnected", redisStatus.isConnected());
        systemStatus.put("queueLength", workerStatus.getOrDefault("queueLength", 0));
        systemStatus.put("apiLatency", redisStatus.getLatencyMillis());
        return systemStatus;
    }

    private Map<String, Object> createDefaultWorkerStatus() {
        Map<String, Object> workerStatus = new HashMap<>();
        workerStatus.put("online", false);
        workerStatus.put("workerId", null);
        workerStatus.put("workerType", "Python Worker");
        workerStatus.put("pid", null);
        workerStatus.put("host", "localhost");
        workerStatus.put("totalTasks", 0);
        workerStatus.put("successTasks", 0);
        workerStatus.put("failedTasks", 0);
        workerStatus.put("queueLength", 0);
        workerStatus.put("lastHeartbeat", null);
        return workerStatus;
    }

    private Map<String, Object> createDefaultSystemStatus() {
        Map<String, Object> systemStatus = new HashMap<>();
        systemStatus.put("workerOnline", false);
        systemStatus.put("redisConnected", false);
        systemStatus.put("dbConnected", true);
        systemStatus.put("queueLength", 0);
        systemStatus.put("apiLatency", 0L);
        return systemStatus;
    }

    private Map<String, Object> buildDefaultNotifyStats() {
        Map<String, Object> notifyStats = new HashMap<>();
        notifyStats.put("successRate", 100);
        notifyStats.put("todayCount", 0);
        notifyStats.put("weekTotal", 0L);
        notifyStats.put("weekSuccess", 0L);
        notifyStats.put("weekFailed", 0L);
        return notifyStats;
    }

    private Map<String, Object> buildDefaultRiskStats() {
        Map<String, Object> riskStats = new HashMap<>();
        riskStats.put("todayBlocks", 0L);
        riskStats.put("blockRate", 0D);
        return riskStats;
    }

    private Map<String, Object> createRetiredProfitLossCurve() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dates", Collections.emptyList());
        result.put("invested", Collections.emptyList());
        result.put("value", Collections.emptyList());
        result.put("profit", Collections.emptyList());
        result.put("profitRate", Collections.emptyList());
        return result;
    }

    private Map<String, Object> createRetiredAiConsumptionSnapshot() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dates", Collections.emptyList());
        result.put("dailyTokens", Collections.emptyList());
        result.put("dailyCost", Collections.emptyList());
        result.put("dailyCount", Collections.emptyList());
        result.put("totalTokens", 0);
        result.put("totalCost", BigDecimal.ZERO);
        result.put("modelTokens", Collections.emptyMap());
        result.put("modelCount", Collections.emptyMap());
        result.put("totalCalls", 0);
        result.put("todayTokens", 0);
        result.put("todayCalls", 0);
        return result;
    }

    private Map<String, Object> createRetiredTriggerTrend() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dates", Collections.emptyList());
        result.put("dcaDay", Collections.emptyList());
        result.put("bigDrop", Collections.emptyList());
        result.put("bigRise", Collections.emptyList());
        return result;
    }

    private Map<String, Object> createRetiredTradeVolume() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dates", Collections.emptyList());
        result.put("volumes", Collections.emptyList());
        result.put("counts", Collections.emptyList());
        return result;
    }

    private Map<String, Object> createRetiredProfitRate() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("symbols", Collections.emptyList());
        result.put("profitRates", Collections.emptyList());
        result.put("overallRate", BigDecimal.ZERO);
        return result;
    }

    private Map<String, Object> createRetiredPriceTrend(String symbol) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dates", Collections.emptyList());
        result.put("prices", Collections.emptyList());
        result.put("symbol", symbol);
        result.put("currentPrice", BigDecimal.ZERO);
        return result;
    }

    private String normalizeExecutionStatus(Object rawStatus) {
        if (rawStatus == null) {
            return "pending";
        }
        String status = rawStatus.toString().trim().toLowerCase(Locale.ROOT);
        switch (status) {
            case "filled":
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

    private long defaultLong(Long value) {
        return value == null ? 0L : value;
    }

    private BigDecimal defaultDecimal(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value;
    }

    private <T> List<T> defaultList(List<T> rows) {
        return rows == null ? Collections.emptyList() : rows;
    }

    private long toLong(Object value) {
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

    public long getCurrentTimeNanos() {
        return System.nanoTime();
    }

    private Long parseHeartbeat(String rawHeartbeat) {
        if (rawHeartbeat == null || rawHeartbeat.isBlank()) {
            return null;
        }
        try {
            long heartbeat = Long.parseLong(rawHeartbeat.trim());
            return heartbeat < 1_000_000_000_000L ? heartbeat * 1000 : heartbeat;
        } catch (NumberFormatException e) {
            log.warn("Failed to parse worker heartbeat: {}", rawHeartbeat);
            return null;
        }
    }

    private String formatHeartbeat(Long heartbeatMillis) {
        if (heartbeatMillis == null) {
            return null;
        }
        try {
            return Instant.ofEpochMilli(heartbeatMillis)
                .atZone(TradeRuntimeTimeUtils.DATABASE_ZONE)
                .toLocalDateTime()
                .format(DATE_FORMATTER);
        } catch (Exception e) {
            log.warn("Failed to format worker heartbeat: {}", heartbeatMillis, e);
            return null;
        }
    }

    private static final class RedisPingResult {
        private final boolean connected;
        private final long latencyMillis;

        private RedisPingResult(boolean connected, long latencyMillis) {
            this.connected = connected;
            this.latencyMillis = latencyMillis;
        }

        public boolean isConnected() {
            return connected;
        }

        public long getLatencyMillis() {
            return latencyMillis;
        }
    }
}
