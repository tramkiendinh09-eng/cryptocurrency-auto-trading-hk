package com.ruoyi.dca.service.trade;

import com.ruoyi.dca.domain.trade.TradeRuntimeConfig;
import com.ruoyi.dca.domain.trade.TradeRuntimeBootstrap;

import java.util.List;

public interface ITradeRuntimeConfigService {

    TradeRuntimeConfig getCurrentConfig();

    TradeRuntimeBootstrap getBootstrapConfig(String symbol, String exchange);

    List<TradeRuntimeBootstrap> listBootstrapConfigs();

    int saveCurrentConfig(TradeRuntimeConfig tradeRuntimeConfig);
}
