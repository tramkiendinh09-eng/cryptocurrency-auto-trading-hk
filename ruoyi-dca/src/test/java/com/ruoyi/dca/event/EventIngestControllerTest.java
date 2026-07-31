package com.ruoyi.dca.event;

import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.dca.controller.event.EventIngestController;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.service.event.IEventIngestService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(EventIngestController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {EventIngestControllerTest.TestApplication.class, EventIngestController.class})
class EventIngestControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private IEventIngestService eventIngestService;

    @Test
    void listMarketHistoryEndpointIsAnonymous() throws Exception {
        Method method = EventIngestController.class.getMethod("listMarketHistory", String.class, String.class, Integer.class, Integer.class);

        org.assertj.core.api.Assertions.assertThat(method.isAnnotationPresent(Anonymous.class)).isTrue();
    }

    @Test
    void listMarketHistoryReturnsRecentPersistedSamples() throws Exception {
        when(eventIngestService.listRecentMarketHistory("BTCUSDT", "okx", 60, 300)).thenReturn(List.of(
            Map.of("observed_at", "2026-04-29T04:00:00Z", "price", 76800.0, "quote_volume", 61193.0),
            Map.of("observed_at", "2026-04-29T04:01:00Z", "price", 76810.0, "quote_volume", 61200.0)
        ));

        mockMvc.perform(get("/dca/event/market-history")
                .param("symbol", "BTCUSDT")
                .param("exchange", "okx")
                .param("limit", "60"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.data[0].price").value(76800.0))
            .andExpect(jsonPath("$.data[1].quote_volume").value(61200.0));
    }

    @Test
    void ingestAcceptsNormalizedMarketEvent() throws Exception {
        String body = """
            {"eventType":"market_tick","symbol":"BTCUSDT","exchange":"binance","payloadJson":"{}"}
            """;

        doNothing().when(eventIngestService).ingest(any(EventRaw.class));

        mockMvc.perform(post("/dca/event/ingest").contentType(APPLICATION_JSON).content(body))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
