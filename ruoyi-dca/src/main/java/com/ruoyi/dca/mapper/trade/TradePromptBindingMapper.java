package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.TradePromptBinding;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface TradePromptBindingMapper {
    List<TradePromptBinding> selectTradePromptBindingList(TradePromptBinding query);
    TradePromptBinding selectTradePromptBindingById(@Param("id") Long id);
    int insertTradePromptBinding(TradePromptBinding tradePromptBinding);
    int updateTradePromptBinding(TradePromptBinding tradePromptBinding);
    int deleteTradePromptBindingByIds(@Param("ids") Long[] ids);
}
