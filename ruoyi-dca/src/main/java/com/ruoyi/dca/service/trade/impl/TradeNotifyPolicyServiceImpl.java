package com.ruoyi.dca.service.trade.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.NotifyChannel;
import com.ruoyi.dca.domain.NotifyTemplate;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicy;
import com.ruoyi.dca.domain.trade.TradeNotifyPolicyChannel;
import com.ruoyi.dca.mapper.NotifyChannelMapper;
import com.ruoyi.dca.mapper.trade.TradeNotifyPolicyMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.INotifyTemplateService;
import com.ruoyi.dca.service.trade.ITradeNotifyPolicyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

@Service
public class TradeNotifyPolicyServiceImpl implements ITradeNotifyPolicyService {

    private static final Set<String> ALLOWED_POLICY_SCOPES = Set.of("GLOBAL", "STRATEGY");
    private static final Set<String> ALLOWED_RUNTIME_MODES = Set.of("paper", "shadow", "live");

    @Autowired
    private TradeNotifyPolicyMapper tradeNotifyPolicyMapper;

    @Autowired
    private TradeStrategyMapper tradeStrategyMapper;

    @Autowired
    private NotifyChannelMapper notifyChannelMapper;

    @Autowired
    private INotifyTemplateService notifyTemplateService;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public List<TradeNotifyPolicy> selectTradeNotifyPolicyList(TradeNotifyPolicy query) {
        List<TradeNotifyPolicy> list = tradeNotifyPolicyMapper.selectTradeNotifyPolicyList(query);
        for (TradeNotifyPolicy policy : list) {
            if (policy.getId() != null) {
                policy.setChannelBindings(tradeNotifyPolicyMapper.selectTradeNotifyPolicyChannels(policy.getId()));
            }
        }
        return list;
    }

    @Override
    public int insertTradeNotifyPolicy(TradeNotifyPolicy tradeNotifyPolicy) {
        normalizeAndValidate(tradeNotifyPolicy);
        int rows = tradeNotifyPolicyMapper.insertTradeNotifyPolicy(tradeNotifyPolicy);
        if (rows > 0) {
            syncChannels(tradeNotifyPolicy);
        }
        return rows;
    }

    @Override
    public int updateTradeNotifyPolicy(TradeNotifyPolicy tradeNotifyPolicy) {
        if (tradeNotifyPolicy == null || tradeNotifyPolicy.getId() == null) {
            throw new ServiceException("Notify policy id is required");
        }
        if (tradeNotifyPolicyMapper.selectTradeNotifyPolicyById(tradeNotifyPolicy.getId()) == null) {
            throw new ServiceException("Notify policy does not exist");
        }
        normalizeAndValidate(tradeNotifyPolicy);
        int rows = tradeNotifyPolicyMapper.updateTradeNotifyPolicy(tradeNotifyPolicy);
        if (rows > 0) {
            syncChannels(tradeNotifyPolicy);
        }
        return rows;
    }

    @Override
    public int deleteTradeNotifyPolicyByIds(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return 0;
        }
        tradeNotifyPolicyMapper.deleteTradeNotifyPolicyChannelsByPolicyIds(ids);
        return tradeNotifyPolicyMapper.deleteTradeNotifyPolicyByIds(ids);
    }

    private void syncChannels(TradeNotifyPolicy tradeNotifyPolicy) {
        if (tradeNotifyPolicy.getId() == null) {
            throw new ServiceException("Notify policy id is required for channel binding persistence");
        }
        tradeNotifyPolicyMapper.deleteTradeNotifyPolicyChannelsByPolicyId(tradeNotifyPolicy.getId());
        if (tradeNotifyPolicy.getChannelBindings() == null || tradeNotifyPolicy.getChannelBindings().isEmpty()) {
            return;
        }
        for (TradeNotifyPolicyChannel channel : tradeNotifyPolicy.getChannelBindings()) {
            channel.setPolicyId(tradeNotifyPolicy.getId());
        }
        tradeNotifyPolicyMapper.insertTradeNotifyPolicyChannels(tradeNotifyPolicy.getChannelBindings());
    }

    private void normalizeAndValidate(TradeNotifyPolicy tradeNotifyPolicy) {
        if (tradeNotifyPolicy == null) {
            throw new ServiceException("Notify policy payload is required");
        }
        tradeNotifyPolicy.setPolicyName(trimToEmpty(tradeNotifyPolicy.getPolicyName()));
        tradeNotifyPolicy.setPolicyScope(defaultIfBlank(
            normalizeUpper(tradeNotifyPolicy.getPolicyScope()),
            tradeNotifyPolicy.getStrategyId() == null ? "GLOBAL" : "STRATEGY"
        ));
        tradeNotifyPolicy.setEventScopeJson(normalizeJsonArray(tradeNotifyPolicy.getEventScopeJson(), false, false));
        tradeNotifyPolicy.setSeverityScopeJson(normalizeJsonArray(tradeNotifyPolicy.getSeverityScopeJson(), true, false));
        tradeNotifyPolicy.setModeScopeJson(normalizeJsonArray(tradeNotifyPolicy.getModeScopeJson(), false, true));
        tradeNotifyPolicy.setNotifyTemplateCode(trimToEmpty(tradeNotifyPolicy.getNotifyTemplateCode()));
        if (tradeNotifyPolicy.getThrottleSeconds() == null) {
            tradeNotifyPolicy.setThrottleSeconds(0);
        }
        if (tradeNotifyPolicy.getEnabled() == null) {
            tradeNotifyPolicy.setEnabled(Boolean.TRUE);
        }

        if (tradeNotifyPolicy.getPolicyName().isEmpty()) {
            throw new ServiceException("Notify policy name is required");
        }
        if (!ALLOWED_POLICY_SCOPES.contains(tradeNotifyPolicy.getPolicyScope())) {
            throw new ServiceException("Notify policy scope must be GLOBAL or STRATEGY");
        }
        if ("STRATEGY".equals(tradeNotifyPolicy.getPolicyScope())) {
            if (tradeNotifyPolicy.getStrategyId() == null) {
                throw new ServiceException("Strategy-scoped notify policy requires strategyId");
            }
            if (tradeStrategyMapper.selectTradeStrategyById(tradeNotifyPolicy.getStrategyId()) == null) {
                throw new ServiceException("Referenced strategy does not exist");
            }
        } else {
            tradeNotifyPolicy.setStrategyId(null);
        }
        if ("[]".equals(tradeNotifyPolicy.getEventScopeJson())) {
            throw new ServiceException("Notify policy event scope is required");
        }
        if ("[]".equals(tradeNotifyPolicy.getSeverityScopeJson())) {
            throw new ServiceException("Notify policy severity scope is required");
        }
        if ("[]".equals(tradeNotifyPolicy.getModeScopeJson())) {
            throw new ServiceException("Notify policy mode scope is required");
        }
        if (tradeNotifyPolicy.getThrottleSeconds() < 0) {
            throw new ServiceException("Notify policy throttleSeconds must be >= 0");
        }
        if (tradeNotifyPolicy.getNotifyTemplateCode().isEmpty()) {
            throw new ServiceException("Notify policy notifyTemplateCode is required");
        }
        NotifyTemplate notifyTemplate = notifyTemplateService.selectNotifyTemplateByCode(tradeNotifyPolicy.getNotifyTemplateCode());
        if (notifyTemplate == null || !Integer.valueOf(1).equals(notifyTemplate.getIsActive())) {
            throw new ServiceException("Referenced notify template does not exist or is not active");
        }

        List<TradeNotifyPolicyChannel> normalizedChannels = normalizeChannels(tradeNotifyPolicy.getChannelBindings());
        if (normalizedChannels.isEmpty()) {
            throw new ServiceException("Notify policy requires at least one channel binding");
        }
        tradeNotifyPolicy.setChannelBindings(normalizedChannels);
    }

    private List<TradeNotifyPolicyChannel> normalizeChannels(List<TradeNotifyPolicyChannel> channels) {
        if (channels == null || channels.isEmpty()) {
            return List.of();
        }
        List<TradeNotifyPolicyChannel> normalized = new ArrayList<>();
        Set<Long> seenChannelIds = new LinkedHashSet<>();
        int nextOrder = 1;
        for (TradeNotifyPolicyChannel channel : channels) {
            if (channel == null || channel.getChannelId() == null || !seenChannelIds.add(channel.getChannelId())) {
                continue;
            }
            NotifyChannel notifyChannel = notifyChannelMapper.selectNotifyChannelById(channel.getChannelId());
            if (notifyChannel == null) {
                throw new ServiceException("Referenced notify channel does not exist: " + channel.getChannelId());
            }
            channel.setChannelOrder(channel.getChannelOrder() == null || channel.getChannelOrder() <= 0
                ? nextOrder
                : channel.getChannelOrder());
            channel.setEnabled(channel.getEnabled() == null ? Boolean.TRUE : channel.getEnabled());
            normalized.add(channel);
            nextOrder++;
        }
        return normalized;
    }

    private String normalizeJsonArray(String json, boolean uppercase, boolean validateMode) {
        List<String> values = parseJsonArray(json);
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (String value : values) {
            String normalizedValue = uppercase ? normalizeUpper(value) : normalizeLower(value);
            if (normalizedValue.isEmpty()) {
                continue;
            }
            if (validateMode && !ALLOWED_RUNTIME_MODES.contains(normalizedValue)) {
                throw new ServiceException("Unsupported runtime mode: " + normalizedValue);
            }
            normalized.add(normalizedValue);
        }
        try {
            return objectMapper.writeValueAsString(new ArrayList<>(normalized));
        } catch (IOException e) {
            throw new ServiceException("Failed to serialize notify policy scope json");
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

    private String normalizeUpper(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toUpperCase(Locale.ROOT);
    }

    private String normalizeLower(String value) {
        String trimmed = trimToEmpty(value);
        return trimmed.isEmpty() ? "" : trimmed.toLowerCase(Locale.ROOT);
    }

    private String defaultIfBlank(String value, String defaultValue) {
        return value == null || value.isEmpty() ? defaultValue : value;
    }

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
