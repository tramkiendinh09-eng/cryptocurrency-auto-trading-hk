package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.TradePositionGuard;

import java.util.List;

public interface ITradePositionGuardService {
    List<TradePositionGuard> selectTradePositionGuardList(TradePositionGuard query);
    int insertTradePositionGuard(TradePositionGuard tradePositionGuard);
    int updateTradePositionGuard(TradePositionGuard tradePositionGuard);
    int deleteTradePositionGuardByIds(Long[] ids);
}
