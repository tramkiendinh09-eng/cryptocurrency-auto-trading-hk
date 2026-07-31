package com.ruoyi.dca.runtime;

import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.mapper.runtime.TradeExecutionMapper;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.annotation.MapperScan;
import org.mybatis.spring.boot.test.autoconfigure.MybatisTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@MybatisTest
@ContextConfiguration(classes = TradeExecutionMapperTest.TestApplication.class)
@TestPropertySource(properties = "mybatis.mapper-locations=classpath*:mapper/dca/runtime/*.xml")
@Sql(statements = {
    "drop table if exists position_snapshot",
    "drop table if exists exchange_fill",
    "drop table if exists exchange_order",
    "create table exchange_order (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "mode varchar(16)," +
        "order_ref varchar(64)," +
        "client_order_id varchar(64)," +
        "action varchar(32)," +
        "order_type varchar(16)," +
        "position_side varchar(16)," +
        "reduce_only boolean," +
        "td_mode varchar(16)," +
        "leverage decimal(10,2)," +
        "limit_price decimal(20,8)," +
        "quantity_base decimal(20,8)," +
        "okx_enhanced_execution boolean," +
        "filled_quantity decimal(20,8)," +
        "avg_fill_price decimal(20,8)," +
        "fee decimal(20,8)," +
        "fee_ccy varchar(16)," +
        "post_only boolean," +
        "status varchar(32)," +
        "order_status varchar(32)," +
        "created_at timestamp default current_timestamp," +
        "updated_at timestamp default current_timestamp," +
        "filled_at timestamp null," +
        "raw_payload clob," +
        "unique(exchange_code, order_ref)" +
    ")",
    "insert into exchange_order (trace_id, exchange_code, symbol, side, mode, order_ref, status, order_status) values " +
        "('t-1', 'binance', 'BTCUSDT', 'BUY', 'paper', 'ord-1', 'filled', 'FILLED')," +
        "('t-2', 'binance', 'ETHUSDT', 'BUY', 'paper', 'ord-2', null, 'PARTIALLY_FILLED')," +
        "('t-3', 'okx', 'SOLUSDT', 'SELL', 'shadow', 'ord-3', 'blocked', 'BLOCKED')",
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
        "exec_type varchar(8)," +
        "realized_pnl decimal(20,8)," +
        "filled_at timestamp null," +
        "raw_payload clob," +
        "created_at timestamp default current_timestamp," +
        "unique(exchange_code, trade_id)" +
    ")",
    "create table position_snapshot (" +
        "id bigint auto_increment primary key," +
        "trace_id varchar(64)," +
        "entry_trace_id varchar(64)," +
        "exchange_code varchar(32)," +
        "symbol varchar(32)," +
        "side varchar(16)," +
        "position_quantity decimal(20,8)," +
        "entry_price decimal(20,8)," +
        "unrealized_pnl decimal(20,8)," +
        "created_at timestamp default current_timestamp" +
    ")",
    "insert into position_snapshot (trace_id, exchange_code, symbol, side, position_quantity, entry_price, unrealized_pnl) values " +
        "('pos-1', 'okx', 'BTCUSDT', 'long', 0.00639486, 78187.80, 0.00)," +
        "('pos-2', 'okx', 'BTCUSDT', 'buy', 0.03764020, 78187.70, 0.00)," +
        "('pos-3', 'okx', 'BTCUSDT', 'sell', 0.06266970, 78187.70, 0.00)"
})
class TradeExecutionMapperTest {

    @SpringBootApplication
    @MapperScan("com.ruoyi.dca.mapper.runtime")
    static class TestApplication {
    }

    @Autowired
    private TradeExecutionMapper tradeExecutionMapper;

    @Test
    void selectExchangeOrdersMapsStatusExecutionStatusAndOrderStatus() {
        List<ExchangeOrder> rows = tradeExecutionMapper.selectExchangeOrders(null, null);

        assertThat(rows)
            .extracting(ExchangeOrder::getStatus, ExchangeOrder::getExecutionStatus, ExchangeOrder::getOrderStatus)
            .containsExactly(
                org.assertj.core.groups.Tuple.tuple("blocked", "blocked", "BLOCKED"),
                org.assertj.core.groups.Tuple.tuple("partial", "partial", "PARTIALLY_FILLED"),
                org.assertj.core.groups.Tuple.tuple("filled", "filled", "FILLED")
            );
    }

    @Test
    void insertAndSelectExchangeOrderPreservesExecutionMetadata() {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("t-meta-1");
        order.setExchangeCode("okx");
        order.setSymbol("BTCUSDT");
        order.setSide("SELL");
        order.setMode("live");
        order.setOrderRef("okx-meta-1");
        order.setStatus("pending");
        order.setOrderStatus("PENDING");
        order.setClientOrderId("client-meta-1");
        order.setOrderType("limit");
        order.setPositionSide("long");
        order.setReduceOnly(Boolean.TRUE);
        order.setTdMode("cross");
        order.setLeverage(new java.math.BigDecimal("3"));
        order.setLimitPrice(new java.math.BigDecimal("65000.10000000"));
        order.setQuantityBase(new java.math.BigDecimal("0.05000000"));
        order.setOkxEnhancedExecution(Boolean.TRUE);
        order.setFilledQuantity(new java.math.BigDecimal("0.01000000"));
        order.setAvgFillPrice(new java.math.BigDecimal("65000.20000000"));
        order.setFee(new java.math.BigDecimal("0.12000000"));
        order.setFeeCcy("USDT");
        order.setPostOnly(Boolean.TRUE);
        order.setRawPayload("{\"ordId\":\"okx-meta-1\"}");

        tradeExecutionMapper.insertExchangeOrder(order);

        ExchangeOrder row = tradeExecutionMapper.selectExchangeOrders(null, null).stream()
            .filter(item -> "t-meta-1".equals(item.getTraceId()))
            .findFirst()
            .orElseThrow();

        assertThat(row.getOrderType()).isEqualTo("limit");
        assertThat(row.getPositionSide()).isEqualTo("long");
        assertThat(row.getReduceOnly()).isTrue();
        assertThat(row.getTdMode()).isEqualTo("cross");
        assertThat(row.getLeverage()).isEqualByComparingTo("3");
        assertThat(row.getLimitPrice()).isEqualByComparingTo("65000.10000000");
        assertThat(row.getQuantityBase()).isEqualByComparingTo("0.05000000");
        assertThat(row.getOkxEnhancedExecution()).isTrue();
        assertThat(row.getClientOrderId()).isEqualTo("client-meta-1");
        assertThat(row.getFilledQuantity()).isEqualByComparingTo("0.01000000");
        assertThat(row.getAvgFillPrice()).isEqualByComparingTo("65000.20000000");
        assertThat(row.getFee()).isEqualByComparingTo("0.12000000");
        assertThat(row.getFeeCcy()).isEqualTo("USDT");
        assertThat(row.getPostOnly()).isTrue();
        assertThat(row.getRawPayload()).contains("okx-meta-1");
    }

    @Test
    void updateExchangeOrderByRefUpdatesExistingOrderStatusAndFillMetadata() {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("t-2-updated");
        order.setExchangeCode("binance");
        order.setOrderRef("ord-2");
        order.setStatus("filled");
        order.setOrderStatus("FILLED");
        order.setFilledQuantity(new java.math.BigDecimal("1.25000000"));
        order.setAvgFillPrice(new java.math.BigDecimal("3300.00000000"));

        assertThat(tradeExecutionMapper.updateExchangeOrderByRef(order)).isEqualTo(1);

        ExchangeOrder row = tradeExecutionMapper.selectExchangeOrders(null, null).stream()
            .filter(item -> "t-2-updated".equals(item.getTraceId()))
            .findFirst()
            .orElseThrow();

        assertThat(row.getStatus()).isEqualTo("filled");
        assertThat(row.getOrderStatus()).isEqualTo("FILLED");
        assertThat(row.getFilledQuantity()).isEqualByComparingTo("1.25000000");
        assertThat(row.getAvgFillPrice()).isEqualByComparingTo("3300.00000000");
    }

    @Test
    void insertAndUpdateExchangeFillPreservesMakerFeeAndTradeId() {
        ExchangeFill fill = new ExchangeFill();
        fill.setTraceId("fill-trace-1");
        fill.setExchangeCode("okx");
        fill.setSymbol("BTCUSDT");
        fill.setSide("buy");
        fill.setPositionSide("long");
        fill.setOrderRef("ord-fill-1");
        fill.setTradeId("trade-fill-1");
        fill.setFillPrice(new java.math.BigDecimal("65000.00000000"));
        fill.setFillQuantity(new java.math.BigDecimal("0.01000000"));
        fill.setFee(new java.math.BigDecimal("0.05000000"));
        fill.setFeeCcy("USDT");
        fill.setIsMaker(Boolean.TRUE);
        fill.setExecType("M");
        fill.setRealizedPnl(new java.math.BigDecimal("1.23000000"));

        tradeExecutionMapper.insertExchangeFill(fill);

        ExchangeFill row = tradeExecutionMapper.selectExchangeFills().stream()
            .filter(item -> "trade-fill-1".equals(item.getTradeId()))
            .findFirst()
            .orElseThrow();
        assertThat(row.getIsMaker()).isTrue();
        assertThat(row.getFee()).isEqualByComparingTo("0.05000000");

        fill.setFillQuantity(new java.math.BigDecimal("0.02000000"));
        fill.setIsMaker(Boolean.FALSE);
        fill.setExecType("T");

        assertThat(tradeExecutionMapper.updateExchangeFillByTradeId(fill)).isEqualTo(1);

        ExchangeFill updated = tradeExecutionMapper.selectExchangeFills().stream()
            .filter(item -> "trade-fill-1".equals(item.getTradeId()))
            .findFirst()
            .orElseThrow();
        assertThat(updated.getFillQuantity()).isEqualByComparingTo("0.02000000");
        assertThat(updated.getIsMaker()).isFalse();
        assertThat(updated.getExecType()).isEqualTo("T");
    }

    @Test
    void selectExecutionStatusCountsNormalizesBusinessBuckets() {
        List<Map<String, Object>> rows = tradeExecutionMapper.selectExecutionStatusCounts();

        assertThat(rows)
            .extracting(
                row -> mapValue(row, "executionStatus"),
                row -> ((Number) mapValue(row, "total")).longValue()
            )
            .containsExactlyInAnyOrder(
                org.assertj.core.groups.Tuple.tuple("filled", 1L),
                org.assertj.core.groups.Tuple.tuple("partial", 1L),
                org.assertj.core.groups.Tuple.tuple("blocked", 1L)
            );
    }


    @Test
    void selectPositionSnapshotsCoalescesLegacyOrderSideAliasesIntoPositionSides() {
        assertThat(tradeExecutionMapper.selectPositionSnapshots())
            .extracting("symbol", "side", "positionQuantity")
            .containsExactlyInAnyOrder(
                org.assertj.core.groups.Tuple.tuple("BTCUSDT", "long", new java.math.BigDecimal("0.03764020")),
                org.assertj.core.groups.Tuple.tuple("BTCUSDT", "short", new java.math.BigDecimal("0.06266970"))
            );
    }

    private Object mapValue(Map<String, Object> row, String key) {
        return row.entrySet().stream()
            .filter(entry -> entry.getKey() != null && entry.getKey().equalsIgnoreCase(key))
            .map(Map.Entry::getValue)
            .findFirst()
            .orElse(null);
    }
}
