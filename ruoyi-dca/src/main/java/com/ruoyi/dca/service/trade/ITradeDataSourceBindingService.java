package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;

import java.util.List;

public interface ITradeDataSourceBindingService {
    List<TradeDataSourceBinding> selectTradeDataSourceBindingList(TradeDataSourceBinding query);
    int insertTradeDataSourceBinding(TradeDataSourceBinding tradeDataSourceBinding);
    int updateTradeDataSourceBinding(TradeDataSourceBinding tradeDataSourceBinding);
    int deleteTradeDataSourceBindingByIds(Long[] ids);
}
