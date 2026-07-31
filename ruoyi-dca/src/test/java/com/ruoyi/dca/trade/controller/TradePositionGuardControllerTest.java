package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.TradePositionGuardController;
import com.ruoyi.dca.domain.trade.TradePositionGuard;
import com.ruoyi.dca.service.trade.ITradePositionGuardService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradePositionGuardController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradePositionGuardControllerTest.TestApplication.class, TradePositionGuardController.class})
class TradePositionGuardControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradePositionGuardService tradePositionGuardService;

    @Test
    void listGuardsReturnsRowsArray() throws Exception {
        TradePositionGuard guard = new TradePositionGuard();
        guard.setId(1L);
        guard.setGuardName("BTC Guard");
        guard.setScopeType("SYMBOL");
        guard.setSymbol("BTCUSDT");
        guard.setExchangeCode("BINANCE");
        guard.setEnabled(Boolean.TRUE);

        when(tradePositionGuardService.selectTradePositionGuardList(any(TradePositionGuard.class)))
            .thenReturn(Collections.singletonList(guard));

        mockMvc.perform(get("/dca/trade/position-guard/list"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].guardName").value("BTC Guard"))
            .andExpect(jsonPath("$.rows[0].scopeType").value("SYMBOL"))
            .andExpect(jsonPath("$.total").value(1));
    }

    @Test
    void createGuardAcceptsWritablePayload() throws Exception {
        when(tradePositionGuardService.insertTradePositionGuard(any(TradePositionGuard.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/position-guard")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "guardName":"BTC Guard",
                      "scopeType":"SYMBOL",
                      "strategyId":7,
                      "symbol":"BTCUSDT",
                      "exchangeCode":"BINANCE",
                      "stopLossPct":0.03,
                      "takeProfitPct":0.05,
                      "maxHoldingMinutes":240,
                      "enabled":true,
                      "priority":0
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updateGuardAcceptsWritablePayload() throws Exception {
        when(tradePositionGuardService.updateTradePositionGuard(any(TradePositionGuard.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/position-guard")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "id":1,
                      "guardName":"Updated Guard",
                      "scopeType":"GLOBAL",
                      "stopLossPct":0.02,
                      "takeProfitPct":0.04,
                      "maxHoldingMinutes":180,
                      "enabled":false
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void deleteGuardAcceptsIds() throws Exception {
        when(tradePositionGuardService.deleteTradePositionGuardByIds(any(Long[].class))).thenReturn(1);

        mockMvc.perform(delete("/dca/trade/position-guard/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
