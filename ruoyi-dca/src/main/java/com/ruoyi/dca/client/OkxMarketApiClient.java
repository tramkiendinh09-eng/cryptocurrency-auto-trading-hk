package com.ruoyi.dca.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.HashMap;
import java.util.Map;

/**
 * OKX???? API ???
 */
@Component
public class OkxMarketApiClient {

    private static final Logger log = LoggerFactory.getLogger(OkxMarketApiClient.class);
    private static final String BASE_URL = "https://www.okx.com";

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public OkxMarketApiClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.objectMapper = new ObjectMapper();
    }

    public Map<String, Object> getTicker(String instId) {
        try {
            String url = BASE_URL + "/api/v5/market/ticker?instId=" + instId;
            String response = restTemplate.getForObject(url, String.class);

            JsonNode root = objectMapper.readTree(response);
            if (!"0".equals(root.path("code").asText()) || !root.path("data").isArray() || root.path("data").isEmpty()) {
                log.warn("OKX API returned error: {}", root.path("msg").asText());
                return null;
            }

            JsonNode data = root.path("data").get(0);
            BigDecimal last = toBigDecimal(data, "last");
            BigDecimal open24h = toBigDecimal(data, "open24h");
            BigDecimal volumeQuote = firstBigDecimal(data, "volCcy24h", "volCcy");
            BigDecimal volumeBase = firstBigDecimal(data, "vol24h", "vol");

            Map<String, Object> result = new HashMap<>();
            result.put("symbol", instId.replace("-", ""));
            result.put("price", last);
            result.put("volume_24h", volumeQuote);
            result.put("volume_24h_base", volumeBase);
            result.put("high_24h", toBigDecimal(data, "high24h"));
            result.put("low_24h", toBigDecimal(data, "low24h"));
            result.put("timestamp", data.path("ts").asLong());
            result.put("source", "okx");

            if (last != null && open24h != null && open24h.compareTo(BigDecimal.ZERO) > 0) {
                BigDecimal priceChange = last.subtract(open24h);
                result.put("price_change_24h", priceChange);
                result.put("price_change_percent_24h",
                        priceChange.divide(open24h, 8, RoundingMode.HALF_UP).multiply(new BigDecimal("100")));
            }

            log.info("OKX ticker fetched successfully: {} = {}", instId, result.get("price"));
            return result;
        } catch (Exception e) {
            log.error("OKX ticker fetch failed: {}", instId, e);
            return null;
        }
    }

    public JsonNode getKlines(String instId, String bar, int limit) {
        try {
            String url = BASE_URL + "/api/v5/market/candles?instId=" + instId + "&bar=" + bar + "&limit=" + limit;
            String response = restTemplate.getForObject(url, String.class);

            JsonNode root = objectMapper.readTree(response);
            if ("0".equals(root.path("code").asText())) {
                return root.path("data");
            }

            log.warn("OKX Kline API returned error: {}", root.path("msg").asText());
            return null;
        } catch (Exception e) {
            log.error("OKX Kline fetch failed: {} - {}", instId, bar, e);
            return null;
        }
    }

    public Map<String, Object> getLatestKline(String instId, String bar) {
        JsonNode klines = getKlines(instId, bar, 1);
        if (klines != null && klines.size() > 0) {
            try {
                JsonNode kline = klines.get(0);
                Map<String, Object> result = new HashMap<>();
                result.put("timestamp", kline.get(0).asLong());
                result.put("open", new BigDecimal(kline.get(1).asText()));
                result.put("high", new BigDecimal(kline.get(2).asText()));
                result.put("low", new BigDecimal(kline.get(3).asText()));
                result.put("close", new BigDecimal(kline.get(4).asText()));
                result.put("volume", new BigDecimal(kline.get(5).asText()));
                result.put("volume_ccy", new BigDecimal(kline.get(6).asText()));
                result.put("source", "okx");
                return result;
            } catch (Exception e) {
                log.error("Failed to parse OKX Kline data", e);
                return null;
            }
        }
        return null;
    }

    private BigDecimal toBigDecimal(JsonNode node, String field) {
        JsonNode valueNode = node.path(field);
        if (valueNode.isMissingNode() || valueNode.isNull()) {
            return null;
        }
        String text = valueNode.asText();
        if (text == null || text.isBlank()) {
            return null;
        }
        return new BigDecimal(text);
    }

    private BigDecimal firstBigDecimal(JsonNode node, String... fields) {
        for (String field : fields) {
            BigDecimal value = toBigDecimal(node, field);
            if (value != null) {
                return value;
            }
        }
        return null;
    }
}
