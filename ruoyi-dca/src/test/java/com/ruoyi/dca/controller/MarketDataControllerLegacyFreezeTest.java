package com.ruoyi.dca.controller;

import com.ruoyi.dca.mapper.MarketDataCollectLogMapper;
import com.ruoyi.dca.service.IMarketApiConfigService;
import com.ruoyi.dca.service.IMarketCollectTaskService;
import com.ruoyi.dca.service.IMarketDataCollectService;
import com.ruoyi.dca.service.IMarketDataConfigService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(MarketDataController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {
    MarketDataControllerLegacyFreezeTest.TestApplication.class,
    MarketDataController.class
})
class MarketDataControllerLegacyFreezeTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private IMarketDataCollectService collectService;

    @MockBean
    private IMarketDataConfigService configService;

    @MockBean
    private MarketDataCollectLogMapper collectLogMapper;

    @MockBean
    private IMarketApiConfigService apiConfigService;

    @MockBean
    private IMarketCollectTaskService taskService;

    @Test
    void legacyMutationEndpointsReturnFrozenCutoverMessage() throws Exception {
        mockMvc.perform(post("/dca/market/config")
                .contentType(APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(500))
            .andExpect(jsonPath("$.msg").value("Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead."));

        mockMvc.perform(put("/dca/market/config")
                .contentType(APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(500))
            .andExpect(jsonPath("$.msg").value("Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead."));

        mockMvc.perform(delete("/dca/market/config/1,2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(500))
            .andExpect(jsonPath("$.msg").value("Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead."));

        mockMvc.perform(post("/dca/market/collect/trigger")
                .contentType(APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(500))
            .andExpect(jsonPath("$.msg").value("Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead."));

        mockMvc.perform(post("/dca/market/task")
                .contentType(APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(500))
            .andExpect(jsonPath("$.msg").value("Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead."));

        mockMvc.perform(put("/dca/market/task")
                .contentType(APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(500))
            .andExpect(jsonPath("$.msg").value("Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead."));

        mockMvc.perform(delete("/dca/market/task/1,2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(500))
            .andExpect(jsonPath("$.msg").value("Legacy market-data collection endpoints are frozen. Use /dca/market/api or /dca/trade/* instead."));

        verifyNoInteractions(collectService, configService, collectLogMapper, apiConfigService, taskService);
    }
}
