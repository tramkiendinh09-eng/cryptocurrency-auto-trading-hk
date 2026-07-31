package com.ruoyi.dca.trade.service;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.trade.TradePositionGuard;
import com.ruoyi.dca.domain.trade.TradeStrategy;
import com.ruoyi.dca.mapper.trade.TradePositionGuardCrudMapper;
import com.ruoyi.dca.mapper.trade.TradeStrategyMapper;
import com.ruoyi.dca.service.trade.impl.TradePositionGuardServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradePositionGuardServiceImplTest {

    @Mock
    private TradePositionGuardCrudMapper tradePositionGuardMapper;

    @Mock
    private TradeStrategyMapper tradeStrategyMapper;

    @InjectMocks
    private TradePositionGuardServiceImpl tradePositionGuardService;

    @Test
    void insertTradePositionGuardNormalizesSymbolScopeAndDefaults() {
        TradePositionGuard guard = new TradePositionGuard();
        guard.setGuardName(" BTC Guard ");
        guard.setScopeType(" symbol ");
        guard.setStrategyId(7L);
        guard.setSymbol(" btcusdt ");
        guard.setExchangeCode(" binance ");
        guard.setStopLossPct(new BigDecimal("0.03"));
        guard.setTakeProfitPct(new BigDecimal("0.06"));
        guard.setMaxHoldingMinutes(180);

        mockStrategy(7L);
        when(tradePositionGuardMapper.insertTradePositionGuard(any(TradePositionGuard.class))).thenReturn(1);

        tradePositionGuardService.insertTradePositionGuard(guard);

        ArgumentCaptor<TradePositionGuard> captor = ArgumentCaptor.forClass(TradePositionGuard.class);
        verify(tradePositionGuardMapper).insertTradePositionGuard(captor.capture());
        TradePositionGuard saved = captor.getValue();
        assertThat(saved.getGuardName()).isEqualTo("BTC Guard");
        assertThat(saved.getScopeType()).isEqualTo("SYMBOL");
        assertThat(saved.getStrategyId()).isEqualTo(7L);
        assertThat(saved.getSymbol()).isEqualTo("BTCUSDT");
        assertThat(saved.getExchangeCode()).isEqualTo("BINANCE");
        assertThat(saved.getEnabled()).isTrue();
        assertThat(saved.getPriority()).isZero();
    }

    @Test
    void insertTradePositionGuardRejectsUnsupportedScopeAndExchange() {
        TradePositionGuard guard = new TradePositionGuard();
        guard.setGuardName("Bad Guard");
        guard.setScopeType("invalid");
        guard.setSymbol("BTCUSDT");
        guard.setExchangeCode("BYBIT");

        assertThatThrownBy(() -> tradePositionGuardService.insertTradePositionGuard(guard))
            .isInstanceOf(ServiceException.class);
    }

    @Test
    void insertTradePositionGuardRequiresStrategyWhenScopeIsStrategy() {
        TradePositionGuard guard = new TradePositionGuard();
        guard.setGuardName("Strategy Guard");
        guard.setScopeType("STRATEGY");
        guard.setStopLossPct(new BigDecimal("0.03"));

        assertThatThrownBy(() -> tradePositionGuardService.insertTradePositionGuard(guard))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("strategy");
    }

    @Test
    void updateTradePositionGuardPreservesExistingScopeFieldsWhenPayloadIsPartial() {
        TradePositionGuard existing = new TradePositionGuard();
        existing.setId(8L);
        existing.setGuardName("Existing Guard");
        existing.setScopeType("STRATEGY");
        existing.setStrategyId(7L);
        existing.setStopLossPct(new BigDecimal("0.03"));
        existing.setTakeProfitPct(new BigDecimal("0.05"));
        existing.setMaxHoldingMinutes(240);
        existing.setEnabled(Boolean.TRUE);
        existing.setPriority(5);

        TradePositionGuard patch = new TradePositionGuard();
        patch.setId(8L);
        patch.setGuardName("Updated Guard");
        patch.setTakeProfitPct(new BigDecimal("0.08"));

        when(tradePositionGuardMapper.selectTradePositionGuardById(8L)).thenReturn(existing);
        when(tradePositionGuardMapper.selectTradePositionGuardList(any(TradePositionGuard.class))).thenReturn(List.of(existing));
        mockStrategy(7L);
        when(tradePositionGuardMapper.updateTradePositionGuard(any(TradePositionGuard.class))).thenReturn(1);

        tradePositionGuardService.updateTradePositionGuard(patch);

        ArgumentCaptor<TradePositionGuard> captor = ArgumentCaptor.forClass(TradePositionGuard.class);
        verify(tradePositionGuardMapper).updateTradePositionGuard(captor.capture());
        TradePositionGuard saved = captor.getValue();
        assertThat(saved.getScopeType()).isEqualTo("STRATEGY");
        assertThat(saved.getStrategyId()).isEqualTo(7L);
        assertThat(saved.getStopLossPct()).isEqualByComparingTo("0.03");
        assertThat(saved.getTakeProfitPct()).isEqualByComparingTo("0.08");
        assertThat(saved.getPriority()).isEqualTo(5);
    }

    @Test
    void insertTradePositionGuardRejectsDuplicateEnabledScope() {
        TradePositionGuard guard = new TradePositionGuard();
        guard.setGuardName("BTC Guard");
        guard.setScopeType("SYMBOL");
        guard.setStrategyId(7L);
        guard.setSymbol("BTCUSDT");
        guard.setExchangeCode("BINANCE");
        guard.setStopLossPct(new BigDecimal("0.03"));
        guard.setEnabled(Boolean.TRUE);

        TradePositionGuard existing = new TradePositionGuard();
        existing.setId(99L);
        existing.setScopeType("SYMBOL");
        existing.setStrategyId(7L);
        existing.setSymbol("BTCUSDT");
        existing.setExchangeCode("BINANCE");
        existing.setStopLossPct(new BigDecimal("0.02"));
        existing.setEnabled(Boolean.TRUE);

        mockStrategy(7L);
        when(tradePositionGuardMapper.selectTradePositionGuardList(any(TradePositionGuard.class))).thenReturn(List.of(existing));

        assertThatThrownBy(() -> tradePositionGuardService.insertTradePositionGuard(guard))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("Duplicate");
    }

    private void mockStrategy(Long strategyId) {
        TradeStrategy strategy = new TradeStrategy();
        strategy.setId(strategyId);
        when(tradeStrategyMapper.selectTradeStrategyById(strategyId)).thenReturn(strategy);
    }
}
