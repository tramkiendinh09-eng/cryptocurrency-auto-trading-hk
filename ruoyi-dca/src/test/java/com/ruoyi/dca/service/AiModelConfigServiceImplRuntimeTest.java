package com.ruoyi.dca.service;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.AuditAiCallLog;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.trade.RuntimeModelCallResponse;
import com.ruoyi.dca.mapper.AiModelConfigMapper;
import com.ruoyi.dca.mapper.AuditAiCallLogMapper;
import com.ruoyi.dca.service.impl.AiModelConfigServiceImpl;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.ResourceAccessException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiModelConfigServiceImplRuntimeTest {

    @Test
    void callAiModelForRuntimeExtractsOpenAiMessageContent() {
        AiModelConfigMapper aiModelConfigMapper = mock(AiModelConfigMapper.class);
        AuditAiCallLogMapper auditAiCallLogMapper = mock(AuditAiCallLogMapper.class);
        RestTemplate restTemplate = mock(RestTemplate.class);

        AiModelConfig config = new AiModelConfig();
        config.setId(31L);
        config.setModelCode("gpt-4.1");
        config.setProvider("openai");
        config.setApiKey("runtime-key");
        config.setApiEndpoint("https://api.openai.internal/v1/chat/completions");
        config.setIsEnabled(1);

        when(aiModelConfigMapper.selectAiModelConfigById(31L)).thenReturn(config);
        when(restTemplate.exchange(
            eq("https://api.openai.internal/v1/chat/completions"),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            eq(String.class)
        )).thenReturn(ResponseEntity.status(HttpStatus.OK).body("""
            {"choices":[{"message":{"content":"{\\"action\\":\\"OPEN_LONG\\"}"}}],"usage":{"prompt_tokens":13,"completion_tokens":8,"total_tokens":21}}
            """));
        when(auditAiCallLogMapper.insertAuditAiCallLog(any(AuditAiCallLog.class))).thenReturn(1);

        AiModelConfigServiceImpl service = createRuntimeService(aiModelConfigMapper, auditAiCallLogMapper, restTemplate);

        RuntimeModelCallResponse response = service.callAiModelForRuntime(31L, "Return JSON only");

        assertEquals(31L, response.getModelId());
        assertEquals("gpt-4.1", response.getModelCode());
        assertEquals("openai", response.getModelProvider());
        assertEquals("{\"action\":\"OPEN_LONG\"}", response.getContent());
        verify(aiModelConfigMapper).incrementUsageCount(31L);

        ArgumentCaptor<AuditAiCallLog> captor = ArgumentCaptor.forClass(AuditAiCallLog.class);
        verify(auditAiCallLogMapper).insertAuditAiCallLog(captor.capture());
        AuditAiCallLog log = captor.getValue();
        assertEquals("trade_runtime", log.getScene());
        assertEquals("gpt-4.1", log.getModel());
        assertEquals("Return JSON only", log.getPrompt());
        assertEquals("{\"action\":\"OPEN_LONG\"}", log.getResponse());
        assertEquals(13, log.getPromptTokens());
        assertEquals(8, log.getCompletionTokens());
        assertEquals(21, log.getTotalTokens());
        assertEquals(1, log.getStatus());
    }

    @Test
    void callAiModelForRuntimeRecordsFailureAuditWhenUpstreamRequestFails() {
        AiModelConfigMapper aiModelConfigMapper = mock(AiModelConfigMapper.class);
        AuditAiCallLogMapper auditAiCallLogMapper = mock(AuditAiCallLogMapper.class);
        RestTemplate restTemplate = mock(RestTemplate.class);

        AiModelConfig config = new AiModelConfig();
        config.setId(31L);
        config.setModelCode("gpt-4.1");
        config.setProvider("openai");
        config.setApiKey("runtime-key");
        config.setApiEndpoint("https://api.openai.internal/v1/chat/completions");
        config.setIsEnabled(1);

        when(aiModelConfigMapper.selectAiModelConfigById(31L)).thenReturn(config);
        when(restTemplate.exchange(
            eq("https://api.openai.internal/v1/chat/completions"),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            eq(String.class)
        )).thenThrow(new ResourceAccessException("connect timed out"));
        when(auditAiCallLogMapper.insertAuditAiCallLog(any(AuditAiCallLog.class))).thenReturn(1);

        AiModelConfigServiceImpl service = createRuntimeService(aiModelConfigMapper, auditAiCallLogMapper, restTemplate);

        assertThrows(ServiceException.class, () -> service.callAiModelForRuntime(31L, "Return JSON only"));

        ArgumentCaptor<AuditAiCallLog> captor = ArgumentCaptor.forClass(AuditAiCallLog.class);
        verify(auditAiCallLogMapper).insertAuditAiCallLog(captor.capture());
        AuditAiCallLog log = captor.getValue();
        assertEquals("trade_runtime", log.getScene());
        assertEquals("gpt-4.1", log.getModel());
        assertEquals("Return JSON only", log.getPrompt());
        assertEquals(0, log.getStatus());
        assertEquals("connect timed out", log.getErrorMsg());
    }

    @Test
    void callAiModelForRuntimeRejectsHtmlResponseWithClearMessage() {
        AiModelConfigMapper aiModelConfigMapper = mock(AiModelConfigMapper.class);
        AuditAiCallLogMapper auditAiCallLogMapper = mock(AuditAiCallLogMapper.class);
        RestTemplate restTemplate = mock(RestTemplate.class);

        AiModelConfig config = new AiModelConfig();
        config.setId(32L);
        config.setModelCode("gpt-5.5");
        config.setProvider("openai");
        config.setApiKey("runtime-key");
        config.setApiEndpoint("https://bad-gateway.example/v1/chat/completions");
        config.setIsEnabled(1);

        when(aiModelConfigMapper.selectAiModelConfigById(32L)).thenReturn(config);
        when(restTemplate.exchange(
            eq("https://bad-gateway.example/v1/chat/completions"),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            eq(String.class)
        )).thenReturn(ResponseEntity.status(HttpStatus.OK).body("<html><body>login required</body></html>"));
        when(auditAiCallLogMapper.insertAuditAiCallLog(any(AuditAiCallLog.class))).thenReturn(1);

        AiModelConfigServiceImpl service = createRuntimeService(aiModelConfigMapper, auditAiCallLogMapper, restTemplate);

        ServiceException exception = assertThrows(
            ServiceException.class,
            () -> service.callAiModelForRuntime(32L, "Return JSON only")
        );

        assertTrue(exception.getMessage().contains("model response is not JSON"));
        assertTrue(exception.getMessage().contains("gpt-5.5"));
        assertTrue(exception.getMessage().contains("https://bad-gateway.example/v1/chat/completions"));

        ArgumentCaptor<AuditAiCallLog> captor = ArgumentCaptor.forClass(AuditAiCallLog.class);
        verify(auditAiCallLogMapper).insertAuditAiCallLog(captor.capture());
        AuditAiCallLog log = captor.getValue();
        assertEquals(0, log.getStatus());
        assertTrue(log.getErrorMsg().contains("model response is not JSON"));
    }

    @Test
    void callAiModelForRuntimeTreatsVersionUrlAsBaseUrl() {
        AiModelConfigMapper aiModelConfigMapper = mock(AiModelConfigMapper.class);
        AuditAiCallLogMapper auditAiCallLogMapper = mock(AuditAiCallLogMapper.class);
        RestTemplate restTemplate = mock(RestTemplate.class);

        AiModelConfig config = new AiModelConfig();
        config.setId(33L);
        config.setModelCode("gpt-4.1-mini");
        config.setProvider("openai");
        config.setApiKey("runtime-key");
        config.setApiEndpoint("https://api.okinto.com/v1");
        config.setIsEnabled(1);

        when(aiModelConfigMapper.selectAiModelConfigById(33L)).thenReturn(config);
        when(restTemplate.exchange(
            eq("https://api.okinto.com/v1/chat/completions"),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            eq(String.class)
        )).thenReturn(ResponseEntity.status(HttpStatus.OK)
            .body("{\"choices\":[{\"message\":{\"content\":\"{\\\"action\\\":\\\"HOLD\\\"}\"}}]}"));
        when(auditAiCallLogMapper.insertAuditAiCallLog(any(AuditAiCallLog.class))).thenReturn(1);

        AiModelConfigServiceImpl service = createRuntimeService(aiModelConfigMapper, auditAiCallLogMapper, restTemplate);

        RuntimeModelCallResponse response = service.callAiModelForRuntime(33L, "Return JSON only");

        assertEquals("{\"action\":\"HOLD\"}", response.getContent());
    }

    @Test
    void callAiModelForRuntimeAcceptsDirectJsonDecisionPayload() {
        AiModelConfigMapper aiModelConfigMapper = mock(AiModelConfigMapper.class);
        AuditAiCallLogMapper auditAiCallLogMapper = mock(AuditAiCallLogMapper.class);
        RestTemplate restTemplate = mock(RestTemplate.class);

        AiModelConfig config = new AiModelConfig();
        config.setId(34L);
        config.setModelCode("gpt-5.5");
        config.setProvider("openai");
        config.setApiKey("runtime-key");
        config.setApiEndpoint("https://api.sfkey.cn/v1/chat/completions");
        config.setIsEnabled(1);

        when(aiModelConfigMapper.selectAiModelConfigById(34L)).thenReturn(config);
        when(restTemplate.exchange(
            eq("https://api.sfkey.cn/v1/chat/completions"),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            eq(String.class)
        )).thenReturn(ResponseEntity.status(HttpStatus.OK).body("""
            {"action":"HOLD","side":"short","confidence":65,"size_hint":0.0,"leverage_hint":0,"holding_window":"4h-8h","invalidation":"price_break_above_range_high_2122.86_or_below_range_low_2114.5_with_confirmation","summary_reason":"range hold"}
            """));
        when(auditAiCallLogMapper.insertAuditAiCallLog(any(AuditAiCallLog.class))).thenReturn(1);

        AiModelConfigServiceImpl service = createRuntimeService(aiModelConfigMapper, auditAiCallLogMapper, restTemplate);

        RuntimeModelCallResponse response = service.callAiModelForRuntime(34L, "Return JSON only");

        assertEquals(34L, response.getModelId());
        assertEquals("gpt-5.5", response.getModelCode());
        assertEquals("openai", response.getModelProvider());
        assertEquals("{\"action\":\"HOLD\",\"side\":\"short\",\"confidence\":65,\"size_hint\":0.0,\"leverage_hint\":0,\"holding_window\":\"4h-8h\",\"invalidation\":\"price_break_above_range_high_2122.86_or_below_range_low_2114.5_with_confirmation\",\"summary_reason\":\"range hold\"}", response.getContent());
    }

    @Test
    void callAiModelForRuntimeFallsBackToModelVersionWhenModelCodeIsMissing() {
        AiModelConfigMapper aiModelConfigMapper = mock(AiModelConfigMapper.class);
        AuditAiCallLogMapper auditAiCallLogMapper = mock(AuditAiCallLogMapper.class);
        RestTemplate restTemplate = mock(RestTemplate.class);

        AiModelConfig config = new AiModelConfig();
        config.setId(31L);
        config.setModelCode(null);
        config.setModelVersion("deepseek-reasoner");
        config.setProvider("deepseek");
        config.setApiKey("runtime-key");
        config.setApiEndpoint("https://api.deepseek.com/chat/completions");
        config.setIsEnabled(1);

        when(aiModelConfigMapper.selectAiModelConfigById(31L)).thenReturn(config);
        when(restTemplate.exchange(
            eq("https://api.deepseek.com/chat/completions"),
            eq(HttpMethod.POST),
            any(HttpEntity.class),
            eq(String.class)
        )).thenReturn(ResponseEntity.status(HttpStatus.OK).body("""
            {"choices":[{"message":{"content":"{\\"action\\":\\"OPEN_LONG\\"}"}}]}
            """));
        when(auditAiCallLogMapper.insertAuditAiCallLog(any(AuditAiCallLog.class))).thenReturn(1);

        AiModelConfigServiceImpl service = createRuntimeService(aiModelConfigMapper, auditAiCallLogMapper, restTemplate);

        RuntimeModelCallResponse response = service.callAiModelForRuntime(31L, "Return JSON only");

        assertEquals("deepseek-reasoner", response.getModelCode());
    }

    @Test
    void insertAiModelConfigBackfillsModelCodeFromModelVersionWhenMissing() {
        AiModelConfigMapper aiModelConfigMapper = mock(AiModelConfigMapper.class);

        AiModelConfig config = new AiModelConfig();
        config.setModelKey("deepseek-reasoner");
        config.setModelName("DeepSeek R1");
        config.setModelCode(null);
        config.setModelVersion("deepseek-reasoner");
        config.setProvider("deepseek");
        config.setApiEndpoint("https://api.deepseek.com/chat/completions");
        config.setApiKeyEncrypted("ENC:test-key");

        when(aiModelConfigMapper.checkModelCodeUnique(null)).thenReturn(null);
        when(aiModelConfigMapper.insertAiModelConfig(any(AiModelConfig.class))).thenReturn(1);
        when(aiModelConfigMapper.selectDefaultModel()).thenReturn(new AiModelConfig());

        AiModelConfigServiceImpl service = new AiModelConfigServiceImpl();
        ReflectionTestUtils.setField(service, "aiModelConfigMapper", aiModelConfigMapper);

        service.insertAiModelConfig(config);

        ArgumentCaptor<AiModelConfig> captor = ArgumentCaptor.forClass(AiModelConfig.class);
        verify(aiModelConfigMapper).insertAiModelConfig(captor.capture());
        assertEquals("deepseek-reasoner", captor.getValue().getModelCode());
    }

    private AiModelConfigServiceImpl createRuntimeService(AiModelConfigMapper aiModelConfigMapper,
                                                          AuditAiCallLogMapper auditAiCallLogMapper,
                                                          RestTemplate runtimeRestTemplate) {
        TestableAiModelConfigServiceImpl service = new TestableAiModelConfigServiceImpl(runtimeRestTemplate);
        ReflectionTestUtils.setField(service, "aiModelConfigMapper", aiModelConfigMapper);
        ReflectionTestUtils.setField(service, "auditAiCallLogMapper", auditAiCallLogMapper);
        return service;
    }

    private static class TestableAiModelConfigServiceImpl extends AiModelConfigServiceImpl {
        private final RestTemplate runtimeRestTemplate;

        private TestableAiModelConfigServiceImpl(RestTemplate runtimeRestTemplate) {
            this.runtimeRestTemplate = runtimeRestTemplate;
        }

        protected RestTemplate createRuntimeRestTemplate(int timeoutSeconds) {
            return runtimeRestTemplate;
        }
    }
}
