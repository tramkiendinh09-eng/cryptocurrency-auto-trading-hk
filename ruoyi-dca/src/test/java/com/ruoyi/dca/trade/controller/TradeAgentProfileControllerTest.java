package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.TradeAgentProfileController;
import com.ruoyi.dca.domain.trade.TradeAgentProfile;
import com.ruoyi.dca.service.trade.ITradeAgentProfileService;
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

@WebMvcTest(TradeAgentProfileController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeAgentProfileControllerTest.TestApplication.class, TradeAgentProfileController.class})
class TradeAgentProfileControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeAgentProfileService tradeAgentProfileService;

    @Test
    void listProfilesReturnsRowsArray() throws Exception {
        TradeAgentProfile profile = new TradeAgentProfile();
        profile.setId(1L);
        profile.setAgentCode("market_agent");
        profile.setAgentName("Market Agent");
        profile.setAgentType("RULE");
        profile.setEnabled(Boolean.TRUE);

        when(tradeAgentProfileService.selectTradeAgentProfileList(any(TradeAgentProfile.class)))
            .thenReturn(Collections.singletonList(profile));

        mockMvc.perform(get("/dca/trade/agent-profile/list"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].agentCode").value("market_agent"))
            .andExpect(jsonPath("$.rows[0].agentType").value("RULE"))
            .andExpect(jsonPath("$.total").value(1));
    }

    @Test
    void createProfileAcceptsWritablePayload() throws Exception {
        when(tradeAgentProfileService.insertTradeAgentProfile(any(TradeAgentProfile.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/agent-profile")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "agentCode":"news_agent",
                      "agentName":"News Agent",
                      "agentType":"LLM",
                      "enabled":true,
                      "llmEnabled":true,
                      "dialogueEnabled":false,
                      "maxDialogueRounds":0,
                      "speakOrder":2,
                      "timeoutSeconds":30,
                      "maxRetries":2,
                      "temperatureOverride":0.2,
                      "topPOverride":0.8,
                      "maxTokensOverride":1024,
                      "structuredSchemaCode":"agent_view_v1",
                      "toolPolicyJson":"{\\"web_search\\":false}",
                      "runtimeOptionsJson":"{\\"parallel\\":false}"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updateProfileAcceptsWritablePayload() throws Exception {
        when(tradeAgentProfileService.updateTradeAgentProfile(any(TradeAgentProfile.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/agent-profile")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "id":1,
                      "agentCode":"social_agent",
                      "agentName":"Social Agent",
                      "agentType":"HYBRID",
                      "enabled":true,
                      "llmEnabled":true,
                      "dialogueEnabled":true,
                      "maxDialogueRounds":1,
                      "speakOrder":4,
                      "timeoutSeconds":30,
                      "maxRetries":1,
                      "structuredSchemaCode":"agent_view_v1"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void deleteProfileAcceptsIds() throws Exception {
        when(tradeAgentProfileService.deleteTradeAgentProfileByIds(any(Long[].class))).thenReturn(1);

        mockMvc.perform(delete("/dca/trade/agent-profile/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
