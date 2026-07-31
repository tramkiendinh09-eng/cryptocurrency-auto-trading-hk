package com.ruoyi.dca.service.memory;

import com.ruoyi.dca.domain.memory.TradeLifecycle;

import java.util.List;

public interface TradeLifecycleService {
    TradeLifecycle createLifecycle(TradeLifecycle lifecycle);
    TradeLifecycle getByTraceId(String traceId);
    TradeLifecycle updateLifecycle(String traceId, TradeLifecycle updates);
    List<TradeLifecycle> listClosedLifecycles(Integer limit);
}