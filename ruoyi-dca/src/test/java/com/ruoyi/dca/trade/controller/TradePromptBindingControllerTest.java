package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.TradePromptBindingController;
import com.ruoyi.dca.domain.trade.TradePromptBinding;
import com.ruoyi.dca.service.trade.ITradePromptBindingService;
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

@WebMvcTest(TradePromptBindingController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradePromptBindingControllerTest.TestApplication.class, TradePromptBindingController.class})
class TradePromptBindingControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradePromptBindingService tradePromptBindingService;

    @Test
    void listBindingsReturnsRowsArray() throws Exception {
        TradePromptBinding binding = new TradePromptBinding();
        binding.setId(1L);
        binding.setBindingName("Supervisor Prompt");
        binding.setBindingScope("SUPERVISOR");
        binding.setTemplateCode("trade.supervisor.v1");
        binding.setOutputSchemaCode("supervisor_decision_v1");
        binding.setEnabled(Boolean.TRUE);

        when(tradePromptBindingService.selectTradePromptBindingList(any(TradePromptBinding.class)))
            .thenReturn(Collections.singletonList(binding));

        mockMvc.perform(get("/dca/trade/prompt-binding/list"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].bindingName").value("Supervisor Prompt"))
            .andExpect(jsonPath("$.rows[0].bindingScope").value("SUPERVISOR"))
            .andExpect(jsonPath("$.total").value(1));
    }

    @Test
    void createBindingAcceptsWritablePayload() throws Exception {
        when(tradePromptBindingService.insertTradePromptBinding(any(TradePromptBinding.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/prompt-binding")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "bindingName":"Supervisor Prompt",
                      "strategyId":7,
                      "strategyVersionId":12,
                      "symbol":"BTCUSDT",
                      "exchangeCode":"BINANCE",
                      "bindingScope":"SUPERVISOR",
                      "templateCode":"trade.supervisor.v1",
                      "fallbackTemplateCode":"trade.supervisor.fallback",
                      "modelId":21,
                      "outputSchemaCode":"supervisor_decision_v1",
                      "priority":100,
                      "modeScopeJson":"[\\"paper\\",\\"shadow\\"]",
                      "eventStrengthScopeJson":"[\\"strong\\",\\"normal\\"]",
                      "enabled":true
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updateBindingAcceptsWritablePayload() throws Exception {
        when(tradePromptBindingService.updateTradePromptBinding(any(TradePromptBinding.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/prompt-binding")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "id":1,
                      "bindingName":"News Agent Prompt",
                      "bindingScope":"NEWS_AGENT",
                      "templateCode":"trade.news.v1",
                      "outputSchemaCode":"agent_view_v1",
                      "priority":50,
                      "enabled":false
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void deleteBindingAcceptsIds() throws Exception {
        when(tradePromptBindingService.deleteTradePromptBindingByIds(any(Long[].class))).thenReturn(1);

        mockMvc.perform(delete("/dca/trade/prompt-binding/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
