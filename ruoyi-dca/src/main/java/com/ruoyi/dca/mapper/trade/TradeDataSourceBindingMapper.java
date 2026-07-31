package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface TradeDataSourceBindingMapper {
    List<TradeDataSourceBinding> selectTradeDataSourceBindingList(TradeDataSourceBinding query);
    TradeDataSourceBinding selectTradeDataSourceBindingById(@Param("id") Long id);
    int insertTradeDataSourceBinding(TradeDataSourceBinding tradeDataSourceBinding);
    int updateTradeDataSourceBinding(TradeDataSourceBinding tradeDataSourceBinding);
    int deleteTradeDataSourceBindingByIds(@Param("ids") Long[] ids);
}
