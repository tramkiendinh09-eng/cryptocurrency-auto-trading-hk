package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.TradePromptBinding;

import java.util.List;

public interface ITradePromptBindingService {
    List<TradePromptBinding> selectTradePromptBindingList(TradePromptBinding query);
    int insertTradePromptBinding(TradePromptBinding tradePromptBinding);
    int updateTradePromptBinding(TradePromptBinding tradePromptBinding);
    int deleteTradePromptBindingByIds(Long[] ids);
}
