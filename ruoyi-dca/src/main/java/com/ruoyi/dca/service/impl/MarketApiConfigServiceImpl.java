package com.ruoyi.dca.service.impl;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.domain.trade.TradeDataSourceHealthLog;
import com.ruoyi.dca.mapper.MarketApiConfigMapper;
import com.ruoyi.dca.mapper.trade.TradeDataSourceHealthLogMapper;
import com.ruoyi.dca.service.IMarketApiConfigService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Market API config service implementation.
 */
@Service
public class MarketApiConfigServiceImpl implements IMarketApiConfigService {

    private static final Logger log = LoggerFactory.getLogger(MarketApiConfigServiceImpl.class);

    private static final String TRANSPORT_REST = "REST";
    private static final String TRANSPORT_WEBSOCKET = "WEBSOCKET";
    private static final String VENDOR_BINANCE = "BINANCE";
    private static final String MARKET_SCOPE_SPOT = "SPOT";
    private static final int BINANCE_WS_DEFAULT_PING_SECONDS = 20;
    private static final int BINANCE_WS_DEFAULT_PONG_TIMEOUT_SECONDS = 60;
    private static final int BINANCE_WS_DEFAULT_CONNECTION_TTL_HOURS = 24;
    private static final int BINANCE_WS_MAX_STREAMS_PER_CONNECTION = 1024;
    private static final int BINANCE_WS_MAX_CONTROL_MESSAGES_PER_SECOND = 5;

    @Autowired
    private MarketApiConfigMapper apiConfigMapper;

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private TradeDataSourceHealthLogMapper tradeDataSourceHealthLogMapper;

    @Override
    public MarketApiConfig selectApiConfigById(Long id) {
        return apiConfigMapper.selectMarketApiConfigById(id);
    }

    @Override
    public List<MarketApiConfig> selectApiConfigList(MarketApiConfig marketApiConfig) {
        return apiConfigMapper.selectMarketApiConfigList(marketApiConfig);
    }

    @Override
    public List<MarketApiConfig> selectEnabledApis(String dataCategory) {
        return apiConfigMapper.selectEnabledApis(dataCategory);
    }

    @Override
    public MarketApiConfig selectApiByName(String apiName) {
        return apiConfigMapper.selectApiByName(apiName);
    }

    @Override
    public int insertApiConfig(MarketApiConfig marketApiConfig) {
        normalizeAndValidate(marketApiConfig);
        applyInsertVersion(marketApiConfig);
        return apiConfigMapper.insertMarketApiConfig(marketApiConfig);
    }

    @Override
    public int updateApiConfig(MarketApiConfig marketApiConfig) {
        normalizeAndValidate(marketApiConfig);
        applyUpdateVersion(marketApiConfig);
        return apiConfigMapper.updateMarketApiConfig(marketApiConfig);
    }

    @Override
    public int deleteApiConfigByIds(Long[] ids) {
        return apiConfigMapper.deleteMarketApiConfigByIds(ids);
    }

    @Override
    public Map<String, Object> testApiConnection(Long id) {
        Map<String, Object> result = new HashMap<>();
        Long startTime = System.currentTimeMillis();
        Long sourceId = id;
        try {
            MarketApiConfig config = selectApiConfigById(id);
            if (config == null) {
                result.put("success", false);
                result.put("message", "API config does not exist");
                persistHealthLog(sourceId, "failed", null, null, String.valueOf(result.get("message")));
                return result;
            }
            sourceId = config.getId();

            normalizeAndValidate(config);
            if (isWebsocketConfig(config)) {
                result.put("success", true);
                result.put("transportType", config.getTransportType());
                result.put("vendorCode", config.getVendorCode());
                result.put("wsBaseUrl", config.getWsBaseUrl());
                result.put("wsPath", config.getWsPath());
                result.put("wsCombinedEnabled", config.getWsCombinedEnabled());
                result.put("message", "WebSocket config validation passed");
                persistHealthLog(
                    sourceId,
                    "healthy",
                    System.currentTimeMillis() - startTime,
                    String.valueOf(result.get("message")),
                    null
                );
                return result;
            }

            String url = config.getApiUrl();
            HttpMethod method = HttpMethod.valueOf(config.getHttpMethod());

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<String> entity = new HttpEntity<>(headers);

            ResponseEntity<String> response = restTemplate.exchange(url, method, entity, String.class);
            long duration = System.currentTimeMillis() - startTime;

            result.put("success", response.getStatusCode().is2xxSuccessful());
            result.put("statusCode", response.getStatusCode().value());
            result.put("duration", duration + "ms");
            result.put("response", response.getBody());
            result.put("message", response.getStatusCode().is2xxSuccessful()
                ? "API test succeeded"
                : "API returned non-success status: " + response.getStatusCode());
            persistHealthLog(
                sourceId,
                response.getStatusCode().is2xxSuccessful() ? "healthy" : "failed",
                duration,
                response.getBody(),
                response.getStatusCode().is2xxSuccessful() ? null : String.valueOf(result.get("message"))
            );
        } catch (Exception e) {
            log.error("API test failed", e);
            result.put("success", false);
            result.put("message", "API test failed: " + e.getMessage());
            persistHealthLog(sourceId, "failed", System.currentTimeMillis() - startTime, null, String.valueOf(result.get("message")));
        }
        return result;
    }

    private void persistHealthLog(Long sourceId, String status, Long latencyMs, String responseExcerpt, String errorMessage) {
        if (sourceId == null) {
            return;
        }
        TradeDataSourceHealthLog healthLog = new TradeDataSourceHealthLog();
        healthLog.setSourceId(sourceId);
        healthLog.setCheckType("manual_test");
        healthLog.setStatus(status);
        healthLog.setLatencyMs(latencyMs);
        healthLog.setResponseExcerpt(truncate(responseExcerpt, 1000));
        healthLog.setErrorMessage(truncate(errorMessage, 1000));
        tradeDataSourceHealthLogMapper.insertTradeDataSourceHealthLog(healthLog);
    }

    private void normalizeAndValidate(MarketApiConfig marketApiConfig) {
        if (marketApiConfig == null) {
            throw new ServiceException("Market API config payload is required");
        }

        marketApiConfig.setConfigName(trimToNull(marketApiConfig.getConfigName()));
        marketApiConfig.setDataCategory(normalizeUpper(marketApiConfig.getDataCategory()));
        marketApiConfig.setDataSubType(normalizeUpper(marketApiConfig.getDataSubType()));
        marketApiConfig.setTransportType(defaultIfBlank(normalizeUpper(marketApiConfig.getTransportType()), TRANSPORT_REST));
        marketApiConfig.setVendorCode(normalizeUpper(marketApiConfig.getVendorCode()));
        marketApiConfig.setMarketScope(defaultIfBlank(normalizeUpper(marketApiConfig.getMarketScope()), MARKET_SCOPE_SPOT));
        marketApiConfig.setApiName(trimToNull(marketApiConfig.getApiName()));
        marketApiConfig.setApiUrl(trimToNull(marketApiConfig.getApiUrl()));
        marketApiConfig.setWsBaseUrl(trimToNull(marketApiConfig.getWsBaseUrl()));
        marketApiConfig.setWsPath(trimToNull(marketApiConfig.getWsPath()));
        marketApiConfig.setWsStreamNameTemplate(trimToNull(marketApiConfig.getWsStreamNameTemplate()));
        marketApiConfig.setDocReferenceUrl(trimToNull(marketApiConfig.getDocReferenceUrl()));
        marketApiConfig.setHttpMethod(defaultIfBlank(normalizeUpper(marketApiConfig.getHttpMethod()), HttpMethod.GET.name()));
        marketApiConfig.setRequestHeaders(trimToNull(marketApiConfig.getRequestHeaders()));
        marketApiConfig.setRequestBody(trimToNull(marketApiConfig.getRequestBody()));
        marketApiConfig.setResponsePath(trimToNull(marketApiConfig.getResponsePath()));
        marketApiConfig.setFieldMapping(trimToNull(marketApiConfig.getFieldMapping()));
        marketApiConfig.setEnabled(defaultIfBlank(trimToNull(marketApiConfig.getEnabled()), "0"));
        marketApiConfig.setDataTransform(trimToNull(marketApiConfig.getDataTransform()));
        marketApiConfig.setUseProxy(trimToNull(marketApiConfig.getUseProxy()));
        marketApiConfig.setProxyUrl(trimToNull(marketApiConfig.getProxyUrl()));
        marketApiConfig.setApplySymbols(trimToNull(marketApiConfig.getApplySymbols()));
        marketApiConfig.setRemark(trimToNull(marketApiConfig.getRemark()));

        if (marketApiConfig.getConfigName() == null) {
            throw new ServiceException("Config name is required");
        }
        if (marketApiConfig.getDataCategory() == null) {
            throw new ServiceException("Data category is required");
        }
        if (marketApiConfig.getApiName() == null) {
            throw new ServiceException("API name is required");
        }

        if (isWebsocketConfig(marketApiConfig)) {
            validateWebsocketConfig(marketApiConfig);
            return;
        }

        if (marketApiConfig.getApiUrl() == null) {
            throw new ServiceException("API URL is required for REST configs");
        }
    }

    private void applyInsertVersion(MarketApiConfig marketApiConfig) {
        if (marketApiConfig.getVersionNo() == null || marketApiConfig.getVersionNo() < 1) {
            marketApiConfig.setVersionNo(1);
        }
    }

    private void applyUpdateVersion(MarketApiConfig marketApiConfig) {
        MarketApiConfig existing = marketApiConfig.getId() == null ? null : apiConfigMapper.selectMarketApiConfigById(marketApiConfig.getId());
        int currentVersion = existing == null || existing.getVersionNo() == null || existing.getVersionNo() < 1
            ? 0
            : existing.getVersionNo();
        marketApiConfig.setVersionNo(currentVersion + 1);
    }

    private void validateWebsocketConfig(MarketApiConfig marketApiConfig) {
        if (marketApiConfig.getWsBaseUrl() == null) {
            throw new ServiceException("WebSocket base URL is required");
        }
        if (marketApiConfig.getWsPath() == null) {
            throw new ServiceException("WebSocket path is required");
        }
        if (marketApiConfig.getWsStreamNameTemplate() == null) {
            throw new ServiceException("WebSocket stream name template is required");
        }
        if (marketApiConfig.getWsCombinedEnabled() == null) {
            marketApiConfig.setWsCombinedEnabled(Boolean.FALSE);
        }

        if (isBinanceWebsocketConfig(marketApiConfig)) {
            applyBinanceDefaults(marketApiConfig);
            validateBinanceWebsocketConfig(marketApiConfig);
        }
    }

    private void applyBinanceDefaults(MarketApiConfig marketApiConfig) {
        if (marketApiConfig.getWsPingIntervalSeconds() == null) {
            marketApiConfig.setWsPingIntervalSeconds(BINANCE_WS_DEFAULT_PING_SECONDS);
        }
        if (marketApiConfig.getWsPongTimeoutSeconds() == null) {
            marketApiConfig.setWsPongTimeoutSeconds(BINANCE_WS_DEFAULT_PONG_TIMEOUT_SECONDS);
        }
        if (marketApiConfig.getWsConnectionTtlHours() == null) {
            marketApiConfig.setWsConnectionTtlHours(BINANCE_WS_DEFAULT_CONNECTION_TTL_HOURS);
        }
        if (marketApiConfig.getWsMaxStreamsPerConnection() == null) {
            marketApiConfig.setWsMaxStreamsPerConnection(BINANCE_WS_MAX_STREAMS_PER_CONNECTION);
        }
        if (marketApiConfig.getWsControlMessagesPerSecond() == null) {
            marketApiConfig.setWsControlMessagesPerSecond(BINANCE_WS_MAX_CONTROL_MESSAGES_PER_SECOND);
        }
    }

    private void validateBinanceWebsocketConfig(MarketApiConfig marketApiConfig) {
        String wsPath = marketApiConfig.getWsPath();
        if (!"/ws".equals(wsPath) && !"/stream".equals(wsPath)) {
            throw new ServiceException("Binance WebSocket path must be /ws or /stream");
        }
        if (Boolean.TRUE.equals(marketApiConfig.getWsCombinedEnabled()) && !"/stream".equals(wsPath)) {
            throw new ServiceException("Binance combined streams must use /stream");
        }
        if (!Boolean.TRUE.equals(marketApiConfig.getWsSymbolLowercase())) {
            throw new ServiceException("Binance stream names require lowercase symbols");
        }

        validatePositive(marketApiConfig.getWsPingIntervalSeconds(), "Binance WebSocket ping interval");
        validatePositive(marketApiConfig.getWsPongTimeoutSeconds(), "Binance WebSocket pong timeout");
        validatePositive(marketApiConfig.getWsConnectionTtlHours(), "Binance WebSocket connection TTL");
        validatePositive(marketApiConfig.getWsMaxStreamsPerConnection(), "Binance max streams per connection");
        validatePositive(marketApiConfig.getWsControlMessagesPerSecond(), "Binance control messages per second");

        if (marketApiConfig.getWsMaxStreamsPerConnection() > BINANCE_WS_MAX_STREAMS_PER_CONNECTION) {
            throw new ServiceException("Binance max streams per connection cannot exceed 1024");
        }
        if (marketApiConfig.getWsControlMessagesPerSecond() > BINANCE_WS_MAX_CONTROL_MESSAGES_PER_SECOND) {
            throw new ServiceException("Binance control messages per second cannot exceed 5");
        }
    }

    private void validatePositive(Integer value, String fieldName) {
        if (value == null || value <= 0) {
            throw new ServiceException(fieldName + " must be greater than 0");
        }
    }

    private boolean isWebsocketConfig(MarketApiConfig marketApiConfig) {
        return TRANSPORT_WEBSOCKET.equals(marketApiConfig.getTransportType());
    }

    private boolean isBinanceWebsocketConfig(MarketApiConfig marketApiConfig) {
        return isWebsocketConfig(marketApiConfig) && VENDOR_BINANCE.equals(marketApiConfig.getVendorCode());
    }

    private String normalizeUpper(String value) {
        String trimmed = trimToNull(value);
        return trimmed == null ? null : trimmed.toUpperCase(Locale.ROOT);
    }

    private String defaultIfBlank(String value, String defaultValue) {
        return value == null || value.isEmpty() ? defaultValue : value;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private String truncate(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        return value.length() <= maxLength ? value : value.substring(0, maxLength);
    }
}
