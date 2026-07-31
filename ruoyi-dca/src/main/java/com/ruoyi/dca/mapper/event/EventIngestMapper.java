package com.ruoyi.dca.mapper.event;

import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.event.MarketEvent;
import com.ruoyi.dca.domain.event.MarketKlineSnapshot;
import com.ruoyi.dca.domain.event.MarketMetricSnapshot;
import com.ruoyi.dca.domain.event.NewsEvent;
import com.ruoyi.dca.domain.event.OnchainEvent;
import com.ruoyi.dca.domain.event.SocialEvent;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface EventIngestMapper {

    int insertEventRaw(EventRaw eventRaw);

    int insertMarketEvent(MarketEvent marketEvent);

    int insertMarketKlineSnapshot(MarketKlineSnapshot snapshot);

    int insertMarketMetricSnapshot(MarketMetricSnapshot snapshot);

    int insertNewsEvent(NewsEvent newsEvent);

    int insertOnchainEvent(OnchainEvent onchainEvent);

    int insertSocialEvent(SocialEvent socialEvent);

    List<EventRaw> selectRecentRawMarketEvents(@Param("symbol") String symbol, @Param("exchangeCode") String exchangeCode, @Param("createdAtMin") String createdAtMin, @Param("limit") int limit);
}
