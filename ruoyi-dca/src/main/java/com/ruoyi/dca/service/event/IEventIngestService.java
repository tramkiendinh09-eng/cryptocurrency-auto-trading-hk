package com.ruoyi.dca.service.event;

import java.util.List;
import java.util.Map;

import com.ruoyi.dca.domain.event.EventRaw;

public interface IEventIngestService {

    void ingest(EventRaw eventRaw);

    List<Map<String, Object>> listRecentMarketHistory(String symbol, String exchange, Integer limit, Integer maxAgeMinutes);
}
