package com.ruoyi.dca.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.core.redis.RedisCache;
import com.ruoyi.dca.client.BinanceMarketApiClient;
import com.ruoyi.dca.client.FearGreedIndexClient;
import com.ruoyi.dca.client.OkxMarketApiClient;
import com.ruoyi.dca.domain.MarketData;
import com.ruoyi.dca.domain.MarketData;
import com.ruoyi.dca.domain.MarketDataCollectLog;
import com.ruoyi.dca.domain.MarketDataConfig;
import com.ruoyi.dca.mapper.MarketDataCollectLogMapper;
import com.ruoyi.dca.mapper.MarketDataMapper;
import com.ruoyi.dca.service.IMarketDataCollectService;
import com.ruoyi.dca.service.IMarketDataConfigService;
import com.ruoyi.dca.service.IMarketApiConfigService;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import com.ruoyi.dca.domain.MarketApiConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.util.concurrent.TimeUnit;
import java.util.Comparator;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

/**
 * 市场数据采集服务实现
 *
 * @author ruoyi
 * @date 2026-04-05
 */
@Service
public class MarketDataCollectServiceImpl implements IMarketDataCollectService {

    private static final Logger log = LoggerFactory.getLogger(MarketDataCollectServiceImpl.class);

    private static final String REDIS_KEY_PREFIX = "market:data:";
    private static final int REDIS_TTL_SECONDS = 3600; // 1小时
    private static final int HISTORY_CACHE_LIMIT = 24 * 7;
    private static final int HISTORY_REDIS_TTL_SECONDS = 7 * 24 * 3600;
    private static final String COLLECT_TYPE_MANUAL = "MANUAL";
    private static final String COLLECT_TYPE_SCHEDULED = "SCHEDULED";

    @Autowired
    private MarketDataMapper marketDataMapper;

    @Autowired
    private MarketDataCollectLogMapper collectLogMapper;

    @Autowired
    private IMarketDataConfigService configService;

    @Autowired
    private IMarketApiConfigService apiConfigService;

    @Autowired
    private OkxMarketApiClient okxClient;

    @Autowired
    private BinanceMarketApiClient binanceClient;

    @Autowired
    private FearGreedIndexClient fearGreedClient;

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private RedisCache redisCache;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    @Transactional
    public MarketData collectMarketData(String symbol) {
        return collectMarketData(symbol, COLLECT_TYPE_MANUAL);
    }

    private MarketData collectMarketData(String symbol, String collectType) {
        long startTime = System.currentTimeMillis();
        List<String> errorMessages = new ArrayList<>();

        try {
            log.info("开始采集市场数据: {}", symbol);

            // 获取配置（如果存在）
            MarketDataConfig config = configService.selectConfigBySymbol(symbol);
            if (config == null) {
                config = createDefaultConfig(symbol);
            }

            MarketData marketData = new MarketData();
            marketData.setSymbol(symbol);
            marketData.setTimestamp(System.currentTimeMillis());
            marketData.setCollectionTime(TradeRuntimeTimeUtils.nowSqlDateTime());

            // 1. 采集基础价格和成交量数据（必须成功）
            boolean priceSuccess = collectPriceData(marketData, symbol, config);
            if (!priceSuccess) {
                String errorMsg = "价格数据采集失败";
                errorMessages.add(errorMsg);
                log.error("{}: {}", symbol, errorMsg);
            }

            // 2. 采集K线数据
            if ("1".equals(config.getCollectKline())) {
                boolean klineSuccess = collectKlineData(marketData, symbol, config);
                if (!klineSuccess) {
                    String errorMsg = "K线数据采集失败";
                    errorMessages.add(errorMsg);
                    log.warn("{}: {}", symbol, errorMsg);
                }
            }

            // 3. 采集恐慌贪婪指数
            if ("1".equals(config.getCollectFearGreed())) {
                boolean fgSuccess = collectFearGreedData(marketData);
                if (!fgSuccess) {
                    String errorMsg = "恐慌指数采集失败";
                    errorMessages.add(errorMsg);
                    log.warn("{}: {}", symbol, errorMsg);
                }
            }

            // 验证必要数据是否采集成功
            if (marketData.getPrice() == null) {
                throw new RuntimeException("价格数据为空，无法保存: " + String.join("; ", errorMessages));
            }

            // 4. 保存到数据库
            marketDataMapper.insertMarketData(marketData);

            // 5. 缓存到Redis（扁平化JSON）
            cacheMarketData(marketData);

            long duration = System.currentTimeMillis() - startTime;
            log.info("市场数据采集完成: {}, 价格: {}, 耗时: {}ms", symbol, marketData.getPrice(), duration);

            // 记录成功日志
            String errorMsg = errorMessages.isEmpty() ? null : String.join("; ", errorMessages);
            collectLog(symbol, collectType, "1", 1, 0, duration, errorMsg, marketData.getDataSource());

            return marketData;

        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            String fullErrorMsg = e.getMessage();
            if (!errorMessages.isEmpty()) {
                fullErrorMsg = e.getMessage() + " | " + String.join("; ", errorMessages);
            }
            log.error("市场数据采集失败: {}, 错误: {}", symbol, fullErrorMsg, e);
            collectLog(symbol, collectType, "0", 0, 1, duration, fullErrorMsg, null);
            return null;
        }
    }

    @Override
    @Transactional
    public Map<String, MarketData> collectAllEnabledConfigs() {
        return collectAllEnabledConfigs(COLLECT_TYPE_SCHEDULED);
    }

    @Override
    @Transactional
    public Map<String, MarketData> collectAllEnabledConfigs(String collectType) {
        long startTime = System.currentTimeMillis();
        Map<String, MarketData> results = new ConcurrentHashMap<>();
        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failCount = new AtomicInteger(0);
        Set<String> dataSources = Collections.synchronizedSet(new HashSet<>());

        try {
            // 获取所有启用的配置
            List<MarketDataConfig> configs = configService.selectEnabledConfigs();
            log.info("开始批量采集市场数据，共{}个交易对", configs.size());

            // 并行采集
            configs.parallelStream().forEach(config -> {
                try {
                    MarketData data = collectMarketData(config.getSymbol());
                    if (data != null) {
                        results.put(config.getSymbol(), data);
                        successCount.incrementAndGet();
                        if (data.getDataSource() != null) {
                            dataSources.add(data.getDataSource());
                        }
                    } else {
                        failCount.incrementAndGet();
                    }
                } catch (Exception e) {
                    log.error("采集失败: {}", config.getSymbol(), e);
                    failCount.incrementAndGet();
                }
            });

            long duration = System.currentTimeMillis() - startTime;
            log.info("批量采集完成: 成功={}, 失败={}, 耗时={}ms", successCount.get(), failCount.get(), duration);

        } catch (Exception e) {
            log.error("批量采集异常", e);
        }

        return results;
    }

    @Override
    public Map<String, Object> triggerManualCollection(String... symbols) {
        Map<String, Object> result = new HashMap<>();
        List<String> successList = new ArrayList<>();
        List<String> failList = new ArrayList<>();

        for (String symbol : symbols) {
            try {
                MarketData data = collectMarketData(symbol);
                if (data != null) {
                    successList.add(symbol);
                } else {
                    failList.add(symbol);
                }
            } catch (Exception e) {
                failList.add(symbol);
            }
        }

        result.put("total", symbols.length);
        result.put("success", successList);
        result.put("failed", failList);
        result.put("successCount", successList.size());
        result.put("failCount", failList.size());

        return result;
    }

    @Override
    public MarketData getLatestMarketData(String symbol) {
        try {
            // 先从Redis获取
            String redisKey = REDIS_KEY_PREFIX + symbol + ":current";
            Object cached = redisCache.getCacheObject(redisKey);

            if (cached != null) {
                return objectMapper.convertValue(cached, MarketData.class);
            }

            // Redis未命中，从数据库获取
            MarketData data = marketDataMapper.selectLatestMarketData(symbol);

            // 缓存到Redis
            if (data != null) {
                redisCache.setCacheObject(redisKey, data, REDIS_TTL_SECONDS, TimeUnit.SECONDS);
            }

            return data;

        } catch (Exception e) {
            log.error("获取市场数据失败: {}", symbol, e);
            return null;
        }
    }

    @Override
    public List<MarketData> getMarketDataHistory(String symbol, int days) {
        try {
            int limit = Math.max(days * 24, 1);

            List<MarketData> cachedHistory = getHistoryFromRedis(symbol, limit);
            if (!cachedHistory.isEmpty()) {
                return cachedHistory;
            }

            LocalDateTime endTime = TradeRuntimeTimeUtils.nowDatabaseLocalDateTime();
            LocalDateTime startTime = endTime.minusDays(days);

            return marketDataMapper.selectMarketDataHistory(symbol, startTime, endTime, limit);

        } catch (Exception e) {
            log.error("鑾峰彇鍘嗗彶鏁版嵁澶辫触: {}", symbol, e);
            return Collections.emptyList();
        }
    }

    @Override
    public Integer getFearGreedIndex() {
        try {
            // 从任意交易对获取最新的恐慌指数
            MarketData data = marketDataMapper.selectLatestFearGreedIndex();
            return data != null ? data.getFearGreedIndex() : null;

        } catch (Exception e) {
            log.error("获取恐慌贪婪指数失败", e);
            return null;
        }
    }

    /**
     * 采集价格和成交量数据
     *
     * @return true表示成功，false表示失败
     */
    private boolean collectPriceData(MarketData marketData, String symbol, MarketDataConfig config) {
        try {
            // 获取所有启用的PRICE类型API配置，按优先级排序
            List<MarketApiConfig> apiConfigs = apiConfigService.selectEnabledApis("PRICE");

            if (apiConfigs == null || apiConfigs.isEmpty()) {
                log.warn("没有找到启用的价格数据API配置，使用默认客户端");
                return collectPriceDataFromDefaultClient(marketData, symbol);
            }

            // 按优先级排序（数字越小优先级越高）
            apiConfigs.sort(Comparator.comparing(MarketApiConfig::getPriority));

            // 依次尝试每个API
            for (MarketApiConfig apiConfig : apiConfigs) {
                try {
                    // 检查API是否适用于当前交易对
                    if (!isApiApplicable(apiConfig, symbol)) {
                        continue;
                    }

                    Map<String, Object> data = callApi(apiConfig, symbol);
                    if (data != null && data.get("price") != null) {
                        // 使用字段映射填充数据
                        fillPriceDataFromApiResponse(marketData, data, apiConfig);
                        marketData.setDataSource(apiConfig.getApiName());
                        log.info("使用API {} 成功采集价格数据: {} = {}", apiConfig.getApiName(), symbol, marketData.getPrice());
                        return true;
                    }
                } catch (Exception e) {
                    log.warn("API {} 调用失败: {}", apiConfig.getApiName(), e.getMessage());
                }
            }

            log.warn("所有价格API都失败，尝试默认客户端");
            return collectPriceDataFromDefaultClient(marketData, symbol);

        } catch (Exception e) {
            log.error("采集价格数据失败: {}", symbol, e);
            return false;
        }
    }

    /**
     * 从默认客户端采集价格数据（兜底方案）
     */
    private boolean collectPriceDataFromDefaultClient(MarketData marketData, String symbol) {
        try {
            // 解析数据源优先级
            List<String> dataSources = parseDataSources(configService.selectConfigBySymbol(symbol) != null ?
                configService.selectConfigBySymbol(symbol).getDataSources() : "[\"okx\",\"binance\"]");

            Map<String, Object> tickerData = null;

            // 按优先级尝试数据源
            for (String source : dataSources) {
                if ("okx".equalsIgnoreCase(source)) {
                    tickerData = okxClient.getTicker(symbol.replace("USDT", "-USDT"));
                } else if ("binance".equalsIgnoreCase(source)) {
                    tickerData = binanceClient.getTicker(symbol);
                }

                if (tickerData != null) {
                    marketData.setDataSource((String) tickerData.get("source"));
                    break;
                }
            }

            if (tickerData != null && tickerData.get("price") != null) {
                marketData.setPrice((BigDecimal) tickerData.get("price"));
                marketData.setVolume24h((BigDecimal) tickerData.get("volume_24h"));
                marketData.setVolume24hBase((BigDecimal) tickerData.get("volume_24h_base"));
                marketData.setHigh24h((BigDecimal) tickerData.get("high_24h"));
                marketData.setLow24h((BigDecimal) tickerData.get("low_24h"));
                marketData.setPriceChange24h((BigDecimal) tickerData.get("price_change_24h"));
                marketData.setPriceChangePercent24h((BigDecimal) tickerData.get("price_change_percent_24h"));
                return true;
            }

            return false;

        } catch (Exception e) {
            log.error("默认客户端采集价格数据失败: {}", symbol, e);
            return false;
        }
    }

    /**
     * 采集K线数据
     *
     * @return true表示至少一个周期成功，false表示全部失败
     */
    private boolean collectKlineData(MarketData marketData, String symbol, MarketDataConfig config) {
        boolean success = false;

        try {
            // 获取所有启用的KLINE类型API配置
            List<MarketApiConfig> apiConfigs = apiConfigService.selectEnabledApis("KLINE");

            if (apiConfigs != null && !apiConfigs.isEmpty()) {
                // 按优先级排序
                apiConfigs.sort(Comparator.comparing(MarketApiConfig::getPriority));

                String[] periods = config.getKlinePeriods().split(",");

                for (String period : periods) {
                    period = period.trim();
                    boolean periodSuccess = false;

                    // 依次尝试每个API
                    for (MarketApiConfig apiConfig : apiConfigs) {
                        if (!isApiApplicable(apiConfig, symbol)) {
                            continue;
                        }

                        // 检查dataSubType是否匹配
                        if (apiConfig.getDataSubType() != null &&
                            !period.toUpperCase().replace("H", "H").equals(apiConfig.getDataSubType())) {
                            continue;
                        }

                        try {
                            Map<String, Object> klineData = callApi(apiConfig, symbol);
                            if (klineData != null && klineData.get("open") != null) {
                                fillKlineDataFromApiResponse(marketData, klineData, period, apiConfig);
                                log.info("使用API {} 成功采集{}K线数据", apiConfig.getApiName(), period);
                                periodSuccess = true;
                                success = true;
                                break;
                            }
                        } catch (Exception e) {
                            log.warn("API {} 采集{}K线失败: {}", apiConfig.getApiName(), period, e.getMessage());
                        }
                    }

                    if (!periodSuccess) {
                        log.warn("所有API都无法采集{}K线数据", period);
                    }
                }
            }

            // 如果API配置方式失败，使用默认客户端
            if (!success) {
                success = collectKlineDataFromDefaultClient(marketData, symbol, config);
            }

        } catch (Exception e) {
            log.error("采集K线数据失败: {}", symbol, e);
            return false;
        }

        return success;
    }

    /**
     * 从默认客户端采集K线数据
     */
    private boolean collectKlineDataFromDefaultClient(MarketData marketData, String symbol, MarketDataConfig config) {
        boolean success = false;

        try {
            String[] periods = config.getKlinePeriods().split(",");

            for (String period : periods) {
                period = period.trim();
                String okxPeriod = period.replace("h", "H").replace("d", "D");

                // 优先使用OKX
                Map<String, Object> kline = okxClient.getLatestKline(
                    symbol.replace("USDT", "-USDT"), okxPeriod);

                // 失败则使用Binance
                if (kline == null) {
                    String binancePeriod = period.toLowerCase();
                    kline = binanceClient.getLatestKline(symbol, binancePeriod);
                }

                if (kline != null && kline.get("open") != null) {
                    switch (period) {
                        case "1H":
                            marketData.setKline1hOpen((BigDecimal) kline.get("open"));
                            marketData.setKline1hHigh((BigDecimal) kline.get("high"));
                            marketData.setKline1hLow((BigDecimal) kline.get("low"));
                            marketData.setKline1hClose((BigDecimal) kline.get("close"));
                            marketData.setKline1hVolume((BigDecimal) kline.get("volume"));
                            marketData.setKline1hTimestamp((Long) kline.get("timestamp"));
                            success = true;
                            break;
                        case "4H":
                            marketData.setKline4hOpen((BigDecimal) kline.get("open"));
                            marketData.setKline4hHigh((BigDecimal) kline.get("high"));
                            marketData.setKline4hLow((BigDecimal) kline.get("low"));
                            marketData.setKline4hClose((BigDecimal) kline.get("close"));
                            marketData.setKline4hVolume((BigDecimal) kline.get("volume"));
                            marketData.setKline4hTimestamp((Long) kline.get("timestamp"));
                            success = true;
                            break;
                        case "1D":
                            marketData.setKline1dOpen((BigDecimal) kline.get("open"));
                            marketData.setKline1dHigh((BigDecimal) kline.get("high"));
                            marketData.setKline1dLow((BigDecimal) kline.get("low"));
                            marketData.setKline1dClose((BigDecimal) kline.get("close"));
                            marketData.setKline1dVolume((BigDecimal) kline.get("volume"));
                            marketData.setKline1dTimestamp((Long) kline.get("timestamp"));
                            success = true;
                            break;
                    }
                }
            }

        } catch (Exception e) {
            log.error("默认客户端采集K线数据失败: {}", symbol, e);
            return false;
        }

        return success;
    }

    /**
     * 根据字段映射填充K线数据
     */
    private void fillKlineDataFromApiResponse(MarketData marketData, Map<String, Object> data, String period, MarketApiConfig apiConfig) {
        try {
            Map<String, String> fieldMapping = objectMapper.readValue(
                apiConfig.getFieldMapping(), new TypeReference<Map<String, String>>() {});

            BigDecimal open = null, high = null, low = null, close = null, volume = null;
            Long timestamp = null;

            if (fieldMapping.containsKey("open")) {
                Object value = getNestedValue(data, fieldMapping.get("open"));
                if (value != null) open = new BigDecimal(value.toString());
            }
            if (fieldMapping.containsKey("high")) {
                Object value = getNestedValue(data, fieldMapping.get("high"));
                if (value != null) high = new BigDecimal(value.toString());
            }
            if (fieldMapping.containsKey("low")) {
                Object value = getNestedValue(data, fieldMapping.get("low"));
                if (value != null) low = new BigDecimal(value.toString());
            }
            if (fieldMapping.containsKey("close")) {
                Object value = getNestedValue(data, fieldMapping.get("close"));
                if (value != null) close = new BigDecimal(value.toString());
            }
            if (fieldMapping.containsKey("volume")) {
                Object value = getNestedValue(data, fieldMapping.get("volume"));
                if (value != null) volume = new BigDecimal(value.toString());
            }
            if (fieldMapping.containsKey("timestamp")) {
                Object value = getNestedValue(data, fieldMapping.get("timestamp"));
                if (value != null) timestamp = Long.valueOf(value.toString());
            }

            switch (period.toUpperCase()) {
                case "1H" -> {
                    marketData.setKline1hOpen(open);
                    marketData.setKline1hHigh(high);
                    marketData.setKline1hLow(low);
                    marketData.setKline1hClose(close);
                    marketData.setKline1hVolume(volume);
                    marketData.setKline1hTimestamp(timestamp);
                }
                case "4H" -> {
                    marketData.setKline4hOpen(open);
                    marketData.setKline4hHigh(high);
                    marketData.setKline4hLow(low);
                    marketData.setKline4hClose(close);
                    marketData.setKline4hVolume(volume);
                    marketData.setKline4hTimestamp(timestamp);
                }
                case "1D" -> {
                    marketData.setKline1dOpen(open);
                    marketData.setKline1dHigh(high);
                    marketData.setKline1dLow(low);
                    marketData.setKline1dClose(close);
                    marketData.setKline1dVolume(volume);
                    marketData.setKline1dTimestamp(timestamp);
                }
            }

        } catch (Exception e) {
            log.error("填充K线数据失败", e);
        }
    }

    /**
     * 采集恐慌贪婪指数
     *
     * @return true表示成功，false表示失败
     */
    private boolean collectFearGreedData(MarketData marketData) {
        try {
            // 获取所有启用的FEAR_GREED类型API配置
            List<MarketApiConfig> apiConfigs = apiConfigService.selectEnabledApis("FEAR_GREED");

            if (apiConfigs != null && !apiConfigs.isEmpty()) {
                // 按优先级排序
                apiConfigs.sort(Comparator.comparing(MarketApiConfig::getPriority));

                for (MarketApiConfig apiConfig : apiConfigs) {
                    try {
                        Map<String, Object> fgData = callApi(apiConfig, null);
                        if (fgData != null && fgData.get("value") != null) {
                            marketData.setFearGreedIndex(Integer.valueOf(fgData.get("value").toString()));
                            if (fgData.containsKey("classification")) {
                                marketData.setFearGreedClassification(fgData.get("classification").toString());
                            }
                            log.info("使用API {} 成功采集恐慌指数: {}", apiConfig.getApiName(), marketData.getFearGreedIndex());
                            return true;
                        }
                    } catch (Exception e) {
                        log.warn("API {} 采集恐慌指数失败: {}", apiConfig.getApiName(), e.getMessage());
                    }
                }
            }

            // 如果API配置方式失败，使用默认客户端
            Map<String, Object> fgData = fearGreedClient.getLatestFearGreedIndex();
            if (fgData != null && fgData.get("value") != null) {
                marketData.setFearGreedIndex((Integer) fgData.get("value"));
                marketData.setFearGreedClassification((String) fgData.get("classification"));
                return true;
            }
            return false;

        } catch (Exception e) {
            log.error("采集恐慌贪婪指数失败", e);
            return false;
        }
    }

    /**
     * 缓存市场数据到Redis
     */
    private void cacheMarketData(MarketData marketData) {
        try {
            String redisKey = REDIS_KEY_PREFIX + marketData.getSymbol() + ":current";
            redisCache.setCacheObject(redisKey, marketData, REDIS_TTL_SECONDS, TimeUnit.SECONDS);

            String historyKey = REDIS_KEY_PREFIX + marketData.getSymbol() + ":history";
            redisCache.redisTemplate.opsForList().rightPush(historyKey, marketData);
            redisCache.redisTemplate.opsForList().trim(historyKey, -HISTORY_CACHE_LIMIT, -1);
            redisCache.expire(historyKey, HISTORY_REDIS_TTL_SECONDS, TimeUnit.SECONDS);

        } catch (Exception e) {
            log.error("缓存市场数据失败: {}", marketData.getSymbol(), e);
        }
    }

    private List<MarketData> getHistoryFromRedis(String symbol, int limit) {
        try {
            if (limit <= 0 || limit > HISTORY_CACHE_LIMIT) {
                return Collections.emptyList();
            }

            String historyKey = REDIS_KEY_PREFIX + symbol + ":history";
            List<?> cachedHistory = redisCache.getCacheList(historyKey);
            if (cachedHistory == null || cachedHistory.size() < limit) {
                return Collections.emptyList();
            }

            List<MarketData> normalized = new ArrayList<>();
            for (Object item : cachedHistory) {
                if (item != null) {
                    normalized.add(objectMapper.convertValue(item, MarketData.class));
                }
            }

            if (normalized.size() < limit) {
                return Collections.emptyList();
            }

            if (normalized.size() > limit) {
                normalized = new ArrayList<>(normalized.subList(normalized.size() - limit, normalized.size()));
            }

            Collections.reverse(normalized);
            return normalized;
        } catch (Exception e) {
            log.warn("Failed to read market history from Redis for {}", symbol, e);
            return Collections.emptyList();
        }
    }

    /**
     * 解析数据源配置
     */
    private List<String> parseDataSources(String dataSourcesJson) {
        try {
            if (dataSourcesJson != null && !dataSourcesJson.isEmpty()) {
                return objectMapper.readValue(dataSourcesJson, new TypeReference<List<String>>() {});
            }
        } catch (Exception e) {
            log.warn("解析数据源配置失败: {}", dataSourcesJson, e);
        }

        // 返回默认数据源
        return Arrays.asList("okx", "binance");
    }

    /**
     * 创建默认配置
     */
    private MarketDataConfig createDefaultConfig(String symbol) {
        MarketDataConfig config = new MarketDataConfig();
        config.setSymbol(symbol);
        config.setEnabled("1");
        config.setCollectInterval(3600);
        config.setDataSources("[\"okx\",\"binance\"]");
        config.setCollectKline("1");
        config.setKlinePeriods("1H,4H,1D");
        config.setCollectFearGreed("1");
        config.setCollectOnchain("0");
        return config;
    }

    /**
     * 检查API是否适用于当前交易对
     */
    private boolean isApiApplicable(MarketApiConfig apiConfig, String symbol) {
        if (apiConfig.getApplySymbols() == null || apiConfig.getApplySymbols().isEmpty()) {
            return true; // 未设置限制，适用于所有交易对
        }

        try {
            List<String> applicableSymbols = objectMapper.readValue(
                apiConfig.getApplySymbols(), new TypeReference<List<String>>() {});
            return applicableSymbols.contains(symbol);
        } catch (Exception e) {
            log.warn("解析适用交易对失败: {}", apiConfig.getApplySymbols(), e);
            return true;
        }
    }

    /**
     * 调用API并返回解析后的数据
     */
    private Map<String, Object> callApi(MarketApiConfig apiConfig, String symbol) {
        try {
            String url = buildApiUrl(apiConfig.getApiUrl(), symbol);

            Object responseData;
            if ("GET".equalsIgnoreCase(apiConfig.getHttpMethod())) {
                responseData = sendGetRequest(url, apiConfig.getRequestHeaders());
            } else {
                responseData = sendPostRequest(url, apiConfig.getRequestHeaders(), apiConfig.getRequestBody());
            }

            if (responseData == null) {
                return null;
            }

            if (apiConfig.getResponsePath() != null && !apiConfig.getResponsePath().isEmpty()) {
                return extractDataByPath(responseData, apiConfig.getResponsePath());
            }

            return toMapObject(responseData);
        } catch (Exception e) {
            log.error("API call failed: {} - {}", apiConfig.getApiName(), e.getMessage());
            return null;
        }
    }

    private String buildApiUrl(String templateUrl, String symbol) {
        String url = templateUrl
            .replace("{symbol}", symbol)
            .replace("{symbol_okx}", symbol.replace("USDT", "-USDT"))
            .replace("{symbol_binance}", symbol)
            .replace("{symbol_gate}", symbol.replace("USDT", "_USDT"))
            .replace("{symbol_lower}", symbol.toLowerCase());
        return url;
    }

    /**
     * 发送GET请求
     */
    private Object sendGetRequest(String url, String headersJson) {
        try {
            String response = restTemplate.getForObject(url, String.class);
            return objectMapper.readValue(response, Object.class);
        } catch (Exception e) {
            log.error("GET request failed: {}", url, e);
            return null;
        }
    }

    private Object sendPostRequest(String url, String headersJson, String bodyJson) {
        try {
            String response = restTemplate.postForObject(url, bodyJson, String.class);
            return objectMapper.readValue(response, Object.class);
        } catch (Exception e) {
            log.error("POST request failed: {}", url, e);
            return null;
        }
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
            log.warn("Failed to extract data by path: path={}", path, e);
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
        merged.putAll(extractedMap);
        return merged;
    }

    private Map<String, Object> toMapObject(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Map) {
            return objectMapper.convertValue(value, new TypeReference<Map<String, Object>>() {});
        }
        if (value instanceof List) {
            Map<String, Object> indexed = new HashMap<>();
            List<?> list = (List<?>) value;
            for (int i = 0; i < list.size(); i++) {
                indexed.put(String.valueOf(i), list.get(i));
            }
            return indexed;
        }
        return objectMapper.convertValue(value, new TypeReference<Map<String, Object>>() {});
    }

    private void fillPriceDataFromApiResponse(MarketData marketData, Map<String, Object> data, MarketApiConfig apiConfig) {
        try {
            Map<String, String> fieldMapping = objectMapper.readValue(
                apiConfig.getFieldMapping(), new TypeReference<Map<String, String>>() {});

            if (fieldMapping.containsKey("price")) {
                BigDecimal value = toBigDecimal(getNestedValue(data, fieldMapping.get("price")));
                if (value != null) {
                    marketData.setPrice(value);
                }
            }
            if (fieldMapping.containsKey("volume_24h")) {
                BigDecimal value = toBigDecimal(getNestedValue(data, fieldMapping.get("volume_24h")));
                if (value != null) {
                    marketData.setVolume24h(value);
                }
            }
            if (fieldMapping.containsKey("volume_24h_base")) {
                BigDecimal value = toBigDecimal(getNestedValue(data, fieldMapping.get("volume_24h_base")));
                if (value != null) {
                    marketData.setVolume24hBase(value);
                }
            }
            if (fieldMapping.containsKey("high_24h")) {
                BigDecimal value = toBigDecimal(getNestedValue(data, fieldMapping.get("high_24h")));
                if (value != null) {
                    marketData.setHigh24h(value);
                }
            }
            if (fieldMapping.containsKey("low_24h")) {
                BigDecimal value = toBigDecimal(getNestedValue(data, fieldMapping.get("low_24h")));
                if (value != null) {
                    marketData.setLow24h(value);
                }
            }
            if (fieldMapping.containsKey("price_change_24h")) {
                BigDecimal value = toBigDecimal(getNestedValue(data, fieldMapping.get("price_change_24h")));
                if (value != null) {
                    marketData.setPriceChange24h(value);
                }
            }
            if (fieldMapping.containsKey("price_change_percent_24h")) {
                BigDecimal value = toBigDecimal(getNestedValue(data, fieldMapping.get("price_change_percent_24h")));
                if (value != null) {
                    marketData.setPriceChangePercent24h(value);
                }
            }

            deriveMissingPriceFields(marketData, data);
        } catch (Exception e) {
            log.error("Failed to fill price data", e);
        }
    }

    private void deriveMissingPriceFields(MarketData marketData, Map<String, Object> data) {
        if (marketData.getPrice() == null) {
            marketData.setPrice(firstBigDecimal(data, "last", "lastPrice", "close"));
        }
        if (marketData.getVolume24h() == null) {
            marketData.setVolume24h(firstBigDecimal(data, "volCcy24h", "volCcy", "quoteVolume", "vol"));
        }
        if (marketData.getVolume24hBase() == null) {
            marketData.setVolume24hBase(firstBigDecimal(data, "vol24h", "amount", "volume", "vol"));
        }
        if (marketData.getHigh24h() == null) {
            marketData.setHigh24h(firstBigDecimal(data, "high24h", "high", "highPrice"));
        }
        if (marketData.getLow24h() == null) {
            marketData.setLow24h(firstBigDecimal(data, "low24h", "low", "lowPrice"));
        }

        BigDecimal currentPrice = marketData.getPrice();
        BigDecimal openPrice = firstBigDecimal(data, "open24h", "open");
        if (currentPrice != null && openPrice != null && openPrice.compareTo(BigDecimal.ZERO) > 0) {
            if (marketData.getPriceChange24h() == null) {
                marketData.setPriceChange24h(currentPrice.subtract(openPrice));
            }
            if (marketData.getPriceChangePercent24h() == null) {
                marketData.setPriceChangePercent24h(
                        currentPrice.subtract(openPrice)
                                .divide(openPrice, 4, BigDecimal.ROUND_HALF_UP)
                                .multiply(new BigDecimal("100"))
                );
            }
        }
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
            log.warn("Failed to resolve field: {}", fieldPath, e);
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
            if (!(current instanceof Map)) {
                return null;
            }
            current = ((Map<?, ?>) current).get(part);
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
                .divide(baseValue, 4, BigDecimal.ROUND_HALF_UP)
                .multiply(new BigDecimal("100"));
    }

    private void collectLog(String symbol, String collectType, String status,
                           int successCount, int failCount, long durationMs,
                           String errorMessage, String dataSourcesUsed) {
        try {
            MarketDataCollectLog log = new MarketDataCollectLog();
            log.setSymbol(symbol);
            log.setCollectType(collectType);
            log.setStatus(status);
            log.setSuccessCount(successCount);
            log.setFailCount(failCount);
            log.setDurationMs(durationMs);
            log.setErrorMessage(errorMessage);
            log.setDataSourcesUsed(dataSourcesUsed);
            collectLogMapper.insertMarketDataCollectLog(log);
        } catch (Exception e) {
            // 日志记录失败不影响主流程
        }
    }
}
