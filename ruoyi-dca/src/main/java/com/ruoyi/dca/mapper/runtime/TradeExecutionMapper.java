package com.ruoyi.dca.mapper.runtime;

import com.ruoyi.dca.domain.order.ExchangeFill;
import com.ruoyi.dca.domain.order.ExchangeOrder;
import com.ruoyi.dca.domain.order.OrderRequest;
import com.ruoyi.dca.domain.pnl.PnlSnapshot;
import com.ruoyi.dca.domain.position.PositionChangeLog;
import com.ruoyi.dca.domain.position.PositionSnapshot;
import com.ruoyi.dca.domain.risk.RiskGuardHit;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * 交易执行Mapper接口
 * 提供订单、成交、风控、持仓等交易执行数据的数据库访问操作
 *
 * @author ruoyi-dca
 */
public interface TradeExecutionMapper {

    /**
     * 插入订单请求
     *
     * @param request 订单请求
     * @return 影响行数
     */
    int insertOrderRequest(OrderRequest request);

    /**
     * 插入交易所订单
     *
     * @param order 交易所订单
     * @return 影响行数
     */
    int insertExchangeOrder(ExchangeOrder order);

    int updateExchangeOrderByRef(ExchangeOrder order);

    /**
     * 插入成交记录
     *
     * @param fill 成交信息
     * @return 影响行数
     */
    int insertExchangeFill(ExchangeFill fill);

    int updateExchangeFillByTradeId(ExchangeFill fill);

    /**
     * 插入风控触发记录
     *
     * @param riskGuardHit 风控触发信息
     * @return 影响行数
     */
    int insertRiskGuardHit(RiskGuardHit riskGuardHit);

    /**
     * 插入持仓快照
     *
     * @param positionSnapshot 持仓快照
     * @return 影响行数
     */
    int insertPositionSnapshot(PositionSnapshot positionSnapshot);

    /**
     * 更新持仓快照
     *
     * @param positionSnapshot 持仓快照
     * @return 影响行数
     */
    int updatePositionSnapshot(PositionSnapshot positionSnapshot);

    /**
     * 根据范围查询最新持仓快照
     *
     * @param exchangeCode 交易所代码
     * @param symbol 交易品种
     * @param side 方向
     * @return 持仓快照
     */
    PositionSnapshot selectLatestPositionSnapshotByScope(@Param("exchangeCode") String exchangeCode,
                                                         @Param("symbol") String symbol,
                                                         @Param("side") String side);

    /**
     * 根据范围查询最新持仓快照ID
     *
     * @param exchangeCode 交易所代码
     * @param symbol 交易品种
     * @param side 方向
     * @return 持仓快照ID
     */
    Long selectLatestPositionSnapshotIdByScope(@Param("exchangeCode") String exchangeCode,
                                               @Param("symbol") String symbol,
                                               @Param("side") String side);

    /**
     * 插入持仓变更记录
     *
     * @param positionChangeLog 持仓变更记录
     * @return 影响行数
     */
    int insertPositionChangeLog(PositionChangeLog positionChangeLog);

    /**
     * 插入盈亏快照
     *
     * @param pnlSnapshot 盈亏快照
     * @return 影响行数
     */
    int insertPnlSnapshot(PnlSnapshot pnlSnapshot);

    /**
     * 根据模式查询最新盈亏快照
     *
     * @param mode 模式
     * @return 盈亏快照
     */
    PnlSnapshot selectLatestPnlSnapshotByMode(@Param("mode") String mode);

    /**
     * 查询最新盈亏快照
     *
     * @return 盈亏快照
     */
    PnlSnapshot selectLatestPnlSnapshot();

    /**
     * 查询交易所订单列表
     *
     * @param status 状态
     * @param orderStatus 订单状态
     * @return 订单列表
     */
    List<ExchangeOrder> selectExchangeOrders(@Param("status") String status,
                                             @Param("orderStatus") String orderStatus);

    List<ExchangeOrder> selectPendingLiveOrders(@Param("exchangeCode") String exchangeCode,
                                                @Param("symbol") String symbol,
                                                @Param("mode") String mode);

    /**
     * 根据范围查询最近的交易所订单
     *
     * @param exchangeCode 交易所代码
     * @param symbol 交易品种
     * @param limit 限制数量
     * @return 订单列表
     */
    List<ExchangeOrder> selectRecentExchangeOrdersByScope(@Param("exchangeCode") String exchangeCode,
                                                          @Param("symbol") String symbol,
                                                          @Param("limit") int limit);

    /**
     * 查询成交列表
     *
     * @return 成交列表
     */
    List<ExchangeFill> selectExchangeFills();

    /**
     * 查询风控触发记录列表
     *
     * @return 风控触发记录列表
     */
    List<RiskGuardHit> selectRiskGuardHits();

    /**
     * 查询执行状态统计
     *
     * @return 状态统计列表
     */
    List<Map<String, Object>> selectExecutionStatusCounts();

    /**
     * 查询持仓快照列表
     *
     * @return 持仓快照列表
     */
    List<PositionSnapshot> selectPositionSnapshots();

    /**
     * 根据范围查询最新活跃持仓快照
     *
     * @param exchangeCode 交易所代码
     * @param symbol 交易品种
     * @return 持仓快照
     */
    PositionSnapshot selectLatestActivePositionSnapshotByScope(@Param("exchangeCode") String exchangeCode,
                                                               @Param("symbol") String symbol);

    /**
     * 查询持仓变更记录列表
     *
     * @return 持仓变更记录列表
     */
    List<PositionChangeLog> selectPositionChangeLogs();
}

