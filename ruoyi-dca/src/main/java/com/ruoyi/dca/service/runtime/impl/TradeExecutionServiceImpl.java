package com.ruoyi.dca.service.runtime.impl;

import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.order.OrderRequest;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionChangeLog;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import com.ruoyi.dca.mapper.runtime.TradeExecutionMapper;
import com.ruoyi.dca.service.INotifyRecordService;
import com.ruoyi.dca.service.runtime.ITradeExecutionService;
import com.ruoyi.dca.support.TradeExecutionStatusNormalizer;
import com.ruoyi.dca.support.TradeRuntimeTimeUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/**
 * 交易执行服务实现类
 *
 * 实现订单、成交、风控、持仓等交易执行数据的记录和查询业务逻辑。
 * 主要功能：
 * - 记录订单请求和交易所订单
 * - 记录成交信息
 * - 记录风控触发事件
 * - 记录盈亏快照和持仓快照
 * - 查询交易执行历史记录
 *
 * @author ruoyi-dca
 */
@Service
public class TradeExecutionServiceImpl implements ITradeExecutionService {

    private static final Logger log = LoggerFactory.getLogger(TradeExecutionServiceImpl.class);

    @Autowired
    private TradeExecutionMapper tradeExecutionMapper;

    @Autowired
    private INotifyRecordService notifyRecordService;

    /**
     * 记录订单请求
     *
     * @param request 订单请求
     */
    @Override
    public void recordOrderRequest(OrderRequest request) {
        if (request.getTraceId() == null || request.getTraceId().isBlank()) {
            request.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        tradeExecutionMapper.insertOrderRequest(request);
    }

    /**
     * 记录交易所订单
     *
     * @param order 交易所订单
     */
    @Override
    public void recordExchangeOrder(ExchangeOrder order) {
        if (order.getTraceId() == null || order.getTraceId().isBlank()) {
            order.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        TradeExecutionStatusNormalizer.StatusPair statusPair = TradeExecutionStatusNormalizer.normalize(
            order.getStatus(),
            order.getExecutionStatus(),
            order.getOrderStatus()
        );
        order.setStatus(statusPair.executionStatus());
        order.setExecutionStatus(statusPair.executionStatus());
        order.setOrderStatus(statusPair.orderStatus());
        order.setOrderRef(blankToNull(order.getOrderRef()));
        order.setCreatedAt(normalizeCreatedAt(order.getCreatedAt()));
        order.setUpdatedAt(normalizeNullableDateTime(order.getUpdatedAt()));
        order.setFilledAt(normalizeNullableDateTime(order.getFilledAt()));
        if (hasText(order.getExchangeCode()) && hasText(order.getOrderRef())) {
            int updated = tradeExecutionMapper.updateExchangeOrderByRef(order);
            if (updated > 0) {
                return;
            }
        }
        tradeExecutionMapper.insertExchangeOrder(order);
    }

    /**
     * 记录成交信息
     *
     * @param fill 成交信息
     */
    @Override
    public void recordExchangeFill(ExchangeFill fill) {
        if (fill.getTraceId() == null || fill.getTraceId().isBlank()) {
            fill.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        fill.setTradeId(blankToNull(fill.getTradeId()));
        fill.setCreatedAt(normalizeCreatedAt(fill.getCreatedAt()));
        fill.setFilledAt(normalizeNullableDateTime(fill.getFilledAt()));
        if (hasText(fill.getExchangeCode()) && hasText(fill.getTradeId())) {
            int updated = tradeExecutionMapper.updateExchangeFillByTradeId(fill);
            if (updated > 0) {
                return;
            }
        }
        tradeExecutionMapper.insertExchangeFill(fill);
    }

    /**
     * 记录风控触发信息
     *
     * @param riskGuardHit 风控触发信息
     */
    @Override
    public void recordRiskGuardHit(RiskGuardHit riskGuardHit) {
        if (riskGuardHit.getTraceId() == null || riskGuardHit.getTraceId().isBlank()) {
            riskGuardHit.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        riskGuardHit.setCreatedAt(normalizeCreatedAt(riskGuardHit.getCreatedAt()));
        tradeExecutionMapper.insertRiskGuardHit(riskGuardHit);
    }

    /**
     * 记录盈亏快照
     *
     * @param pnlSnapshot 盈亏快照
     */
    @Override
    public void recordPnlSnapshot(PnlSnapshot pnlSnapshot) {
        if (pnlSnapshot.getTraceId() == null || pnlSnapshot.getTraceId().isBlank()) {
            pnlSnapshot.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        pnlSnapshot.setCreatedAt(normalizeCreatedAt(pnlSnapshot.getCreatedAt()));
        if (pnlSnapshot.getUnrealizedPnl() == null) {
            pnlSnapshot.setUnrealizedPnl(BigDecimal.ZERO);
        }
        if (pnlSnapshot.getRealizedPnl() == null) {
            pnlSnapshot.setRealizedPnl(BigDecimal.ZERO);
        }
        if (pnlSnapshot.getDailyPnl() == null) {
            pnlSnapshot.setDailyPnl(BigDecimal.ZERO);
        }
        if (pnlSnapshot.getMaxDrawdownPct() == null) {
            pnlSnapshot.setMaxDrawdownPct(BigDecimal.ZERO);
        }
        if (pnlSnapshot.getPeakAccountEquity() == null) {
            pnlSnapshot.setPeakAccountEquity(
                pnlSnapshot.getAccountEquity() == null ? BigDecimal.ZERO : pnlSnapshot.getAccountEquity()
            );
        }
        tradeExecutionMapper.insertPnlSnapshot(pnlSnapshot);
    }

    @Override
    public void recordPositionSnapshot(PositionSnapshot positionSnapshot) {
        if (positionSnapshot.getTraceId() == null || positionSnapshot.getTraceId().isBlank()) {
            positionSnapshot.setTraceId(UUID.randomUUID().toString().replace("-", ""));
        }
        if (positionSnapshot.getPositionQuantity() == null) {
            positionSnapshot.setPositionQuantity(BigDecimal.ZERO);
        }
        if (positionSnapshot.getUnrealizedPnl() == null) {
            positionSnapshot.setUnrealizedPnl(BigDecimal.ZERO);
        }
        positionSnapshot.setSide(normalizePositionSide(positionSnapshot.getSide()));
        normalizePositionSnapshotCreatedAt(positionSnapshot);
        PositionSnapshot previous = selectPreviousPositionSnapshot(positionSnapshot);
        normalizePositionSnapshotEntryTraceId(positionSnapshot, previous);
        tradeExecutionMapper.insertPositionSnapshot(positionSnapshot);
        PositionChangeLog changeLog = buildPositionChangeLog(positionSnapshot, previous);
        tradeExecutionMapper.insertPositionChangeLog(changeLog);
        sendPositionChangeNotification(positionSnapshot, changeLog);
    }

    private void normalizePositionSnapshotCreatedAt(PositionSnapshot positionSnapshot) {
        positionSnapshot.setCreatedAt(normalizeCreatedAt(positionSnapshot.getCreatedAt()));
    }

    private PositionSnapshot selectPreviousPositionSnapshot(PositionSnapshot positionSnapshot) {
        if (positionSnapshot == null) {
            return null;
        }
        String side = positionSnapshot.getSide() == null ? "" : positionSnapshot.getSide().trim().toLowerCase();
        if ("flat".equals(side)) {
            return tradeExecutionMapper.selectLatestActivePositionSnapshotByScope(
                positionSnapshot.getExchangeCode(),
                positionSnapshot.getSymbol()
            );
        }
        return tradeExecutionMapper.selectLatestPositionSnapshotByScope(
            positionSnapshot.getExchangeCode(),
            positionSnapshot.getSymbol(),
            positionSnapshot.getSide()
        );
    }

    private void normalizePositionSnapshotEntryTraceId(PositionSnapshot positionSnapshot, PositionSnapshot previous) {
        if (positionSnapshot == null || hasText(positionSnapshot.getEntryTraceId())) {
            return;
        }
        BigDecimal quantity = positionSnapshot.getPositionQuantity() == null ? BigDecimal.ZERO : positionSnapshot.getPositionQuantity();
        String side = positionSnapshot.getSide() == null ? "" : positionSnapshot.getSide().trim().toLowerCase();
        if (previous != null) {
            BigDecimal previousQuantity = previous.getPositionQuantity() == null ? BigDecimal.ZERO : previous.getPositionQuantity();
            String previousSide = previous.getSide() == null ? "" : previous.getSide().trim().toLowerCase();
            if (previousQuantity.compareTo(BigDecimal.ZERO) > 0 && (side.equals(previousSide) || "flat".equals(side))) {
                String previousEntryTraceId = blankToNull(previous.getEntryTraceId());
                positionSnapshot.setEntryTraceId(previousEntryTraceId == null ? blankToNull(previous.getTraceId()) : previousEntryTraceId);
                return;
            }
        }
        if (quantity.compareTo(BigDecimal.ZERO) <= 0 || "flat".equals(side)) {
            return;
        }
        positionSnapshot.setEntryTraceId(blankToNull(positionSnapshot.getTraceId()));
    }

    private String normalizeCreatedAt(String createdAt) {
        String normalized = TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(createdAt);
        if (normalized == null || normalized.isBlank() || normalized.matches("^-?\\d+$")) {
            return TradeRuntimeTimeUtils.nowSqlDateTime();
        }
        return normalized;
    }

    private String normalizeNullableDateTime(String value) {
        String normalized = TradeRuntimeTimeUtils.normalizeToDatabaseDateTime(value);
        if (normalized == null || normalized.isBlank() || normalized.matches("^-?\\d+$")) {
            return null;
        }
        return normalized;
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private String blankToNull(String value) {
        return hasText(value) ? value.trim() : null;
    }

    @Override
    public List<ExchangeOrder> listOrders(String status, String orderStatus) {
        return tradeExecutionMapper.selectExchangeOrders(status, orderStatus);
    }

    @Override
    public List<ExchangeOrder> listPendingLiveOrders(String exchangeCode, String symbol, String mode) {
        return tradeExecutionMapper.selectPendingLiveOrders(exchangeCode, symbol, mode);
    }

    @Override
    public List<ExchangeFill> listFills() {
        return tradeExecutionMapper.selectExchangeFills();
    }

    @Override
    public List<RiskGuardHit> listRiskGuardHits() {
        return tradeExecutionMapper.selectRiskGuardHits();
    }

    @Override
    public List<PositionSnapshot> listPositions() {
        return tradeExecutionMapper.selectPositionSnapshots();
    }

    @Override
    public List<PositionChangeLog> listPositionChanges() {
        return tradeExecutionMapper.selectPositionChangeLogs();
    }


    private String normalizePositionSide(String side) {
        if (side == null || side.isBlank()) {
            return "flat";
        }
        String normalized = side.trim().toLowerCase(Locale.ROOT);
        if ("buy".equals(normalized) || "long".equals(normalized)) {
            return "long";
        }
        if ("sell".equals(normalized) || "short".equals(normalized)) {
            return "short";
        }
        if ("hold".equals(normalized) || "skip".equals(normalized) || "none".equals(normalized) || "no_action".equals(normalized)) {
            return "flat";
        }
        return normalized;
    }

    private PositionChangeLog buildPositionChangeLog(PositionSnapshot current, PositionSnapshot previous) {
        BigDecimal beforeQuantity = previous == null || previous.getPositionQuantity() == null
            ? BigDecimal.ZERO
            : previous.getPositionQuantity();
        BigDecimal afterQuantity = current.getPositionQuantity() == null
            ? BigDecimal.ZERO
            : current.getPositionQuantity();
        PositionChangeLog changeLog = new PositionChangeLog();
        changeLog.setTraceId(current.getTraceId());
        changeLog.setExchangeCode(current.getExchangeCode());
        changeLog.setSymbol(current.getSymbol());
        String changeSide = current.getSide();
        if ("flat".equalsIgnoreCase(changeSide) && previous != null && previous.getSide() != null
            && beforeQuantity.compareTo(BigDecimal.ZERO) > 0) {
            changeSide = previous.getSide();
        }
        changeLog.setSide(changeSide);
        changeLog.setBeforeQuantity(beforeQuantity);
        changeLog.setAfterQuantity(afterQuantity);
        changeLog.setDeltaQuantity(afterQuantity.subtract(beforeQuantity));
        changeLog.setEntryPrice(current.getEntryPrice());
        changeLog.setUnrealizedPnl(current.getUnrealizedPnl());
        changeLog.setCreatedAt(normalizeCreatedAt(current.getCreatedAt()));
        changeLog.setChangeType(resolveChangeType(previous, beforeQuantity, afterQuantity, changeSide));
        return changeLog;
    }

    private String resolveChangeType(PositionSnapshot previous,
                                     BigDecimal beforeQuantity,
                                     BigDecimal afterQuantity,
                                     String currentSide) {
        if (previous != null && previous.getSide() != null && currentSide != null
            && !previous.getSide().equalsIgnoreCase(currentSide)
            && beforeQuantity.compareTo(BigDecimal.ZERO) > 0
            && afterQuantity.compareTo(BigDecimal.ZERO) > 0) {
            return "REVERSE";
        }
        if (beforeQuantity.compareTo(BigDecimal.ZERO) == 0 && afterQuantity.compareTo(BigDecimal.ZERO) > 0) {
            return "OPEN";
        }
        if (beforeQuantity.compareTo(BigDecimal.ZERO) > 0 && afterQuantity.compareTo(BigDecimal.ZERO) == 0) {
            return "CLOSE";
        }
        if (afterQuantity.abs().compareTo(beforeQuantity.abs()) > 0) {
            return "ADD";
        }
        if (afterQuantity.abs().compareTo(beforeQuantity.abs()) < 0) {
            return "REDUCE";
        }
        return "UPDATE";
    }

    private void sendPositionChangeNotification(PositionSnapshot snapshot, PositionChangeLog changeLog) {
        if (snapshot == null || changeLog == null || snapshot.getUserId() == null || notifyRecordService == null) {
            return;
        }
        String changeType = changeLog.getChangeType();
        if (!"OPEN".equals(changeType) && !"ADD".equals(changeType) && !"CLOSE".equals(changeType)) {
            return;
        }
        try {
            notifyRecordService.sendByUserId(
                snapshot.getUserId(),
                buildNotificationTitle(changeType, snapshot),
                buildNotificationContent(changeType, snapshot, changeLog)
            );
        } catch (Exception ex) {
            log.warn("Failed to send trade execution notification: traceId={}, changeType={}", snapshot.getTraceId(), changeType, ex);
        }
    }

    private String buildNotificationTitle(String changeType, PositionSnapshot snapshot) {
        String actionLabel;
        if ("OPEN".equals(changeType)) {
            actionLabel = "开仓";
        } else if ("ADD".equals(changeType)) {
            actionLabel = "加仓";
        } else {
            actionLabel = "平仓";
        }
        return "AI交易" + actionLabel + "通知";
    }

    private String buildNotificationContent(String changeType, PositionSnapshot snapshot, PositionChangeLog changeLog) {
        return String.format(
            "类型:%s 标的:%s 方向:%s 数量:%s 价格:%s traceId:%s",
            changeType,
            defaultString(snapshot.getSymbol()),
            defaultString(snapshot.getSide()),
            formatDecimal(changeLog.getDeltaQuantity() == null ? snapshot.getPositionQuantity() : changeLog.getDeltaQuantity().abs()),
            formatDecimal(snapshot.getEntryPrice()),
            defaultString(snapshot.getTraceId())
        );
    }

    private String formatDecimal(BigDecimal value) {
        if (value == null) {
            return "0";
        }
        return value.stripTrailingZeros().toPlainString();
    }

    private String defaultString(String value) {
        return value == null ? "" : value;
    }
}

