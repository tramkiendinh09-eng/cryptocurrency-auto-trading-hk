package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.TradeStrategyController;
import com.ruoyi.dca.domain.enums.TradeRuntimeMode;
import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.service.trade.ITradeStrategyService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradeStrategyController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeStrategyControllerTest.TestApplication.class, TradeStrategyController.class})
class TradeStrategyControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeStrategyService tradeStrategyService;

    @Test
    void listStrategiesReturnsRowsArray() throws Exception {
        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(1L);
        strategy.setStrategyKey("alpha");
        strategy.setStrategyName("Alpha Strategy");
        strategy.setRuntimeMode(TradeRuntimeMode.PAPER);
        strategy.setEnabled(Boolean.TRUE);

        when(tradeStrategyService.selectTradeStrategyList(any(TradeStrategy.class)))
            .thenReturn(Collections.singletonList(strategy));

        mockMvc.perform(get("/dca/trade/strategy/list"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows").isArray())
            .andExpect(jsonPath("$.rows[0].strategyKey").value("alpha"))
            .andExpect(jsonPath("$.rows[0].runtimeMode").value("PAPER"))
            .andExpect(jsonPath("$.total").value(1));
    }

    @Test
    void listStrategiesAcceptsLowercaseRuntimeModeQueryParam() throws Exception {
        when(tradeStrategyService.selectTradeStrategyList(any(TradeStrategy.class)))
            .thenReturn(Collections.emptyList());

        mockMvc.perform(get("/dca/trade/strategy/list").param("runtimeMode", "paper"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<TradeStrategy> captor = ArgumentCaptor.forClass(TradeStrategy.class);
        verify(tradeStrategyService).selectTradeStrategyList(captor.capture());
        assertEquals(TradeRuntimeMode.PAPER, captor.getValue().getRuntimeMode());
    }

    @Test
    void createStrategyAcceptsWritablePayload() throws Exception {
        when(tradeStrategyService.insertTradeStrategy(any(TradeStrategy.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/strategy")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"strategyKey":"alpha","strategyName":"Alpha","runtimeMode":"PAPER","symbolsJson":"[\\\"BTCUSDT\\\"]","exchangesJson":"[\\\"binance\\\"]","enabled":true}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void createStrategyAcceptsLowercaseRuntimeModeInJsonBody() throws Exception {
        when(tradeStrategyService.insertTradeStrategy(any(TradeStrategy.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/strategy")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"strategyKey":"alpha","strategyName":"Alpha","runtimeMode":"shadow","symbolsJson":"[\\\"BTCUSDT\\\"]","exchangesJson":"[\\\"binance\\\"]","enabled":true}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<TradeStrategy> captor = ArgumentCaptor.forClass(TradeStrategy.class);
        verify(tradeStrategyService).insertTradeStrategy(captor.capture());
        assertEquals(TradeRuntimeMode.SHADOW, captor.getValue().getRuntimeMode());
    }

    @Test
    void updateStrategyAcceptsWritablePayload() throws Exception {
        when(tradeStrategyService.updateTradeStrategy(any(TradeStrategy.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/strategy")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"id":9,"strategyKey":"alpha","strategyName":"Alpha 2","runtimeMode":"SHADOW","symbolsJson":"[\\\"ETHUSDT\\\"]","exchangesJson":"[\\\"okx\\\"]","enabled":false}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updateStrategyAcceptsLowercaseRuntimeModeInJsonBody() throws Exception {
        when(tradeStrategyService.updateTradeStrategy(any(TradeStrategy.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/strategy")
                .contentType(APPLICATION_JSON)
                .content("""
                    {"id":9,"strategyKey":"alpha","strategyName":"Alpha 2","runtimeMode":"live","symbolsJson":"[\\\"ETHUSDT\\\"]","exchangesJson":"[\\\"okx\\\"]","enabled":false}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        ArgumentCaptor<TradeStrategy> captor = ArgumentCaptor.forClass(TradeStrategy.class);
        verify(tradeStrategyService).updateTradeStrategy(captor.capture());
        assertEquals(TradeRuntimeMode.LIVE, captor.getValue().getRuntimeMode());
    }

    @Test
    void deleteStrategyAcceptsIds() throws Exception {
        when(tradeStrategyService.deleteTradeStrategyByIds(any(Long[].class))).thenReturn(1);

        mockMvc.perform(delete("/dca/trade/strategy/7"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void listStrategyVersionsReturnsAuditRows() throws Exception {
        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(5L);
        version.setVersionNo(2);
        version.setConfigJson("{\"runtimeMode\":\"LIVE\"}");

        when(tradeStrategyService.selectTradeStrategyVersions(eq(5L)))
            .thenReturn(Collections.singletonList(version));

        mockMvc.perform(get("/dca/trade/strategy/5/versions"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].strategyId").value(5))
            .andExpect(jsonPath("$.data[0].versionNo").value(2));
    }

    @Test
    void listStrategyBindingsReturnsBindingRows() throws Exception {
        ExchangeAccountBinding binding = new ExchangeAccountBinding();
        binding.setStrategyId(6L);
        binding.setAccountId(12L);
        binding.setExchangeCode("binance");
        binding.setEnabled(Boolean.TRUE);

        when(tradeStrategyService.selectExchangeAccountBindings(eq(6L)))
            .thenReturn(Collections.singletonList(binding));

        mockMvc.perform(get("/dca/trade/strategy/6/bindings"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].strategyId").value(6))
            .andExpect(jsonPath("$.data[0].accountId").value(12));
    }

    @Test
    void replaceStrategyBindingsAcceptsWritablePayload() throws Exception {
        when(tradeStrategyService.replaceExchangeAccountBindings(eq(8L), any())).thenReturn(2);

        mockMvc.perform(put("/dca/trade/strategy/8/bindings")
                .contentType(APPLICATION_JSON)
                .content("""
                    [{"accountId":21,"exchangeCode":"binance","enabled":true},{"accountId":22,"exchangeCode":"okx","enabled":false}]
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
