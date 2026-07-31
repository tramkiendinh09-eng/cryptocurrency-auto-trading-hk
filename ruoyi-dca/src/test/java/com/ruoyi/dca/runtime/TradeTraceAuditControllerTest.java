package com.ruoyi.dca.runtime;

import com.ruoyi.dca.controller.runtime.TradeTraceAuditController;
import com.ruoyi.dca.domain.replay.TraceAuditDetail;
import com.ruoyi.dca.domain.replay.TraceAuditEvent;
import com.ruoyi.dca.domain.replay.TraceAuditSummary;
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

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradeTraceAuditController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeTraceAuditControllerTest.TestApplication.class, TradeTraceAuditController.class})
class TradeTraceAuditControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeReplayService tradeReplayService;

    @Test
    void getTraceAuditDetailReturnsAggregatedPayload() throws Exception {
        TraceAuditSummary summary = new TraceAuditSummary();
        summary.setTraceId("trace-audit-1");
        summary.setSymbol("BTCUSDT");
        summary.setExchangeCode("binance");
        summary.setMode("shadow");
        summary.setAction("SKIP");

        TraceAuditEvent event = new TraceAuditEvent();
        event.setEventType("news");
        event.setCreatedAt("2026-04-21 15:03:39");
        event.setDisplayTitle("Bitcoin reclaims $75,000");

        TraceAuditDetail detail = new TraceAuditDetail();
        detail.setSummary(summary);
        detail.setEvents(List.of(event));

        when(tradeReplayService.getTraceAuditDetail("trace-audit-1")).thenReturn(detail);

        mockMvc.perform(get("/dca/trade/trace/detail").param("traceId", "trace-audit-1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data.summary.traceId").value("trace-audit-1"))
            .andExpect(jsonPath("$.data.summary.symbol").value("BTCUSDT"))
            .andExpect(jsonPath("$.data.events[0].eventType").value("news"))
            .andExpect(jsonPath("$.data.events[0].displayTitle").value("Bitcoin reclaims $75,000"));

        verify(tradeReplayService).getTraceAuditDetail("trace-audit-1");
    }
}
