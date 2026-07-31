package com.ruoyi.dca.runtime;

import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.FeatureSnapshot;
import com.ruoyi.dca.domain.dto.TaskDTO;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.replay.PaperTradeOrder;
import com.ruoyi.dca.domain.replay.ReplayComparison;
import com.ruoyi.dca.domain.replay.ReplaySession;
import com.ruoyi.dca.domain.replay.ShadowDecisionLog;
import com.ruoyi.dca.domain.replay.TraceAuditDetail;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.mapper.decision.DecisionAuditMapper;
import com.ruoyi.dca.mapper.runtime.TradeReplayMapper;
import com.ruoyi.dca.service.ITaskQueueService;
import com.ruoyi.dca.service.runtime.impl.TradeReplayServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeReplayServiceImplTest {

    @Mock
    private TradeReplayMapper tradeReplayMapper;

    @Mock
    private ITaskQueueService taskQueueService;

    @Mock
    private DecisionAuditMapper decisionAuditMapper;

    @InjectMocks
    private TradeReplayServiceImpl tradeReplayService;

    @Test
    void recordReplaySessionBackfillsReplayTraceIdWhenMissing() {
        ReplaySession session = new ReplaySession();
        session.setSessionName("replay-trace-source-1");
        session.setSourceTraceId("trace-source-1");

        tradeReplayService.recordReplaySession(session);

        ArgumentCaptor<ReplaySession> captor = ArgumentCaptor.forClass(ReplaySession.class);
        verify(tradeReplayMapper).insertReplaySession(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("running");
        assertThat(captor.getValue().getReplayTraceId()).matches("^[a-f0-9]{32}$");
    }

    @Test
    void dispatchReplayCreatesReplayTraceIdAndQueuesReplayTask() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-source-1");
        eventRaw.setEventType("news");
        eventRaw.setSymbol("BTCUSDT");
        eventRaw.setExchangeCode("binance");
        eventRaw.setPayloadJson("{\"event_type\":\"news\",\"headline\":\"ETF inflow\"}");
        when(tradeReplayMapper.selectEventRawsByTraceId("trace-source-1")).thenReturn(java.util.List.of(eventRaw));
        when(tradeReplayMapper.selectSignalEventsByTraceId("trace-source-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectDecisionRunByTraceId("trace-source-1")).thenReturn(null);
        when(tradeReplayMapper.selectLatestExchangeOrderByTraceId("trace-source-1")).thenReturn(null);
        doAnswer(invocation -> {
            ReplaySession session = invocation.getArgument(0);
            session.setId(18L);
            return null;
        }).when(tradeReplayMapper).insertReplaySession(org.mockito.ArgumentMatchers.any(ReplaySession.class));

        ReplaySession session = tradeReplayService.dispatchReplay("trace-source-1");

        ArgumentCaptor<ReplaySession> sessionCaptor = ArgumentCaptor.forClass(ReplaySession.class);
        verify(tradeReplayMapper).insertReplaySession(sessionCaptor.capture());
        assertThat(session.getId()).isEqualTo(18L);
        assertThat(sessionCaptor.getValue().getSourceTraceId()).isEqualTo("trace-source-1");
        assertThat(sessionCaptor.getValue().getStatus()).isEqualTo("queued");
        assertThat(sessionCaptor.getValue().getReplayTraceId()).matches("^[a-f0-9]{32}$");

        ArgumentCaptor<TaskDTO> taskCaptor = ArgumentCaptor.forClass(TaskDTO.class);
        verify(taskQueueService).pushPriorityTask(taskCaptor.capture());
        assertThat(taskCaptor.getValue().getTaskType()).isEqualTo("TRADE_RUNTIME_REPLAY");
        assertThat(taskCaptor.getValue().getTaskData()).containsEntry("sessionId", 18L);
        assertThat(taskCaptor.getValue().getTaskData()).containsEntry("sourceTraceId", "trace-source-1");
    }

    @Test
    void recordPaperTradeOrderBackfillsExecutionStatusFromOrderStatus() {
        PaperTradeOrder order = new PaperTradeOrder();
        order.setTraceId("trace-paper-1");
        order.setExchangeCode("binance");
        order.setSymbol("BTCUSDT");
        order.setSide("BUY");
        order.setMode("paper");
        order.setOrderRef("paper-BTCUSDT");
        order.setOrderStatus("PARTIALLY_FILLED");

        tradeReplayService.recordPaperTradeOrder(order);

        ArgumentCaptor<PaperTradeOrder> captor = ArgumentCaptor.forClass(PaperTradeOrder.class);
        verify(tradeReplayMapper).insertPaperTradeOrder(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("partial");
        assertThat(captor.getValue().getExecutionStatus()).isEqualTo("partial");
        assertThat(captor.getValue().getOrderStatus()).isEqualTo("PARTIALLY_FILLED");
    }

    @Test
    void recordPaperTradeOrderBackfillsOrderStatusFromExecutionStatusAlias() {
        PaperTradeOrder order = new PaperTradeOrder();
        order.setTraceId("trace-paper-2");
        order.setExchangeCode("okx");
        order.setSymbol("ETHUSDT");
        order.setSide("SELL");
        order.setMode("paper");
        order.setOrderRef("paper-ETHUSDT");
        order.setExecutionStatus("submitted");

        tradeReplayService.recordPaperTradeOrder(order);

        ArgumentCaptor<PaperTradeOrder> captor = ArgumentCaptor.forClass(PaperTradeOrder.class);
        verify(tradeReplayMapper).insertPaperTradeOrder(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("submitted");
        assertThat(captor.getValue().getExecutionStatus()).isEqualTo("submitted");
        assertThat(captor.getValue().getOrderStatus()).isEqualTo("SUBMITTED");
    }

    @Test
    void recordShadowDecisionLogBackfillsExecutionStatusPair() {
        ShadowDecisionLog log = new ShadowDecisionLog();
        log.setTraceId("trace-shadow-1");
        log.setExchangeCode("okx");
        log.setSymbol("ETHUSDT");
        log.setMode("shadow");
        log.setAction("OPEN_LONG");
        log.setSide("long");
        log.setOrderStatus("PENDING");

        tradeReplayService.recordShadowDecisionLog(log);

        ArgumentCaptor<ShadowDecisionLog> captor = ArgumentCaptor.forClass(ShadowDecisionLog.class);
        verify(tradeReplayMapper).insertShadowDecisionLog(captor.capture());
        assertThat(captor.getValue().getExecutionStatus()).isEqualTo("pending");
        assertThat(captor.getValue().getOrderStatus()).isEqualTo("PENDING");
    }

    @Test
    void getReplayComparisonCarriesPromptAndModelMetadataForOriginalAndReplaySides() {
        ReplaySession session = new ReplaySession();
        session.setId(12L);
        session.setSourceTraceId("trace-source-1");
        session.setReplayTraceId("trace-replay-1");

        DecisionRun originalDecision = new DecisionRun();
        originalDecision.setTraceId("trace-source-1");
        originalDecision.setAction("OPEN_LONG");
        originalDecision.setModelCode("gpt-4.1");
        originalDecision.setModelProvider("openai");
        originalDecision.setPromptSource("template");
        originalDecision.setBindingTemplateCode("trade.supervisor.v1");
        originalDecision.setResolvedTemplateCode("trade.supervisor.v1");
        originalDecision.setPromptTemplateFallbackUsed(Boolean.FALSE);
        originalDecision.setExecutionStatus("filled");
        originalDecision.setOrderStatus("FILLED");

        ShadowDecisionLog replayDecision = new ShadowDecisionLog();
        replayDecision.setTraceId("trace-replay-1");
        replayDecision.setAction("OPEN_LONG");
        replayDecision.setModelCode("gpt-4.1-mini");
        replayDecision.setModelProvider("openai");
        replayDecision.setPromptSource("inline");
        replayDecision.setBindingTemplateCode("trade.supervisor.v1");
        replayDecision.setResolvedTemplateCode("");
        replayDecision.setPromptTemplateFallbackUsed(Boolean.TRUE);
        replayDecision.setExecutionStatus("pending");
        replayDecision.setOrderStatus("PENDING");

        ExchangeOrder originalOrder = new ExchangeOrder();
        originalOrder.setTraceId("trace-source-1");
        originalOrder.setOrderStatus("FILLED");
        ExchangeOrder replayOrder = new ExchangeOrder();
        replayOrder.setTraceId("trace-replay-1");
        replayOrder.setOrderStatus("PENDING");

        when(tradeReplayMapper.selectReplaySessionById(12L)).thenReturn(session);
        when(tradeReplayMapper.selectDecisionRunByTraceId("trace-source-1")).thenReturn(originalDecision);
        when(tradeReplayMapper.selectLatestShadowDecisionLogByTraceId("trace-replay-1")).thenReturn(replayDecision);
        when(tradeReplayMapper.selectLatestExchangeOrderByTraceId("trace-source-1")).thenReturn(originalOrder);
        when(tradeReplayMapper.selectLatestExchangeOrderByTraceId("trace-replay-1")).thenReturn(replayOrder);
        when(tradeReplayMapper.selectRiskGuardHitsByTraceId("trace-source-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectRiskGuardHitsByTraceId("trace-replay-1")).thenReturn(java.util.List.of());

        ReplayComparison comparison = tradeReplayService.getReplayComparison(12L);

        assertThat(comparison.getOriginalDecision()).containsEntry("modelCode", "gpt-4.1");
        assertThat(comparison.getOriginalDecision()).containsEntry("promptSource", "template");
        assertThat(comparison.getOriginalDecision()).containsEntry("bindingTemplateCode", "trade.supervisor.v1");
        assertThat(comparison.getOriginalDecision()).containsEntry("resolvedTemplateCode", "trade.supervisor.v1");
        assertThat(comparison.getOriginalDecision()).containsEntry("promptTemplateFallbackUsed", false);
        assertThat(comparison.getReplayDecision()).containsEntry("modelCode", "gpt-4.1-mini");
        assertThat(comparison.getReplayDecision()).containsEntry("modelProvider", "openai");
        assertThat(comparison.getReplayDecision()).containsEntry("promptSource", "inline");
        assertThat(comparison.getReplayDecision()).containsEntry("bindingTemplateCode", "trade.supervisor.v1");
        assertThat(comparison.getReplayDecision()).containsEntry("resolvedTemplateCode", "");
        assertThat(comparison.getReplayDecision()).containsEntry("promptTemplateFallbackUsed", true);
    }

    @Test
    void getReplayComparisonCarriesRiskGuardHitsForOriginalAndReplaySides() {
        ReplaySession session = new ReplaySession();
        session.setId(18L);
        session.setSourceTraceId("trace-source-risk");
        session.setReplayTraceId("trace-replay-risk");

        RiskGuardHit originalHit = new RiskGuardHit();
        originalHit.setTraceId("trace-source-risk");
        originalHit.setRuleCode("max_position_ratio");
        originalHit.setReason("requested notional too large");

        RiskGuardHit replayHit = new RiskGuardHit();
        replayHit.setTraceId("trace-replay-risk");
        replayHit.setRuleCode("live_account_unhealthy");
        replayHit.setReason("live account is degraded");

        when(tradeReplayMapper.selectReplaySessionById(18L)).thenReturn(session);
        when(tradeReplayMapper.selectDecisionRunByTraceId("trace-source-risk")).thenReturn(new DecisionRun());
        when(tradeReplayMapper.selectLatestShadowDecisionLogByTraceId("trace-replay-risk")).thenReturn(new ShadowDecisionLog());
        when(tradeReplayMapper.selectLatestExchangeOrderByTraceId("trace-source-risk")).thenReturn(null);
        when(tradeReplayMapper.selectLatestExchangeOrderByTraceId("trace-replay-risk")).thenReturn(null);
        when(tradeReplayMapper.selectRiskGuardHitsByTraceId("trace-source-risk")).thenReturn(java.util.List.of(originalHit));
        when(tradeReplayMapper.selectRiskGuardHitsByTraceId("trace-replay-risk")).thenReturn(java.util.List.of(replayHit));

        ReplayComparison comparison = tradeReplayService.getReplayComparison(18L);

        assertThat(comparison.getOriginalRiskHits()).hasSize(1);
        assertThat(comparison.getOriginalRiskHits().get(0).getRuleCode()).isEqualTo("max_position_ratio");
        assertThat(comparison.getReplayRiskHits()).hasSize(1);
        assertThat(comparison.getReplayRiskHits().get(0).getRuleCode()).isEqualTo("live_account_unhealthy");
    }

    @Test
    void getTraceAuditDetailCarriesTradeSummary() {
        com.ruoyi.dca.domain.trade.TradeActionSummary summary = new com.ruoyi.dca.domain.trade.TradeActionSummary();
        summary.setTraceId("trace-short-close-1");
        summary.setAction("CLOSE");
        summary.setOpenPrice(new java.math.BigDecimal("2371.05000000"));
        summary.setClosePrice(new java.math.BigDecimal("2362.05000000"));
        summary.setRealizedPnl(new java.math.BigDecimal("13.50000000"));

        when(tradeReplayMapper.selectEventRawsByTraceId("trace-short-close-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectDecisionRunByTraceId("trace-short-close-1")).thenReturn(null);
        when(tradeReplayMapper.selectLatestExchangeOrderByTraceId("trace-short-close-1")).thenReturn(null);
        when(tradeReplayMapper.selectExchangeFillsByTraceId("trace-short-close-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectRiskGuardHitsByTraceId("trace-short-close-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectLatestPositionSnapshotByTraceId("trace-short-close-1")).thenReturn(null);
        when(tradeReplayMapper.selectLatestPnlSnapshotByTraceId("trace-short-close-1")).thenReturn(null);
        when(tradeReplayMapper.selectNotifyRecordsByTraceId("trace-short-close-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectTradeActionSummaryByTraceId("trace-short-close-1")).thenReturn(summary);

        TraceAuditDetail detail = tradeReplayService.getTraceAuditDetail("trace-short-close-1");

        assertThat(detail.getTradeSummary()).isNotNull();
        assertThat(detail.getTradeSummary().getOpenPrice()).isEqualByComparingTo("2371.05000000");
        assertThat(detail.getTradeSummary().getClosePrice()).isEqualByComparingTo("2362.05000000");
        assertThat(detail.getTradeSummary().getRealizedPnl()).isEqualByComparingTo("13.50000000");
    }

    @Test
    void getTraceAuditDetailHydratesTradeMemoryOutcomeFromFeatureSnapshot() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-memory-detail-1");
        decisionRun.setSymbol("ETHUSDT");
        decisionRun.setAction("CLOSE");

        FeatureSnapshot featureSnapshot = new FeatureSnapshot();
        featureSnapshot.setTraceId("trace-memory-detail-1");
        featureSnapshot.setSnapshotJson(
            """
            {"tradeMemoryStatus":{"status":"stored","reason":"","trace_id":"trace-memory-detail-1","lesson_text":"Only close after reclaim confirmation."},"lifecycleStatus":{"status":"recorded","operation":"exit","trace_id":"trace-memory-detail-1","memory_status":"stored","memory_reason":"","memory":{"lesson_text":"Only close after reclaim confirmation."}}}
            """
        );

        when(tradeReplayMapper.selectEventRawsByTraceId("trace-memory-detail-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectDecisionRunByTraceId("trace-memory-detail-1")).thenReturn(decisionRun);
        when(tradeReplayMapper.selectLatestExchangeOrderByTraceId("trace-memory-detail-1")).thenReturn(null);
        when(tradeReplayMapper.selectExchangeFillsByTraceId("trace-memory-detail-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectRiskGuardHitsByTraceId("trace-memory-detail-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectLatestPositionSnapshotByTraceId("trace-memory-detail-1")).thenReturn(null);
        when(tradeReplayMapper.selectLatestPnlSnapshotByTraceId("trace-memory-detail-1")).thenReturn(null);
        when(tradeReplayMapper.selectNotifyRecordsByTraceId("trace-memory-detail-1")).thenReturn(java.util.List.of());
        when(tradeReplayMapper.selectTradeActionSummaryByTraceId("trace-memory-detail-1")).thenReturn(null);
        when(decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(java.util.List.of("trace-memory-detail-1")))
            .thenReturn(java.util.List.of(featureSnapshot));

        TraceAuditDetail detail = tradeReplayService.getTraceAuditDetail("trace-memory-detail-1");

        assertThat(detail.getDecision()).isNotNull();
        assertThat(detail.getDecision().getTradeMemoryStatus()).containsEntry("status", "stored");
        assertThat(detail.getDecision().getTradeMemoryStatus()).containsEntry("lesson_text", "Only close after reclaim confirmation.");
        assertThat(detail.getDecision().getLifecycleStatus()).containsEntry("memory_status", "stored");
    }
}
