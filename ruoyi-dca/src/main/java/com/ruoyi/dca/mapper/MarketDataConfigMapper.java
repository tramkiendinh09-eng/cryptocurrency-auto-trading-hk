package com.ruoyi.dca.mapper;

import com.ruoyi.dca.domain.MarketDataConfig;

import java.util.List;

public interface MarketDataConfigMapper {

    MarketDataConfig selectMarketDataConfigById(Long id);

    List<MarketDataConfig> selectMarketDataConfigList(MarketDataConfig marketDataConfig);

    List<MarketDataConfig> selectEnabledConfigs();

    MarketDataConfig selectConfigBySymbol(String symbol);
}
