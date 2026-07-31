package com.ruoyi.dca.trade.service;

import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.domain.trade.TradeRuntimeBootstrap;
import com.ruoyi.dca.domain.trade.TradeRuntimeOverview;
import com.ruoyi.dca.domain.trade.TradeActionSummary;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.mapper.trade.TradeRuntimeOverviewMapper;
import com.ruoyi.dca.service.trade.ITradeRuntimeConfigService;
import com.ruoyi.dca.service.trade.impl.TradeRuntimeOverviewServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeRuntimeOverviewServiceImplTest {

    @Mock
    private ITradeRuntimeConfigService runtimeConfigService;

    @Mock
    private TradeRuntimeOverviewMapper tradeRuntimeOverviewMapper;

    @InjectMocks
    private TradeRuntimeOverviewServiceImpl tradeRuntimeOverviewService;

    @Test
    void getOverviewBuildsExecutionStatsWithTotal() {
        DecisionRun latestDecisionRun = new DecisionRun();
        latestDecisionRun.setDispatchMode("RULE_ONLY");
        latestDecisionRun.setTriggerReason("budget_blocked");
        latestDecisionRun.setTriggerSource("news");
        latestDecisionRun.setSelectedAgentsJson("[\"news_agent\",\"market_agent\"]");
        latestDecisionRun.setCombinationMatchJson("{\"code\":\"strong_news_then_break\"}");

        SignalWindowState signalWindowState = new SignalWindowState();
        signalWindowState.setWindowKey("news:BTCUSDT:15m");
        signalWindowState.setSourceType("news");
        signalWindowState.setSymbol("BTCUSDT");

        when(runtimeConfigService.getCurrentConfig()).thenReturn(new TradeRuntimeConfig());
        when(tradeRuntimeOverviewMapper.countEventRaws()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countSignalEvents()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countRiskGuardHits()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countActivePositions()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()).thenReturn(BigDecimal.ZERO);
        when(tradeRuntimeOverviewMapper.selectLatestPnlSnapshot()).thenReturn(null);
        when(tradeRuntimeOverviewMapper.selectLatestDecisionRun()).thenReturn(latestDecisionRun);
        when(tradeRuntimeOverviewMapper.countCooldownBlockedDecisionRuns()).thenReturn(2L);
        when(tradeRuntimeOverviewMapper.countBudgetBlockedDecisionRuns()).thenReturn(3L);
        when(tradeRuntimeOverviewMapper.selectRecentEventRaws(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentSignalEvents(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectActiveSignalWindows(eq(5), anyString())).thenReturn(List.of(signalWindowState));
        when(tradeRuntimeOverviewMapper.selectRecentAgentConclusions(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentDecisionRuns(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentRiskGuardHits(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeFills(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentTradeActionSummaries(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeOrders(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentPositionSnapshots(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectExecutionStatusCounts()).thenReturn(List.of(
            Map.of("executionStatus", "filled", "total", 3L),
            Map.of("executionStatus", "submitted", "total", 1L),
            Map.of("executionStatus", "partial", "total", 1L),
            Map.of("executionStatus", "blocked", "total", 1L),
            Map.of("executionStatus", "skipped", "total", 1L),
            Map.of("executionStatus", "failed", "total", 1L)
        ));

        TradeRuntimeOverview overview = tradeRuntimeOverviewService.getOverview();

        assertThat(overview.getExecutionStats())
            .containsEntry("total", 8L)
            .containsEntry("filled", 3L)
            .containsEntry("submitted", 1L)
            .containsEntry("partial", 1L)
            .containsEntry("failed", 1L)
            .containsEntry("blocked", 1L)
            .containsEntry("skipped", 1L)
            .containsEntry("pending", 0L)
            .containsEntry("canceled", 0L)
            .containsEntry("expired", 0L);
        assertThat(overview.getLatestDispatchMode()).isEqualTo("RULE_ONLY");
        assertThat(overview.getLastTriggerReason()).isEqualTo("budget_blocked");
        assertThat(overview.getLastTriggerSource()).isEqualTo("news");
        assertThat(overview.getCooldownSuppressionCount()).isEqualTo(2L);
        assertThat(overview.getBudgetSuppressionCount()).isEqualTo(3L);
        assertThat(overview.getLastSelectedAgentsJson()).isEqualTo("[\"news_agent\",\"market_agent\"]");
        assertThat(overview.getLastCombinationMatchJson()).isEqualTo("{\"code\":\"strong_news_then_break\"}");
        assertThat(overview.getActiveSignalWindows()).hasSize(1);
        assertThat(overview.getActiveSignalWindows().get(0).getWindowKey()).isEqualTo("news:BTCUSDT:15m");
        assertThat(overview.getRecentFills()).isEmpty();
    }

    @Test
    void getOverviewPrefersResolvedBootstrapRuntimeConfigWhenAvailable() {
        TradeRuntimeConfig currentConfig = new TradeRuntimeConfig();
        currentConfig.setMaxPositionRatio(new BigDecimal("0.10"));

        TradeRuntimeConfig resolvedConfig = new TradeRuntimeConfig();
        resolvedConfig.setMaxPositionRatio(new BigDecimal("1.00"));

        TradeRuntimeBootstrap bootstrap = new TradeRuntimeBootstrap();
        bootstrap.setRuntimeConfig(resolvedConfig);

        when(runtimeConfigService.getCurrentConfig()).thenReturn(currentConfig);
        when(runtimeConfigService.listBootstrapConfigs()).thenReturn(List.of(bootstrap));
        when(tradeRuntimeOverviewMapper.countEventRaws()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countSignalEvents()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countRiskGuardHits()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countActivePositions()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()).thenReturn(BigDecimal.ZERO);
        when(tradeRuntimeOverviewMapper.selectLatestPnlSnapshot()).thenReturn(null);
        when(tradeRuntimeOverviewMapper.selectLatestDecisionRun()).thenReturn(null);
        when(tradeRuntimeOverviewMapper.countCooldownBlockedDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countBudgetBlockedDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.selectRecentEventRaws(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentSignalEvents(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectActiveSignalWindows(eq(5), anyString())).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentAgentConclusions(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentDecisionRuns(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentRiskGuardHits(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeFills(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentTradeActionSummaries(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeOrders(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentPositionSnapshots(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectExecutionStatusCounts()).thenReturn(List.of());

        TradeRuntimeOverview overview = tradeRuntimeOverviewService.getOverview();

        assertThat(overview.getRuntimeConfig().getMaxPositionRatio()).isEqualByComparingTo("1.00");
    }

    @Test
    void getOverviewResetsStaleDailyPnlFromPreviousUtcDay() {
        PnlSnapshot latestPnlSnapshot = new PnlSnapshot();
        latestPnlSnapshot.setAccountEquity(new BigDecimal("12500.50"));
        latestPnlSnapshot.setDailyPnl(new BigDecimal("235.10"));
        latestPnlSnapshot.setMaxDrawdownPct(new BigDecimal("4.25"));
        latestPnlSnapshot.setCreatedAt("2000-01-01 23:59:59");

        when(runtimeConfigService.getCurrentConfig()).thenReturn(new TradeRuntimeConfig());
        when(runtimeConfigService.listBootstrapConfigs()).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.countEventRaws()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countSignalEvents()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countRiskGuardHits()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countActivePositions()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()).thenReturn(BigDecimal.ZERO);
        when(tradeRuntimeOverviewMapper.selectLatestPnlSnapshot()).thenReturn(latestPnlSnapshot);
        when(tradeRuntimeOverviewMapper.selectLatestDecisionRun()).thenReturn(null);
        when(tradeRuntimeOverviewMapper.countCooldownBlockedDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countBudgetBlockedDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.selectRecentEventRaws(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentSignalEvents(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectActiveSignalWindows(eq(5), anyString())).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentAgentConclusions(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentDecisionRuns(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentRiskGuardHits(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeFills(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentTradeActionSummaries(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeOrders(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentPositionSnapshots(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectExecutionStatusCounts()).thenReturn(List.of());

        TradeRuntimeOverview overview = tradeRuntimeOverviewService.getOverview();

        assertThat(overview.getLatestPnlSnapshot()).isEqualTo(latestPnlSnapshot);
        assertThat(overview.getLatestDailyPnl()).isEqualByComparingTo("0");
        assertThat(overview.getMaxDrawdownPct()).isEqualByComparingTo("4.25");
    }

    @Test
    void getOverviewReconcilesLatestDailyPnlAndMaxDrawdownFromPostSnapshotTrades() {
        String currentUtcDay = LocalDate.now(ZoneOffset.UTC).toString();
        PnlSnapshot latestPnlSnapshot = new PnlSnapshot();
        latestPnlSnapshot.setAccountEquity(new BigDecimal("10003.81733931"));
        latestPnlSnapshot.setDailyPnl(new BigDecimal("3.81733931"));
        latestPnlSnapshot.setMaxDrawdownPct(new BigDecimal("0.0849"));
        latestPnlSnapshot.setPeakAccountEquity(new BigDecimal("10003.81733931"));
        latestPnlSnapshot.setCreatedAt(currentUtcDay + " 08:00:00");

        TradeActionSummary guardClose = new TradeActionSummary();
        guardClose.setRealizedPnl(new BigDecimal("10.93732274"));
        guardClose.setCreatedAt(currentUtcDay + " 09:10:14");

        when(runtimeConfigService.getCurrentConfig()).thenReturn(new TradeRuntimeConfig());
        when(runtimeConfigService.listBootstrapConfigs()).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.countEventRaws()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countSignalEvents()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countRiskGuardHits()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countActivePositions()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()).thenReturn(BigDecimal.ZERO);
        when(tradeRuntimeOverviewMapper.selectLatestPnlSnapshot()).thenReturn(latestPnlSnapshot);
        when(tradeRuntimeOverviewMapper.selectLatestDecisionRun()).thenReturn(null);
        when(tradeRuntimeOverviewMapper.countCooldownBlockedDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.countBudgetBlockedDecisionRuns()).thenReturn(0L);
        when(tradeRuntimeOverviewMapper.selectRecentEventRaws(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentSignalEvents(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectActiveSignalWindows(eq(5), anyString())).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentAgentConclusions(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentDecisionRuns(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentRiskGuardHits(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeFills(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentTradeActionSummaries(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentExchangeOrders(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectRecentPositionSnapshots(5)).thenReturn(List.of());
        when(tradeRuntimeOverviewMapper.selectTradeActionSummariesAfter(currentUtcDay + " 08:00:00")).thenReturn(List.of(guardClose));
        when(tradeRuntimeOverviewMapper.selectExecutionStatusCounts()).thenReturn(List.of());

        TradeRuntimeOverview overview = tradeRuntimeOverviewService.getOverview();

        assertThat(overview.getLatestDailyPnl()).isEqualByComparingTo("14.75466205");
        assertThat(overview.getMaxDrawdownPct()).isEqualByComparingTo("0.0849");
        assertThat(overview.getLatestPnlSnapshot().getAccountEquity()).isEqualByComparingTo("10014.75466205");
    }
}
