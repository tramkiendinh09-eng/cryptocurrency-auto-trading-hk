package com.ruoyi.dca.decision;

import com.ruoyi.dca.domain.decision.AgentConclusion;
import com.ruoyi.dca.domain.decision.AgentMessage;
import com.ruoyi.dca.domain.decision.AgentObservation;
import com.ruoyi.dca.domain.decision.AgentRun;
import com.ruoyi.dca.domain.decision.DecisionAction;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.FeatureSnapshot;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.decision.SignalScore;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.mapper.decision.DecisionAuditMapper;
import com.ruoyi.dca.service.decision.impl.DecisionAuditServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DecisionAuditServiceImplTest {

    @Mock
    private DecisionAuditMapper decisionAuditMapper;

    @InjectMocks
    private DecisionAuditServiceImpl decisionAuditService;

    @Test
    void saveDecisionRunBackfillsNestedTraceAndSymbolFields() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-9");
        decisionRun.setSymbol("BTCUSDT");
        decisionRun.setMode("paper");
        decisionRun.setAction("OPEN_LONG");
        decisionRun.setConfidence(82);
        decisionRun.setEventStrength("strong");
        decisionRun.setModelCode("gpt-4.1");
        decisionRun.setModelProvider("openai");
        decisionRun.setPromptSource("template");
        decisionRun.setBindingTemplateCode("trade.supervisor.v1");
        decisionRun.setFallbackTemplateCode("trade.supervisor.fallback");
        decisionRun.setResolvedTemplateCode("trade.supervisor.v1");
        decisionRun.setPromptTemplateFallbackUsed(Boolean.FALSE);
        decisionRun.setMarketSourceConfig(Map.of(
            "config_id", 91,
            "updated_at", "2026-04-17 10:15:00",
            "transport_type", "WEBSOCKET",
            "vendor_code", "BINANCE"
        ));
        decisionRun.setFeatureSnapshot(new FeatureSnapshot(Map.of(
            "price_change_pct", 6.4,
            "news_score", 0.82
        )));

        SignalEvent signalEvent = new SignalEvent();
        signalEvent.setSignalType("market_tick");
        signalEvent.setScore(0.82);
        signalEvent.setFeatureJson("{\"price_change_pct\":6.4}");
        SignalWindowState signalWindowState = new SignalWindowState();
        signalWindowState.setWindowKey("market:BTCUSDT:15m");
        signalWindowState.setStateJson("{\"count\":2}");
        AgentRun agentRun = new AgentRun();
        agentRun.setAgentName("market");
        agentRun.setStatus("completed");
        AgentObservation agentObservation = new AgentObservation();
        agentObservation.setAgentName("market");
        agentObservation.setObservationType("feature_context");
        agentObservation.setObservationJson("{\"price_change_pct\":6.4}");
        AgentConclusion agentConclusion = new AgentConclusion();
        agentConclusion.setAgentName("market");
        agentConclusion.setBias("bullish");
        agentConclusion.setConfidence(82);
        agentConclusion.setReason("trend confirmed");
        AgentMessage agentMessage = new AgentMessage();
        agentMessage.setSpeakerAgent("market");
        agentMessage.setTargetAgent("news");
        agentMessage.setRoundNo(0);
        agentMessage.setMessageType("proposal");
        agentMessage.setContentJson("{\"stance\":\"bullish\"}");
        agentMessage.setSummaryText("market remains bullish");
        DecisionAction decisionAction = new DecisionAction();
        decisionAction.setAction("OPEN_LONG");
        decisionAction.setSide("long");
        decisionAction.setExecutionStatus("filled");
        decisionAction.setOrderStatus("FILLED");
        decisionRun.setSignalEvents(List.of(signalEvent));
        decisionRun.setSignalWindowStates(List.of(signalWindowState));
        decisionRun.setAgentRuns(List.of(agentRun));
        decisionRun.setAgentObservations(List.of(agentObservation));
        decisionRun.setAgentConclusions(List.of(agentConclusion));
        decisionRun.setAgentMessages(List.of(agentMessage));
        decisionRun.setDecisionActions(List.of(decisionAction));

        doAnswer(invocation -> {
            DecisionRun captured = invocation.getArgument(0);
            captured.setId(99L);
            return 1;
        }).when(decisionAuditMapper).insertDecisionRun(any(DecisionRun.class));
        doAnswer(invocation -> {
            SignalEvent captured = invocation.getArgument(0);
            captured.setId(199L);
            return 1;
        }).when(decisionAuditMapper).insertSignalEvent(any(SignalEvent.class));
        doAnswer(invocation -> {
            AgentRun captured = invocation.getArgument(0);
            captured.setId(299L);
            return 1;
        }).when(decisionAuditMapper).insertAgentRun(any(AgentRun.class));

        decisionAuditService.saveDecisionRun(decisionRun);

        ArgumentCaptor<DecisionRun> runCaptor = ArgumentCaptor.forClass(DecisionRun.class);
        verify(decisionAuditMapper).insertDecisionRun(runCaptor.capture());
        assertThat(runCaptor.getValue().getSummaryReason()).isEqualTo("");
        assertThat(runCaptor.getValue().getModelCode()).isEqualTo("gpt-4.1");
        assertThat(runCaptor.getValue().getModelProvider()).isEqualTo("openai");
        assertThat(runCaptor.getValue().getPromptSource()).isEqualTo("template");
        assertThat(runCaptor.getValue().getBindingTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(runCaptor.getValue().getFallbackTemplateCode()).isEqualTo("trade.supervisor.fallback");
        assertThat(runCaptor.getValue().getResolvedTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(runCaptor.getValue().getPromptTemplateFallbackUsed()).isFalse();

        ArgumentCaptor<SignalEvent> signalCaptor = ArgumentCaptor.forClass(SignalEvent.class);
        verify(decisionAuditMapper).insertSignalEvent(signalCaptor.capture());
        assertThat(signalCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(signalCaptor.getValue().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(signalCaptor.getValue().getScore()).isEqualTo(0.82);

        ArgumentCaptor<FeatureSnapshot> featureCaptor = ArgumentCaptor.forClass(FeatureSnapshot.class);
        verify(decisionAuditMapper).insertFeatureSnapshot(featureCaptor.capture());
        assertThat(featureCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(featureCaptor.getValue().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(featureCaptor.getValue().getEventStrength()).isEqualTo("strong");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"price_change_pct\":6.4");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"marketSourceConfig\"");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"config_id\":91");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"vendor_code\":\"BINANCE\"");

        ArgumentCaptor<SignalScore> scoreCaptor = ArgumentCaptor.forClass(SignalScore.class);
        verify(decisionAuditMapper).insertSignalScore(scoreCaptor.capture());
        assertThat(scoreCaptor.getValue().getSignalEventId()).isEqualTo(199L);
        assertThat(scoreCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(scoreCaptor.getValue().getSignalType()).isEqualTo("market_tick");
        assertThat(scoreCaptor.getValue().getScore()).isEqualByComparingTo("0.82");

        ArgumentCaptor<SignalWindowState> windowCaptor = ArgumentCaptor.forClass(SignalWindowState.class);
        verify(decisionAuditMapper).insertSignalWindowState(windowCaptor.capture());
        assertThat(windowCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(windowCaptor.getValue().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(windowCaptor.getValue().getWindowKey()).isEqualTo("market:BTCUSDT:15m");

        ArgumentCaptor<AgentRun> runAuditCaptor = ArgumentCaptor.forClass(AgentRun.class);
        verify(decisionAuditMapper).insertAgentRun(runAuditCaptor.capture());
        assertThat(runAuditCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(runAuditCaptor.getValue().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(runAuditCaptor.getValue().getEventStrength()).isEqualTo("strong");
        assertThat(runAuditCaptor.getValue().getStatus()).isEqualTo("completed");

        ArgumentCaptor<AgentObservation> observationCaptor = ArgumentCaptor.forClass(AgentObservation.class);
        verify(decisionAuditMapper).insertAgentObservation(observationCaptor.capture());
        assertThat(observationCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(observationCaptor.getValue().getAgentName()).isEqualTo("market");
        assertThat(observationCaptor.getValue().getAgentRunId()).isEqualTo(299L);
        assertThat(observationCaptor.getValue().getObservationType()).isEqualTo("feature_context");

        ArgumentCaptor<AgentConclusion> agentCaptor = ArgumentCaptor.forClass(AgentConclusion.class);
        verify(decisionAuditMapper).insertAgentConclusion(agentCaptor.capture());
        assertThat(agentCaptor.getValue().getTraceId()).isEqualTo("trace-9");

        ArgumentCaptor<AgentMessage> messageCaptor = ArgumentCaptor.forClass(AgentMessage.class);
        verify(decisionAuditMapper).insertAgentMessage(messageCaptor.capture());
        assertThat(messageCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(messageCaptor.getValue().getAgentRunId()).isEqualTo(299L);
        assertThat(messageCaptor.getValue().getSpeakerAgent()).isEqualTo("market");
        assertThat(messageCaptor.getValue().getMessageType()).isEqualTo("proposal");

        ArgumentCaptor<DecisionAction> actionCaptor = ArgumentCaptor.forClass(DecisionAction.class);
        verify(decisionAuditMapper).insertDecisionAction(actionCaptor.capture());
        assertThat(actionCaptor.getValue().getTraceId()).isEqualTo("trace-9");
        assertThat(actionCaptor.getValue().getDecisionRunId()).isEqualTo(99L);
        assertThat(actionCaptor.getValue().getExecutionStatus()).isEqualTo("filled");
        assertThat(actionCaptor.getValue().getOrderStatus()).isEqualTo("FILLED");
    }

    @Test
    void saveDecisionRunGeneratesTraceIdWhenMissing() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setSymbol("ETHUSDT");
        decisionRun.setMode("shadow");
        decisionRun.setAction("SKIP");
        decisionRun.setConfidence(0);

        decisionAuditService.saveDecisionRun(decisionRun);

        ArgumentCaptor<DecisionRun> runCaptor = ArgumentCaptor.forClass(DecisionRun.class);
        verify(decisionAuditMapper).insertDecisionRun(runCaptor.capture());
        assertThat(runCaptor.getValue().getTraceId()).isNotBlank();
    }

    @Test
    void saveDecisionRunCreatesFeatureSnapshotWhenOnlyMarketSourceConfigIsProvided() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-market-source-only");
        decisionRun.setSymbol("BTCUSDT");
        decisionRun.setMode("paper");
        decisionRun.setAction("SKIP");
        decisionRun.setEventStrength("normal");
        decisionRun.setMarketSourceConfig(Map.of(
            "config_id", 88,
            "updated_at", "2026-04-17 12:00:00",
            "vendor_code", "BINANCE"
        ));

        decisionAuditService.saveDecisionRun(decisionRun);

        ArgumentCaptor<FeatureSnapshot> featureCaptor = ArgumentCaptor.forClass(FeatureSnapshot.class);
        verify(decisionAuditMapper).insertFeatureSnapshot(featureCaptor.capture());
        assertThat(featureCaptor.getValue().getTraceId()).isEqualTo("trace-market-source-only");
        assertThat(featureCaptor.getValue().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"marketSourceConfig\"");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"config_id\":88");
    }

    @Test
    void saveDecisionRunPersistsTradeMemoryAndLifecycleStatusIntoFeatureSnapshot() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-memory-status");
        decisionRun.setSymbol("ETHUSDT");
        decisionRun.setMode("paper");
        decisionRun.setAction("CLOSE");
        decisionRun.setEventStrength("strong");
        decisionRun.setTradeMemoryStatus(Map.of(
            "status", "stored",
            "reason", "",
            "trace_id", "trace-memory-status",
            "lesson_text", "Wait for reclaim confirmation before closing the short."
        ));
        decisionRun.setLifecycleStatus(Map.of(
            "status", "recorded",
            "operation", "exit",
            "trace_id", "trace-memory-status",
            "memory_status", "stored",
            "memory_reason", "",
            "memory", Map.of("lesson_text", "Wait for reclaim confirmation before closing the short.")
        ));

        decisionAuditService.saveDecisionRun(decisionRun);

        ArgumentCaptor<FeatureSnapshot> featureCaptor = ArgumentCaptor.forClass(FeatureSnapshot.class);
        verify(decisionAuditMapper).insertFeatureSnapshot(featureCaptor.capture());
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"tradeMemoryStatus\"");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"lesson_text\":\"Wait for reclaim confirmation before closing the short.\"");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"lifecycleStatus\"");
        assertThat(featureCaptor.getValue().getSnapshotJson()).contains("\"memory_status\":\"stored\"");
    }

    @Test
    void listDecisionRunsDelegatesStatusFiltersToMapper() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-join");
        decisionRun.setPromptSource("template");
        decisionRun.setResolvedTemplateCode("trade.supervisor.v1");
        decisionRun.setPromptTemplateFallbackUsed(Boolean.FALSE);
        when(decisionAuditMapper.selectDecisionRuns("filled", "FILLED")).thenReturn(List.of(decisionRun));
        when(decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(List.of("trace-join"))).thenReturn(List.of());
        when(decisionAuditMapper.selectAgentMessagesByTraceIds(List.of("trace-join"))).thenReturn(List.of());

        List<DecisionRun> results = decisionAuditService.listDecisionRuns("filled", "FILLED");

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getTraceId()).isEqualTo("trace-join");
        assertThat(results.get(0).getPromptSource()).isEqualTo("template");
        assertThat(results.get(0).getResolvedTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(results.get(0).getPromptTemplateFallbackUsed()).isFalse();
        verify(decisionAuditMapper).selectDecisionRuns("filled", "FILLED");
    }

    @Test
    void listDecisionRunsWithoutFiltersAttachesLatestExchangeOrderStatus() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-join");
        decisionRun.setSymbol("BTCUSDT");

        ExchangeOrder exchangeOrder = new ExchangeOrder();
        exchangeOrder.setTraceId("trace-join");
        exchangeOrder.setStatus("filled");
        exchangeOrder.setOrderStatus("FILLED");

        when(decisionAuditMapper.selectDecisionRunsBase()).thenReturn(List.of(decisionRun));
        when(decisionAuditMapper.selectLatestExchangeOrdersByTraceIds(List.of("trace-join"))).thenReturn(List.of(exchangeOrder));
        when(decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(List.of("trace-join"))).thenReturn(List.of());
        when(decisionAuditMapper.selectAgentMessagesByTraceIds(List.of("trace-join"))).thenReturn(List.of());

        List<DecisionRun> results = decisionAuditService.listDecisionRuns(null, null);

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getExecutionStatus()).isEqualTo("filled");
        assertThat(results.get(0).getOrderStatus()).isEqualTo("FILLED");
        verify(decisionAuditMapper).selectDecisionRunsBase();
        verify(decisionAuditMapper, never()).selectDecisionRuns(null, null);
    }

    @Test
    void listDecisionRunsRestoresFeatureSnapshotAndMarketSourceConfig() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-feature");
        decisionRun.setSymbol("BTCUSDT");

        FeatureSnapshot featureSnapshot = new FeatureSnapshot();
        featureSnapshot.setTraceId("trace-feature");
        featureSnapshot.setSymbol("BTCUSDT");
        featureSnapshot.setEventStrength("strong");
        featureSnapshot.setSnapshotJson(
            "{\"priceChangePct\":6.4,\"marketSourceConfig\":{\"vendorCode\":\"BINANCE\",\"updateTime\":\"2026-04-17 10:15:00\"}}"
        );

        when(decisionAuditMapper.selectDecisionRunsBase()).thenReturn(List.of(decisionRun));
        when(decisionAuditMapper.selectLatestExchangeOrdersByTraceIds(List.of("trace-feature"))).thenReturn(List.of());
        when(decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(List.of("trace-feature"))).thenReturn(List.of(featureSnapshot));
        when(decisionAuditMapper.selectAgentMessagesByTraceIds(List.of("trace-feature"))).thenReturn(List.of());

        List<DecisionRun> results = decisionAuditService.listDecisionRuns(null, null);

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getEventStrength()).isEqualTo("strong");
        assertThat(results.get(0).getFeatureSnapshot()).isNotNull();
        assertThat(results.get(0).getFeatureSnapshot().getSnapshot()).containsEntry("priceChangePct", 6.4);
        assertThat(results.get(0).getMarketSourceConfig()).containsEntry("vendorCode", "BINANCE");
        assertThat(results.get(0).getMarketSourceConfig()).containsEntry("updateTime", "2026-04-17 10:15:00");
        verify(decisionAuditMapper).selectLatestFeatureSnapshotsByTraceIds(List.of("trace-feature"));
    }

    @Test
    void listDecisionRunsRestoresTradeMemoryAndLifecycleStatusFromFeatureSnapshot() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-memory-restore");
        decisionRun.setSymbol("ETHUSDT");

        FeatureSnapshot featureSnapshot = new FeatureSnapshot();
        featureSnapshot.setTraceId("trace-memory-restore");
        featureSnapshot.setSymbol("ETHUSDT");
        featureSnapshot.setEventStrength("normal");
        featureSnapshot.setSnapshotJson(
            """
            {"tradeMemoryStatus":{"status":"stored","reason":"","trace_id":"trace-memory-restore","lesson_text":"Only close after reclaim confirmation."},"lifecycleStatus":{"status":"recorded","operation":"exit","trace_id":"trace-memory-restore","memory_status":"stored","memory_reason":"","memory":{"lesson_text":"Only close after reclaim confirmation."}}}
            """
        );

        when(decisionAuditMapper.selectDecisionRunsBase()).thenReturn(List.of(decisionRun));
        when(decisionAuditMapper.selectLatestExchangeOrdersByTraceIds(List.of("trace-memory-restore"))).thenReturn(List.of());
        when(decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(List.of("trace-memory-restore"))).thenReturn(List.of(featureSnapshot));
        when(decisionAuditMapper.selectAgentMessagesByTraceIds(List.of("trace-memory-restore"))).thenReturn(List.of());

        List<DecisionRun> results = decisionAuditService.listDecisionRuns(null, null);

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getTradeMemoryStatus()).containsEntry("status", "stored");
        assertThat(results.get(0).getTradeMemoryStatus()).containsEntry("lesson_text", "Only close after reclaim confirmation.");
        assertThat(results.get(0).getLifecycleStatus()).containsEntry("status", "recorded");
        assertThat(results.get(0).getLifecycleStatus()).containsEntry("memory_status", "stored");
    }

    @Test
    void listDecisionRunsAttachesOrderedAgentMessagesByTraceId() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-transcript");
        decisionRun.setSymbol("BTCUSDT");

        AgentMessage first = new AgentMessage();
        first.setTraceId("trace-transcript");
        first.setRoundNo(0);
        first.setSpeakerAgent("market_agent");
        first.setMessageType("proposal");
        first.setSummaryText("market opens bearish");

        AgentMessage second = new AgentMessage();
        second.setTraceId("trace-transcript");
        second.setRoundNo(1);
        second.setSpeakerAgent("news_agent");
        second.setMessageType("revision");
        second.setSummaryText("news revises to neutral");

        when(decisionAuditMapper.selectDecisionRunsBase()).thenReturn(List.of(decisionRun));
        when(decisionAuditMapper.selectLatestExchangeOrdersByTraceIds(List.of("trace-transcript"))).thenReturn(List.of());
        when(decisionAuditMapper.selectLatestFeatureSnapshotsByTraceIds(List.of("trace-transcript"))).thenReturn(List.of());
        when(decisionAuditMapper.selectAgentMessagesByTraceIds(List.of("trace-transcript"))).thenReturn(List.of(first, second));

        List<DecisionRun> results = decisionAuditService.listDecisionRuns(null, null);

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getAgentMessages()).hasSize(2);
        assertThat(results.get(0).getAgentMessages())
            .extracting(AgentMessage::getSpeakerAgent, AgentMessage::getMessageType)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple("market_agent", "proposal"),
                org.assertj.core.groups.Tuple.tuple("news_agent", "revision")
            );
    }

    @Test
    void listRecentSupervisorDecisionsFallsBackToDecisionRunsWhenTranscriptMessageMissing() {
        DecisionRun fallbackRun = new DecisionRun();
        fallbackRun.setTraceId("trace-fallback-1");
        fallbackRun.setAction("HOLD");
        fallbackRun.setConfidence(65);
        fallbackRun.setSummaryReason("wait_for_breakout");
        fallbackRun.setModelCode("gpt-4.1");
        fallbackRun.setResolvedTemplateCode("trade.supervisor.v1");
        fallbackRun.setCreatedAt("2026-05-18 10:00:00");

        when(decisionAuditMapper.selectRecentSupervisorDecisionMessages("BTCUSDT", "paper", "trace-current", 2))
            .thenReturn(List.of());
        when(decisionAuditMapper.selectRecentSupervisorDecisionRuns(eq("BTCUSDT"), eq("paper"), eq("trace-current"), anyInt()))
            .thenReturn(List.of(fallbackRun));

        List<AgentMessage> results = decisionAuditService.listRecentSupervisorDecisions(" BTCUSDT ", "paper", "trace-current", 2);

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getTraceId()).isEqualTo("trace-fallback-1");
        assertThat(results.get(0).getSpeakerAgent()).isEqualTo("supervisor_agent");
        assertThat(results.get(0).getMessageType()).isEqualTo("final_decision");
        assertThat(results.get(0).getModelCode()).isEqualTo("gpt-4.1");
        assertThat(results.get(0).getTemplateCode()).isEqualTo("trade.supervisor.v1");
        assertThat(results.get(0).getCreatedAt()).isEqualTo("2026-05-18 10:00:00");
        assertThat(results.get(0).getContentJson()).contains("\"action\":\"HOLD\"");
        assertThat(results.get(0).getContentJson()).contains("\"confidence\":65");
        assertThat(results.get(0).getContentJson()).contains("\"summary_reason\":\"wait_for_breakout\"");
        verify(decisionAuditMapper).selectRecentSupervisorDecisionMessages("BTCUSDT", "paper", "trace-current", 2);
        verify(decisionAuditMapper).selectRecentSupervisorDecisionRuns(eq("BTCUSDT"), eq("paper"), eq("trace-current"), anyInt());
    }

    @Test
    void listRecentSupervisorDecisionsMergesTranscriptAndDecisionRunFallbackInNewestOrder() {
        AgentMessage message = new AgentMessage();
        message.setTraceId("trace-history-1");
        message.setSpeakerAgent("supervisor_agent");
        message.setMessageType("final_decision");
        message.setContentJson("{\"action\":\"SKIP\",\"summary_reason\":\"older_transcript\"}");
        message.setCreatedAt("2026-05-18 09:00:00");

        DecisionRun newerFallbackRun = new DecisionRun();
        newerFallbackRun.setTraceId("trace-history-2");
        newerFallbackRun.setAction("HOLD");
        newerFallbackRun.setConfidence(72);
        newerFallbackRun.setSummaryReason("newer_run_only");
        newerFallbackRun.setCreatedAt("2026-05-18 10:00:00");

        DecisionRun duplicateRun = new DecisionRun();
        duplicateRun.setTraceId("trace-history-1");
        duplicateRun.setAction("SKIP");
        duplicateRun.setConfidence(40);
        duplicateRun.setSummaryReason("should_not_override_transcript");
        duplicateRun.setCreatedAt("2026-05-18 09:00:00");

        when(decisionAuditMapper.selectRecentSupervisorDecisionMessages("BTCUSDT", "paper", "", 2))
            .thenReturn(List.of(message));
        when(decisionAuditMapper.selectRecentSupervisorDecisionRuns(eq("BTCUSDT"), eq("paper"), eq(""), anyInt()))
            .thenReturn(List.of(newerFallbackRun, duplicateRun));

        List<AgentMessage> results = decisionAuditService.listRecentSupervisorDecisions("BTCUSDT", "paper", "", 2);

        assertThat(results).hasSize(2);
        assertThat(results)
            .extracting(AgentMessage::getTraceId)
            .containsExactly("trace-history-2", "trace-history-1");
        assertThat(results.get(0).getContentJson()).contains("\"summary_reason\":\"newer_run_only\"");
        assertThat(results.get(1).getContentJson()).contains("\"summary_reason\":\"older_transcript\"");
    }

    @Test
    void saveDecisionRunBackfillsExecutionStatusFromOrderStatus() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-status-1");
        decisionRun.setSymbol("BTCUSDT");
        decisionRun.setMode("paper");
        decisionRun.setAction("OPEN_LONG");
        decisionRun.setConfidence(88);
        decisionRun.setOrderStatus("FILLED");

        decisionAuditService.saveDecisionRun(decisionRun);

        ArgumentCaptor<DecisionRun> runCaptor = ArgumentCaptor.forClass(DecisionRun.class);
        verify(decisionAuditMapper).insertDecisionRun(runCaptor.capture());
        assertThat(runCaptor.getValue().getExecutionStatus()).isEqualTo("filled");
        assertThat(runCaptor.getValue().getOrderStatus()).isEqualTo("FILLED");
    }

    @Test
    void saveDecisionRunNormalizesSignalWindowUtcTimesToDatabaseTimezone() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-window-timezone");
        decisionRun.setSymbol("BTCUSDT");
        decisionRun.setMode("paper");
        decisionRun.setAction("SKIP");
        decisionRun.setConfidence(0);

        SignalWindowState signalWindowState = new SignalWindowState();
        signalWindowState.setWindowKey("market:BTCUSDT:15m");
        signalWindowState.setOpenedAt("2026-05-08T03:37:54Z");
        signalWindowState.setExpiresAt("2026-05-08T03:42:54+00:00");
        signalWindowState.setLastEventAt("2026-05-08T03:37:55.123456+00:00");
        signalWindowState.setLastConfirmedAt("2026-05-08 11:37:56");
        signalWindowState.setCombineUntilAt("2026-05-08T03:42:54Z");
        signalWindowState.setStateJson("{\"count\":5}");
        signalWindowState.setActive(Boolean.TRUE);
        decisionRun.setSignalWindowStates(List.of(signalWindowState));

        decisionAuditService.saveDecisionRun(decisionRun);

        ArgumentCaptor<SignalWindowState> windowCaptor = ArgumentCaptor.forClass(SignalWindowState.class);
        verify(decisionAuditMapper).insertSignalWindowState(windowCaptor.capture());
        assertThat(windowCaptor.getValue().getOpenedAt()).isEqualTo("2026-05-08 11:37:54");
        assertThat(windowCaptor.getValue().getExpiresAt()).isEqualTo("2026-05-08 11:42:54");
        assertThat(windowCaptor.getValue().getLastEventAt()).isEqualTo("2026-05-08 11:37:55");
        assertThat(windowCaptor.getValue().getLastConfirmedAt()).isEqualTo("2026-05-08 11:37:56");
        assertThat(windowCaptor.getValue().getCombineUntilAt()).isEqualTo("2026-05-08 11:42:54");
    }

    @Test
    void saveDecisionRunDeactivatesExpiredSignalWindowsBeforeInsert() {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("trace-window-expire");
        decisionRun.setSymbol("BTCUSDT");
        decisionRun.setMode("paper");
        decisionRun.setAction("SKIP");
        decisionRun.setConfidence(0);

        SignalWindowState signalWindowState = new SignalWindowState();
        signalWindowState.setWindowKey("market:BTCUSDT:15m");
        signalWindowState.setStateJson("{\"count\":5}");
        signalWindowState.setActive(Boolean.TRUE);
        decisionRun.setSignalWindowStates(List.of(signalWindowState));

        decisionAuditService.saveDecisionRun(decisionRun);

        InOrder inOrder = inOrder(decisionAuditMapper);
        inOrder.verify(decisionAuditMapper).insertDecisionRun(any(DecisionRun.class));
        inOrder.verify(decisionAuditMapper).deactivateExpiredSignalWindowStates(eq("BTCUSDT"), anyString());
        inOrder.verify(decisionAuditMapper).insertSignalWindowState(any(SignalWindowState.class));
    }
}
