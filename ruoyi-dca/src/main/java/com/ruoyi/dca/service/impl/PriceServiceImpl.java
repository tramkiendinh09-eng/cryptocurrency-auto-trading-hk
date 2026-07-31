package com.ruoyi.dca.service.impl;

import com.ruoyi.common.core.redis.RedisCache;
import com.ruoyi.dca.domain.dto.TaskDTO;
import com.ruoyi.dca.service.IPriceService;
import com.ruoyi.dca.service.ITaskQueueService;
import com.ruoyi.dca.service.support.ConfiguredPriceFetchSupport;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
public class PriceServiceImpl implements IPriceService {

    private static final Logger log = LoggerFactory.getLogger(PriceServiceImpl.class);
    private static final String PRICE_CACHE_KEY_PREFIX = "dca:price:";
    private static final int PRICE_CACHE_TTL = 60;

    private static final String[] SUPPORTED_SYMBOLS = {
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "MATICUSDT",
            "DOTUSDT"
    };

    @Autowired
    private RedisCache redisCache;

    @Autowired
    private ITaskQueueService taskQueueService;

    @Autowired
    private ConfiguredPriceFetchSupport configuredPriceFetchSupport;

    @Override
    public BigDecimal getCurrentPrice(String symbol) {
        try {
            String cacheKey = PRICE_CACHE_KEY_PREFIX + symbol;
            BigDecimal cachedPrice = parsePrice(redisCache.getCacheObject(cacheKey));
            if (cachedPrice != null && cachedPrice.compareTo(BigDecimal.ZERO) > 0) {
                log.debug("Got price from cache: {} = {}", symbol, cachedPrice);
                return cachedPrice;
            }

            log.warn("Price cache miss for {}, fetching synchronously from configured PRICE APIs...", symbol);
            ConfiguredPriceFetchSupport.PriceQuote quote = configuredPriceFetchSupport.fetchPrice(symbol);
            if (quote != null && quote.price() != null && quote.price().compareTo(BigDecimal.ZERO) > 0) {
                setPrice(symbol, quote.price(), PRICE_CACHE_TTL);
                log.info("Got price by configured direct fetch: {} = {}, source={}", symbol, quote.price(), quote.source());
                return quote.price();
            }

            log.warn("Configured direct price fetch failed for {}, submitting async refresh task", symbol);
            refreshPrice(symbol);
            return null;
        } catch (Exception e) {
            log.error("Failed to get current price for {}", symbol, e);
            return null;
        }
    }

    @Override
    public void refreshPrice(String symbol) {
        try {
            TaskDTO task = new TaskDTO();
            task.setTaskType("PRICE_CHECK");
            task.setPriority(1);
            task.setStatus("pending");
            task.setCreateTime(System.currentTimeMillis());

            Map<String, Object> taskData = new HashMap<>();
            taskData.put("symbol", symbol);
            taskData.put("include_gas", false);
            task.setTaskData(taskData);

            taskQueueService.pushTask(task);
            log.info("Submitted async price refresh task for {}", symbol);
        } catch (Exception e) {
            log.error("Failed to refresh price for {}", symbol, e);
        }
    }

    @Override
    public Map<String, BigDecimal> getAllPrices() {
        Map<String, BigDecimal> prices = new HashMap<>();
        for (String symbol : SUPPORTED_SYMBOLS) {
            prices.put(symbol, getCurrentPrice(symbol));
        }
        return prices;
    }

    @Override
    public void batchRefreshPrice(String... symbols) {
        if (symbols == null || symbols.length == 0) {
            symbols = SUPPORTED_SYMBOLS;
        }

        for (String symbol : symbols) {
            refreshPrice(symbol);
        }

        log.info("Submitted batch price refresh for {} symbols", symbols.length);
    }

    public void setPrice(String symbol, BigDecimal price, int ttlSeconds) {
        try {
            String cacheKey = PRICE_CACHE_KEY_PREFIX + symbol;
            redisCache.setCacheObject(cacheKey, price.toString(), ttlSeconds, TimeUnit.SECONDS);
            log.info("Set price for cache: {} = {} (TTL: {}s)", symbol, price, ttlSeconds);
        } catch (Exception e) {
            log.error("Failed to set price for {}", symbol, e);
        }
    }

    public String[] getSupportedSymbols() {
        return SUPPORTED_SYMBOLS.clone();
    }

    private BigDecimal parsePrice(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof BigDecimal) {
            return (BigDecimal) value;
        }
        if (value instanceof Number || value instanceof String) {
            try {
                return new BigDecimal(value.toString());
            } catch (Exception e) {
                return null;
            }
        }
        return null;
    }
}