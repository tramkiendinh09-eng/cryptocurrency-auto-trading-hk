package com.ruoyi.dca.runtime;

import com.ruoyi.dca.mapper.runtime.TradeReplayMapper;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.annotation.MapperScan;
import org.mybatis.spring.boot.test.autoconfigure.MybatisTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;

import static org.assertj.core.api.Assertions.assertThat;

@MybatisTest
@ContextConfiguration(classes = TradeReplayMapperTest.TestApplication.class)
@TestPropertySource(properties = "mybatis.mapper-locations=classpath*:mapper/dca/runtime/*.xml")
@Sql(statements = {
    "drop table if exists pnl_snapshot",
    "drop table if exists position_change_log",
    "drop table if exists exchange_fill",
    "drop table if exists exchange_order",
    "drop table if exists position_snapshot",
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
        "status varchar(32)," +
        "order_status varchar(32)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into exchange_order (trace_id, exchange_code, symbol, side, mode, order_ref, action, position_side, reduce_only, status, order_status) values " +
        "('trace-short-open-1', 'binance', 'XAUUSDT', 'SELL', 'paper', 'ord-short-open-1', 'OPEN_SHORT', 'short', false, 'filled', 'FILLED')," +
        "('trace-short-close-1', 'binance', 'XAUUSDT', 'BUY', 'paper', '', null, 'short', true, 'skipped', 'SKIPPED')," +
        "('trace-short-close-1', 'binance', 'XAUUSDT', 'BUY', 'paper', 'ord-short-close-1', 'CLOSE', 'short', true, 'filled', 'FILLED')",
    "create table exchange_fill (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "order_ref varchar(64)," +
        "fill_price decimal(20,8)," +
        "fill_quantity decimal(20,8)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into exchange_fill (trace_id, order_ref, fill_price, fill_quantity) values " +
        "('trace-short-open-1', 'ord-short-open-1', 2371.05000000, 1.50000000)," +
        "('trace-short-close-1', '', 9999.00000000, 9.00000000)," +
        "('trace-short-close-1', 'ord-short-close-1', 2362.05000000, 1.50000000)",
    "create table position_snapshot (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "position_quantity decimal(20,8)," +
        "entry_price decimal(20,8)," +
        "unrealized_pnl decimal(20,8)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into position_snapshot (trace_id, exchange_code, symbol, side, position_quantity, entry_price, unrealized_pnl) values " +
        "('trace-buy-side', 'okx', 'BTCUSDT', 'buy', 0.03764020, 78187.70, 0.00)," +
        "('trace-sell-side', 'okx', 'BTCUSDT', 'sell', 0.06266970, 78187.70, 0.00)," +
        "('trace-short-open-1', 'binance', 'XAUUSDT', 'short', 1.50000000, 2371.05000000, 0.00)," +
        "('trace-short-close-1', 'binance', 'XAUUSDT', 'short', 0.00000000, 0.00000000, 0.00)",
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
        "('trace-short-close-1', 'binance', 'XAUUSDT', 'short', 'CLOSE', 1.50000000, 0.00000000, -1.50000000, 0.00000000, 0.00)",
    "create table pnl_snapshot (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "mode varchar(16)," +
        "account_equity decimal(20,8)," +
        "unrealized_pnl decimal(20,8)," +
        "realized_pnl decimal(20,8)," +
        "daily_pnl decimal(20,8)," +
        "max_drawdown_pct decimal(20,8)," +
        "peak_account_equity decimal(20,8)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into pnl_snapshot (trace_id, mode, account_equity, unrealized_pnl, realized_pnl, daily_pnl, max_drawdown_pct, peak_account_equity) values " +
        "('trace-short-close-1', 'paper', 10000.00, 0.00, 13.50000000, 13.50000000, 0.00, 10013.50)"
})
class TradeReplayMapperTest {

    @SpringBootApplication
    @MapperScan("com.ruoyi.dca.mapper.runtime")
    static class TestApplication {
    }

    @Autowired
    private TradeReplayMapper tradeReplayMapper;

    @Test
    void selectLatestPositionSnapshotByTraceIdNormalizesLegacyOrderSideAliases() {
        assertThat(tradeReplayMapper.selectLatestPositionSnapshotByTraceId("trace-buy-side").getSide()).isEqualTo("long");
        assertThat(tradeReplayMapper.selectLatestPositionSnapshotByTraceId("trace-sell-side").getSide()).isEqualTo("short");
    }

    @Test
    void selectTradeActionSummaryByTraceIdReturnsOpenCloseAndRealizedPnl() {
        var summary = tradeReplayMapper.selectTradeActionSummaryByTraceId("trace-short-close-1");

        assertThat(summary).isNotNull();
        assertThat(summary.getTraceId()).isEqualTo("trace-short-close-1");
        assertThat(summary.getAction()).isEqualTo("CLOSE");
        assertThat(summary.getOpenPrice()).isEqualByComparingTo("2371.05000000");
        assertThat(summary.getClosePrice()).isEqualByComparingTo("2362.05000000");
        assertThat(summary.getRealizedPnl()).isEqualByComparingTo("13.50000000");
    }
}
