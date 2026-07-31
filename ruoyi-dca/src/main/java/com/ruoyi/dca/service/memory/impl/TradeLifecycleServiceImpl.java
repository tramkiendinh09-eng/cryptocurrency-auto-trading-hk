package com.ruoyi.dca.service.memory.impl;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.memory.TradeLifecycle;
import com.ruoyi.dca.mapper.memory.TradeLifecycleMapper;
import com.ruoyi.dca.service.memory.TradeLifecycleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Locale;

@Service
public class TradeLifecycleServiceImpl implements TradeLifecycleService {
    private static final int DEFAULT_LIMIT = 20;
    private static final int MAX_LIMIT = 100;

    @Autowired
    private TradeLifecycleMapper tradeLifecycleMapper;

    @Override
    public TradeLifecycle createLifecycle(TradeLifecycle lifecycle) {
        if (lifecycle == null) {
            throw new ServiceException("Lifecycle payload is required");
        }
        lifecycle.setTraceId(normalizeRequired(lifecycle.getTraceId(), "traceId"));
        lifecycle.setSymbol(normalizeRequired(lifecycle.getSymbol(), "symbol").toUpperCase(Locale.ROOT));
        lifecycle.setExchangeCode(normalizeRequired(lifecycle.getExchangeCode(), "exchangeCode").toLowerCase(Locale.ROOT));
        lifecycle.setSide(normalizeRequired(lifecycle.getSide(), "side").toLowerCase(Locale.ROOT));
        if (lifecycle.getEntryPrice() == null || lifecycle.getEntryPrice().compareTo(BigDecimal.ZERO) <= 0) {
            throw new ServiceException("entryPrice must be positive");
        }
        if (lifecycle.getEntryTime() == null) {
            throw new ServiceException("entryTime is required");
        }
        if (lifecycle.getMaxFavorablePct() == null) {
            lifecycle.setMaxFavorablePct(BigDecimal.ZERO);
        }
        if (lifecycle.getMaxAdversePct() == null) {
            lifecycle.setMaxAdversePct(BigDecimal.ZERO);
        }
        if (lifecycle.getHoldingMinutes() == null) {
            lifecycle.setHoldingMinutes(0);
        }
        if (lifecycle.getMemoryGenerated() == null) {
            lifecycle.setMemoryGenerated(Boolean.FALSE);
        }
        tradeLifecycleMapper.insertTradeLifecycle(lifecycle);
        return lifecycle;
    }

    @Override
    public TradeLifecycle getByTraceId(String traceId) {
        String normalized = normalizeRequired(traceId, "traceId");
        return tradeLifecycleMapper.selectByTraceId(normalized);
    }

    @Override
    public TradeLifecycle updateLifecycle(String traceId, TradeLifecycle updates) {
        String normalized = normalizeRequired(traceId, "traceId");
        TradeLifecycle existing = tradeLifecycleMapper.selectByTraceId(normalized);
        if (existing == null) {
            throw new ServiceException("Lifecycle not found for traceId: " + normalized);
        }
        if (updates.getExitPrice() != null) {
            existing.setExitPrice(updates.getExitPrice());
        }
        if (updates.getExitTime() != null) {
            existing.setExitTime(updates.getExitTime());
        }
        if (updates.getExitReason() != null) {
            existing.setExitReason(updates.getExitReason());
        }
        if (updates.getRealizedPnlPct() != null) {
            existing.setRealizedPnlPct(updates.getRealizedPnlPct());
        }
        if (updates.getHoldingMinutes() != null) {
            existing.setHoldingMinutes(updates.getHoldingMinutes());
        }
        if (updates.getMemoryGenerated() != null) {
            existing.setMemoryGenerated(updates.getMemoryGenerated());
        }
        if (updates.getLessonText() != null) {
            existing.setLessonText(updates.getLessonText());
        }
        if (updates.getMemoryStatus() != null) {
            existing.setMemoryStatus(updates.getMemoryStatus());
        }
        if (updates.getMemoryReason() != null) {
            existing.setMemoryReason(updates.getMemoryReason());
        }
        if (updates.getAddOperationsJson() != null) {
            existing.setAddOperationsJson(updates.getAddOperationsJson());
        }
        if (updates.getReduceOperationsJson() != null) {
            existing.setReduceOperationsJson(updates.getReduceOperationsJson());
        }
        tradeLifecycleMapper.updateTradeLifecycle(existing);
        return existing;
    }

    @Override
    public List<TradeLifecycle> listClosedLifecycles(Integer limit) {
        int normalizedLimit = limit == null ? DEFAULT_LIMIT : Math.max(1, Math.min(MAX_LIMIT, limit));
        return tradeLifecycleMapper.selectClosedLifecycles(normalizedLimit);
    }

    private String normalizeRequired(String value, String fieldName) {
        String normalized = value == null ? "" : value.trim();
        if (normalized.isEmpty()) {
            throw new ServiceException(fieldName + " is required");
        }
        return normalized;
    }
}
