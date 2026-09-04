package com.ruoyi.dca.trade.mapper;

import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.mapper.trade.TradeRuntimeOverviewMapper;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.boot.test.autoconfigure.MybatisTest;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;

import java.util.List;
import java.util.Map;
import java.util.TimeZone;

import static org.assertj.core.api.Assertions.assertThat;

@MybatisTest
@ContextConfiguration(classes = TradeRuntimeOverviewMapperTest.TestApplication.class)
@TestPropertySource(properties = "mybatis.mapper-locations=classpath*:mapper/dca/trade/*.xml")
@Sql(statements = {
    "drop table if exists event_raw",
    "drop table if exists signal_window_state",
    "drop table if exists position_change_log",
    "drop table if exists position_snapshot",
    "drop table if exists exchange_fill",
    "drop table if exists exchange_order",
    "create table event_raw (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "event_type varchar(64)," +
        "symbol varchar(32)," +
        "exchange_code varchar(32)," +
        "payload_json clob," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into event_raw (trace_id, event_type, symbol, exchange_code, payload_json) values " +
        "('trace-event-1', 'market_tick', 'BTCUSDT', 'binance', '{\"price\":65000}')," +
        "('trace-event-2', 'news', 'ETHUSDT', 'okx', '{\"headline\":\"ETF\"}')",
    "create table position_snapshot (" +
        "id bigint auto_increment primary key," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "trace_id varchar(64)," +
        "position_quantity decimal(20,8)," +
        "entry_price decimal(20,8)," +
        "unrealized_pnl decimal(20,8)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into position_snapshot (trace_id, exchange_code, symbol, side, position_quantity, entry_price, unrealized_pnl) values " +
        "('trace-pos-1', 'binance', 'BTCUSDT', 'long', 0.10000000, 65000.00, 10.00)," +
        "('trace-pos-2', 'binance', 'BTCUSDT', 'long', 0.12500000, 65200.00, 15.50)," +
        "('trace-pos-legacy-buy', 'binance', 'BTCUSDT', 'buy', 0.13000000, 65300.00, 17.00)," +
        "('trace-short-open-1', 'binance', 'XAUUSDT', 'short', 1.50000000, 2371.05000000, 0.00)," +
        "('trace-short-close-1', 'binance', 'XAUUSDT', 'short', 0.00000000, 0.00000000, 0.00)," +
        "('trace-guard-open-1', 'okx', 'ETHUSDT', 'short', 1.00000000, 100.00000000, 0.00)," +
        "('trace-guard-close-1', 'okx', 'ETHUSDT', 'short', 0.00000000, 0.00000000, 0.00)," +
        "('trace-pos-3', 'okx', 'ETHUSDT', 'long', 0.00000000, 3200.00, 0.00)",
    "create table position_change_log (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "change_type varchar(32)," +
        "before_quantity decimal(20,8)," +
        "after_quantity decimal(20,8)," +
        "delta_quantity decimal(20,8)," +
        "entry_price decimal(20,8)," +
        "unrealized_pnl decimal(20,8)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into position_change_log (trace_id, exchange_code, symbol, side, change_type, before_quantity, after_quantity, delta_quantity, entry_price, unrealized_pnl) values " +
        "('trace-short-open-1', 'binance', 'XAUUSDT', 'short', 'OPEN', 0.00000000, 1.50000000, 1.50000000, 2371.05000000, 0.00)," +
        "('trace-short-close-1', 'binance', 'XAUUSDT', 'short', 'CLOSE', 1.50000000, 0.00000000, -1.50000000, 0.00000000, 0.00)," +
        "('trace-guard-open-1', 'okx', 'ETHUSDT', 'short', 'OPEN', 0.00000000, 1.00000000, 1.00000000, 100.00000000, 0.00)," +
        "('trace-guard-close-1', 'okx', 'ETHUSDT', 'short', 'CLOSE', 1.00000000, 0.00000000, -1.00000000, 0.00000000, 0.00)",
    "create table signal_window_state (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "symbol varchar(32)," +
        "window_key varchar(128)," +
        "source_type varchar(32)," +
        "signal_type varchar(32)," +
        "direction varchar(16)," +
        "strength_score decimal(10,4)," +
        "decay_score decimal(10,4)," +
        "opened_at timestamp null," +
        "expires_at timestamp null," +
        "last_event_at timestamp null," +
        "last_confirmed_at timestamp null," +
        "dedupe_key varchar(128)," +
        "combine_until_at timestamp null," +
        "is_active tinyint," +
        "state_json clob," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into signal_window_state (" +
        "trace_id, symbol, window_key, source_type, signal_type, direction, strength_score, decay_score, opened_at, expires_at, " +
        "last_event_at, last_confirmed_at, dedupe_key, combine_until_at, is_active, state_json) values " +
        "('trace-window-1', 'BTCUSDT', 'news:BTCUSDT:15m', 'news', 'headline', 'bullish', 0.8200, 0.8200, " +
        "TIMESTAMPADD('MINUTE', -5, CURRENT_TIMESTAMP), TIMESTAMPADD('MINUTE', 10, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, " +
        "'news:bullish', TIMESTAMPADD('MINUTE', 10, CURRENT_TIMESTAMP), 1, '{\"count\":1}')," +
        "('trace-window-2', 'ETHUSDT', 'social:ETHUSDT:15m', 'social', 'sentiment', 'bearish', 0.7700, 0.7700, " +
        "TIMESTAMPADD('MINUTE', -30, CURRENT_TIMESTAMP), TIMESTAMPADD('MINUTE', -1, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, " +
        "'social:bearish', TIMESTAMPADD('MINUTE', -1, CURRENT_TIMESTAMP), 1, '{\"count\":2}')",
    "create table exchange_order (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "mode varchar(16)," +
        "order_ref varchar(64)," +
        "action varchar(32)," +
        "order_type varchar(16)," +
        "position_side varchar(16)," +
        "reduce_only boolean," +
        "td_mode varchar(16)," +
        "leverage decimal(10,2)," +
        "limit_price decimal(20,8)," +
        "quantity_base decimal(20,8)," +
        "okx_enhanced_execution boolean," +
        "client_order_id varchar(64)," +
        "filled_quantity decimal(20,8)," +
        "avg_fill_price decimal(20,8)," +
        "fee decimal(20,8)," +
        "fee_ccy varchar(16)," +
        "post_only boolean," +
        "status varchar(32)," +
        "order_status varchar(32)," +
        "filled_at timestamp," +
        "raw_payload clob," +
        "created_at timestamp default current_timestamp," +
        "updated_at timestamp" +
    ")",
    "insert into exchange_order (trace_id, exchange_code, symbol, side, mode, order_ref, status, order_status) values " +
        "('t-1', 'binance', 'BTCUSDT', 'BUY', 'paper', 'ord-1', 'filled', 'FILLED')," +
        "('t-2', 'binance', 'ETHUSDT', 'BUY', 'paper', 'ord-2', null, 'PARTIALLY_FILLED')," +
        "('t-3', 'okx', 'BTCUSDT', 'SELL', 'shadow', 'ord-3', 'failed', 'REJECTED')," +
        "('t-4', 'binance', 'SOLUSDT', 'BUY', 'paper', 'ord-4', 'blocked', 'BLOCKED')," +
        "('t-5', 'okx', 'ETHUSDT', 'SELL', 'shadow', 'ord-5', 'skipped', 'SKIPPED')," +
        "('trace-guard-close-1', 'okx', 'ETHUSDT', 'BUY', 'paper', '', 'skipped', 'SKIPPED')",
    "insert into exchange_order (trace_id, exchange_code, symbol, side, mode, order_ref, action, position_side, reduce_only, status, order_status) values " +
        "('trace-short-open-1', 'binance', 'XAUUSDT', 'SELL', 'paper', 'ord-short-open-1', 'OPEN_SHORT', 'short', false, 'filled', 'FILLED')," +
        "('trace-short-close-1', 'binance', 'XAUUSDT', 'BUY', 'paper', 'ord-short-close-1', 'CLOSE', 'short', true, 'filled', 'FILLED')," +
        "('trace-guard-close-1', 'okx', 'ETHUSDT', 'BUY', 'paper', 'ord-guard-close-1', null, 'short', true, 'filled', 'FILLED')",
    // 列必须覆盖 selectRecentExchangeFills 查询的全部字段。这份内联 DDL 和
    // mapper 漂移过一次：缺 exchange_code 等列，H2 直接抛
    // "Column EXCHANGE_CODE not found"，用例长期红着被当成已知失败。
    // 生产 MySQL 上这些列都在，所以只是测试陈旧，不是 mapper 有问题。
    "create table exchange_fill (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "position_side varchar(16)," +
        "order_ref varchar(64)," +
        "trade_id varchar(64)," +
        "fill_price decimal(20,8)," +
        "fill_quantity decimal(20,8)," +
        "fee decimal(20,8)," +
        "fee_ccy varchar(16)," +
        "is_maker boolean," +
        "exec_type varchar(16)," +
        "realized_pnl decimal(20,8)," +
        "filled_at timestamp," +
        "raw_payload clob," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into exchange_fill (trace_id, order_ref, fill_price, fill_quantity) values " +
        "('t-fill-1', 'ord-1', 65000.00, 0.01000000)," +
        "('t-fill-2', 'ord-2', 3300.00, 1.25000000)," +
        "('trace-short-open-1', 'ord-short-open-1', 2371.05000000, 1.50000000)," +
        "('trace-short-close-1', 'ord-short-close-1', 2362.05000000, 1.50000000)," +
        "('trace-guard-close-1', 'ord-guard-close-1', 95.00000000, 1.00000000)," +
        "('trace-unrelated-same-ref', 'ord-guard-close-1', 120.00000000, 9.00000000)"
})
class TradeRuntimeOverviewMapperTest {

    static {
        // 测试数据用 H2 的 CURRENT_TIMESTAMP 生成（JVM 默认时区），而查询参数用
        // TradeRuntimeTimeUtils.nowSqlDateTime()（固定 Asia/Shanghai，见
        // TradeRuntimeTimeUtils.DATABASE_ZONE）。JVM 时区不是 Asia/Shanghai 时
        // 两者相差整整 8 小时，"10 分钟后过期"的窗口会被判成已过期，
        // selectActiveSignalWindowsExcludesExpiredRows 恒返回空。
        //
        // 生产上不会有这个问题：MySQL 实例已设 default-time-zone='+08:00'，
        // 与 DATABASE_ZONE 一致（实测 NOW() 比系统 UTC 正好快 8 小时）。所以这里
        // 把测试 JVM 钉到同一时区，让 H2 复现生产的那对配对，而不是去改判定。
        //
        // static 块在 Spring 上下文构建（以及 @Sql 插入数据）之前执行。
        TimeZone.setDefault(TimeZone.getTimeZone(TradeRuntimeTimeUtils.DATABASE_ZONE));
    }

    @SpringBootApplication
    @MapperScan("com.ruoyi.dca.mapper.trade")
    static class TestApplication {
    }

    @Autowired
    private TradeRuntimeOverviewMapper tradeRuntimeOverviewMapper;

    @Test
    void selectRecentEventRawsReturnsLatestRowsFirst() {
        assertThat(tradeRuntimeOverviewMapper.selectRecentEventRaws(5))
            .extracting("traceId")
            .containsExactly("trace-event-2", "trace-event-1");
    }

    @Test
    void selectRecentExchangeOrdersMapsUnifiedExecutionStatus() {
        List<ExchangeOrder> orders = tradeRuntimeOverviewMapper.selectRecentExchangeOrders(9);

        assertThat(orders).hasSize(9);
        assertThat(orders)
            .extracting(ExchangeOrder::getStatus, ExchangeOrder::getOrderStatus)
            .contains(
                org.assertj.core.groups.Tuple.tuple("filled", "FILLED"),
                org.assertj.core.groups.Tuple.tuple("partial", "PARTIALLY_FILLED"),
                org.assertj.core.groups.Tuple.tuple("failed", "REJECTED"),
                org.assertj.core.groups.Tuple.tuple("blocked", "BLOCKED"),
                org.assertj.core.groups.Tuple.tuple("skipped", "SKIPPED")
            );
    }

    @Test
    void selectExecutionStatusCountsNormalizesBusinessStatusBuckets() {
        List<Map<String, Object>> rows = tradeRuntimeOverviewMapper.selectExecutionStatusCounts();

        assertThat(rows)
            .extracting(row -> row.get("executionStatus"), row -> ((Number) row.get("total")).longValue())
            .containsExactlyInAnyOrder(
                org.assertj.core.groups.Tuple.tuple("filled", 4L),
                org.assertj.core.groups.Tuple.tuple("partial", 1L),
                org.assertj.core.groups.Tuple.tuple("failed", 1L),
                org.assertj.core.groups.Tuple.tuple("blocked", 1L),
                org.assertj.core.groups.Tuple.tuple("skipped", 2L)
            );
    }

    @Test
    void selectRecentExchangeFillsReturnsLatestExecutionTape() {
        List<ExchangeFill> fills = tradeRuntimeOverviewMapper.selectRecentExchangeFills(5);

        assertThat(fills).hasSize(5);
        assertThat(fills)
            .extracting(ExchangeFill::getTraceId, ExchangeFill::getOrderRef)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple("trace-unrelated-same-ref", "ord-guard-close-1"),
                org.assertj.core.groups.Tuple.tuple("trace-guard-close-1", "ord-guard-close-1"),
                org.assertj.core.groups.Tuple.tuple("trace-short-close-1", "ord-short-close-1"),
                org.assertj.core.groups.Tuple.tuple("trace-short-open-1", "ord-short-open-1"),
                org.assertj.core.groups.Tuple.tuple("t-fill-2", "ord-2")
            );
    }

    @Test
    void selectRecentTradeActionSummariesJoinsOpenCloseAndRealizedPnl() {
        var actions = tradeRuntimeOverviewMapper.selectRecentTradeActionSummaries(5);

        assertThat(actions).extracting("traceId", "action", "openPrice", "closePrice", "realizedPnl")
            .contains(
                org.assertj.core.groups.Tuple.tuple(
                    "trace-guard-close-1",
                    "CLOSE",
                    new java.math.BigDecimal("100.00000000"),
                    new java.math.BigDecimal("95.00000000"),
                    new java.math.BigDecimal("5.00000000")
                ),
                org.assertj.core.groups.Tuple.tuple(
                    "trace-short-open-1",
                    "OPEN_SHORT",
                    new java.math.BigDecimal("2371.05000000"),
                    null,
                    new java.math.BigDecimal("0")
                ),
                org.assertj.core.groups.Tuple.tuple(
                    "trace-short-close-1",
                    "CLOSE",
                    new java.math.BigDecimal("2371.05000000"),
                    new java.math.BigDecimal("2362.05000000"),
                    new java.math.BigDecimal("13.50000000")
                )
            );
        assertThat(actions)
            .filteredOn(action -> "trace-guard-close-1".equals(action.getTraceId()))
            .singleElement()
            .satisfies(action -> {
                assertThat(action.getOrderRef()).isEqualTo("ord-guard-close-1");
                assertThat(action.getAction()).isEqualTo("CLOSE");
            });
    }

    @Test
    void countActivePositionsCountsLatestSnapshotPerScope() {
        assertThat(tradeRuntimeOverviewMapper.countActivePositions()).isEqualTo(1L);
    }

    @Test
    void sumTotalUnrealizedPnlUsesLatestSnapshotPerScope() {
        assertThat(tradeRuntimeOverviewMapper.sumTotalUnrealizedPnl()).isEqualByComparingTo("17.00");
    }

    @Test
    void selectRecentPositionSnapshotsReturnsLatestSnapshotPerScope() {
        assertThat(tradeRuntimeOverviewMapper.selectRecentPositionSnapshots(5))
            .hasSize(1)
            .first()
            .satisfies(position -> {
                assertThat(position.getSide()).isEqualTo("long");
                assertThat(position.getPositionQuantity()).isEqualByComparingTo("0.13000000");
                assertThat(position.getEntryPrice()).isEqualByComparingTo("65300.00");
                assertThat(position.getUnrealizedPnl()).isEqualByComparingTo("17.00");
            });
    }

    @Test
    void selectActiveSignalWindowsExcludesExpiredRows() {
        assertThat(tradeRuntimeOverviewMapper.selectActiveSignalWindows(5, TradeRuntimeTimeUtils.nowSqlDateTime()))
            .hasSize(1)
            .first()
            .satisfies(window -> {
                assertThat(window.getWindowKey()).isEqualTo("news:BTCUSDT:15m");
                assertThat(window.getSourceType()).isEqualTo("news");
                assertThat(window.getActive()).isTrue();
            });
    }
}
