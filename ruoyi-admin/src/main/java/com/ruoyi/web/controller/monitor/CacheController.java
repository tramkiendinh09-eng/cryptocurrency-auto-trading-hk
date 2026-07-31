package com.ruoyi.web.controller.monitor;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.constant.CacheConstants;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.utils.StringUtils;
import com.ruoyi.system.domain.SysCache;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Range;
import org.springframework.data.redis.connection.DataType;
import org.springframework.data.redis.connection.Limit;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

/**
 * 缓存监控
 *
 * 补全点：支持查看 String/List/Hash/Set/ZSet，并补充项目自定义 Redis 前缀。
 */
@RestController
@RequestMapping("/monitor/cache")
public class CacheController
{
    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private final static List<SysCache> caches = new ArrayList<SysCache>();
    {
        caches.add(new SysCache(CacheConstants.LOGIN_TOKEN_KEY, "用户信息"));
        caches.add(new SysCache(CacheConstants.SYS_CONFIG_KEY, "配置信息"));
        caches.add(new SysCache(CacheConstants.SYS_DICT_KEY, "数据字典"));
        caches.add(new SysCache(CacheConstants.CAPTCHA_CODE_KEY, "验证码"));
        caches.add(new SysCache(CacheConstants.REPEAT_SUBMIT_KEY, "防重复提交"));
        caches.add(new SysCache(CacheConstants.RATE_LIMIT_KEY, "限流处理"));
        caches.add(new SysCache(CacheConstants.PWD_ERR_CNT_KEY, "密码错误次数"));
        caches.add(new SysCache("market:data:", "市场数据当前值与历史窗口"));
        caches.add(new SysCache("dca:price:", "交易运行时价格缓存"));
        caches.add(new SysCache("trade.runtime.events", "运行时事件流（含新闻/链上/社交/行情事件）"));
        caches.add(new SysCache("trade.runtime.events.dlq", "运行时事件死信流"));
        caches.add(new SysCache("trade.runtime.events:retries", "运行时事件重试计数"));
        caches.add(new SysCache("trade.runtime.events:processed:", "运行时事件去重标记"));
        caches.add(new SysCache("dca:task:", "DCA任务队列与结果"));
        caches.add(new SysCache("dca:worker:heartbeat:", "Python Worker 心跳"));
    }

    @SuppressWarnings("deprecation")
    @PreAuthorize("@ss.hasPermi('monitor:cache:list')")
    @GetMapping()
    public AjaxResult getInfo() throws Exception
    {
        Properties info = (Properties) redisTemplate.execute((RedisCallback<Object>) connection -> connection.info());
        Properties commandStats = (Properties) redisTemplate.execute((RedisCallback<Object>) connection -> connection.info("commandstats"));
        Object dbSize = redisTemplate.execute((RedisCallback<Object>) connection -> connection.dbSize());

        Map<String, Object> result = new HashMap<>(3);
        result.put("info", info);
        result.put("dbSize", dbSize);

        List<Map<String, String>> pieList = new ArrayList<>();
        commandStats.stringPropertyNames().forEach(key -> {
            Map<String, String> data = new HashMap<>(2);
            String property = commandStats.getProperty(key);
            data.put("name", StringUtils.removeStart(key, "cmdstat_"));
            data.put("value", StringUtils.substringBetween(property, "calls=", ",usec"));
            pieList.add(data);
        });
        result.put("commandStats", pieList);
        return AjaxResult.success(result);
    }

    @PreAuthorize("@ss.hasPermi('monitor:cache:list')")
    @GetMapping("/getNames")
    public AjaxResult cache()
    {
        return AjaxResult.success(caches);
    }

    @PreAuthorize("@ss.hasPermi('monitor:cache:list')")
    @GetMapping("/getKeys/{cacheName}")
    public AjaxResult getCacheKeys(@PathVariable String cacheName)
    {
        Set<String> cacheKeys = redisTemplate.keys(cacheName + "*");
        return AjaxResult.success(cacheKeys == null ? new TreeSet<>() : new TreeSet<>(cacheKeys));
    }

    @PreAuthorize("@ss.hasPermi('monitor:cache:list')")
    @GetMapping("/getValue/{cacheName}/{cacheKey}")
    public AjaxResult getCacheValue(@PathVariable String cacheName, @PathVariable String cacheKey)
    {
        DataType dataType = redisTemplate.type(cacheKey);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", dataType != null ? dataType.code() : "none");
        payload.put("ttl", redisTemplate.getExpire(cacheKey));
        payload.put("value", getCacheObjectByType(cacheKey, dataType));

        SysCache sysCache = new SysCache(cacheName, cacheKey, formatCacheValue(payload));
        return AjaxResult.success(sysCache);
    }

    @PreAuthorize("@ss.hasPermi('monitor:cache:list')")
    @DeleteMapping("/clearCacheName/{cacheName}")
    public AjaxResult clearCacheName(@PathVariable String cacheName)
    {
        Collection<String> cacheKeys = redisTemplate.keys(cacheName + "*");
        if (cacheKeys != null && !cacheKeys.isEmpty()) {
            redisTemplate.delete(cacheKeys);
        }
        return AjaxResult.success();
    }

    @PreAuthorize("@ss.hasPermi('monitor:cache:list')")
    @DeleteMapping("/clearCacheKey/{cacheKey}")
    public AjaxResult clearCacheKey(@PathVariable String cacheKey)
    {
        redisTemplate.delete(cacheKey);
        return AjaxResult.success();
    }

    @PreAuthorize("@ss.hasPermi('monitor:cache:list')")
    @DeleteMapping("/clearCacheAll")
    public AjaxResult clearCacheAll()
    {
        Collection<String> cacheKeys = redisTemplate.keys("*");
        if (cacheKeys != null && !cacheKeys.isEmpty()) {
            redisTemplate.delete(cacheKeys);
        }
        return AjaxResult.success();
    }

    private Object getCacheObjectByType(String cacheKey, DataType dataType)
    {
        if (dataType == null) {
            return null;
        }
        if (DataType.STRING.equals(dataType)) {
            return redisTemplate.opsForValue().get(cacheKey);
        }
        if (DataType.LIST.equals(dataType)) {
            return redisTemplate.opsForList().range(cacheKey, 0, -1);
        }
        if (DataType.HASH.equals(dataType)) {
            return redisTemplate.opsForHash().entries(cacheKey);
        }
        if (DataType.SET.equals(dataType)) {
            return redisTemplate.opsForSet().members(cacheKey);
        }
        if (DataType.ZSET.equals(dataType)) {
            return redisTemplate.opsForZSet().rangeWithScores(cacheKey, 0, -1);
        }
        if (DataType.STREAM.equals(dataType)) {
            return redisTemplate.opsForStream()
                .reverseRange(cacheKey, Range.unbounded(), Limit.limit().count(20))
                .stream()
                .map(record -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("id", record.getId() != null ? record.getId().getValue() : "");
                    item.put("value", new LinkedHashMap<>(record.getValue()));
                    return item;
                })
                .collect(Collectors.toList());
        }
        return null;
    }

    private String formatCacheValue(Object cacheValue)
    {
        if (cacheValue == null) {
            return "";
        }
        if (cacheValue instanceof String stringValue) {
            try {
                Object json = objectMapper.readValue(stringValue, Object.class);
                return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(json);
            }
            catch (Exception ignored) {
                return stringValue;
            }
        }
        try {
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(cacheValue);
        }
        catch (JsonProcessingException e) {
            return String.valueOf(cacheValue);
        }
    }
}
