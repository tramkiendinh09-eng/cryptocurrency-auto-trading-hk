package com.ruoyi.dca.service.trade.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.constants.TradeConstants;
import com.ruoyi.dca.domain.AiModelConfig;
import com.ruoyi.dca.domain.PromptTemplate;
import com.ruoyi.dca.domain.trade.TradePromptBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.mapper.trade.TradePromptBindingMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.IAiModelConfigService;
import com.ruoyi.dca.service.IPromptTemplateService;
import com.ruoyi.dca.service.trade.ITradePromptBindingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

@Service
public class TradePromptBindingServiceImpl implements ITradePromptBindingService {

    private static final Set<String> ALLOWED_RUNTIME_MODES = Set.of("paper", "shadow", "live");
    private static final Set<String> ALLOWED_EVENT_STRENGTHS = Set.of("strong", "normal", "noise");
    private static final Set<String> ALLOWED_BINDING_SCOPES = Set.of(
        "SUPERVISOR",
        "MARKET_AGENT",
        "NEWS_AGENT",
        "ONCHAIN_AGENT",
        "SOCIAL_AGENT",
        "DELIBERATION_REFEREE"
    );

    @Autowired
    private TradePromptBindingMapper tradePromptBindingMapper;

    @Autowired
    private TradeStrategyMapper tradeStrategyMapper;

    @Autowired
    private IPromptTemplateService promptTemplateService;

    @Autowired
    private IAiModelConfigService aiModelConfigService;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public List<TradePromptBinding> selectTradePromptBindingList(TradePromptBinding query) {
        return tradePromptBindingMapper.selectTradePromptBindingList(query);
    }

    @Override
    public int insertTradePromptBinding(TradePromptBinding tradePromptBinding) {
        normalizeAndValidate(tradePromptBinding);
        return tradePromptBindingMapper.insertTradePromptBinding(tradePromptBinding);
    }

    @Override
    public int updateTradePromptBinding(TradePromptBinding tradePromptBinding) {
        if (tradePromptBinding == null || tradePromptBinding.getId() == null) {
            throw new ServiceException("Prompt binding id is required");
        }
        TradePromptBinding existing = tradePromptBindingMapper.selectTradePromptBindingById(tradePromptBinding.getId());
        if (existing == null) {
            throw new ServiceException("Prompt binding does not exist");
        }
        TradePromptBinding merged = mergeWithExisting(existing, tradePromptBinding);
        normalizeAndValidate(merged);
        return tradePromptBindingMapper.updateTradePromptBinding(merged);
    }

    @Override
    public int deleteTradePromptBindingByIds(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return 0;
        }
        return tradePromptBindingMapper.deleteTradePromptBindingByIds(ids);
    }

    private void normalizeAndValidate(TradePromptBinding tradePromptBinding) {
        if (tradePromptBinding == null) {
            throw new ServiceException("Prompt binding payload is required");
        }
        tradePromptBinding.setBindingName(trimToEmpty(tradePromptBinding.getBindingName()));
        tradePromptBinding.setSymbol(normalizeUpperOrNull(tradePromptBinding.getSymbol()));
        tradePromptBinding.setExchangeCode(normalizeUpperOrNull(tradePromptBinding.getExchangeCode()));
        tradePromptBinding.setBindingScope(normalizeUpper(tradePromptBinding.getBindingScope()));
        tradePromptBinding.setTemplateCode(trimToNull(tradePromptBinding.getTemplateCode()));
        tradePromptBinding.setFallbackTemplateCode(trimToNull(tradePromptBinding.getFallbackTemplateCode()));
        tradePromptBinding.setOutputSchemaCode(trimToNull(tradePromptBinding.getOutputSchemaCode()));
        tradePromptBinding.setRemark(trimToNull(tradePromptBinding.getRemark()));
        tradePromptBinding.setModeScopeJson(normalizeJsonArray(tradePromptBinding.getModeScopeJson(), ALLOWED_RUNTIME_MODES, false));
        tradePromptBinding.setEventStrengthScopeJson(
            normalizeJsonArray(tradePromptBinding.getEventStrengthScopeJson(), ALLOWED_EVENT_STRENGTHS, false)
        );
        if (tradePromptBinding.getPriority() == null) {
            tradePromptBinding.setPriority(100);
        }
        if (tradePromptBinding.getEnabled() == null) {
            tradePromptBinding.setEnabled(Boolean.TRUE);
        }

        if (tradePromptBinding.getBindingName().isEmpty()) {
            throw new ServiceException("Prompt binding name is required");
        }
        if (!ALLOWED_BINDING_SCOPES.contains(tradePromptBinding.getBindingScope())) {
            throw new ServiceException("Unsupported prompt binding scope: " + tradePromptBinding.getBindingScope());
        }
        if (tradePromptBinding.getSymbol() != null && !TradeConstants.V1_ALLOWED_SYMBOLS.contains(tradePromptBinding.getSymbol())) {
            throw new ServiceException("Unsupported prompt binding symbol: " + tradePromptBinding.getSymbol());
        }
        if (tradePromptBinding.getExchangeCode() != null && !TradeConstants.V1_ALLOWED_EXCHANGES.contains(tradePromptBinding.getExchangeCode())) {
            throw new ServiceException("Unsupported prompt binding exchange: " + tradePromptBinding.getExchangeCode());
        }

        validateStrategyReferences(tradePromptBinding);
        validateTemplateCodes(tradePromptBinding);
        validateModelReference(tradePromptBinding.getModelId());
        validateOutputSchema(tradePromptBinding);
        validateDuplicateBinding(tradePromptBinding);
    }

    private void validateStrategyReferences(TradePromptBinding tradePromptBinding) {
        if (tradePromptBinding.getStrategyId() == null && tradePromptBinding.getStrategyVersionId() == null) {
            return;
        }
        if (tradePromptBinding.getStrategyId() == null) {
            throw new ServiceException("strategyId is required when strategyVersionId is provided");
        }
        TradeStrategy strategy = tradeStrategyMapper.selectTradeStrategyById(tradePromptBinding.getStrategyId());
        if (strategy == null) {
            throw new ServiceException("Referenced strategy does not exist");
        }
        if (tradePromptBinding.getStrategyVersionId() == null) {
            return;
        }
        boolean versionExists = false;
        for (TradeStrategyVersion version : tradeStrategyMapper.selectTradeStrategyVersions(tradePromptBinding.getStrategyId())) {
            if (version != null && tradePromptBinding.getStrategyVersionId().equals(version.getId())) {
                versionExists = true;
                break;
            }
        }
        if (!versionExists) {
            throw new ServiceException("Referenced strategy version does not belong to strategy");
        }
    }

    private void validateTemplateCodes(TradePromptBinding tradePromptBinding) {
        if (tradePromptBinding.getTemplateCode() == null && tradePromptBinding.getFallbackTemplateCode() == null) {
            return;
        }
        if (tradePromptBinding.getTemplateCode() == null) {
            throw new ServiceException("templateCode is required when fallbackTemplateCode override is provided");
        }
        PromptTemplate template = promptTemplateService.selectTemplateByCode(tradePromptBinding.getTemplateCode());
        if (template == null || !Integer.valueOf(1).equals(template.getIsActive())) {
            throw new ServiceException("Referenced prompt template does not exist or is not active");
        }
        if (tradePromptBinding.getFallbackTemplateCode() == null) {
            return;
        }
        PromptTemplate fallbackTemplate = promptTemplateService.selectTemplateByCode(tradePromptBinding.getFallbackTemplateCode());
        if (fallbackTemplate == null || !Integer.valueOf(1).equals(fallbackTemplate.getIsActive())) {
            throw new ServiceException("Referenced fallback prompt template does not exist or is not active");
        }
    }

    private void validateModelReference(Long modelId) {
        if (modelId == null) {
            return;
        }
        AiModelConfig config = aiModelConfigService.selectAiModelConfigById(modelId);
        if (config == null) {
            throw new ServiceException("Referenced model does not exist");
        }
        if (!Integer.valueOf(1).equals(config.getIsEnabled())) {
            throw new ServiceException("Referenced model is not enabled");
        }
    }

    private void validateOutputSchema(TradePromptBinding tradePromptBinding) {
        String bindingScope = tradePromptBinding.getBindingScope();
        String outputSchemaCode = tradePromptBinding.getOutputSchemaCode();
        if (outputSchemaCode == null) {
            return;
        }
        if ("SUPERVISOR".equals(bindingScope) && !"supervisor_decision_v1".equals(outputSchemaCode)) {
            throw new ServiceException("outputSchemaCode does not match SUPERVISOR binding scope");
        }
        if (Set.of("MARKET_AGENT", "NEWS_AGENT", "ONCHAIN_AGENT", "SOCIAL_AGENT").contains(bindingScope)
            && !"agent_view_v1".equals(outputSchemaCode)) {
            throw new ServiceException("outputSchemaCode does not match specialist agent binding scope");
        }
        if ("DELIBERATION_REFEREE".equals(bindingScope)
            && !Set.of("agent_view_v1", "deliberation_referee_v1").contains(outputSchemaCode)) {
            throw new ServiceException("outputSchemaCode does not match DELIBERATION_REFEREE binding scope");
        }
    }

    private void validateDuplicateBinding(TradePromptBinding tradePromptBinding) {
        TradePromptBinding query = new TradePromptBinding();
        query.setEnabled(Boolean.TRUE);
        List<TradePromptBinding> existingBindings = tradePromptBindingMapper.selectTradePromptBindingList(query);
        if (existingBindings == null || existingBindings.isEmpty()) {
            return;
        }
        for (TradePromptBinding existing : existingBindings) {
            if (existing == null) {
                continue;
            }
            if (tradePromptBinding.getId() != null && tradePromptBinding.getId().equals(existing.getId())) {
                continue;
            }
            if (!sameNullableLong(existing.getStrategyId(), tradePromptBinding.getStrategyId())) {
                continue;
            }
            if (!sameNullableLong(existing.getStrategyVersionId(), tradePromptBinding.getStrategyVersionId())) {
                continue;
            }
            if (!sameNullableText(existing.getSymbol(), tradePromptBinding.getSymbol())) {
                continue;
            }
            if (!sameNullableText(existing.getExchangeCode(), tradePromptBinding.getExchangeCode())) {
                continue;
            }
            if (!sameNullableText(existing.getBindingScope(), tradePromptBinding.getBindingScope())) {
                continue;
            }
            if (!sameNullableText(existing.getModeScopeJson(), tradePromptBinding.getModeScopeJson())) {
                continue;
            }
            if (!sameNullableText(existing.getEventStrengthScopeJson(), tradePromptBinding.getEventStrengthScopeJson())) {
                continue;
            }
            throw new ServiceException("Duplicate enabled prompt binding already exists for scope");
        }
    }

    private TradePromptBinding mergeWithExisting(TradePromptBinding existing, TradePromptBinding patch) {
        TradePromptBinding merged = new TradePromptBinding();
        merged.setId(existing.getId());
        merged.setBindingName(firstNonNull(patch.getBindingName(), existing.getBindingName()));
        merged.setStrategyId(firstNonNull(patch.getStrategyId(), existing.getStrategyId()));
        merged.setStrategyVersionId(firstNonNull(patch.getStrategyVersionId(), existing.getStrategyVersionId()));
        merged.setSymbol(firstNonNull(patch.getSymbol(), existing.getSymbol()));
        merged.setExchangeCode(firstNonNull(patch.getExchangeCode(), existing.getExchangeCode()));
        merged.setBindingScope(firstNonNull(patch.getBindingScope(), existing.getBindingScope()));
        merged.setTemplateCode(firstNonNull(patch.getTemplateCode(), existing.getTemplateCode()));
        merged.setFallbackTemplateCode(firstNonNull(patch.getFallbackTemplateCode(), existing.getFallbackTemplateCode()));
        merged.setModelId(firstNonNull(patch.getModelId(), existing.getModelId()));
        merged.setOutputSchemaCode(firstNonNull(patch.getOutputSchemaCode(), existing.getOutputSchemaCode()));
        merged.setPriority(firstNonNull(patch.getPriority(), existing.getPriority()));
        merged.setModeScopeJson(firstNonNull(patch.getModeScopeJson(), existing.getModeScopeJson()));
        merged.setEventStrengthScopeJson(firstNonNull(patch.getEventStrengthScopeJson(), existing.getEventStrengthScopeJson()));
        merged.setEnabled(firstNonNull(patch.getEnabled(), existing.getEnabled()));
        merged.setRemark(firstNonNull(patch.getRemark(), existing.getRemark()));
        return merged;
    }

    private String normalizeJsonArray(String json, Set<String> allowedValues, boolean uppercase) {
        List<String> values = parseJsonArray(json);
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (String value : values) {
            String normalizedValue = uppercase ? normalizeUpper(value) : normalizeLower(value);
            if (normalizedValue.isEmpty()) {
                continue;
            }
            if (!allowedValues.contains(normalizedValue)) {
                throw new ServiceException("Unsupported scope value: " + normalizedValue);
            }
            normalized.add(normalizedValue);
        }
        try {
            return objectMapper.writeValueAsString(new ArrayList<>(normalized));
        } catch (IOException e) {
            throw new ServiceException("Failed to serialize prompt binding scope json");
        }
    }

    private List<String> parseJsonArray(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<String> parsed = objectMapper.readValue(json, new TypeReference<>() {});
            return parsed == null ? List.of() : parsed;
        } catch (IOException e) {
            throw new ServiceException("Invalid json array payload");
        }
    }

    private String normalizeUpperOrNull(String value) {
        String normalized = normalizeUpper(value);
        return normalized.isEmpty() ? null : normalized;
    }

    private String normalizeUpper(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toUpperCase(Locale.ROOT);
    }

    private String normalizeLower(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toLowerCase(Locale.ROOT);
    }

    private String trimToNull(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? null : trimmed;
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private boolean sameNullableLong(Long left, Long right) {
        return left == null ? right == null : left.equals(right);
    }

    private boolean sameNullableText(String left, String right) {
        String normalizedLeft = left == null ? null : left.trim();
        String normalizedRight = right == null ? null : right.trim();
        return normalizedLeft == null ? normalizedRight == null : normalizedLeft.equalsIgnoreCase(normalizedRight);
    }

    private <T> T firstNonNull(T preferred, T fallback) {
        return preferred != null ? preferred : fallback;
    }
}
