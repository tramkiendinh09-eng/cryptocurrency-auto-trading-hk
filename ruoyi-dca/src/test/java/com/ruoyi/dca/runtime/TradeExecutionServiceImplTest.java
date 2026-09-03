package com.ruoyi.dca.runtime;

import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionChangeLog;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.mapper.runtime.TradeExecutionMapper;
import com.ruoyi.dca.service.INotifyRecordService;
import com.ruoyi.dca.service.runtime.impl.TradeExecutionServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TradeExecutionServiceImplTest {

    @Mock
    private TradeExecutionMapper tradeExecutionMapper;

    @Mock
    private INotifyRecordService notifyRecordService;

    @InjectMocks
    private TradeExecutionServiceImpl tradeExecutionService;

    @Test
    void recordExchangeOrderBackfillsBusinessStatusFromOrderStatus() {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("trace-order-1");
        order.setExchangeCode("binance");
        order.setSymbol("BTCUSDT");
        order.setSide("BUY");
        order.setMode("live");
        order.setOrderRef("ord-1");
        order.setOrderStatus("PARTIALLY_FILLED");

        tradeExecutionService.recordExchangeOrder(order);

        ArgumentCaptor<ExchangeOrder> captor = ArgumentCaptor.forClass(ExchangeOrder.class);
        verify(tradeExecutionMapper).insertExchangeOrder(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("partial");
        assertThat(captor.getValue().getExecutionStatus()).isEqualTo("partial");
        assertThat(captor.getValue().getOrderStatus()).isEqualTo("PARTIALLY_FILLED");
    }

    @Test
    void recordExchangeOrderBackfillsOrderStatusFromBusinessStatus() {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("trace-order-2");
        order.setExchangeCode("okx");
        order.setSymbol("ETHUSDT");
        order.setSide("SELL");
        order.setMode("shadow");
        order.setOrderRef("ord-2");
        order.setStatus("blocked");

        tradeExecutionService.recordExchangeOrder(order);

        ArgumentCaptor<ExchangeOrder> captor = ArgumentCaptor.forClass(ExchangeOrder.class);
        verify(tradeExecutionMapper).insertExchangeOrder(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("blocked");
        assertThat(captor.getValue().getExecutionStatus()).isEqualTo("blocked");
        assertThat(captor.getValue().getOrderStatus()).isEqualTo("BLOCKED");
    }

    @Test
    void recordExchangeOrderAcceptsExecutionStatusOnly() {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("trace-order-3");
        order.setExchangeCode("binance");
        order.setSymbol("SOLUSDT");
        order.setSide("BUY");
        order.setMode("paper");
        order.setOrderRef("ord-3");
        order.setExecutionStatus("submitted");

        tradeExecutionService.recordExchangeOrder(order);

        ArgumentCaptor<ExchangeOrder> captor = ArgumentCaptor.forClass(ExchangeOrder.class);
        verify(tradeExecutionMapper).insertExchangeOrder(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo("submitted");
        assertThat(captor.getValue().getExecutionStatus()).isEqualTo("submitted");
        assertThat(captor.getValue().getOrderStatus()).isEqualTo("SUBMITTED");
    }

    @Test
    void recordExchangeOrderUpdatesExistingOrderByExchangeAndOrderRef() {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("trace-order-updated");
        order.setExchangeCode("okx");
        order.setSymbol("BTCUSDT");
        order.setSide("BUY");
        order.setMode("live");
        order.setOrderRef("okx-order-1");
        order.setOrderStatus("FILLED");

        when(tradeExecutionMapper.updateExchangeOrderByRef(order)).thenReturn(1);

        tradeExecutionService.recordExchangeOrder(order);

        verify(tradeExecutionMapper).updateExchangeOrderByRef(order);
        verify(tradeExecutionMapper, never()).insertExchangeOrder(order);
    }

    @Test
    void recordExchangeFillUpdatesExistingFillByExchangeAndTradeId() {
        ExchangeFill fill = new ExchangeFill();
        fill.setTraceId("trace-fill-updated");
        fill.setExchangeCode("okx");
        fill.setTradeId("trade-1");
        fill.setOrderRef("okx-order-1");
        fill.setFillPrice(new java.math.BigDecimal("65000.00"));
        fill.setFillQuantity(new java.math.BigDecimal("0.01"));

        when(tradeExecutionMapper.updateExchangeFillByTradeId(fill)).thenReturn(1);

        tradeExecutionService.recordExchangeFill(fill);

        verify(tradeExecutionMapper).updateExchangeFillByTradeId(fill);
        verify(tradeExecutionMapper, never()).insertExchangeFill(fill);
    }

    @Test
    void recordExchangeOrderStoresBlankOrderRefAsNullWithoutUpsert() {
        ExchangeOrder order = new ExchangeOrder();
        order.setTraceId("trace-order-blank-ref");
        order.setExchangeCode("okx");
        order.setSymbol("BTCUSDT");
        order.setMode("paper");
        order.setOrderRef(" ");
        order.setStatus("skipped");

        tradeExecutionService.recordExchangeOrder(order);

        ArgumentCaptor<ExchangeOrder> captor = ArgumentCaptor.forClass(ExchangeOrder.class);
        verify(tradeExecutionMapper, never()).updateExchangeOrderByRef(order);
        verify(tradeExecutionMapper).insertExchangeOrder(captor.capture());
        assertThat(captor.getValue().getOrderRef()).isNull();
    }

    @Test
    void recordExchangeFillStoresBlankTradeIdAsNullWithoutUpsert() {
        ExchangeFill fill = new ExchangeFill();
        fill.setTraceId("trace-fill-blank-id");
        fill.setExchangeCode("okx");
        fill.setTradeId(" ");
        fill.setOrderRef("okx-order-blank-fill");
        fill.setFillPrice(new java.math.BigDecimal("65000.00"));
        fill.setFillQuantity(new java.math.BigDecimal("0.01"));

        tradeExecutionService.recordExchangeFill(fill);

        ArgumentCaptor<ExchangeFill> captor = ArgumentCaptor.forClass(ExchangeFill.class);
        verify(tradeExecutionMapper, never()).updateExchangeFillByTradeId(fill);
        verify(tradeExecutionMapper).insertExchangeFill(captor.capture());
        assertThat(captor.getValue().getTradeId()).isNull();
    }

    @Test
    void recordPnlSnapshotDefaultsPeakAccountEquityToAccountEquityWhenMissing() {
        PnlSnapshot snapshot = new PnlSnapshot();
        snapshot.setTraceId("trace-pnl-1");
        snapshot.setMode("paper");
        snapshot.setAccountEquity(new java.math.BigDecimal("10250.25"));
        snapshot.setDailyPnl(new java.math.BigDecimal("120.50"));
        snapshot.setMaxDrawdownPct(new java.math.BigDecimal("4.25"));

        tradeExecutionService.recordPnlSnapshot(snapshot);

        ArgumentCaptor<PnlSnapshot> captor = ArgumentCaptor.forClass(PnlSnapshot.class);
        verify(tradeExecutionMapper).insertPnlSnapshot(captor.capture());
        assertThat(captor.getValue().getPeakAccountEquity()).isEqualByComparingTo("10250.25");
    }

    @Test
    void recordPositionSnapshotPersistsTraceScopedChangeLogForNewPosition() {
        PositionSnapshot snapshot = new PositionSnapshot();
        snapshot.setTraceId("trace-position-1");
        snapshot.setExchangeCode("binance");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setSide("long");
        snapshot.setPositionQuantity(new java.math.BigDecimal("0.0546875"));
        snapshot.setEntryPrice(new java.math.BigDecimal("64000"));
        snapshot.setUnrealizedPnl(java.math.BigDecimal.ZERO);
        snapshot.setCreatedAt("2026-05-08T03:37:54Z");

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("binance", "BTCUSDT", "long")).thenReturn(null);

        tradeExecutionService.recordPositionSnapshot(snapshot);

        ArgumentCaptor<PositionSnapshot> snapshotCaptor = ArgumentCaptor.forClass(PositionSnapshot.class);
        verify(tradeExecutionMapper).insertPositionSnapshot(snapshotCaptor.capture());
        assertThat(snapshotCaptor.getValue().getTraceId()).isEqualTo("trace-position-1");
        assertThat(snapshotCaptor.getValue().getCreatedAt()).isEqualTo("2026-05-08 11:37:54");

        ArgumentCaptor<PositionChangeLog> changeCaptor = ArgumentCaptor.forClass(PositionChangeLog.class);
        verify(tradeExecutionMapper).insertPositionChangeLog(changeCaptor.capture());
        assertThat(changeCaptor.getValue().getTraceId()).isEqualTo("trace-position-1");
        assertThat(changeCaptor.getValue().getChangeType()).isEqualTo("OPEN");
        assertThat(changeCaptor.getValue().getBeforeQuantity()).isEqualByComparingTo("0");
        assertThat(changeCaptor.getValue().getAfterQuantity()).isEqualByComparingTo("0.0546875");
    }

    @Test
    void markToMarketSnapshotDoesNotPolluteTheChangeLog() {
        // 浮盈盯市会以相同数量、相同方向重新落一次快照。快照该落，但"仓位
        // 变更"是给人看的列表，一条 delta 为 0 的记录只会把真正的开平仓淹掉。
        PositionSnapshot previous = new PositionSnapshot();
        previous.setTraceId("trace-open-1");
        previous.setEntryTraceId("trace-open-1");
        previous.setExchangeCode("binance");
        previous.setSymbol("BNBUSDT");
        previous.setSide("long");
        previous.setPositionQuantity(new java.math.BigDecimal("0.01"));
        previous.setEntryPrice(new java.math.BigDecimal("701.16"));

        PositionSnapshot mark = new PositionSnapshot();
        mark.setTraceId("trace-hold-9");
        mark.setEntryTraceId("trace-open-1");
        mark.setExchangeCode("binance");
        mark.setSymbol("BNBUSDT");
        mark.setSide("long");
        mark.setPositionQuantity(new java.math.BigDecimal("0.01"));
        mark.setEntryPrice(new java.math.BigDecimal("701.16"));
        mark.setUnrealizedPnl(new java.math.BigDecimal("0.1132"));

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("binance", "BNBUSDT", "long"))
            .thenReturn(previous);

        tradeExecutionService.recordPositionSnapshot(mark);

        // 快照要落——控制台的收益读的就是它
        ArgumentCaptor<PositionSnapshot> captor = ArgumentCaptor.forClass(PositionSnapshot.class);
        verify(tradeExecutionMapper).insertPositionSnapshot(captor.capture());
        assertThat(captor.getValue().getUnrealizedPnl()).isEqualByComparingTo("0.1132");
        // 变更日志不要落
        verify(tradeExecutionMapper, never()).insertPositionChangeLog(any(PositionChangeLog.class));
    }

    @Test
    void realPositionChangesStillReachTheChangeLog() {
        // 守卫不能把真实的加仓一起挡掉。
        PositionSnapshot previous = new PositionSnapshot();
        previous.setExchangeCode("binance");
        previous.setSymbol("BNBUSDT");
        previous.setSide("long");
        previous.setPositionQuantity(new java.math.BigDecimal("0.01"));

        PositionSnapshot added = new PositionSnapshot();
        added.setTraceId("trace-add-1");
        added.setExchangeCode("binance");
        added.setSymbol("BNBUSDT");
        added.setSide("long");
        added.setPositionQuantity(new java.math.BigDecimal("0.02"));
        added.setEntryPrice(new java.math.BigDecimal("705.00"));

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("binance", "BNBUSDT", "long"))
            .thenReturn(previous);

        tradeExecutionService.recordPositionSnapshot(added);

        ArgumentCaptor<PositionChangeLog> captor = ArgumentCaptor.forClass(PositionChangeLog.class);
        verify(tradeExecutionMapper).insertPositionChangeLog(captor.capture());
        assertThat(captor.getValue().getChangeType()).isEqualTo("ADD");
    }

    @Test
    void recordPositionSnapshotSendsNotificationWhenPositionOpens() {
        PositionSnapshot snapshot = new PositionSnapshot();
        snapshot.setTraceId("trace-position-open-1");
        snapshot.setUserId(42L);
        snapshot.setExchangeCode("binance");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setSide("long");
        snapshot.setPositionQuantity(new java.math.BigDecimal("0.0546875"));
        snapshot.setEntryPrice(new java.math.BigDecimal("64000"));
        snapshot.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("binance", "BTCUSDT", "long")).thenReturn(null);

        tradeExecutionService.recordPositionSnapshot(snapshot);

        verify(notifyRecordService).sendByUserId(anyLong(), anyString(), anyString());
    }

    @Test
    void recordPositionSnapshotSendsNotificationWhenPositionAdds() {
        PositionSnapshot previous = new PositionSnapshot();
        previous.setId(8L);
        previous.setTraceId("trace-position-open-1");
        previous.setExchangeCode("binance");
        previous.setSymbol("BTCUSDT");
        previous.setSide("long");
        previous.setPositionQuantity(new java.math.BigDecimal("0.0546875"));
        previous.setEntryPrice(new java.math.BigDecimal("64000"));
        previous.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        PositionSnapshot snapshot = new PositionSnapshot();
        snapshot.setTraceId("trace-position-add-1");
        snapshot.setUserId(42L);
        snapshot.setExchangeCode("binance");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setSide("long");
        snapshot.setPositionQuantity(new java.math.BigDecimal("0.0750000"));
        snapshot.setEntryPrice(new java.math.BigDecimal("64100"));
        snapshot.setUnrealizedPnl(new java.math.BigDecimal("12.50"));

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("binance", "BTCUSDT", "long")).thenReturn(previous);

        tradeExecutionService.recordPositionSnapshot(snapshot);

        verify(notifyRecordService).sendByUserId(anyLong(), anyString(), anyString());
    }

    @Test
    void recordPositionSnapshotSendsNotificationWhenPositionCloses() {
        PositionSnapshot previous = new PositionSnapshot();
        previous.setId(9L);
        previous.setTraceId("trace-position-add-1");
        previous.setExchangeCode("binance");
        previous.setSymbol("BTCUSDT");
        previous.setSide("long");
        previous.setPositionQuantity(new java.math.BigDecimal("0.0750000"));
        previous.setEntryPrice(new java.math.BigDecimal("64100"));
        previous.setUnrealizedPnl(new java.math.BigDecimal("12.50"));

        PositionSnapshot snapshot = new PositionSnapshot();
        snapshot.setTraceId("trace-position-close-1");
        snapshot.setUserId(42L);
        snapshot.setExchangeCode("binance");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setSide("long");
        snapshot.setPositionQuantity(java.math.BigDecimal.ZERO);
        snapshot.setEntryPrice(new java.math.BigDecimal("64200"));
        snapshot.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("binance", "BTCUSDT", "long")).thenReturn(previous);

        tradeExecutionService.recordPositionSnapshot(snapshot);

        verify(notifyRecordService).sendByUserId(anyLong(), anyString(), anyString());
    }

    @Test
    void recordPositionSnapshotAppendsHistoryInsteadOfUpdatingScopeRow() {
        PositionSnapshot previous = new PositionSnapshot();
        previous.setId(18L);
        previous.setTraceId("trace-position-open-1");
        previous.setExchangeCode("binance");
        previous.setSymbol("BTCUSDT");
        previous.setSide("short");
        previous.setPositionQuantity(new java.math.BigDecimal("1.50000000"));
        previous.setEntryPrice(new java.math.BigDecimal("2371.05000000"));
        previous.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        PositionSnapshot snapshot = new PositionSnapshot();
        snapshot.setTraceId("trace-position-close-1");
        snapshot.setExchangeCode("binance");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setSide("short");
        snapshot.setPositionQuantity(java.math.BigDecimal.ZERO);
        snapshot.setEntryPrice(java.math.BigDecimal.ZERO);
        snapshot.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("binance", "BTCUSDT", "short")).thenReturn(previous);

        tradeExecutionService.recordPositionSnapshot(snapshot);

        ArgumentCaptor<PositionSnapshot> snapshotCaptor = ArgumentCaptor.forClass(PositionSnapshot.class);
        verify(tradeExecutionMapper).insertPositionSnapshot(snapshotCaptor.capture());
        verify(tradeExecutionMapper, never()).updatePositionSnapshot(org.mockito.ArgumentMatchers.any(PositionSnapshot.class));
        assertThat(snapshotCaptor.getValue().getTraceId()).isEqualTo("trace-position-close-1");

        ArgumentCaptor<PositionChangeLog> changeCaptor = ArgumentCaptor.forClass(PositionChangeLog.class);
        verify(tradeExecutionMapper).insertPositionChangeLog(changeCaptor.capture());
        assertThat(changeCaptor.getValue().getTraceId()).isEqualTo("trace-position-close-1");
        assertThat(changeCaptor.getValue().getBeforeQuantity()).isEqualByComparingTo("1.50000000");
        assertThat(changeCaptor.getValue().getAfterQuantity()).isEqualByComparingTo("0");
        assertThat(changeCaptor.getValue().getChangeType()).isEqualTo("CLOSE");
    }


    @Test
    void recordFlatCloseSnapshotInheritsEntryTraceIdAndPreviousSide() {
        PositionSnapshot previous = new PositionSnapshot();
        previous.setTraceId("trace-open-1");
        previous.setEntryTraceId("trace-open-1");
        previous.setExchangeCode("okx");
        previous.setSymbol("ETHUSDT");
        previous.setSide("long");
        previous.setPositionQuantity(new java.math.BigDecimal("0.50000000"));
        previous.setEntryPrice(new java.math.BigDecimal("1691.64000000"));
        previous.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        PositionSnapshot closeSnapshot = new PositionSnapshot();
        closeSnapshot.setTraceId("trace-close-1");
        closeSnapshot.setExchangeCode("okx");
        closeSnapshot.setSymbol("ETHUSDT");
        closeSnapshot.setSide("flat");
        closeSnapshot.setPositionQuantity(java.math.BigDecimal.ZERO);
        closeSnapshot.setEntryPrice(java.math.BigDecimal.ZERO);
        closeSnapshot.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        when(tradeExecutionMapper.selectLatestActivePositionSnapshotByScope("okx", "ETHUSDT")).thenReturn(previous);

        tradeExecutionService.recordPositionSnapshot(closeSnapshot);

        ArgumentCaptor<PositionSnapshot> snapshotCaptor = ArgumentCaptor.forClass(PositionSnapshot.class);
        verify(tradeExecutionMapper).insertPositionSnapshot(snapshotCaptor.capture());
        assertThat(snapshotCaptor.getValue().getTraceId()).isEqualTo("trace-close-1");
        assertThat(snapshotCaptor.getValue().getEntryTraceId()).isEqualTo("trace-open-1");

        ArgumentCaptor<PositionChangeLog> changeCaptor = ArgumentCaptor.forClass(PositionChangeLog.class);
        verify(tradeExecutionMapper).insertPositionChangeLog(changeCaptor.capture());
        assertThat(changeCaptor.getValue().getSide()).isEqualTo("long");
        assertThat(changeCaptor.getValue().getChangeType()).isEqualTo("CLOSE");
        assertThat(changeCaptor.getValue().getBeforeQuantity()).isEqualByComparingTo("0.50000000");
        assertThat(changeCaptor.getValue().getAfterQuantity()).isEqualByComparingTo("0");
    }

    @Test
    void recordPositionSnapshotInheritsEntryTraceIdFromPreviousActiveSnapshot() {
        PositionSnapshot previous = new PositionSnapshot();
        previous.setTraceId("trace-open-1");
        previous.setEntryTraceId("trace-open-1");
        previous.setExchangeCode("okx");
        previous.setSymbol("ETHUSDT");
        previous.setSide("long");
        previous.setPositionQuantity(new java.math.BigDecimal("0.50000000"));
        previous.setEntryPrice(new java.math.BigDecimal("1691.64000000"));
        previous.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        PositionSnapshot reduceSnapshot = new PositionSnapshot();
        reduceSnapshot.setTraceId("trace-reduce-1");
        reduceSnapshot.setExchangeCode("okx");
        reduceSnapshot.setSymbol("ETHUSDT");
        reduceSnapshot.setSide("long");
        reduceSnapshot.setPositionQuantity(new java.math.BigDecimal("0.25000000"));
        reduceSnapshot.setEntryPrice(new java.math.BigDecimal("1691.64000000"));
        reduceSnapshot.setUnrealizedPnl(new java.math.BigDecimal("-2.50"));

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("okx", "ETHUSDT", "long")).thenReturn(previous);

        tradeExecutionService.recordPositionSnapshot(reduceSnapshot);

        ArgumentCaptor<PositionSnapshot> snapshotCaptor = ArgumentCaptor.forClass(PositionSnapshot.class);
        verify(tradeExecutionMapper).insertPositionSnapshot(snapshotCaptor.capture());
        assertThat(snapshotCaptor.getValue().getTraceId()).isEqualTo("trace-reduce-1");
        assertThat(snapshotCaptor.getValue().getEntryTraceId()).isEqualTo("trace-open-1");
    }

    @Test
    void recordPositionSnapshotNormalizesOrderSideAliasesBeforeLookupAndPersist() {
        PositionSnapshot snapshot = new PositionSnapshot();
        snapshot.setTraceId("trace-position-alias-1");
        snapshot.setExchangeCode("okx");
        snapshot.setSymbol("BTCUSDT");
        snapshot.setSide("buy");
        snapshot.setPositionQuantity(new java.math.BigDecimal("0.03764020"));
        snapshot.setEntryPrice(new java.math.BigDecimal("78187.70"));
        snapshot.setUnrealizedPnl(java.math.BigDecimal.ZERO);

        when(tradeExecutionMapper.selectLatestPositionSnapshotByScope("okx", "BTCUSDT", "long")).thenReturn(null);

        tradeExecutionService.recordPositionSnapshot(snapshot);

        ArgumentCaptor<PositionSnapshot> snapshotCaptor = ArgumentCaptor.forClass(PositionSnapshot.class);
        verify(tradeExecutionMapper).insertPositionSnapshot(snapshotCaptor.capture());
        assertThat(snapshotCaptor.getValue().getSide()).isEqualTo("long");
    }

}
