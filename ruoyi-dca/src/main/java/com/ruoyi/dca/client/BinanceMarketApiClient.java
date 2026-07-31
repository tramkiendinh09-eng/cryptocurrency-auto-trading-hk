package com.ruoyi.dca.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

/**
 * Binance交易所市场数据API客户端
 *
 * @author ruoyi
 * @date 2026-04-05
 */
@Component
public class BinanceMarketApiClient {

    private static final Logger log = LoggerFactory.getLogger(BinanceMarketApiClient.class);

    private static final String BASE_URL = "https://api.binance.com";

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public BinanceMarketApiClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.objectMapper = new ObjectMapper();
    }

    /**
     * 获取24小时ticker数据
     *
     * @param symbol 交易对（如BTCUSDT）
     * @return ticker数据
     */
    public Map<String, Object> getTicker(String symbol) {
        try {
            String url = BASE_URL + "/api/v3/ticker/24hr?symbol=" + symbol;
            String response = restTemplate.getForObject(url, String.class);

            JsonNode root = objectMapper.readTree(response);

            Map<String, Object> result = new HashMap<>();
            result.put("symbol", symbol);
            result.put("price", new BigDecimal(root.path("lastPrice").asText()));
            result.put("volume_24h", new BigDecimal(root.path("quoteVolume").asText()));
            result.put("volume_24h_base", new BigDecimal(root.path("volume").asText()));
            result.put("high_24h", new BigDecimal(root.path("highPrice").asText()));
            result.put("low_24h", new BigDecimal(root.path("lowPrice").asText()));
            result.put("price_change_24h", new BigDecimal(root.path("priceChange").asText()));
            result.put("price_change_percent_24h", new BigDecimal(root.path("priceChangePercent").asText()));
            result.put("timestamp", root.path("closeTime").asLong());
            result.put("source", "binance");

            log.info("Binance ticker获取成功: {} = {}", symbol, result.get("price"));
            return result;

        } catch (Exception e) {
            log.error("Binance ticker获取失败: {}", symbol, e);
            return null;
        }
    }

    /**
     * 获取K线数据
     *
     * @param symbol 交易对
     * @param interval 周期（1h, 4h, 1d等）
     * @param limit 数量限制
     * @return K线数据列表
     */
    public JsonNode getKlines(String symbol, String interval, int limit) {
        try {
            String url = BASE_URL + "/api/v3/klines?symbol=" + symbol + "&interval=" + interval + "&limit=" + limit;
            String response = restTemplate.getForObject(url, String.class);

            return objectMapper.readTree(response);

        } catch (Exception e) {
            log.error("Binance K线获取失败: {} - {}", symbol, interval, e);
            return null;
        }
    }

    /**
     * 获取最新K线数据（单条）
     *
     * @param symbol 交易对
     * @param interval 周期
     * @return K线数据Map
     */
    public Map<String, Object> getLatestKline(String symbol, String interval) {
        JsonNode klines = getKlines(symbol, interval, 1);
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
                result.put("source", "binance");
                return result;
            } catch (Exception e) {
                log.error("解析Binance K线数据失败", e);
                return null;
            }
        }
        return null;
    }
}
