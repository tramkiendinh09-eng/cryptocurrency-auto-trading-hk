package com.ruoyi.dca.controller;

import com.ruoyi.dca.service.IAuditAiCallLogService;
import com.ruoyi.dca.service.IAuditOperationLogService;
import com.ruoyi.dca.service.IAuditStrategyTriggerService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(AuditController.class)
@AutoConfigureMockMvc(addFilters = false)
@ContextConfiguration(classes = {
    AuditControllerLegacyRetirementTest.TestApplication.class,
    AuditController.class
})
class AuditControllerLegacyRetirementTest {

    @SpringBootApplication
    static class TestApplication {
    }

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private IAuditOperationLogService auditOperationLogService;

    @MockBean
    private IAuditStrategyTriggerService auditStrategyTriggerService;

    @MockBean
    private IAuditAiCallLogService auditAiCallLogService;

    @Test
    void triggerEndpointsReturnLegacyRetiredPayload() throws Exception {
        mockMvc.perform(get("/dca/audit/triggers"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.msg").isString());

        mockMvc.perform(get("/dca/audit/trigger/9"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.msg").isString());

        mockMvc.perform(post("/dca/audit/triggers/export"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.msg").isString());

        mockMvc.perform(delete("/dca/audit/triggers/1,2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(200))
            .andExpect(jsonPath("$.msg").isString());

        verifyNoInteractions(auditStrategyTriggerService);
    }
}
