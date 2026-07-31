package com.ruoyi.dca.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * Fear & Greed Index API客户端
 * 数据源: alternative.me
 *
 * @author ruoyi
 * @date 2026-04-05
 */
@Component
public class FearGreedIndexClient {

    private static final Logger log = LoggerFactory.getLogger(FearGreedIndexClient.class);

    private static final String API_URL = "https://api.alternative.me/fng/";

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public FearGreedIndexClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.objectMapper = new ObjectMapper();
    }

    /**
     * 获取最新的恐慌贪婪指数
     *
     * @return 恐慌贪婪指数数据
     */
    public Map<String, Object> getLatestFearGreedIndex() {
        try {
            String response = restTemplate.getForObject(API_URL, String.class);

            JsonNode root = objectMapper.readTree(response);
            JsonNode data = root.path("data");

            if (data.size() > 0) {
                JsonNode latest = data.get(0);

                Map<String, Object> result = new HashMap<>();
                result.put("value", latest.path("value").asInt());
                result.put("classification", latest.path("value_classification").asText());
                result.put("timestamp", latest.path("timestamp").asLong());
                result.put("source", "alternative.me");

                log.info("Fear & Greed Index获取成功: {} ({})",
                    result.get("value"), result.get("classification"));

                return result;
            }

            return null;

        } catch (Exception e) {
            log.error("Fear & Greed Index获取失败", e);
            return null;
        }
    }
}
