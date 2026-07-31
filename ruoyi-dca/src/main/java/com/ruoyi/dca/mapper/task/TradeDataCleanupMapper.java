package com.ruoyi.dca.mapper.task;

import org.apache.ibatis.annotations.Param;

public interface TradeDataCleanupMapper {

    int deleteSignalScoresBefore(@Param("cutoffTime") String cutoffTime);

    int deleteSignalEventsBefore(@Param("cutoffTime") String cutoffTime);

    int deleteExpiredSignalWindowStatesBefore(@Param("cutoffTime") String cutoffTime);

    int deleteMarketEventsBefore(@Param("cutoffTime") String cutoffTime);

    int deleteMarketKlineSnapshotsBefore(@Param("cutoffTime") String cutoffTime);

    int deleteMarketMetricSnapshotsBefore(@Param("cutoffTime") String cutoffTime);

    int deleteNewsEventsBefore(@Param("cutoffTime") String cutoffTime);

    int deleteOnchainEventsBefore(@Param("cutoffTime") String cutoffTime);

    int deleteSocialEventsBefore(@Param("cutoffTime") String cutoffTime);

    int deleteEventRawsBefore(@Param("cutoffTime") String cutoffTime);
}
