package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.TradeDataSourceBindingController;
import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;
import com.ruoyi.dca.service.trade.ITradeDataSourceBindingService;
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

@WebMvcTest(TradeDataSourceBindingController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeDataSourceBindingControllerTest.TestApplication.class, TradeDataSourceBindingController.class})
class TradeDataSourceBindingControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeDataSourceBindingService tradeDataSourceBindingService;

    @Test
    void listBindingsReturnsRowsArray() throws Exception {
        TradeDataSourceBinding binding = new TradeDataSourceBinding();
        binding.setId(12L);
        binding.setBindingName("Primary News Feed");
        binding.setStrategyId(7L);
        binding.setSourceId(21L);
        binding.setEventType("news");
        binding.setSymbolScopeJson("[\"BTCUSDT\"]");
        binding.setExchangeScopeJson("[\"BINANCE\"]");
        binding.setModeScopeJson("[\"shadow\"]");
        binding.setEnabled(Boolean.TRUE);

        when(tradeDataSourceBindingService.selectTradeDataSourceBindingList(any(TradeDataSourceBinding.class)))
            .thenReturn(Collections.singletonList(binding));

        mockMvc.perform(get("/dca/trade/source-binding/list"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].bindingName").value("Primary News Feed"))
            .andExpect(jsonPath("$.rows[0].eventType").value("news"))
            .andExpect(jsonPath("$.total").value(1));
    }

    @Test
    void createBindingAcceptsWritablePayload() throws Exception {
        when(tradeDataSourceBindingService.insertTradeDataSourceBinding(any(TradeDataSourceBinding.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/source-binding")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "bindingName":"Primary News Feed",
                      "strategyId":7,
                      "sourceId":21,
                      "eventType":"news",
                      "symbolScopeJson":"[\\"BTCUSDT\\",\\"ETHUSDT\\"]",
                      "exchangeScopeJson":"[\\"BINANCE\\"]",
                      "modeScopeJson":"[\\"shadow\\",\\"live\\"]",
                      "enabled":true
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updateBindingAcceptsWritablePayload() throws Exception {
        when(tradeDataSourceBindingService.updateTradeDataSourceBinding(any(TradeDataSourceBinding.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/source-binding")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "id":12,
                      "bindingName":"Primary Onchain Feed",
                      "strategyId":7,
                      "sourceId":22,
                      "eventType":"onchain",
                      "symbolScopeJson":"[\\"BTCUSDT\\"]",
                      "exchangeScopeJson":"[\\"OKX\\"]",
                      "modeScopeJson":"[\\"paper\\",\\"shadow\\"]",
                      "enabled":false
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void deleteBindingAcceptsIds() throws Exception {
        when(tradeDataSourceBindingService.deleteTradeDataSourceBindingByIds(any(Long[].class))).thenReturn(1);

        mockMvc.perform(delete("/dca/trade/source-binding/12"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
