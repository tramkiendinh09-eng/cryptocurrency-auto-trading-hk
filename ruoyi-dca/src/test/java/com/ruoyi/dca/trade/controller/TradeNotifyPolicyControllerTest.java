package com.ruoyi.dca.trade.controller;

import com.ruoyi.dca.controller.trade.TradeNotifyPolicyController;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicy;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicyChannel;
import com.ruoyi.dca.service.trade.ITradeNotifyPolicyService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TradeNotifyPolicyController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {TradeNotifyPolicyControllerTest.TestApplication.class, TradeNotifyPolicyController.class})
class TradeNotifyPolicyControllerTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ITradeNotifyPolicyService tradeNotifyPolicyService;

    @Test
    void listPoliciesReturnsRowsWithChannelBindings() throws Exception {
        TradeNotifyPolicy policy = new TradeNotifyPolicy();
        policy.setId(5L);
        policy.setPolicyName("Runtime Risk");
        policy.setPolicyScope("STRATEGY");
        policy.setStrategyId(7L);
        policy.setEventScopeJson("[\"risk_guard_hit\"]");
        policy.setSeverityScopeJson("[\"ERROR\"]");
        policy.setModeScopeJson("[\"shadow\",\"live\"]");
        policy.setEnabled(Boolean.TRUE);
        TradeNotifyPolicyChannel channel = new TradeNotifyPolicyChannel();
        channel.setPolicyId(5L);
        channel.setChannelId(3L);
        channel.setChannelOrder(1);
        channel.setEnabled(Boolean.TRUE);
        policy.setChannelBindings(List.of(channel));

        when(tradeNotifyPolicyService.selectTradeNotifyPolicyList(any(TradeNotifyPolicy.class)))
            .thenReturn(Collections.singletonList(policy));

        mockMvc.perform(get("/dca/trade/notify-policy/list"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.rows[0].policyName").value("Runtime Risk"))
            .andExpect(jsonPath("$.rows[0].channelBindings[0].channelId").value(3))
            .andExpect(jsonPath("$.total").value(1));
    }

    @Test
    void createPolicyAcceptsWritablePayload() throws Exception {
        when(tradeNotifyPolicyService.insertTradeNotifyPolicy(any(TradeNotifyPolicy.class))).thenReturn(1);

        mockMvc.perform(post("/dca/trade/notify-policy")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "policyName":"Runtime Risk",
                      "policyScope":"STRATEGY",
                      "strategyId":7,
                      "eventScopeJson":"[\\"risk_guard_hit\\"]",
                      "severityScopeJson":"[\\"ERROR\\"]",
                      "modeScopeJson":"[\\"shadow\\",\\"live\\"]",
                      "throttleSeconds":90,
                      "templateCode":"runtime-risk",
                      "enabled":true,
                      "channelBindings":[{"channelId":3,"channelOrder":1,"enabled":true}]
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void updatePolicyAcceptsWritablePayload() throws Exception {
        when(tradeNotifyPolicyService.updateTradeNotifyPolicy(any(TradeNotifyPolicy.class))).thenReturn(1);

        mockMvc.perform(put("/dca/trade/notify-policy")
                .contentType(APPLICATION_JSON)
                .content("""
                    {
                      "id":9,
                      "policyName":"Runtime Risk Escalation",
                      "policyScope":"GLOBAL",
                      "eventScopeJson":"[\\"decision\\",\\"risk_guard_hit\\"]",
                      "severityScopeJson":"[\\"WARN\\",\\"ERROR\\"]",
                      "modeScopeJson":"[\\"paper\\",\\"shadow\\"]",
                      "throttleSeconds":60,
                      "enabled":false,
                      "channelBindings":[{"channelId":4,"channelOrder":1,"enabled":true}]
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void deletePolicyAcceptsIds() throws Exception {
        when(tradeNotifyPolicyService.deleteTradeNotifyPolicyByIds(any(Long[].class))).thenReturn(1);

        mockMvc.perform(delete("/dca/trade/notify-policy/9"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200));
    }
}
