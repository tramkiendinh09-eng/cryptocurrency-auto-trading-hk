package com.ruoyi.dca.decision;

import com.ruoyi.dca.controller.decision.DecisionAuditController;
import com.ruoyi.dca.domain.decision.AgentConclusion;
import com.ruoyi.dca.domain.decision.AgentMessage;
import com.ruoyi.dca.domain.decision.AgentObservation;
import com.ruoyi.dca.domain.decision.AgentRun;
import com.ruoyi.dca.domain.decision.DecisionAction;
import com.ruoyi.dca.domain.decision.DecisionRun;
import com.ruoyi.dca.domain.decision.FeatureSnapshot;
import com.ruoyi.dca.domain.decision.SignalEvent;
import com.ruoyi.dca.domain.decision.SignalWindowState;
import com.ruoyi.dca.service.decision.IDecisionAuditService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

@WebMvcTest(DecisionAuditController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {DecisionAuditControllerTest.TestApplication.class, DecisionAuditController.class})
class DecisionAuditControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private IDecisionAuditService decisionAuditService;

    @Test
    void ingestDecisionRunPersistsStructuredPayload() throws Exception {
        String body = """
            {
              "traceId":"t-1",
              "symbol":"BTCUSDT",
              "mode":"paper",
              "action":"OPEN_LONG",
              "confidence":82,
              "eventStrength":"strong",
               "featureSnapshot":{
                 "price_change_pct":6.4,
                 "news_score":0.82
               },
               "marketSourceConfig":{
                 "config_id":91,
                 "updated_at":"2026-04-17 10:15:00",
                 "transport_type":"WEBSOCKET",
                 "vendor_code":"BINANCE"
               },
               "modelCode":"gpt-4.1",
               "modelProvider":"openai",
               "promptSource":"template",
               "bindingTemplateCode":"trade.supervisor.v1",
               "fallbackTemplateCode":"trade.supervisor.fallback",
               "resolvedTemplateCode":"trade.supervisor.v1",
               "promptTemplateFallbackUsed":false,
               "summaryReason":"multi-signal aligned",
              "signalEvents":[
                {
                  "traceId":"t-1",
                  "symbol":"BTCUSDT",
                  "signalType":"news",
                  "score":0.82,
                  "featureJson":"{\\"event_type\\":\\"news\\",\\"headline\\":\\"ETF inflow\\"}"
                }
              ],
               "signalWindowStates":[
                 {
                   "windowKey":"news:BTCUSDT:15m",
                   "stateJson":"{\\"count\\":2,\\"max_score\\":0.82}"
                 }
               ],
               "agentRuns":[
                 {
                   "traceId":"t-1",
                   "symbol":"BTCUSDT",
                   "agentName":"news",
                   "eventStrength":"strong",
                   "status":"completed"
                 }
               ],
               "agentObservations":[
                 {
                   "traceId":"t-1",
                   "agentName":"news",
                   "observationType":"event_context",
                   "observationJson":"{\\"events\\":[{\\"event_type\\":\\"news\\",\\"headline\\":\\"ETF inflow\\"}]}"
                 }
               ],
               "agentConclusions":[
                  {
                    "traceId":"t-1",
                   "agentName":"news",
                   "bias":"bullish",
                   "confidence":82,
                   "reason":"ETF inflow"
                 }
               ],
               "agentMessages":[
                 {
                   "traceId":"t-1",
                   "speakerAgent":"news_agent",
                   "targetAgent":"market_agent",
                   "roundNo":0,
                   "messageType":"proposal",
                   "templateCode":"trade.news.v1",
                   "modelCode":"gpt-4.1",
                   "contentJson":"{\\"stance\\":\\"bullish\\"}",
                   "summaryText":"news stays bullish"
                 }
               ],
               "decisionActions":[
                 {
                   "traceId":"t-1",
                   "action":"OPEN_LONG",
                   "side":"long",
                   "orderRef":"paper-BTCUSDT",
                   "executionStatus":"filled",
                   "orderStatus":"FILLED"
                 }
               ]
             }
             """;

        doNothing().when(decisionAuditService).saveDecisionRun(any(DecisionRun.class));

        mockMvc.perform(post("/dca/decision/audit").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<DecisionRun> decisionRunCaptor = ArgumentCaptor.forClass(DecisionRun.class);
        verify(decisionAuditService).saveDecisionRun(decisionRunCaptor.capture());

        DecisionRun captured = decisionRunCaptor.getValue();
        SignalEvent capturedSignalEvent = captured.getSignalEvents().get(0);
        FeatureSnapshot capturedFeatureSnapshot = captured.getFeatureSnapshot();
        SignalWindowState capturedWindowState = captured.getSignalWindowStates().get(0);
        AgentRun capturedAgentRun = captured.getAgentRuns().get(0);
        AgentObservation capturedObservation = captured.getAgentObservations().get(0);
        AgentConclusion capturedConclusion = captured.getAgentConclusions().get(0);
        AgentMessage capturedMessage = captured.getAgentMessages().get(0);
        DecisionAction capturedAction = captured.getDecisionActions().get(0);
        org.junit.jupiter.api.Assertions.assertEquals("t-1", captured.getTraceId());
        org.junit.jupiter.api.Assertions.assertEquals("BTCUSDT", captured.getSymbol());
        org.junit.jupiter.api.Assertions.assertEquals("strong", captured.getEventStrength());
        org.junit.jupiter.api.Assertions.assertEquals("6.4", String.valueOf(capturedFeatureSnapshot.getSnapshot().get("price_change_pct")));
        org.junit.jupiter.api.Assertions.assertEquals(91, captured.getMarketSourceConfig().get("config_id"));
        org.junit.jupiter.api.Assertions.assertEquals("BINANCE", captured.getMarketSourceConfig().get("vendor_code"));
        org.junit.jupiter.api.Assertions.assertEquals("gpt-4.1", captured.getModelCode());
        org.junit.jupiter.api.Assertions.assertEquals("openai", captured.getModelProvider());
        org.junit.jupiter.api.Assertions.assertEquals("template", captured.getPromptSource());
        org.junit.jupiter.api.Assertions.assertEquals("trade.supervisor.v1", captured.getBindingTemplateCode());
        org.junit.jupiter.api.Assertions.assertEquals("trade.supervisor.fallback", captured.getFallbackTemplateCode());
        org.junit.jupiter.api.Assertions.assertEquals("trade.supervisor.v1", captured.getResolvedTemplateCode());
        org.junit.jupiter.api.Assertions.assertEquals(Boolean.FALSE, captured.getPromptTemplateFallbackUsed());
        org.junit.jupiter.api.Assertions.assertEquals("news", capturedSignalEvent.getSignalType());
        org.junit.jupiter.api.Assertions.assertEquals(Double.valueOf(0.82), capturedSignalEvent.getScore());
        org.junit.jupiter.api.Assertions.assertEquals("news:BTCUSDT:15m", capturedWindowState.getWindowKey());
        org.junit.jupiter.api.Assertions.assertEquals("news", capturedAgentRun.getAgentName());
        org.junit.jupiter.api.Assertions.assertEquals("completed", capturedAgentRun.getStatus());
        org.junit.jupiter.api.Assertions.assertEquals("event_context", capturedObservation.getObservationType());
        org.junit.jupiter.api.Assertions.assertEquals("news", capturedConclusion.getAgentName());
        org.junit.jupiter.api.Assertions.assertEquals("bullish", capturedConclusion.getBias());
        org.junit.jupiter.api.Assertions.assertEquals("news_agent", capturedMessage.getSpeakerAgent());
        org.junit.jupiter.api.Assertions.assertEquals("market_agent", capturedMessage.getTargetAgent());
        org.junit.jupiter.api.Assertions.assertEquals(0, capturedMessage.getRoundNo());
        org.junit.jupiter.api.Assertions.assertEquals("proposal", capturedMessage.getMessageType());
        org.junit.jupiter.api.Assertions.assertEquals("OPEN_LONG", capturedAction.getAction());
        org.junit.jupiter.api.Assertions.assertEquals("filled", capturedAction.getExecutionStatus());
        org.junit.jupiter.api.Assertions.assertEquals("FILLED", capturedAction.getOrderStatus());
    }

    @Test
    void ingestDecisionRunAcceptsSnakeCaseStructuredPayload() throws Exception {
        String body = """
            {
              "trace_id":"t-1-snake",
              "symbol":"BTCUSDT",
              "mode":"paper",
              "action":"OPEN_LONG",
              "confidence":82,
              "event_strength":"strong",
              "feature_snapshot":{
                "price_change_pct":6.4
              },
              "market_source_config":{
                "config_id":92,
                "updated_at":"2026-04-17 11:20:00",
                "transport_type":"WEBSOCKET",
                "vendor_code":"OKX"
              },
              "model_code":"gpt-4.1",
              "model_provider":"openai",
              "prompt_source":"inline",
              "binding_template_code":"trade.supervisor.v1",
              "fallback_template_code":"trade.supervisor.fallback",
              "resolved_template_code":"",
              "prompt_template_fallback_used":true,
              "summary_reason":"multi-signal aligned",
              "signal_events":[
                {
                  "trace_id":"t-1-snake",
                  "symbol":"BTCUSDT",
                  "signal_type":"news",
                  "score":0.82,
                  "feature_json":"{\\"event_type\\":\\"news\\",\\"headline\\":\\"ETF inflow\\"}"
                }
              ],
              "signal_window_states":[
                {
                  "window_key":"news:BTCUSDT:15m",
                  "state_json":"{\\"count\\":2,\\"max_score\\":0.82}"
                }
              ],
              "agent_runs":[
                {
                  "trace_id":"t-1-snake",
                  "symbol":"BTCUSDT",
                  "agent_name":"news",
                  "event_strength":"strong",
                  "status":"completed"
                }
              ],
              "agent_observations":[
                {
                  "trace_id":"t-1-snake",
                  "agent_name":"news",
                  "observation_type":"event_context",
                  "observation_json":"{\\"events\\":[{\\"event_type\\":\\"news\\",\\"headline\\":\\"ETF inflow\\"}]}"
                }
              ],
              "agent_conclusions":[
                {
                  "trace_id":"t-1-snake",
                  "agent_name":"news",
                  "bias":"bullish",
                  "confidence":82,
                  "reason":"ETF inflow"
                }
              ],
              "agent_messages":[
                {
                  "trace_id":"t-1-snake",
                  "speaker_agent":"news_agent",
                  "target_agent":"market_agent",
                  "round_no":1,
                  "message_type":"revision",
                  "template_code":"trade.news.v1",
                  "model_code":"gpt-4.1",
                  "content_json":"{\\"stance\\":\\"maintain\\"}",
                  "summary_text":"news maintains conviction"
                }
              ]
            }
            """;

        doNothing().when(decisionAuditService).saveDecisionRun(any(DecisionRun.class));

        mockMvc.perform(post("/dca/decision/audit").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<DecisionRun> decisionRunCaptor = ArgumentCaptor.forClass(DecisionRun.class);
        verify(decisionAuditService).saveDecisionRun(decisionRunCaptor.capture());

        DecisionRun captured = decisionRunCaptor.getValue();
        SignalEvent capturedSignalEvent = captured.getSignalEvents().get(0);
        AgentConclusion capturedConclusion = captured.getAgentConclusions().get(0);
        org.junit.jupiter.api.Assertions.assertEquals("t-1-snake", captured.getTraceId());
        org.junit.jupiter.api.Assertions.assertEquals("strong", captured.getEventStrength());
        org.junit.jupiter.api.Assertions.assertEquals(92, captured.getMarketSourceConfig().get("config_id"));
        org.junit.jupiter.api.Assertions.assertEquals("OKX", captured.getMarketSourceConfig().get("vendor_code"));
        org.junit.jupiter.api.Assertions.assertEquals("gpt-4.1", captured.getModelCode());
        org.junit.jupiter.api.Assertions.assertEquals("openai", captured.getModelProvider());
        org.junit.jupiter.api.Assertions.assertEquals("inline", captured.getPromptSource());
        org.junit.jupiter.api.Assertions.assertEquals("trade.supervisor.v1", captured.getBindingTemplateCode());
        org.junit.jupiter.api.Assertions.assertEquals("trade.supervisor.fallback", captured.getFallbackTemplateCode());
        org.junit.jupiter.api.Assertions.assertEquals("", captured.getResolvedTemplateCode());
        org.junit.jupiter.api.Assertions.assertEquals(Boolean.TRUE, captured.getPromptTemplateFallbackUsed());
        org.junit.jupiter.api.Assertions.assertEquals("multi-signal aligned", captured.getSummaryReason());
        org.junit.jupiter.api.Assertions.assertEquals("news", capturedSignalEvent.getSignalType());
        org.junit.jupiter.api.Assertions.assertEquals(Double.valueOf(0.82), capturedSignalEvent.getScore());
        org.junit.jupiter.api.Assertions.assertEquals("news", captured.getAgentRuns().get(0).getAgentName());
        org.junit.jupiter.api.Assertions.assertEquals("event_context", captured.getAgentObservations().get(0).getObservationType());
        org.junit.jupiter.api.Assertions.assertEquals("news", capturedConclusion.getAgentName());
        org.junit.jupiter.api.Assertions.assertEquals("news:BTCUSDT:15m", captured.getSignalWindowStates().get(0).getWindowKey());
        org.junit.jupiter.api.Assertions.assertEquals("news_agent", captured.getAgentMessages().get(0).getSpeakerAgent());
        org.junit.jupiter.api.Assertions.assertEquals("revision", captured.getAgentMessages().get(0).getMessageType());
    }

    @Test
    void ingestDecisionRunAcceptsTradeMemoryAndLifecycleStatusPayloads() throws Exception {
        String body = """
            {
              "traceId":"t-memory",
              "symbol":"ETHUSDT",
              "mode":"paper",
              "action":"CLOSE",
              "confidence":71,
              "tradeMemoryStatus":{
                "status":"stored",
                "reason":"",
                "trace_id":"t-memory",
                "lesson_text":"Only close after reclaim confirmation."
              },
              "lifecycleStatus":{
                "status":"recorded",
                "operation":"exit",
                "trace_id":"t-memory",
                "memory_status":"stored",
                "memory_reason":"",
                "memory":{
                  "lesson_text":"Only close after reclaim confirmation."
                }
              }
            }
            """;

        doNothing().when(decisionAuditService).saveDecisionRun(any(DecisionRun.class));

        mockMvc.perform(post("/dca/decision/audit").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<DecisionRun> decisionRunCaptor = ArgumentCaptor.forClass(DecisionRun.class);
        verify(decisionAuditService).saveDecisionRun(decisionRunCaptor.capture());

        DecisionRun captured = decisionRunCaptor.getValue();
        org.junit.jupiter.api.Assertions.assertEquals("stored", captured.getTradeMemoryStatus().get("status"));
        org.junit.jupiter.api.Assertions.assertEquals(
            "Only close after reclaim confirmation.",
            captured.getTradeMemoryStatus().get("lesson_text")
        );
        org.junit.jupiter.api.Assertions.assertEquals("recorded", captured.getLifecycleStatus().get("status"));
        org.junit.jupiter.api.Assertions.assertEquals("stored", captured.getLifecycleStatus().get("memory_status"));
    }

    @Test
    void listDecisionRunsReturnsRecentAuditRows() throws Exception {
        DecisionRun decisionRun = new DecisionRun();
        decisionRun.setTraceId("t-2");
        decisionRun.setSymbol("ETHUSDT");
        decisionRun.setMode("shadow");
        decisionRun.setAction("SKIP");
        decisionRun.setEventStrength("normal");
        decisionRun.setModelCode("gpt-4.1");
        decisionRun.setModelProvider("openai");
        decisionRun.setPromptSource("template");
        decisionRun.setBindingTemplateCode("trade.supervisor.v1");
        decisionRun.setResolvedTemplateCode("trade.supervisor.v1");
        decisionRun.setPromptTemplateFallbackUsed(Boolean.FALSE);
        decisionRun.setExecutionStatus("pending");
        decisionRun.setOrderStatus("PENDING");
        decisionRun.setMarketSourceConfig(Map.of(
            "vendorCode", "BINANCE",
            "updateTime", "2026-04-17 10:15:00"
        ));
        FeatureSnapshot featureSnapshot = new FeatureSnapshot();
        featureSnapshot.setTraceId("t-2");
        featureSnapshot.setSymbol("ETHUSDT");
        featureSnapshot.setEventStrength("normal");
        featureSnapshot.setSnapshot(Map.of(
            "priceChangePct", 1.8,
            "marketSourceConfig", Map.of("vendorCode", "BINANCE")
        ));
        decisionRun.setFeatureSnapshot(featureSnapshot);
        decisionRun.setTradeMemoryStatus(Map.of(
            "status", "stored",
            "reason", "",
            "trace_id", "t-2",
            "lesson_text", "Only close after reclaim confirmation."
        ));
        decisionRun.setLifecycleStatus(Map.of(
            "status", "recorded",
            "operation", "exit",
            "trace_id", "t-2",
            "memory_status", "stored",
            "memory_reason", "",
            "memory", Map.of("lesson_text", "Only close after reclaim confirmation.")
        ));
        AgentMessage agentMessage = new AgentMessage();
        agentMessage.setTraceId("t-2");
        agentMessage.setRoundNo(0);
        agentMessage.setSpeakerAgent("market_agent");
        agentMessage.setTargetAgent("news_agent");
        agentMessage.setMessageType("proposal");
        agentMessage.setTemplateCode("trade.market.v1");
        agentMessage.setModelCode("gpt-4.1");
        agentMessage.setContentJson("{\"stance\":\"bearish\"}");
        agentMessage.setSummaryText("market opens bearish");
        decisionRun.setAgentMessages(List.of(agentMessage));
        when(decisionAuditService.listDecisionRuns(null, null)).thenReturn(List.of(decisionRun));

        mockMvc.perform(get("/dca/decision/runs"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].traceId").value("t-2"))
            .andExpect(jsonPath("$.rows[0].action").value("SKIP"))
            .andExpect(jsonPath("$.rows[0].modelCode").value("gpt-4.1"))
            .andExpect(jsonPath("$.rows[0].modelProvider").value("openai"))
            .andExpect(jsonPath("$.rows[0].promptSource").value("template"))
            .andExpect(jsonPath("$.rows[0].bindingTemplateCode").value("trade.supervisor.v1"))
            .andExpect(jsonPath("$.rows[0].resolvedTemplateCode").value("trade.supervisor.v1"))
            .andExpect(jsonPath("$.rows[0].promptTemplateFallbackUsed").value(false))
            .andExpect(jsonPath("$.rows[0].executionStatus").value("pending"))
            .andExpect(jsonPath("$.rows[0].orderStatus").value("PENDING"))
            .andExpect(jsonPath("$.rows[0].eventStrength").value("normal"))
            .andExpect(jsonPath("$.rows[0].marketSourceConfig.vendorCode").value("BINANCE"))
            .andExpect(jsonPath("$.rows[0].featureSnapshot.snapshot.priceChangePct").value(1.8))
            .andExpect(jsonPath("$.rows[0].tradeMemoryStatus.status").value("stored"))
            .andExpect(jsonPath("$.rows[0].tradeMemoryStatus.lesson_text").value("Only close after reclaim confirmation."))
            .andExpect(jsonPath("$.rows[0].lifecycleStatus.memory_status").value("stored"))
            .andExpect(jsonPath("$.rows[0].agentMessages[0].speakerAgent").value("market_agent"))
            .andExpect(jsonPath("$.rows[0].agentMessages[0].messageType").value("proposal"))
            .andExpect(jsonPath("$.rows[0].agentMessages[0].templateCode").value("trade.market.v1"));
    }

    @Test
    void listDecisionRunsPassesExecutionFiltersToService() throws Exception {
        when(decisionAuditService.listDecisionRuns(eq("filled"), eq("FILLED"))).thenReturn(List.of());

        mockMvc.perform(get("/dca/decision/runs")
                .param("executionStatus", "filled")
                .param("orderStatus", "FILLED"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        verify(decisionAuditService).listDecisionRuns("filled", "FILLED");
    }

    @Test
    void listRecentSupervisorHistoryReturnsRecentDecisionMessages() throws Exception {
        AgentMessage first = new AgentMessage();
        first.setTraceId("trace-history-2");
        first.setSpeakerAgent("supervisor_agent");
        first.setMessageType("final_decision");
        first.setContentJson("{\"action\":\"HOLD\"}");
        AgentMessage second = new AgentMessage();
        second.setTraceId("trace-history-1");
        second.setSpeakerAgent("supervisor_agent");
        second.setMessageType("final_decision");
        second.setContentJson("{\"action\":\"SKIP\"}");
        when(decisionAuditService.listRecentSupervisorDecisions("BTCUSDT", "paper", "trace-current", 2))
            .thenReturn(List.of(first, second));

        mockMvc.perform(get("/dca/decision/supervisor-history")
                .param("symbol", "BTCUSDT")
                .param("mode", "paper")
                .param("excludeTraceId", "trace-current")
                .param("limit", "2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].traceId").value("trace-history-2"))
            .andExpect(jsonPath("$.data[0].speakerAgent").value("supervisor_agent"))
            .andExpect(jsonPath("$.data[1].contentJson").value("{\"action\":\"SKIP\"}"));

        verify(decisionAuditService).listRecentSupervisorDecisions("BTCUSDT", "paper", "trace-current", 2);
    }
}
