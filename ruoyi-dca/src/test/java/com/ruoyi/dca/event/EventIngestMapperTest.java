package com.ruoyi.dca.event;

import com.ruoyi.dca.domain.event.EventRaw;
import com.ruoyi.dca.domain.event.MarketEvent;
import com.ruoyi.dca.domain.event.MarketKlineSnapshot;
import com.ruoyi.dca.domain.event.MarketMetricSnapshot;
import com.ruoyi.dca.domain.event.NewsEvent;
import com.ruoyi.dca.domain.event.OnchainEvent;
import com.ruoyi.dca.domain.event.SocialEvent;
import com.ruoyi.dca.mapper.event.EventIngestMapper;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.annotation.MapperScan;
import org.mybatis.spring.boot.test.autoconfigure.MybatisTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;

import static org.assertj.core.api.Assertions.assertThat;

@MybatisTest
@ContextConfiguration(classes = EventIngestMapperTest.TestApplication.class)
@TestPropertySource(properties = "mybatis.mapper-locations=classpath*:mapper/dca/event/*.xml")
@Sql(statements = {
    "drop table if exists social_event",
    "drop table if exists onchain_event",
    "drop table if exists news_event",
    "drop table if exists market_metric_snapshot",
    "drop table if exists market_kline_snapshot",
    "drop table if exists market_event",
    "drop table if exists event_raw",
    "create table event_raw (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64) not null," +
        "event_type varchar(32) not null," +
        "symbol varchar(32) not null," +
        "exchange_code varchar(16) not null," +
        "payload_json clob not null," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table market_event (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64) not null," +
        "symbol varchar(32) not null," +
        "exchange_code varchar(16) not null," +
        "price decimal(20,8) not null," +
        "volume decimal(20,8) not null," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table market_kline_snapshot (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64) not null," +
        "symbol varchar(32) not null," +
        "exchange_code varchar(16) not null," +
        "interval_code varchar(16) not null," +
        "open_time varchar(64)," +
        "close_time varchar(64)," +
        "open_price decimal(30,12)," +
        "high_price decimal(30,12)," +
        "low_price decimal(30,12)," +
        "close_price decimal(30,12)," +
        "volume decimal(30,12)," +
        "quote_volume decimal(30,12)," +
        "trade_count bigint," +
        "source varchar(32)," +
        "payload_json clob," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table market_metric_snapshot (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64) not null," +
        "symbol varchar(32) not null," +
        "exchange_code varchar(16) not null," +
        "observed_at varchar(64)," +
        "latest_price decimal(30,12)," +
        "mark_price decimal(30,12)," +
        "mark_price_deviation_pct decimal(20,8)," +
        "funding_rate decimal(20,10)," +
        "open_interest decimal(30,12)," +
        "volume_24h decimal(30,12)," +
        "quote_volume_24h decimal(30,12)," +
        "liquidation_notional_15m decimal(30,12)," +
        "liquidation_notional_60m decimal(30,12)," +
        "liquidation_notional_240m decimal(30,12)," +
        "largest_liquidation_notional_usd decimal(30,12)," +
        "largest_liquidation_side varchar(16)," +
        "source_status varchar(64)," +
        "payload_json clob," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table news_event (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64) not null," +
        "symbol varchar(32) not null," +
        "source varchar(64) not null," +
        "headline varchar(512) not null," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table onchain_event (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64) not null," +
        "symbol varchar(32) not null," +
        "wallet varchar(128) not null," +
        "payload_json clob not null," +
        "created_at timestamp default current_timestamp" +
    ")",
    "create table social_event (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64) not null," +
        "symbol varchar(32) not null," +
        "score decimal(10,4) not null," +
        "payload_json clob not null," +
        "created_at timestamp default current_timestamp" +
    ")"
})
class EventIngestMapperTest {

    @SpringBootApplication
    @MapperScan("com.ruoyi.dca.mapper.event")
    static class TestApplication {
    }

    @Autowired
    private EventIngestMapper eventIngestMapper;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void selectRecentRawMarketEventsReturnsLatestRowsInDescendingOrder() {
        jdbcTemplate.update("insert into event_raw(trace_id,event_type,symbol,exchange_code,payload_json,created_at) values('trace-old','market_tick','BTCUSDT','okx','{\"price\":1}', timestamp '2026-04-29 04:00:00')");
        jdbcTemplate.update("insert into event_raw(trace_id,event_type,symbol,exchange_code,payload_json,created_at) values('trace-new','market_tick','BTCUSDT','okx','{\"price\":2}', timestamp '2026-04-29 04:01:00')");
        jdbcTemplate.update("insert into event_raw(trace_id,event_type,symbol,exchange_code,payload_json,created_at) values('trace-news','news','BTCUSDT','okx','{\"headline\":\"ignore\"}', timestamp '2026-04-29 04:02:00')");
        jdbcTemplate.update("insert into event_raw(trace_id,event_type,symbol,exchange_code,payload_json,created_at) values('trace-stale','market_tick','BTCUSDT','okx','{\"price\":0.5}', timestamp '2026-04-29 03:00:00')");

        java.util.List<EventRaw> rows = eventIngestMapper.selectRecentRawMarketEvents("BTCUSDT", "okx", "2026-04-29 03:59:00", 2);

        assertThat(rows).hasSize(2);
        assertThat(rows.get(0).getTraceId()).isEqualTo("trace-new");
        assertThat(rows.get(1).getTraceId()).isEqualTo("trace-old");
    }

    @Test
    void insertEventRawPersistsRawRow() {
        EventRaw eventRaw = new EventRaw();
        eventRaw.setTraceId("trace-raw-1");
        eventRaw.setEventType("news");
        eventRaw.setSymbol("BTCUSDT");
        eventRaw.setExchangeCode("external");
        eventRaw.setPayloadJson("{\"headline\":\"macro headline\"}");

        eventIngestMapper.insertEventRaw(eventRaw);

        assertThat(jdbcTemplate.queryForObject("select count(*) from event_raw where trace_id = 'trace-raw-1'", Long.class))
            .isEqualTo(1L);
    }

    @Test
    void insertMarketEventPersistsTypedMarketRow() {
        MarketEvent marketEvent = new MarketEvent();
        marketEvent.setTraceId("trace-market-1");
        marketEvent.setSymbol("BTCUSDT");
        marketEvent.setExchangeCode("binance");
        marketEvent.setPrice(new java.math.BigDecimal("65000.5"));
        marketEvent.setVolume(new java.math.BigDecimal("12.4"));

        eventIngestMapper.insertMarketEvent(marketEvent);

        assertThat(jdbcTemplate.queryForObject("select exchange_code from market_event where trace_id = 'trace-market-1'", String.class))
            .isEqualTo("binance");
    }

    @Test
    void insertMarketKlineSnapshotPersistsTypedKlineRow() {
        MarketKlineSnapshot snapshot = new MarketKlineSnapshot();
        snapshot.setTraceId("trace-kline-1");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setExchangeCode("okx");
        snapshot.setIntervalCode("1m");
        snapshot.setOpenTime("2026-04-29 18:00:00");
        snapshot.setCloseTime("2026-04-29 18:01:00");
        snapshot.setOpenPrice(new java.math.BigDecimal("77000.1"));
        snapshot.setHighPrice(new java.math.BigDecimal("77120.0"));
        snapshot.setLowPrice(new java.math.BigDecimal("76980.0"));
        snapshot.setClosePrice(new java.math.BigDecimal("77100.5"));
        snapshot.setVolume(new java.math.BigDecimal("12.5"));
        snapshot.setQuoteVolume(new java.math.BigDecimal("963756.25"));
        snapshot.setSource("okx_rest");
        snapshot.setPayloadJson("{\"interval\":\"1m\"}");

        eventIngestMapper.insertMarketKlineSnapshot(snapshot);

        assertThat(jdbcTemplate.queryForObject("select close_price from market_kline_snapshot where trace_id = 'trace-kline-1'", java.math.BigDecimal.class))
            .isEqualByComparingTo("77100.5");
    }

    @Test
    void insertMarketMetricSnapshotPersistsTypedMetricRow() {
        MarketMetricSnapshot snapshot = new MarketMetricSnapshot();
        snapshot.setTraceId("trace-metric-1");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setExchangeCode("okx");
        snapshot.setObservedAt("2026-04-29 18:01:00");
        snapshot.setLatestPrice(new java.math.BigDecimal("77100.5"));
        snapshot.setMarkPrice(new java.math.BigDecimal("77102.0"));
        snapshot.setFundingRate(new java.math.BigDecimal("0.0001"));
        snapshot.setLiquidationNotional60m(new java.math.BigDecimal("360000"));
        snapshot.setPayloadJson("{\"latest_price\":77100.5}");

        eventIngestMapper.insertMarketMetricSnapshot(snapshot);

        assertThat(jdbcTemplate.queryForObject("select liquidation_notional_60m from market_metric_snapshot where trace_id = 'trace-metric-1'", java.math.BigDecimal.class))
            .isEqualByComparingTo("360000");
    }

    @Test
    void insertNewsEventPersistsTypedNewsRow() {
        NewsEvent newsEvent = new NewsEvent();
        newsEvent.setTraceId("trace-news-1");
        newsEvent.setSymbol("BTCUSDT");
        newsEvent.setSource("rss");
        newsEvent.setHeadline("ETF inflow accelerates");

        eventIngestMapper.insertNewsEvent(newsEvent);

        assertThat(jdbcTemplate.queryForObject("select source from news_event where trace_id = 'trace-news-1'", String.class))
            .isEqualTo("rss");
    }

    @Test
    void insertOnchainEventPersistsTypedOnchainRow() {
        OnchainEvent onchainEvent = new OnchainEvent();
        onchainEvent.setTraceId("trace-onchain-1");
        onchainEvent.setSymbol("ETHUSDT");
        onchainEvent.setWallet("0xabc");
        onchainEvent.setPayloadJson("{\"flow\":\"exchange_outflow\"}");

        eventIngestMapper.insertOnchainEvent(onchainEvent);

        assertThat(jdbcTemplate.queryForObject("select wallet from onchain_event where trace_id = 'trace-onchain-1'", String.class))
            .isEqualTo("0xabc");
    }

    @Test
    void insertSocialEventPersistsTypedSocialRow() {
        SocialEvent socialEvent = new SocialEvent();
        socialEvent.setTraceId("trace-social-1");
        socialEvent.setSymbol("SOLUSDT");
        socialEvent.setScore(0.82d);
        socialEvent.setPayloadJson("{\"headline\":\"macro_anon\"}");

        eventIngestMapper.insertSocialEvent(socialEvent);

        assertThat(jdbcTemplate.queryForObject("select score from social_event where trace_id = 'trace-social-1'", Double.class))
            .isEqualTo(0.82d);
    }
}
