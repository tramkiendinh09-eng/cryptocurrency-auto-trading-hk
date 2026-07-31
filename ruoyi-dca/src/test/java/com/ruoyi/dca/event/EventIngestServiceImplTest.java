package com.ruoyi.dca.event;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.event.MarketEvent;
import com.ruoyi.dca.domain.event.MarketKlineSnapshot;
import com.ruoyi.dca.domain.event.MarketMetricSnapshot;
import com.ruoyi.dca.domain.event.NewsEvent;
import com.ruoyi.dca.domain.event.OnchainEvent;
import com.ruoyi.dca.domain.event.SocialEvent;
import com.ruoyi.dca.mapper.event.EventIngestMapper;
import com.ruoyi.dca.service.event.impl.EventIngestServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class EventIngestServiceImplTest {

    @Mock
    private EventIngestMapper eventIngestMapper;

    @Spy
    private ObjectMapper objectMapper;

    @InjectMocks
    private EventIngestServiceImpl eventIngestService;

    @Test
    void listRecentMarketHistoryParsesRawMarketPayloads() {
        EventRaw older = new EventRaw();
        older.setTraceId("trace-db-1");
        older.setEventType("market_tick");
        older.setSymbol("BTCUSDT");
        older.setExchangeCode("okx");
        older.setCreatedAt("2026-04-29T04:00:00Z");
        older.setPayloadJson("{\"price\":76800.0,\"volume\":6119303.89,\"quote_volume\":61193.0389}");
        EventRaw newer = new EventRaw();
        newer.setTraceId("trace-db-2");
        newer.setEventType("market_tick");
        newer.setSymbol("BTCUSDT");
        newer.setExchangeCode("okx");
        newer.setCreatedAt("2026-04-29T04:01:00Z");
        newer.setPayloadJson("{\"price\":76810.0,\"volume\":6119400.0,\"quoteVolume\":61194.0,\"markPrice\":76809.5}");
        when(eventIngestMapper.selectRecentRawMarketEvents(eq("BTCUSDT"), eq("okx"), anyString(), eq(60))).thenReturn(List.of(newer, older));

        List<Map<String, Object>> history = eventIngestService.listRecentMarketHistory("btcusdt", "OKX", 60, 300);

        assertThat(history).hasSize(2);
        assertThat(history.get(0).get("price")).isEqualTo(76800.0d);
        assertThat(history.get(0).get("quote_volume")).isEqualTo(61193.0389d);
        assertThat(history.get(1).get("price")).isEqualTo(76810.0d);
        assertThat(history.get(1).get("mark_price")).isEqualTo(76809.5d);
    }

    @Test
    void listRecentMarketHistoryParsesMetricPayloadAliases() {
        EventRaw metric = new EventRaw();
        metric.setTraceId("trace-metric-history");
        metric.setEventType("market_metric");
        metric.setSymbol("BTCUSDT");
        metric.setExchangeCode("okx");
        metric.setCreatedAt("2026-04-29 18:01:00");
        metric.setPayloadJson("{\"latest_price\":77100.5,\"volume_24h\":8888,\"quote_volume_24h\":684000000,\"mark_price\":77102.0,\"funding_rate\":0.0001,\"open_interest\":123456.7,\"liquidation_notional_60m\":360000}");
        when(eventIngestMapper.selectRecentRawMarketEvents(eq("BTCUSDT"), eq("okx"), anyString(), eq(60))).thenReturn(List.of(metric));

        List<Map<String, Object>> history = eventIngestService.listRecentMarketHistory("btcusdt", "OKX", 60, 300);

        assertThat(history).hasSize(1);
        assertThat(history.get(0).get("price")).isEqualTo(77100.5d);
        assertThat(history.get(0).get("quote_volume")).isEqualTo(684000000d);
        assertThat(history.get(0).get("liquidation_notional_60m")).isEqualTo(360000d);
    }

    @Test
    void ingestProjectsMarketPayloadIntoTypedMarketEvent() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-market-1");
        eventRaw.setEventType("market_tick");
        eventRaw.setSymbol("BTCUSDT");
        eventRaw.setExchangeCode("binance");
        eventRaw.setPayloadJson("{\"price\":65000.5,\"volume\":12.4}");

        eventIngestService.ingest(eventRaw);

        ArgumentCaptor<MarketEvent> captor = ArgumentCaptor.forClass(MarketEvent.class);
        verify(eventIngestMapper).insertMarketEvent(captor.capture());
        assertThat(captor.getValue().getTraceId()).isEqualTo("trace-market-1");
        assertThat(captor.getValue().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(captor.getValue().getExchangeCode()).isEqualTo("binance");
        assertThat(captor.getValue().getPrice().toPlainString()).isEqualTo("65000.5");
        assertThat(captor.getValue().getVolume().toPlainString()).isEqualTo("12.4");
    }

    @Test
    void ingestProjectsMarketKlinePayloadIntoTypedSnapshot() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-kline-1");
        eventRaw.setEventType("market_kline");
        eventRaw.setSymbol("BTCUSDT");
        eventRaw.setExchangeCode("okx");
        eventRaw.setPayloadJson("{\"interval\":\"1m\",\"open_time\":\"2026-04-29 18:00:00\",\"open\":77000.1,\"high\":77120.0,\"low\":76980.0,\"close\":77100.5,\"volume\":12.5,\"quote_volume\":963756.25}");

        eventIngestService.ingest(eventRaw);

        ArgumentCaptor<MarketKlineSnapshot> captor = ArgumentCaptor.forClass(MarketKlineSnapshot.class);
        verify(eventIngestMapper).insertMarketKlineSnapshot(captor.capture());
        assertThat(captor.getValue().getTraceId()).isEqualTo("trace-kline-1");
        assertThat(captor.getValue().getExchangeCode()).isEqualTo("okx");
        assertThat(captor.getValue().getIntervalCode()).isEqualTo("1m");
        assertThat(captor.getValue().getClosePrice().toPlainString()).isEqualTo("77100.5");
        assertThat(captor.getValue().getQuoteVolume().toPlainString()).isEqualTo("963756.25");
    }

    @Test
    void ingestProjectsMarketMetricPayloadIntoTypedSnapshot() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-metric-1");
        eventRaw.setEventType("market_metric");
        eventRaw.setSymbol("BTCUSDT");
        eventRaw.setExchangeCode("okx");
        eventRaw.setCreatedAt("2026-04-29 18:01:00");
        eventRaw.setPayloadJson("{\"latest_price\":77100.5,\"mark_price\":77102.0,\"mark_price_deviation_pct\":0.0019,\"funding_rate\":0.0001,\"open_interest\":123456.7,\"volume_24h\":8888,\"quote_volume_24h\":684000000,\"liquidation_notional_15m\":250000,\"liquidation_notional_60m\":360000,\"liquidation_notional_240m\":500000,\"largest_liquidation_notional_usd\":200000,\"largest_liquidation_side\":\"long\"}");

        eventIngestService.ingest(eventRaw);

        ArgumentCaptor<MarketMetricSnapshot> captor = ArgumentCaptor.forClass(MarketMetricSnapshot.class);
        verify(eventIngestMapper).insertMarketMetricSnapshot(captor.capture());
        assertThat(captor.getValue().getTraceId()).isEqualTo("trace-metric-1");
        assertThat(captor.getValue().getObservedAt()).isEqualTo("2026-04-29 18:01:00");
        assertThat(captor.getValue().getLatestPrice().toPlainString()).isEqualTo("77100.5");
        assertThat(captor.getValue().getLiquidationNotional60m().toPlainString()).isEqualTo("360000");
        assertThat(captor.getValue().getLargestLiquidationSide()).isEqualTo("long");
    }

    @Test
    void ingestNormalizesIsoMarketSnapshotTimesToDatabaseTimezone() {
        EventRaw metricRaw = new EventRaw();
        metricRaw.setTraceId("trace-metric-timezone");
        metricRaw.setEventType("market_metric");
        metricRaw.setSymbol("ETHUSDT");
        metricRaw.setExchangeCode("okx");
        metricRaw.setCreatedAt("2026-05-08T03:37:58Z");
        metricRaw.setPayloadJson("{\"observed_at\":\"2026-05-08T03:37:56.375971+00:00\",\"latest_price\":2279.34}");

        eventIngestService.ingest(metricRaw);

        ArgumentCaptor<MarketMetricSnapshot> metricCaptor = ArgumentCaptor.forClass(MarketMetricSnapshot.class);
        verify(eventIngestMapper).insertMarketMetricSnapshot(metricCaptor.capture());
        assertThat(metricCaptor.getValue().getObservedAt()).isEqualTo("2026-05-08 11:37:56");

        EventRaw klineRaw = new EventRaw();
        klineRaw.setTraceId("trace-kline-timezone");
        klineRaw.setEventType("market_kline");
        klineRaw.setSymbol("ETHUSDT");
        klineRaw.setExchangeCode("okx");
        klineRaw.setPayloadJson("{\"interval\":\"1m\",\"open_time\":\"2026-05-08T03:37:00Z\",\"close_time\":\"2026-05-08T03:37:59+00:00\",\"close\":2279.34}");

        eventIngestService.ingest(klineRaw);

        ArgumentCaptor<MarketKlineSnapshot> klineCaptor = ArgumentCaptor.forClass(MarketKlineSnapshot.class);
        verify(eventIngestMapper).insertMarketKlineSnapshot(klineCaptor.capture());
        assertThat(klineCaptor.getValue().getOpenTime()).isEqualTo("2026-05-08 11:37:00");
        assertThat(klineCaptor.getValue().getCloseTime()).isEqualTo("2026-05-08 11:37:59");
    }

    @Test
    void ingestProjectsNewsPayloadIntoTypedNewsEvent() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-news-1");
        eventRaw.setEventType("news");
        eventRaw.setSymbol("BTCUSDT");
        eventRaw.setExchangeCode("external");
        eventRaw.setPayloadJson("{\"source\":\"rss\",\"headline\":\"ETF inflow accelerates\"}");

        eventIngestService.ingest(eventRaw);

        ArgumentCaptor<NewsEvent> captor = ArgumentCaptor.forClass(NewsEvent.class);
        verify(eventIngestMapper).insertNewsEvent(captor.capture());
        assertThat(captor.getValue().getTraceId()).isEqualTo("trace-news-1");
        assertThat(captor.getValue().getSymbol()).isEqualTo("BTCUSDT");
        assertThat(captor.getValue().getSource()).isEqualTo("rss");
        assertThat(captor.getValue().getHeadline()).isEqualTo("ETF inflow accelerates");
    }

    @Test
    void ingestProjectsOnchainPayloadIntoTypedOnchainEvent() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-onchain-1");
        eventRaw.setEventType("onchain");
        eventRaw.setSymbol("ETHUSDT");
        eventRaw.setExchangeCode("external");
        eventRaw.setPayloadJson("{\"wallet\":\"0xabc\",\"flow\":\"exchange_outflow\"}");

        eventIngestService.ingest(eventRaw);

        ArgumentCaptor<OnchainEvent> captor = ArgumentCaptor.forClass(OnchainEvent.class);
        verify(eventIngestMapper).insertOnchainEvent(captor.capture());
        assertThat(captor.getValue().getTraceId()).isEqualTo("trace-onchain-1");
        assertThat(captor.getValue().getSymbol()).isEqualTo("ETHUSDT");
        assertThat(captor.getValue().getWallet()).isEqualTo("0xabc");
        assertThat(captor.getValue().getPayloadJson()).contains("exchange_outflow");
    }

    @Test
    void ingestProjectsSocialPayloadIntoTypedSocialEvent() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-social-1");
        eventRaw.setEventType("social");
        eventRaw.setSymbol("SOLUSDT");
        eventRaw.setExchangeCode("external");
        eventRaw.setPayloadJson("{\"score\":0.82,\"author\":\"macro_anon\"}");

        eventIngestService.ingest(eventRaw);

        ArgumentCaptor<SocialEvent> captor = ArgumentCaptor.forClass(SocialEvent.class);
        verify(eventIngestMapper).insertSocialEvent(captor.capture());
        assertThat(captor.getValue().getTraceId()).isEqualTo("trace-social-1");
        assertThat(captor.getValue().getSymbol()).isEqualTo("SOLUSDT");
        assertThat(captor.getValue().getScore()).isEqualTo(0.82d);
        assertThat(captor.getValue().getPayloadJson()).contains("macro_anon");
    }

    @Test
    void ingestGeneratesTraceIdAndKeepsRawDurabilityWhenTypedProjectionFails() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setEventType("market_tick");
        eventRaw.setSymbol("BTCUSDT");
        eventRaw.setExchangeCode("binance");
        eventRaw.setPayloadJson("{\"price\":\"bad-number\",\"volume\":12.4}");

        eventIngestService.ingest(eventRaw);

        ArgumentCaptor<EventRaw> rawCaptor = ArgumentCaptor.forClass(EventRaw.class);
        verify(eventIngestMapper).insertEventRaw(rawCaptor.capture());
        assertThat(rawCaptor.getValue().getTraceId()).isNotBlank();
        verify(eventIngestMapper, never()).insertMarketEvent(any(MarketEvent.class));
    }
}
