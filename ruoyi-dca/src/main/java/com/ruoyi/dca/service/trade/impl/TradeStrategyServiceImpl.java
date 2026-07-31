package com.ruoyi.dca.service.trade.impl;

import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeSymbolScope;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.trade.ITradeStrategyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class TradeStrategyServiceImpl implements ITradeStrategyService {

    @Autowired
    private TradeStrategyMapper tradeStrategyMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public List<TradeStrategy> selectTradeStrategyList(TradeStrategy query) {
        return tradeStrategyMapper.selectTradeStrategyList(query);
    }

    @Override
    public int insertTradeStrategy(TradeStrategy tradeStrategy) {
        int rows = tradeStrategyMapper.insertTradeStrategy(tradeStrategy);
        if (rows > 0) {
            syncTradeSymbolScopes(tradeStrategy);
            saveStrategyVersionSnapshot(tradeStrategy);
        }
        return rows;
    }

    @Override
    public int updateTradeStrategy(TradeStrategy tradeStrategy) {
        int rows = tradeStrategyMapper.updateTradeStrategy(tradeStrategy);
        if (rows > 0) {
            syncTradeSymbolScopes(tradeStrategy);
            saveStrategyVersionSnapshot(tradeStrategy);
        }
        return rows;
    }

    @Override
    public int deleteTradeStrategyByIds(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return 0;
        }
        tradeStrategyMapper.deleteTradeStrategyVersionsByStrategyIds(ids);
        tradeStrategyMapper.deleteTradeSymbolScopesByStrategyIds(ids);
        tradeStrategyMapper.deleteExchangeAccountBindingsByStrategyIds(ids);
        return tradeStrategyMapper.deleteTradeStrategyByIds(ids);
    }

    @Override
    public List<TradeStrategyVersion> selectTradeStrategyVersions(Long strategyId) {
        return tradeStrategyMapper.selectTradeStrategyVersions(strategyId);
    }

    @Override
    public List<ExchangeAccountBinding> selectExchangeAccountBindings(Long strategyId) {
        return tradeStrategyMapper.selectExchangeAccountBindings(strategyId);
    }

    @Override
    public int replaceExchangeAccountBindings(Long strategyId, List<ExchangeAccountBinding> bindings) {
        tradeStrategyMapper.deleteExchangeAccountBindingsByStrategyId(strategyId);
        if (bindings == null || bindings.isEmpty()) {
            return 0;
        }
        for (ExchangeAccountBinding binding : bindings) {
            binding.setStrategyId(strategyId);
        }
        return tradeStrategyMapper.insertExchangeAccountBindings(bindings);
    }

    private void saveStrategyVersionSnapshot(TradeStrategy tradeStrategy) {
        if (tradeStrategy.getId() == null) {
            return;
        }
        TradeStrategyVersion version = new TradeStrategyVersion();
        version.setStrategyId(tradeStrategy.getId());
        Integer currentMaxVersionNo = tradeStrategyMapper.selectMaxVersionNo(tradeStrategy.getId());
        version.setVersionNo(currentMaxVersionNo == null ? 1 : currentMaxVersionNo + 1);
        TradeStrategyVersion previousVersion = currentMaxVersionNo == null
            ? null
            : tradeStrategyMapper.selectLatestTradeStrategyVersion(tradeStrategy.getId());
        version.setConfigJson(buildVersionConfigJson(tradeStrategy, previousVersion));
        tradeStrategyMapper.insertTradeStrategyVersion(version);
    }

    private String buildVersionConfigJson(TradeStrategy tradeStrategy, TradeStrategyVersion previousVersion) {
        Map<String, Object> payload = new LinkedHashMap<>(parseVersionConfig(previousVersion == null ? null : previousVersion.getConfigJson()));
        payload.putAll(parseVersionConfig(tradeStrategy.getConfigJson()));
        payload.put("strategyKey", tradeStrategy.getStrategyKey());
        payload.put("strategyName", tradeStrategy.getStrategyName());
        payload.put("runtimeMode", tradeStrategy.getRuntimeMode() != null ? tradeStrategy.getRuntimeMode().name() : null);
        payload.put("symbolsJson", tradeStrategy.getSymbolsJson());
        payload.put("exchangesJson", tradeStrategy.getExchangesJson());
        payload.put("enabled", tradeStrategy.getEnabled());
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Failed to serialize trade strategy version payload", e);
        }
    }

    private Map<String, Object> parseVersionConfig(String json) {
        if (json == null || json.isBlank()) {
            return new HashMap<>();
        }
        try {
            Map<String, Object> parsed = objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
            return parsed == null ? new HashMap<>() : new LinkedHashMap<>(parsed);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to parse trade strategy version config json", e);
        }
    }

    private void syncTradeSymbolScopes(TradeStrategy tradeStrategy) {
        if (tradeStrategy.getId() == null) {
            return;
        }
        tradeStrategyMapper.deleteTradeSymbolScopesByStrategyId(tradeStrategy.getId());
        List<TradeSymbolScope> scopes = buildTradeSymbolScopes(tradeStrategy);
        if (!scopes.isEmpty()) {
            tradeStrategyMapper.insertTradeSymbolScopes(scopes);
        }
    }

    private List<TradeSymbolScope> buildTradeSymbolScopes(TradeStrategy tradeStrategy) {
        List<String> symbols = parseJsonArray(tradeStrategy.getSymbolsJson());
        List<String> exchanges = parseJsonArray(tradeStrategy.getExchangesJson());
        List<TradeSymbolScope> scopes = new ArrayList<>();
        for (String symbol : symbols) {
            for (String exchange : exchanges) {
                TradeSymbolScope scope = new TradeSymbolScope();
                scope.setStrategyId(tradeStrategy.getId());
                scope.setSymbol(symbol);
                scope.setExchangeCode(exchange);
                scopes.add(scope);
            }
        }
        return scopes;
    }

    private List<String> parseJsonArray(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {})
                .stream()
                .filter(value -> value != null && !value.isBlank())
                .collect(Collectors.toList());
        } catch (IOException e) {
            throw new IllegalStateException("Failed to parse trade strategy scope json", e);
        }
    }
}
