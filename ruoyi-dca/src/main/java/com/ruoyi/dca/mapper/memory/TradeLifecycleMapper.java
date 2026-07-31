package com.ruoyi.dca.mapper.memory;

import com.ruoyi.dca.domain.memory.TradeLifecycle;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface TradeLifecycleMapper {
    int insertTradeLifecycle(TradeLifecycle lifecycle);

    TradeLifecycle selectByTraceId(@Param("traceId") String traceId);

    int updateTradeLifecycle(TradeLifecycle lifecycle);

    int updateExitInfo(@Param("traceId") String traceId,
                       @Param("exitPrice") java.math.BigDecimal exitPrice,
                       @Param("exitTime") java.util.Date exitTime,
                       @Param("exitReason") String exitReason,
                       @Param("realizedPnlPct") java.math.BigDecimal realizedPnlPct,
                       @Param("holdingMinutes") Integer holdingMinutes);

    int updateMemoryGenerated(@Param("traceId") String traceId,
                              @Param("memoryGenerated") Boolean memoryGenerated,
                              @Param("lessonText") String lessonText,
                              @Param("memoryStatus") String memoryStatus,
                              @Param("memoryReason") String memoryReason);

    List<TradeLifecycle> selectClosedLifecycles(@Param("limit") Integer limit);
}
