package com.ruoyi.dca.trade.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.enums.TradeRuntimeMode;
import com.ruoyi.dca.domain.trade.ExchangeAccountBinding;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.domain.trade.TradeSymbolScope;
import com.ruoyi.dca.domain.trade.TradeStrategyVersion;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.trade.impl.TradeStrategyServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeStrategyServiceImplTest {

    @Mock
    private TradeStrategyMapper tradeStrategyMapper;

    @Spy
    private ObjectMapper objectMapper;

    @InjectMocks
    private TradeStrategyServiceImpl tradeStrategyService;

    @Test
    void insertTradeStrategyCreatesInitialVersionRow() {
        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(10L);
        strategy.setStrategyKey("alpha");
        strategy.setStrategyName("Alpha");
        strategy.setRuntimeMode(TradeRuntimeMode.PAPER);
        strategy.setSymbolsJson("[\"BTCUSDT\"]");
        strategy.setExchangesJson("[\"binance\"]");
        strategy.setEnabled(Boolean.TRUE);

        when(tradeStrategyMapper.insertTradeStrategy(strategy)).thenReturn(1);
        when(tradeStrategyMapper.selectMaxVersionNo(10L)).thenReturn(null);

        tradeStrategyService.insertTradeStrategy(strategy);

        ArgumentCaptor<TradeStrategyVersion> captor = ArgumentCaptor.forClass(TradeStrategyVersion.class);
        verify(tradeStrategyMapper).insertTradeStrategyVersion(captor.capture());
        assertThat(captor.getValue().getStrategyId()).isEqualTo(10L);
        assertThat(captor.getValue().getVersionNo()).isEqualTo(1);
        assertThat(captor.getValue().getConfigJson()).contains("\"strategyKey\":\"alpha\"");

        ArgumentCaptor<java.util.List<TradeSymbolScope>> scopeCaptor = ArgumentCaptor.forClass(java.util.List.class);
        verify(tradeStrategyMapper).deleteTradeSymbolScopesByStrategyId(10L);
        verify(tradeStrategyMapper).insertTradeSymbolScopes(scopeCaptor.capture());
        assertThat(scopeCaptor.getValue())
            .extracting(TradeSymbolScope::getSymbol, TradeSymbolScope::getExchangeCode)
            .containsExactlyInAnyOrder(
                org.assertj.core.groups.Tuple.tuple("BTCUSDT", "binance")
            );
    }

    @Test
    void updateTradeStrategyCreatesIncrementedVersionRow() {
        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(11L);
        strategy.setStrategyKey("beta");
        strategy.setStrategyName("Beta");
        strategy.setRuntimeMode(TradeRuntimeMode.SHADOW);
        strategy.setSymbolsJson("[\"ETHUSDT\"]");
        strategy.setExchangesJson("[\"okx\"]");
        strategy.setEnabled(Boolean.FALSE);

        when(tradeStrategyMapper.updateTradeStrategy(strategy)).thenReturn(1);
        when(tradeStrategyMapper.selectMaxVersionNo(11L)).thenReturn(3);

        tradeStrategyService.updateTradeStrategy(strategy);

        ArgumentCaptor<TradeStrategyVersion> captor = ArgumentCaptor.forClass(TradeStrategyVersion.class);
        verify(tradeStrategyMapper).insertTradeStrategyVersion(captor.capture());
        assertThat(captor.getValue().getStrategyId()).isEqualTo(11L);
        assertThat(captor.getValue().getVersionNo()).isEqualTo(4);
        assertThat(captor.getValue().getConfigJson()).contains("\"runtimeMode\":\"SHADOW\"");
    }

    @Test
    void updateTradeStrategyPreservesPreviousCustomConfigAndMergesNewConfigJson() {
        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(19L);
        strategy.setStrategyKey("delta");
        strategy.setStrategyName("Delta");
        strategy.setRuntimeMode(TradeRuntimeMode.LIVE);
        strategy.setSymbolsJson("[\"SOLUSDT\"]");
        strategy.setExchangesJson("[\"binance\"]");
        strategy.setConfigJson("{\"aiModelId\":31,\"riskConfig\":{\"maxPositionRatio\":0.25}}");
        strategy.setEnabled(Boolean.TRUE);

        TradeStrategyVersion previousVersion = new TradeStrategyVersion();
        previousVersion.setStrategyId(19L);
        previousVersion.setVersionNo(2);
        previousVersion.setConfigJson("{\"marketDataConfigId\":52,\"agentConfig\":{\"supervisorPrompt\":\"strict\"}}");

        when(tradeStrategyMapper.updateTradeStrategy(strategy)).thenReturn(1);
        when(tradeStrategyMapper.selectMaxVersionNo(19L)).thenReturn(2);
        when(tradeStrategyMapper.selectLatestTradeStrategyVersion(19L)).thenReturn(previousVersion);

        tradeStrategyService.updateTradeStrategy(strategy);

        ArgumentCaptor<TradeStrategyVersion> captor = ArgumentCaptor.forClass(TradeStrategyVersion.class);
        verify(tradeStrategyMapper).insertTradeStrategyVersion(captor.capture());
        assertThat(captor.getValue().getConfigJson()).contains("\"marketDataConfigId\":52");
        assertThat(captor.getValue().getConfigJson()).contains("\"aiModelId\":31");
        assertThat(captor.getValue().getConfigJson()).contains("\"supervisorPrompt\":\"strict\"");
        assertThat(captor.getValue().getConfigJson()).contains("\"maxPositionRatio\":0.25");
    }

    @Test
    void updateTradeStrategyRefreshesCartesianSymbolScopeRows() {
        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(12L);
        strategy.setStrategyKey("gamma");
        strategy.setStrategyName("Gamma");
        strategy.setRuntimeMode(TradeRuntimeMode.LIVE);
        strategy.setSymbolsJson("[\"BTCUSDT\",\"ETHUSDT\"]");
        strategy.setExchangesJson("[\"binance\",\"okx\"]");
        strategy.setEnabled(Boolean.TRUE);

        when(tradeStrategyMapper.updateTradeStrategy(strategy)).thenReturn(1);
        when(tradeStrategyMapper.selectMaxVersionNo(12L)).thenReturn(1);

        tradeStrategyService.updateTradeStrategy(strategy);

        ArgumentCaptor<java.util.List<TradeSymbolScope>> scopeCaptor = ArgumentCaptor.forClass(java.util.List.class);
        verify(tradeStrategyMapper).deleteTradeSymbolScopesByStrategyId(12L);
        verify(tradeStrategyMapper).insertTradeSymbolScopes(scopeCaptor.capture());
        assertThat(scopeCaptor.getValue())
            .extracting(TradeSymbolScope::getSymbol, TradeSymbolScope::getExchangeCode)
            .containsExactlyInAnyOrder(
                org.assertj.core.groups.Tuple.tuple("BTCUSDT", "binance"),
                org.assertj.core.groups.Tuple.tuple("BTCUSDT", "okx"),
                org.assertj.core.groups.Tuple.tuple("ETHUSDT", "binance"),
                org.assertj.core.groups.Tuple.tuple("ETHUSDT", "okx")
            );
    }

    @Test
    void replaceExchangeAccountBindingsRewritesStrategyIdBeforeInsert() {
        ExchangeAccountBinding first = new ExchangeAccountBinding();
        first.setAccountId(21L);
        first.setExchangeCode("binance");
        first.setEnabled(Boolean.TRUE);
        ExchangeAccountBinding second = new ExchangeAccountBinding();
        second.setAccountId(22L);
        second.setExchangeCode("okx");
        second.setEnabled(Boolean.FALSE);

        tradeStrategyService.replaceExchangeAccountBindings(18L, List.of(first, second));

        verify(tradeStrategyMapper).deleteExchangeAccountBindingsByStrategyId(18L);
        ArgumentCaptor<List<ExchangeAccountBinding>> captor = ArgumentCaptor.forClass(List.class);
        verify(tradeStrategyMapper).insertExchangeAccountBindings(captor.capture());
        assertThat(captor.getValue())
            .extracting(ExchangeAccountBinding::getStrategyId, ExchangeAccountBinding::getAccountId, ExchangeAccountBinding::getExchangeCode, ExchangeAccountBinding::getEnabled)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple(18L, 21L, "binance", Boolean.TRUE),
                org.assertj.core.groups.Tuple.tuple(18L, 22L, "okx", Boolean.FALSE)
            );
    }

    @Test
    void deleteTradeStrategyByIdsCleansBindingRowsBeforeDeletingStrategies() {
        when(tradeStrategyMapper.deleteTradeStrategyByIds(new Long[] {31L, 32L})).thenReturn(2);

        tradeStrategyService.deleteTradeStrategyByIds(new Long[] {31L, 32L});

        verify(tradeStrategyMapper).deleteTradeStrategyVersionsByStrategyIds(new Long[] {31L, 32L});
        verify(tradeStrategyMapper).deleteTradeSymbolScopesByStrategyIds(new Long[] {31L, 32L});
        verify(tradeStrategyMapper).deleteExchangeAccountBindingsByStrategyIds(new Long[] {31L, 32L});
        verify(tradeStrategyMapper).deleteTradeStrategyByIds(new Long[] {31L, 32L});
    }
}
