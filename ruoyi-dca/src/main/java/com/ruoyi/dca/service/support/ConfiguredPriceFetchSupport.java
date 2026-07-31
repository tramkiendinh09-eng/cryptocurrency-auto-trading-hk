package com.ruoyi.dca.service.support;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.service.IMarketApiConfigService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class ConfiguredPriceFetchSupport {

    private static final Logger log = LoggerFactory.getLogger(ConfiguredPriceFetchSupport.class);

    private final IMarketApiConfigService marketApiConfigService;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ConfiguredPriceFetchSupport(IMarketApiConfigService marketApiConfigService, RestTemplate restTemplate) {
        this.marketApiConfigService = marketApiConfigService;
        this.restTemplate = restTemplate;
    }

    public PriceQuote fetchPrice(String symbol) {
        List<MarketApiConfig> apiConfigs = marketApiConfigService.selectEnabledApis("PRICE");
        if (apiConfigs == null || apiConfigs.isEmpty()) {
            log.warn("No enabled PRICE API configs found for symbol={}", symbol);
            return null;
        }

        apiConfigs = new ArrayList<>(apiConfigs);
        apiConfigs.sort(Comparator.comparing(config -> config.getPriority() == null ? Integer.MAX_VALUE : config.getPriority()));

        for (MarketApiConfig apiConfig : apiConfigs) {
            if (!isApiApplicable(apiConfig, symbol)) {
                continue;
            }

            try {
                Map<String, Object> data = callApi(apiConfig, symbol);
                BigDecimal price = resolvePrice(data, apiConfig);
                if (price != null && price.compareTo(BigDecimal.ZERO) > 0) {
                    return new PriceQuote(price, apiConfig.getApiName());
                }
            } catch (Exception e) {
                log.warn("Configured PRICE API {} failed for {}", apiConfig.getApiName(), symbol, e);
            }
        }

        return null;
    }

    private boolean isApiApplicable(MarketApiConfig apiConfig, String symbol) {
        if (apiConfig.getApplySymbols() == null || apiConfig.getApplySymbols().isBlank()) {
            return true;
        }
        try {
            List<String> applicableSymbols = objectMapper.readValue(
                    apiConfig.getApplySymbols(), new TypeReference<List<String>>() {});
            return applicableSymbols.contains(symbol);
        } catch (Exception e) {
            log.warn("Failed to parse applySymbols for api={}", apiConfig.getApiName(), e);
            return true;
        }
    }

    private Map<String, Object> callApi(MarketApiConfig apiConfig, String symbol) throws Exception {
        String url = buildApiUrl(apiConfig.getApiUrl(), symbol);
        Object responseBody;
        if ("POST".equalsIgnoreCase(apiConfig.getHttpMethod())) {
            responseBody = sendPostRequest(url, apiConfig.getRequestHeaders(), apiConfig.getRequestBody());
        } else {
            responseBody = sendGetRequest(url, apiConfig.getRequestHeaders());
        }

        if (responseBody == null) {
            return null;
        }

        if (apiConfig.getResponsePath() != null && !apiConfig.getResponsePath().isBlank()) {
            return extractDataByPath(responseBody, apiConfig.getResponsePath());
        }
        return toMapObject(responseBody);
    }

    private Object sendGetRequest(String url, String headersJson) throws Exception {
        HttpHeaders headers = buildHeaders(headersJson);
        HttpEntity<Void> entity = new HttpEntity<>(headers);
        ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, entity, String.class);
        return objectMapper.readValue(response.getBody(), Object.class);
    }

    private Object sendPostRequest(String url, String headersJson, String bodyJson) throws Exception {
        HttpHeaders headers = buildHeaders(headersJson);
        Object requestBody = parseJsonValue(bodyJson);
        HttpEntity<?> entity = new HttpEntity<>(requestBody == null ? bodyJson : requestBody, headers);
        ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, entity, String.class);
        return objectMapper.readValue(response.getBody(), Object.class);
    }

    private HttpHeaders buildHeaders(String headersJson) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        Object parsedHeaders = parseJsonValue(headersJson);
        if (parsedHeaders instanceof Map<?, ?> headerMap) {
            for (Map.Entry<?, ?> entry : headerMap.entrySet()) {
                if (entry.getKey() != null && entry.getValue() != null) {
                    headers.set(entry.getKey().toString(), entry.getValue().toString());
                }
            }
        }
        return headers;
    }

    private Object parseJsonValue(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(rawValue, Object.class);
        } catch (Exception e) {
            return rawValue;
        }
    }

    private BigDecimal resolvePrice(Map<String, Object> data, MarketApiConfig apiConfig) {
        if (data == null) {
            return null;
        }

        try {
            if (apiConfig.getFieldMapping() != null && !apiConfig.getFieldMapping().isBlank()) {
                Map<String, String> fieldMapping = objectMapper.readValue(
                        apiConfig.getFieldMapping(), new TypeReference<Map<String, String>>() {});
                if (fieldMapping.containsKey("price")) {
                    BigDecimal mappedPrice = toBigDecimal(getNestedValue(data, fieldMapping.get("price")));
                    if (mappedPrice != null) {
                        return mappedPrice;
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Failed to parse field mapping for api={}", apiConfig.getApiName(), e);
        }

        return firstBigDecimal(data, "price", "last", "lastPrice", "close");
    }

    private String buildApiUrl(String templateUrl, String symbol) {
        return templateUrl
                .replace("{symbol}", symbol)
                .replace("{symbol_okx}", symbol.replace("USDT", "-USDT"))
                .replace("{symbol_binance}", symbol)
                .replace("{symbol_gate}", symbol.replace("USDT", "_USDT"))
                .replace("{symbol_lower}", symbol.toLowerCase());
    }

    private Map<String, Object> extractDataByPath(Object data, String path) {
        try {
            if (data == null) {
                return null;
            }
            if (path == null || path.isBlank() || "$".equals(path.trim())) {
                return toMapObject(data);
            }

            String cleanPath = path.trim();
            if (cleanPath.startsWith("$")) {
                cleanPath = cleanPath.substring(1);
            }
            if (cleanPath.startsWith(".")) {
                cleanPath = cleanPath.substring(1);
            }

            Object extracted = data;
            if (!cleanPath.isEmpty()) {
                for (String segment : cleanPath.split("\\.")) {
                    if (segment == null || segment.isEmpty()) {
                        continue;
                    }
                    extracted = navigatePathSegment(extracted, segment);
                    if (extracted == null) {
                        return toMapObject(data);
                    }
                }
            }

            return mergeRootFields(data, extracted);
        } catch (Exception e) {
            log.warn("Failed to extract data by path={}", path, e);
            return toMapObject(data);
        }
    }

    private Object navigatePathSegment(Object current, String segment) {
        String remaining = segment;

        if (!remaining.startsWith("[")) {
            int bracketIndex = remaining.indexOf('[');
            String property = bracketIndex >= 0 ? remaining.substring(0, bracketIndex) : remaining;
            if (!(current instanceof Map)) {
                return null;
            }
            current = ((Map<?, ?>) current).get(property);
            remaining = bracketIndex >= 0 ? remaining.substring(bracketIndex) : "";
        }

        while (remaining.startsWith("[")) {
            int endIndex = remaining.indexOf(']');
            if (endIndex <= 1 || !(current instanceof List)) {
                return null;
            }
            int index = Integer.parseInt(remaining.substring(1, endIndex));
            List<?> list = (List<?>) current;
            if (index < 0 || index >= list.size()) {
                return null;
            }
            current = list.get(index);
            remaining = remaining.substring(endIndex + 1);
        }

        return current;
    }

    private Map<String, Object> mergeRootFields(Object root, Object extracted) {
        Map<String, Object> extractedMap = toMapObject(extracted);
        if (!(root instanceof Map)) {
            return extractedMap;
        }
        Map<String, Object> merged = toMapObject(root);
        if (extractedMap != null) {
            merged.putAll(extractedMap);
        }
        return merged;
    }

    private Map<String, Object> toMapObject(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Map) {
            return objectMapper.convertValue(value, new TypeReference<Map<String, Object>>() {});
        }
        if (value instanceof List<?> list) {
            Map<String, Object> indexed = new HashMap<>();
            for (int i = 0; i < list.size(); i++) {
                indexed.put(String.valueOf(i), list.get(i));
            }
            return indexed;
        }
        return objectMapper.convertValue(value, new TypeReference<Map<String, Object>>() {});
    }

    private BigDecimal firstBigDecimal(Map<String, Object> data, String... fieldNames) {
        for (String fieldName : fieldNames) {
            BigDecimal value = toBigDecimal(getNestedValue(data, fieldName));
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    private BigDecimal toBigDecimal(Object value) {
        if (value == null) {
            return null;
        }
        try {
            String text = value.toString();
            if (text.isBlank()) {
                return null;
            }
            return new BigDecimal(text);
        } catch (Exception e) {
            return null;
        }
    }

    private Object getNestedValue(Map<String, Object> data, String fieldPath) {
        if (fieldPath == null || fieldPath.isEmpty()) {
            return null;
        }

        try {
            String[] parts = fieldPath.split("\\|");
            Object value = resolveFieldExpression(data, parts[0].trim());
            for (int i = 1; i < parts.length; i++) {
                value = applyTransform(data, value, parts[i].trim());
            }
            return value;
        } catch (Exception e) {
            log.warn("Failed to resolve field={}", fieldPath, e);
            return null;
        }
    }

    private Object resolveFieldExpression(Map<String, Object> data, String expression) {
        if (expression.contains("-") && !expression.startsWith("-")) {
            String[] tokens = expression.split("-", 2);
            BigDecimal left = toBigDecimal(resolveSimpleFieldValue(data, tokens[0].trim()));
            BigDecimal right = toBigDecimal(resolveSimpleFieldValue(data, tokens[1].trim()));
            if (left != null && right != null) {
                return left.subtract(right);
            }
            return null;
        }

        if (expression.contains("+") && !expression.startsWith("+")) {
            String[] tokens = expression.split("\\+", 2);
            BigDecimal left = toBigDecimal(resolveSimpleFieldValue(data, tokens[0].trim()));
            BigDecimal right = toBigDecimal(resolveSimpleFieldValue(data, tokens[1].trim()));
            if (left != null && right != null) {
                return left.add(right);
            }
            return null;
        }

        return resolveSimpleFieldValue(data, expression);
    }

    private Object resolveSimpleFieldValue(Map<String, Object> data, String fieldPath) {
        Object current = data;
        for (String part : fieldPath.split("\\.")) {
            if (!(current instanceof Map<?, ?> map)) {
                return null;
            }
            current = map.get(part);
            if (current == null) {
                return null;
            }
        }
        return current;
    }

    private Object applyTransform(Map<String, Object> data, Object value, String transform) {
        if (!"calc:percent".equalsIgnoreCase(transform)) {
            return value;
        }

        BigDecimal currentValue = toBigDecimal(value);
        BigDecimal baseValue = firstBigDecimal(data, "open24h", "open");
        if (currentValue == null || baseValue == null || baseValue.compareTo(BigDecimal.ZERO) == 0) {
            return null;
        }

        return currentValue.subtract(baseValue)
                .divide(baseValue, 4, RoundingMode.HALF_UP)
                .multiply(new BigDecimal("100"));
    }

    public record PriceQuote(BigDecimal price, String source) {
    }
}