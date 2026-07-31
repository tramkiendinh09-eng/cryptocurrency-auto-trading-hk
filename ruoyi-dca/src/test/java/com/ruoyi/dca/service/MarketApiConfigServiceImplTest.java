package com.ruoyi.dca.service;

import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.dca.domain.MarketApiConfig;
import com.ruoyi.dca.mapper.MarketApiConfigMapper;
import com.ruoyi.dca.mapper.trade.TradeDataSourceHealthLogMapper;
import com.ruoyi.dca.service.impl.MarketApiConfigServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpMethod;
import org.springframework.web.client.RestTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class MarketApiConfigServiceImplTest {

    @Mock
    private MarketApiConfigMapper apiConfigMapper;

    @Mock
    private RestTemplate restTemplate;

    @Mock
    private TradeDataSourceHealthLogMapper tradeDataSourceHealthLogMapper;

    @InjectMocks
    private MarketApiConfigServiceImpl marketApiConfigService;

    @Test
    void insertApiConfigRejectsBinanceWebsocketPathOutsideOfficialOptions() {
        MarketApiConfig config = websocketConfig();
        config.setWsPath("/socket");

        assertThatThrownBy(() -> marketApiConfigService.insertApiConfig(config))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("/ws")
            .hasMessageContaining("/stream");
    }

    @Test
    void insertApiConfigRejectsBinanceCombinedStreamOnRawPath() {
        MarketApiConfig config = websocketConfig();
        config.setWsCombinedEnabled(Boolean.TRUE);
        config.setWsPath("/ws");

        assertThatThrownBy(() -> marketApiConfigService.insertApiConfig(config))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("/stream");
    }

    @Test
    void insertApiConfigRejectsBinanceWebsocketWithoutLowercaseSymbols() {
        MarketApiConfig config = websocketConfig();
        config.setWsSymbolLowercase(Boolean.FALSE);

        assertThatThrownBy(() -> marketApiConfigService.insertApiConfig(config))
            .isInstanceOf(ServiceException.class)
            .hasMessageContaining("lowercase");
    }

    @Test
    void insertApiConfigNormalizesBinanceWebsocketDefaultsBeforePersist() {
        MarketApiConfig config = websocketConfig();
        config.setVendorCode(" binance ");
        config.setTransportType(" websocket ");
        config.setMarketScope(" spot ");
        config.setWsPingIntervalSeconds(null);
        config.setWsPongTimeoutSeconds(null);
        config.setWsConnectionTtlHours(null);
        config.setWsMaxStreamsPerConnection(null);
        config.setWsControlMessagesPerSecond(null);
        when(apiConfigMapper.insertMarketApiConfig(any(MarketApiConfig.class))).thenReturn(1);

        marketApiConfigService.insertApiConfig(config);

        ArgumentCaptor<MarketApiConfig> captor = ArgumentCaptor.forClass(MarketApiConfig.class);
        verify(apiConfigMapper).insertMarketApiConfig(captor.capture());
        assertThat(captor.getValue().getVendorCode()).isEqualTo("BINANCE");
        assertThat(captor.getValue().getTransportType()).isEqualTo("WEBSOCKET");
        assertThat(captor.getValue().getMarketScope()).isEqualTo("SPOT");
        assertThat(captor.getValue().getVersionNo()).isEqualTo(1);
        assertThat(captor.getValue().getWsPingIntervalSeconds()).isEqualTo(20);
        assertThat(captor.getValue().getWsPongTimeoutSeconds()).isEqualTo(60);
        assertThat(captor.getValue().getWsConnectionTtlHours()).isEqualTo(24);
        assertThat(captor.getValue().getWsMaxStreamsPerConnection()).isEqualTo(1024);
        assertThat(captor.getValue().getWsControlMessagesPerSecond()).isEqualTo(5);
    }

    @Test
    void updateApiConfigIncrementsPersistedVersionNumber() {
        MarketApiConfig existing = websocketConfig();
        existing.setId(101L);
        existing.setVersionNo(3);

        MarketApiConfig update = websocketConfig();
        update.setId(101L);
        update.setVersionNo(1);

        when(apiConfigMapper.selectMarketApiConfigById(101L)).thenReturn(existing);
        when(apiConfigMapper.updateMarketApiConfig(any(MarketApiConfig.class))).thenReturn(1);

        marketApiConfigService.updateApiConfig(update);

        ArgumentCaptor<MarketApiConfig> captor = ArgumentCaptor.forClass(MarketApiConfig.class);
        verify(apiConfigMapper).updateMarketApiConfig(captor.capture());
        assertThat(captor.getValue().getVersionNo()).isEqualTo(4);
    }

    @Test
    void testApiConnectionWritesHealthyLogForValidatedWebsocketConfig() {
        MarketApiConfig config = websocketConfig();
        config.setId(91L);
        when(apiConfigMapper.selectMarketApiConfigById(91L)).thenReturn(config);

        marketApiConfigService.testApiConnection(91L);

        ArgumentCaptor<com.ruoyi.dca.domain.trade.TradeDataSourceHealthLog> captor =
            ArgumentCaptor.forClass(com.ruoyi.dca.domain.trade.TradeDataSourceHealthLog.class);
        verify(tradeDataSourceHealthLogMapper).insertTradeDataSourceHealthLog(captor.capture());
        assertThat(captor.getValue().getSourceId()).isEqualTo(91L);
        assertThat(captor.getValue().getCheckType()).isEqualTo("manual_test");
        assertThat(captor.getValue().getStatus()).isEqualTo("healthy");
        assertThat(captor.getValue().getResponseExcerpt()).contains("validation passed");
        assertThat(captor.getValue().getErrorMessage()).isNull();
    }

    @Test
    void testApiConnectionWritesFailureLogWhenRestProbeThrows() {
        MarketApiConfig config = new MarketApiConfig();
        config.setId(92L);
        config.setConfigName("REST ticker");
        config.setDataCategory("PRICE");
        config.setApiName("REST_TICKER");
        config.setTransportType("REST");
        config.setApiUrl("https://feeds.internal/ticker");
        config.setHttpMethod("GET");
        when(apiConfigMapper.selectMarketApiConfigById(92L)).thenReturn(config);
        when(restTemplate.exchange(eq("https://feeds.internal/ticker"), eq(HttpMethod.GET), any(), eq(String.class)))
            .thenThrow(new IllegalStateException("connect timeout"));

        marketApiConfigService.testApiConnection(92L);

        ArgumentCaptor<com.ruoyi.dca.domain.trade.TradeDataSourceHealthLog> captor =
            ArgumentCaptor.forClass(com.ruoyi.dca.domain.trade.TradeDataSourceHealthLog.class);
        verify(tradeDataSourceHealthLogMapper).insertTradeDataSourceHealthLog(captor.capture());
        assertThat(captor.getValue().getSourceId()).isEqualTo(92L);
        assertThat(captor.getValue().getStatus()).isEqualTo("failed");
        assertThat(captor.getValue().getErrorMessage()).contains("connect timeout");
    }

    private static MarketApiConfig websocketConfig() {
        MarketApiConfig config = new MarketApiConfig();
        config.setConfigName("Binance Spot Ticker");
        config.setDataCategory("PRICE");
        config.setDataSubType("TICKER");
        config.setApiName("BINANCE_SPOT_TICKER_WS");
        config.setTransportType("WEBSOCKET");
        config.setVendorCode("BINANCE");
        config.setMarketScope("SPOT");
        config.setWsBaseUrl("wss://stream.binance.com:9443");
        config.setWsPath("/ws");
        config.setWsStreamNameTemplate("{symbol_lower}@ticker");
        config.setWsCombinedEnabled(Boolean.FALSE);
        config.setWsSymbolLowercase(Boolean.TRUE);
        config.setResponsePath("$");
        config.setFieldMapping("{\"symbol\":\"s\",\"price\":\"c\"}");
        config.setTimeout(10);
        config.setEnabled("1");
        return config;
    }
}
