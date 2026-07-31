package com.ruoyi.dca.service.trade.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.PromptTemplate;
import com.ruoyi.dca.domain.trade.TradeAgentProfile;
import com.ruoyi.dca.mapper.trade.TradeAgentProfileMapper;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.IPromptTemplateService;
import com.ruoyi.dca.service.trade.ITradeAgentProfileService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

@Service
public class TradeAgentProfileServiceImpl implements ITradeAgentProfileService {

    private static final Set<String> ALLOWED_AGENT_CODES = Set.of(
        "market_agent",
        "news_agent",
        "onchain_agent",
        "social_agent",
        "supervisor_agent",
        "deliberation_referee"
    );
    private static final Set<String> ALLOWED_AGENT_TYPES = Set.of("RULE", "LLM", "HYBRID");
    private static final int MAX_DIALOGUE_ROUNDS_LIMIT = 2;
    private static final int DEFAULT_SPEAK_ORDER = 100;
    private static final int DEFAULT_TIMEOUT_SECONDS = 30;
    private static final int DEFAULT_MAX_RETRIES = 1;
    private static final String DEFAULT_JSON_OBJECT = "{}";
    private static final String SUPERVISOR_SCHEMA_CODE = "supervisor_decision_v1";
    private static final String SPECIALIST_SCHEMA_CODE = "agent_view_v1";
    private static final Set<String> SPECIALIST_AGENT_CODES = Set.of(
        "market_agent",
        "news_agent",
        "onchain_agent",
        "social_agent"
    );

    @Autowired
    private TradeAgentProfileMapper tradeAgentProfileMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private IAiModelConfigService aiModelConfigService;

    @Autowired
    private IPromptTemplateService promptTemplateService;

    @Override
    public List<TradeAgentProfile> selectTradeAgentProfileList(TradeAgentProfile query) {
        return tradeAgentProfileMapper.selectTradeAgentProfileList(query);
    }

    @Override
    public TradeAgentProfile selectTradeAgentProfileById(Long id) {
        return tradeAgentProfileMapper.selectTradeAgentProfileById(id);
    }

    @Override
    public int insertTradeAgentProfile(TradeAgentProfile tradeAgentProfile) {
        normalizeAndValidate(tradeAgentProfile);
        return tradeAgentProfileMapper.insertTradeAgentProfile(tradeAgentProfile);
    }

    @Override
    public int updateTradeAgentProfile(TradeAgentProfile tradeAgentProfile) {
        if (tradeAgentProfile == null || tradeAgentProfile.getId() == null) {
            throw new ServiceException("Trade agent profile id is required");
        }
        if (tradeAgentProfileMapper.selectTradeAgentProfileById(tradeAgentProfile.getId()) == null) {
            throw new ServiceException("Trade agent profile does not exist");
        }
        normalizeAndValidate(tradeAgentProfile);
        return tradeAgentProfileMapper.updateTradeAgentProfile(tradeAgentProfile);
    }

    @Override
    public int deleteTradeAgentProfileByIds(Long[] ids) {
        return tradeAgentProfileMapper.deleteTradeAgentProfileByIds(ids);
    }

    private void normalizeAndValidate(TradeAgentProfile tradeAgentProfile) {
        if (tradeAgentProfile == null) {
            throw new ServiceException("Trade agent profile payload is required");
        }
        tradeAgentProfile.setAgentCode(normalizeLower(tradeAgentProfile.getAgentCode()));
        tradeAgentProfile.setAgentName(trimToEmpty(tradeAgentProfile.getAgentName()));
        tradeAgentProfile.setAgentType(normalizeUpper(tradeAgentProfile.getAgentType()));
        tradeAgentProfile.setStructuredSchemaCode(trimToEmpty(tradeAgentProfile.getStructuredSchemaCode()));
        tradeAgentProfile.setDefaultTemplateCode(trimToNull(tradeAgentProfile.getDefaultTemplateCode()));
        tradeAgentProfile.setDefaultFallbackTemplateCode(trimToNull(tradeAgentProfile.getDefaultFallbackTemplateCode()));
        tradeAgentProfile.setDefaultOutputSchemaCode(trimToNull(tradeAgentProfile.getDefaultOutputSchemaCode()));
        tradeAgentProfile.setToolPolicyJson(normalizeObjectJson(tradeAgentProfile.getToolPolicyJson(), "toolPolicyJson"));
        tradeAgentProfile.setRuntimeOptionsJson(normalizeObjectJson(tradeAgentProfile.getRuntimeOptionsJson(), "runtimeOptionsJson"));
        tradeAgentProfile.setRemark(trimToNull(tradeAgentProfile.getRemark()));

        if (tradeAgentProfile.getEnabled() == null) {
            tradeAgentProfile.setEnabled(Boolean.TRUE);
        }
        if (tradeAgentProfile.getSpeakOrder() == null) {
            tradeAgentProfile.setSpeakOrder(DEFAULT_SPEAK_ORDER);
        }
        if (tradeAgentProfile.getTimeoutSeconds() == null) {
            tradeAgentProfile.setTimeoutSeconds(DEFAULT_TIMEOUT_SECONDS);
        }
        if (tradeAgentProfile.getMaxRetries() == null) {
            tradeAgentProfile.setMaxRetries(DEFAULT_MAX_RETRIES);
        }
        if (tradeAgentProfile.getDialogueEnabled() == null) {
            tradeAgentProfile.setDialogueEnabled(Boolean.FALSE);
        }

        if (tradeAgentProfile.getAgentCode().isEmpty()) {
            throw new ServiceException("agentCode is required");
        }
        if (!ALLOWED_AGENT_CODES.contains(tradeAgentProfile.getAgentCode())) {
            throw new ServiceException("Unsupported agentCode: " + tradeAgentProfile.getAgentCode());
        }
        if (tradeAgentProfile.getAgentName().isEmpty()) {
            throw new ServiceException("agentName is required");
        }
        if (!ALLOWED_AGENT_TYPES.contains(tradeAgentProfile.getAgentType())) {
            throw new ServiceException("Unsupported agentType: " + tradeAgentProfile.getAgentType());
        }
        if (tradeAgentProfile.getStructuredSchemaCode().isEmpty()) {
            throw new ServiceException("structuredSchemaCode is required");
        }
        if (tradeAgentProfile.getSpeakOrder() < 0) {
            throw new ServiceException("speakOrder must be greater than or equal to 0");
        }
        if (tradeAgentProfile.getTimeoutSeconds() < 1) {
            throw new ServiceException("timeoutSeconds must be greater than 0");
        }
        if (tradeAgentProfile.getMaxRetries() < 0) {
            throw new ServiceException("maxRetries must be greater than or equal to 0");
        }
        validateProbability(tradeAgentProfile.getTemperatureOverride(), "temperatureOverride");
        validateProbability(tradeAgentProfile.getTopPOverride(), "topPOverride");

        boolean ruleAgent = "RULE".equals(tradeAgentProfile.getAgentType());
        if (tradeAgentProfile.getLlmEnabled() == null) {
            tradeAgentProfile.setLlmEnabled(!ruleAgent);
        }
        if (ruleAgent && Boolean.TRUE.equals(tradeAgentProfile.getLlmEnabled())) {
            throw new ServiceException("RULE agentType does not support llmEnabled=true");
        }

        if (Boolean.TRUE.equals(tradeAgentProfile.getDialogueEnabled())) {
            if (tradeAgentProfile.getMaxDialogueRounds() == null) {
                tradeAgentProfile.setMaxDialogueRounds(1);
            }
            if (tradeAgentProfile.getMaxDialogueRounds() < 0 || tradeAgentProfile.getMaxDialogueRounds() > MAX_DIALOGUE_ROUNDS_LIMIT) {
                throw new ServiceException("maxDialogueRounds exceeds bounded deliberation limit");
            }
        } else {
            tradeAgentProfile.setMaxDialogueRounds(0);
        }

        if (tradeAgentProfile.getDefaultOutputSchemaCode() == null) {
            tradeAgentProfile.setDefaultOutputSchemaCode(tradeAgentProfile.getStructuredSchemaCode());
        }
        validateDefaultSchema(tradeAgentProfile);
        validateDefaultLlmConfig(tradeAgentProfile);
    }

    private void validateDefaultSchema(TradeAgentProfile tradeAgentProfile) {
        String schemaCode = tradeAgentProfile.getDefaultOutputSchemaCode();
        if ("supervisor_agent".equals(tradeAgentProfile.getAgentCode()) && !SUPERVISOR_SCHEMA_CODE.equals(schemaCode)) {
            throw new ServiceException("defaultOutputSchemaCode must be " + SUPERVISOR_SCHEMA_CODE + " for supervisor_agent");
        }
        if (SPECIALIST_AGENT_CODES.contains(tradeAgentProfile.getAgentCode()) && !SPECIALIST_SCHEMA_CODE.equals(schemaCode)) {
            throw new ServiceException("defaultOutputSchemaCode must be " + SPECIALIST_SCHEMA_CODE + " for specialist agents");
        }
    }

    private void validateDefaultLlmConfig(TradeAgentProfile tradeAgentProfile) {
        if (!Boolean.TRUE.equals(tradeAgentProfile.getLlmEnabled())) {
            return;
        }
        if (tradeAgentProfile.getDefaultModelId() == null) {
            throw new ServiceException("defaultModelId is required when llmEnabled=true");
        }
        if (tradeAgentProfile.getDefaultTemplateCode() == null) {
            throw new ServiceException("defaultTemplateCode is required when llmEnabled=true");
        }
        AiModelConfig modelConfig = aiModelConfigService.selectAiModelConfigById(tradeAgentProfile.getDefaultModelId());
        if (modelConfig == null || !Integer.valueOf(1).equals(modelConfig.getIsEnabled())) {
            throw new ServiceException("defaultModelId must reference an enabled AI model");
        }
        validateActiveTemplate(tradeAgentProfile.getDefaultTemplateCode(), "defaultTemplateCode");
        if (tradeAgentProfile.getDefaultFallbackTemplateCode() != null) {
            validateActiveTemplate(tradeAgentProfile.getDefaultFallbackTemplateCode(), "defaultFallbackTemplateCode");
        }
    }

    private void validateActiveTemplate(String templateCode, String fieldName) {
        PromptTemplate template = promptTemplateService.selectTemplateByCode(templateCode);
        if (template == null || !Integer.valueOf(1).equals(template.getIsActive())) {
            throw new ServiceException(fieldName + " must reference an active prompt template");
        }
    }

    private void validateProbability(BigDecimal value, String fieldName) {
        if (value == null) {
            return;
        }
        if (value.compareTo(BigDecimal.ZERO) < 0 || value.compareTo(BigDecimal.ONE) > 0) {
            throw new ServiceException(fieldName + " must be between 0 and 1");
        }
    }

    private String normalizeObjectJson(String rawJson, String fieldName) {
        if (rawJson == null || rawJson.isBlank()) {
            return DEFAULT_JSON_OBJECT;
        }
        try {
            Map<String, Object> parsed = objectMapper.readValue(rawJson, new TypeReference<Map<String, Object>>() {});
            return objectMapper.writeValueAsString(parsed == null ? Map.of() : new LinkedHashMap<>(parsed));
        } catch (IOException e) {
            throw new ServiceException(fieldName + " must be a JSON object");
        }
    }

    private String normalizeLower(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toLowerCase(Locale.ROOT);
    }

    private String normalizeUpper(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toUpperCase(Locale.ROOT);
    }

    private String trimToNull(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? null : trimmed;
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
