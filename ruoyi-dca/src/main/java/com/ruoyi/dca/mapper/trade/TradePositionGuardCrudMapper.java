package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.TradePositionGuard;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface TradePositionGuardCrudMapper {
    List<TradePositionGuard> selectTradePositionGuardList(TradePositionGuard query);
    TradePositionGuard selectTradePositionGuardById(@Param("id") Long id);
    int insertTradePositionGuard(TradePositionGuard tradePositionGuard);
    int updateTradePositionGuard(TradePositionGuard tradePositionGuard);
    int deleteTradePositionGuardByIds(@Param("ids") Long[] ids);
}
