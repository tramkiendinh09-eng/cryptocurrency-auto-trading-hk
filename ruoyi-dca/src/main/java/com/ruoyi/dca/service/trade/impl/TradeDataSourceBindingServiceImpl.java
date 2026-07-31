package com.ruoyi.dca.service.trade.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.constants.TradeConstants;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;
import com.ruoyi.dca.mapper.trade.TradeDataSourceBindingMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.IMarketApiConfigService;
import com.ruoyi.dca.service.trade.ITradeDataSourceBindingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

@Service
public class TradeDataSourceBindingServiceImpl implements ITradeDataSourceBindingService {

    private static final Set<String> ALLOWED_RUNTIME_MODES = Set.of("paper", "shadow", "live");

    @Autowired
    private TradeDataSourceBindingMapper tradeDataSourceBindingMapper;

    @Autowired
    private TradeStrategyMapper tradeStrategyMapper;

    @Autowired
    private IMarketApiConfigService marketApiConfigService;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public List<TradeDataSourceBinding> selectTradeDataSourceBindingList(TradeDataSourceBinding query) {
        return tradeDataSourceBindingMapper.selectTradeDataSourceBindingList(query);
    }

    @Override
    public int insertTradeDataSourceBinding(TradeDataSourceBinding tradeDataSourceBinding) {
        normalizeAndValidate(tradeDataSourceBinding);
        return tradeDataSourceBindingMapper.insertTradeDataSourceBinding(tradeDataSourceBinding);
    }

    @Override
    public int updateTradeDataSourceBinding(TradeDataSourceBinding tradeDataSourceBinding) {
        if (tradeDataSourceBinding == null || tradeDataSourceBinding.getId() == null) {
            throw new ServiceException("Data source binding id is required");
        }
        if (tradeDataSourceBindingMapper.selectTradeDataSourceBindingById(tradeDataSourceBinding.getId()) == null) {
            throw new ServiceException("Data source binding does not exist");
        }
        normalizeAndValidate(tradeDataSourceBinding);
        return tradeDataSourceBindingMapper.updateTradeDataSourceBinding(tradeDataSourceBinding);
    }

    @Override
    public int deleteTradeDataSourceBindingByIds(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return 0;
        }
        return tradeDataSourceBindingMapper.deleteTradeDataSourceBindingByIds(ids);
    }

    private void normalizeAndValidate(TradeDataSourceBinding tradeDataSourceBinding) {
        if (tradeDataSourceBinding == null) {
            throw new ServiceException("Data source binding payload is required");
        }
        tradeDataSourceBinding.setBindingName(trimToEmpty(tradeDataSourceBinding.getBindingName()));
        tradeDataSourceBinding.setEventType(normalizeLower(tradeDataSourceBinding.getEventType()));
        tradeDataSourceBinding.setSymbolScopeJson(normalizeJsonArray(tradeDataSourceBinding.getSymbolScopeJson(), new LinkedHashSet<>(TradeConstants.V1_ALLOWED_SYMBOLS), true));
        tradeDataSourceBinding.setExchangeScopeJson(normalizeJsonArray(tradeDataSourceBinding.getExchangeScopeJson(), new LinkedHashSet<>(TradeConstants.V1_ALLOWED_EXCHANGES), true));
        tradeDataSourceBinding.setModeScopeJson(normalizeJsonArray(tradeDataSourceBinding.getModeScopeJson(), ALLOWED_RUNTIME_MODES, false));
        if (tradeDataSourceBinding.getEnabled() == null) {
            tradeDataSourceBinding.setEnabled(Boolean.TRUE);
        }

        if (tradeDataSourceBinding.getBindingName().isEmpty()) {
            throw new ServiceException("Data source binding name is required");
        }
        if (tradeDataSourceBinding.getSourceId() == null) {
            throw new ServiceException("Data source binding requires sourceId");
        }
        MarketApiConfig marketApiConfig = marketApiConfigService.selectApiConfigById(tradeDataSourceBinding.getSourceId());
        if (marketApiConfig == null) {
            throw new ServiceException("Referenced market api source does not exist");
        }
        if (tradeDataSourceBinding.getStrategyId() != null
            && tradeStrategyMapper.selectTradeStrategyById(tradeDataSourceBinding.getStrategyId()) == null) {
            throw new ServiceException("Referenced strategy does not exist");
        }
        if (tradeDataSourceBinding.getEventType().isEmpty()) {
            throw new ServiceException("Data source binding eventType is required");
        }
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
            throw new ServiceException("Failed to serialize data source binding scope json");
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

    private String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
