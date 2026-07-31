package com.ruoyi.dca.service.impl;

import com.ruoyi.dca.domain.MarketDataConfig;
import com.ruoyi.dca.mapper.MarketDataConfigMapper;
import com.ruoyi.dca.service.IMarketDataConfigService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class MarketDataConfigServiceImpl implements IMarketDataConfigService {

    @Autowired
    private MarketDataConfigMapper configMapper;

    @Override
    public MarketDataConfig selectConfigById(Long id) {
        return configMapper.selectMarketDataConfigById(id);
    }

    @Override
    public List<MarketDataConfig> selectConfigList(MarketDataConfig marketDataConfig) {
        return configMapper.selectMarketDataConfigList(marketDataConfig);
    }

    @Override
    public List<MarketDataConfig> selectEnabledConfigs() {
        return configMapper.selectEnabledConfigs();
    }

    @Override
    public MarketDataConfig selectConfigBySymbol(String symbol) {
        return configMapper.selectConfigBySymbol(symbol);
    }
}
