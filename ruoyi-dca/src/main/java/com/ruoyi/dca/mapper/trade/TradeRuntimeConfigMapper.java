package com.ruoyi.dca.mapper.trade;

import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;

public interface TradeRuntimeConfigMapper {

    TradeRuntimeConfig selectCurrentConfig();

    int insertTradeRuntimeConfig(TradeRuntimeConfig tradeRuntimeConfig);

    int updateTradeRuntimeConfig(TradeRuntimeConfig tradeRuntimeConfig);
}
