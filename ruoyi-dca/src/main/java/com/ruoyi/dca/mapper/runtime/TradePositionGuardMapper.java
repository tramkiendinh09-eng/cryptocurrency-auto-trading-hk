package com.ruoyi.dca.mapper.runtime;

import com.ruoyi.dca.domain.trade.TradePositionGuard;
import org.apache.ibatis.annotations.Param;

public interface TradePositionGuardMapper {

    TradePositionGuard selectEffectiveGuard(@Param("strategyId") Long strategyId,
                                           @Param("symbol") String symbol,
                                           @Param("exchangeCode") String exchangeCode);

    String selectCurrentPositionOpenedAt(@Param("exchangeCode") String exchangeCode,
                                         @Param("symbol") String symbol,
                                         @Param("side") String side);
}
