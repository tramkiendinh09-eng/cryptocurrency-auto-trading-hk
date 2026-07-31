package com.ruoyi.dca.trade.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.domain.trade.TradeDataSourceBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.mapper.trade.TradeDataSourceBindingMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.IMarketApiConfigService;
import com.ruoyi.dca.service.trade.impl.TradeDataSourceBindingServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeDataSourceBindingServiceImplTest {

    @Mock
    private TradeDataSourceBindingMapper tradeDataSourceBindingMapper;

    @Mock
    private TradeStrategyMapper tradeStrategyMapper;

    @Mock
    private IMarketApiConfigService marketApiConfigService;

    @Spy
    private ObjectMapper objectMapper;

    @InjectMocks
    private TradeDataSourceBindingServiceImpl tradeDataSourceBindingService;

    @Test
    void insertTradeDataSourceBindingNormalizesScopesAgainstSpecsWhitelist() {
        TradeDataSourceBinding binding = new TradeDataSourceBinding();
        binding.setBindingName(" Primary News Feed ");
        binding.setStrategyId(9L);
        binding.setSourceId(21L);
        binding.setEventType(" News ");
        binding.setSymbolScopeJson("[\" btcusdt \",\"ETHUSDT\"]");
        binding.setExchangeScopeJson("[\" binance \",\"OKX\"]");
        binding.setModeScopeJson("[\" shadow \",\"LIVE\"]");

        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(9L);
        when(tradeStrategyMapper.selectTradeStrategyById(9L)).thenReturn(strategy);

        MarketApiConfig source = new MarketApiConfig();
        source.setId(21L);
        source.setConfigName("Binance News");
        source.setEnabled("1");
        when(marketApiConfigService.selectApiConfigById(21L)).thenReturn(source);
        when(tradeDataSourceBindingMapper.insertTradeDataSourceBinding(any(TradeDataSourceBinding.class))).thenReturn(1);

        tradeDataSourceBindingService.insertTradeDataSourceBinding(binding);

        ArgumentCaptor<TradeDataSourceBinding> captor = ArgumentCaptor.forClass(TradeDataSourceBinding.class);
        verify(tradeDataSourceBindingMapper).insertTradeDataSourceBinding(captor.capture());
        assertThat(captor.getValue().getBindingName()).isEqualTo("Primary News Feed");
        assertThat(captor.getValue().getEventType()).isEqualTo("news");
        assertThat(captor.getValue().getSymbolScopeJson()).isEqualTo("[\"BTCUSDT\",\"ETHUSDT\"]");
        assertThat(captor.getValue().getExchangeScopeJson()).isEqualTo("[\"BINANCE\",\"OKX\"]");
        assertThat(captor.getValue().getModeScopeJson()).isEqualTo("[\"shadow\",\"live\"]");
        assertThat(captor.getValue().getEnabled()).isTrue();
    }

    @Test
    void insertTradeDataSourceBindingRejectsSymbolsOutsideV1Whitelist() {
        TradeDataSourceBinding binding = new TradeDataSourceBinding();
        binding.setBindingName("Alt Feed");
        binding.setSourceId(21L);
        binding.setEventType("news");
        binding.setSymbolScopeJson("[\"BTCUSDT\",\"XRPUSDT\"]");
        binding.setExchangeScopeJson("[\"BINANCE\"]");
        binding.setModeScopeJson("[\"paper\"]");

        assertThatThrownBy(() -> tradeDataSourceBindingService.insertTradeDataSourceBinding(binding))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("XRPUSDT");
    }

    @Test
    void insertTradeDataSourceBindingRejectsMissingSourceConfig() {
        TradeDataSourceBinding binding = new TradeDataSourceBinding();
        binding.setBindingName("Market Ticks");
        binding.setSourceId(404L);
        binding.setEventType("market_tick");

        when(marketApiConfigService.selectApiConfigById(404L)).thenReturn(null);

        assertThatThrownBy(() -> tradeDataSourceBindingService.insertTradeDataSourceBinding(binding))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("source");
    }
}
