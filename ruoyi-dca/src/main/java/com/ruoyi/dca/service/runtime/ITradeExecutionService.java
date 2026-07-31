package com.ruoyi.dca.service.runtime;

import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.order.OrderRequest;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionChangeLog;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;

import java.util.List;

/**
 * 交易执行服务接口
 * 提供订单、成交、风控、持仓等交易执行数据的记录和查询业务逻辑
 *
 * @author ruoyi-dca
 */
public interface ITradeExecutionService {

    /**
     * 记录订单请求
     *
     * @param request 订单请求
     */
    void recordOrderRequest(OrderRequest request);

    /**
     * 记录交易所订单
     *
     * @param order 交易所订单
     */
    void recordExchangeOrder(ExchangeOrder order);

    List<ExchangeOrder> listPendingLiveOrders(String exchangeCode, String symbol, String mode);

    /**
     * 记录成交信息
     *
     * @param fill 成交信息
     */
    void recordExchangeFill(ExchangeFill fill);

    /**
     * 记录风控触发信息
     *
     * @param riskGuardHit 风控触发信息
     */
    void recordRiskGuardHit(RiskGuardHit riskGuardHit);

    /**
     * 记录盈亏快照
     *
     * @param pnlSnapshot 盈亏快照
     */
    void recordPnlSnapshot(PnlSnapshot pnlSnapshot);

    /**
     * 记录持仓快照
     *
     * @param positionSnapshot 持仓快照
     */
    void recordPositionSnapshot(PositionSnapshot positionSnapshot);

    /**
     * 查询订单列表
     *
     * @param status 状态
     * @param orderStatus 订单状态
     * @return 订单列表
     */
    List<ExchangeOrder> listOrders(String status, String orderStatus);

    /**
     * 查询成交列表
     *
     * @return 成交列表
     */
    List<ExchangeFill> listFills();

    /**
     * 查询风控触发记录列表
     *
     * @return 风控触发记录列表
     */
    List<RiskGuardHit> listRiskGuardHits();

    /**
     * 查询持仓列表
     *
     * @return 持仓列表
     */
    List<PositionSnapshot> listPositions();

    /**
     * 查询持仓变更记录列表
     *
     * @return 持仓变更记录列表
     */
    List<PositionChangeLog> listPositionChanges();
}

