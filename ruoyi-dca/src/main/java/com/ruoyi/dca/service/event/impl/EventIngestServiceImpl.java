package com.ruoyi.dca.service.event.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.event.MarketEvent;
import com.ruoyi.dca.domain.event.MarketKlineSnapshot;
import com.ruoyi.dca.domain.event.MarketMetricSnapshot;
import com.ruoyi.dca.domain.event.NewsEvent;
import com.ruoyi.dca.domain.event.OnchainEvent;
import com.ruoyi.dca.domain.event.SocialEvent;
import com.ruoyi.dca.mapper.event.EventIngestMapper;
import com.ruoyi.dca.service.event.IEventIngestService;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Locale;
import java.util.UUID;

@Service
public class EventIngestServiceImpl implements IEventIngestService {

    private static final int DEFAULT_MARKET_HISTORY_MAX_AGE_MINUTES = 300;
    private static final int MAX_MARKET_HISTORY_MAX_AGE_MINUTES = 1440;
    @Autowired
    private EventIngestMapper eventIngestMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public void ingest(EventRaw eventRaw) {
        if (eventRaw.getTraceId() == null || eventRaw.getTraceId().isEmpty()) {
            eventRaw.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        eventRaw.setCreatedAt(normalizeCreatedAt(eventRaw.getCreatedAt()));
        eventIngestMapper.insertEventRaw(eventRaw);
        persistTypedEvent(eventRaw);
    }


    @Override
    public List<Map<String, Object>> listRecentMarketHistory(String symbol, String exchange, Integer limit, Integer maxAgeMinutes) {
        String normalizedSymbol = normalizeUpper(symbol);
        String normalizedExchange = normalizeLower(exchange);
        if (normalizedSymbol.isEmpty() || normalizedExchange.isEmpty()) {
            return Collections.emptyList();
        }
        int safeLimit = Math.max(1, Math.min(limit == null ? 60 : limit, 240));
        int safeMaxAgeMinutes = Math.max(1, Math.min(maxAgeMinutes == null ? DEFAULT_MARKET_HISTORY_MAX_AGE_MINUTES : maxAgeMinutes, MAX_MARKET_HISTORY_MAX_AGE_MINUTES));
        String createdAtMin = TradeRuntimeTimeUtils.formatSqlDateTime(TradeRuntimeTimeUtils.nowDatabaseLocalDateTime().minusMinutes(safeMaxAgeMinutes));
        List<EventRaw> rows = eventIngestMapper.selectRecentRawMarketEvents(normalizedSymbol, normalizedExchange, createdAtMin, safeLimit);
        List<Map<String, Object>> history = new ArrayList<>();
        for (int index = rows.size() - 1; index >= 0; index--) {
            Map<String, Object> item = toMarketHistoryItem(rows.get(index));
            if (!item.isEmpty()) {
                history.add(item);
            }
        }
        return history;
    }

    private String normalizeCreatedAt(String createdAt) {
        String normalized = TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(createdAt);
        if (normalized == null || normalized.isBlank() || normalized.matches("^-?\\d+$")) {
            return TradeRuntimeTimeUtils.nowSqlDateTime();
        }
        return normalized;
    }

    private Map<String, Object> toMarketHistoryItem(EventRaw eventRaw) {
        if (eventRaw == null || eventRaw.getPayloadJson() == null || eventRaw.getPayloadJson().isBlank()) {
            return Collections.emptyMap();
        }
        try {
            JsonNode node = objectMapper.readTree(eventRaw.getPayloadJson());
            Double price = doubleValue(node, "price", "latest_price", "latestPrice", "last_price", "lastPrice", "p", "c", "last");
            if (price == null || price <= 0) {
                return Collections.emptyMap();
            }
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("observed_at", eventRaw.getCreatedAt());
            item.put("symbol", eventRaw.getSymbol());
            item.put("exchange", eventRaw.getExchangeCode());
            item.put("price", price);
            putIfPresent(item, "volume", doubleValue(node, "volume", "volume_24h", "volume24h", "base_volume", "baseVolume", "v", "vol24h"));
            putIfPresent(item, "quote_volume", doubleValue(node, "quote_volume", "quote_volume_24h", "quoteVolume24h", "quoteVolume", "turnover", "q", "volCcy24h"));
            putIfPresent(item, "mark_price", doubleValue(node, "mark_price", "markPrice"));
            putIfPresent(item, "funding_rate", doubleValue(node, "funding_rate", "fundingRate"));
            putIfPresent(item, "open_interest", doubleValue(node, "open_interest", "openInterest", "oi"));
            putIfPresent(item, "liquidation_notional_15m", doubleValue(node, "liquidation_notional_15m", "liquidationNotional15m"));
            putIfPresent(item, "liquidation_notional_60m", doubleValue(node, "liquidation_notional_60m", "liquidationNotional60m"));
            putIfPresent(item, "liquidation_notional_240m", doubleValue(node, "liquidation_notional_240m", "liquidationNotional240m"));
            return item;
        } catch (Exception ignored) {
            return Collections.emptyMap();
        }
    }

    private void putIfPresent(Map<String, Object> item, String key, Double value) {
        if (value != null) {
            item.put(key, value);
        }
    }

    private Double doubleValue(JsonNode node, String... fieldNames) {
        for (String fieldName : fieldNames) {
            if (node.hasNonNull(fieldName)) {
                try {
                    return Double.valueOf(node.get(fieldName).asText());
                } catch (NumberFormatException ignored) {
                    return null;
                }
            }
        }
        return null;
    }

    private String normalizeUpper(String value) {
        return value == null ? "" : value.trim().toUpperCase(Locale.ROOT);
    }

    private String normalizeLower(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private void persistTypedEvent(EventRaw eventRaw) {
        if (eventRaw.getEventType() == null || eventRaw.getEventType().isBlank()) {
            return;
        }
        if (eventRaw.getPayloadJson() == null || eventRaw.getPayloadJson().isBlank()) {
            return;
        }

        try {
            JsonNode node = objectMapper.readTree(eventRaw.getPayloadJson());
            String eventType = eventRaw.getEventType().trim().toLowerCase(Locale.ROOT);
            switch (eventType) {
                case "market_tick":
                    persistMarketEvent(eventRaw, node);
                    break;
                case "market_kline":
                    persistMarketKlineSnapshot(eventRaw, node);
                    break;
                case "market_metric":
                    persistMarketMetricSnapshot(eventRaw, node);
                    break;
                case "news":
                    persistNewsEvent(eventRaw, node);
                    break;
                case "onchain":
                    persistOnchainEvent(eventRaw, node);
                    break;
                case "social":
                    persistSocialEvent(eventRaw, node);
                    break;
                default:
                    break;
            }
        } catch (Exception ignored) {
            // Keep raw-event durability even if typed payload projection fails.
        }
    }

    private void persistMarketEvent(EventRaw eventRaw, JsonNode node) {
        if (!node.hasNonNull("price") || !node.hasNonNull("volume")) {
            return;
        }
        MarketEvent marketEvent = new MarketEvent();
        marketEvent.setTraceId(eventRaw.getTraceId());
        marketEvent.setSymbol(eventRaw.getSymbol());
        marketEvent.setExchangeCode(eventRaw.getExchangeCode());
        marketEvent.setPrice(new BigDecimal(node.get("price").asText()));
        marketEvent.setVolume(new BigDecimal(node.get("volume").asText()));
        eventIngestMapper.insertMarketEvent(marketEvent);
    }

    private void persistMarketKlineSnapshot(EventRaw eventRaw, JsonNode node) {
        BigDecimal closePrice = decimalValue(node, "close", "close_price", "closePrice", "c");
        String intervalCode = textValue(node, "interval", "interval_code", "bar");
        if (closePrice == null || intervalCode == null || intervalCode.isBlank()) {
            return;
        }
        MarketKlineSnapshot snapshot = new MarketKlineSnapshot();
        snapshot.setTraceId(eventRaw.getTraceId());
        snapshot.setSymbol(eventRaw.getSymbol());
        snapshot.setExchangeCode(eventRaw.getExchangeCode());
        snapshot.setIntervalCode(intervalCode);
        snapshot.setOpenTime(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(textValue(node, "open_time", "openTime", "event_time", "eventTime")));
        snapshot.setCloseTime(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(textValue(node, "close_time", "closeTime", "event_time", "eventTime")));
        snapshot.setOpenPrice(decimalValue(node, "open", "open_price", "openPrice", "o"));
        snapshot.setHighPrice(decimalValue(node, "high", "high_price", "highPrice", "h"));
        snapshot.setLowPrice(decimalValue(node, "low", "low_price", "lowPrice", "l"));
        snapshot.setClosePrice(closePrice);
        snapshot.setVolume(decimalValue(node, "volume", "base_volume", "baseVolume", "v"));
        snapshot.setQuoteVolume(decimalValue(node, "quote_volume", "quoteVolume", "turnover", "q"));
        snapshot.setTradeCount(longValue(node, "trade_count", "tradeCount", "count"));
        snapshot.setSource(textValue(node, "source", "data_source"));
        snapshot.setPayloadJson(eventRaw.getPayloadJson());
        eventIngestMapper.insertMarketKlineSnapshot(snapshot);
    }

    private void persistMarketMetricSnapshot(EventRaw eventRaw, JsonNode node) {
        BigDecimal latestPrice = decimalValue(node, "latest_price", "latestPrice", "price");
        BigDecimal markPrice = decimalValue(node, "mark_price", "markPrice");
        BigDecimal fundingRate = decimalValue(node, "funding_rate", "fundingRate");
        BigDecimal openInterest = decimalValue(node, "open_interest", "openInterest", "oi");
        if (latestPrice == null && markPrice == null && fundingRate == null && openInterest == null) {
            return;
        }
        MarketMetricSnapshot snapshot = new MarketMetricSnapshot();
        snapshot.setTraceId(eventRaw.getTraceId());
        snapshot.setSymbol(eventRaw.getSymbol());
        snapshot.setExchangeCode(eventRaw.getExchangeCode());
        snapshot.setObservedAt(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(textValue(node, "observed_at", "observedAt", "event_time", "eventTime")));
        if (snapshot.getObservedAt() == null || snapshot.getObservedAt().isBlank()) {
            snapshot.setObservedAt(TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(eventRaw.getCreatedAt()));
        }
        snapshot.setLatestPrice(latestPrice);
        snapshot.setMarkPrice(markPrice);
        snapshot.setMarkPriceDeviationPct(decimalValue(node, "mark_price_deviation_pct", "markPriceDeviationPct"));
        snapshot.setFundingRate(fundingRate);
        snapshot.setOpenInterest(openInterest);
        snapshot.setVolume24h(decimalValue(node, "volume_24h", "volume24h", "volume"));
        snapshot.setQuoteVolume24h(decimalValue(node, "quote_volume_24h", "quoteVolume24h", "quote_volume", "quoteVolume"));
        snapshot.setLiquidationNotional15m(decimalValue(node, "liquidation_notional_15m", "liquidationNotional15m"));
        snapshot.setLiquidationNotional60m(decimalValue(node, "liquidation_notional_60m", "liquidationNotional60m"));
        snapshot.setLiquidationNotional240m(decimalValue(node, "liquidation_notional_240m", "liquidationNotional240m"));
        snapshot.setLargestLiquidationNotionalUsd(decimalValue(node, "largest_liquidation_notional_usd", "largestLiquidationNotionalUsd"));
        snapshot.setLargestLiquidationSide(textValue(node, "largest_liquidation_side", "largestLiquidationSide"));
        snapshot.setSourceStatus(textValue(node, "source_status", "sourceStatus"));
        snapshot.setPayloadJson(eventRaw.getPayloadJson());
        eventIngestMapper.insertMarketMetricSnapshot(snapshot);
    }

    private BigDecimal decimalValue(JsonNode node, String... fieldNames) {
        for (String fieldName : fieldNames) {
            if (node.hasNonNull(fieldName)) {
                try {
                    return new BigDecimal(node.get(fieldName).asText());
                } catch (NumberFormatException ignored) {
                    return null;
                }
            }
        }
        return null;
    }

    private Long longValue(JsonNode node, String... fieldNames) {
        for (String fieldName : fieldNames) {
            if (node.hasNonNull(fieldName)) {
                try {
                    return Long.valueOf(node.get(fieldName).asText());
                } catch (NumberFormatException ignored) {
                    return null;
                }
            }
        }
        return null;
    }

    private String textValue(JsonNode node, String... fieldNames) {
        for (String fieldName : fieldNames) {
            if (node.hasNonNull(fieldName)) {
                return node.get(fieldName).asText();
            }
        }
        return null;
    }

    private void persistNewsEvent(EventRaw eventRaw, JsonNode node) {
        if (!node.hasNonNull("headline")) {
            return;
        }
        NewsEvent newsEvent = new NewsEvent();
        newsEvent.setTraceId(eventRaw.getTraceId());
        newsEvent.setSymbol(eventRaw.getSymbol());
        newsEvent.setSource(node.hasNonNull("source") ? node.get("source").asText() : defaultSource(eventRaw));
        newsEvent.setHeadline(node.get("headline").asText());
        eventIngestMapper.insertNewsEvent(newsEvent);
    }

    private void persistOnchainEvent(EventRaw eventRaw, JsonNode node) {
        if (!node.hasNonNull("wallet")) {
            return;
        }
        OnchainEvent onchainEvent = new OnchainEvent();
        onchainEvent.setTraceId(eventRaw.getTraceId());
        onchainEvent.setSymbol(eventRaw.getSymbol());
        onchainEvent.setWallet(node.get("wallet").asText());
        onchainEvent.setPayloadJson(eventRaw.getPayloadJson());
        eventIngestMapper.insertOnchainEvent(onchainEvent);
    }

    private void persistSocialEvent(EventRaw eventRaw, JsonNode node) {
        if (!node.hasNonNull("score")) {
            return;
        }
        SocialEvent socialEvent = new SocialEvent();
        socialEvent.setTraceId(eventRaw.getTraceId());
        socialEvent.setSymbol(eventRaw.getSymbol());
        socialEvent.setScore(node.get("score").asDouble());
        socialEvent.setPayloadJson(eventRaw.getPayloadJson());
        eventIngestMapper.insertSocialEvent(socialEvent);
    }

    private String defaultSource(EventRaw eventRaw) {
        if (eventRaw.getExchangeCode() != null && !eventRaw.getExchangeCode().isBlank()) {
            return eventRaw.getExchangeCode();
        }
        return "external";
    }
}
