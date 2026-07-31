package com.ruoyi.dca.service;

import com.ruoyi.dca.domain.MarketDataConfig;

import java.util.List;

public interface IMarketDataConfigService {

    MarketDataConfig selectConfigById(Long id);

    List<MarketDataConfig> selectConfigList(MarketDataConfig marketDataConfig);

    List<MarketDataConfig> selectEnabledConfigs();

    MarketDataConfig selectConfigBySymbol(String symbol);
}
