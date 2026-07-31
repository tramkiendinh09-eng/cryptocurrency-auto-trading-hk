package com.ruoyi.web.controller.monitor;

import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.system.domain.SysCache;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.connection.DataType;
import org.springframework.data.redis.connection.Limit;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.RecordId;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StreamOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class CacheControllerTest
{
    private CacheController controller;

    @BeforeEach
    void setUp()
    {
        controller = new CacheController();
    }

    @Test
    void cacheShouldExposeMarketCachePrefixes()
    {
        AjaxResult result = controller.cache();
        @SuppressWarnings("unchecked")
        List<SysCache> caches = (List<SysCache>) result.get(AjaxResult.DATA_TAG);

        assertTrue(caches.stream().anyMatch(cache -> "market:data:".equals(cache.getCacheName())));
        assertTrue(caches.stream().anyMatch(cache -> "dca:price:".equals(cache.getCacheName())));
        assertTrue(caches.stream().anyMatch(cache -> "trade.runtime.events".equals(cache.getCacheName())));
        assertTrue(caches.stream().anyMatch(cache -> "trade.runtime.events.dlq".equals(cache.getCacheName())));
        assertTrue(caches.stream().anyMatch(cache -> "trade.runtime.events:retries".equals(cache.getCacheName())));
        assertTrue(caches.stream().anyMatch(cache -> "trade.runtime.events:processed:".equals(cache.getCacheName())));
    }

    @Test
    void getCacheValueShouldRenderRecentStreamEntries()
    {
        @SuppressWarnings("unchecked")
        RedisTemplate<String, String> redisTemplate = mock(RedisTemplate.class);
        @SuppressWarnings("unchecked")
        StreamOperations<String, Object, Object> streamOperations = mock(StreamOperations.class);

        MapRecord<String, Object, Object> record = MapRecord.create(
            "trade.runtime.events",
            Map.<Object, Object>of("event_type", "news", "headline", "ETF inflow")
        ).withId(RecordId.of("1-0"));

        when(redisTemplate.type("trade.runtime.events")).thenReturn(DataType.STREAM);
        when(redisTemplate.getExpire("trade.runtime.events")).thenReturn(60L);
        when(redisTemplate.opsForStream()).thenReturn(streamOperations);
        when(streamOperations.reverseRange(eq("trade.runtime.events"), any(), any(Limit.class))).thenReturn(List.of(record));

        ReflectionTestUtils.setField(controller, "redisTemplate", redisTemplate);

        AjaxResult result = controller.getCacheValue("trade.runtime.events", "trade.runtime.events");
        SysCache cache = (SysCache) result.get(AjaxResult.DATA_TAG);

        assertTrue(cache.getCacheValue().contains("\"id\" : \"1-0\""));
        assertTrue(cache.getCacheValue().contains("\"event_type\" : \"news\""));
    }
}
