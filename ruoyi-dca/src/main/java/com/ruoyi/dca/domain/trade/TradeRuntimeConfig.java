package com.ruoyi.dca.domain.trade;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.enums.TradeRuntimeMode;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class TradeRuntimeConfig {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private Long id;
    private TradeRuntimeMode defaultMode;
    private Boolean liveEnabled;
    private BigDecimal maxPositionRatio;
    private BigDecimal maxDailyLoss;
    private Integer maxConsecutiveFailures;
    private String allowedSymbolsJson;
    private String allowedExchangesJson;
    private Boolean requireAccountBinding;
    private Boolean liveOrderRequiresHealthyAccount;
    private String runtimeFlagsJson;
    private String notifyDefaultsJson;
    private Integer eventRetentionDays;
    private Integer replayRetentionDays;
    private Boolean deliberationEnabled;
    private Integer deliberationMaxRounds;
    private Boolean deliberationFailOpen;
    private Integer routeMaxConcurrency;
    private String routeSchedulerMode;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public TradeRuntimeMode getDefaultMode() {
        return defaultMode;
    }

    public void setDefaultMode(TradeRuntimeMode defaultMode) {
        this.defaultMode = defaultMode;
    }

    public Boolean getLiveEnabled() {
        return liveEnabled;
    }

    public void setLiveEnabled(Boolean liveEnabled) {
        this.liveEnabled = liveEnabled;
    }

    public BigDecimal getMaxPositionRatio() {
        return maxPositionRatio;
    }

    public void setMaxPositionRatio(BigDecimal maxPositionRatio) {
        this.maxPositionRatio = maxPositionRatio;
    }

    public BigDecimal getMaxDailyLoss() {
        return maxDailyLoss;
    }

    public void setMaxDailyLoss(BigDecimal maxDailyLoss) {
        this.maxDailyLoss = maxDailyLoss;
    }

    public Integer getMaxConsecutiveFailures() {
        return maxConsecutiveFailures;
    }

    public void setMaxConsecutiveFailures(Integer maxConsecutiveFailures) {
        this.maxConsecutiveFailures = maxConsecutiveFailures;
    }

    public String getAllowedSymbolsJson() {
        return allowedSymbolsJson;
    }

    public void setAllowedSymbolsJson(String allowedSymbolsJson) {
        this.allowedSymbolsJson = allowedSymbolsJson;
    }

    public String getAllowedExchangesJson() {
        return allowedExchangesJson;
    }

    public void setAllowedExchangesJson(String allowedExchangesJson) {
        this.allowedExchangesJson = allowedExchangesJson;
    }

    public Boolean getRequireAccountBinding() {
        return requireAccountBinding;
    }

    public void setRequireAccountBinding(Boolean requireAccountBinding) {
        this.requireAccountBinding = requireAccountBinding;
    }

    public Boolean getLiveOrderRequiresHealthyAccount() {
        return liveOrderRequiresHealthyAccount;
    }

    public void setLiveOrderRequiresHealthyAccount(Boolean liveOrderRequiresHealthyAccount) {
        this.liveOrderRequiresHealthyAccount = liveOrderRequiresHealthyAccount;
    }

    public String getRuntimeFlagsJson() {
        return runtimeFlagsJson;
    }

    public void setRuntimeFlagsJson(String runtimeFlagsJson) {
        this.runtimeFlagsJson = runtimeFlagsJson;
    }

    public String getNotifyDefaultsJson() {
        return notifyDefaultsJson;
    }

    public void setNotifyDefaultsJson(String notifyDefaultsJson) {
        this.notifyDefaultsJson = notifyDefaultsJson;
    }

    public Integer getEventRetentionDays() {
        return eventRetentionDays;
    }

    public void setEventRetentionDays(Integer eventRetentionDays) {
        this.eventRetentionDays = eventRetentionDays;
    }

    public Integer getReplayRetentionDays() {
        return replayRetentionDays;
    }

    public void setReplayRetentionDays(Integer replayRetentionDays) {
        this.replayRetentionDays = replayRetentionDays;
    }

    public Boolean getDeliberationEnabled() {
        return deliberationEnabled;
    }

    public void setDeliberationEnabled(Boolean deliberationEnabled) {
        this.deliberationEnabled = deliberationEnabled;
    }

    public Integer getDeliberationMaxRounds() {
        return deliberationMaxRounds;
    }

    public void setDeliberationMaxRounds(Integer deliberationMaxRounds) {
        this.deliberationMaxRounds = deliberationMaxRounds;
    }

    public Boolean getDeliberationFailOpen() {
        return deliberationFailOpen;
    }

    public void setDeliberationFailOpen(Boolean deliberationFailOpen) {
        this.deliberationFailOpen = deliberationFailOpen;
    }

    public Integer getRouteMaxConcurrency() {
        return routeMaxConcurrency;
    }

    public void setRouteMaxConcurrency(Integer routeMaxConcurrency) {
        this.routeMaxConcurrency = routeMaxConcurrency;
    }

    public String getRouteSchedulerMode() {
        return routeSchedulerMode;
    }

    public void setRouteSchedulerMode(String routeSchedulerMode) {
        this.routeSchedulerMode = routeSchedulerMode;
    }

    public String getTriggerMode() {
        Object value = runtimeFlagsValue("triggerMode");
        return value == null ? null : String.valueOf(value);
    }

    public Map<String, Object> getMarketTrigger() {
        return runtimeFlagsMap("marketTrigger");
    }

    public Map<String, Object> getNewsTrigger() {
        return runtimeFlagsMap("newsTrigger");
    }

    public Map<String, Object> getOnchainTrigger() {
        return runtimeFlagsMap("onchainTrigger");
    }

    public Map<String, Object> getSocialTrigger() {
        return runtimeFlagsMap("socialTrigger");
    }

    public Map<String, Object> getSignalMemoryPolicy() {
        return runtimeFlagsMap("signalMemoryPolicy");
    }

    public List<Object> getTriggerMatrix() {
        Object value = runtimeFlagsValue("triggerMatrix");
        if (value instanceof List<?> listValue) {
            return List.copyOf(listValue);
        }
        return List.of();
    }

    public Map<String, Object> getCooldownPolicy() {
        return runtimeFlagsMap("cooldownPolicy");
    }

    public Map<String, Object> getLlmBudgetPolicy() {
        return runtimeFlagsMap("llmBudgetPolicy");
    }

    public Map<String, Object> getDedupePolicy() {
        return runtimeFlagsMap("dedupePolicy");
    }

    private Object runtimeFlagsValue(String key) {
        return parseRuntimeFlags().get(key);
    }

    private Map<String, Object> runtimeFlagsMap(String key) {
        Object value = runtimeFlagsValue(key);
        if (!(value instanceof Map<?, ?> rawMap)) {
            return new LinkedHashMap<>();
        }
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
            if (entry.getKey() == null) {
                continue;
            }
            normalized.put(String.valueOf(entry.getKey()), entry.getValue());
        }
        return normalized;
    }

    private Map<String, Object> parseRuntimeFlags() {
        if (runtimeFlagsJson == null || runtimeFlagsJson.isBlank()) {
            return new LinkedHashMap<>();
        }
        try {
            Map<String, Object> parsed = OBJECT_MAPPER.readValue(runtimeFlagsJson, new TypeReference<Map<String, Object>>() {});
            return parsed == null ? new LinkedHashMap<>() : new LinkedHashMap<>(parsed);
        } catch (Exception ignored) {
            return new LinkedHashMap<>();
        }
    }
}
