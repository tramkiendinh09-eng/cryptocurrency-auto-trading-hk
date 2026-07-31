package com.ruoyi.dca.runtime;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.controller.runtime.TradeExecutionController;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.service.runtime.ITradeExecutionService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verify;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradeExecutionController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {
    TradeExecutionStatusContractTest.TestApplication.class,
    TradeExecutionController.class,
})
class TradeExecutionStatusContractTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ITradeExecutionService tradeExecutionService;

    @Test
    void exchangeOrderCallbackCarriesBusinessStatusAndExchangeStatusTogether() throws Exception {
        ExchangeOrder callback = new ExchangeOrder();
        callback.setTraceId("trace-status-1");
        callback.setExchangeCode("binance");
        callback.setSymbol("BTCUSDT");
        callback.setSide("BUY");
        callback.setMode("paper");
        callback.setOrderRef("paper-BTCUSDT");
        callback.setStatus("filled");
        callback.setExecutionStatus("filled");
        callback.setOrderStatus("FILLED");

        doNothing().when(tradeExecutionService).recordExchangeOrder(
            argThat(order ->
                "filled".equals(order.getStatus())
                    && "filled".equals(order.getExecutionStatus())
                    && "FILLED".equals(order.getOrderStatus())
            )
        );

        mockMvc.perform(
                post("/dca/trade/execution/exchange-order")
                    .contentType(APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(callback))
            )
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));

        verify(tradeExecutionService).recordExchangeOrder(
            argThat(order ->
                "filled".equals(order.getStatus())
                    && "filled".equals(order.getExecutionStatus())
                    && "FILLED".equals(order.getOrderStatus())
            )
        );
    }
}
