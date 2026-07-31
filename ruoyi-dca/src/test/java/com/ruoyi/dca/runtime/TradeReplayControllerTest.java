package com.ruoyi.dca.runtime;

import com.ruoyi.dca.controller.runtime.TradeReplayController;
import com.ruoyi.dca.domain.replay.PaperTradeOrder;
import com.ruoyi.dca.domain.replay.ReplayComparison;
import com.ruoyi.dca.domain.replay.ReplayEvent;
import com.ruoyi.dca.domain.replay.ReplaySession;
import com.ruoyi.dca.domain.replay.ReplayTraceSource;
import com.ruoyi.dca.domain.replay.ShadowDecisionLog;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.service.runtime.ITradeReplayService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import org.mockito.ArgumentCaptor;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradeReplayController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeReplayControllerTest.TestApplication.class, TradeReplayController.class})
class TradeReplayControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeReplayService tradeReplayService;

    @Test
    void createReplaySessionAcceptsStructuredPayload() throws Exception {
        String body = """
            {"sessionName":"BTC replay","symbol":"BTCUSDT","exchangeCode":"binance","mode":"paper","sourceType":"event_raw","status":"draft"}
            """;

        doNothing().when(tradeReplayService).recordReplaySession(any(ReplaySession.class));

        mockMvc.perform(post("/dca/trade/replay/session").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void createReplayEventAcceptsStructuredPayload() throws Exception {
        String body = """
            {"sessionId":8,"traceId":"trace-r-1","eventType":"news","symbol":"BTCUSDT","exchangeCode":"binance","payloadJson":"{\\"headline\\":\\"ETF inflow\\"}"}
            """;

        doNothing().when(tradeReplayService).recordReplayEvent(any(ReplayEvent.class));

        mockMvc.perform(post("/dca/trade/replay/event").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void createPaperTradeOrderAcceptsStructuredPayload() throws Exception {
        String body = """
            {"traceId":"trace-paper-1","exchangeCode":"binance","symbol":"BTCUSDT","side":"BUY","mode":"paper","orderRef":"paper-BTCUSDT","quoteAmount":3500,"executionStatus":"filled","orderStatus":"FILLED"}
            """;

        doNothing().when(tradeReplayService).recordPaperTradeOrder(any(PaperTradeOrder.class));

        mockMvc.perform(post("/dca/trade/replay/paper-order").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<PaperTradeOrder> captor = ArgumentCaptor.forClass(PaperTradeOrder.class);
        verify(tradeReplayService).recordPaperTradeOrder(captor.capture());
        org.assertj.core.api.Assertions.assertThat(captor.getValue().getExecutionStatus()).isEqualTo("filled");
        org.assertj.core.api.Assertions.assertThat(captor.getValue().getStatus()).isNull();
    }

    @Test
    void createShadowDecisionLogAcceptsStructuredPayload() throws Exception {
        String body = """
            {"traceId":"trace-shadow-1","exchangeCode":"okx","symbol":"ETHUSDT","mode":"shadow","action":"OPEN_LONG","side":"long","confidence":79,"summaryReason":"shadow confirmation","executionStatus":"pending","orderStatus":"PENDING"}
            """;

        doNothing().when(tradeReplayService).recordShadowDecisionLog(any(ShadowDecisionLog.class));

        mockMvc.perform(post("/dca/trade/replay/shadow-decision").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void listReplaySessionsReturnsRows() throws Exception {
        ReplaySession session = new ReplaySession();
        session.setSessionName("BTC replay");
        session.setSymbol("BTCUSDT");
        when(tradeReplayService.listReplaySessions()).thenReturn(List.of(session));

        mockMvc.perform(get("/dca/trade/replay/sessions"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].sessionName").value("BTC replay"))
            .andExpect(jsonPath("$.rows[0].symbol").value("BTCUSDT"));
    }

    @Test
    void listReplayEventsPassesSessionFilterToService() throws Exception {
        ReplayEvent event = new ReplayEvent();
        event.setTraceId("trace-r-1");
        event.setEventType("news");
        when(tradeReplayService.listReplayEvents(eq(8L))).thenReturn(List.of(event));

        mockMvc.perform(get("/dca/trade/replay/events").param("sessionId", "8"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].traceId").value("trace-r-1"))
            .andExpect(jsonPath("$.data[0].eventType").value("news"));

        verify(tradeReplayService).listReplayEvents(8L);
    }

    @Test
    void listPaperTradeOrdersReturnsRows() throws Exception {
        PaperTradeOrder order = new PaperTradeOrder();
        order.setTraceId("trace-paper-1");
        order.setOrderRef("paper-BTCUSDT");
        order.setExecutionStatus("submitted");
        when(tradeReplayService.listPaperTradeOrders()).thenReturn(List.of(order));

        mockMvc.perform(get("/dca/trade/replay/paper-orders"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].traceId").value("trace-paper-1"))
            .andExpect(jsonPath("$.data[0].orderRef").value("paper-BTCUSDT"))
            .andExpect(jsonPath("$.data[0].executionStatus").value("submitted"));
    }

    @Test
    void listShadowDecisionLogsReturnsRows() throws Exception {
        ShadowDecisionLog log = new ShadowDecisionLog();
        log.setTraceId("trace-shadow-1");
        log.setAction("OPEN_LONG");
        when(tradeReplayService.listShadowDecisionLogs()).thenReturn(List.of(log));

        mockMvc.perform(get("/dca/trade/replay/shadow-decisions"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].traceId").value("trace-shadow-1"))
            .andExpect(jsonPath("$.data[0].action").value("OPEN_LONG"));
    }

    @Test
    void getReplaySourceReturnsTracePayload() throws Exception {
        ReplayTraceSource source = new ReplayTraceSource();
        source.setTraceId("trace-source-1");
        source.setSymbol("BTCUSDT");
        source.setExchangeCode("binance");
        source.setMode("paper");
        source.setEventBundle(List.of(
            java.util.Map.of(
                "event_type", "news",
                "headline", "ETF inflow",
                "score", 0.92
            )
        ));
        when(tradeReplayService.getReplaySource("trace-source-1")).thenReturn(source);

        mockMvc.perform(get("/dca/trade/replay/source").param("traceId", "trace-source-1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.traceId").value("trace-source-1"))
            .andExpect(jsonPath("$.data.symbol").value("BTCUSDT"))
            .andExpect(jsonPath("$.data.exchangeCode").value("binance"))
            .andExpect(jsonPath("$.data.eventBundle[0].event_type").value("news"))
            .andExpect(jsonPath("$.data.eventBundle[0].headline").value("ETF inflow"));

        verify(tradeReplayService).getReplaySource("trace-source-1");
    }

    @Test
    void getReplayComparisonReturnsSideBySidePayload() throws Exception {
        ReplayComparison comparison = new ReplayComparison();
        comparison.setSessionId(12L);
        comparison.setSourceTraceId("trace-source-1");
        comparison.setReplayTraceId("trace-replay-1");
        comparison.setActionMatched(true);
        comparison.setExecutionStatusChanged(true);
        comparison.setOrderStatusChanged(false);
        comparison.setOriginalDecision(java.util.Map.of(
            "action", "OPEN_LONG",
            "executionStatus", "filled",
            "modelCode", "gpt-4.1",
            "promptSource", "template",
            "resolvedTemplateCode", "trade.supervisor.v1"
        ));
        comparison.setReplayDecision(java.util.Map.of(
            "action", "OPEN_LONG",
            "executionStatus", "pending",
            "modelCode", "gpt-4.1-mini",
            "promptSource", "inline",
            "resolvedTemplateCode", ""
        ));
        RiskGuardHit originalHit = new RiskGuardHit();
        originalHit.setRuleCode("max_position_ratio");
        originalHit.setReason("requested notional too large");
        RiskGuardHit replayHit = new RiskGuardHit();
        replayHit.setRuleCode("live_account_unhealthy");
        replayHit.setReason("live account degraded");
        comparison.setOriginalRiskHits(List.of(originalHit));
        comparison.setReplayRiskHits(List.of(replayHit));
        when(tradeReplayService.getReplayComparison(12L)).thenReturn(comparison);

        mockMvc.perform(get("/dca/trade/replay/compare").param("sessionId", "12"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.sessionId").value(12))
            .andExpect(jsonPath("$.data.sourceTraceId").value("trace-source-1"))
            .andExpect(jsonPath("$.data.replayTraceId").value("trace-replay-1"))
            .andExpect(jsonPath("$.data.actionMatched").value(true))
            .andExpect(jsonPath("$.data.executionStatusChanged").value(true))
            .andExpect(jsonPath("$.data.orderStatusChanged").value(false))
            .andExpect(jsonPath("$.data.originalDecision.action").value("OPEN_LONG"))
            .andExpect(jsonPath("$.data.originalDecision.modelCode").value("gpt-4.1"))
            .andExpect(jsonPath("$.data.originalDecision.promptSource").value("template"))
            .andExpect(jsonPath("$.data.originalDecision.resolvedTemplateCode").value("trade.supervisor.v1"))
            .andExpect(jsonPath("$.data.originalRiskHits[0].ruleCode").value("max_position_ratio"))
            .andExpect(jsonPath("$.data.replayDecision.executionStatus").value("pending"))
            .andExpect(jsonPath("$.data.replayDecision.modelCode").value("gpt-4.1-mini"))
            .andExpect(jsonPath("$.data.replayDecision.promptSource").value("inline"))
            .andExpect(jsonPath("$.data.replayRiskHits[0].ruleCode").value("live_account_unhealthy"));

        verify(tradeReplayService).getReplayComparison(12L);
    }

    @Test
    void updateReplaySessionAcceptsStatusAndReplayTrace() throws Exception {
        String body = """
            {"id":18,"status":"completed","replayTraceId":"trace-replay-18"}
            """;

        doNothing().when(tradeReplayService).updateReplaySession(any(ReplaySession.class));

        mockMvc.perform(put("/dca/trade/replay/session").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        verify(tradeReplayService).updateReplaySession(any(ReplaySession.class));
    }

    @Test
    void dispatchReplayCreatesQueuedSession() throws Exception {
        ReplaySession session = new ReplaySession();
        session.setId(18L);
        session.setSourceTraceId("trace-source-1");
        session.setStatus("queued");
        when(tradeReplayService.dispatchReplay("trace-source-1")).thenReturn(session);

        mockMvc.perform(post("/dca/trade/replay/dispatch").param("traceId", "trace-source-1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.id").value(18))
            .andExpect(jsonPath("$.data.sourceTraceId").value("trace-source-1"))
            .andExpect(jsonPath("$.data.status").value("queued"));

        verify(tradeReplayService).dispatchReplay("trace-source-1");
    }
}
