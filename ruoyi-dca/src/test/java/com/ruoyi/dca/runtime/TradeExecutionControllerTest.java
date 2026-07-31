package com.ruoyi.dca.runtime;

import com.ruoyi.dca.controller.runtime.TradeExecutionController;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.order.OrderRequest;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionChangeLog;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.service.runtime.ITradeExecutionService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradeExecutionController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeExecutionControllerTest.TestApplication.class, TradeExecutionController.class})
class TradeExecutionControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeExecutionService tradeExecutionService;

    @Test
    void createOrderAcceptsStructuredRequest() throws Exception {
        String body = """
            {"traceId":"t-1","exchangeCode":"binance","symbol":"BTCUSDT","side":"BUY","mode":"paper","quoteAmount":500}
            """;

        doNothing().when(tradeExecutionService).recordOrderRequest(any(OrderRequest.class));

        mockMvc.perform(post("/dca/trade/execution/order").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void createPnlSnapshotAcceptsPerformancePayload() throws Exception {
        String body = """
            {"traceId":"t-2","mode":"paper","accountEquity":10250.25,"dailyPnl":120.50,"maxDrawdownPct":4.25,"peakAccountEquity":10710.00}
            """;

        doNothing().when(tradeExecutionService).recordPnlSnapshot(any(PnlSnapshot.class));

        mockMvc.perform(post("/dca/trade/execution/pnl-snapshot").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        verify(tradeExecutionService).recordPnlSnapshot(
            argThat(snapshot ->
                snapshot.getPeakAccountEquity() != null
                    && new java.math.BigDecimal("10710.00").compareTo(snapshot.getPeakAccountEquity()) == 0
            )
        );
    }

    @Test
    void createPositionSnapshotAcceptsStructuredPayload() throws Exception {
        String body = """
            {"traceId":"trace-position-1","exchangeCode":"binance","symbol":"BTCUSDT","side":"long","positionQuantity":0.0538,"entryPrice":65000.00,"unrealizedPnl":0}
            """;

        doNothing().when(tradeExecutionService).recordPositionSnapshot(any(PositionSnapshot.class));

        mockMvc.perform(post("/dca/trade/execution/position-snapshot").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void createExchangeOrderAcceptsStructuredPayload() throws Exception {
        String body = """
            {"traceId":"t-5","exchangeCode":"okx","symbol":"BTCUSDT","side":"SELL","mode":"live","orderRef":"okx-1","status":"pending","executionStatus":"pending","orderStatus":"PENDING","orderType":"limit","positionSide":"long","reduceOnly":true,"tdMode":"cross","leverage":3,"limitPrice":65000.1,"quantityBase":0.05,"okxEnhancedExecution":true}
            """;

        doNothing().when(tradeExecutionService).recordExchangeOrder(
            argThat(order ->
                "pending".equals(order.getStatus())
                    && "pending".equals(order.getExecutionStatus())
                    && "PENDING".equals(order.getOrderStatus())
                    && "limit".equals(order.getOrderType())
                    && "long".equals(order.getPositionSide())
                    && Boolean.TRUE.equals(order.getReduceOnly())
                    && "cross".equals(order.getTdMode())
                    && new java.math.BigDecimal("3").compareTo(order.getLeverage()) == 0
                    && new java.math.BigDecimal("65000.1").compareTo(order.getLimitPrice()) == 0
                    && new java.math.BigDecimal("0.05").compareTo(order.getQuantityBase()) == 0
                    && Boolean.TRUE.equals(order.getOkxEnhancedExecution())
            )
        );

        mockMvc.perform(post("/dca/trade/execution/exchange-order").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        verify(tradeExecutionService).recordExchangeOrder(
            argThat(order ->
                "pending".equals(order.getStatus())
                    && "pending".equals(order.getExecutionStatus())
                    && "PENDING".equals(order.getOrderStatus())
                    && "limit".equals(order.getOrderType())
                    && "long".equals(order.getPositionSide())
                    && Boolean.TRUE.equals(order.getReduceOnly())
            )
        );
    }

    @Test
    void createExchangeFillAcceptsStructuredPayload() throws Exception {
        String body = """
            {"traceId":"t-6","orderRef":"paper-BTCUSDT","fillPrice":65000.00,"fillQuantity":0.0538}
            """;

        doNothing().when(tradeExecutionService).recordExchangeFill(any(ExchangeFill.class));

        mockMvc.perform(post("/dca/trade/execution/exchange-fill").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void createRiskGuardHitAcceptsStructuredPayload() throws Exception {
        String body = """
            {"traceId":"t-risk-1","ruleCode":"market_source_abnormal","reason":"market_source_abnormal"}
            """;

        doNothing().when(tradeExecutionService).recordRiskGuardHit(
            argThat(hit -> "market_source_abnormal".equals(hit.getRuleCode()) && "market_source_abnormal".equals(hit.getReason()))
        );

        mockMvc.perform(post("/dca/trade/execution/risk-guard-hit").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void listOrdersPassesStatusFiltersToService() throws Exception {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("trace-order-1");
        order.setStatus("filled");
        order.setOrderStatus("FILLED");
        when(tradeExecutionService.listOrders(eq("filled"), eq("FILLED"))).thenReturn(java.util.List.of(order));

        mockMvc.perform(get("/dca/trade/execution/orders")
                .param("status", "filled")
                .param("orderStatus", "FILLED"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].executionStatus").value("filled"));

        verify(tradeExecutionService).listOrders("filled", "FILLED");
    }

    @Test
    void listPositionsReturnsOperatorPositionSnapshots() throws Exception {
        PositionSnapshot snapshot = new PositionSnapshot();
        snapshot.setExchangeCode("binance");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setSide("long");
        when(tradeExecutionService.listPositions()).thenReturn(java.util.List.of(snapshot));

        mockMvc.perform(get("/dca/trade/execution/positions"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].exchangeCode").value("binance"))
            .andExpect(jsonPath("$.rows[0].symbol").value("BTCUSDT"))
            .andExpect(jsonPath("$.rows[0].side").value("long"));

        verify(tradeExecutionService).listPositions();
    }

    @Test
    void listFillsReturnsExecutionFillRows() throws Exception {
        ExchangeFill fill = new ExchangeFill();
        fill.setTraceId("trace-fill-1");
        fill.setOrderRef("ord-1");
        fill.setFillPrice(new java.math.BigDecimal("65000.00"));
        fill.setFillQuantity(new java.math.BigDecimal("0.0150"));
        when(tradeExecutionService.listFills()).thenReturn(java.util.List.of(fill));

        mockMvc.perform(get("/dca/trade/execution/fills"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].traceId").value("trace-fill-1"))
            .andExpect(jsonPath("$.rows[0].orderRef").value("ord-1"));

        verify(tradeExecutionService).listFills();
    }

    @Test
    void listRiskHitsReturnsRuntimeRiskAuditRows() throws Exception {
        RiskGuardHit hit = new RiskGuardHit();
        hit.setTraceId("trace-risk-1");
        hit.setRuleCode("daily_loss_limit");
        hit.setReason("daily_loss_limit");
        when(tradeExecutionService.listRiskGuardHits()).thenReturn(java.util.List.of(hit));

        mockMvc.perform(get("/dca/trade/execution/risk-hits"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].traceId").value("trace-risk-1"))
            .andExpect(jsonPath("$.rows[0].ruleCode").value("daily_loss_limit"));

        verify(tradeExecutionService).listRiskGuardHits();
    }

    @Test
    void listPositionChangesReturnsExecutionAuditRows() throws Exception {
        PositionChangeLog changeLog = new PositionChangeLog();
        changeLog.setTraceId("trace-position-1");
        changeLog.setSymbol("BTCUSDT");
        changeLog.setSide("long");
        changeLog.setChangeType("OPEN");
        when(tradeExecutionService.listPositionChanges()).thenReturn(java.util.List.of(changeLog));

        mockMvc.perform(get("/dca/trade/execution/position-changes"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].traceId").value("trace-position-1"))
            .andExpect(jsonPath("$.rows[0].changeType").value("OPEN"));

        verify(tradeExecutionService).listPositionChanges();
    }
}
